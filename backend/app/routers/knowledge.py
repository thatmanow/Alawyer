import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user, require_lawyer_or_admin
from app.models import KbDocument, User
from app.schemas import KbDocOut
from app.services.neo4j_service import neo4j_service
from app.services.chroma_store import chroma_store
from app.services.embedding import embedding_service
from app.services.ollama_client import ollama
from app.utils import (
    chunk_text,
    classify_domain,
    extract_keywords,
    parse_uploaded_file,
    sanitize_filename,
)

router = APIRouter(prefix="/api/kb", tags=["知识库"])

ALLOWED_EXTS = {"txt", "md", "markdown", "pdf", "docx", "doc", "xlsx", "csv", "json", "html"}


def _doc_out(d: KbDocument, db: Session) -> dict:
    uploader = db.get(User, d.uploader_id) if d.uploader_id else None
    return {
        "id": d.id,
        "name": d.name,
        "file_type": d.file_type,
        "file_size": d.file_size,
        "domain": d.domain,
        "chunk_count": d.chunk_count,
        "uploader_name": uploader.nickname if uploader else None,
        "created_at": d.created_at,
        "updated_at": d.updated_at,
    }


def _auto_name(text: str, filename: str) -> str:
    try:
        answer = ollama.chat(
            [
                {
                    "role": "system",
                    "content": "你是一个文档命名助手。请为法律文档起一个简洁准确的中文标题，直接输出标题本身，不要任何解释、引号或标点，不超过18个字。",
                },
                {"role": "user", "content": f"文档开头内容：\n{text[:600]}\n\n请为该文档命名："},
            ],
            temperature=0.3,
            timeout=60,
        )
        name = answer.strip().strip('"“”').replace("\n", " ")
        name = sanitize_filename(name)
        if 2 <= len(name) <= 24:
            return name
    except Exception:
        pass
    first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    if 2 <= len(first_line) <= 24:
        return sanitize_filename(first_line)
    stem = Path(filename).stem or "法律文档"
    return sanitize_filename(stem)[:24] or "法律文档"


def _smart_keywords(text: str) -> list:
    base = extract_keywords(text, limit=6)
    if len(base) >= 4:
        return base
    try:
        answer = ollama.chat(
            [
                {
                    "role": "system",
                    "content": "你是法律文本实体抽取器。从文本中提取4到8个关键法律实体或术语，只输出一个JSON字符串数组，如 [\"劳动合同\",\"试用期\"]，不要输出其他内容。",
                },
                {"role": "user", "content": text[:1500]},
            ],
            temperature=0.2,
            timeout=60,
        )
        data = None
        import json as _json
        import re as _re

        try:
            data = _json.loads(answer)
        except Exception:
            m = _re.search(r"\[[\s\S]*\]", answer)
            if m:
                try:
                    data = _json.loads(m.group(0))
                except Exception:
                    data = None
        if isinstance(data, list):
            extra = [str(x).strip() for x in data if 1 < len(str(x).strip()) <= 12][:8]
            merged = list(dict.fromkeys(base + extra))
            return merged[:8]
    except Exception:
        pass
    return base or ["法律文档"]


@router.get("/list")
def list_docs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    docs = db.query(KbDocument).order_by(KbDocument.id.desc()).all()
    return [_doc_out(d, db) for d in docs]


@router.get("/{doc_id}/content")
def get_doc_content(doc_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    doc = db.get(KbDocument, doc_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "文档不存在")
    uploader = db.get(User, doc.uploader_id) if doc.uploader_id else None
    return {
        "id": doc.id,
        "name": doc.name,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "domain": doc.domain,
        "keywords": doc.keywords or [],
        "chunk_count": doc.chunk_count,
        "content": doc.content_text or "",
        "uploader_name": uploader.nickname if uploader else None,
        "created_at": doc.created_at,
        "updated_at": doc.updated_at,
    }


@router.post("/upload", response_model=KbDocOut)
def upload_doc(
    file: UploadFile = File(...),
    name: str = Form(default=""),
    db: Session = Depends(get_db),
    user: User = Depends(require_lawyer_or_admin),
):
    data = file.file.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "文件过大（限制 20MB）")
    filename = file.filename or "document.txt"
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"不支持的文件类型 .{ext}，支持: {'/'.join(sorted(ALLOWED_EXTS))}")

    file_type, text = parse_uploaded_file(filename, data)
    text = (text or "").strip()
    if len(text) < 20:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "无法解析出有效文本内容")

    doc_name = (name or "").strip()
    if not doc_name:
        doc_name = _auto_name(text, filename)
    else:
        doc_name = sanitize_filename(doc_name)[:60]

    domain = classify_domain(text)
    keywords = _smart_keywords(text)

    store_dir = Path(settings.UPLOAD_DIR) / "kb"
    store_dir.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid.uuid4().hex[:12]}_{sanitize_filename(filename)}"
    (store_dir / stored).write_bytes(data)

    chunks = chunk_text(text)
    vectors, _mode = embedding_service.embed_texts(chunks)

    doc = KbDocument(
        name=doc_name,
        stored_filename=stored,
        file_type=file_type,
        file_size=len(data),
        content_text=text[:200000],
        domain=domain,
        chunk_count=len(chunks),
        keywords=keywords,
        uploader_id=user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    chroma_store.add_document(doc.id, doc.name, chunks, vectors)
    if neo4j_service.available():
        neo4j_service.add_document(
            {"id": doc.id, "name": doc.name, "domain": domain, "keywords": keywords}
        )
    return _doc_out(doc, db)


@router.put("/{doc_id}")
def update_doc(
    doc_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_lawyer_or_admin),
):
    doc = db.get(KbDocument, doc_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "文档不存在")

    new_name = (payload.get("name") or "").strip()
    new_content = payload.get("content")
    if new_content is not None:
        new_content = str(new_content).strip()
        if len(new_content) < 20:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "文档内容过短（至少 20 字符）")

    if new_name:
        doc.name = sanitize_filename(new_name)[:60]

    if new_content is not None and new_content != (doc.content_text or ""):
        chunks = chunk_text(new_content)
        vectors, _mode = embedding_service.embed_texts(chunks)
        chroma_store.delete_document(doc.id)
        chroma_store.add_document(doc.id, doc.name, chunks, vectors)
        doc.content_text = new_content[:200000]
        doc.chunk_count = len(chunks)
        doc.domain = classify_domain(new_content)
        doc.keywords = _smart_keywords(new_content)
        if neo4j_service.available():
            neo4j_service.remove_document(doc.id)
            neo4j_service.add_document(
                {"id": doc.id, "name": doc.name, "domain": doc.domain, "keywords": doc.keywords}
            )

    from datetime import datetime

    doc.updated_at = datetime.now()
    db.commit()
    db.refresh(doc)
    return _doc_out(doc, db)


@router.delete("/{doc_id}")
def delete_doc(
    doc_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_lawyer_or_admin),
):
    doc = db.get(KbDocument, doc_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "文档不存在")
    chroma_store.delete_document(doc.id)
    if neo4j_service.available():
        neo4j_service.remove_document(doc.id)
    file_path = Path(settings.UPLOAD_DIR) / "kb" / doc.stored_filename
    if file_path.exists():
        try:
            file_path.unlink()
        except OSError:
            pass
    db.delete(doc)
    db.commit()
    return {"detail": "已删除"}