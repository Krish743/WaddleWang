"""RAG: retrieve relevant chunks and generate source-grounded answers/summaries."""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.llm import get_llm
from app.vector_store import search_similar


QA_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are PolicyAssist. Answer the user's question using ONLY the following context from policy documents. "
            "If the context does not contain enough information to answer, say so clearly. "
            "Do not invent or assume information. Keep answers clear and concise."
            "\n\nContext:\n{context}",
        ),
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


def _format_docs(docs):
    return "\n\n---\n\n".join(d.page_content for d in docs)


def answer_question(
    question: str,
    collection_name: str = "policy_docs",
    top_k: int = 5,
) -> str:
    """Retrieve relevant chunks and generate an answer grounded in the document."""
    docs = search_similar(question, k=top_k, collection_name=collection_name)
    if not docs:
        return (
            "No relevant content was found in the uploaded documents. "
            "Please upload policy documents first or rephrase your question."
        )
    context = _format_docs(docs)
    chain = QA_PROMPT | get_llm() | StrOutputParser()
    return chain.invoke({"context": context, "question": question})


def summarize_section(
    section_text: str,
) -> str:
    """Summarize a document section (e.g. leave policy, attendance rules)."""
    if not section_text.strip():
        return "No content to summarize."
    chain = SUMMARIZE_PROMPT | get_llm() | StrOutputParser()
    return chain.invoke({"context": section_text})
