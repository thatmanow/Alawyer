from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=6, max_length=64)
    nickname: Optional[str] = Field(default=None, max_length=32)


class LoginIn(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    nickname: str
    role: str
    avatar: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserUpdateIn(BaseModel):
    nickname: Optional[str] = Field(default=None, max_length=32)
    avatar: Optional[str] = None


class PasswordChangeIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=64)


class StatusIn(BaseModel):
    status: str  # online / offline / invisible


class RoleIn(BaseModel):
    role: str  # super_admin / lawyer / user


class ChatTurnIn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=8000)


class ChatAskIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[ChatTurnIn] = Field(default_factory=list)


class SourceOut(BaseModel):
    doc_id: int
    doc_name: str
    snippet: str
    score: float


class ChatAnswerOut(BaseModel):
    answer: str
    sources: List[SourceOut]
    used_rag: str
    from_cache: str
    meta: dict = Field(default_factory=dict)


class ContractBrief(BaseModel):
    id: int
    name: str
    status: str
    score: Optional[float]
    verdict: Optional[str]
    owner_id: int
    owner_name: Optional[str] = None
    reviewer_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ContractDetail(ContractBrief):
    content_text: Optional[str] = None
    dimensions: Optional[dict] = None
    agent_report: Optional[dict] = None
    optimization: Optional[str] = None
    lawyer_comment: Optional[str] = None


class LawyerReviewIn(BaseModel):
    verdict: str  # compliant / needs_revision / non_compliant
    score: float = Field(ge=0, le=100)
    comment: str = ""


class KbDocOut(BaseModel):
    id: int
    name: str
    file_type: str
    file_size: int
    domain: str
    chunk_count: int
    uploader_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DashboardOut(BaseModel):
    server_time: datetime
    today_consultations: int
    contract_reviewed: int
    kb_docs: int
    total_users: int
    online_users: int
    domain_distribution: List[dict]
    consultation_trend: List[dict]
    graph: dict
    services: dict