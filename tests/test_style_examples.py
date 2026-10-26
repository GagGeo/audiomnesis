from anamnese import config, style_examples
from anamnese.docx_filler import fill_report


def _make_report(path, lang):
    fill_report(
        config.DEFAULT_TEMPLATE_EN if lang == "en" else config.DEFAULT_TEMPLATE,
        path, intro_text="", header_fields={}, lang=lang,
        section_texts={
            "plaintes": "STYLE_PLAINTE one.\nSTYLE_PLAINTE two.",
            "atcd_perso": "STYLE_ATCD.",
            "atcd_fam": None, "developpement": None,
            "thymie": "STYLE_THYMIE.",
        })


def test_load_parses_sections_from_report(tmp_path):
    _make_report(tmp_path / "ex.docx", "fr")
    got = style_examples.load(tmp_path, "fr")
    assert "STYLE_PLAINTE one." in got["plaintes"]
    assert "STYLE_ATCD" in got["atcd_perso"]
    assert "STYLE_THYMIE" in got["thymie"]


def test_last_section_does_not_swallow_rest_of_report(tmp_path):
    _make_report(tmp_path / "ex.docx", "fr")
    got = style_examples.load(tmp_path, "fr")
    # thymie must stop at the boundary, not absorb the cognitive-sphere defs
    assert "instrumental" not in got["thymie"].lower()
    assert len(got["thymie"]) <= 1600


def test_missing_or_empty_folder_returns_empty():
    assert style_examples.load(None, "fr") == {}
    assert style_examples.load("/nonexistent/path/xyz", "fr") == {}


def test_english_report_parsed_with_english_headings(tmp_path):
    _make_report(tmp_path / "ex.docx", "en")
    got = style_examples.load(tmp_path, "en")
    assert "STYLE_PLAINTE one." in got["plaintes"]
    # headings are language-specific: FR parse of an EN report finds nothing
    assert style_examples.load(tmp_path, "fr") == {} or \
        "STYLE_PLAINTE one." not in style_examples.load(tmp_path, "fr").get("plaintes", "")
