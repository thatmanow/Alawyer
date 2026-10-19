from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    nickname = Column(String(64), nullable=False)
    role = Column(String(20), nullable=False, default="user")  # super_admin / lawyer / user
    avatar = Column(String(255), default="")
    status = Column(String(20), default="offline")  # online / offline / invisible
    created_at = Column(DateTime, default=datetime.now)
    last_active_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class KbDocument(Base):
    __tablename__ = "kb_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_type = Column(String(20), default="txt")
    file_size = Column(Integer, default=0)
    content_text = Column(Text)
    domain = Column(String(50), default="综合法律", index=True)
    chunk_count = Column(Integer, default=0)
    keywords = Column(JSON, default=list)
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Consultation(Base):
    __tablename__ = "consultations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    sources = Column(JSON, default=list)
    used_rag = Column(String(10), default="rag")  # rag / direct
    from_cache = Column(String(10), default="no")  # yes / no
    created_at = Column(DateTime, default=datetime.now, index=True)


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    stored_filename = Column(String(255), default="")
    content_text = Column(Text)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), default="pending")  # pending / reviewed / lawyer_reviewed
    score = Column(Float, nullable=True)
    verdict = Column(String(30), nullable=True)  # compliant / needs_revision / non_compliant
    dimensions = Column(JSON, nullable=True)
    agent_report = Column(JSON, nullable=True)
    optimization = Column(Text, nullable=True)
    lawyer_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)