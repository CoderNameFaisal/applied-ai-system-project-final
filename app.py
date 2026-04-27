from datetime import datetime, time, timedelta

import streamlit as st

from pawpal import CareTask, Owner, Pet, Scheduler
from pawpal.ai.conflict_rag import apply_conflict_moves, propose_conflict_resolution
from pawpal.ai.plan_explainer import explain_plan_with_agent
from pawpal.ai.rag_intake import apply_rag_intake
from pawpal.config import load_settings

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Owner Setup")
settings = load_settings()

# Persist core domain objects across Streamlit reruns.
if "owners_by_name" not in st.session_state:
    default_owner = Owner(name="Jordan", available_minutes_per_day=90)
    st.session_state.owners_by_name = {default_owner.name.lower(): default_owner}
    st.session_state.current_owner_key = default_owner.name.lower()

if "current_owner_key" not in st.session_state and st.session_state.owners_by_name:
    st.session_state.current_owner_key = next(iter(st.session_state.owners_by_name))

if "scheduler" not in st.session_state:
    st.session_state.scheduler = Scheduler()
if "conflict_suggestion" not in st.session_state:
    st.session_state.conflict_suggestion = None

owner_options = [owner.name for owner in st.session_state.owners_by_name.values()]
selected_owner_name = st.selectbox("Saved owners", owner_options)

selected_owner_key = selected_owner_name.strip().lower()
if selected_owner_key != st.session_state.current_owner_key:
    st.session_state.current_owner_key = selected_owner_key

owner_name_input = st.text_input("Owner name (create or switch)", value=selected_owner_name)

owner_action_col1, owner_action_col2 = st.columns(2)
with owner_action_col1:
    if st.button("Use owner name"):
        key = owner_name_input.strip().lower()
        if not key:
            st.warning("Owner name cannot be empty.")
        elif key in st.session_state.owners_by_name:
            st.session_state.current_owner_key = key
            st.success(f"Switched to owner: {st.session_state.owners_by_name[key].name}")
        else:
            new_owner = Owner(name=owner_name_input.strip(), available_minutes_per_day=90)
            st.session_state.owners_by_name[key] = new_owner
            st.session_state.current_owner_key = key
            st.success(f"Created owner: {new_owner.name}")

with owner_action_col2:
    st.caption("Preferences are now persisted from the text area below.")

current_owner = st.session_state.owners_by_name[st.session_state.current_owner_key]
preferences_input = st.text_area(
    "Owner preferences",
    value=current_owner.preferences,
    help="Scheduling preferences or constraints, for example: prioritize mornings, avoid evenings.",
)
if st.button("Apply owner preferences"):
    current_owner.set_preferences(preferences_input)
    st.success("Owner preferences saved.")

availability = st.number_input(
    "Available minutes per day",
    min_value=0,
    max_value=720,
    value=current_owner.available_minutes_per_day,
)
current_owner.set_availability(int(availability))

st.markdown("### Add a Pet")
pet_col1, pet_col2, pet_col3, pet_col4 = st.columns(4)
with pet_col1:
    pet_name = st.text_input("Pet name", value="Mochi")
with pet_col2:
    species = st.selectbox("Species", ["dog", "cat", "other"])
with pet_col3:
    breed = st.text_input("Breed", value="Mixed")
with pet_col4:
    age = st.number_input("Age", min_value=0, max_value=40, value=1)
habits = st.text_area("Habits (optional)", value="")

if st.button("Add pet"):
    try:
        current_owner.add_pet(
            Pet(
                name=pet_name,
                species=species,
                breed=breed,
                age=int(age),
                habits=habits,
            )
        )
        st.success(f"Added pet for {current_owner.name}: {pet_name}")
    except ValueError as error:
        st.warning(str(error))

if not current_owner.pets:
    st.info("No pets added yet. Add at least one pet to schedule tasks.")
    st.stop()

pet_names = [pet.name for pet in current_owner.pets]
selected_pet_name = st.selectbox("Select pet for task scheduling", pet_names)
selected_pet = next(pet for pet in current_owner.pets if pet.name == selected_pet_name)

st.markdown("### Tasks")
st.caption("Schedule tasks by calling your Pet and CareTask methods.")

col1, col2, col3 = st.columns(3)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

col4, col5 = st.columns(2)
with col4:
    recurrence = st.selectbox("Recurrence", ["none", "daily", "weekly"], index=1)
with col5:
    has_start_time = st.checkbox("Set start time", value=False)

task_start_time = st.time_input("Start time", value=time(9, 0)) if has_start_time else None

if st.button("Add task"):
    try:
        selected_pet.add_task(
            CareTask(
                title=task_title,
                duration_minutes=int(duration),
                priority=priority,
                recurrence=recurrence,
                start_time=task_start_time,
            )
        )
        st.success(f"Added task for {selected_pet.name}: {task_title}")
    except ValueError as error:
        st.warning(str(error))

current_tasks = selected_pet.get_tasks()
if current_tasks:
    st.write(f"Current tasks for {selected_pet.name}:")
    st.table(
        [
            {
                "title": task.title,
                "duration_minutes": task.duration_minutes,
                "priority": task.priority,
                "recurrence": task.recurrence,
                "start_time": task.start_time.strftime("%H:%M") if task.start_time else "Anytime",
                "status": "completed" if task.is_completed else "incomplete",
            }
            for task in current_tasks
        ]
    )
else:
    st.info("No tasks yet. Add one above.")

