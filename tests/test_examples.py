from anamnese import config
from anamnese.examples import extract_examples

def test_extracts_all_five_sections_from_real_completed_docx():
    ex = extract_examples(config.STYLE_EXAMPLE_DOCX)
    assert set(ex) == {"plaintes", "atcd_perso", "atcd_fam", "developpement", "thymie"}
    assert "Spontanément" in ex["plaintes"]
    assert "Concernant ses antécédents familiaux" in ex["atcd_fam"]
    # style examples must not include next section's heading text
    assert "Antécédents médicaux personnels" not in ex["plaintes"]
