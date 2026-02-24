## Goal
# Parse and chunk PDF.

## Checklist
# Extract text
# Chunk into list
#Extract file paths mentioned
# src/tools/pdf_tools.py
from __future__ import annotations
import re
from typing import Dict, List, Tuple
from pypdf import PdfReader


def ingest_pdf(pdf_path: str, chunk_chars: int = 1600, overlap: int = 200) -> Dict:
    """
    Extracts text and chunks it for RAG-lite querying.
    Returns dict with chunks and extracted file paths.
    """
    reader = PdfReader(pdf_path)
    pages: List[str] = []
    for p in reader.pages:
        try:
            pages.append(p.extract_text() or "")
        except Exception:
            pages.append("")

    full = "\n".join(pages)
    chunks = _chunk_text(full, chunk_chars=chunk_chars, overlap=overlap)
    paths = _extract_paths(full)
    return {"full_text_len": len(full), "chunks": chunks, "paths_mentioned": paths}


def search_chunks(chunks: List[str], query: str, top_k: int = 5) -> List[Tuple[int, str]]:
    """
    Simple keyword scoring. No embeddings.
    """
    q = (query or "").lower().strip()
    if not q:
        return []
    scored: List[Tuple[int, int]] = []
    for i, c in enumerate(chunks):
        score = c.lower().count(q)
        if score > 0:
            scored.append((score, i))
    scored.sort(reverse=True)
    out: List[Tuple[int, str]] = []
    for score, idx in scored[:top_k]:
        out.append((idx, chunks[idx]))
    return out


_PATH_RE = re.compile(r"\b(?:src|rubric|audit)/[A-Za-z0-9_\-./]+\b")


def _extract_paths(text: str) -> List[str]:
    return sorted(set(_PATH_RE.findall(text or "")))


def _chunk_text(text: str, chunk_chars: int, overlap: int) -> List[str]:
    t = text or ""
    if not t:
        return []
    out: List[str] = []
    i = 0
    while i < len(t):
        j = min(len(t), i + chunk_chars)
        out.append(t[i:j])
        if j == len(t):
            break
        i = max(0, j - overlap)
    return out