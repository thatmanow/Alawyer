from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import Consultation, User
from app.schemas import ChatAnswerOut, ChatAskIn
from app.services.ollama_client import ollama
from app.services.rag import rag_service
from app.services.redis_cache import cache_service

router = APIRouter(prefix="/api/chat", tags=["AI问答"])

RAG_SYSTEM = (
    "你是 alawyer 智能法律顾问平台的专业法律顾问AI，具有深厚的中国法学功底。"
    "请仅依据下面提供的知识库参考资料回答用户问题，观点须有依据，并在引用处标注[1][2]等来源编号。"
    "回答使用 Markdown 格式组织（可用小标题、列表、加粗），语言严谨专业。"
    "若参考资料不足以完整回答，请明确说明并补充一般性法律常识，最后提醒'本回答仅供参考，具体请咨询执业律师'。"
)

DIRECT_SYSTEM = (
    "你是 alawyer 智能法律顾问平台的专业法律顾问AI。知识库中暂无与该问题直接相关的资料，"
    "请你依据中国现行法律体系的一般原则独立作答。"
    "回答使用 Markdown 格式组织（可用小标题、列表、加粗），语言严谨专业，"
    "最后提醒'本回答仅供参考，具体请咨询执业律师'。"
)


@router.post("/ask", response_model=ChatAnswerOut)
def ask(payload: ChatAskIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    question = payload.question.strip()

    history = [
        {"role": t.role, "content": t.content}
        for t in (payload.history or [])[-8:]
    ]

    import hashlib

    cache_key = question
    if history:
        ctx_digest = hashlib.sha1(
            "|".join(f"{t['role']}:{t['content'][:200]}" for t in history).encode("utf-8")
        ).hexdigest()[:12]
        cache_key = f"{question}#ctx{ctx_digest}"

    cached = cache_service.get_answer(cache_key)
    if cached and cached.get("answer"):
        record = Consultation(
            user_id=user.id,
            question=question,
            answer=cached["answer"],
            sources=cached.get("sources", []),
            used_rag=cached.get("used_rag", "rag"),
            from_cache="yes",
        )
        db.add(record)
        db.commit()
        return ChatAnswerOut(
            answer=cached["answer"],
            sources=cached.get("sources", []),
            used_rag=cached.get("used_rag", "rag"),
            from_cache="yes",
            meta=cached.get("meta", {}),
        )

    chunks, meta = rag_service.retrieve(question)
    if chunks:
        context = rag_service.build_context(chunks)
        user_content = f"知识库参考资料：\n\n{context}\n\n用户问题：{question}"
        system_prompt = RAG_SYSTEM
        used_rag = "rag"
    else:
        user_content = question
        system_prompt = DIRECT_SYSTEM
        used_rag = "direct"

    try:
        chat_messages = [{"role": "system", "content": system_prompt}]
        if history:
            chat_messages.append(
                {
                    "role": "user",
                    "content": "以下是你与用户此前的对话记录，供理解上下文使用：\n"
                    + "\n".join(
                        f"{'用户' if t['role'] == 'user' else '顾问'}：{t['content'][:1500]}" for t in history
                    ),
                }
            )
        chat_messages.append({"role": "user", "content": user_content})
        answer = ollama.chat(chat_messages, temperature=0.6)
    except Exception as e:
        answer = (
            "## 服务暂时不可用\n\n很抱歉，本地大模型服务暂时无法响应"
            f"（{type(e).__name__}）。请确认 Ollama 服务已启动后重试。"
        )

    sources = [
        {
            "doc_id": c["doc_id"],
            "doc_name": c["doc_name"],
            "snippet": c["text"][:160],
            "score": c.get("score", 0),
        }
        for c in chunks
    ]

    record = Consultation(
        user_id=user.id,
        question=question,
        answer=answer,
        sources=sources,
        used_rag=used_rag,
        from_cache="no",
    )
    db.add(record)
    db.commit()

    payload_cache = {
        "answer": answer,
        "sources": sources,
        "used_rag": used_rag,
        "meta": meta,
    }
    cache_service.set_answer(cache_key, payload_cache)

    return ChatAnswerOut(answer=answer, sources=sources, used_rag=used_rag, from_cache="no", meta=meta)


@router.get("/history")
def history(limit: int = 50, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    limit = max(1, min(limit, 200))
    records = (
        db.query(Consultation)
        .filter(Consultation.user_id == user.id)
        .order_by(Consultation.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "question": r.question,
            "answer": r.answer,
            "sources": r.sources or [],
            "used_rag": r.used_rag,
            "from_cache": r.from_cache,
            "created_at": r.created_at,
        }
        for r in records
    ]