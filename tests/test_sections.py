from anamnese.sections import SECTIONS, INTRO_LEADIN, norm

def test_norm_handles_nbsp_and_curly_apostrophe():
    assert norm("Niveau d’études\xa0: ") == "niveau d'études :"
    assert norm("  Thymie,   sommeil, appétit ") == "thymie, sommeil, appétit"

def test_five_sections_with_keys_and_stubs():
    keys = [s.key for s in SECTIONS]
    assert keys == ["plaintes", "atcd_perso", "atcd_fam", "developpement", "thymie"]
    for s in SECTIONS:
        assert s.heading and s.purpose and s.stubs

def test_intro_leadin():
    assert norm(INTRO_LEADIN) == "je rencontre ce jour"
