from datetime import datetime, time, timedelta

import streamlit as st

from pawpal import CareTask, Owner, Pet, Scheduler
from pawpal.ai.plan_explainer import explain_plan_with_agent
from pawpal.ai.profile_scheduler import generate_profile_schedule_for_pet
from pawpal.ai.rag_schedule_validator import validate_schedule_with_rag
from pawpal.ai.rag_task_suggestions import apply_suggested_tasks, suggest_tasks_with_rag
from pawpal.ai.rag_tips import get_care_tips
from pawpal.config import load_settings

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.markdown(
    """
<style>
.main > div {
    padding-top: 1.6rem;
}
.hero-card {
    border: 1px solid rgba(120, 120, 120, 0.25);
    border-radius: 16px;
    padding: 1rem 1rem 0.8rem 1rem;
    background: rgba(40, 40, 45, 0.12);
}
.muted {
    opacity: 0.85;
    font-size: 0.95rem;
}
.section-title {
    margin-top: 0.35rem;
    margin-bottom: 0.25rem;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="hero-card">
  <h1 style="margin:0;">🐾 PawPal+</h1>
  <p class="muted">A simple daily pet-care planner that helps you organize tasks, avoid conflicts, and stay within your available time.</p>
</div>
""",
    unsafe_allow_html=True,
)

with st.expander("How to use PawPal+", expanded=True):
    st.markdown(
        """
1. Create or select an owner profile and set available minutes per day.  
2. Add each pet with species, breed, age.  
3. Add care tasks (walks, feeding, medication, grooming, play) with priority and optional start time.  
4. Click **Generate schedule** to build a daily plan, review conflicts.
"""
    )

st.divider()

st.subheader("Owner Setup")
settings = load_settings()
SPECIES_BREEDS = {
    "dog": [
        "Labrador Retriever",
        "German Shepherd",
        "Golden Retriever",
        "French Bulldog",
        "Poodle",
        "Beagle",
        "Rottweiler",
        "Dachshund",
        "Corgi",
        "Husky",
        "Mixed",
    ],
    "cat": [
        "Domestic Shorthair",
        "Maine Coon",
        "Siamese",
        "Ragdoll",
        "Persian",
        "Bengal",
        "Sphynx",
        "Mixed",
    ],
    "rabbit": ["Holland Lop", "Lionhead", "Mini Rex", "Netherland Dwarf", "Mixed"],
    "bird": ["Parakeet", "Cockatiel", "Canary", "Lovebird", "Parrot", "Other"],
    "hamster": ["Syrian", "Dwarf", "Roborovski", "Chinese", "Other"],
    "guinea pig": ["American", "Abyssinian", "Peruvian", "Silkie", "Other"],
    "fish": ["Goldfish", "Betta", "Guppy", "Tetra", "Cichlid", "Other"],
    "ferret": ["Standard", "Angora", "Other"],
    "reptile": ["Bearded Dragon", "Leopard Gecko", "Corn Snake", "Turtle", "Other"],
}


def _friendly_ai_error(error: Exception, feature_name: str) -> str:
    message = str(error)
    lowered = message.lower()
    if "429" in lowered or "resource_exhausted" in lowered or "quota" in lowered:
        return (
            f"{feature_name} is temporarily unavailable because your API quota/rate limit was reached. "
            "Wait about a minute and retry, or upgrade/check billing for your API key."
        )
    return f"{feature_name} is temporarily unavailable. Please try again."


# Persist core domain objects across Streamlit reruns.
if "owners_by_name" not in st.session_state:
    default_owner = Owner(name="Jordan", available_minutes_per_day=90)
    st.session_state.owners_by_name = {default_owner.name.lower(): default_owner}
    st.session_state.current_owner_key = default_owner.name.lower()

if "current_owner_key" not in st.session_state and st.session_state.owners_by_name:
    st.session_state.current_owner_key = next(iter(st.session_state.owners_by_name))

if "scheduler" not in st.session_state:
    st.session_state.scheduler = Scheduler()
if "last_schedule_result" not in st.session_state:
    st.session_state.last_schedule_result = None
if "rag_task_suggestions" not in st.session_state:
    st.session_state.rag_task_suggestions = None
if "schedule_validation" not in st.session_state:
    st.session_state.schedule_validation = None

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
st.caption(
    "What this does: saves your personal scheduling rules (for example, "
    "'morning tasks first' or 'no walks after 8 PM') and uses them when building schedules."
)
if st.button("Save preferences for scheduling"):
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
    species = st.selectbox("Species", list(SPECIES_BREEDS.keys()))
with pet_col3:
    breed = st.selectbox("Breed", SPECIES_BREEDS[species])
with pet_col4:
    age = st.number_input("Age", min_value=0, max_value=40, value=1)

