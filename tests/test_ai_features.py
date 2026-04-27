from types import SimpleNamespace

from pawpal.ai.conflict_rag import apply_conflict_moves
from pawpal.ai.rag_intake import apply_rag_intake
from pawpal.system import CareTask, Owner, Pet


def _mock_chat_completion(json_payload: str):
    message = SimpleNamespace(content=json_payload)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


def test_rag_intake_applies_add_task_and_preferences(monkeypatch) -> None:
    owner = Owner(name="Jordan", available_minutes_per_day=90)
    owner.add_pet(Pet(name="Mochi", species="dog", breed="corgi", age=3))

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
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
