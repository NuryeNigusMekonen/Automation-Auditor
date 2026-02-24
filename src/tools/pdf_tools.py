from __future__ import annotations

import re
from typing import List

from pypdf import PdfReader

from src.state import Evidence


def ingest_pdf_chunks(pdf_path: str, max_chars: int = 2500) -> List[str]:
    reader = PdfReader(pdf_path)
    full: List[str] = []
    for p in reader.pages:
        txt = p.extract_text() or ""
        full.append(txt)
    text = "\n".join(full)

    chunks: List[str] = []
    i = 0
    while i < len(text):
        chunks.append(text[i : i + max_chars])
        i += max_chars
    return chunks


def extract_keyword_evidence(chunks: List[str], keywords: List[str], goal: str) -> List[Evidence]:
    joined = "\n".join(chunks)
    low = joined.lower()

    hits: List[str] = []
    for k in keywords:
        if k.lower() in low:
            hits.append(k)

    return [
        Evidence(
            goal=goal,
            found=bool(hits),
            content=("Keywords found: " + ", ".join(hits)) if hits else None,
            location="pdf",
            rationale="Keyword scan over extracted PDF text",
            confidence=0.7 if hits else 0.6,
        )
    ]


def extract_report_paths_evidence(chunks: List[str], goal: str) -> List[Evidence]:
    joined = "\n".join(chunks)
    paths = sorted(set(re.findall(r"\b(?:src|rubric|audit|reports)/[A-Za-z0-9_./-]+\b", joined)))

    return [
        Evidence(
            goal=goal,
            found=bool(paths),
            content="\n".join(paths[:200]) if paths else None,
            location="pdf",
            rationale="Regex extraction of repo-like paths from PDF text",
            confidence=0.65 if paths else 0.55,
        )
    ]