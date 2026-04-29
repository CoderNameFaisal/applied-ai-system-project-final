from datetime import date, timedelta, time
from pawpal.ai.profile_scheduler import generate_profile_schedule_for_pet
from pawpal import CareTask, Owner, Pet, Scheduler


def test_mark_complete_updates_task_status() -> None:
    task = CareTask(title="Evening Feed", duration_minutes=15, priority="high")

    task.mark_complete()

    assert task.is_completed is True


def test_add_task_increases_pet_task_count() -> None:
    pet = Pet(name="Mochi", species="dog", breed="corgi", age=3)
    starting_count = len(pet.tasks)

    pet.add_task(CareTask(title="Walk", duration_minutes=20, priority="medium"))

    assert len(pet.tasks) == starting_count + 1


def test_sort_tasks_orders_by_start_time() -> None:
    scheduler = Scheduler()
    later_task = CareTask(
        title="Late Walk",
        duration_minutes=20,
        priority="high",
        start_time=time(10, 0),
    )
    earlier_task = CareTask(
        title="Breakfast",
        duration_minutes=10,
        priority="medium",
        start_time=time(8, 0),
    )
    anytime_task = CareTask(
        title="Training",
        duration_minutes=15,
        priority="high",
    )

    sorted_tasks = scheduler.sort_tasks([later_task, anytime_task, earlier_task])

    assert [task.title for task in sorted_tasks] == ["Breakfast", "Late Walk", "Training"]


def test_filter_tasks_by_pet_and_status() -> None:
    scheduler = Scheduler()
    owner = Owner(name="Jordan", available_minutes_per_day=120)
    dog = Pet(name="Mochi", species="dog", breed="shiba inu", age=3)
    cat = Pet(name="Luna", species="cat", breed="tabby", age=5)

    dog_task = CareTask(title="Walk", duration_minutes=20, priority="high")
    cat_task = CareTask(title="Feed Cat", duration_minutes=10, priority="medium")
    cat_task.mark_complete()

    dog.add_task(dog_task)
    cat.add_task(cat_task)
    owner.add_pet(dog)
    owner.add_pet(cat)

    filtered = scheduler.filter_tasks(owner.get_all_tasks(), pet_name="Luna", status="completed")

    assert [task.title for task in filtered] == ["Feed Cat"]


def test_expand_recurring_tasks_includes_daily_and_matching_weekly() -> None:
    scheduler = Scheduler()
    target_day = date.today()
    weekly_start_same_weekday = target_day - timedelta(days=7)

    daily = CareTask(
        title="Daily Med",
        duration_minutes=5,
        priority="high",
        recurrence="daily",
    )
    weekly = CareTask(
        title="Weekly Groom",
        duration_minutes=30,
        priority="medium",
        recurrence="weekly",
        start_date=weekly_start_same_weekday,
    )
    one_time_done = CareTask(
        title="One Time",
        duration_minutes=10,
        priority="low",
        recurrence="none",
    )
    one_time_done.mark_complete()

    expanded = scheduler.expand_recurring_tasks([daily, weekly, one_time_done], on_date=target_day)

    assert [task.title for task in expanded] == ["Daily Med", "Weekly Groom"]


def test_detect_conflicts_finds_overlapping_timed_tasks() -> None:
    scheduler = Scheduler()
    task_one = CareTask(
        title="Medication",
        duration_minutes=30,
        priority="high",
        start_time=time(9, 0),
    )
    task_two = CareTask(
        title="Vet Call",
        duration_minutes=15,
        priority="medium",
        start_time=time(9, 15),
    )
    task_three = CareTask(
        title="Lunch",
        duration_minutes=20,
        priority="low",
        start_time=time(10, 0),
    )

    conflicts = scheduler.detect_conflicts([task_one, task_two, task_three])

    assert len(conflicts) == 1
    assert conflicts[0][0].title == "Medication"
    assert conflicts[0][1].title == "Vet Call"


def test_mark_task_complete_creates_next_daily_instance() -> None:
    pet = Pet(name="Mochi", species="dog", breed="beagle", age=3)
    today = date.today()
    pet.add_task(
        CareTask(
            title="Daily Med",
            duration_minutes=5,
            priority="high",
            recurrence="daily",
            start_date=today,
            start_time=time(8, 0),
        )
    )

    next_task = pet.mark_task_complete("Daily Med", on_date=today)

    assert next_task is not None
    assert next_task.title == "Daily Med"
    assert next_task.start_date == today + timedelta(days=1)
    assert next_task.is_completed is False
    assert len(pet.tasks) == 2


def test_mark_task_complete_creates_next_weekly_instance() -> None:
    pet = Pet(name="Luna", species="cat", breed="siamese", age=5)
    today = date.today()
    pet.add_task(
        CareTask(
            title="Weekly Groom",
            duration_minutes=30,
            priority="medium",
            recurrence="weekly",
            start_date=today,
            start_time=time(9, 0),
        )
    )

    next_task = pet.mark_task_complete("Weekly Groom", on_date=today)

    assert next_task is not None
    assert next_task.title == "Weekly Groom"
    assert next_task.start_date == today + timedelta(days=7)
    assert next_task.is_completed is False
    assert len(pet.tasks) == 2


def test_generate_daily_plan_returns_empty_for_pet_with_no_tasks() -> None:
    scheduler = Scheduler()
    owner = Owner(name="Jordan", available_minutes_per_day=60)
    owner.add_pet(Pet(name="Mochi", species="dog", breed="labrador", age=3))

    plan = scheduler.generate_daily_plan(owner)

    assert plan == []


