from datetime import date, timedelta, time

from pawpal_system import CareTask, Owner, Pet, Scheduler


def test_mark_complete_updates_task_status() -> None:
    task = CareTask(title="Evening Feed", duration_minutes=15, priority="high")

    task.mark_complete()

    assert task.is_completed is True


def test_add_task_increases_pet_task_count() -> None:
    pet = Pet(name="Mochi", species="dog", age=3)
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
    dog = Pet(name="Mochi", species="dog", age=3)
    cat = Pet(name="Luna", species="cat", age=5)

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
    pet = Pet(name="Mochi", species="dog", age=3)
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
    pet = Pet(name="Luna", species="cat", age=5)
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
