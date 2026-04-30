# PawPal+ (AI-Enhanced Pet Care Planner)

## Original Project (Modules 1-3)
My original project from Modules 1-3 was **PawPal**, a deterministic pet-care scheduler. The goal was to help owners plan daily tasks (feeding, walks, medication, play) without overloading their available time. It already handled recurring tasks, priorities, and conflict checks, but it did not have retrieval or AI-assisted reasoning.

## Title and Summary
**PawPal+** is a Streamlit app that combines rule-based scheduling with retrieval-augmented AI features. It matters because pet owners need plans that are both realistic and explainable, not just random suggestions. The system can still function when AI services fail by falling back to local retrieval and deterministic scheduling.

## Project Video (Loom)
Loom walkthrough: [Watch the project demonstration](https://www.loom.com/share/2bbcbb2756b34c80a58f2163775ce1c2)


## Architecture Overview
The final UML diagram is in `docs/Mermaid.txt`.

High-level flow:
- Input: Owner profile, pet profile (species, breed, age), and care goals.
- Process: Scheduler builds a base plan, retriever pulls supporting care knowledge, and AI modules generate explanations/suggestions/validation.
- Output: A daily care plan with optional grounded AI guidance.
- Human/Test checkpoints: User reviews outputs in the UI; automated tests validate scheduler logic, retrieval fallback behavior, and API retry/auth handling.

Main components:
- `Scheduler`: deterministic plan creation and conflict handling.
- `RAGUtils` + `VectorStore`: retrieval pipeline (vector retrieval with lexical fallback).
- `AIClient`: provider calls with retries and auth error handling.
- AI modules: plan explainer, task suggestion agent, schedule validator.
- `PytestSuite`: regression checks for both deterministic and AI-assisted paths.

## Setup Instructions
1. Clone the repository and move into the project folder.
2. Create and activate a virtual environment.
3. Install dependencies.
4. Configure environment variables.
5. Optionally build the vector index.
6. Run the app.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set environment values in `.env`:
- `AI_PROVIDER=gemini` (or `openai`)
- `GEMINI_API_KEY=...` (if using Gemini)
- `OPENAI_API_KEY=...` (if using OpenAI)
- `AI_MODEL=gemini-2.0-flash`
- `AI_EMBEDDING_MODEL=...`

Optional vector ingest (only if embeddings are available):

```bash
PYTHONPATH=. python3 scripts/ingest_rag.py
```

Run app:

```bash
streamlit run app.py
```

## Run Tests

To run tests with pytest:

```bash
python3 -m pytest tests
```

Run tests in quiet mode (less output):

```bash
python3 -m pytest -q tests
```

Run only scheduler tests:

```bash
python3 -m pytest tests/test_pawpal.py
```

Run only RAG feature tests:

```bash
python3 -m pytest tests/test_ai_features.py tests/test_rag_features.py
```

Run with verbose output to see each test:

```bash
python3 -m pytest -v tests
```

## Sample Interactions
These examples show actual behavior patterns in the current system.

Example 1: RAG intake action application
- Input:
    - "Add daily evening walk and update preferences."
- AI output (grounded action style):
    - Explanation: "Applied grounded updates."
    - Actions:
        - set owner preferences to "Morning walks first"
        - add task "Evening walk", 15 min, high priority, daily, 18:00
- Result:
    - Owner preferences updated.
    - New task appears under the selected pet.

Example 2: Retrieval fallback when vector service is unavailable
- Input:
    - "How should I adjust care for species, breed, age, and habits?"
- System output:
    - "Vector retrieval unavailable; using local lexical fallback."
    - Returns grounded snippets from local knowledge files.
- Result:
    - App still returns useful guidance instead of crashing.

Example 3: Schedule validation with reliability score
- Input:
    - A generated daily plan with multiple pet tasks.
- AI output:
    - Validation summary + reliability score + citations from knowledge context.
- Result:
    - User can keep the plan, edit tasks, or regenerate based on feedback.

## Design Decisions and Trade-Offs
- Decision: Keep a deterministic scheduler as the core engine.
    - Why: predictable, testable, safe baseline behavior.
    - Trade-off: less flexible than pure LLM planning for unusual edge cases.

- Decision: Use retrieval-augmented features instead of free-form generation.
    - Why: better grounding and fewer hallucinations.
    - Trade-off: answers are limited to what is in local knowledge docs.

- Decision: Add lexical fallback when vector retrieval fails.
    - Why: reliability during API outages, key issues, or model availability issues.
    - Trade-off: lexical matching is weaker than embeddings for semantic similarity.

- Decision: Fast-fail on non-retryable auth errors.
    - Why: avoid wasting time on repeated failing calls and give clear logs.
    - Trade-off: stricter behavior means misconfigured keys surface immediately.

## Testing Summary
What worked:
- Deterministic scheduling tests passed.
- AI feature tests using mocks passed.
- New AI client tests confirmed retry behavior and auth fast-fail behavior.

What did not work smoothly:
- Embedding ingestion failed during provider/model issues.

What I learned:
- Reliability work (fallbacks, better logs, tests) matters as much as model quality.
- If setup is unclear, even good code looks broken.
- Guardrails and failure paths should be designed early, not as an afterthought.

## Reflection

**What I Learned About AI and Responsibility**

This project taught me that AI works best as a helper, not as magic. I used AI to write faster, understand hard parts of the code, and think through better ways to handle failures. But I had to check everything myself to make sure it actually worked. The project was frustrating at times—especially dealing with API keys breaking, services going down, and models disappearing. That frustration taught me something important: build fallbacks, write tests for when things fail, and make sure the system still works when external services go down.

**System Limitations and Biases**

PawPal+ uses the Gemini AI to give care suggestions. This has real limitations:
- The AI doesn't know each individual pet's health, age, allergies, or medicine needs.
- Suggested task times are based on general internet data, not your specific pet or home.
- Vet guidance can go out of date if the AI's training data is old.
- When the embedding models weren't available, the system fell back to simple keyword matching—which sometimes worked by accident rather than real understanding.

**Preventing Misuse**

The system is made to suggest, not to make decisions:
- Every plan shows the reasoning so owners can review it before applying.
- The scheduler enforces a time limit to prevent owners from scheduling impossible days.
- The app says: "Always talk to your veterinarian before changing your pet's food or medicine."
- When the API is down, the system uses our safe local knowledge files instead of guessing.
- Tests verify that suggestions only come from safe, known sources.

**Surprises While Testing**

1. **Silent failures are bad**: When API keys expired, the system would quietly keep trying instead of giving up. Once I made it immediately reject bad auth errors, failures became honest and clear.

2. **Expected AI models didn't exist**: I thought certain text-embedding models would work. They didn't. Simple keyword matching from local files turned out to work surprisingly well and was more transparent to users.

3. **Fake tests are better than real ones**: I thought testing with real API calls would be better. It wasn't—they were slow and broke when the API changed. Fake tests (where I make up responses) let me test what happens when APIs fail, which was actually important.

**AI as a Collaborator: One Good, One Bad**

*A helpful suggestion*: When I asked how to test without real API calls, the AI suggested using Python's `monkeypatch` feature to replace real functions with fake ones. This made tests run 50x faster and forced me to think about what happens when the API breaks. The suggestion even showed how to structure fake data to match real responses—this reduced test bugs.

*A bad suggestion*: Early on, I asked about error handling. The AI suggested building "exponential backoff with circuit breaker patterns"—basically: retry with longer and longer waits, and give up if it keeps failing. This is what big tech companies do, but my project didn't need it. The real answer was simpler: *if the API says the key is bad (error 401), fail immediately*. I had to tell the AI: "Stop over-engineering this." Once I was clear about that, it helped me do it right.

**The Main Thing I Learned**:
Clear constraints make AI suggestions better. Vague requests produce over-engineered answers. Specific requests ("make tests fast" or "fail immediately on bad auth") produce simple, elegant solutions.

For more details, see [docs/reflection.md](docs/reflection.md).

## Assets
- UML source: `docs/Mermaid.txt`
- Architecture image: `assets/architecture/uml_final.png`
- App screenshot: `assets/screenshots/pawpalplus.png`
