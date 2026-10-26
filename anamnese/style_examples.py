"""Load the clinician's own anonymized reports as per-section STYLE references.

This is how the tool "learns" a writing style: not by training (impossible on
an 8 GB machine) but by showing real anonymized reports in-context so the local
model imitates the phrasing. The reports must follow the bilan-cr template so
their section headings can be matched; text under each anamnesis heading becomes
that section's style canvas, replacing the generic skeleton.

The reports MUST be anonymized by the clinician before being placed here — they
are sent verbatim into the prompt as style references.
"""
from pathlib import Path

import docx

from anamnese import sections
from anamnese.sections import SECTIONS, norm

# Headings that bracket the anamnesis block — reaching one ends the current
# section, so the last section (thymie) does not swallow the rest of the report.
_BOUNDARY = {
    "fr": {norm("ÉLÉMENTS ANAMNÈSTIQUES"), norm("ÉVALUATION NEUROPSYCHOLOGIQUE"),
           norm("CONCLUSIONS DE L'ÉVALUATION NEUROPSYCHOLOGIQUE")},
    "en": {norm("ANAMNESTIC ELEMENTS"), norm("NEUROPSYCHOLOGICAL ASSESSMENT"),
           norm("CONCLUSIONS OF THE NEUROPSYCHOLOGICAL ASSESSMENT")},
}

# Per-section cap (characters) so several examples still fit OLLAMA_NUM_CTX
# alongside the transcript. ponytail: fixed cap, revisit if context grows.
_PER_SECTION_CHARS = 1600


def _sections_in_doc(path: Path, lang: str) -> dict:
    """{section key -> style text} parsed from one report by its headings."""
    headings = {norm(sections.heading(s, lang)): s.key for s in SECTIONS}
    boundaries = _BOUNDARY.get(lang, set())
    buckets = {}
    current = None
    for p in docx.Document(str(path)).paragraphs:
        text = p.text.strip()
        if not text:
            continue
        n = norm(text)
        if n in headings:
            current = headings[n]
            continue
        if n in boundaries:
            current = None
            continue
        if current:
            buckets.setdefault(current, []).append(text)
    return {k: "\n".join(v) for k, v in buckets.items()}


def load(folder, lang: str) -> dict:
    """Merge per-section style text from every .docx report in `folder`.
    Returns {} when the folder is missing/empty or holds no usable report."""
    if not folder:
        return {}
    folder = Path(folder)
    if not folder.is_dir():
        return {}
    merged = {}
    for path in sorted(folder.glob("*.docx")):
        if path.name.startswith("~$"):  # Word lock files
            continue
        try:
            found = _sections_in_doc(path, lang)
        except Exception:
            continue  # a malformed example must never break generation
        for key, text in found.items():
            if not text:
                continue
            prev = merged.get(key, "")
            if len(prev) >= _PER_SECTION_CHARS:
                continue
            merged[key] = (prev + "\n\n" + text).strip() if prev else text
    return {k: v[:_PER_SECTION_CHARS] for k, v in merged.items()}
