"""Shared RAG helpers, validation, and fallback retrieval."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import time
from pathlib import Path

from pawpal.ai.vectorstore import retrieve_chunks
from pawpal.logging_utils import get_logger

logger = get_logger("pawpal.ai.rag_utils")


@dataclass(frozen=True)
class KnowledgeSnippet:
    text: str
    source: str
    score: float


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _chunk_markdown_paragraphs(text: str, chunk_size: int = 500) -> list[str]:
    pieces: list[str] = []
    for paragraph in re.split(r"\n\s*\n", text):
        normalized = " ".join(paragraph.split()).strip()
        if not normalized:
            continue
        if len(normalized) <= chunk_size:
            pieces.append(normalized)
            continue
        start = 0
        while start < len(normalized):
            end = min(start + chunk_size, len(normalized))
            pieces.append(normalized[start:end].strip())
            if end == len(normalized):
                break
            start = end
    return pieces


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 1}


def _local_knowledge_fallback(query: str, top_k: int) -> list[KnowledgeSnippet]:
    knowledge_dir = _project_root() / "knowledge"
    if not knowledge_dir.exists():
        return []
    query_tokens = _tokenize(query)
    scored: list[KnowledgeSnippet] = []
    for file_path in sorted(knowledge_dir.glob("*.md")):
        content = file_path.read_text(encoding="utf-8")
        for piece in _chunk_markdown_paragraphs(content):
            tokens = _tokenize(piece)
            if not tokens:
                continue
            overlap = len(query_tokens & tokens)
            score = overlap / max(len(query_tokens), 1)
            if score <= 0:
                continue
            scored.append(KnowledgeSnippet(text=piece, source=file_path.as_posix(), score=score))
    scored.sort(key=lambda row: row.score, reverse=True)
    return scored[:top_k]


def retrieve_knowledge(query: str, top_k: int = 4) -> tuple[list[KnowledgeSnippet], bool, str]:
    """
    Retrieve knowledge snippets.

    Returns:
      (snippets, used_vectorstore, note)
    """
    try:
        chunks = retrieve_chunks(query, top_k=top_k)
        return (
            [KnowledgeSnippet(text=chunk.text, source=chunk.source, score=chunk.score) for chunk in chunks],
            True,
            "",
        )
    except Exception as error:  # pragma: no cover - fallback guard
        logger.warning("Vector retrieval unavailable, using local fallback: %s", error)
        fallback_rows = _local_knowledge_fallback(query, top_k=top_k)
        note = "Vector retrieval unavailable; using local lexical fallback."
        return fallback_rows, False, note


def normalize_priority(value: str) -> str:
    cleaned = (value or "").strip().lower()
    if cleaned in {"high", "medium", "low"}:
        return cleaned
    return "medium"


def normalize_recurrence(value: str) -> str:
    cleaned = (value or "").strip().lower()
    if cleaned in {"none", "daily", "weekly"}:
        return cleaned
    return "none"


def parse_time_safe(value: str | None) -> time | None:
    if not value:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    return time.fromisoformat(candidate)


def sanitize_duration(value: int | str, default: int = 15, minimum: int = 1, maximum: int = 240) -> int:
    try:
        duration = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, duration))
