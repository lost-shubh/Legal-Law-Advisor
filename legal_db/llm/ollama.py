from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

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
    fallback_models: str = os.getenv("OLLAMA_FALLBACK_MODELS", "llama3.2:1b")
    timeout_seconds: int = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "300"))
    max_answer_tokens: int = int(os.getenv("OLLAMA_MAX_ANSWER_TOKENS", "350"))
    context_window: int = int(os.getenv("OLLAMA_CONTEXT_WINDOW", "4096"))
    num_thread: int = int(os.getenv("OLLAMA_NUM_THREAD", "0"))


@dataclass(frozen=True)
class OllamaModelStatus:
    configured_model: str
    selected_model: str | None
    installed_models: list[str]
    available: bool
    base_url: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "configured_model": self.configured_model,
            "selected_model": self.selected_model,
            "installed_models": self.installed_models,
            "available": self.available,
            "base_url": self.base_url,
        }


class OllamaChatClient:
    def __init__(self, settings: OllamaSettings | None = None) -> None:
        self.settings = settings or OllamaSettings()

    def list_models(self) -> list[str]:
        response = requests.get(
            f"{self.settings.base_url.rstrip('/')}/api/tags",
            timeout=min(self.settings.timeout_seconds, 30),
        )
        response.raise_for_status()
        data = response.json()
        return [item.get("name", "") for item in data.get("models", []) if item.get("name")]

    def resolve_model(self) -> str:
        installed = self.list_models()
        candidates = [
            self.settings.model,
            *[item.strip() for item in self.settings.fallback_models.split(",") if item.strip()],
        ]
        for candidate in candidates:
            if candidate in installed:
                return candidate
        raise RuntimeError(
            "No configured Ollama model is installed. "
            f"Configured candidates: {candidates}. Installed models: {installed}."
        )

    def status(self) -> OllamaModelStatus:
        try:
            installed = self.list_models()
        except Exception:
            return OllamaModelStatus(
                configured_model=self.settings.model,
                selected_model=None,
                installed_models=[],
                available=False,
                base_url=self.settings.base_url,
            )
        selected = None
        for candidate in [
            self.settings.model,
            *[item.strip() for item in self.settings.fallback_models.split(",") if item.strip()],
        ]:
            if candidate in installed:
                selected = candidate
                break
        return OllamaModelStatus(
            configured_model=self.settings.model,
            selected_model=selected,
            installed_models=installed,
            available=selected is not None,
            base_url=self.settings.base_url,
        )

    def chat(
        self,
        question: str,
        context: str = "",
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        model: str | None = None,
    ) -> str:
        selected_model = model or self.resolve_model()
        options: dict[str, int | float] = {
            "num_predict": self.settings.max_answer_tokens,
            "num_ctx": self.settings.context_window,
            "temperature": 0.2,
            "top_p": 0.9,
        }
        if self.settings.num_thread > 0:
            options["num_thread"] = self.settings.num_thread
        context_text = context.strip()
        user_content = (
            "CONTEXT:\n"
            f"{context_text}\n\n"
            f"QUESTION:\n{question}"
            if context_text
            else f"QUESTION:\n{question}"
        )
        response = requests.post(
            f"{self.settings.base_url.rstrip('/')}/api/chat",
            json={
                "model": selected_model,
                "stream": False,
                "keep_alive": "30m",
                "options": options,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
            },
            timeout=self.settings.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "")
