"""Document Difference Mode – semantic comparison using ISOLATED Chroma collections.

Each document uploaded for comparison gets its own Chroma collection
(named  compare_<uuid>). This ensures:
  - Compare documents NEVER mix with policy_docs
  - The diff reflects only the two files being compared
  - No cross-contamination with other documents

Algorithm (vectorised, O(n+m) embedding calls):
  1. Pre-embed ALL chunks from both collections in two batch calls.
  2. Build a cosine-similarity matrix (n_a × n_b) via normalised dot-product.
  3. Chunks in A with best-match score < THRESHOLD → "removed in B".
  4. Chunks in B with best-match score < THRESHOLD → "added in B".
"""
from langchain_core.documents import Document

from app.vector_store import get_vector_store

SIMILARITY_THRESHOLD = 0.70   # below this → semantically absent


def _get_all_chunks(collection_name: str) -> list[Document]:
    """Retrieve ALL chunks from a Chroma collection."""
    store = get_vector_store(collection_name=collection_name)
    try:
        result = store._collection.get(include=["documents", "metadatas"])
        return [
            Document(page_content=text, metadata=meta or {})
            for text, meta in zip(result["documents"], result["metadatas"])
        ]
    except Exception:
        return []


def compare_documents(collection_a: str, collection_b: str) -> dict:
    """Compare two isolated Chroma collections and return a structured diff.

    Args:
        collection_a: Chroma collection for document A (e.g. "compare_<uuid_a>")
        collection_b: Chroma collection for document B (e.g. "compare_<uuid_b>")
    """
    import numpy as np
    from app.embeddings import get_embeddings

    chunks_a = _get_all_chunks(collection_a)
    chunks_b = _get_all_chunks(collection_b)

    if not chunks_a and not chunks_b:
        return {
            "error": (
                "Neither document was found. "
                "Please upload both documents using the Compare tab."
            ),
            "source_a": collection_a,
            "source_b": collection_b,
        }
    if not chunks_a:
        return {
            "error": f"Document A has no indexed content (collection: {collection_a}).",
            "source_a": collection_a, "source_b": collection_b,
        }
    if not chunks_b:
        return {
            "error": f"Document B has no indexed content (collection: {collection_b}).",
            "source_a": collection_a, "source_b": collection_b,
        }

    embedder = get_embeddings()

    # ── Batch-embed both corpora ──────────────────────────────────
    emb_a = np.array(embedder.embed_documents([c.page_content for c in chunks_a]))
    emb_b = np.array(embedder.embed_documents([c.page_content for c in chunks_b]))

    # Normalise rows → cosine similarity == dot product
    emb_a /= np.linalg.norm(emb_a, axis=1, keepdims=True) + 1e-9
    emb_b /= np.linalg.norm(emb_b, axis=1, keepdims=True) + 1e-9

    # (n_a, n_b) all-pairs cosine similarity
    sim = emb_a @ emb_b.T

    removed_in_b: list[dict] = []
    added_in_b: list[dict] = []
    common_count = 0

    # Best B-match for each A-chunk
    for i, chunk in enumerate(chunks_a):
        score = float(sim[i].max())
        if score < SIMILARITY_THRESHOLD:
            removed_in_b.append({
                "page":       chunk.metadata.get("page", "?"),
                "excerpt":    chunk.page_content[:250].strip(),
                "similarity": round(score, 3),
            })
        else:
            common_count += 1

    # Best A-match for each B-chunk
    for j, chunk in enumerate(chunks_b):
        score = float(sim[:, j].max())
        if score < SIMILARITY_THRESHOLD:
            added_in_b.append({
                "page":       chunk.metadata.get("page", "?"),
                "excerpt":    chunk.page_content[:250].strip(),
                "similarity": round(score, 3),
            })

    # ── Plain-English summary ─────────────────────────────────────
    if not removed_in_b and not added_in_b:
        summary = "The two documents appear semantically identical."
    else:
        parts = []
        if removed_in_b:
            parts.append(
                f"{len(removed_in_b)} section(s) from Document A have no close match "
                "in Document B — possibly revised or removed."
            )
        if added_in_b:
            parts.append(
                f"{len(added_in_b)} section(s) in Document B have no close match "
                "in Document A — possibly new content."
            )
        parts.append(
            f"{common_count} section(s) are semantically common to both documents."
        )
        summary = " ".join(parts)

    return {
        "source_a":     collection_a,
        "source_b":     collection_b,
        "added_in_b":   added_in_b[:20],
        "removed_in_b": removed_in_b[:20],
        "common_count": common_count,
        "summary":      summary,
    }
