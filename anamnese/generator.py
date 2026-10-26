"""Orchestrates section-by-section report generation from a transcript."""
from dataclasses import dataclass, field

from anamnese.condenser import prepare_source
from anamnese.ollama_client import parse_json_reply
from anamnese.prompts import (NO_INFO, header_prompt, intro_prompt,
                              section_prompt, system_prompt)
from anamnese import sections
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
                    progress_cb=None, lang="fr", example_is_real=False) -> ReportResult:
    """examples: section key -> style example text (skeletons or anonymized
    reports). patient_title: anonymous designation matching `lang`.
    lang: report language ("fr"|"en"). example_is_real: True when `examples`
    come from the clinician's real reports, so the prompt forbids fact copying."""
    def progress(msg):
        if progress_cb:
            progress_cb(msg)

    system = system_prompt(lang)
    no_info = NO_INFO[lang]
    result = ReportResult()
    source = prepare_source(transcript, client, progress_cb, lang)

    progress("Extraction des informations administratives")
    try:
        raw = client.generate(header_prompt(source, lang), system=system,
                              num_predict=1500)  # budget includes thinking tokens
        data = parse_json_reply(raw)
        result.header_fields = {k: data.get(k) for k in _HEADER_KEYS
                                if data.get(k)}
    except Exception:
        result.header_fields = {}

    for i, section in enumerate(SECTIONS, 1):
        heading = sections.heading(section, lang)
        progress(f"Rédaction {i}/{len(SECTIONS)} : {heading}")
        try:
            text = client.generate(
                section_prompt(section, source, examples.get(section.key, ""),
                               patient_title, lang, example_is_real),
                system=system)
            if no_info in text.upper():
                result.section_texts[section.key] = None
                result.no_info.append(heading)
            else:
                result.section_texts[section.key] = text
        except Exception:
            result.section_texts[section.key] = None
            result.failed.append(heading)

    progress("Rédaction de l'introduction")
    try:
        result.intro_text = client.generate(
            intro_prompt(source, patient_title, lang), system=system,
            num_predict=1200)  # budget includes thinking tokens
    except Exception:
        result.intro_text = ""

    return result
