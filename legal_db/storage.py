from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from legal_db.config import settings


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_key(prefix: str, content_hash: str, suffix: str) -> str:
    clean_prefix = prefix.strip("/").replace("\\", "/")
    return f"{clean_prefix}/{content_hash[:2]}/{content_hash}.{suffix.lstrip('.')}"


@dataclass(frozen=True)
class StoredObject:
    key: str
    content_hash: str
    byte_size: int
    local_path: Path | None = None


class LocalObjectStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or settings.local_storage_root

    def put_bytes(self, key: str, data: bytes) -> StoredObject:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return StoredObject(
            key=key,
            content_hash=sha256_bytes(data),
            byte_size=len(data),
            local_path=path,
        )

    def get_bytes(self, key: str) -> bytes:
        return (self.root / key).read_bytes()


def default_store() -> LocalObjectStore:
    # S3/R2 can be added behind the same interface once credentials are final.
    return LocalObjectStore()