def test_detect_conflicts_flags_tasks_with_exact_same_start_time() -> None:
    scheduler = Scheduler()
    first = CareTask(
        title="Breakfast",
        duration_minutes=20,
        priority="high",
        start_time=time(8, 0),
    )
    second = CareTask(
        title="Medication",
        duration_minutes=10,
        priority="high",
        start_time=time(8, 0),
    )

    conflicts = scheduler.detect_conflicts([first, second])

    assert len(conflicts) == 1
    assert conflicts[0][0].title == "Breakfast"
    assert conflicts[0][1].title == "Medication"


def test_pet_requires_non_empty_breed() -> None:
    try:
        Pet(name="Mochi", species="dog", breed="  ", age=2)
        raise AssertionError("Expected ValueError for empty breed.")
    except ValueError as error:
        assert "breed" in str(error).lower()


def test_set_start_time_str_updates_and_clears_time() -> None:
    task = CareTask(title="Walk", duration_minutes=20, priority="high")
    task.set_start_time_str("08:15")
    assert task.start_time is not None
    assert task.start_time.strftime("%H:%M") == "08:15"
    task.set_start_time_str("")
    assert task.start_time is None


def test_generate_profile_schedule_for_dog_uses_profile_preferences() -> None:
    owner = Owner(name="Jordan", available_minutes_per_day=120)
    pet = Pet(
        name="Mochi",
        species="dog",
        breed="corgi",
        age=3,
        habits="Favorite toy: Rope\nFavorite food: Salmon kibble",
    )
    owner.add_pet(pet)

    added = generate_profile_schedule_for_pet(owner, pet)

    assert "Play session (Rope)" in added
    assert "Breakfast (Salmon kibble)" in added
    assert "Dinner (Salmon kibble)" in added
    assert any(task.title == "Morning walk" for task in pet.tasks)


def test_generate_profile_schedule_skips_existing_titles() -> None:
    owner = Owner(name="Jordan", available_minutes_per_day=120)
    pet = Pet(name="Mochi", species="dog", breed="corgi", age=3)
    pet.add_task(CareTask(title="Morning walk", duration_minutes=20, priority="high", recurrence="daily"))
    owner.add_pet(pet)

    added = generate_profile_schedule_for_pet(owner, pet)

    assert "Morning walk" not in added


def test_generate_profile_schedule_applies_owner_preferences_morning_first() -> None:
    owner = Owner(name="Jordan", available_minutes_per_day=120, preferences="prioritize mornings")
    pet = Pet(name="Mochi", species="dog", breed="corgi", age=3)
    owner.add_pet(pet)

    generate_profile_schedule_for_pet(owner, pet)

    morning_walk = next(task for task in pet.tasks if task.title == "Morning walk")
    assert morning_walk.start_time is not None
    assert morning_walk.start_time.strftime("%H:%M") == "07:45"


def test_generate_profile_schedule_applies_owner_preferences_avoid_evenings() -> None:
    owner = Owner(name="Jordan", available_minutes_per_day=120, preferences="avoid evenings")
    pet = Pet(name="Mochi", species="dog", breed="corgi", age=3)
    owner.add_pet(pet)

    generate_profile_schedule_for_pet(owner, pet)

    dinner = next(task for task in pet.tasks if task.title == "Dinner")
    evening_walk = next(task for task in pet.tasks if task.title == "Evening walk")
    assert dinner.start_time is not None
    assert evening_walk.start_time is not None
    assert dinner.start_time.strftime("%H:%M") == "17:00"
    assert evening_walk.start_time.strftime("%H:%M") == "17:30"


def test_remove_task_removes_existing_task() -> None:
    pet = Pet(name="Mochi", species="dog", breed="corgi", age=3)
    pet.add_task(CareTask(title="Walk", duration_minutes=20, priority="high"))
    pet.add_task(CareTask(title="Feed", duration_minutes=10, priority="medium"))

    removed = pet.remove_task("Walk")
    assert removed is True
    assert [t.title for t in pet.tasks] == ["Feed"]


def test_remove_task_returns_false_for_missing_task() -> None:
    pet = Pet(name="Mochi", species="dog", breed="corgi", age=3)
    pet.add_task(CareTask(title="Walk", duration_minutes=20, priority="high"))

    removed = pet.remove_task("Does not exist")
    assert removed is False
    assert len(pet.tasks) == 1


def test_generate_daily_plan_enforces_available_minutes_limit() -> None:
    scheduler = Scheduler()
    owner = Owner(name="Jordan", available_minutes_per_day=30)
    pet = Pet(name="Mochi", species="dog", breed="corgi", age=3)
    pet.add_task(CareTask(title="Morning walk", duration_minutes=20, priority="high", start_time=time(8, 0)))
    pet.add_task(CareTask(title="Breakfast", duration_minutes=15, priority="high", start_time=time(9, 0)))
    pet.add_task(CareTask(title="Play", duration_minutes=10, priority="medium"))
    owner.add_pet(pet)

    plan = scheduler.generate_daily_plan(owner)

    assert [task.title for task in plan] == ["Morning walk", "Play"]
    assert sum(task.duration_minutes for task in plan) <= owner.available_minutes_per_day


def test_generate_daily_plan_removes_conflicting_tasks() -> None:
    scheduler = Scheduler()
    owner = Owner(name="Jordan", available_minutes_per_day=120)
    pet = Pet(name="Mochi", species="dog", breed="corgi", age=3)
    pet.add_task(CareTask(title="Medication", duration_minutes=30, priority="high", start_time=time(9, 0)))
    pet.add_task(CareTask(title="Vet call", duration_minutes=15, priority="high", start_time=time(9, 10)))
    pet.add_task(CareTask(title="Lunch", duration_minutes=15, priority="medium", start_time=time(10, 0)))
    owner.add_pet(pet)

    plan = scheduler.generate_daily_plan(owner)

    assert [task.title for task in plan] == ["Medication", "Lunch"]
