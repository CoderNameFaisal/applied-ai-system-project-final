from types import SimpleNamespace

from pawpal.ai.conflict_rag import apply_conflict_moves
from pawpal.ai.rag_intake import apply_rag_intake
from pawpal.ai.rag_schedule_validator import validate_schedule_with_rag
from pawpal.ai.rag_task_suggestions import SuggestedTask, apply_suggested_tasks, suggest_tasks_with_rag
from pawpal.ai.rag_tips import get_care_tips
from pawpal.system import CareTask, Owner, Pet


def _mock_chat_completion(json_payload: str):
    message = SimpleNamespace(content=json_payload)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


def test_rag_intake_applies_add_task_and_preferences(monkeypatch) -> None:
    owner = Owner(name="Jordan", available_minutes_per_day=90)
    owner.add_pet(Pet(name="Mochi", species="dog", breed="corgi", age=3))

    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        "pawpal.ai.rag_intake.retrieve_chunks",
        lambda _: [SimpleNamespace(text="Dogs benefit from consistent walks.", source="knowledge/care_basics.md")],
    )

    completion = _mock_chat_completion(
        '{"explanation":"Applied grounded updates.","actions":['
        '{"type":"set_owner_preferences","preferences":"Morning walks first"},'
        '{"type":"add_task","pet_name":"Mochi","title":"Evening walk","duration_minutes":15,'
        '"priority":"high","recurrence":"daily","start_time":"18:00"}]}'
    )
    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_: completion)))
    monkeypatch.setattr("pawpal.ai.rag_intake.get_openai_client", lambda: fake_client)

    result = apply_rag_intake(owner, "Add daily evening walk and update preferences.")

    assert owner.preferences == "Morning walks first"
    assert any(task.title == "Evening walk" for task in owner.pets[0].tasks)
    assert result.applied_actions
    assert "knowledge/care_basics.md" in result.citations


def test_apply_conflict_moves_updates_matching_tasks() -> None:
    owner = Owner(name="Jordan", available_minutes_per_day=90)
    pet = Pet(name="Mochi", species="dog", breed="corgi", age=3)
    task = CareTask(title="Breakfast", duration_minutes=15, priority="high", start_time="08:00")
    pet.add_task(task)
    owner.add_pet(pet)

    applied = apply_conflict_moves(
        owner,
        [{"pet_name": "Mochi", "task_title": "Breakfast", "new_start_time": "07:45"}],
    )

    assert applied == ["Mochi:Breakfast->07:45"]
    assert task.start_time is not None
    assert task.start_time.strftime("%H:%M") == "07:45"


def test_get_care_tips_uses_retrieval(monkeypatch) -> None:
    owner = Owner(name="Jordan", available_minutes_per_day=90)
    pet = Pet(name="Mochi", species="dog", breed="corgi", age=3)
    owner.add_pet(pet)

    calls = {"count": 0}

    def _mock_retrieve(*_args, **_kwargs):
        calls["count"] += 1
        rows = [
            SimpleNamespace(text="Walk daily.", source="knowledge/care_basics.md", score=0.9),
            SimpleNamespace(text="Keep routines consistent.", source="knowledge/profile_adjustments.md", score=0.7),
        ]
        return (rows, False, "fallback")

    monkeypatch.setattr(
        "pawpal.ai.rag_tips.retrieve_knowledge",
        _mock_retrieve,
    )

    result = get_care_tips(owner, pet, top_k=1)

    assert len(result.tips) == 1
    assert "corgi" in result.tips[0].text.lower()
    assert "age 3" in result.tips[0].text.lower()
    assert "walk daily." in result.tips[0].text.lower()
    assert calls["count"] == 3
    assert result.note == "fallback"


def test_suggest_tasks_with_rag_fallback_without_api_key(monkeypatch) -> None:
    owner = Owner(name="Jordan", available_minutes_per_day=90)
    pet = Pet(name="Mochi", species="dog", breed="corgi", age=3)
    owner.add_pet(pet)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(
        "pawpal.ai.rag_task_suggestions.retrieve_knowledge",
        lambda *_args, **_kwargs: (
            [SimpleNamespace(text="Use short training sessions.", source="knowledge/dog_training.md", score=0.8)],
            False,
            "fallback",
        ),
    )

    result = suggest_tasks_with_rag(owner, pet, top_k=1)

    assert result.used_llm is False
    assert result.suggestions
    assert "knowledge/dog_training.md" in result.citations


def test_apply_suggested_tasks_applies_and_skips_duplicates() -> None:
    pet = Pet(name="Mochi", species="dog", breed="corgi", age=3)
    pet.add_task(CareTask(title="Morning walk", duration_minutes=20, priority="high"))
    suggestions = [
        SuggestedTask(
            title="Morning walk",
            duration_minutes=25,
            priority="high",
            recurrence="daily",
            start_time="08:00",
            rationale="duplicate",
            confidence=0.7,
        ),
        SuggestedTask(
            title="Evening enrichment",
            duration_minutes=15,
            priority="medium",
            recurrence="daily",
            start_time="18:30",
            rationale="new",
            confidence=0.7,
        ),
    ]

    applied, skipped = apply_suggested_tasks(pet, suggestions)

    assert applied == ["Evening enrichment"]
    assert skipped == ["Morning walk"]


def test_validate_schedule_with_rag_fallback(monkeypatch) -> None:
    owner = Owner(name="Jordan", available_minutes_per_day=90)
    pet = Pet(name="Mochi", species="dog", breed="corgi", age=3)
    task = CareTask(title="Morning walk", duration_minutes=20, priority="high", start_time="08:00")
    pet.add_task(task)
    owner.add_pet(pet)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(
        "pawpal.ai.rag_schedule_validator.retrieve_knowledge",
        lambda *_args, **_kwargs: (
            [SimpleNamespace(text="Keep routines consistent.", source="knowledge/care_basics.md", score=0.7)],
            False,
            "fallback",
        ),
    )

    result = validate_schedule_with_rag(owner, [task], top_k=1)

    assert result.used_llm is False
    assert result.reliability_score >= 0
    assert "knowledge/care_basics.md" in result.citations
