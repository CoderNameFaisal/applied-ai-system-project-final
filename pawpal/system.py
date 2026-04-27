"""Core domain skeleton for PawPal+ scheduling logic.

This module defines the main classes and method signatures used by the app.
Behavior focuses on practical scheduling for daily pet care planning.
"""

from __future__ import annotations

from datetime import date, time, timedelta
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union


@dataclass
class CareTask:
    """Represents a single pet care activity."""

    title: str
    duration_minutes: int
    priority: str  # e.g., "low", "medium", "high"
    recurrence: str = "none"  # e.g., "none", "daily", "weekly"
    is_completed: bool = False
    start_date: date = field(default_factory=date.today)
    start_time: Optional[Union[time, str]] = None
    pet_name: Optional[str] = None
    last_completed_on: Optional[date] = None

    def __post_init__(self) -> None:
        """Validate and normalize task fields after initialization."""
        self.title = self.title.strip()
        self.priority = self.priority.strip().lower()
        self.recurrence = self.recurrence.strip().lower()

        if isinstance(self.start_time, str):
            self.start_time = time.fromisoformat(self.start_time)

        if not self.title:
            raise ValueError("Task title cannot be empty.")
        if self.duration_minutes <= 0:
            raise ValueError("Task duration must be greater than 0 minutes.")
        if self.priority not in {"high", "medium", "low"}:
            raise ValueError("Priority must be one of: high, medium, low.")
        if self.recurrence not in {"none", "daily", "weekly"}:
            raise ValueError("Recurrence must be one of: none, daily, weekly.")

    def mark_complete(self, on_date: Optional[date] = None) -> None:
        """Mark this task as completed."""
        self.is_completed = True
        self.last_completed_on = on_date or date.today()

    def mark_incomplete(self) -> None:
        """Reset completion state for one-time tasks or edits."""
        self.is_completed = False

    def set_start_time_str(self, value: Optional[str]) -> None:
        """Set start_time from HH:MM text, or clear it with None/empty."""
        if value is None:
            self.start_time = None
            return
        cleaned = value.strip()
        if not cleaned:
            self.start_time = None
            return
        self.start_time = time.fromisoformat(cleaned)

    def is_due_on(self, on_date: date) -> bool:
        """Return whether the task should run on a specific date."""
        if on_date < self.start_date:
            return False

        # Completed tasks are historical records and should not be re-scheduled.
        if self.is_completed:
            return False

        if self.recurrence == "none":
            return True

        if self.recurrence == "daily":
            return True

        # Weekly tasks recur on the same weekday as start_date.
        if on_date.weekday() != self.start_date.weekday():
            return False
        return True

    def is_due_today(self) -> bool:
        """Return whether the task should run today."""
        return self.is_due_on(date.today())


@dataclass
class Pet:
    """Represents a pet and its care tasks."""

    name: str
    species: str
    breed: str
    age: int
    habits: str = ""
    tasks: List[CareTask] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate and normalize pet fields after initialization."""
        self.name = self.name.strip()
        self.species = self.species.strip().lower()
        self.breed = self.breed.strip()
        self.habits = self.habits.strip()
        if not self.name:
            raise ValueError("Pet name cannot be empty.")
        if not self.breed:
            raise ValueError("Pet breed cannot be empty.")
        if self.age < 0:
            raise ValueError("Pet age cannot be negative.")

    def add_task(self, task: CareTask) -> None:
        """Add a care task for this pet."""
        if not isinstance(task, CareTask):
            raise TypeError("task must be a CareTask instance.")
        task.pet_name = self.name
        self.tasks.append(task)

    def remove_task(self, task_title: str) -> bool:
        """Remove the first task with a matching title and return success state."""
        for index, task in enumerate(self.tasks):
            if task.title == task_title:
                del self.tasks[index]
                return True
        return False

    def get_tasks(self) -> List[CareTask]:
        """Return this pet's current tasks."""
        return list(self.tasks)

    def get_due_tasks(self, on_date: Optional[date] = None) -> List[CareTask]:
        """Return tasks that are due on a given date."""
        target_date = on_date or date.today()
        return [task for task in self.tasks if task.is_due_on(target_date)]

    def mark_task_complete(self, task_title: str, on_date: Optional[date] = None) -> Optional[CareTask]:
        """Mark a task complete and create the next recurring instance when applicable."""
        completed_on = on_date or date.today()
        for task in self.tasks:
            if task.title != task_title or task.is_completed:
                continue

            task.mark_complete(on_date=completed_on)

            if task.recurrence == "daily":
                next_start = completed_on + timedelta(days=1)
            elif task.recurrence == "weekly":
                next_start = completed_on + timedelta(days=7)
            else:
                return None

            next_task = CareTask(
                title=task.title,
                duration_minutes=task.duration_minutes,
                priority=task.priority,
                recurrence=task.recurrence,
                start_date=next_start,
                start_time=task.start_time,
            )
            self.add_task(next_task)
            return next_task

        return None


