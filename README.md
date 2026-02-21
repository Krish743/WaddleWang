# PolicyAssist – Policy Intelligence System

AI-powered policy assistant for **HTS'26 Gen AI Problem Statement 2**. Upload HR/company policy documents (PDF, TXT), ask grounded questions, run compliance checks, and auto-generate section summaries.

---

## Features

| Feature | Description |
|---|---|
| 📄 **Document Upload** | PDF and TXT; parsed, chunked, table-extracted, and embedded into ChromaDB |
| ❓ **Ask a Question** | Semantic retrieval + strict LLM grounding — answers cite exact clauses and page numbers |
| ⚖️ **Compliance Check** | Describe a workplace scenario; get a policy-grounded compliance verdict with citations |
| 📑 **Sections** | Auto-detects headings (numbered, ALL CAPS, Title Case) and generates per-section summaries |
| 🔍 **Gap Detection** | Flags when a question has no answer in the uploaded documents and suggests what policy is missing |

---

## Project Structure

```
HackX/
├── .env                        # API keys (gitignored – copy from .env.example)
├── .gitignore
├── README.md
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI app – all endpoints
│   │   ├── config.py           # Settings loaded from .env
│   │   ├── document.py         # PDF/TXT loading, chunking
│   │   ├── embeddings.py       # HuggingFace / OpenAI embedding models
│   │   ├── llm.py              # LLM client (Groq / OpenAI-compatible)
│   │   ├── rag.py              # Grounded Q&A and compliance chains + gap detection
│   │   ├── classifier.py       # Query-type classifier (factual, numeric, procedural…)
│   │   ├── sections.py         # Heading detection & LLM section summarization
│   │   ├── table_parser.py     # pdfplumber table extraction → indexable chunks
│   │   ├── diff.py             # Semantic document diff (isolated Chroma collections)
│   │   └── vector_store.py     # ChromaDB helpers (add, search, score)
│   ├── data/                   # Runtime data – gitignored
│   │   ├── chroma/             # ChromaDB persistence
│   │   ├── uploads/            # Uploaded files
│   │   └── sections/           # Cached section JSON per file_id
│   └── requirements.txt
│
└── frontend/
    ├── index.html              # Single-page app shell + tab panels
    ├── styles.css              # Dark-theme design system
    └── app.js                  # All API calls, tab navigation, UI logic
```

---

## Quick Start

### 1. Clone and enter backend

```bash
git clone https://github.com/Krish743/WaddleWang.git
cd WaddleWang/backend
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
```

- **Windows (PowerShell):** `.\venv\Scripts\Activate.ps1`
- **Windows (cmd):** `.\venv\Scripts\activate.bat`
- **macOS / Linux:** `source venv/bin/activate`

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file at the project root (or inside `backend/`) and add:

```env
# LLM – Groq (recommended)
API_KEY=gsk-your-groq-key-here
BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.1-70b-versatile

# Embeddings – HuggingFace (free, runs locally)
EMBEDDING_PROVIDER=huggingface
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

> **OpenAI alternative:**
> ```env
> API_KEY=sk-your-openai-key-here
> LLM_MODEL=gpt-4o-mini
> EMBEDDING_PROVIDER=openai
> EMBEDDING_MODEL=text-embedding-3-small
> EMBEDDING_API_KEY=sk-your-openai-key-here
> ```

### 5. Run the backend

```bash
cd backend
uvicorn app.main:app --reload
```

Expect:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### 6. Open the app

Navigate to **http://127.0.0.1:8000** — the backend serves the frontend automatically.

| URL | Purpose |
|---|---|
| http://127.0.0.1:8000 | Full web UI |
| http://127.0.0.1:8000/docs | Interactive API docs (Swagger) |
| http://127.0.0.1:8000/health | Health check |

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/upload` | Upload PDF or TXT (`multipart/form-data`). Optional `?collection_name=` for isolated indexing. Returns `file_id`, chunk/table/section counts. |
| `POST` | `/ask` | `{"question": "..."}` → grounded answer with page citations and gap detection. |
| `POST` | `/analyze_scenario` | `{"scenario": "..."}` → compliance verdict with citations and gap detection. |
| `GET`  | `/sections` | Returns auto-detected section summaries from all uploaded documents. |
| `POST` | `/summarize` | `{"section_text": "..."}` → concise LLM summary. |
| `GET`  | `/health` | `{"status": "ok"}` |

---

## How It Works

```
Upload → parse → chunk → embed → ChromaDB
                                    │
Ask / Compliance ──────────────────►│ semantic search (top-k chunks)
                                    │
                              LLM (strict grounded prompt)
                                    │
                         answer + page citations + gap flag
```

1. **Upload**: document is split into overlapping chunks; tables extracted separately; section headings detected and summarised by LLM; all stored in `policy_docs` Chroma collection.
2. **Ask**: query is classified (factual / numeric / procedural / comparative), top-k chunks retrieved with relevance scores, passed to LLM with a strict system prompt that forbids fabrication and preamble phrases.
3. **Compliance**: same retrieval pipeline, different system prompt focused on policy outcomes and compliance verdicts.
4. **Sections**: heading detection uses 3 patterns (numbered `1.`, ALL CAPS, Title Case); page numbers are 1-indexed; each section is summarised by LLM and cached to `data/sections/<file_id>.json`.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI + Uvicorn |
| LLM | Groq (llama-3.1-70b) / any OpenAI-compatible API |
| Embeddings | HuggingFace `all-MiniLM-L6-v2` (local) or OpenAI |
| Vector store | ChromaDB (disk-persisted) |
| Document parsing | LangChain + PyPDF + pdfplumber |
| Frontend | Vanilla HTML / CSS / JavaScript (dark theme SPA) |

---

## .gitignore Highlights

The following are **not** committed:
- `venv/`, `.venv/` — virtual environments
- `.env` — secrets (use `.env.example` as template)
- `backend/data/` — ChromaDB, uploads, section cache
- `__pycache__/`, `*.pyc`
