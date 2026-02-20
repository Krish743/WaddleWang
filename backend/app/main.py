"""PolicyAssist RAG API: document upload, question answering, summarization."""
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import get_settings
from app.document import load_document, chunk_documents
from app.vector_store import add_documents_to_store
from app.rag import answer_question, summarize_section


app = FastAPI(
    title="PolicyAssist",
    description="Intelligent Policy and FAQ Assistant – RAG over uploaded documents",
    version="0.2.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files at root (/)
_FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


# ---------------------------------------------------------------------------
# Routes defined BEFORE static mount so they take priority
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    """Serve the frontend UI at the root path."""
    index = _FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"service": "PolicyAssist", "docs": "/docs", "health": "/health"}



COLLECTION_NAME = "policy_docs"
ALLOWED_EXTENSIONS = {".pdf", ".txt"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Ensure all errors return JSON so the frontend can parse them."""
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "error": str(exc)},
    )


def get_uploads_dir() -> Path:
    s = get_settings()
    d = s.data_dir / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d



# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    question: str


class SourceCitation(BaseModel):
    """A single citation grounded in a retrieved document chunk."""
    page: int
    excerpt: str


class AskResponse(BaseModel):
    """Structured answer with document-grounded citations."""
    answer: str
    sources: list[SourceCitation]


class SummarizeRequest(BaseModel):
    section_text: str


class SummarizeResponse(BaseModel):
    summary: str


class UploadResponse(BaseModel):
    message: str
    file_id: str
    chunks_ingested: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/upload")
async def upload_get():
    """Use POST /upload with a file. See /docs."""
    return {"method": "POST", "description": "Upload a PDF or TXT file (multipart/form-data).", "docs": "/docs"}


@app.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload a policy document (PDF or TXT). It will be chunked and indexed for QA."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Allowed types: {', '.join(ALLOWED_EXTENSIONS)}. Got: {suffix or 'unknown'}",
        )

    file_id = str(uuid.uuid4())
    uploads_dir = get_uploads_dir()
    path = uploads_dir / f"{file_id}{suffix}"

    try:
        contents = await file.read()
        path.write_bytes(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}") from e

    try:
        docs = load_document(path)
        if not docs:
            raise HTTPException(status_code=400, detail="Document could not be parsed or is empty.")
        chunks = chunk_documents(docs)
        add_documents_to_store(chunks, collection_name=COLLECTION_NAME)
        return UploadResponse(
            message="Document uploaded and indexed successfully.",
            file_id=file_id,
            chunks_ingested=len(chunks),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}") from e


@app.get("/ask")
async def ask_get():
    """Use POST /ask with JSON body {\"question\": \"...\"}. See /docs."""
    return {"method": "POST", "description": "Send JSON: {\"question\": \"your question\"}.", "docs": "/docs"}


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    """Ask a question; answer is strictly grounded in uploaded policy documents.

    Response includes:
    - **answer**: LLM-generated answer referencing the document.
    - **sources**: list of ``{page, excerpt}`` citations built from retrieved chunks.

    If the document does not contain the answer, ``sources`` will be ``[]`` and
    ``answer`` will be ``"The document does not contain this information."``.
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    result = answer_question(req.question, collection_name=COLLECTION_NAME)
    return AskResponse(
        answer=result["answer"],
        sources=[SourceCitation(**s) for s in result["sources"]],
    )


@app.get("/summarize")
async def summarize_get():
    """Use POST /summarize with JSON body {\"section_text\": \"...\"}. See /docs."""
    return {"method": "POST", "description": "Send JSON: {\"section_text\": \"text to summarize\"}.", "docs": "/docs"}


@app.post("/summarize", response_model=SummarizeResponse)
async def summarize(req: SummarizeRequest):
    """Summarize a document section (e.g. paste a section or use retrieved chunk)."""
    summary = summarize_section(req.section_text)
    return SummarizeResponse(summary=summary)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "PolicyAssist"}


# Mount frontend directory last so API routes always take priority.
# CSS / JS requested by index.html are served from here.
if _FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR)), name="frontend")
