from __future__ import annotations

import hashlib
from typing import Iterable

from legal_db.config import settings


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


def embed_texts_openai(texts: Iterable[str], model: str | None = None) -> list[list[float]]:
    from openai import OpenAI

    selected_model = model or settings.openai_embedding_model
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.embeddings.create(model=selected_model, input=list(texts))
    return [item.embedding for item in response.data]


def vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"


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
