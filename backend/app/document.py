"""Document loading and chunking for policy documents (PDF, TXT).

Chunk metadata stored per chunk:
  - page      : int  — page number (0-indexed from PyPDFLoader; 1-indexed for TXT)
  - source    : str  — original filename stem
  - chunk_id  : str  — unique id, e.g. "report_p3_c1"
"""
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.config import get_settings


def load_document(file_path: Path) -> list[Document]:
    """Load a single document from path. Supports PDF and TXT."""
    path_str = str(file_path)
    if file_path.suffix.lower() == ".pdf":
        loader = PyPDFLoader(path_str)
    elif file_path.suffix.lower() in (".txt", ".text"):
        loader = TextLoader(path_str, encoding="utf-8", autodetect_encoding=True)
    else:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")

    return loader.load()


def chunk_documents(documents: list[Document]) -> list[Document]:
    """Split documents into overlapping chunks and stamp each with rich metadata.

    Each chunk gets:
      - ``page``     : int  — page number (PyPDFLoader gives 0-based; we convert to 1-based)
      - ``source``   : str  — filename stem from the original loader metadata
      - ``chunk_id`` : str  — deterministic id suitable for use as a Chroma document id
    """
    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    raw_chunks = splitter.split_documents(documents)

    for i, chunk in enumerate(raw_chunks):
        # PyPDFLoader sets metadata["page"] as a 0-based int.
        # TextLoader has no page; default to page 1.
        raw_page = chunk.metadata.get("page", 0)
        page = int(raw_page) + 1  # convert to 1-based page number

        # Source is the filename stem (e.g. "employee_handbook")
        raw_source = chunk.metadata.get("source", "doc")
        source = Path(raw_source).stem

        # Build a deterministic chunk id
        chunk_id = f"{source}_p{page}_c{i}"

        chunk.metadata["page"] = page
        chunk.metadata["source"] = source
        chunk.metadata["chunk_id"] = chunk_id
        # Preserve section_title if a loader supplies it (future-proof)
        chunk.metadata.setdefault("section_title", "")

    return raw_chunks
