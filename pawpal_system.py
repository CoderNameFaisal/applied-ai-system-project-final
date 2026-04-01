"""Core domain skeleton for PawPal+ scheduling logic.

This module defines the main classes and method signatures used by the app.
Behavior focuses on practical scheduling for daily pet care planning.
"""

from __future__ import annotations

from datetime import date
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CareTask:
    """Represents a single pet care activity."""

    title: str
    duration_minutes: int
    priority: str  # e.g., "low", "medium", "high"
    recurrence: str = "none"  # e.g., "none", "daily", "weekly"
    is_completed: bool = False
    start_date: date = field(default_factory=date.today)
    last_completed_on: Optional[date] = None

    def __post_init__(self) -> None:
        """Validate and normalize task fields after initialization."""
        self.title = self.title.strip()
        self.priority = self.priority.strip().lower()
        self.recurrence = self.recurrence.strip().lower()

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

    def is_due_on(self, on_date: date) -> bool:
        """Return whether the task should run on a specific date."""
        if on_date < self.start_date:
            return False

        if self.recurrence == "none":
            return not self.is_completed

        if self.recurrence == "daily":
            return self.last_completed_on != on_date

        # Weekly tasks recur on the same weekday as start_date.
        if on_date.weekday() != self.start_date.weekday():
            return False
        return self.last_completed_on != on_date

    def is_due_today(self) -> bool:
        """Return whether the task should run today."""
        return self.is_due_on(date.today())


@dataclass
class Pet:
    """Represents a pet and its care tasks."""

    name: str
    species: str
    age: int
    tasks: List[CareTask] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate and normalize pet fields after initialization."""
        self.name = self.name.strip()
        self.species = self.species.strip().lower()
        if not self.name:
            raise ValueError("Pet name cannot be empty.")
        if self.age < 0:
            raise ValueError("Pet age cannot be negative.")

    def add_task(self, task: CareTask) -> None:
        """Add a care task for this pet."""
        if not isinstance(task, CareTask):
            raise TypeError("task must be a CareTask instance.")
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

    def generate_daily_plan(self, owner: Owner, on_date: Optional[date] = None) -> List[CareTask]:
        """Generate a plan across all owner pets for the target date."""
        target_date = on_date or date.today()
        due_tasks = owner.get_due_tasks(on_date=target_date)
        sorted_tasks = self.sort_tasks(due_tasks)
        return self.filter_by_available_time(sorted_tasks, owner.available_minutes_per_day)

    def sort_tasks(self, tasks: List[CareTask]) -> List[CareTask]:
        """Return tasks sorted by priority, then shorter duration, then title."""
        return sorted(
            tasks,
            key=lambda task: (
                self._priority_rank.get(task.priority, 3),
                task.duration_minutes,
                task.title.lower(),
            ),
        )

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
            "Plan built by sorting tasks by priority, then duration, and keeping only tasks "
            f"that fit your time budget. Total scheduled time: {total_minutes} minutes. "
            f"Tasks: {titles}."
        )
