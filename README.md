# PRAGATI

A Telugu-first AI caseworker concept for helping rural women explore Telangana welfare schemes through voice. PRAGATI turns a caller’s message into a structured profile, retrieves relevant scheme information, and responds in Telugu.

## Live demo

The public Streamlit demo uses curated, deterministic cases so it stays free to operate and does not expose an API key. The full local pipeline supports:

`Telugu voice → speech-to-text → profile extraction → RAG retrieval → Telugu response → text-to-speech`

## Run the public demo locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Run the AI backend

```bash
pip install -r requirements-backend.txt
cp .env.example .env
# Add your OPENAI_API_KEY to .env
python ingest_schemas.py
uvicorn main:app --reload
```

In another terminal:

```bash
export PRAGATI_API_URL=http://localhost:8000
streamlit run app.py
```

## Stack

Streamlit, FastAPI, OpenAI speech and language models, ChromaDB, and SQLite.

> Prototype only—not an official government service or eligibility determination. Scheme rules can change; verify all guidance with the linked Telangana government source or MeeSeva.
