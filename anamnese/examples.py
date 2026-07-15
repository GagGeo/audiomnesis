"""Extract per-section style examples from a completed report docx."""
from pathlib import Path

import docx

from anamnese.sections import SECTIONS, norm

_HEADINGS = {norm(s.heading): s.key for s in SECTIONS}


def extract_examples(completed_docx: Path) -> dict:
    """Map section key -> example text (paragraphs joined by newline)."""
    doc = docx.Document(str(completed_docx))
    out, current = {}, None
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue
        n = norm(text)
        if n in _HEADINGS:
            current = _HEADINGS[n]
            out[current] = []
        elif text == text.upper() and len(text) > 8:
            current = None  # an all-caps title ends the anamnesis block
        elif current:
            out[current].append(text)
    return {k: "\n".join(v) for k, v in out.items() if v}
