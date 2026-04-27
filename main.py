from pawpal import CareTask, Owner, Pet, Scheduler


def build_sample_data() -> Owner:
    owner = Owner(name="Jordan", available_minutes_per_day=75, preferences="Morning first")

    dog = Pet(name="Mochi", species="dog", age=3)
    cat = Pet(name="Luna", species="cat", age=5)

    # Add tasks out of time order to validate sorting behavior.
    dog.add_task(
        CareTask(
            title="Morning Walk",
            duration_minutes=30,
            priority="high",
            recurrence="daily",
            start_time="09:30",
        )
    )
    dog.add_task(
        CareTask(
            title="Breakfast",
            duration_minutes=10,
            priority="high",
            recurrence="daily",
            start_time="08:00",
        )
    )
    cat.add_task(
        CareTask(
            title="Playtime",
            duration_minutes=20,
            priority="medium",
            recurrence="daily",
            start_time="10:00",
        )
    )
    cat.add_task(
        CareTask(
            title="Brush Fur",
            duration_minutes=15,
            priority="low",
            recurrence="none",
            start_time="07:30",
        )
    )
    # Mark one task complete to validate status filtering.
    cat.tasks[-1].mark_complete()

    owner.add_pet(dog)
    owner.add_pet(cat)
    return owner


def print_schedule(owner: Owner) -> None:
    scheduler = Scheduler()
    all_tasks = owner.get_all_tasks()
    time_sorted = scheduler.sort_by_time(all_tasks)
    only_mochi = scheduler.filter_tasks(all_tasks, pet_name="Mochi", status="incomplete")
    only_completed = scheduler.filter_tasks(all_tasks, status="completed")
    plan = scheduler.generate_daily_plan(owner)

    print("All Tasks Sorted By Time")
    print("-" * 40)
    for task in time_sorted:
        label = task.start_time.strftime("%H:%M") if task.start_time else "Anytime"
        print(f"- {label} | {task.pet_name}: {task.title}")
    print()

    print("Filtered Tasks (Pet = Mochi, Status = incomplete)")
    print("-" * 40)
    for task in only_mochi:
        print(f"- {task.pet_name}: {task.title} [{task.priority}]")
    print()

    print("Filtered Tasks (Status = completed)")
    print("-" * 40)
    for task in only_completed:
        print(f"- {task.pet_name}: {task.title}")
    print()

    print("Today's Schedule")
    print("-" * 40)

    if not plan:
        print("No tasks scheduled today.")
        return

    running_total = 0
    for index, task in enumerate(plan, start=1):
        running_total += task.duration_minutes
        label = task.start_time.strftime("%H:%M") if task.start_time else "Anytime"
        print(
            f"{index}. {label} | {task.pet_name}: {task.title} "
            f"({task.duration_minutes} min, {task.priority} priority)"
        )

    print("-" * 40)
    print(f"Total scheduled minutes: {running_total}")
    print(scheduler.explain_plan(plan))


if __name__ == "__main__":
    sample_owner = build_sample_data()
    print_schedule(sample_owner)
