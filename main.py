from pawpal_system import CareTask, Owner, Pet, Scheduler


def build_sample_data() -> Owner:
    owner = Owner(name="Jordan", available_minutes_per_day=75, preferences="Morning first")

    dog = Pet(name="Mochi", species="dog", age=3)
    cat = Pet(name="Luna", species="cat", age=5)

    # Three tasks with different durations/priorities across both pets.
    dog.add_task(CareTask(title="Morning Walk", duration_minutes=30, priority="high", recurrence="daily"))
    dog.add_task(CareTask(title="Breakfast", duration_minutes=10, priority="high", recurrence="daily"))
    cat.add_task(CareTask(title="Playtime", duration_minutes=20, priority="medium", recurrence="daily"))

    owner.add_pet(dog)
    owner.add_pet(cat)
    return owner


def print_schedule(owner: Owner) -> None:
    scheduler = Scheduler()
    plan = scheduler.generate_daily_plan(owner)

    print("Today's Schedule")
    print("-" * 40)

    if not plan:
        print("No tasks scheduled today.")
        return

    running_total = 0
    for index, task in enumerate(plan, start=1):
        running_total += task.duration_minutes
        print(f"{index}. {task.title} ({task.duration_minutes} min, {task.priority} priority)")

    print("-" * 40)
    print(f"Total scheduled minutes: {running_total}")
    print(scheduler.explain_plan(plan))


if __name__ == "__main__":
    sample_owner = build_sample_data()
    print_schedule(sample_owner)
