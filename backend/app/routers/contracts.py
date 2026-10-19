import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import Contract, KbDocument, User
from app.schemas import ContractBrief, ContractDetail, LawyerReviewIn
from app.services.agents import contract_agents
from app.utils import parse_uploaded_file, sanitize_filename

router = APIRouter(prefix="/api/contracts", tags=["合同审查"])

VERDICTS = {"compliant", "needs_revision", "non_compliant"}


def _can_view(user: User, c: Contract) -> bool:
    if user.role in ("super_admin", "lawyer"):
        return True
    return c.owner_id == user.id


def _brief(c: Contract, db: Session) -> dict:
    owner = db.get(User, c.owner_id)
    reviewer = db.get(User, c.reviewer_id) if c.reviewer_id else None
    return {
        "id": c.id,
        "name": c.name,
        "status": c.status,
        "score": c.score,
        "verdict": c.verdict,
        "owner_id": c.owner_id,
        "owner_name": owner.nickname if owner else None,
        "reviewer_name": reviewer.nickname if reviewer else None,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
    }


@router.post("/upload", response_model=ContractBrief)
def upload_contract(
    file: UploadFile = File(...),
    name: str = Form(default=""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = file.file.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "文件过大（限制 20MB）")
    file_type, text = parse_uploaded_file(file.filename or "contract.txt", data)
    text = (text or "").strip()
    if len(text) < 30:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "无法从文件中解析出有效合同内容，请上传 txt/pdf/docx 等文本文档")

    store_dir = Path(settings.UPLOAD_DIR) / "contracts"
    store_dir.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid.uuid4().hex[:12]}_{sanitize_filename(file.filename or 'contract.txt')}"
    (store_dir / stored).write_bytes(data)

    contract = Contract(
        name=(name or "").strip() or (file.filename or "未命名合同"),
        stored_filename=stored,
        content_text=text,
        owner_id=user.id,
        status="pending",
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return _brief(contract, db)


@router.post("/{contract_id}/review", response_model=ContractDetail)
def review_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = db.get(Contract, contract_id)
    if not c or not _can_view(user, c):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "合同不存在或无权访问")
    report = contract_agents.review(c.content_text, c.name)
    c.status = "reviewed"
    c.reviewer_id = None
    c.score = report["score"]
    c.verdict = report["verdict"]
    c.dimensions = report["dimensions"]
    c.agent_report = report
    c.optimization = report["optimization"]
    c.lawyer_comment = None
    db.commit()
    db.refresh(c)
    return _detail(c, db)


def _detail(c: Contract, db: Session) -> dict:
    base = _brief(c, db)
    base.update(
        {
            "content_text": c.content_text,
            "dimensions": c.dimensions,
            "agent_report": c.agent_report,
            "optimization": c.optimization,
            "lawyer_comment": c.lawyer_comment,
        }
    )
    return base


@router.get("/list")
def list_contracts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Contract).order_by(Contract.id.desc())
    if user.role in ("super_admin", "lawyer"):
        items = q.all()
    else:
        items = q.filter(Contract.owner_id == user.id).all()
    return [_brief(c, db) for c in items]


@router.get("/{contract_id}", response_model=ContractDetail)
def get_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = db.get(Contract, contract_id)
    if not c or not _can_view(user, c):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "合同不存在或无权访问")
    return _detail(c, db)


@router.delete("/{contract_id}")
def delete_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = db.get(Contract, contract_id)
    if not c or not _can_view(user, c):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "合同不存在或无权访问")
    if user.role != "super_admin" and c.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "只有合同所有者与超级管理员可以删除审查结果")
    db.delete(c)
    db.commit()
    return {"detail": "已删除"}


@router.put("/{contract_id}/lawyer-review", response_model=ContractDetail)
def lawyer_review(
    contract_id: int,
    payload: LawyerReviewIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "lawyer":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "仅律师可以执行人工复核")
    c = db.get(Contract, contract_id)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "合同不存在")
    if payload.verdict not in VERDICTS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "verdict 取值非法")
    if c.status == "pending":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "请先完成智能体自动审查")
    c.verdict = payload.verdict
    c.score = payload.score
    c.reviewer_id = user.id
    c.lawyer_comment = payload.comment
    c.status = "lawyer_reviewed"
    db.commit()
    db.refresh(c)
    return _detail(c, db)