"""Vector store (Chroma) for document embeddings and semantic search."""
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.config import get_settings
from app.embeddings import get_embeddings


def get_vector_store(collection_name: str = "policy_docs"):
    """Get or create a Chroma collection. Persists to disk."""
    s = get_settings()
    s.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=collection_name,
        embedding_function=get_embeddings(),
        persist_directory=str(s.chroma_persist_dir),
    )


def add_documents_to_store(
    documents: list[Document],
    collection_name: str = "policy_docs",
    ids: list[str] | None = None,
) -> None:
    """Add chunked documents to the vector store."""
    store = get_vector_store(collection_name=collection_name)
    store.add_documents(documents, ids=ids)


def search_similar(
    query: str,
    k: int = 5,
    collection_name: str = "policy_docs",
) -> list[Document]:
    """Retrieve top-k most relevant document chunks for a query."""
    store = get_vector_store(collection_name=collection_name)
    return store.similarity_search(query, k=k)
