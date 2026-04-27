"""Agentic plan explanation grounded in current scheduler output."""

from __future__ import annotations

import json
from typing import Any

from pawpal.ai.client import call_with_retries, get_openai_client
from pawpal.config import load_settings
from pawpal.logging_utils import get_logger, truncate_text
from pawpal.system import CareTask, Owner

logger = get_logger("pawpal.ai.plan_explainer")


def _serialize_task(task: CareTask) -> dict[str, Any]:
    return {
        "pet": task.pet_name or "unknown",
        "title": task.title,
        "start_time": task.start_time.strftime("%H:%M") if task.start_time else "Anytime",
        "duration_minutes": task.duration_minutes,
        "priority": task.priority,
        "recurrence": task.recurrence,
    }


def _tool_data(owner: Owner, plan: list[CareTask], scheduler_stub: str) -> dict[str, Any]:
    return {
        "plan_summary": [_serialize_task(task) for task in plan],
        "pet_profiles": [
            {
                "name": pet.name,
                "species": pet.species,
                "breed": pet.breed,
                "age": pet.age,
                "habits": pet.habits,
            }
            for pet in owner.pets
        ],
        "owner_constraints": {
            "available_minutes_per_day": owner.available_minutes_per_day,
            "preferences": owner.preferences,
        },
        "scheduler_explanation_stub": scheduler_stub,
    }


def explain_plan_with_agent(owner: Owner, plan: list[CareTask], scheduler_stub: str) -> str:
    if not plan:
        return scheduler_stub
    settings = load_settings()
    if not settings.openai_api_key:
        return scheduler_stub

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_plan_summary",
                "description": "Get the current generated plan as structured rows.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_pet_profiles",
                "description": "Get species, breed, age, and habits for all pets.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_owner_constraints",
                "description": "Get owner time budget and preference text.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_scheduler_explanation_stub",
                "description": "Get deterministic scheduler explanation string.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
    ]
    tool_data = _tool_data(owner=owner, plan=plan, scheduler_stub=scheduler_stub)

    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are a pet care planning assistant. Call tools before answering. "
                "Then explain why the plan is reasonable in plain language using owner constraints "
                "and pet profile details including species, breed, age, and habits when provided."
            ),
        },
        {"role": "user", "content": "Explain this plan and how it matches pet profiles and owner constraints."},
    ]
    client = get_openai_client()
    max_turns = 4

    for turn in range(max_turns):
        logger.info("Plan explainer turn %s", turn + 1)

        def _request() -> Any:
            return client.chat.completions.create(
                model=settings.openai_model,
                temperature=0.2,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=500,
            )

        response = call_with_retries(_request)
        message = response.choices[0].message
        tool_calls = message.tool_calls or []
        if not tool_calls:
            content = message.content or ""
            logger.info("Plan explainer completed with %s chars", len(content))
            return content.strip() or scheduler_stub

        messages.append(
            {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in tool_calls
                ],
            }
        )
        for tc in tool_calls:
            name = tc.function.name
            result = tool_data.get(name.replace("get_", ""), tool_data.get(name))
            if result is None:
                result = {"error": f"Unknown tool: {name}"}
            payload = json.dumps(result)
            logger.info("Tool %s returned: %s", name, truncate_text(payload))
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": payload})

    logger.warning("Plan explainer reached max turns; falling back.")
    return scheduler_stub

