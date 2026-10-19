import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import SessionLocal, init_db
from app.models import KbDocument, User
from app.routers import auth, chat, contracts, dashboard, knowledge, users
from app.services.neo4j_service import neo4j_service
from app.services.chroma_store import chroma_store
from app.services.embedding import embedding_service
from app.services.ollama_client import ollama
from app.services.redis_cache import cache_service
from app.utils import chunk_text, classify_domain, extract_keywords, hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("alawyer")

SEED_USERS = [
    ("admin", "admin123", "超级管理员", "super_admin"),
    ("lawyer01", "lawyer123", "张律师", "lawyer"),
    ("user01", "user123", "王先生", "user"),
]


def seed_users():
    with SessionLocal() as db:
        if db.query(User).count() > 0:
            return
        for username, password, nickname, role in SEED_USERS:
            db.add(
                User(
                    username=username,
                    password_hash=hash_password(password),
                    nickname=nickname,
                    role=role,
                    status="offline",
                )
            )
        db.commit()
        logger.info("已初始化内置账户: admin/admin123, lawyer01/lawyer123, user01/user123")


def seed_knowledge_base():
    with SessionLocal() as db:
        if db.query(KbDocument).count() > 0:
            _rebuild_neo4j(db)
            return
        seed_dir = Path(settings.SEED_DIR)
        if not seed_dir.exists():
            return
        files = sorted(p for p in seed_dir.glob("*.md") if p.is_file())
        for path in files:
            text = path.read_text(encoding="utf-8").strip()
            if len(text) < 50:
                continue
            name = path.stem
            domain = classify_domain(text)
            keywords = extract_keywords(text, limit=8) or [domain]
            chunks = chunk_text(text)
            vectors, mode = embedding_service.embed_texts(chunks)
            doc = KbDocument(
                name=name,
                stored_filename=path.name,
                file_type="md",
                file_size=path.stat().st_size,
                content_text=text[:200000],
                domain=domain,
                chunk_count=len(chunks),
                keywords=keywords,
                uploader_id=None,
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            chroma_store.add_document(doc.id, doc.name, chunks, vectors)
            logger.info(
                "种子文档已导入: %s (领域: %s, 分块: %d, 向量: %s)", name, domain, len(chunks), mode
            )
        _rebuild_neo4j(db)


def _rebuild_neo4j(db):
    if not neo4j_service.available():
        logger.warning("Neo4j 不可用，跳过知识图谱构建")
        return
    docs = db.query(KbDocument).all()
    if not docs:
        return
    neo4j_service.build_from_documents(
        [
            {"id": d.id, "name": d.name, "domain": d.domain, "keywords": d.keywords or []}
            for d in docs
        ]
    )
    logger.info("Neo4j 知识图谱已构建: %d 个文档节点", len(docs))


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_users()
    logger.info(
        "服务状态: ollama=%s rerank探测=运行时 redis=%s neo4j=%s chroma_chunks=%d",
        ollama.healthy(),
        cache_service.available,
        neo4j_service.available(),
        chroma_store.count(),
    )
    seed_knowledge_base()
    yield


app = FastAPI(title="alawyer 智能法律顾问平台", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(chat.router)
app.include_router(contracts.router)
app.include_router(knowledge.router)
app.include_router(users.router)

uploads_dir = Path(settings.UPLOAD_DIR)
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


@app.get("/api/health")
def health():
    return {
        "app": settings.APP_NAME,
        "status": "ok",
        "services": {
            "mysql": True,
            "redis": cache_service.available,
            "neo4j": neo4j_service.available(),
            "ollama": ollama.healthy(),
            "chroma": chroma_store.count(),
        },
    }


frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    from fastapi.responses import FileResponse

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        if full_path:
            target = (frontend_dist / full_path).resolve()
            if target.is_file() and frontend_dist.resolve() in target.parents:
                return FileResponse(target)
        return FileResponse(frontend_dist / "index.html")

    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
    logger.info("已挂载前端静态资源: %s", frontend_dist)