st.divider()
st.subheader("Natural language (AI + RAG)")
nl_request = st.text_area(
    "Describe updates you want (preferences/tasks).",
    help="Example: Add a 15 minute evening walk for Mochi and prioritize morning feed windows.",
)
if not settings.openai_api_key:
    st.info("Set OPENAI_API_KEY in .env to enable AI intake and conflict suggestions.")
if st.button("Apply with AI (RAG)", disabled=not bool(settings.openai_api_key)):
    try:
        intake_result = apply_rag_intake(current_owner, nl_request)
        if intake_result.applied_actions:
            st.success("Applied actions: " + ", ".join(intake_result.applied_actions))
        else:
            st.warning("No valid actions were returned by the AI.")
        st.caption(intake_result.explanation)
        if intake_result.citations:
            st.caption("Knowledge sources: " + ", ".join(intake_result.citations))
    except Exception as error:  # pragma: no cover - streamlit runtime guard
        st.error(f"AI intake failed: {error}")

st.divider()

st.subheader("Build Schedule")
st.caption("This button now uses your scheduler with session-persisted Owner and Pet data.")

pet_filter_options = ["All"] + [pet.name for pet in current_owner.pets]
filter_col1, filter_col2 = st.columns(2)
with filter_col1:
    selected_pet_filter = st.selectbox("Filter by pet", pet_filter_options)
with filter_col2:
    selected_status_filter = st.selectbox("Filter by status", ["due", "incomplete", "completed"])


def _format_end_time(task: CareTask) -> str:
    if not task.start_time:
        return "N/A"
    start_dt = datetime.combine(datetime.today(), task.start_time)
    end_dt = start_dt + timedelta(minutes=task.duration_minutes)
    return end_dt.strftime("%H:%M")

if st.button("Generate schedule"):
    all_due_filtered = st.session_state.scheduler.filter_tasks(
        st.session_state.scheduler.expand_recurring_tasks(current_owner.get_all_tasks()),
        pet_name=selected_pet_filter,
        status=selected_status_filter,
    )

    sorted_filtered = st.session_state.scheduler.sort_tasks(all_due_filtered)
    st.success(f"Filtered tasks ready: {len(sorted_filtered)}")
    if sorted_filtered:
        st.write("Filtered + Sorted Task Preview")
        st.table(
            [
                {
                    "pet": task.pet_name or "Unknown",
                    "title": task.title,
                    "start_time": task.start_time.strftime("%H:%M") if task.start_time else "Anytime",
                    "end_time": _format_end_time(task),
                    "duration_minutes": task.duration_minutes,
                    "priority": task.priority,
                    "status": "completed" if task.is_completed else "incomplete",
                }
                for task in sorted_filtered
            ]
        )

    conflicts = st.session_state.scheduler.detect_conflicts(sorted_filtered)
    if conflicts:
        conflict_rows = [
            {
                "first_task": first.title,
                "first_window": (
                    f"{first.start_time.strftime('%H:%M')} - {_format_end_time(first)}"
                    if first.start_time
                    else "N/A"
                ),
                "second_task": second.title,
                "second_window": (
                    f"{second.start_time.strftime('%H:%M')} - {_format_end_time(second)}"
                    if second.start_time
                    else "N/A"
                ),
                "tip": "Adjust start time or shorten one task.",
            }
            for first, second in conflicts
        ]
        st.warning(
            "Scheduling conflict detected. Review overlapping tasks below and adjust time or duration."
        )
        st.table(conflict_rows)
        if settings.openai_api_key:
            if st.button("Suggest conflict fix (RAG)"):
                try:
                    st.session_state.conflict_suggestion = propose_conflict_resolution(current_owner, conflicts)
                except Exception as error:  # pragma: no cover - streamlit runtime guard
                    st.error(f"Conflict RAG failed: {error}")
            suggestion = st.session_state.conflict_suggestion
            if suggestion:
                st.caption(suggestion.explanation)
                if suggestion.citations:
                    st.caption("Knowledge sources: " + ", ".join(suggestion.citations))
                if suggestion.moves:
                    st.table(suggestion.moves)
                    if st.button("Apply suggested times"):
                        applied = apply_conflict_moves(current_owner, suggestion.moves)
                        if applied:
                            st.success("Applied updates: " + ", ".join(applied))
                        else:
                            st.warning("No suggested moves could be applied.")
                else:
                    st.warning("No schedule move suggestions were generated.")
        else:
            st.info("Add OPENAI_API_KEY to enable RAG conflict suggestions.")
    else:
        st.session_state.conflict_suggestion = None

    plan = st.session_state.scheduler.generate_daily_plan(
        current_owner,
        pet_name=selected_pet_filter,
        status=selected_status_filter,
    )

    if not plan:
        st.warning("No tasks fit within the current schedule constraints.")
    else:
        st.success("Today's Schedule")
        st.table(
            [
                {
                    "pet": task.pet_name or "Unknown",
                    "title": task.title,
                    "start_time": task.start_time.strftime("%H:%M") if task.start_time else "Anytime",
                    "duration_minutes": task.duration_minutes,
                    "priority": task.priority,
                    "status": "completed" if task.is_completed else "incomplete",
                }
                for task in plan
            ]
        )
        stub_explanation = st.session_state.scheduler.explain_plan(plan)
        try:
            agent_explanation = explain_plan_with_agent(current_owner, plan, scheduler_stub=stub_explanation)
            st.markdown("### Agent plan explanation")
            st.write(agent_explanation)
        except Exception as error:  # pragma: no cover - streamlit runtime guard
            st.warning(f"Agent explanation unavailable: {error}")
            st.caption(stub_explanation)
        with st.expander("Deterministic scheduler explanation"):
            st.caption(stub_explanation)
