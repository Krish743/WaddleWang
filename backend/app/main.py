"""PolicyAssist RAG API: document upload, question answering, summarization."""
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.config import get_settings
from app.document import load_document, chunk_documents
from app.vector_store import add_documents_to_store
from app.rag import answer_question, summarize_section


app = FastAPI(
    title="PolicyAssist",
    description="Intelligent Policy and FAQ Assistant – RAG over uploaded documents",
    version="0.1.0",
)

COLLECTION_NAME = "policy_docs"
ALLOWED_EXTENSIONS = {".pdf", ".txt"}


def get_uploads_dir() -> Path:
    s = get_settings()
    d = s.data_dir / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str


class SummarizeRequest(BaseModel):
    section_text: str


class SummarizeResponse(BaseModel):
    summary: str


class UploadResponse(BaseModel):
    message: str
    file_id: str
    chunks_ingested: int


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


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    """Ask a question; answer is grounded in uploaded policy documents."""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    answer = answer_question(req.question, collection_name=COLLECTION_NAME)
    return AskResponse(answer=answer)


@app.post("/summarize", response_model=SummarizeResponse)
async def summarize(req: SummarizeRequest):
    """Summarize a document section (e.g. paste a section or use retrieved chunk)."""
    summary = summarize_section(req.section_text)
    return SummarizeResponse(summary=summary)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "PolicyAssist"}
