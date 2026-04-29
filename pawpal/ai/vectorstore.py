"""Persistent Chroma-backed RAG store for PawPal knowledge."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import chromadb
from chromadb.api.models.Collection import Collection

from pawpal.ai.client import call_with_retries, get_openai_client
from pawpal.config import load_settings
from pawpal.logging_utils import get_logger

logger = get_logger("pawpal.ai.vectorstore")


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    source: str
    score: float


def _embed_texts(texts: list[str]) -> list[list[float]]:
    settings = load_settings()
    client = get_openai_client()

    def _request() -> list[list[float]]:
        response = client.embeddings.create(model=settings.ai_embedding_model, input=texts)
        return [row.embedding for row in response.data]

    return call_with_retries(_request)


def _get_collection() -> Collection:
    settings = load_settings()
    Path(settings.rag_db_path).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=settings.rag_db_path)
    return client.get_or_create_collection(name=settings.rag_collection_name, metadata={"hnsw:space": "cosine"})


def upsert_chunks(chunks: Iterable[dict[str, str]]) -> int:
    chunk_list = list(chunks)
    if not chunk_list:
        return 0
    collection = _get_collection()
    ids = [chunk["id"] for chunk in chunk_list]
    docs = [chunk["text"] for chunk in chunk_list]
    metadatas = [{"source": chunk["source"]} for chunk in chunk_list]
    embeddings = _embed_texts(docs)
    collection.upsert(ids=ids, documents=docs, embeddings=embeddings, metadatas=metadatas)
    logger.info("Upserted %s chunks into %s", len(chunk_list), collection.name)
    return len(chunk_list)


def retrieve_chunks(query: str, top_k: int | None = None) -> list[RetrievedChunk]:
    settings = load_settings()
    collection = _get_collection()
    query_embedding = _embed_texts([query])[0]
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k or settings.rag_top_k,
        include=["documents", "metadatas", "distances"],
    )
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]
    chunks: list[RetrievedChunk] = []
    for text, metadata, distance in zip(documents, metadatas, distances):
        source = (metadata or {}).get("source", "unknown")
        chunks.append(RetrievedChunk(text=text, source=source, score=float(distance)))
    logger.info("Retrieved %s chunks for query", len(chunks))
    return chunks

