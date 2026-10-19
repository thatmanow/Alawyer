import hashlib
import math
import re

from app.config import settings
from app.services.ollama_client import ollama


class EmbeddingService:
    """bge-large-zh-v1.5 (1024维) 语义向量；Ollama 不可用时回退到本地哈希向量。"""

    def __init__(self):
        self.dim = settings.EMBED_DIM

    def embed_texts(self, texts: list) -> tuple:
        try:
            vectors = ollama.embed(texts)
            if vectors and len(vectors) == len(texts):
                return vectors, "ollama:bge-large-zh-v1.5"
        except Exception:
            pass
        return [self.hash_embed(t) for t in texts], "local-hash"

    def embed_query(self, text: str) -> tuple:
        vecs, mode = self.embed_texts([text])
        return vecs[0], mode

    def hash_embed(self, text: str) -> list:
        vec = [0.0] * self.dim

        def _add(token: str, weight: float):
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 64) % 2 == 0 else -1.0
            vec[idx] += sign * weight

        tokens = re.findall(r"[\u4e00-\u9fff]{2,6}|[A-Za-z]{2,12}|\d{1,8}", text)
        bigrams = []
        for t in tokens:
            if re.match(r"^[\u4e00-\u9fff]+$", t):
                bigrams.extend(t[i : i + 2] for i in range(len(t) - 1))
            else:
                bigrams.append(t.lower())
        if not bigrams:
            bigrams = ["empty"]
        for bg in bigrams:
            _add(bg, 1.0)
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


embedding_service = EmbeddingService()