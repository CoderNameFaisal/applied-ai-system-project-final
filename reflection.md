# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
A: My initial UML design focused on a simple domain model with clear responsibilities and relationships. I modeled one owner who can manage one or many pets (one-to-many), and each pet can have zero or many care tasks (one-to-many). The scheduler is a service-style class that reads owner constraints and pet tasks, then generates an ordered daily plan based on priority and available time. I kept the design intentionally lightweight so the core scheduling logic stayed easy to test and explain.

- What classes did you include, and what responsibilities did you assign to each?
A: I included four main classes in my initial design:
   - `Owner`: stores owner profile details and preferences, such as available time and care priorities.
   - `Pet`: stores pet details (name, species, basic needs) and links the pet to its care tasks.
   - `CareTask`: represents one care activity with fields like title, duration, priority, and optional recurrence settings.
   - `Scheduler`: takes the task list and constraints, sorts/selects tasks for the day, and returns the final ordered plan with brief reasoning.

**b. Design changes**

- Did your design change during implementation?
A: Yes. The design evolved from a simple static task list into a date-aware scheduling model that supports recurrence, completion state, and conflict handling.
- If yes, describe at least one change and why you made it.
A: A major change was adding `start_date`, `start_time`, and recurrence behavior directly to `CareTask`, plus completion rollover for daily/weekly tasks in `Pet.mark_task_complete`. I made this change so the app could represent real recurring care behavior instead of repeatedly editing one task by hand. I also added filtering by pet and status in `Scheduler.filter_tasks` to support focused planning views in the Streamlit UI.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
A: The scheduler considers (1) owner time budget (`available_minutes_per_day`), (2) task due state for the selected date (`is_due_on` with `none`/`daily`/`weekly` recurrence), (3) selected pet filter, (4) selected status filter (`due`, `incomplete`, `completed`), (5) task priority (`high`, `medium`, `low`), and (6) timed-task overlap conflicts. It then keeps only non-conflicting tasks that fit within the available minutes.
- How did you decide which constraints mattered most?
A: I prioritized constraints by practical impact on daily usability: first eligibility (due date/status/pet filter), then ordering (start time first, then priority), then feasibility (no overlap, fit in time budget). This sequence mirrors how a real owner thinks: “What must be done today?”, “When should I do it?”, and “What can actually fit?”

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
A: One tradeoff is that conflict detection only compares neighboring timed tasks after sorting by start time, and untimed tasks are treated as flexible. This keeps the algorithm simple and fast for daily planning, but it does not model deeper constraints like travel time, owner energy, or pet-specific cooldown windows.
- Why is that tradeoff reasonable for this scenario?
A: This tradeoff is reasonable for the project scope because the goal is a readable and testable scheduling baseline. Adjacent-overlap checks catch the most common real conflicts with low complexity, which makes the behavior easier to explain in both the app UI and tests.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
A: I used AI for design brainstorming (class boundaries and method responsibilities), implementation scaffolding (clear docstrings and validation patterns), and test expansion (recurrence, conflict detection, and completion rollover cases). I also used AI feedback to improve readability in the Streamlit flow and keep method responsibilities separated across `Pet`, `Owner`, and `Scheduler`.
- What kinds of prompts or questions were most helpful?
A: The most helpful prompts were direct tasks that left no room for ambiguity, as "update the state of owner such that changes to the owner's name is reflected. These prompts produced actionable code.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
A: I did not accept suggestions that overcomplicated scheduling with advanced optimization (for example, adding weighted scoring or complex route-style constraints) because that would reduce clarity for this module’s scope.
- How did you evaluate or verify what the AI suggested?
A: I checked each suggestion against project requirements, then validated behavior with focused pytest cases (sorting by time, recurrence expansion, conflict detection, and next-instance creation for daily/weekly tasks). If a suggestion made the code harder to explain or test, I simplified it before adopting it.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
A: I tested task completion state updates, adding tasks to pets, sorting by start time (with untimed tasks last), filtering by pet and status, recurrence expansion for daily/weekly tasks, overlap conflict detection (including exact same start time), recurring-task rollover when marking complete, and empty-plan behavior when no tasks are available.
- Why were these tests important?
A: These tests cover the highest-risk scheduling paths: ordering correctness, due-date correctness, recurrence correctness, and conflict correctness. Together they protect core planner behavior so UI changes are less likely to break schedule logic.

**b. Confidence**

- How confident are you that your scheduler works correctly?
A: I am moderately to highly confident for the current scope. Core behavior is covered by targeted unit tests and matches what the Streamlit app demonstrates during interactive use.
- What edge cases would you test next if you had more time?
A: Next I would test boundary and data-quality cases: midnight-adjacent times, very large task lists, mixed timed/untimed conflicts across many pets, duplicate task titles on the same pet, timezone/date rollover behavior, and more detailed recurrence rules (for example, specific weekdays rather than only weekly-by-start-day).

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?
A: I am most satisfied with the separation of concerns: domain modeling in `CareTask`/`Pet`/`Owner`, orchestration in `Scheduler`, and presentation in Streamlit. That structure made testing straightforward and kept feature growth manageable.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?
A: I would redesign task identity and persistence by adding unique IDs and storage-backed state (instead of session-only memory), then improve scheduling with richer constraints like soft preferences, blocked times, and optional reminders.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
A: I learned that AI is most valuable when I treat it as a collaborator for iteration, not as an autopilot. The best results came from combining AI-generated ideas with clear constraints, small testable steps, and human judgment about simplicity versus complexity.