if st.button("Add pet"):
    try:
        current_owner.add_pet(
            Pet(
                name=pet_name,
                species=species,
                breed=breed,
                age=int(age),
            )
        )
        st.success(f"Added pet for {current_owner.name}: {pet_name}")
        st.session_state.last_schedule_result = None
        st.session_state.schedule_validation = None
    except ValueError as error:
        st.warning(str(error))

if not current_owner.pets:
    st.info("No pets added yet. Add at least one pet to schedule tasks.")
    st.stop()

pet_names = [pet.name for pet in current_owner.pets]
selected_pet_name = st.selectbox("Select pet for task scheduling", pet_names)
selected_pet = next(pet for pet in current_owner.pets if pet.name == selected_pet_name)
if st.session_state.get("rag_suggestion_pet") != selected_pet.name:
    st.session_state.rag_task_suggestions = None
    st.session_state.rag_suggestion_pet = selected_pet.name

st.markdown("### RAG care tips")
tips_result = get_care_tips(current_owner, selected_pet)
if tips_result.note:
    st.caption(tips_result.note)
if tips_result.tips:
    for tip in tips_result.tips:
        st.caption(f"- {tip.text[:220]}")
    tip_sources = sorted({tip.source for tip in tips_result.tips})
    if tip_sources:
        st.caption("Sources: " + ", ".join(tip_sources))
else:
    st.info("No knowledge tips were found for this pet yet.")

st.markdown("### RAG task suggestions")
st.caption("Generate grounded task suggestions and optionally apply them safely.")
if st.button("Generate RAG task suggestions"):
    st.session_state.rag_task_suggestions = suggest_tasks_with_rag(current_owner, selected_pet)

suggestion_result = st.session_state.rag_task_suggestions
if suggestion_result:
    if suggestion_result.note:
        st.caption(suggestion_result.note)
    suggestion_rows = [
        {
            "title": row.title,
            "duration_minutes": row.duration_minutes,
            "priority": row.priority,
            "recurrence": row.recurrence,
            "start_time": row.start_time or "Anytime",
            "confidence": round(row.confidence, 2),
            "rationale": row.rationale,
        }
        for row in suggestion_result.suggestions
    ]
    if suggestion_rows:
        st.table(suggestion_rows)
        if st.button("Apply suggested tasks"):
            try:
                applied, skipped = apply_suggested_tasks(selected_pet, suggestion_result.suggestions)
                st.session_state.last_schedule_result = None
                st.session_state.schedule_validation = None
                st.success(f"Applied {len(applied)} tasks, skipped {len(skipped)}.")
            except Exception as error:  # pragma: no cover - streamlit runtime guard
                st.error(_friendly_ai_error(error, "Apply suggested tasks"))
    if suggestion_result.citations:
        st.caption("Sources: " + ", ".join(suggestion_result.citations))

st.markdown("### Quick starter schedule")
st.caption(
    "Auto-create a profile-based daily routine from species, breed, and age."
)
if st.button("Auto-generate tasks from profile"):
    generated_titles = generate_profile_schedule_for_pet(current_owner, selected_pet)
    if generated_titles:
        st.success("Added starter tasks: " + ", ".join(generated_titles))
        st.session_state.last_schedule_result = None
        st.session_state.schedule_validation = None
    else:
        st.info("Starter tasks already exist for this pet.")

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
        st.session_state.last_schedule_result = None
        st.session_state.schedule_validation = None
    except ValueError as error:
        st.warning(str(error))

current_tasks = selected_pet.get_tasks()
if current_tasks:
    st.write(f"Current tasks for {selected_pet.name}:")
    # Table-like layout: consistent columns per row.
    header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns([3, 1, 1, 2, 1.7])
    with header_col1:
        st.caption("Title")
    with header_col2:
        st.caption("Duration")
    with header_col3:
        st.caption("Priority")
    with header_col4:
        st.caption("Recurrence | Start")
    with header_col5:
        st.caption("Action")
    for idx, task in enumerate(current_tasks):
        row_col1, row_col2, row_col3, row_col4, row_col5 = st.columns([3, 1, 1, 2, 1.7])
        with row_col1:
            st.caption(task.title)
        with row_col2:
            st.caption(f"{task.duration_minutes}m")
        with row_col3:
            st.caption(task.priority)
        with row_col4:
            # Format times in 12-hour AM/PM for the UI.
            start_display = (
                task.start_time.strftime("%I:%M %p").lstrip("0") if task.start_time else "Anytime"
            )
            st.caption(f"{task.recurrence} | {start_display}")
        with row_col5:
            if st.button(
                "Remove",
                key=f"remove-task-{selected_pet.name}-{idx}",
                use_container_width=True,
            ):
                try:
                    selected_pet.remove_task(task.title)
                    st.session_state.last_schedule_result = None
                    st.session_state.schedule_validation = None
                except Exception as error:  # pragma: no cover - streamlit runtime guard
                    st.error(_friendly_ai_error(error, "Remove task"))
