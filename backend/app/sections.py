"""Section detection, auto-summarization, and caching.

Strategy: scan every line across all pages. A line is a heading if it meets
any of these criteria:
  - Numbered:   "1.", "2.1", "3.1.2" followed by text  (common in policy docs)
  - ALL CAPS:   ≥ 3 uppercase words, no trailing period  (e.g. LEAVE POLICY)
  - Short+Bold: ≤ 60 chars, title-cased ≥ 3 words, no sentence-ending punctuation

When a heading is detected every piece of text after it (until the next heading)
belongs to that section. If no headings are found the whole document becomes
one section called "Document Overview".
"""
import json
import re
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.config import get_settings

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SECTION_SUMMARY_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are PolicyAssist. Summarize the following policy section in 2-4 concise sentences. "
            "Focus on key rules, conditions, and limits. Do NOT add information not present in the text.\n\n"
            "Section text:\n{text}",
        ),
        ("human", "Provide a concise summary."),
    ]
)

# ---------------------------------------------------------------------------
# Heading patterns (applied per line, stripped)
# ---------------------------------------------------------------------------

# 1) Numbered section: "1.", "2.1", "2.1.1", "1.2.3 Title text"
_NUMBERED_RE = re.compile(r"^\d+(\.\d+)*\.?\s+\S")

# 2) ALL CAPS line: at least 2 words, all uppercase letters/spaces/&/-
_ALLCAPS_RE = re.compile(r"^[A-Z][A-Z\s\-&/,]{4,}[A-Z]$")

# 3) Title Case: ≥ 3 words, each starting with uppercase, no trailing period/comma/semicolon
_TITLECASE_RE = re.compile(
    r"^([A-Z][a-zA-Z]{0,}(\s+[A-Z][a-zA-Z]{0,}){2,})[^.,:;!?]*$"
)


def _is_heading(line: str) -> bool:
    """Return True if `line` looks like a section heading."""
    line = line.strip()
    # Must be non-empty and not too long
    if not line or len(line) > 80:
        return False
    # Must have at least 2 "words"
    words = line.split()
    if len(words) < 2:
        return False
    # Must not end with sentence-ending punctuation (real headings rarely do)
    if line[-1] in ".?!;,":
        return False

    return (
        bool(_NUMBERED_RE.match(line))
        or bool(_ALLCAPS_RE.match(line))
        or bool(_TITLECASE_RE.match(line))
    )


# ---------------------------------------------------------------------------
# Core detection
# ---------------------------------------------------------------------------

def detect_sections(docs: list[Document]) -> list[dict]:
    """Split document chunks into logical sections by heading detection.

    Returns a list of dicts:
        {
            "section_name": "Leave Policy",
            "text": "...",
            "start_page": 3,
            "end_page": 5,
        }

    Each heading starts a new section. Text before the first heading is
    collected under "Introduction / General".
    """
    sections: list[dict] = []
    current: dict | None = None

    def _save(sec: dict | None):
        if sec and sec["text"].strip():
            sections.append(sec)

    for doc in docs:
        page = int(doc.metadata.get("page", 1))
        for raw_line in doc.page_content.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if _is_heading(line):
                _save(current)
                current = {
                    "section_name": _clean_heading(line),
                    "text": "",
                    "start_page": page,
                    "end_page": page,
                }
            else:
                if current is None:
                    current = {
                        "section_name": "Introduction / General",
                        "text": "",
                        "start_page": page,
                        "end_page": page,
                    }
                current["text"] += " " + line
                current["end_page"] = page

    _save(current)

    # If nothing was detected, return the whole thing as one section
    if not sections:
        full_text = " ".join(d.page_content for d in docs)
        start = int(docs[0].metadata.get("page", 1)) if docs else 1
        end   = int(docs[-1].metadata.get("page", 1)) if docs else 1
        return [{"section_name": "Document Overview", "text": full_text,
                 "start_page": start, "end_page": end}]

    return sections


def _clean_heading(line: str) -> str:
    """Normalise heading text to title-case for display."""
    # If it's already mixed case, leave as-is; if ALL CAPS, convert to title
    if line == line.upper():
        return line.title()
    return line.strip()


# ---------------------------------------------------------------------------
# LLM summarization
# ---------------------------------------------------------------------------

def summarize_sections(sections: list[dict], llm) -> list[dict]:
    """Generate LLM summaries per section. Skips sections with < 50 chars."""
    chain = SECTION_SUMMARY_PROMPT | llm | StrOutputParser()
    result = []
    for sec in sections:
        text = sec["text"].strip()[:3000]
        if len(text) < 50:
            continue
        try:
            summary = chain.invoke({"text": text})
        except Exception:
            summary = "Summary unavailable."
        result.append(
            {
                "section_name": sec["section_name"],
                "summary": summary.strip(),
                "page_range": f"{sec['start_page']}-{sec['end_page']}",
                "start_page": sec["start_page"],
                "end_page": sec["end_page"],
            }
        )
    return result


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _sections_dir() -> Path:
    d = get_settings().data_dir / "sections"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cache_sections(sections_data: list[dict], file_id: str) -> None:
    """Persist section data to  data/sections/<file_id>.json."""
    path = _sections_dir() / f"{file_id}.json"
    path.write_text(json.dumps(sections_data, indent=2), encoding="utf-8")


def load_all_sections() -> list[dict]:
    """Load and merge all cached section JSON files."""
    all_sections: list[dict] = []
    for f in sorted(_sections_dir().glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            all_sections.extend(data)
        except Exception:
            continue
    return all_sections
