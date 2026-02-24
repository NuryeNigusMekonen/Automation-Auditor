# src/tools/vision_tools.py
from __future__ import annotations
import base64
import io
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from pypdf import PdfReader


@dataclass(frozen=True)
class ExtractedImage:
    image_id: str
    page_index: int
    mime: str
    data: bytes


class VisionToolError(RuntimeError):
    pass


def extract_images_from_pdf(pdf_path: str, max_images: int = 12) -> List[ExtractedImage]:
    """
    Best-effort extraction of images from a PDF using pypdf.
    Many PDFs store diagrams as vector drawings, not images.
    In those cases, this returns an empty list.

    Returns a list of ExtractedImage with raw bytes.
    """
    if not os.path.isfile(pdf_path):
        raise VisionToolError(f"PDF not found: {pdf_path}")

    reader = PdfReader(pdf_path)
    extracted: List[ExtractedImage] = []
    img_count = 0

    for page_index, page in enumerate(reader.pages):
        if img_count >= max_images:
            break

        # pypdf exposes images through page.images for many PDFs
        images = getattr(page, "images", None)
        if not images:
            continue

        for j, img in enumerate(images):
            if img_count >= max_images:
                break
            try:
                data = img.data
                mime = _infer_mime(img.name or "")
                extracted.append(
                    ExtractedImage(
                        image_id=f"p{page_index}_img{j}",
                        page_index=page_index,
                        mime=mime,
                        data=data,
                    )
                )
                img_count += 1
            except Exception:
                continue

    return extracted


def analyze_diagrams_with_vision(
    images: List[ExtractedImage],
    questions: Optional[List[str]] = None,
    model: str = "gpt-4o-mini",
) -> List[Dict]:
    """
    Uses OpenAI vision-capable chat model to classify each extracted image.

    Requires:
      OPENAI_API_KEY in environment.

    Output per image:
      image_id, page_index, classification, flow_flags, payload_labels_present, notes
    """
    if not images:
        return []

    # Lazy import so the project still runs with vision disabled
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage
    except Exception as e:
        raise VisionToolError("Vision dependencies missing. Install langchain-openai and langchain-core.") from e

    qs = questions or [
        "Classify the diagram type: State machine, sequence diagram, flowchart, or unknown.",
        "Does it show parallel Detectives, fan-in Evidence Aggregation, parallel Judges, and Chief Justice synthesis? Answer yes/no for each.",
        "Are data payloads labeled on arrows, for example Evidence JSON, Opinions JSON, rubric id? yes/no.",
        "Provide a short factual description of what the diagram shows."
    ]

    llm = ChatOpenAI(model=model, temperature=0)
    results: List[Dict] = []

    for img in images:
        b64 = base64.b64encode(img.data).decode("utf-8")

        prompt = "\n".join(
            [
                "You are VisionInspector. Only report observable facts from the image.",
                "Answer in strict JSON with keys:",
                "classification, shows_parallel_detectives, shows_aggregation, shows_parallel_judges, shows_synthesis, payload_labels_present, notes",
                "Questions:",
                *[f"- {q}" for q in qs],
            ]
        )

        msg = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{img.mime};base64,{b64}"},
                },
            ]
        )

        txt = llm.invoke([msg]).content
        parsed = _safe_parse_json(txt)

        results.append(
            {
                "image_id": img.image_id,
                "page_index": img.page_index,
                "mime": img.mime,
                "raw_response": txt if not parsed else None,
                "analysis": parsed or {},
            }
        )

    return results


def _infer_mime(name: str) -> str:
    low = (name or "").lower()
    if low.endswith(".png"):
        return "image/png"
    if low.endswith(".jpg") or low.endswith(".jpeg"):
        return "image/jpeg"
    if low.endswith(".webp"):
        return "image/webp"
    # pypdf images often lack extension
    return "image/png"


def _safe_parse_json(text: str) -> Optional[Dict]:
    """
    Best-effort JSON extraction.
    """
    import json
    t = (text or "").strip()
    if not t:
        return None
    # Try direct parse
    try:
        return json.loads(t)
    except Exception:
        pass
    # Try to extract first {...}
    start = t.find("{")
    end = t.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(t[start : end + 1])
        except Exception:
            return None
    return None