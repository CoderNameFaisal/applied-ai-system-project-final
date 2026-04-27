# PawPal+

PawPal+ is a Streamlit app that helps a pet owner build a realistic daily care schedule. It combines deterministic scheduling rules with optional AI features:

- Agentic explanation for generated plans.
- RAG-backed natural language intake that can update preferences and add tasks.
- RAG-backed conflict resolution suggestions for overlapping timed tasks.

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
│       ├── rag_intake.py
│       └── conflict_rag.py
└── tests/
    ├── test_pawpal.py
    └── test_ai_features.py
```

## What the app does

- Captures owner constraints and pet profiles (species, breed, age, optional habits).
- Lets users create and manage care tasks with duration, priority, recurrence, and optional start time.
- Generates daily plans with filtering, sorting, conflict checks, and time-budget enforcement.
- Uses AI to explain plans in context of the active owner and pets.
- Uses RAG to turn natural-language requests into real task/preference updates.
- Uses RAG to suggest conflict time moves and apply those changes directly in app state.

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

Copy `.env.example` to `.env` and set your key:

```bash
cp .env.example .env
```

Required:

- `OPENAI_API_KEY`

Optional:

- `OPENAI_MODEL` (default: `gpt-4.1-mini`)
- `OPENAI_EMBEDDING_MODEL` (default: `text-embedding-3-small`)
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

The app still runs without an API key for deterministic scheduling, but AI sections are disabled with clear guardrail messages.

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
