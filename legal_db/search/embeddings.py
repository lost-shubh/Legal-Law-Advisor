from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from legal_db.config import settings


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STAGING_DB_PATH = ROOT / "data" / "legal_corpus_staging.sqlite"
LOCAL_HASH_EMBEDDING_MODEL = "local-hash-embedding-v1"


def chunk_words(text_value: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    words = text_value.split()
    if not words:
        return []
    chunks: list[str] = []
    step = max(chunk_size - overlap, 1)
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks


def content_hash(text_value: str) -> str:
    return hashlib.sha256(text_value.encode("utf-8")).hexdigest()


def embedding_tokens(text_value: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9]{2,}", text_value.lower())


def normalize_vector(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def local_hash_embedding(text_value: str, dimensions: int = 128) -> list[float]:
    if dimensions <= 0:
        raise ValueError("dimensions must be positive")
    vector = [0.0] * dimensions
    for token in embedding_tokens(text_value):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign
    return normalize_vector(vector)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("vectors must have the same dimensions")
    return sum(a * b for a, b in zip(left, right, strict=True))


def embed_texts_openai(texts: Iterable[str], model: str | None = None) -> list[list[float]]:
    from openai import OpenAI

    selected_model = model or settings.openai_embedding_model
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.embeddings.create(model=selected_model, input=list(texts))
    return [item.embedding for item in response.data]


def vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"


@dataclass(frozen=True)
class StagingEmbeddingSummary:
    source_type: str
    source_rows: int
    chunks: int
    model_name: str
    dimensions: int

    def to_dict(self) -> dict[str, int | str]:
        return {
            "source_type": self.source_type,
            "source_rows": self.source_rows,
            "chunks": self.chunks,
            "model_name": self.model_name,
            "dimensions": self.dimensions,
        }


def ensure_staging_embedding_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS staging_embeddings (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          source_type TEXT NOT NULL,
          source_id INTEGER NOT NULL,
          chunk_index INTEGER NOT NULL DEFAULT 0,
          chunk_text TEXT NOT NULL,
          embedding_json TEXT NOT NULL,
          model_name TEXT NOT NULL,
          dimensions INTEGER NOT NULL,
          content_hash TEXT NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(source_type, source_id, chunk_index, model_name)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_staging_embeddings_source
        ON staging_embeddings(source_type, source_id)
        """
    )
    conn.commit()


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    return (
        conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()[0]
        > 0
    )


def build_staging_judgment_embeddings(
    db_path: str | Path = DEFAULT_STAGING_DB_PATH,
    *,
    dimensions: int = 128,
    model_name: str = LOCAL_HASH_EMBEDDING_MODEL,
    chunk_size: int = 450,
    overlap: int = 75,
    limit: int | None = None,
) -> StagingEmbeddingSummary:
    path = Path(db_path)
    if not path.exists():
        return StagingEmbeddingSummary("JUDGMENT_CHUNK", 0, 0, model_name, dimensions)
    conn = sqlite3.connect(path)
    try:
        required = ["judgments", "document_texts"]
        if not all(_table_exists(conn, table_name) for table_name in required):
            return StagingEmbeddingSummary("JUDGMENT_CHUNK", 0, 0, model_name, dimensions)
        ensure_staging_embedding_tables(conn)
        sql = """
            SELECT j.id, dt.clean_text
            FROM judgments j
            JOIN document_texts dt ON dt.source_document_id = j.source_document_id
            WHERE dt.clean_text IS NOT NULL
            ORDER BY j.id
        """
        if limit is not None:
            sql += " LIMIT ?"
            rows = conn.execute(sql, (max(limit, 0),)).fetchall()
        else:
            rows = conn.execute(sql).fetchall()

        chunk_count = 0
        for judgment_id, clean_text in rows:
            chunks = chunk_words(clean_text or "", chunk_size=chunk_size, overlap=overlap)
            for idx, chunk in enumerate(chunks):
                vector = local_hash_embedding(chunk, dimensions=dimensions)
                conn.execute(
                    """
                    INSERT INTO staging_embeddings
                    (source_type, source_id, chunk_index, chunk_text, embedding_json,
                     model_name, dimensions, content_hash)
                    VALUES ('JUDGMENT_CHUNK', ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_type, source_id, chunk_index, model_name)
                    DO UPDATE SET chunk_text = excluded.chunk_text,
                                  embedding_json = excluded.embedding_json,
                                  dimensions = excluded.dimensions,
                                  content_hash = excluded.content_hash
                    """,
                    (
                        judgment_id,
                        idx,
                        chunk,
                        json.dumps(vector),
                        model_name,
                        dimensions,
                        content_hash(chunk),
                    ),
                )
                chunk_count += 1
        conn.commit()
        return StagingEmbeddingSummary("JUDGMENT_CHUNK", len(rows), chunk_count, model_name, dimensions)
    finally:
        conn.close()


def store_embeddings(
    source_type: str,
    source_id: int,
    chunks: list[str],
    vectors: list[list[float]],
    model_name: str,
) -> None:
    from sqlalchemy import text

    from legal_db.db import session_scope

    if len(chunks) != len(vectors):
        raise ValueError("chunks and vectors length mismatch")
    with session_scope() as session:
        for idx, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
            session.execute(
                text(
                    """
                    INSERT INTO embeddings
                    (source_type, source_id, chunk_index, chunk_text, embedding, model_name, content_hash)
                    VALUES (:source_type, :source_id, :chunk_index, :chunk_text,
                            CAST(:embedding AS vector), :model_name, :content_hash)
                    ON CONFLICT (source_type, source_id, chunk_index, model_name)
                    DO UPDATE SET chunk_text = EXCLUDED.chunk_text,
                                  embedding = EXCLUDED.embedding,
                                  content_hash = EXCLUDED.content_hash
                    """
                ),
                {
                    "source_type": source_type,
                    "source_id": source_id,
                    "chunk_index": idx,
                    "chunk_text": chunk,
                    "embedding": vector_literal(vector),
                    "model_name": model_name,
                    "content_hash": content_hash(chunk),
                },
            )
