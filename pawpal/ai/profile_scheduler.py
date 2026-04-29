"""Profile-based starter schedules to reduce manual task entry."""

from __future__ import annotations

import re
from datetime import time
from typing import Iterable

from pawpal.system import CareTask, Owner, Pet

_DOG_PUPPY_AGE_MAX = 1
_DOG_SENIOR_AGE_MIN = 8


def _preferences_flags(preferences: str) -> dict[str, bool]:
    prefs = (preferences or "").strip().lower()
    return {
        # Examples:
        # "prioritize mornings", "morning first", "morning tasks first"
        "morning_first": "morning" in prefs
        and (
            "first" in prefs
            or "prioritize" in prefs
            or "prioritise" in prefs
            or "mornings" in prefs
            or "morning tasks" in prefs
        ),
        # Examples:
        # "avoid evenings", "avoid evening", "no evening"
        "avoid_evenings": "avoid evening" in prefs or "avoid evenings" in prefs or "no evening" in prefs,
    }


def _extract_after_time_limit_minutes(preferences: str) -> int | None:
    """
    Extract simple patterns like:
    - "no walks after 8 pm"
    - "no walks after 20:00"
    Returns minutes-since-midnight for the limit.
    """
    prefs = (preferences or "").lower()

    # HH:MM (24h) pattern
    match_24 = re.search(r"after\s+([01]?\d|2[0-3]):([0-5]\d)", prefs)
    if match_24:
        hour = int(match_24.group(1))
        minute = int(match_24.group(2))
        return hour * 60 + minute

    # "after 8 pm" / "after 8:30 pm" pattern
    match_12 = re.search(
        r"after\s+(\d{1,2})(?::([0-5]\d))?\s*(am|pm)\b",
        prefs,
        flags=re.IGNORECASE,
    )
    if not match_12:
        return None

    hour = int(match_12.group(1))
    minute = int(match_12.group(2) or "0")
    ampm = match_12.group(3).lower()
    if ampm == "pm" and hour != 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0
    return hour * 60 + minute


def _minutes_to_hhmm(minutes_since_midnight: int) -> tuple[int, int]:
    minutes_since_midnight = max(0, min(24 * 60 - 1, minutes_since_midnight))
    return divmod(minutes_since_midnight, 60)


def _shift_evening_walk_by_owner_preferences(start_hour: int, start_minute: int, owner_preferences: str) -> tuple[int, int]:
    """
    Applies only "after TIME" style constraints to the evening-walk task.
    This is intentionally narrow (walks only) to keep behavior predictable.
    """
    limit_minutes = _extract_after_time_limit_minutes(owner_preferences)
    if limit_minutes is None:
        return start_hour, start_minute

    current_minutes = start_hour * 60 + start_minute
    if current_minutes <= limit_minutes:
        return start_hour, start_minute

    # Move it earlier to give some buffer.
    new_minutes = limit_minutes - 30
    return _minutes_to_hhmm(new_minutes)


def _apply_owner_time_preferences(
    *,
    base_times: dict[str, tuple[int, int]],
    owner_preferences: str,
) -> dict[str, tuple[int, int]]:
    flags = _preferences_flags(owner_preferences)
    times = dict(base_times)

    if flags["morning_first"]:
        times["breakfast"] = (7, 15)
        times["morning_walk"] = (7, 45)
        times["play"] = (11, 45)
        times["dinner"] = (17, 15)
        times["evening_walk"] = (18, 15)
    elif flags["avoid_evenings"]:
        times["dinner"] = (17, 0)
        times["evening_walk"] = (17, 30)
        # Nudge play a little earlier so more things fit pre-evening.
        times["play"] = (12, 0)

    # Apply "no walks after X" style constraints as the final clamp.
    (eh, em) = times["evening_walk"]
    times["evening_walk"] = _shift_evening_walk_by_owner_preferences(eh, em, owner_preferences)
    return times


def _apply_owner_time_preferences_cat(
    *,
    base_times: dict[str, tuple[int, int]],
    owner_preferences: str,
) -> dict[str, tuple[int, int]]:
    flags = _preferences_flags(owner_preferences)
    times = dict(base_times)
    if flags["morning_first"]:
        times["breakfast"] = (7, 15)
        times["litter"] = (7, 45)
        times["play"] = (17, 45)
        times["dinner"] = (18, 15)
    elif flags["avoid_evenings"]:
        times["play"] = (17, 30)
        times["dinner"] = (18, 0)
    return times


def _extract_preference_value(text: str, label: str) -> str:
    pattern = re.compile(rf"{label}\s*[:=-]\s*([^\n,;]+)", re.IGNORECASE)
    match = pattern.search(text or "")
    if not match:
        return ""
    return match.group(1).strip()


def _task(
    *,
    title: str,
    duration_minutes: int,
    priority: str,
    start_hour: int,
    start_minute: int,
    recurrence: str = "daily",
) -> CareTask:
    return CareTask(
        title=title,
        duration_minutes=duration_minutes,
        priority=priority,
        recurrence=recurrence,
        start_time=time(start_hour, start_minute),
    )


