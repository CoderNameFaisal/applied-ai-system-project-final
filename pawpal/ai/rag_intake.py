"""RAG-backed natural language intake that mutates domain state."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import time
from typing import Any

from pawpal.ai.client import call_with_retries, get_openai_client
from pawpal.ai.vectorstore import RetrievedChunk, retrieve_chunks
from pawpal.config import load_settings
from pawpal.logging_utils import get_logger, truncate_text
from pawpal.system import CareTask, Owner

logger = get_logger("pawpal.ai.rag_intake")


@dataclass
class IntakeResult:
    applied_actions: list[str]
    citations: list[str]
    explanation: str


def _owner_snapshot(owner: Owner) -> dict[str, Any]:
    return {
        "owner_name": owner.name,
        "preferences": owner.preferences,
        "available_minutes_per_day": owner.available_minutes_per_day,
        "pets": [
            {
                "name": pet.name,
                "species": pet.species,
                "breed": pet.breed,
                "age": pet.age,
                "habits": pet.habits,
                "tasks": [task.title for task in pet.tasks],
            }
            for pet in owner.pets
        ],
    }


def _find_pet(owner: Owner, pet_name: str):
    target = pet_name.strip().lower()
    for pet in owner.pets:
        if pet.name.strip().lower() == target:
            return pet
    raise ValueError(f"Could not find pet '{pet_name}'.")


def _parse_time_value(value: str | None) -> time | None:
    if not value:
        return None
    return time.fromisoformat(value)


def apply_rag_intake(owner: Owner, user_prompt: str) -> IntakeResult:
    settings = load_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for RAG intake.")
    if not user_prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    context_query = f"{user_prompt}\n\nOwner and pet state:\n{json.dumps(_owner_snapshot(owner), ensure_ascii=True)}"
    chunks = retrieve_chunks(context_query)
    citations = sorted({chunk.source for chunk in chunks})
    knowledge = "\n\n".join(
        f"[{index + 1}] ({chunk.source}) {chunk.text}" for index, chunk in enumerate(chunks)
    )

    schema_instruction = (
        'Return JSON with keys: "explanation", "actions". '
        'actions is a list of objects with "type" and fields. Supported actions: '
        '"set_owner_preferences" with {"preferences"}, '
        '"add_task" with {"pet_name","title","duration_minutes","priority","recurrence","start_time"}. '
        'Only produce actions grounded in retrieved knowledge.'
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You convert user requests into safe scheduling actions. "
                "Use retrieved knowledge and current owner snapshot. "
                f"{schema_instruction}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"User request:\n{user_prompt}\n\nOwner snapshot:\n{json.dumps(_owner_snapshot(owner))}\n\n"
                f"Retrieved knowledge:\n{knowledge}"
            ),
        },
    ]
    client = get_openai_client()

    def _request() -> Any:
        return client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            temperature=0,
            max_tokens=700,
            response_format={"type": "json_object"},
        )

    response = call_with_retries(_request)
    text = response.choices[0].message.content or "{}"
    logger.info("RAG intake response: %s", truncate_text(text))
    payload = json.loads(text)
    actions = payload.get("actions", [])
    explanation = str(payload.get("explanation", "")).strip()
    if not isinstance(actions, list):
        raise ValueError("Model returned invalid actions format.")

    applied_actions: list[str] = []
    for action in actions:
        action_type = str(action.get("type", "")).strip()
        if action_type == "set_owner_preferences":
            preferences = str(action.get("preferences", "")).strip()
            owner.set_preferences(preferences)
            applied_actions.append("set_owner_preferences")
            continue
        if action_type == "add_task":
            pet = _find_pet(owner, str(action.get("pet_name", "")))
            task = CareTask(
                title=str(action.get("title", "")).strip(),
                duration_minutes=int(action.get("duration_minutes", 0)),
                priority=str(action.get("priority", "medium")).strip().lower(),
                recurrence=str(action.get("recurrence", "none")).strip().lower(),
                start_time=_parse_time_value(action.get("start_time")),
            )
            pet.add_task(task)
            applied_actions.append(f"add_task:{pet.name}:{task.title}")
            continue
        logger.warning("Skipped unsupported action type: %s", action_type)

    return IntakeResult(
        applied_actions=applied_actions,
        citations=citations,
        explanation=explanation or "Applied RAG-backed updates to owner and task data.",
    )

