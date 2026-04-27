"""RAG-backed conflict resolution proposals and optional application."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pawpal.ai.client import call_with_retries, get_openai_client
from pawpal.ai.vectorstore import retrieve_chunks
from pawpal.config import load_settings
from pawpal.logging_utils import get_logger, truncate_text
from pawpal.system import CareTask, Owner

logger = get_logger("pawpal.ai.conflict_rag")


@dataclass
class ConflictSuggestion:
    moves: list[dict[str, str]]
    explanation: str
    citations: list[str]


def _task_window(task: CareTask) -> str:
    if not task.start_time:
        return "Anytime"
    return task.start_time.strftime("%H:%M")


def propose_conflict_resolution(owner: Owner, conflicts: list[tuple[CareTask, CareTask]]) -> ConflictSuggestion:
    settings = load_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for conflict RAG.")
    if not conflicts:
        return ConflictSuggestion(moves=[], explanation="No conflicts to resolve.", citations=[])

    conflict_rows = [
        {
            "first_pet": first.pet_name,
            "first_title": first.title,
            "first_start": _task_window(first),
            "second_pet": second.pet_name,
            "second_title": second.title,
            "second_start": _task_window(second),
        }
        for first, second in conflicts
    ]
    query = "Resolve pet schedule conflict based on priorities and pet profile: " + json.dumps(conflict_rows)
    chunks = retrieve_chunks(query)
    citations = sorted({chunk.source for chunk in chunks})
    knowledge = "\n\n".join(f"[{idx + 1}] ({chunk.source}) {chunk.text}" for idx, chunk in enumerate(chunks))

    client = get_openai_client()
    messages = [
        {
            "role": "system",
            "content": (
                "You propose safe time moves for overlapping pet tasks. "
                'Return JSON with keys "moves" and "explanation". '
                '"moves" is a list of {"pet_name","task_title","new_start_time"} in HH:MM format.'
            ),
        },
        {
            "role": "user",
            "content": f"Conflicts:\n{json.dumps(conflict_rows)}\n\nKnowledge:\n{knowledge}",
        },
    ]

    def _request() -> Any:
        return client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            temperature=0,
            max_tokens=500,
            response_format={"type": "json_object"},
        )

    response = call_with_retries(_request)
    content = response.choices[0].message.content or "{}"
    logger.info("Conflict RAG response: %s", truncate_text(content))
    payload = json.loads(content)
    moves = payload.get("moves", [])
    if not isinstance(moves, list):
        moves = []
    explanation = str(payload.get("explanation", "")).strip() or "Suggested conflict adjustments based on knowledge."
    return ConflictSuggestion(moves=moves, explanation=explanation, citations=citations)


def apply_conflict_moves(owner: Owner, moves: list[dict[str, str]]) -> list[str]:
    applied: list[str] = []
    for move in moves:
        pet_name = str(move.get("pet_name", "")).strip().lower()
        task_title = str(move.get("task_title", "")).strip().lower()
        new_start = str(move.get("new_start_time", "")).strip()
        if not pet_name or not task_title or not new_start:
            continue
        target_pet = next((pet for pet in owner.pets if pet.name.strip().lower() == pet_name), None)
        if target_pet is None:
            continue
        target_task = next((task for task in target_pet.tasks if task.title.strip().lower() == task_title), None)
        if target_task is None:
            continue
        target_task.set_start_time_str(new_start)
        applied.append(f"{target_pet.name}:{target_task.title}->{new_start}")
    return applied

