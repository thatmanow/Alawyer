from app.config import settings
from app.services.chroma_store import chroma_store
from app.services.embedding import embedding_service
from app.services.rerank import rerank_service


class RagService:
    def retrieve(self, question: str, top_k: int = None) -> tuple:
        """返回 (chunks, meta)。chunks: [{doc_id, doc_name, text, score}]"""
        top_k = top_k or settings.RAG_TOP_K
        query_vec, embedder = embedding_service.embed_query(question)
        try:
            candidates = chroma_store.query(query_vec, top_k=max(top_k * 2, 8))
        except Exception:
            candidates = []
        if not candidates:
            return [], {"embedder": embedder, "reranker": "none"}

        docs = [c["text"] for c in candidates]
        ranked, reranker = rerank_service.rerank(question, docs, top_n=settings.RERANK_TOP_N)
        threshold = settings.RERANK_SCORE_THRESHOLD
        if reranker == "none":
            ranked = [
                {"index": i, "score": max(0.0, 1.0 - c["distance"])}
                for i, c in enumerate(candidates[:top_k])
            ]
            threshold = 0.25
        chunks = []
        for item in ranked:
            idx = item["index"]
            if 0 <= idx < len(candidates) and item["score"] >= threshold:
                c = dict(candidates[idx])
                c["score"] = round(item["score"], 4)
                chunks.append(c)
        meta = {"embedder": embedder, "reranker": reranker}
        return chunks, meta

    @staticmethod
    def build_context(chunks: list) -> str:
        parts = []
        for i, c in enumerate(chunks, 1):
            parts.append(f"[{i}] 来源：《{c['doc_name']}》\n{c['text']}")
        return "\n\n".join(parts)


rag_service = RagService()