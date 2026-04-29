"""RAG-backed task suggestions with safe fallback and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pawpal.ai.client import call_with_retries, get_openai_client
from pawpal.ai.rag_utils import (
    normalize_priority,
    normalize_recurrence,
    parse_time_safe,
    retrieve_knowledge,
    sanitize_duration,
)
from pawpal.config import load_settings
from pawpal.logging_utils import get_logger, truncate_text
from pawpal.system import CareTask, Owner, Pet

logger = get_logger("pawpal.ai.rag_task_suggestions")


@dataclass(frozen=True)
class SuggestedTask:
    title: str
    duration_minutes: int
    priority: str
    recurrence: str
    start_time: str | None
    rationale: str
    confidence: float


@dataclass(frozen=True)
class TaskSuggestionResult:
    suggestions: list[SuggestedTask]
    citations: list[str]
    used_llm: bool
    note: str


def _sanitize_confidence(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.6
    return max(0.0, min(1.0, score))


def _validate_title(title: Any) -> str:
    cleaned = str(title or "").strip()
    return cleaned[:80]


def _from_payload(rows: list[dict[str, Any]]) -> list[SuggestedTask]:
    suggestions: list[SuggestedTask] = []
    for row in rows:
        title = _validate_title(row.get("title"))
        if not title:
            continue
        start_time = str(row.get("start_time", "")).strip() or None
        if start_time is not None:
            try:
                parse_time_safe(start_time)
            except ValueError:
                start_time = None
        suggestions.append(
            SuggestedTask(
                title=title,
                duration_minutes=sanitize_duration(row.get("duration_minutes", 15)),
                priority=normalize_priority(str(row.get("priority", "medium"))),
                recurrence=normalize_recurrence(str(row.get("recurrence", "daily"))),
                start_time=start_time,
                rationale=str(row.get("rationale", "")).strip()[:220],
                confidence=_sanitize_confidence(row.get("confidence")),
            )
        )
    return suggestions


def _fallback_suggestions(owner: Owner, pet: Pet, top_k: int = 4) -> TaskSuggestionResult:
    query = (
        f"Suggest practical tasks for {pet.species} {pet.breed} age {pet.age}. "
        f"Owner preferences: {owner.preferences or 'none'}."
    )
    snippets, _, note = retrieve_knowledge(query, top_k=top_k)
    suggestions: list[SuggestedTask] = []
    for idx, snippet in enumerate(snippets):
        title = f"Care review from knowledge #{idx + 1}"
        suggestions.append(
            SuggestedTask(
                title=title,
                duration_minutes=15,
                priority="medium",
                recurrence="daily",
                start_time=None,
                rationale=snippet.text[:180],
                confidence=0.45,
            )
        )
    if not suggestions:
        suggestions = [
            SuggestedTask(
                title="Daily wellbeing check",
                duration_minutes=10,
                priority="medium",
                recurrence="daily",
                start_time=None,
                rationale="Fallback suggestion because no retrieval snippets were available.",
                confidence=0.35,
            )
        ]
    return TaskSuggestionResult(
        suggestions=suggestions,
        citations=sorted({row.source for row in snippets}),
        used_llm=False,
        note=note or "Using retrieval fallback suggestions.",
    )


def suggest_tasks_with_rag(owner: Owner, pet: Pet, top_k: int = 4) -> TaskSuggestionResult:
    query = (
        f"Pet task suggestions for species={pet.species}, breed={pet.breed}, age={pet.age}. "
        f"Owner preferences: {owner.preferences or 'none'}."
    )
    snippets, _, retrieval_note = retrieve_knowledge(query, top_k=top_k)
    citations = sorted({row.source for row in snippets})
    settings = load_settings()
    if not settings.ai_api_key:
        result = _fallback_suggestions(owner, pet, top_k=top_k)
        return TaskSuggestionResult(
            suggestions=result.suggestions,
            citations=sorted(set(citations + result.citations)),
            used_llm=False,
            note="LLM unavailable (no API key). " + (retrieval_note or result.note),
        )

    knowledge = "\n\n".join(
        f"[{idx + 1}] ({row.source}) {row.text}" for idx, row in enumerate(snippets)
    )
    client = get_openai_client()
    messages = [
        {
            "role": "system",
            "content": (
                "You create safe pet-care task suggestions. "
                'Return JSON with key "suggestions", which is a list of objects with keys: '
                '"title","duration_minutes","priority","recurrence","start_time","rationale","confidence". '
                "Use HH:MM for start_time when provided. Keep confidence between 0 and 1."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Owner: {owner.name}\nPreferences: {owner.preferences}\n"
                f"Pet: {pet.name}, {pet.species}, {pet.breed}, age {pet.age}\n\nKnowledge:\n{knowledge}"
            ),
        },
    ]

    def _request() -> Any:
        return client.chat.completions.create(
            model=settings.ai_model,
            messages=messages,
            temperature=0.2,
            max_tokens=600,
            response_format={"type": "json_object"},
        )

    try:
        response = call_with_retries(_request)
        text = response.choices[0].message.content or "{}"
        logger.info("Task suggestion response: %s", truncate_text(text))
        payload = json.loads(text)
        rows = payload.get("suggestions", [])
        if not isinstance(rows, list):
            rows = []
        suggestions = _from_payload(rows)
        if not suggestions:
            fallback = _fallback_suggestions(owner, pet, top_k=top_k)
            return TaskSuggestionResult(
                suggestions=fallback.suggestions,
                citations=sorted(set(citations + fallback.citations)),
                used_llm=False,
                note="LLM returned no valid suggestions; fallback used.",
            )
        return TaskSuggestionResult(
            suggestions=suggestions,
            citations=citations,
            used_llm=True,
            note=retrieval_note,
        )
    except Exception as error:  # pragma: no cover - defensive fallback
        logger.warning("Task suggestion fallback triggered: %s", error)
        fallback = _fallback_suggestions(owner, pet, top_k=top_k)
        return TaskSuggestionResult(
            suggestions=fallback.suggestions,
            citations=sorted(set(citations + fallback.citations)),
            used_llm=False,
            note=f"LLM unavailable; fallback used. {retrieval_note or ''}".strip(),
        )


def apply_suggested_tasks(pet: Pet, suggestions: list[SuggestedTask]) -> tuple[list[str], list[str]]:
    existing_titles = {task.title.strip().lower() for task in pet.tasks}
    applied: list[str] = []
    skipped: list[str] = []
    for suggestion in suggestions:
        normalized_title = suggestion.title.strip().lower()
        if not normalized_title or normalized_title in existing_titles:
            skipped.append(suggestion.title)
            continue
        task = CareTask(
            title=suggestion.title,
            duration_minutes=suggestion.duration_minutes,
            priority=suggestion.priority,
            recurrence=suggestion.recurrence,
            start_time=parse_time_safe(suggestion.start_time),
        )
        pet.add_task(task)
        existing_titles.add(normalized_title)
        applied.append(suggestion.title)
    return applied, skipped
