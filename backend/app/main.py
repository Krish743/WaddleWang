"""PolicyAssist RAG API – Policy Intelligence System.

Endpoints:
  POST /upload              Upload + index a document; triggers section detection.
  POST /ask                 Grounded Q&A with confidence + gap detection.
  POST /analyze_scenario    AI compliance advisor for workplace scenarios.
  GET  /sections            Return auto-detected section summaries.
  POST /compare_documents   Semantic diff between two uploaded documents.
  POST /summarize           Summarize a raw text section.
  GET  /health              Health check.
"""
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import get_settings
from app.document import load_document, chunk_documents
from app.vector_store import add_documents_to_store
from app.rag import answer_question, analyze_scenario, summarize_section
from app.classifier import classify_query


app = FastAPI(
    title="PolicyAssist – Policy Intelligence System",
    description=(
        "Enterprise-grade AI policy advisor: grounded Q&A, compliance analysis, "
        "section summaries, table intelligence, gap detection, and document diff."
    ),
    version="1.0.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    """Structured answer with confidence, citations, and gap detection."""
    answer: str
    confidence: str                 # "High" | "Medium" | "Low"
    sources: list[SourceCitation]
    gap_detected: bool
    suggestion: str | None          # populated when gap_detected is True
    query_type: str                 # classifier label for transparency


class ScenarioRequest(BaseModel):
    scenario: str


class ScenarioResponse(BaseModel):
    scenario: str
    outcome: str
    confidence: str
    sources: list[SourceCitation]
    gap_detected: bool
    suggestion: str | None


class SummarizeRequest(BaseModel):
    section_text: str


class SummarizeResponse(BaseModel):
    summary: str


class UploadResponse(BaseModel):
    message: str
    file_id: str
    filename: str
    chunks_ingested: int
    tables_ingested: int
    sections_detected: int


class SectionInfo(BaseModel):
    section_name: str
    summary: str
    page_range: str


class CompareRequest(BaseModel):
    collection_a: str   # Chroma collection for document A  ("compare_<uuid_a>")
    collection_b: str   # Chroma collection for document B  ("compare_<uuid_b>")


class CompareResponse(BaseModel):
    source_a: str
    source_b: str
    added_in_b: list[dict]
    removed_in_b: list[dict]
    common_count: int
    summary: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/upload")
async def upload_get():
    """Use POST /upload with a file. See /docs."""
    return {"method": "POST", "description": "Upload a PDF or TXT file (multipart/form-data).", "docs": "/docs"}


@app.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    collection_name: str = Query(
        default=COLLECTION_NAME,
        description="Chroma collection to index into. Use a custom name for isolated compare uploads.",
    ),
):
    """Upload a policy document (PDF or TXT).

    On upload the system:
    1. Parses and chunks the document.
    2. Indexes all chunks in ChromaDB.
    3. Extracts tables from PDFs (pdfplumber) and indexes them as table chunks.
    4. Detects section headings and generates LLM summaries, cached to disk.
    """
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
        add_documents_to_store(chunks, collection_name=collection_name)

        # --- Table extraction (PDF only) – only for policy_docs uploads ---
        tables_ingested = 0
        if suffix == ".pdf" and collection_name == COLLECTION_NAME:
            from app.table_parser import extract_tables_from_pdf
            table_docs = extract_tables_from_pdf(path)
            if table_docs:
                add_documents_to_store(table_docs, collection_name=collection_name)
                tables_ingested = len(table_docs)

        # --- Section detection + caching (only for normal policy uploads) ---
        sections_detected = 0
        if collection_name == COLLECTION_NAME:
            try:
                from app.sections import detect_sections, summarize_sections, cache_sections
                from app.llm import get_llm
                sections = detect_sections(docs)
                if sections:
                    summarized = summarize_sections(sections, get_llm())
                    cache_sections(summarized, file_id)
                    sections_detected = len(summarized)
            except Exception:
                pass

        return UploadResponse(
            message="Document uploaded, indexed, and analyzed successfully.",
            file_id=file_id,
            filename=file.filename or path.name,
            chunks_ingested=len(chunks),
            tables_ingested=tables_ingested,
            sections_detected=sections_detected,
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
    """Ask a question about uploaded policy documents.

    The response is strictly grounded — LLM cannot fabricate information.

    Response fields:
    - **answer**: Grounded LLM answer referencing the document.
    - **confidence**: "High" | "Medium" | "Low" — computed from retrieval scores.
    - **sources**: Citations built from retrieved chunk metadata (page + excerpt).
    - **gap_detected**: True if the information is not present in any document.
    - **suggestion**: Advice to add the missing policy (when gap_detected is True).
    - **query_type**: Classifier label for transparency (factual_lookup, numeric_lookup, etc.)
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # Classify query to pick optimal retrieval strategy
    query_class = classify_query(req.question)

    result = answer_question(
        req.question,
        collection_name=COLLECTION_NAME,
        top_k=query_class.top_k,
        query_label=query_class.label,
    )
    return AskResponse(
        answer=result["answer"],
        confidence=result["confidence"],
        sources=[SourceCitation(**s) for s in result["sources"]],
        gap_detected=result["gap_detected"],
        suggestion=result.get("suggestion"),
        query_type=query_class.label,
    )


@app.post("/analyze_scenario", response_model=ScenarioResponse)
async def analyze_scenario_endpoint(req: ScenarioRequest):
    """AI Compliance Advisor: analyze a workplace scenario against uploaded policies.

    Send a scenario in natural language; the system retrieves relevant policy clauses,
    reasons over them, and explains the compliance outcome with exact citations.

    Example body:
    ```json
    {\"scenario\": \"I was absent for 20 days without submitting a medical certificate.\"}
    ```
    """
    if not req.scenario.strip():
        raise HTTPException(status_code=400, detail="Scenario cannot be empty.")

    result = analyze_scenario(req.scenario, collection_name=COLLECTION_NAME)
    return ScenarioResponse(
        scenario=result["scenario"],
        outcome=result["outcome"],
        confidence=result["confidence"],
        sources=[SourceCitation(**s) for s in result["sources"]],
        gap_detected=result["gap_detected"],
        suggestion=result.get("suggestion"),
    )


@app.get("/sections", response_model=list[SectionInfo])
async def get_sections():
    """Return auto-detected section summaries from all uploaded documents.

    Sections are detected when a document is uploaded. Each entry contains:
    - **section_name**: Detected heading text.
    - **summary**: Concise LLM-generated summary of the section.
    - **page_range**: e.g. "3-5" — pages spanned by this section.
    """
    try:
        from app.sections import load_all_sections
        sections = load_all_sections()
        return [
            SectionInfo(
                section_name=s["section_name"],
                summary=s["summary"],
                page_range=s["page_range"],
            )
            for s in sections
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load sections: {e}") from e


@app.post("/compare_documents", response_model=CompareResponse)
async def compare_documents_endpoint(req: CompareRequest):
    """Compare two uploaded documents and highlight semantic differences.

    Provide the **source** stems (filename without extension) of two documents
    that have already been uploaded and indexed.

    The system compares chunk embeddings and returns:
    - **added_in_b**: Content present in document B but not A (new policies).
    - **removed_in_b**: Content present in document A but not B (deleted/revised policies).
    - **common_count**: Number of chunks shared semantically between both.
    - **summary**: Plain-English diff summary.
    """
    if req.collection_a.strip() == req.collection_b.strip():
        raise HTTPException(status_code=400, detail="collection_a and collection_b must be different.")

    try:
        from app.diff import compare_documents
        result = compare_documents(
            collection_a=req.collection_a.strip(),
            collection_b=req.collection_b.strip(),
        )
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return CompareResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {e}") from e


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
    return {"status": "ok", "service": "PolicyAssist", "version": "1.0.0"}


# Mount frontend directory last so API routes always take priority.
if _FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR)), name="frontend")
