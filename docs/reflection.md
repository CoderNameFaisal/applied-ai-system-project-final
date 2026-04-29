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

---

## 6. AI Responsibility and Ethics

**a. What are the limitations or biases in your system?**

PawPal+ uses the Gemini API to give scheduling suggestions. This means the system has real problems that I need to be honest about:

1. **Bias from Training Data**: The AI learned from stuff on the internet. More common pet types (dogs, cats) probably get better advice than rare or exotic pets. Advice that works for most dogs might be wrong for a specific dog.

2. **One-Size-Fits-All Advice**: The system doesn't know if a pet is young or old, has health problems, allergies, or takes medicine. A suggestion that "grooming takes 30 minutes" might be way too long for a nervous dog that needs calm preparation.

3. **No Real Veterinary Information**: The AI can't access up-to-date vet guidelines. If new safety concerns come out about a food type, the AI might not know.

4. **Basic Keyword Matching Falls Back**: When the vector database failed, the system fell back to simple keyword matching in local knowledge files. Sometimes this finds relevant results by accident rather than real understanding.

**b. Could your AI be misused, and how would you prevent that?**

Yes, there are real risks:

**Risk 1: Bad Health Advice**
- *What could go wrong*: An owner follows AI suggestions that hurt their pet (wrong food, wrong medicine timing).
- *How to prevent it*:
  - The app says "suggestions only" not "medical advice"—clear warning on the screen.
  - Pop-up message: "Always talk to your vet before changing your pet's food or medicine."
  - Tests check that suggestions only come from safe, local knowledge files.
  - When the API is down, the system uses our known-safe local knowledge base, not guesses.

**Risk 2: Owner Ignores Real Problems**
- *What could go wrong*: Owner trusts the AI schedule without thinking, misses that a pet is stressed or sick.
- *How to prevent it*:
  - Every plan shows why it was created ("prioritizing high-need tasks that fit in 2 hours").
  - Owner has to click "apply" before anything changes—system doesn't auto-apply.
  - The scheduler enforces a time limit so owners can't schedule impossible days.

**Risk 3: False Trust in the System**
- *What could go wrong*: Owner thinks the AI knows everything about their pet and stops paying attention to their pet's signals.
- *How to prevent it*:
  - System is designed to suggest, not decide. Owner always has the final say.
  - When tests run, they show that the system only suggests what's in our safe local knowledge.

**c. What surprised you while testing AI's reliability?**

1. **Silent Failures Hurt More Than Loud Failures**: At first, when API keys expired, the system would quietly keep trying instead of giving up. That made owners think it was working when it wasn't. Once I made the system immediately reject bad auth errors, failures became clear and honest. Frustrating but better.

2. **Embedding Models Just Weren't There**: I expected certain AI models to exist for text embedding (converting words to numbers). They didn't. But I found out that simple keyword matching from local files worked surprisingly well and was actually more transparent to the user.

3. **Fake Testing Is Better Than Real API Calls**: I thought real tests that call the actual API would be more thorough. They weren't—they were slow and broke when the API changed. Fake tests (where I make up responses) were faster and forced me to think about what the system should do if the API fails. That turned out to be important.

4. **Systems Work Better Without Complexity**: A simple system that gracefully falls back when things fail is better than a fancy system that breaks when one thing goes wrong.

**d. Describe your collaboration with AI during this project. One helpful instance and one flawed instance.**

**A Time the AI Helped**:
I asked the AI how to test the system without making real API calls. The AI suggested using a Python feature called `monkeypatch` to replace real functions with fake ones that return test data. This let my tests run in 0.1 seconds instead of 5 seconds, and tests didn't break when the API changed. The suggestion also showed how to structure fake data so it matched what the real API returns. This was genuinely smart.

**A Time the AI Was Wrong**:
Early on, I asked the AI about error handling. It suggested I build something called "exponential backoff with circuit breaker patterns"—basically: if something fails, wait longer before retrying, and if it keeps failing, give up entirely. This is what big tech companies do. But for my project, it was overkill. The real answer was simpler: *if the API says the auth key is bad (error 401), fail immediately instead of waiting*. I had to tell the AI: "Stop. I don't need production-grade complexity. I need the simple solution." Once I was clear about that, the AI helped me do it right.

**The Main Thing I Learned About Working With AI**:
The AI is best when I give it clear constraints. Vague requests produce over-engineered answers. Specific requests ("test without real API calls" or "fast-fail for permanent errors") produce elegant solutions.
