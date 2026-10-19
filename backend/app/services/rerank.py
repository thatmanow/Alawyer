import re

from app.config import settings
from app.services.ollama_client import ollama


class RerankService:
    """Cross-Encoder 批量精排（单次 HTTP 请求），服务不可用时降级为 LLM 逐条打分。"""

    def rerank(self, query: str, documents: list, top_n: int = None) -> tuple:
        if not documents:
            return [], "none"
        top_n = top_n or settings.RERANK_TOP_N
        try:
            import httpx

            with httpx.Client(timeout=60) as client:
                r = client.post(
                    f"{settings.RERANK_BASE_URL}/rerank",
                    json={"query": query, "documents": documents, "top_n": top_n},
                )
                r.raise_for_status()
                results = r.json().get("results", [])
            ranked = [
                {"index": item["index"], "score": float(item.get("score", 0.0))}
                for item in results
            ]
            ranked.sort(key=lambda x: -x["score"])
            return ranked[:top_n], "cross-encoder"
        except Exception:
            pass
        return self._llm_rerank(query, documents, top_n)

    def _llm_rerank(self, query: str, documents: list, top_n: int) -> tuple:
        scored = []
        try:
            for i, doc in enumerate(documents):
                prompt = (
                    "你是文档相关性评估器。给定用户问题和候选文档片段，"
                    "请评估该文档对回答问题的相关性，只输出一个0到100的整数分数，不要输出其他任何内容。\n"
                    f"问题：{query}\n文档片段：{doc[:400]}\n相关性分数："
                )
                answer = ollama.chat(
                    [{"role": "user", "content": prompt}], temperature=0.0, timeout=60
                )
                m = re.search(r"\d{1,3}", answer)
                score = int(m.group(0)) if m else 0
                scored.append({"index": i, "score": min(score, 100) / 100.0})
            scored.sort(key=lambda x: -x["score"])
            return scored[:top_n], "llm"
        except Exception:
            return [{"index": i, "score": 0.0} for i in range(min(len(documents), top_n))], "none"


rerank_service = RerankService()