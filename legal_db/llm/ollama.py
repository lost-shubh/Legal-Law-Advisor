from __future__ import annotations

import os
from dataclasses import dataclass

import requests


DEFAULT_SYSTEM_PROMPT = """You are an Indian legal information assistant.
Use only the provided context when answering legal questions.
Do not pretend to be a lawyer. Do not give final legal advice.
Always tell the user that an advocate should verify before filing or taking action.
If the context is insufficient, say what information is missing."""


@dataclass(frozen=True)
class OllamaSettings:
    base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    timeout_seconds: int = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "300"))
    max_answer_tokens: int = int(os.getenv("OLLAMA_MAX_ANSWER_TOKENS", "350"))


class OllamaChatClient:
    def __init__(self, settings: OllamaSettings | None = None) -> None:
        self.settings = settings or OllamaSettings()

    def chat(self, question: str, context: str = "", system_prompt: str = DEFAULT_SYSTEM_PROMPT) -> str:
        response = requests.post(
            f"{self.settings.base_url.rstrip('/')}/api/chat",
            json={
                "model": self.settings.model,
                "stream": False,
                "options": {
                    "num_predict": self.settings.max_answer_tokens,
                    "temperature": 0.2,
                    "top_p": 0.9,
                },
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            "CONTEXT:\n"
                            f"{context.strip() or 'No retrieved context was provided.'}\n\n"
                            f"QUESTION:\n{question}"
                        ),
                    },
                ],
            },
            timeout=self.settings.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "")
