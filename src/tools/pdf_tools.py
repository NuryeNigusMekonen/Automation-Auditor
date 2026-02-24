import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from pypdf import PdfReader


@dataclass
class PdfIngest:
    full_text: str
    chunks: List[str]
    keyword_hits: Dict[str, List[str]]
    mentioned_paths: List[str]


def extract_text(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    texts: List[str] = []
    for page in reader.pages:
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        if t:
            texts.append(t)
    return "\n".join(texts)


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> List[str]:
    if not text.strip():
        return []
    chunks: List[str] = []
    i = 0
    while i < len(text):
        end = min(len(text), i + chunk_size)
        chunks.append(text[i:end])
        i = end - overlap
        if i < 0:
            i = 0
        if end == len(text):
            break
    return chunks


def find_keywords(text: str, keywords: List[str]) -> Dict[str, List[str]]:
    hits: Dict[str, List[str]] = {k: [] for k in keywords}
    lower = text.lower()
    for k in keywords:
        kl = k.lower()
        idx = 0
        while True:
            j = lower.find(kl, idx)
            if j == -1:
                break
            start = max(0, j - 80)
            end = min(len(text), j + len(k) + 80)
            snippet = text[start:end].replace("\n", " ").strip()
            hits[k].append(snippet)
            idx = j + len(kl)
    return hits


_PATH_RE = re.compile(r"\b[a-zA-Z0-9_\-]+(?:/[a-zA-Z0-9_\-\.]+)+\.(?:py|ts|md|json|yaml|yml)\b")


def extract_file_paths(text: str) -> List[str]:
    paths = _PATH_RE.findall(text or "")
    # normalize duplicates
    seen = set()
    out: List[str] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def ingest_pdf(pdf_path: str) -> PdfIngest:
    text = extract_text(pdf_path)
    chunks = chunk_text(text)
    keywords = ["Dialectical Synthesis", "Fan-In", "Fan-Out", "Metacognition", "State Synchronization"]
    hits = find_keywords(text, keywords)
    mentioned = extract_file_paths(text)
    return PdfIngest(full_text=text, chunks=chunks, keyword_hits=hits, mentioned_paths=mentioned)


def cross_reference_paths(mentioned_paths: List[str], repo_files: List[str]) -> Tuple[List[str], List[str]]:
    repo_set = set(repo_files)
    verified: List[str] = []
    hallucinated: List[str] = []
    for p in mentioned_paths:
        # allow both with and without leading ./ or root folder
        p2 = p.lstrip("./")
        if p2 in repo_set:
            verified.append(p)
        else:
            hallucinated.append(p)
    return verified, hallucinated