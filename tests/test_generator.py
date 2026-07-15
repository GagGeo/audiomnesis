from anamnese.generator import generate_report, ReportResult

class FakeClient:
    """Returns canned replies; can fail or return no-info for chosen prompts."""
    def __init__(self, fail_on=(), no_info_on=()):
        self.fail_on, self.no_info_on = fail_on, no_info_on
    def generate(self, prompt, system=None, num_predict=1500):
        if '"laterality"' in prompt:
            return '{"laterality": "Gaucher", "langue_maternelle": null, '\
                   '"statut_marital": null, "niveau_etudes": null, '\
                   '"profession": null, "motif_consultation": "bilan", '\
                   '"accompagnant": null}'
        if "Je rencontre ce jour" in prompt:
            return "Je rencontre ce jour Monsieur XXX, âgé de 30 ans."
        for key in self.fail_on:
            if f"« {key}" in prompt:
                raise RuntimeError("boom")
        for key in self.no_info_on:
            if f"« {key}" in prompt:
                return "AUCUNE INFORMATION"
        return "Paragraphe généré.\nSecond paragraphe."

EXAMPLES = {k: "exemple" for k in
            ("plaintes", "atcd_perso", "atcd_fam", "developpement", "thymie")}


def test_happy_path_fills_everything():
    r = generate_report("transcript", FakeClient(), EXAMPLES, "Monsieur XXX")
    assert isinstance(r, ReportResult)
    assert set(r.section_texts) == set(EXAMPLES)
    assert all(v for v in r.section_texts.values())
    assert r.header_fields["laterality"] == "Gaucher"
    assert r.intro_text.startswith("Je rencontre ce jour")
    assert r.failed == [] and r.no_info == []


def test_one_section_failure_does_not_stop_others():
    r = generate_report("t", FakeClient(fail_on=("Antécédents médicaux familiaux",)),
                        EXAMPLES, "Monsieur XXX")
    assert r.section_texts["atcd_fam"] is None
    assert r.failed == ["Antécédents médicaux familiaux"]
    assert r.section_texts["plaintes"]  # others still generated


def test_no_info_section_reported_and_left_blank():
    r = generate_report("t", FakeClient(no_info_on=("Thymie, sommeil, appétit",)),
                        EXAMPLES, "Monsieur XXX")
    assert r.section_texts["thymie"] is None
    assert r.no_info == ["Thymie, sommeil, appétit"]


def test_header_extraction_failure_is_non_fatal():
    class BadJson(FakeClient):
        def generate(self, prompt, system=None, num_predict=1500):
            if '"laterality"' in prompt:
                return "pas du json"
            return super().generate(prompt, system, num_predict)
    r = generate_report("t", BadJson(), EXAMPLES, "Monsieur XXX")
    assert r.header_fields == {}
    assert r.section_texts["plaintes"]
