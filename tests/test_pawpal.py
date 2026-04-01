from pawpal_system import CareTask, Pet


def test_mark_complete_updates_task_status() -> None:
    task = CareTask(title="Evening Feed", duration_minutes=15, priority="high")

    task.mark_complete()

    assert task.is_completed is True


def test_add_task_increases_pet_task_count() -> None:
    pet = Pet(name="Mochi", species="dog", age=3)
    starting_count = len(pet.tasks)

    pet.add_task(CareTask(title="Walk", duration_minutes=20, priority="medium"))

    assert len(pet.tasks) == starting_count + 1
