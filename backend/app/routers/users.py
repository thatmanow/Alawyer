import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user, require_super_admin
from app.models import User
from app.schemas import PasswordChangeIn, RoleIn, StatusIn, UserOut, UserUpdateIn
from app.utils import hash_password, verify_password

router = APIRouter(prefix="/api/users", tags=["个人设置"])

VALID_STATUSES = {"online", "offline", "invisible"}
VALID_ROLES = {"super_admin", "lawyer", "user"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.put("/me", response_model=UserOut)
def update_me(
    payload: UserUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.nickname is not None:
        user.nickname = payload.nickname.strip() or user.nickname
    if payload.avatar is not None:
        user.avatar = payload.avatar
    db.commit()
    db.refresh(user)
    return user


@router.put("/me/password", response_model=UserOut)
def change_password(
    payload: PasswordChangeIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "原密码错误")
    if payload.old_password == payload.new_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "新密码不能与原密码相同")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    db.refresh(user)
    return user


@router.put("/me/status", response_model=UserOut)
def update_status(
    payload: StatusIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "status 取值非法")
    user.status = payload.status
    db.commit()
    db.refresh(user)
    return user


@router.post("/me/avatar")
def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = file.file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "头像文件过大（限制 5MB）")
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "png"
    if ext not in {"png", "jpg", "jpeg", "gif", "webp", "svg"}:
        ext = "png"
    avatar_dir = Path(settings.UPLOAD_DIR) / "avatars"
    avatar_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex[:12]}.{ext}"
    (avatar_dir / filename).write_bytes(data)
    user.avatar = f"/uploads/avatars/{filename}"
    db.commit()
    return {"avatar": user.avatar}


@router.get("/list")
def list_users(
    block: str = "user",
    page: int = 1,
    page_size: int = 8,
    search: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(require_super_admin),
):
    if block not in VALID_ROLES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "block 取值非法")
    q = db.query(User).filter(User.role == block)
    if search.strip():
        q = q.filter(User.username.like(f"%{search.strip()}%"))
    total = q.count()
    page = max(1, page)
    page_size = max(1, min(page_size, 50))
    items = q.order_by(User.id).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "block": block,
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": u.id,
                "username": u.username,
                "nickname": u.nickname,
                "role": u.role,
                "avatar": u.avatar,
                "status": u.status,
                "created_at": u.created_at,
            }
            for u in items
        ],
    }


@router.put("/{user_id}/role", response_model=UserOut)
def update_role(
    user_id: int,
    payload: RoleIn,
    db: Session = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    if payload.role not in VALID_ROLES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "role 取值非法")
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")
    if target.id == admin.id and payload.role != "super_admin":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "不能降级自己的管理员权限")
    target.role = payload.role
    db.commit()
    db.refresh(target)
    return target