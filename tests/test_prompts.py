from anamnese.prompts import (SYSTEM_PROMPT, section_prompt, intro_prompt,
                              header_prompt, notes_prompt)
from anamnese.sections import SECTIONS

def test_system_prompt_bans_real_names():
    assert "XXX" in SYSTEM_PROMPT and "JAMAIS" in SYSTEM_PROMPT

def test_section_prompt_contains_all_parts():
    s = SECTIONS[0]
    p = section_prompt(s, "TRANSCRIPT_SENTINEL", "EXAMPLE_SENTINEL", "Madame XXX")
    for token in ("TRANSCRIPT_SENTINEL", "EXAMPLE_SENTINEL", s.heading,
                  "Madame XXX", "Spontanément,", "AUCUNE INFORMATION"):
        assert token in p

def test_header_prompt_requests_json_keys():
    p = header_prompt("T")
    for key in ("laterality", "langue_maternelle", "statut_marital",
                "niveau_etudes", "profession", "motif_consultation",
                "accompagnant"):
        assert key in p

def test_intro_and_notes_prompts():
    assert "Je rencontre ce jour" in intro_prompt("T", "Monsieur XXX")
    assert "notes" in notes_prompt("T").lower()
