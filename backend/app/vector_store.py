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
) -> None:
    """Add chunked documents to the vector store.

    Uses ``chunk_id`` from each document's metadata as the Chroma document id.
    This ensures idempotent re-ingestion (same chunk won't be duplicated).
    """
    store = get_vector_store(collection_name=collection_name)
    ids = [doc.metadata.get("chunk_id", str(i)) for i, doc in enumerate(documents)]
    store.add_documents(documents, ids=ids)


def search_similar(
    query: str,
    k: int = 5,
    collection_name: str = "policy_docs",
) -> list[Document]:
    """Retrieve top-k most relevant document chunks for a query.

    Returns ``Document`` objects whose ``.metadata`` contains:
        - ``page``      : int
        - ``source``    : str
        - ``chunk_id``  : str
    """
    store = get_vector_store(collection_name=collection_name)
    return store.similarity_search(query, k=k)


def search_similar_with_scores(
    query: str,
    k: int = 5,
    collection_name: str = "policy_docs",
) -> list[tuple[Document, float]]:
    """Retrieve top-k chunks with their relevance scores.

    Scores are cosine-similarity-based relevance scores in [0, 1] where
    higher = more relevant.  Used for confidence computation.

    Returns list of (Document, score) tuples, sorted by score descending.
    """
    store = get_vector_store(collection_name=collection_name)
    return store.similarity_search_with_relevance_scores(query, k=k)


def search_tables(
    query: str,
    k: int = 4,
    collection_name: str = "policy_docs",
) -> list[Document]:
    """Retrieve top-k table chunks specifically (is_table == True metadata).

    Used for numeric_lookup queries to prioritise structured table data.
    Falls back to regular search if no tables are found.
    """
    store = get_vector_store(collection_name=collection_name)
    try:
        results = store.similarity_search(
            query,
            k=k,
            filter={"is_table": True},
        )
        if results:
            return results
    except Exception:
        pass
    # Fallback: regular search (tables may be mixed in with text)
    return store.similarity_search(query, k=k)
