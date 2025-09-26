"""
PDF to Text Tool - Extract text from given pages of a PDF file.
- Input: file path, optional page selection
- Output: plain text per page and concatenated text
- Pages syntax: '1' (page1), '1-3' (1..3), '1,3,5', '2-'
- Paths are resolved from project root (pyproject/.git/src) if relative
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None

try:
    from add_mcp_server.config import find_project_root
except Exception:
    find_project_root = lambda: Path.cwd()  # type: ignore

PROJECT_ROOT = find_project_root()


def _resolve(p: str) -> Path:
    q = Path(p).expanduser()
    return q if q.is_absolute() else (PROJECT_ROOT / q).resolve()


def _parse_pages(pages: str | None, total: int) -> List[int]:
    if not pages:
        return list(range(total))
    indices: List[int] = []
    pages = pages.strip()
    for part in pages.split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            a, b = part.split('-', 1)
            start = int(a) - 1 if a else 0
            end = int(b) - 1 if b else total - 1
            start = max(0, start); end = min(total - 1, end)
            if start <= end:
                indices.extend(range(start, end + 1))
        else:
            idx = int(part) - 1
            if 0 <= idx < total:
                indices.append(idx)
    # unique
    seen = set(); out: List[int] = []
    for i in indices:
        if i not in seen:
            seen.add(i); out.append(i)
    return out


def run(path: str, pages: str | None = None) -> Dict[str, Any]:
    if PdfReader is None:
        return {"error": "pypdf is not installed. Please install pypdf>=4.2.0."}
    pdf_path = _resolve(path)
    if not pdf_path.exists() or not pdf_path.is_file():
        return {"error": f"PDF not found: {pdf_path}"}
    try:
        reader = PdfReader(str(pdf_path))
        total = len(reader.pages)
        indices = _parse_pages(pages, total)
        pages_text: List[Dict[str, Any]] = []
        for i in indices:
            try:
                txt = reader.pages[i].extract_text() or ""
            except Exception as e:
                txt = f"<ERROR extracting page {i+1}: {e}>"
            pages_text.append({"page": i + 1, "text": txt})
        joined = "\n\n".join(p["text"] for p in pages_text)
        return {
            "success": True,
            "file": str(pdf_path),
            "pages": [p["page"] for p in pages_text],
            "pages_count": len(pages_text),
            "text": joined,
            "by_page": pages_text,
        }
    except Exception as e:
        return {"error": str(e)}


def spec() -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "pdf2text",
            "description": "Extraction de texte depuis un PDF pour des pages données. Entrée: path (string), pages (string optionnelle) — Sortie: texte concaténé et par page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Chemin du fichier PDF (relatif au projet ou absolu)"},
                    "pages": {"type": "string", "description": "Pages à extraire (1-based), ex: '1-3,5,10'"}
                },
                "required": ["path"],
                "additionalProperties": False
            }
        }
    }
