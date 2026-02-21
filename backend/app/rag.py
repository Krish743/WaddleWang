"""RAG: retrieve relevant chunks and generate strictly source-grounded answers.

Design principles:
  - LLM is ONLY allowed to use the provided context.
  - Citations are built server-side from retrieved chunk metadata — the LLM
    is never trusted to generate page numbers or excerpts.
  - Confidence is computed from retrieval scores — not LLM output.
  - If the LLM cannot find an answer, it returns a fixed refusal string.
  - Gap detection is automatic when a refusal is detected.
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

from app.llm import get_llm
from app.vector_store import search_similar, search_similar_with_scores, search_tables

# ---------------------------------------------------------------------------
# Strict system prompt — LLM must answer ONLY from the supplied context
# ---------------------------------------------------------------------------
STRICT_SYSTEM_PROMPT = (
    "You are PolicyAssist, a document-grounded policy question-answering assistant.\n\n"
    "RULES (follow exactly — no exceptions):\n"
    "1. Answer ONLY using the context passages provided below. Do NOT use any prior knowledge.\n"
    "2. Quote the exact relevant clause from the context and mention its page number.\n"
    "3. If the answer is not explicitly stated anywhere in the context, respond with EXACTLY:\n"
    '   "The document does not contain this information."\n'
    "4. Do NOT fabricate, infer, or assume any information not present in the context.\n"
    "5. Do NOT generate or invent citation page numbers or excerpts — only reference what is given.\n"
    "6. Keep your answer concise and professional.\n"
    "7. NEVER start your answer with phrases like 'According to the context', "
    "'Based on the provided context', 'According to the document', "
    "'Based on the information provided', or any similar preamble. "
    "Begin your answer directly with the substance.\n\n"
    "CONTEXT:\n{context}"
)

QA_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", STRICT_SYSTEM_PROMPT),
        ("human", "{question}"),
    ]
)

# ---------------------------------------------------------------------------
# Scenario / Compliance Analyzer prompt
# ---------------------------------------------------------------------------
COMPLIANCE_SYSTEM_PROMPT = (
    "You are PolicyAssist, an AI compliance advisor.\n\n"
    "A user has described a workplace scenario. Your job is to:\n"
    "1. Analyze the scenario against the policy excerpts provided below.\n"
    "2. State the applicable policy rule(s) with their exact wording.\n"
    "3. Explain the likely outcome or consequence for the employee.\n"
    "4. Be specific — mention page numbers and exact clause text from the context.\n"
    "5. If no relevant policy is found, respond with EXACTLY:\n"
    '   "The document does not contain a policy for this scenario."\n'
    "6. Do NOT fabricate rules or outcomes not present in the context.\n\n"
    "POLICY CONTEXT:\n{context}"
)

COMPLIANCE_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", COMPLIANCE_SYSTEM_PROMPT),
        ("human", "Scenario: {scenario}"),
    ]
)

# ---------------------------------------------------------------------------
# Section summarization prompt (used by sections.py too, kept here for import convenience)
# ---------------------------------------------------------------------------
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
SCENARIO_REFUSAL_TEXT = "The document does not contain a policy for this scenario."

# Gap suggestion template
_GAP_SUGGESTION = (
    "Consider adding a dedicated policy section for this topic to improve "
    "clarity and ensure employees have clear guidance."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_context(docs: list[Document]) -> str:
    """Format retrieved chunks into a page-annotated context string."""
    parts = []
    for doc in docs:
        page = doc.metadata.get("page", "?")
        parts.append(f"[Page {page}]\n{doc.page_content.strip()}")
    return "\n\n".join(parts)


def _smart_excerpt(text: str, max_len: int = 300) -> str:
    """Extract the most informative excerpt from a chunk.

    Skips short leading lines (headings, single chars) and returns first
    substantial prose paragraph trimmed to ``max_len`` characters.
    """
    lines = [l.strip() for l in text.strip().splitlines()]
    PROSE_MIN_LEN = 35
    start_idx = 0
    for i, line in enumerate(lines):
        if len(line) >= PROSE_MIN_LEN:
            start_idx = i
            break
    excerpt = " ".join(l for l in lines[start_idx:] if l).strip()
    return excerpt[:max_len] if len(excerpt) > max_len else excerpt


def _build_sources(docs: list[Document]) -> list[dict]:
    """Build citation list from retrieved chunk metadata (never from LLM output)."""
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


def compute_confidence(docs_with_scores: list[tuple[Document, float]]) -> str:
    """Compute confidence level from retrieval relevance scores.

    Scoring logic:
      - High   → top score ≥ 0.75  (answer clearly in top chunk)
      - Medium → top score ≥ 0.50 or answer spread across multiple chunks
      - Low    → top score < 0.50  (weak match)

    Args:
        docs_with_scores: list of (Document, relevance_score) from Chroma,
                          scores in [0, 1] (higher = more relevant).
    """
    if not docs_with_scores:
        return "Low"
    scores = [score for _, score in docs_with_scores]
    top_score = max(scores)
    if top_score >= 0.75:
        return "High"
    if top_score >= 0.50:
        return "Medium"
    return "Low"


# ---------------------------------------------------------------------------
# Core RAG functions
# ---------------------------------------------------------------------------

def answer_question(
    question: str,
    collection_name: str = "policy_docs",
    top_k: int = 5,
    query_label: str = "factual_lookup",
) -> dict:
    """Retrieve relevant chunks and return a fully structured grounded answer.

    Returns:
        {
            "answer": "<LLM answer string>",
            "confidence": "High | Medium | Low",
            "sources": [{"page": 3, "excerpt": "..."}],
            "gap_detected": bool,
            "suggestion": str | None,
        }
    """
    # For numeric queries, also include table-specific chunks
    if query_label == "numeric_lookup":
        table_docs = search_tables(question, k=top_k, collection_name=collection_name)
        docs_with_scores = search_similar_with_scores(question, k=top_k, collection_name=collection_name)
        # Merge: prepend table docs with an artificial high score so they rank first
        all_docs = [d for d, _ in docs_with_scores]
        table_ids = {d.metadata.get("chunk_id") for d in table_docs}
        extra = [d for d in table_docs if d.metadata.get("chunk_id") not in
                 {dd.metadata.get("chunk_id") for dd in all_docs}]
        docs_with_scores = [(d, 0.9) for d in extra] + docs_with_scores
    else:
        docs_with_scores = search_similar_with_scores(question, k=top_k, collection_name=collection_name)
        all_docs = [d for d, _ in docs_with_scores]

    all_docs = [d for d, _ in docs_with_scores]

    if not all_docs:
        return {
            "answer": (
                "No relevant content was found in the uploaded documents. "
                "Please upload policy documents first or rephrase your question."
            ),
            "confidence": "Low",
            "sources": [],
            "gap_detected": True,
            "suggestion": "Please upload relevant policy documents before querying.",
        }

    confidence = compute_confidence(docs_with_scores)
    context = _build_context(all_docs)
    chain = QA_PROMPT | get_llm() | StrOutputParser()
    answer = chain.invoke({"context": context, "question": question})

    # If LLM returned a refusal → gap detected
    if answer.strip().startswith(REFUSAL_TEXT[:40]):
        return {
            "answer": REFUSAL_TEXT,
            "confidence": "Low",
            "sources": [],
            "gap_detected": True,
            "suggestion": _GAP_SUGGESTION,
        }

    sources = _build_sources(all_docs)
    return {
        "answer": answer.strip(),
        "confidence": confidence,
        "sources": sources,
        "gap_detected": False,
        "suggestion": None,
    }


def analyze_scenario(
    scenario: str,
    collection_name: str = "policy_docs",
    top_k: int = 7,
) -> dict:
    """Compliance advisor: retrieve policy chunks and reason over a user scenario.

    Returns:
        {
            "scenario": "...",
            "outcome": "LLM reasoning text",
            "confidence": "High | Medium | Low",
            "sources": [{"page": int, "excerpt": str}],
            "gap_detected": bool,
            "suggestion": str | None,
        }
    """
    docs_with_scores = search_similar_with_scores(scenario, k=top_k, collection_name=collection_name)
    docs = [d for d, _ in docs_with_scores]

    if not docs:
        return {
            "scenario": scenario,
            "outcome": "No relevant policy found. Please upload policy documents first.",
            "confidence": "Low",
            "sources": [],
            "gap_detected": True,
            "suggestion": "Please upload relevant policy documents before analyzing scenarios.",
        }

    confidence = compute_confidence(docs_with_scores)
    context = _build_context(docs)
    chain = COMPLIANCE_PROMPT | get_llm() | StrOutputParser()
    outcome = chain.invoke({"context": context, "scenario": scenario})

    if outcome.strip().startswith(SCENARIO_REFUSAL_TEXT[:50]):
        return {
            "scenario": scenario,
            "outcome": SCENARIO_REFUSAL_TEXT,
            "confidence": "Low",
            "sources": [],
            "gap_detected": True,
            "suggestion": _GAP_SUGGESTION,
        }

    sources = _build_sources(docs)
    return {
        "scenario": scenario,
        "outcome": outcome.strip(),
        "confidence": confidence,
        "sources": sources,
        "gap_detected": False,
        "suggestion": None,
    }


def summarize_section(section_text: str) -> str:
    """Summarize a document section (e.g. leave policy, attendance rules)."""
    if not section_text.strip():
        return "No content to summarize."
    chain = SUMMARIZE_PROMPT | get_llm() | StrOutputParser()
    return chain.invoke({"context": section_text})