else:
    st.info("No tasks yet. Add one above.")

st.subheader("Build Schedule")
st.caption("Generate a daily plan based on priorities, timing, and your available minutes.")

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
    return end_dt.strftime("%I:%M %p").lstrip("0")


def _format_time_12h(t: time) -> str:
    # Uses 12-hour clock display only; internal logic remains HH:MM.
    return t.strftime("%I:%M %p").lstrip("0")


if st.button("Generate schedule"):
    all_due_filtered = st.session_state.scheduler.filter_tasks(
        st.session_state.scheduler.expand_recurring_tasks(current_owner.get_all_tasks()),
        pet_name=selected_pet_filter,
        status=selected_status_filter,
    )

    sorted_filtered = st.session_state.scheduler.sort_tasks(all_due_filtered)
    conflicts = st.session_state.scheduler.detect_conflicts(sorted_filtered)
    st.session_state.last_schedule_result = {
        "sorted_filtered": sorted_filtered,
        "conflicts": conflicts,
        "pet_filter": selected_pet_filter,
        "status_filter": selected_status_filter,
    }

    plan = st.session_state.scheduler.generate_daily_plan(
        current_owner,
        pet_name=selected_pet_filter,
        status=selected_status_filter,
    )

    st.session_state.last_schedule_result["plan"] = plan
    st.session_state.last_schedule_result["stub_explanation"] = st.session_state.scheduler.explain_plan(plan)
    st.session_state.schedule_validation = validate_schedule_with_rag(current_owner, plan)

schedule_result = st.session_state.last_schedule_result
if schedule_result:
    sorted_filtered = schedule_result["sorted_filtered"]
    conflicts = schedule_result["conflicts"]
    plan = schedule_result["plan"]
    stub_explanation = schedule_result["stub_explanation"]

    st.success(f"Filtered tasks ready: {len(sorted_filtered)}")
    if sorted_filtered:
        st.write("Filtered + Sorted Task Preview")
        st.table(
            [
                {
                    "pet": task.pet_name or "Unknown",
                    "title": task.title,
                    "start_time": _format_time_12h(task.start_time) if task.start_time else "Anytime",
                    "end_time": _format_end_time(task),
                    "duration_minutes": task.duration_minutes,
                    "priority": task.priority,
                    "status": "completed" if task.is_completed else "incomplete",
                }
                for task in sorted_filtered
            ]
        )

    if conflicts:
        conflict_rows = [
            {
                "first_task": first.title,
                "first_window": (
                    f"{_format_time_12h(first.start_time)} - {_format_end_time(first)}"
                    if first.start_time
                    else "N/A"
                ),
                "second_task": second.title,
                "second_window": (
                    f"{_format_time_12h(second.start_time)} - {_format_end_time(second)}"
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
        # Conflict suggestions removed; user can adjust tasks manually.

    if not plan:
        st.warning("No tasks fit within the current schedule constraints.")
    else:
        st.success("Today's Schedule")
        st.table(
            [
                {
                    "pet": task.pet_name or "Unknown",
                    "title": task.title,
                    "start_time": _format_time_12h(task.start_time) if task.start_time else "Anytime",
                    "duration_minutes": task.duration_minutes,
                    "priority": task.priority,
                    "status": "completed" if task.is_completed else "incomplete",
                }
                for task in plan
            ]
        )
        try:
            agent_explanation = explain_plan_with_agent(current_owner, plan, scheduler_stub=stub_explanation)
            st.markdown("### Agent plan explanation")
            st.write(agent_explanation)
        except Exception as error:  # pragma: no cover - streamlit runtime guard
            st.warning(_friendly_ai_error(error, "Smart explanation"))
            st.caption(stub_explanation)
        with st.expander("Deterministic scheduler explanation"):
            st.caption(stub_explanation)

    validation = st.session_state.schedule_validation
    if validation:
        st.markdown("### RAG schedule validation")
        st.caption(
            f"Reliability score: {validation.reliability_score}/100 "
            f"({'LLM-assisted' if validation.used_llm else 'deterministic/retrieval fallback'})"
        )
        if validation.note:
            st.caption(validation.note)
        if validation.findings:
            st.table(
                [
                    {
                        "severity": finding.severity,
                        "category": finding.category,
                        "message": finding.message,
                        "source": finding.source,
                    }
                    for finding in validation.findings
                ]
            )
        else:
            st.caption("No issues detected by current validation checks.")
        if validation.bias_flags:
            st.caption("Bias/safety flags: " + ", ".join(validation.bias_flags))
        if validation.citations:
            st.caption("Sources: " + ", ".join(validation.citations))
