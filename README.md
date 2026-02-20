# PolicyAssist – Intelligent Policy and FAQ Assistant

RAG backend for the **HTS'26 Gen AI Problem Statement 2**: upload policy/FAQ documents (PDF, TXT), ask questions, and get answers grounded in the uploaded content.

## Features

- **Document upload**: PDF and TXT supported; parsed, chunked, and embedded.
- **Question answering**: Semantic retrieval + LLM answers **only from document content** (source-aware).
- **Summarization**: Section-wise summaries (e.g. leave policy, attendance rules).
- **Vector search**: ChromaDB for local persistence; configurable chunk size/overlap.

## Backend setup

### 1. Environment

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate   # macOS/Linux
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API keys

Copy the example env file and set your LLM/embedding API key:

```bash
copy .env.example .env
# Edit .env and set your API key
```

**For OpenAI:**
```env
API_KEY=sk-your-openai-key
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
```

**For Groq (fast inference with open-source models):**
```env
API_KEY=gsk-your-groq-key
BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.1-70b-versatile

# Embeddings - Use Hugging Face (recommended, free, no API key)
EMBEDDING_PROVIDER=huggingface
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

**Popular Groq models:** `llama-3.1-70b-versatile`, `mixtral-8x7b-32768`, `llama-3.1-8b-instant`

**Popular Hugging Face embedding models:**
- `sentence-transformers/all-MiniLM-L6-v2` (fast, 384 dimensions)
- `sentence-transformers/all-mpnet-base-v2` (better quality, 768 dimensions)
- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (multilingual)

**Using OpenAI embeddings (alternative):**
```env
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_API_KEY=sk-your-openai-key
```

Optional: `CHUNK_SIZE`, `CHUNK_OVERLAP` for document chunking.

### 4. Run the API

```bash
uvicorn app.main:app --reload
```

- API: **http://127.0.0.1:8000**
- Docs: **http://127.0.0.1:8000/docs**
- Basic UI: **http://127.0.0.1:8000/ui** (if frontend is mounted)

## Frontend (Basic UI)

A simple HTML/CSS/JS UI is included in `frontend/` for testing. It's designed to be easily replaced with React, Vue, Next.js, etc.

**To use the basic UI:**
- The backend automatically serves it at `/ui` if the `frontend/` folder exists
- Or open `frontend/index.html` directly in a browser (may need CORS workaround)
- Or serve with: `python -m http.server 8080` from the `frontend/` directory

See `frontend/README.md` for details.

## API overview

| Method | Endpoint    | Description |
|--------|-------------|-------------|
| POST   | `/upload`   | Upload a PDF or TXT file; chunks are embedded and stored. |
| POST   | `/ask`      | Body: `{"question": "..."}` → answer from document context. |
| POST   | `/summarize`| Body: `{"section_text": "..."}` → concise summary. |
| GET    | `/health`   | Health check. |

## Project structure

```
backend/
  app/
    main.py         # FastAPI app, /upload, /ask, /summarize
    config.py       # Settings (env)
    document.py     # Load PDF/TXT, chunk
    embeddings.py   # Embedding client
    vector_store.py # ChromaDB add/search
    llm.py          # LLM client
    rag.py          # QA and summarize prompts + chains
  data/             # Created at runtime (uploads, chroma)
  requirements.txt
  .env.example

frontend/           # Basic UI (replace with proper frontend)
  index.html
  styles.css
  app.js
  README.md
```

## Workflow (as per problem statement)

1. User uploads a policy document → backend processes and chunks it.
2. Embeddings are generated and stored in ChromaDB.
3. User asks a question → semantic search retrieves relevant chunks.
4. Chunks are passed to the LLM with a strict “answer only from context” prompt.
5. Answer (or “not in document”) is returned.

You can now build a frontend that calls `/upload` and `/ask` (and optionally `/summarize`) to complete PolicyAssist.
