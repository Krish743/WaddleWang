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

Copy the example env file and set your LLM/embedding API key (OpenAI or any OpenAI-compatible provider):

```bash
copy .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...
```

Optional: `OPENAI_BASE_URL` for Azure or other endpoints; `LLM_MODEL`, `EMBEDDING_MODEL`, `CHUNK_SIZE`, `CHUNK_OVERLAP`.

### 4. Run the API

```bash
uvicorn app.main:app --reload
```

- API: **http://127.0.0.1:8000**
- Docs: **http://127.0.0.1:8000/docs**

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
```

## Workflow (as per problem statement)

1. User uploads a policy document → backend processes and chunks it.
2. Embeddings are generated and stored in ChromaDB.
3. User asks a question → semantic search retrieves relevant chunks.
4. Chunks are passed to the LLM with a strict “answer only from context” prompt.
5. Answer (or “not in document”) is returned.

You can now build a frontend that calls `/upload` and `/ask` (and optionally `/summarize`) to complete PolicyAssist.
