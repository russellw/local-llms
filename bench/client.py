"""Minimal client for an OpenAI-compatible chat endpoint (llama-server, ollama, ...).

Stdlib only, on purpose: this repo should run on a bare machine with no pip install.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict


@dataclass
class Completion:
    """One model response plus whatever performance data the server exposed."""

    text: str
    wall_s: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    # llama.cpp reports its own timings; other servers do not.
    prompt_per_s: float | None = None
    predict_per_s: float | None = None
    stop_reason: str | None = None
    error: str | None = None
    raw: dict = field(default_factory=dict, repr=False)

    @property
    def tok_per_s(self) -> float:
        """Generation speed, preferring the server's own number over wall clock."""
        if self.predict_per_s:
            return self.predict_per_s
        return self.completion_tokens / self.wall_s if self.wall_s else 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("raw")
        d["tok_per_s"] = round(self.tok_per_s, 3)
        return d


class ChatClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        model: str = "local",
        api_key: str = "none",
        timeout: float = 3600.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def _post(self, path: str, payload: dict) -> dict:
        req = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode())

    def health(self) -> bool:
        try:
            with urllib.request.urlopen(self.base_url + "/v1/models", timeout=10):
                return True
        except Exception:
            return False

    def chat(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        seed: int = 0,
    ) -> Completion:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "seed": seed,
            "stream": False,
        }

        t0 = time.monotonic()
        try:
            data = self._post("/v1/chat/completions", payload)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:500]
            return Completion("", time.monotonic() - t0, error=f"HTTP {e.code}: {body}")
        except Exception as e:
            return Completion("", time.monotonic() - t0, error=f"{type(e).__name__}: {e}")
        wall = time.monotonic() - t0

        choice = (data.get("choices") or [{}])[0]
        usage = data.get("usage") or {}
        timings = data.get("timings") or {}

        return Completion(
            text=(choice.get("message") or {}).get("content") or "",
            wall_s=wall,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            prompt_per_s=timings.get("prompt_per_second"),
            predict_per_s=timings.get("predicted_per_second"),
            stop_reason=choice.get("finish_reason"),
            raw=data,
        )
