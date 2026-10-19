import json
import re

import httpx

from app.config import settings


class OllamaClient:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self._client = httpx.Client(timeout=httpx.Timeout(settings.LLM_TIMEOUT, connect=5))

    def healthy(self) -> bool:
        try:
            r = self._client.get(f"{self.base_url}/api/tags", timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def chat(self, messages: list, model: str = None, temperature: float = 0.6, timeout: int = None,
             json_mode: bool = False, num_predict: int = None) -> str:
        payload = {
            "model": model or settings.LLM_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if json_mode:
            payload["format"] = "json"
        if num_predict:
            payload["options"]["num_predict"] = num_predict
        r = self._client.post(f"{self.base_url}/api/chat", json=payload, timeout=timeout or settings.LLM_TIMEOUT)
        r.raise_for_status()
        return (r.json().get("message") or {}).get("content", "").strip()

    def chat_json(self, messages: list, model: str = None, temperature: float = 0.2, timeout: int = None):
        text = self.chat(messages, model=model, temperature=temperature, timeout=timeout, json_mode=True)
        parsed = extract_json(text)
        if parsed is None:
            retry = self.chat(
                [
                    {"role": "system", "content": "你是格式转换器。把给定的内容改写为严格的JSON对象，不要输出任何解释、注释或代码块标记。"},
                    {"role": "user", "content": text[:2000] + '\n请输出：{"opinion": "...", "score": 0-100整数, "points": ["..."]}'},
                ],
                temperature=0.1,
                timeout=timeout,
                json_mode=True,
            )
            parsed = extract_json(retry)
        return parsed

    def embed(self, texts: list, model: str = None) -> list:
        payload = {"model": model or settings.EMBED_MODEL, "input": texts}
        r = self._client.post(f"{self.base_url}/api/embed", json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        embeddings = data.get("embeddings")
        if not embeddings:
            raise ValueError("Ollama 嵌入接口返回为空")
        return embeddings


def extract_json(text: str):
    text = (text or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        try:
            return json.loads(fence.group(1).strip())
        except Exception:
            pass
    for pattern in (r"\{[\s\S]*\}", r"\[[\s\S]*\]"):
        m = re.search(pattern, text)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                continue
    return None


ollama = OllamaClient()