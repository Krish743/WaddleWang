"""RAG: retrieve relevant chunks and generate strictly source-grounded answers.

Design principles:
  - LLM is ONLY allowed to use the provided context.
  - Citations are built server-side from retrieved chunk metadata — the LLM
    is never trusted to generate page numbers or excerpts.
  - If the LLM cannot find an answer, it returns a fixed refusal string.
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

from app.llm import get_llm
from app.vector_store import search_similar

# ---------------------------------------------------------------------------
# Strict system prompt — LLM must answer ONLY from the supplied context
# ---------------------------------------------------------------------------
STRICT_SYSTEM_PROMPT = (
    "You are PolicyAssist, a document-grounded policy question-answering assistant.\n\n"
    "RULES (follow exactly — no exceptions):\n"
    "1. Answer ONLY using the context passages provided below. Do NOT use any prior knowledge.\n"
    "2. When answering, quote the exact relevant clause from the context and mention its page number.\n"
    "3. If the answer is not explicitly stated anywhere in the context, respond with EXACTLY:\n"
    '   "The document does not contain this information."\n'
    "4. Do NOT fabricate, infer, or assume any information not present in the context.\n"
    "5. Do NOT generate or invent citation page numbers or excerpts — only reference what is given.\n"
    "6. Keep your answer concise and professional.\n\n"
    "CONTEXT:\n{context}"
)

QA_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", STRICT_SYSTEM_PROMPT),
        ("human", "{question}"),
    ]
)

SUMMARIZE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are PolicyAssist. Summarize the following section from a policy document in simple, clear language. "
            "Preserve key points (rules, deadlines, conditions). Do not add information that is not in the text."
            "\n\nSection:\n{context}",
        ),
        ("human", "Provide a concise summary."),
    ]
)

# Refusal sentinel — returned by the LLM when info is not found
REFUSAL_TEXT = "The document does not contain this information."


def _build_context(docs: list[Document]) -> str:
    """Format retrieved chunks into a page-annotated context string.

    Each chunk is prefixed with its page number so the LLM can reference it.
    Example output:
        [Page 3]
        Employees are entitled to 15 days of annual leave per calendar year...

        [Page 7]
        Overtime must be pre-approved in writing by the department head...
    """
    parts = []
    for doc in docs:
        page = doc.metadata.get("page", "?")
        parts.append(f"[Page {page}]\n{doc.page_content.strip()}")
    return "\n\n".join(parts)


def _smart_excerpt(text: str, max_len: int = 300) -> str:
    """Extract the most informative excerpt from a chunk.

    Skips short leading lines (document titles, section headings, single chars)
    and returns the first substantial prose paragraph, trimmed to ``max_len``
    characters.  This avoids showing "Document Title / 1. Introduction / Welcome"
    when the relevant policy clause is further down in the same chunk.
    """
    lines = [l.strip() for l in text.strip().splitlines()]

    # Find the first line with enough content to be prose (not a heading)
    PROSE_MIN_LEN = 35
    start_idx = 0
    for i, line in enumerate(lines):
        if len(line) >= PROSE_MIN_LEN:
            start_idx = i
            break

    # Re-join from the first prose line onward
    excerpt = " ".join(l for l in lines[start_idx:] if l).strip()
    return excerpt[:max_len] if len(excerpt) > max_len else excerpt


def _build_sources(docs: list[Document]) -> list[dict]:
    """Build citation list from retrieved chunk metadata.

    Sources are derived entirely from the vector store metadata — never from
    LLM output — so they are guaranteed to be real.

    Each source contains:
        - page    : int   — 1-based page number
        - excerpt : str   — smart excerpt from chunk (skips headings/titles)

    All top-k retrieved chunks are included as separate citations; deduplicating
    by page would discard relevant chunks that happen to share a page.
    """
    sources = []
    seen_chunk_ids: set[str] = set()
    for doc in docs:
        cid = doc.metadata.get("chunk_id", "")
        if cid in seen_chunk_ids:
            continue
        seen_chunk_ids.add(cid)
        page = int(doc.metadata.get("page", 0))
        excerpt = _smart_excerpt(doc.page_content)
        sources.append({"page": page, "excerpt": excerpt})
    return sources



def answer_question(
    question: str,
    collection_name: str = "policy_docs",
    top_k: int = 5,
) -> dict:
    """Retrieve relevant chunks and return a grounded answer with citations.

    Returns:
        {
            "answer": "<LLM answer string>",
            "sources": [
                {"page": 3, "excerpt": "exact text from retrieved chunk..."},
                ...
            ]
        }
    If no relevant chunks are found, sources will be [] and the answer will
    indicate that no documents are uploaded or relevant.
    """
    docs = search_similar(question, k=top_k, collection_name=collection_name)

    if not docs:
        return {
            "answer": (
                "No relevant content was found in the uploaded documents. "
                "Please upload policy documents first or rephrase your question."
            ),
            "sources": [],
        }

    context = _build_context(docs)
    chain = QA_PROMPT | get_llm() | StrOutputParser()
    answer = chain.invoke({"context": context, "question": question})

    # If LLM returned a refusal, sources list is empty (nothing to cite)
    if answer.strip().startswith(REFUSAL_TEXT[:40]):
        return {"answer": REFUSAL_TEXT, "sources": []}

    sources = _build_sources(docs)
    return {"answer": answer.strip(), "sources": sources}


def summarize_section(section_text: str) -> str:
    """Summarize a document section (e.g. leave policy, attendance rules)."""
    if not section_text.strip():
        return "No content to summarize."
    chain = SUMMARIZE_PROMPT | get_llm() | StrOutputParser()
    return chain.invoke({"context": section_text})
