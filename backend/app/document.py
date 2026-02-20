"""Document loading and chunking for policy documents (PDF, TXT)."""
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
    """Split documents into overlapping chunks suitable for embedding."""
    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(documents)
