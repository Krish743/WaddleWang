"""Table Intelligence – extract tables from PDFs and store them as structured chunks.

Uses pdfplumber (lightweight, no Java required) to extract tables.
Each table is serialised as a Markdown table string and stored in Chroma
with metadata  {"is_table": True, "page": <n>}  so numeric-lookup queries
can filter to table-only chunks for precise answers.

Install:  pip install pdfplumber
"""
from pathlib import Path

from langchain_core.documents import Document


def _table_to_markdown(table: list[list]) -> str:
    """Convert a pdfplumber table (list of rows) to a Markdown table string.

    pdfplumber returns None for empty cells; we replace with empty string.
    """
    if not table:
        return ""

    rows = [[str(cell) if cell is not None else "" for cell in row] for row in table]
    if not rows:
        return ""

    header = rows[0]
    body = rows[1:]

    # Build markdown
    separator = " | ".join(["---"] * len(header))
    lines = [
        " | ".join(header),
        separator,
    ]
    for row in body:
        # Pad short rows
        while len(row) < len(header):
            row.append("")
        lines.append(" | ".join(row))

    return "\n".join(lines)


def extract_tables_from_pdf(file_path: Path) -> list[Document]:
    """Extract all tables from a PDF and return them as LangChain Documents.

    Each Document has:
        page_content : Markdown-formatted table text
        metadata     : {
            "page"      : int  (1-based),
            "source"    : str  (filename stem),
            "chunk_id"  : str,
            "is_table"  : True,
            "section_title": "",
        }

    Returns an empty list if pdfplumber is not installed or no tables found.
    """
    try:
        import pdfplumber  # optional dependency
    except ImportError:
        return []

    source = file_path.stem
    table_docs: list[Document] = []
    table_index = 0

    try:
        with pdfplumber.open(str(file_path)) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                for table in tables:
                    md = _table_to_markdown(table)
                    if not md.strip():
                        continue
                    chunk_id = f"{source}_table_p{page_num}_t{table_index}"
                    doc = Document(
                        page_content=f"[TABLE – Page {page_num}]\n{md}",
                        metadata={
                            "page": page_num,
                            "source": source,
                            "chunk_id": chunk_id,
                            "is_table": True,
                            "section_title": "",
                        },
                    )
                    table_docs.append(doc)
                    table_index += 1
    except Exception:
        return []

    return table_docs