@dataclass
class Owner:
    """Represents a pet owner and planning constraints."""

    name: str
    available_minutes_per_day: int
    preferences: str = ""
    pets: List[Pet] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate and normalize owner fields after initialization."""
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("Owner name cannot be empty.")
        if self.available_minutes_per_day < 0:
            raise ValueError("Available minutes per day cannot be negative.")

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        if not isinstance(pet, Pet):
            raise TypeError("pet must be a Pet instance.")
        if any(existing_pet.name.lower() == pet.name.lower() for existing_pet in self.pets):
            raise ValueError(f"A pet named '{pet.name}' already exists for this owner.")
        self.pets.append(pet)

    def remove_pet(self, pet_name: str) -> bool:
        """Remove a pet by name. Returns True if removed."""
        for index, pet in enumerate(self.pets):
            if pet.name.lower() == pet_name.strip().lower():
                del self.pets[index]
                return True
        return False

    def set_availability(self, minutes: int) -> None:
        """Update daily available time in minutes."""
        if minutes < 0:
            raise ValueError("Available minutes per day cannot be negative.")
        self.available_minutes_per_day = minutes

    def set_preferences(self, preferences: str) -> None:
        """Update owner preferences text."""
        self.preferences = preferences

    def get_all_tasks(self) -> List[CareTask]:
        """Return all tasks across all pets."""
        tasks: List[CareTask] = []
        for pet in self.pets:
            tasks.extend(pet.get_tasks())
        return tasks

    def get_due_tasks(self, on_date: Optional[date] = None) -> List[CareTask]:
        """Return all due tasks across pets for a given date."""
        due_tasks: List[CareTask] = []
        for pet in self.pets:
            due_tasks.extend(pet.get_due_tasks(on_date=on_date))
        return due_tasks


class Scheduler:
    """Builds an ordered daily task plan using owner constraints."""

    def __init__(self) -> None:
        """Initialize priority ranking used in task sorting."""
        self._priority_rank = {"high": 0, "medium": 1, "low": 2}

    def mark_task_complete(
        self,
        owner: Owner,
        pet_name: str,
        task_title: str,
        on_date: Optional[date] = None,
    ) -> Optional[CareTask]:
        """Mark a task complete for a pet and auto-create next recurring instance."""
        selected_pet = next(
            (pet for pet in owner.pets if pet.name.lower() == pet_name.strip().lower()),
            None,
        )
        if selected_pet is None:
            raise ValueError(f"No pet named '{pet_name}' found.")
        return selected_pet.mark_task_complete(task_title=task_title, on_date=on_date)

    def generate_daily_plan(
        self,
        owner: Owner,
        on_date: Optional[date] = None,
        pet_name: Optional[str] = None,
        status: str = "due",
    ) -> List[CareTask]:
        """Generate a plan across all owner pets for the target date."""
        target_date = on_date or date.today()
        owner_tasks = owner.get_all_tasks()
        expanded_tasks = self.expand_recurring_tasks(owner_tasks, on_date=target_date)
        filtered_tasks = self.filter_tasks(
            expanded_tasks,
            pet_name=pet_name,
            status=status,
            on_date=target_date,
        )
        sorted_tasks = self.sort_tasks(filtered_tasks)
        conflict_free_tasks = self.remove_conflicting_tasks(sorted_tasks)
        return self.filter_by_available_time(conflict_free_tasks, owner.available_minutes_per_day)

    def expand_recurring_tasks(self, tasks: List[CareTask], on_date: Optional[date] = None) -> List[CareTask]:
        """Return tasks that are eligible for scheduling on the target date."""
        target_date = on_date or date.today()
        return [task for task in tasks if task.is_due_on(target_date)]

    def filter_tasks(
        self,
        tasks: List[CareTask],
        pet_name: Optional[str] = None,
        status: str = "due",
        on_date: Optional[date] = None,
    ) -> List[CareTask]:
        """Filter tasks by pet and status for the selected date."""
        target_date = on_date or date.today()
        filtered_tasks = tasks

        if pet_name and pet_name.strip().lower() != "all":
            selected_pet = pet_name.strip().lower()
            filtered_tasks = [
                task for task in filtered_tasks if (task.pet_name or "").strip().lower() == selected_pet
            ]

        status_key = status.strip().lower()
        if status_key == "completed":
            filtered_tasks = [task for task in filtered_tasks if task.is_completed]
        elif status_key == "incomplete":
            filtered_tasks = [task for task in filtered_tasks if not task.is_completed]
        elif status_key == "due":
            filtered_tasks = [task for task in filtered_tasks if task.is_due_on(target_date)]
        else:
            raise ValueError("status must be one of: due, completed, incomplete.")

        return filtered_tasks

    def sort_tasks(self, tasks: List[CareTask]) -> List[CareTask]:
        """Return tasks sorted by time first, then priority, duration, and title."""
        return sorted(
            tasks,
            key=lambda task: (
                task.start_time.strftime("%H:%M") if task.start_time else "99:99",
                self._priority_rank.get(task.priority, 3),
                task.duration_minutes,
                task.title.lower(),
            ),
        )

    def sort_by_time(self, tasks: List[CareTask]) -> List[CareTask]:
        """Return tasks sorted by HH:MM start_time, placing untimed tasks last."""
        return sorted(
            tasks,
            key=lambda task: task.start_time.strftime("%H:%M") if task.start_time else "99:99",
        )

    def detect_conflicts(self, tasks: List[CareTask]) -> List[Tuple[CareTask, CareTask]]:
        """Detect overlaps between timed tasks."""
        timed_tasks = sorted(
            (task for task in tasks if task.start_time is not None),
            key=lambda task: task.start_time,
        )

        conflicts: List[Tuple[CareTask, CareTask]] = []
        for previous, current in zip(timed_tasks, timed_tasks[1:]):

            previous_end_minutes = (
                previous.start_time.hour * 60
                + previous.start_time.minute
                + previous.duration_minutes
            )
            current_start_minutes = current.start_time.hour * 60 + current.start_time.minute

            if current_start_minutes < previous_end_minutes:
                conflicts.append((previous, current))

        return conflicts

    def remove_conflicting_tasks(self, tasks: List[CareTask]) -> List[CareTask]:
        """Keep tasks in order, skipping timed tasks that overlap already-selected tasks."""
        selected_tasks: List[CareTask] = []
        for task in tasks:
            if task.start_time is None:
                selected_tasks.append(task)
                continue

            task_start_minutes = task.start_time.hour * 60 + task.start_time.minute
            task_end_minutes = task_start_minutes + task.duration_minutes

            overlaps_existing = False
            for chosen_task in selected_tasks:
                if chosen_task.start_time is None:
                    continue
                chosen_start = chosen_task.start_time.hour * 60 + chosen_task.start_time.minute
                chosen_end = chosen_start + chosen_task.duration_minutes
                if task_start_minutes < chosen_end and chosen_start < task_end_minutes:
                    overlaps_existing = True
                    break

            if not overlaps_existing:
                selected_tasks.append(task)

        return selected_tasks

    def filter_by_available_time(self, tasks: List[CareTask], minutes: int) -> List[CareTask]:
        """Keep tasks that fit in the time budget."""
        if minutes < 0:
            raise ValueError("minutes must be non-negative.")

        plan: List[CareTask] = []
        used = 0
        for task in tasks:
            if used + task.duration_minutes <= minutes:
                plan.append(task)
                used += task.duration_minutes
        return plan

    def explain_plan(self, plan: List[CareTask]) -> str:
        """Return a short human-readable explanation of ordering."""
        if not plan:
            return "No tasks fit within the available time today."
        total_minutes = sum(task.duration_minutes for task in plan)
        titles = ", ".join(task.title for task in plan)
        return (
            "Plan built by sorting tasks by time, then priority and duration, filtering by pet/status, "
            "and keeping non-conflicting tasks within your time budget. "
            f"Total scheduled time: {total_minutes} minutes. "
            f"Tasks: {titles}."
        )
