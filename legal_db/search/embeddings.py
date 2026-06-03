from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from legal_db.config import settings


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STAGING_DB_PATH = ROOT / "data" / "legal_corpus_staging.sqlite"
LOCAL_HASH_EMBEDDING_MODEL = "local-hash-embedding-v1"
PRODUCTION_EMBEDDING_DIMENSIONS = 1536


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


@dataclass(frozen=True)
class ProductionEmbeddingSummary:
    database_available: bool
    source_rows: dict[str, int]
    chunks: dict[str, int]
    model_name: str
    dimensions: int
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "database_available": self.database_available,
            "source_rows": self.source_rows,
            "chunks": self.chunks,
            "model_name": self.model_name,
            "dimensions": self.dimensions,
            "errors": self.errors,
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


def build_section_embedding_text(row: Any) -> str:
    return "\n".join(
        part
        for part in [
            row["act_name"],
            f"Section {row['section_number']}",
            row["section_title"],
            row["section_text"],
        ]
        if part
    )


def build_judgment_embedding_text(row: Any) -> str:
    title = " v. ".join(part for part in [row["petitioner"], row["respondent"]] if part)
    return "\n".join(
        part
        for part in [
            row["neutral_citation"],
            row["case_number"],
            title,
            str(row["judgment_date"]) if row["judgment_date"] else None,
            row["clean_text"],
        ]
        if part
    )


def build_book_embedding_text(row: Any) -> str:
    return "\n".join(
        part
        for part in [row["title"], row["chapter_title"], row["chunk_text"]]
        if part
    )


def _insert_production_embedding(
    conn: Any,
    *,
    source_type: str,
    source_id: int,
    chunk_index: int,
    chunk_text: str,
    model_name: str,
    model_version: str,
    dimensions: int,
) -> None:
    from sqlalchemy import text

    vector = local_hash_embedding(chunk_text, dimensions=dimensions)
    conn.execute(
        text(
            """
            INSERT INTO embeddings
            (source_type, source_id, chunk_index, chunk_text, embedding, model_name,
             model_version, content_hash)
            VALUES (:source_type, :source_id, :chunk_index, :chunk_text,
                    CAST(:embedding AS vector), :model_name, :model_version, :content_hash)
            ON CONFLICT (source_type, source_id, chunk_index, model_name)
            DO UPDATE SET chunk_text = EXCLUDED.chunk_text,
                          embedding = EXCLUDED.embedding,
                          model_version = EXCLUDED.model_version,
                          content_hash = EXCLUDED.content_hash
            """
        ),
        {
            "source_type": source_type,
            "source_id": source_id,
            "chunk_index": chunk_index,
            "chunk_text": chunk_text,
            "embedding": vector_literal(vector),
            "model_name": model_name,
            "model_version": model_version,
            "content_hash": content_hash(chunk_text),
        },
    )


def _delete_existing_embeddings(conn: Any, source_types: list[str], model_name: str) -> None:
    from sqlalchemy import bindparam, text

    statement = (
        text(
            """
            DELETE FROM embeddings
            WHERE model_name = :model_name
              AND source_type IN :source_types
            """
        )
        .bindparams(bindparam("source_types", expanding=True))
    )
    conn.execute(statement, {"model_name": model_name, "source_types": source_types})


