# PawPal+

PawPal+ is a Streamlit app that helps a pet owner build a realistic daily care schedule. It combines deterministic scheduling rules with optional AI features:

- Agentic explanation for generated plans.
- Retrieval-only RAG care tips grounded in local knowledge files.
- RAG task suggestions with safe one-click apply and fallback behavior.
- RAG schedule validation with reliability scoring and citations.

## Project structure

```text
.
├── app.py
├── main.py
├── requirements.txt
├── README.md
├── .env.example
├── assets/
│   ├── architecture/
│   └── screenshots/
├── docs/
├── knowledge/                 # Committed RAG source documents
├── scripts/
│   └── ingest_rag.py          # Builds local Chroma index
├── pawpal/
│   ├── __init__.py
│   ├── system.py
│   ├── config.py
│   ├── logging_utils.py
│   └── ai/
│       ├── client.py
│       ├── vectorstore.py
│       ├── plan_explainer.py
│       ├── rag_utils.py
│       ├── rag_tips.py
│       ├── rag_task_suggestions.py
│       └── rag_schedule_validator.py
└── tests/
    ├── test_pawpal.py
    └── test_ai_features.py
```

## What the app does

- Captures owner constraints and pet profiles (species, breed, age).
- Lets users create and manage care tasks with duration, priority, recurrence, and optional start time.
- Generates daily plans with filtering, sorting, conflict checks, and time-budget enforcement.
- Uses AI to explain plans in context of the active owner and pets.
- Auto-generates starter tasks from pet profile (species, breed, age) and applies owner time preferences.
- Shows retrieval-only RAG care tips for the selected pet with source citations.
- Generates RAG-backed task suggestions and supports validated one-click apply.
- Validates generated schedules with RAG context and a reliability score.

## Setup (reproducible)

### 1) Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Configure environment

Copy `.env.example` to `.env` and optionally set your key:

```bash
cp .env.example .env
```

Optional:

- `GEMINI_API_KEY` (enables LLM-enhanced explanation/suggestions/validation)
- `AI_PROVIDER` (`gemini` default, `openai` also supported)
- `AI_MODEL` (default: `gemini-2.0-flash`)
- `AI_EMBEDDING_MODEL` (default: `text-embedding-004`)
- `PAWPAL_LOG_LEVEL` (default: `INFO`)

### 4) Build the local RAG index

Run once after setup, and whenever files in `knowledge/` change:

```bash
python scripts/ingest_rag.py
```

This writes the local vector index under `data/chroma/` (ignored by git).

## Run the app

```bash
streamlit run app.py
```

The app runs without an API key using deterministic scheduling and retrieval fallbacks; LLM-enhanced sections degrade gracefully when unavailable.

## Run tests

```bash
python -m pytest
```

- Core scheduler tests are deterministic.
- AI tests use mocks and do not call external APIs.

## Logging and guardrails

- AI paths use bounded retries and timeout-backed OpenAI client calls.
- Agent loops are turn-limited to prevent runaway behavior.
- Domain mutations from AI output only happen through validated `Owner`, `Pet`, and `CareTask` methods.
- App-level fallbacks keep deterministic schedule functionality available if AI is unavailable.

## Assets

- UML diagram: `assets/architecture/uml_final.png`
- App screenshot: `assets/screenshots/pawpalplus.png`
