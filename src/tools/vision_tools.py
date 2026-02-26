from __future__ import annotations

from typing import List, Tuple

from pypdf import PdfReader

from src.state import Evidence


def _extract_page_images(reader: PdfReader) -> Tuple[int, List[str]]:
    count = 0
    meta: List[str] = []

    for page_idx, page in enumerate(reader.pages):
        try:
            resources = page.get("/Resources") or {}
            xobj = resources.get("/XObject") or {}
            if hasattr(xobj, "get_object"):
                xobj = xobj.get_object()
        except Exception:
            continue

        try:
            items = list((xobj or {}).items())
        except Exception:
            items = []

        for name, obj in items:
            try:
                o = obj.get_object()
            except Exception:
                continue

            subtype = None
            try:
                subtype = o.get("/Subtype")
            except Exception:
                subtype = None

            if str(subtype) != "/Image":
                continue

            count += 1
            w = o.get("/Width")
            h = o.get("/Height")
            cs = o.get("/ColorSpace")
            flt = o.get("/Filter")

            meta.append(
                f"page={page_idx + 1} name={name} width={w} height={h} colorspace={cs} filter={flt}"
            )

    return count, meta


def _count_images(reader: PdfReader) -> List[int]:
    pages_with_images: List[int] = []

    for i, page in enumerate(reader.pages):
        try:
            resources = page.get("/Resources") or {}
            xobj = resources.get("/XObject") or {}
            if hasattr(xobj, "get_object"):
                xobj = xobj.get_object()

            has_img = False
            for _, obj in (xobj or {}).items():
                try:
                    o = obj.get_object()
                    if str(o.get("/Subtype")) == "/Image":
                        has_img = True
                        break
                except Exception:
                    continue

            if has_img:
                pages_with_images.append(i + 1)
        except Exception:
            continue

    return pages_with_images


def _collect_page_snippets(
    reader: PdfReader, terms: List[str], max_snips: int = 12
) -> List[str]:
    snips: List[str] = []
    term_set = [t.lower() for t in terms if t]

    for i, page in enumerate(reader.pages):
        try:
            txt = (page.extract_text() or "").replace("\n", " ")
        except Exception:
            txt = ""

        low = txt.lower()
        if not low:
            continue

        hit = None
        for t in term_set:
            if t in low:
                hit = t
                break

        if not hit:
            continue

        cut = txt.strip()
        if len(cut) > 420:
            cut = cut[:420]

        if cut:
            snips.append(f"page={i + 1} term={hit} snippet={cut}")

        if len(snips) >= max_snips:
            break

    return snips


def analyze_pdf_diagrams_safe(pdf_path: str) -> List[Evidence]:
    """
    Deterministic PDF diagram evidence:
    - Counts embedded images per PDF via /XObject scanning
    - Emits per-image metadata (page, size, filter)
    - Scans text for diagram labels to link images to narrative
    Output is stable across different PDFs.
    """
    try:
        reader = PdfReader(pdf_path)

        img_count, img_meta = _extract_page_images(reader)
        pages_with_images = _count_images(reader)

        diagram_terms = [
            "figure",
            "diagram",
            "architecture",
            "stategraph",
            "state graph",
            "flow",
        ]
        parallel_terms = [
            "parallel",
            "fan-out",
            "fan out",
            "fan-in",
            "fan in",
            "conditional",
            "branch",
            "concurrent",
        ]

        joined = []
        for p in reader.pages:
            try:
                joined.append(p.extract_text() or "")
            except Exception:
                joined.append("")
        full_text = "\n".join(joined)
        low = full_text.lower()

        diagram_hits = [t for t in diagram_terms if t in low]
        parallel_hits = [t for t in parallel_terms if t in low]

        label_snips = _collect_page_snippets(
            reader,
            terms=list(dict.fromkeys(diagram_terms + parallel_terms)),
            max_snips=12,
        )

        content_lines: List[str] = []
        content_lines.append(f"embedded_images={img_count}")
        content_lines.append(f"pages_with_images={pages_with_images}")

        if img_meta:
            content_lines.append("image_metadata:")
            content_lines.extend(img_meta[:60])

        content_lines.append(f"diagram_terms_found={diagram_hits}")
        content_lines.append(f"parallel_terms_found={parallel_hits}")

        if label_snips:
            content_lines.append("label_snippets:")
            content_lines.extend(label_snips)

        found = img_count > 0 or bool(diagram_hits) or bool(parallel_hits)

        if img_count > 0:
            confidence = 0.9
        elif diagram_hits or parallel_hits:
            confidence = 0.8
        else:
            confidence = 0.75

        rationale = "Extracted embedded image metadata and diagram label cues from PDF"

        return [
            Evidence(
                goal="swarm_visual",
                found=found,
                content="\n".join(content_lines) if content_lines else None,
                location="pdf",
                rationale=rationale,
                confidence=confidence,
            )
        ]
    except Exception as e:
        return [
            Evidence(
                goal="swarm_visual",
                found=False,
                content=f"Diagram analysis failed: {e}",
                location="pdf",
                rationale="PDF read or image extraction failed",
                confidence=0.85,
            )
        ]
