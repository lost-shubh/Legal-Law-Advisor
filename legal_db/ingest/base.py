from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Mapping

import httpx

from legal_db.config import settings


@dataclass(frozen=True)
class FetchResult:
    url: str
    status_code: int
    content: bytes
    headers: Mapping[str, str]

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")


class PoliteFetcher:
    def __init__(
        self,
        delay_seconds: int | None = None,
        timeout_seconds: int = 30,
        user_agent: str | None = None,
    ) -> None:
        self.delay_seconds = settings.scrape_delay_seconds if delay_seconds is None else delay_seconds
        self.timeout_seconds = timeout_seconds
        self._last_fetch_at: float | None = None
        self._client = httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": user_agent or settings.scrape_user_agent},
        )

    def get(self, url: str) -> FetchResult:
        if self._last_fetch_at is not None:
            elapsed = time.monotonic() - self._last_fetch_at
            if elapsed < self.delay_seconds:
                time.sleep(self.delay_seconds - elapsed)
        response = self._client.get(url)
        self._last_fetch_at = time.monotonic()
        return FetchResult(
            url=str(response.url),
            status_code=response.status_code,
            content=response.content,
            headers=response.headers,
        )

