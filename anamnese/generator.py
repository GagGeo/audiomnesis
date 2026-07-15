"""Orchestrates section-by-section report generation from a transcript."""
from dataclasses import dataclass, field

from anamnese.condenser import prepare_source
from anamnese.ollama_client import parse_json_reply
from anamnese.prompts import (SYSTEM_PROMPT, header_prompt, intro_prompt,
                              section_prompt)
from anamnese.sections import SECTIONS

_HEADER_KEYS = ("laterality", "langue_maternelle", "statut_marital",
                "niveau_etudes", "profession", "motif_consultation",
                "accompagnant")


@dataclass
class ReportResult:
    intro_text: str = ""
    section_texts: dict = field(default_factory=dict)
    header_fields: dict = field(default_factory=dict)
    failed: list = field(default_factory=list)     # section headings that errored
    no_info: list = field(default_factory=list)    # headings with no transcript info


def generate_report(transcript, client, examples, patient_title,
                    progress_cb=None) -> ReportResult:
    """examples: section key -> style example text (from examples.py).
    patient_title: "Monsieur XXX" or "Madame XXX" (chosen in the UI)."""
    def progress(msg):
        if progress_cb:
            progress_cb(msg)

    result = ReportResult()
    source = prepare_source(transcript, client, progress_cb)

    progress("Extraction des informations administratives")
    try:
        raw = client.generate(header_prompt(source), system=SYSTEM_PROMPT,
                              num_predict=300)
        data = parse_json_reply(raw)
        result.header_fields = {k: data.get(k) for k in _HEADER_KEYS
                                if data.get(k)}
    except Exception:
        result.header_fields = {}

    for i, section in enumerate(SECTIONS, 1):
        progress(f"Rédaction {i}/{len(SECTIONS)} : {section.heading}")
        try:
            text = client.generate(
                section_prompt(section, source, examples.get(section.key, ""),
                               patient_title),
                system=SYSTEM_PROMPT)
            if "AUCUNE INFORMATION" in text.upper():
                result.section_texts[section.key] = None
                result.no_info.append(section.heading)
            else:
                result.section_texts[section.key] = text
        except Exception:
            result.section_texts[section.key] = None
            result.failed.append(section.heading)

    progress("Rédaction de l'introduction")
    try:
        result.intro_text = client.generate(
            intro_prompt(source, patient_title), system=SYSTEM_PROMPT,
            num_predict=200)
    except Exception:
        result.intro_text = ""

    return result
