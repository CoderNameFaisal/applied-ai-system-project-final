"""RAG-backed schedule validation with reliability scoring."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pawpal.ai.client import call_with_retries, get_openai_client
from pawpal.ai.rag_utils import retrieve_knowledge
from pawpal.config import load_settings
from pawpal.logging_utils import get_logger, truncate_text
from pawpal.system import CareTask, Owner

logger = get_logger("pawpal.ai.rag_schedule_validator")


@dataclass(frozen=True)
class ValidationFinding:
    severity: str
    category: str
    message: str
    source: str


@dataclass(frozen=True)
class ScheduleValidationResult:
    findings: list[ValidationFinding]
    reliability_score: int
    bias_flags: list[str]
    citations: list[str]
    used_llm: bool
    note: str


def _timed_minutes(task: CareTask) -> int | None:
    if task.start_time is None:
        return None
    return task.start_time.hour * 60 + task.start_time.minute


def _deterministic_findings(owner: Owner, plan: list[CareTask]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    if not plan:
        findings.append(
            ValidationFinding(
                severity="high",
                category="coverage",
                message="No tasks were scheduled for the current filters and constraints.",
                source="deterministic",
            )
        )
        return findings

    total_minutes = sum(task.duration_minutes for task in plan)
    if total_minutes < min(20, owner.available_minutes_per_day):
        findings.append(
            ValidationFinding(
                severity="medium",
                category="coverage",
                message="Scheduled time is very low; important care activities may be missing.",
                source="deterministic",
            )
        )

    timed = [task for task in plan if task.start_time is not None]
    timed = sorted(timed, key=lambda row: row.start_time)
    for previous, current in zip(timed, timed[1:]):
        prev_end = _timed_minutes(previous)
        cur_start = _timed_minutes(current)
        if prev_end is None or cur_start is None:
            continue
        prev_end += previous.duration_minutes
        gap = cur_start - prev_end
        if gap > 240:
            findings.append(
                ValidationFinding(
                    severity="low",
                    category="timing",
                    message=f"Large schedule gap detected between {previous.title} and {current.title}.",
                    source="deterministic",
                )
            )
    return findings


def _base_reliability(findings: list[ValidationFinding]) -> int:
    score = 88
    for row in findings:
        if row.severity == "high":
            score -= 20
        elif row.severity == "medium":
            score -= 10
        else:
            score -= 4
    return max(0, min(100, score))


def _llm_evaluate(owner: Owner, plan: list[CareTask], knowledge: str) -> tuple[list[ValidationFinding], list[str], int]:
    settings = load_settings()
    client = get_openai_client()
    plan_rows = [
        {
            "pet": task.pet_name or "Unknown",
            "title": task.title,
            "duration_minutes": task.duration_minutes,
            "priority": task.priority,
            "recurrence": task.recurrence,
            "start_time": task.start_time.strftime("%H:%M") if task.start_time else None,
        }
        for task in plan
    ]
    messages = [
        {
            "role": "system",
            "content": (
                "Evaluate pet schedule quality and fairness. "
                'Return JSON with keys: "findings","bias_flags","score_adjustment". '
                '"findings" entries: {"severity","category","message"}. '
                '"score_adjustment" is integer between -20 and +10.'
            ),
        },
        {
            "role": "user",
            "content": (
                f"Owner preferences: {owner.preferences}\nPlan: {json.dumps(plan_rows)}\n\nKnowledge:\n{knowledge}"
            ),
        },
    ]

    def _request() -> Any:
        return client.chat.completions.create(
            model=settings.ai_model,
            messages=messages,
            temperature=0,
            max_tokens=500,
            response_format={"type": "json_object"},
        )

    response = call_with_retries(_request)
    text = response.choices[0].message.content or "{}"
    logger.info("Schedule validator response: %s", truncate_text(text))
    payload = json.loads(text)

    findings_payload = payload.get("findings", [])
    llm_findings: list[ValidationFinding] = []
    if isinstance(findings_payload, list):
        for row in findings_payload:
            llm_findings.append(
                ValidationFinding(
                    severity=str(row.get("severity", "low")).strip().lower(),
                    category=str(row.get("category", "quality")).strip().lower(),
                    message=str(row.get("message", "")).strip()[:220],
                    source="llm",
                )
            )
    bias_flags_raw = payload.get("bias_flags", [])
    bias_flags = [str(row).strip() for row in bias_flags_raw] if isinstance(bias_flags_raw, list) else []
    try:
        score_adjustment = int(payload.get("score_adjustment", 0))
    except (TypeError, ValueError):
        score_adjustment = 0
    score_adjustment = max(-20, min(10, score_adjustment))
    return llm_findings, bias_flags, score_adjustment


def validate_schedule_with_rag(owner: Owner, plan: list[CareTask], top_k: int = 4) -> ScheduleValidationResult:
    query = (
        f"Validate pet schedule quality for owner preferences: {owner.preferences or 'none'}. "
        f"Tasks count: {len(plan)}."
    )
    snippets, _, retrieval_note = retrieve_knowledge(query, top_k=top_k)
    citations = sorted({row.source for row in snippets})
    deterministic = _deterministic_findings(owner, plan)
    base_score = _base_reliability(deterministic)
    knowledge = "\n\n".join(
        f"[{idx + 1}] ({row.source}) {row.text}" for idx, row in enumerate(snippets)
    )

    settings = load_settings()
    if not settings.ai_api_key:
        return ScheduleValidationResult(
            findings=deterministic,
            reliability_score=base_score,
            bias_flags=[],
            citations=citations,
            used_llm=False,
            note="LLM unavailable (no API key). " + retrieval_note,
        )

    try:
        llm_findings, bias_flags, adjustment = _llm_evaluate(owner, plan, knowledge)
        merged = deterministic + llm_findings
        return ScheduleValidationResult(
            findings=merged,
            reliability_score=max(0, min(100, base_score + adjustment)),
            bias_flags=bias_flags,
            citations=citations,
            used_llm=True,
            note=retrieval_note,
        )
    except Exception as error:  # pragma: no cover - defensive fallback
        logger.warning("Schedule validator fallback triggered: %s", error)
        return ScheduleValidationResult(
            findings=deterministic,
            reliability_score=base_score,
            bias_flags=[],
            citations=citations,
            used_llm=False,
            note=f"LLM unavailable; deterministic validation used. {retrieval_note}".strip(),
        )
