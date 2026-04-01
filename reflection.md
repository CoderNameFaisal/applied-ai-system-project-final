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
- If yes, describe at least one change and why you made it.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
A: One tradeoff is that conflict detection only compares neighboring timed tasks after sorting by start time, and untimed tasks are treated as flexible. This keeps the algorithm simple and fast for daily planning, but it does not model deeper constraints like travel time, owner energy, or pet-specific cooldown windows.
- Why is that tradeoff reasonable for this scenario?
A: This tradeoff is reasonable for the project scope because the goal is a readable and testable scheduling baseline. Adjacent-overlap checks catch the most common real conflicts with low complexity, which makes the behavior easier to explain in both the app UI and tests.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