def build_production_embeddings(
    *,
    database_url: str | None = None,
    source_types: list[str] | None = None,
    limit: int | None = None,
    replace: bool = False,
    dimensions: int = PRODUCTION_EMBEDDING_DIMENSIONS,
    model_name: str = LOCAL_HASH_EMBEDDING_MODEL,
    model_version: str | None = None,
    chunk_size: int = 450,
    overlap: int = 75,
) -> ProductionEmbeddingSummary:
    from sqlalchemy import text

    from legal_db.db import make_engine

    selected_types = source_types or ["SECTION", "JUDGMENT_CHUNK", "BOOK_CHUNK"]
    selected_types = [source_type.upper() for source_type in selected_types]
    model_version = model_version or f"{dimensions}d"
    source_rows = {source_type: 0 for source_type in selected_types}
    chunks = {source_type: 0 for source_type in selected_types}
    errors: list[str] = []

    try:
        engine = make_engine(database_url)
        with engine.begin() as conn:
            conn.execute(text("SELECT 1"))
            if replace:
                _delete_existing_embeddings(conn, selected_types, model_name)

            if "SECTION" in selected_types:
                sql = """
                    SELECT s.id, s.section_number, s.section_title, s.section_text, st.act_name
                    FROM sections s
                    JOIN statutes st ON st.id = s.statute_id
                    WHERE s.section_text IS NOT NULL
                    ORDER BY s.id
                """
                params: tuple[int, ...] = ()
                if limit is not None:
                    sql += " LIMIT :limit"
                rows = conn.execute(text(sql), {"limit": max(limit or 0, 0)} if limit is not None else {}).mappings()
                for row in rows:
                    source_rows["SECTION"] += 1
                    chunk_text = build_section_embedding_text(row)
                    _insert_production_embedding(
                        conn,
                        source_type="SECTION",
                        source_id=int(row["id"]),
                        chunk_index=0,
                        chunk_text=chunk_text,
                        model_name=model_name,
                        model_version=model_version,
                        dimensions=dimensions,
                    )
                    chunks["SECTION"] += 1

            if "JUDGMENT_CHUNK" in selected_types:
                sql = """
                    SELECT
                      j.id,
                      j.clean_text,
                      j.judgment_date,
                      c.case_number,
                      c.neutral_citation,
                      c.petitioner,
                      c.respondent
                    FROM judgments j
                    JOIN cases c ON c.id = j.case_id
                    WHERE j.clean_text IS NOT NULL
                    ORDER BY j.id
                """
                if limit is not None:
                    sql += " LIMIT :limit"
                rows = conn.execute(text(sql), {"limit": max(limit or 0, 0)} if limit is not None else {}).mappings()
                for row in rows:
                    source_rows["JUDGMENT_CHUNK"] += 1
                    text_value = build_judgment_embedding_text(row)
                    for idx, chunk_text in enumerate(
                        chunk_words(text_value, chunk_size=chunk_size, overlap=overlap)
                    ):
                        _insert_production_embedding(
                            conn,
                            source_type="JUDGMENT_CHUNK",
                            source_id=int(row["id"]),
                            chunk_index=idx,
                            chunk_text=chunk_text,
                            model_name=model_name,
                            model_version=model_version,
                            dimensions=dimensions,
                        )
                        chunks["JUDGMENT_CHUNK"] += 1

            if "BOOK_CHUNK" in selected_types:
                sql = """
                    SELECT bc.id, bc.chunk_text, b.title, ch.chapter_title
                    FROM book_chunks bc
                    JOIN legal_books b ON b.id = bc.book_id
                    LEFT JOIN book_chapters ch ON ch.id = bc.chapter_id
                    WHERE bc.chunk_text IS NOT NULL
                    ORDER BY bc.id
                """
                if limit is not None:
                    sql += " LIMIT :limit"
                rows = conn.execute(text(sql), {"limit": max(limit or 0, 0)} if limit is not None else {}).mappings()
                for row in rows:
                    source_rows["BOOK_CHUNK"] += 1
                    chunk_text = build_book_embedding_text(row)
                    _insert_production_embedding(
                        conn,
                        source_type="BOOK_CHUNK",
                        source_id=int(row["id"]),
                        chunk_index=0,
                        chunk_text=chunk_text,
                        model_name=model_name,
                        model_version=model_version,
                        dimensions=dimensions,
                    )
                    chunks["BOOK_CHUNK"] += 1
            conn.execute(text("ANALYZE embeddings"))
    except Exception as exc:
        errors.append(str(exc))
        return ProductionEmbeddingSummary(False, source_rows, chunks, model_name, dimensions, errors)

    return ProductionEmbeddingSummary(True, source_rows, chunks, model_name, dimensions, errors)
