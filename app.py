import streamlit as st

from pawpal_system import CareTask, Owner, Pet, Scheduler

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

# Persist core domain objects across Streamlit reruns.
if "owners_by_name" not in st.session_state:
    default_owner = Owner(name="Jordan", available_minutes_per_day=90)
    st.session_state.owners_by_name = {default_owner.name.lower(): default_owner}
    st.session_state.current_owner_key = default_owner.name.lower()

if "current_owner_key" not in st.session_state and st.session_state.owners_by_name:
    st.session_state.current_owner_key = next(iter(st.session_state.owners_by_name))

if "scheduler" not in st.session_state:
    st.session_state.scheduler = Scheduler()

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
    if st.button("Save preferences"):
        st.success("Owner preferences saved.")

current_owner = st.session_state.owners_by_name[st.session_state.current_owner_key]
current_owner.set_preferences("Use priority-first scheduling")

availability = st.number_input(
    "Available minutes per day",
    min_value=0,
    max_value=720,
    value=current_owner.available_minutes_per_day,
)
current_owner.set_availability(int(availability))

st.markdown("### Add a Pet")
pet_col1, pet_col2, pet_col3 = st.columns(3)
with pet_col1:
    pet_name = st.text_input("Pet name", value="Mochi")
with pet_col2:
    species = st.selectbox("Species", ["dog", "cat", "other"])
with pet_col3:
    age = st.number_input("Age", min_value=0, max_value=40, value=1)

if st.button("Add pet"):
    try:
        current_owner.add_pet(Pet(name=pet_name, species=species, age=int(age)))
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

task_start_time = st.time_input("Start time", value="09:00") if has_start_time else None

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

st.subheader("Build Schedule")
st.caption("This button now uses your scheduler with session-persisted Owner and Pet data.")

pet_filter_options = ["All"] + [pet.name for pet in current_owner.pets]
filter_col1, filter_col2 = st.columns(2)
with filter_col1:
    selected_pet_filter = st.selectbox("Filter by pet", pet_filter_options)
with filter_col2:
    selected_status_filter = st.selectbox("Filter by status", ["due", "incomplete", "completed"])

if st.button("Generate schedule"):
    plan = st.session_state.scheduler.generate_daily_plan(
        current_owner,
        pet_name=selected_pet_filter,
        status=selected_status_filter,
    )
    all_due_filtered = st.session_state.scheduler.filter_tasks(
        st.session_state.scheduler.expand_recurring_tasks(current_owner.get_all_tasks()),
        pet_name=selected_pet_filter,
        status=selected_status_filter,
    )
    conflicts = st.session_state.scheduler.detect_conflicts(all_due_filtered)
    if conflicts:
        st.warning(
            "Conflicts detected: "
            + ", ".join(
                f"{first.title} overlaps with {second.title}" for first, second in conflicts
            )
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
        st.caption(st.session_state.scheduler.explain_plan(plan))
