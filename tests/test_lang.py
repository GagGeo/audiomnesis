from anamnese.lang import detect_lang, resolve, patient_title


def test_detect_french_vs_english():
    assert detect_lang("Le patient explique qu'il a des troubles de mémoire") == "fr"
    assert detect_lang("The patient explains that he has memory trouble") == "en"


def test_detect_empty_falls_back_to_french():
    assert detect_lang("") == "fr"
    assert detect_lang("12345 ...") == "fr"


def test_resolve_explicit_choice_wins_over_detection():
    assert resolve("en", "Le patient est fatigué et malade") == "en"
    assert resolve("fr", "The patient is tired and unwell") == "fr"
    assert resolve("auto", "The patient is tired and unwell today") == "en"


def test_patient_title_matches_language_and_civility():
    assert patient_title("M", "fr") == "Monsieur XXX"
    assert patient_title("F", "fr") == "Madame XXX"
    assert patient_title("M", "en") == "Mr XXX"
    assert patient_title("F", "en") == "Ms XXX"
