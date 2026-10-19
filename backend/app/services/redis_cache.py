import hashlib
import json

import redis as redis_lib

from app.config import settings


class CacheService:
    def __init__(self):
        self.r = None
        self.available = False
        try:
            self.r = redis_lib.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=5,
            )
            self.r.ping()
            self.available = True
        except Exception:
            self.r = None

    @staticmethod
    def make_key(question: str) -> str:
        normalized = "".join(question.split()).lower()
        return "alawyer:chat:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def get_answer(self, question: str):
        if not self.available:
            return None
        try:
            raw = self.r.get(self.make_key(question))
            return json.loads(raw) if raw else None
        except Exception:
            return None

    def set_answer(self, question: str, payload: dict):
        if not self.available:
            return
        try:
            self.r.set(self.make_key(question), json.dumps(payload, ensure_ascii=False), ex=settings.CHAT_CACHE_TTL)
        except Exception:
            pass


cache_service = CacheService()