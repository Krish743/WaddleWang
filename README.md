# PolicyAssist – Intelligent Policy and FAQ Assistant

RAG app for **HTS'26 Gen AI Problem Statement 2**: upload policy/FAQ documents (PDF, TXT), ask questions, and get answers grounded in the uploaded content.

## Features

- **Document upload**: PDF and TXT; parsed, chunked, and embedded.
- **Question answering**: Semantic retrieval + LLM answers **only from document content** (source-aware).
- **Summarization**: Section-wise summaries (e.g. leave policy, attendance rules).
- **Vector search**: ChromaDB; configurable chunk size/overlap.

## Project structure

```
HackX/
├── .gitignore              # Ignores .venv, .env, backend/data, __pycache__, etc.
├── README.md
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py         # FastAPI app, /upload, /ask, /summarize
│   │   ├── config.py       # Settings (env)
│   │   ├── document.py      # Load PDF/TXT, chunk
│   │   ├── embeddings.py   # Hugging Face / OpenAI embeddings
│   │   ├── vector_store.py # ChromaDB
│   │   ├── llm.py          # LLM client (e.g. Groq)
│   │   └── rag.py          # QA and summarize chains
│   ├── data/               # Created at runtime (uploads, chroma) – gitignored
│   ├── requirements.txt
│   └── .env.example        # Copy to .env and fill in – .env is gitignored
└── frontend/
    ├── index.html
    ├── styles.css
    ├── app.js
    └── README.md
```

## Quick Start

### Step 1: Clone and navigate

```bash
cd HackX
cd backend
```

### Step 2: Create virtual environment

```bash
python -m venv .venv
```

**Activate venv:**

- **Windows (PowerShell):** `.\\.venv\\Scripts\\Activate.ps1`
- **Windows (cmd):** `.\\.venv\\Scripts\\activate.bat`
- **macOS/Linux:** `source .venv/bin/activate`

You should see `(.venv)` in your prompt.

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure environment variables

Copy the example file and add your API key:

```bash
copy .env.example .env
```

Edit `backend/.env` and set:

**For Groq (recommended):**
```env
API_KEY=gsk-your-groq-key-here
BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.1-70b-versatile
EMBEDDING_PROVIDER=huggingface
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

**For OpenAI:**
```env
API_KEY=sk-your-openai-key-here
LLM_MODEL=gpt-4o-mini
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_API_KEY=sk-your-openai-key-here
```

### Step 5: Run the backend

Make sure you're in `backend/` with venv activated:

```bash
uvicorn app.main:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### Step 6: Access the app

- **API Docs:** http://127.0.0.1:8000/docs
- **Basic UI:** http://127.0.0.1:8000/ui
- **Health Check:** http://127.0.0.1:8000/health

## Backend setup (detailed)

### Virtual environment

The venv is created inside `backend/` and is gitignored (`.venv/` won't be committed).

### Environment variables

The backend reads from `backend/.env`. Copy `backend/.env.example` to `backend/.env` and fill in your keys.

**Important:** Never commit `.env` (it's in `.gitignore`). Only commit `.env.example`.

### Running the API

Always run from `backend/` directory with venv activated:

```bash
cd backend
# Activate venv first
uvicorn app.main:app --reload
```

The `--reload` flag enables auto-reload on code changes (useful for development).

## Frontend (Basic UI)

The `frontend/` folder is a simple HTML/CSS/JS UI for testing (replace later with any framework).

- Served by the backend at **http://127.0.0.1:8000/ui** when the backend is running.
- Or open `frontend/index.html` in a browser, or run a local static server from `frontend/`.

See `frontend/README.md` for details.

## API overview

| Method | Endpoint    | Description |
|--------|-------------|-------------|
| POST   | `/upload`   | Upload PDF or TXT; chunks are embedded and stored. |
| POST   | `/ask`      | Body: `{"question": "..."}` → answer from document context. |
| POST   | `/summarize`| Body: `{"section_text": "..."}` → concise summary. |
| GET    | `/health`   | Health check. |

## Workflow

1. User uploads a policy document → backend chunks and embeds it.
2. Embeddings are stored in ChromaDB.
3. User asks a question → semantic search retrieves relevant chunks.
4. Chunks are sent to the LLM with a strict “answer only from context” prompt.
5. Answer (or “not in document”) is returned.

## Git / .gitignore

The root `.gitignore` excludes:

- Virtual envs: `.venv/`, `venv/`, `backend/.venv/`, etc.
- Secrets: `.env`
- Python: `__pycache__/`, `*.pyc`
- Backend data: `backend/data/`, `data/`
- IDE/OS: `.idea/`, `.vscode/`, `.DS_Store`

Create `.env` from `backend/.env.example`; do not commit `.env`.