def _meal_titles(food: str) -> tuple[str, str]:
    if not food:
        return "Breakfast", "Dinner"
    return f"Breakfast ({food})", f"Dinner ({food})"


def _build_dog_starter_tasks(pet: Pet, owner_preferences: str) -> list[CareTask]:
    toy = _extract_preference_value(pet.habits, "favorite toy")
    food = _extract_preference_value(pet.habits, "favorite food")
    play_title = f"Play session ({toy})" if toy else "Play session"
    breakfast_title, dinner_title = _meal_titles(food)

    base_times = {
        "breakfast": (7, 30),
        "morning_walk": (8, 0),
        "play": (12, 30),
        "dinner": (18, 0),
        "evening_walk": (19, 0),
    }
    times = _apply_owner_time_preferences(base_times=base_times, owner_preferences=owner_preferences)

    tasks = [
        _task(
            title=breakfast_title,
            duration_minutes=15,
            priority="high",
            start_hour=times["breakfast"][0],
            start_minute=times["breakfast"][1],
        ),
        _task(
            title="Morning walk",
            duration_minutes=25,
            priority="high",
            start_hour=times["morning_walk"][0],
            start_minute=times["morning_walk"][1],
        ),
        _task(
            title=play_title,
            duration_minutes=20,
            priority="medium",
            start_hour=times["play"][0],
            start_minute=times["play"][1],
        ),
        _task(
            title=dinner_title,
            duration_minutes=15,
            priority="high",
            start_hour=times["dinner"][0],
            start_minute=times["dinner"][1],
        ),
        _task(
            title="Evening walk",
            duration_minutes=20,
            priority="high",
            start_hour=times["evening_walk"][0],
            start_minute=times["evening_walk"][1],
        ),
    ]

    if pet.age <= _DOG_PUPPY_AGE_MAX:
        tasks.append(
            _task(title="Puppy training", duration_minutes=15, priority="high", start_hour=14, start_minute=0)
        )
    elif pet.age >= _DOG_SENIOR_AGE_MIN:
        tasks.append(
            _task(
                title="Mobility and wellness check",
                duration_minutes=10,
                priority="medium",
                start_hour=16,
                start_minute=0,
            )
        )
    return tasks


def _build_default_starter_tasks(pet: Pet, owner_preferences: str) -> list[CareTask]:
    if pet.species == "dog":
        return _build_dog_starter_tasks(pet, owner_preferences=owner_preferences)
    if pet.species == "cat":
        base_times = {
            "breakfast": (7, 30),
            "litter": (8, 0),
            "play": (18, 30),
            "dinner": (19, 0),
        }
        times = _apply_owner_time_preferences_cat(base_times=base_times, owner_preferences=owner_preferences)
        return [
            _task(title="Breakfast", duration_minutes=10, priority="high", start_hour=times["breakfast"][0], start_minute=times["breakfast"][1]),
            _task(title="Litter box scoop", duration_minutes=10, priority="high", start_hour=times["litter"][0], start_minute=times["litter"][1]),
            _task(title="Interactive play", duration_minutes=15, priority="medium", start_hour=times["play"][0], start_minute=times["play"][1]),
            _task(title="Dinner", duration_minutes=10, priority="high", start_hour=times["dinner"][0], start_minute=times["dinner"][1]),
        ]
    flags = _preferences_flags(owner_preferences)
    if flags["morning_first"]:
        return [
            _task(title="Morning care check", duration_minutes=15, priority="high", start_hour=7, start_minute=30),
            _task(title="Evening care check", duration_minutes=15, priority="high", start_hour=17, start_minute=30),
        ]
    if flags["avoid_evenings"]:
        return [
            _task(title="Morning care check", duration_minutes=15, priority="high", start_hour=8, start_minute=0),
            _task(title="Evening care check", duration_minutes=15, priority="high", start_hour=17, start_minute=0),
        ]
    return [
        _task(title="Morning care check", duration_minutes=15, priority="high", start_hour=8, start_minute=0),
        _task(title="Evening care check", duration_minutes=15, priority="high", start_hour=18, start_minute=0),
    ]


def _dedupe_and_add_tasks(pet: Pet, tasks: Iterable[CareTask]) -> list[str]:
    existing_titles = {task.title.strip().lower() for task in pet.tasks}
    added: list[str] = []
    for task in tasks:
        normalized_title = task.title.strip().lower()
        if normalized_title in existing_titles:
            continue
        pet.add_task(task)
        existing_titles.add(normalized_title)
        added.append(task.title)
    return added


def generate_profile_schedule_for_pet(owner: Owner, pet: Pet) -> list[str]:
    """Create starter tasks from profile, skipping titles that already exist."""
    if pet not in owner.pets:
        raise ValueError("Pet must belong to the selected owner.")
    return _dedupe_and_add_tasks(pet, _build_default_starter_tasks(pet, owner_preferences=owner.preferences))
