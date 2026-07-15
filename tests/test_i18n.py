import re

from anamnese.i18n import STRINGS


def test_both_languages_have_identical_keys():
    assert set(STRINGS["fr"]) == set(STRINGS["en"])


def test_format_placeholders_match_between_languages():
    for key in STRINGS["fr"]:
        fr_slots = set(re.findall(r"\{(\w+)\}", STRINGS["fr"][key]))
        en_slots = set(re.findall(r"\{(\w+)\}", STRINGS["en"][key]))
        assert fr_slots == en_slots, key


def test_no_empty_strings():
    for lang, table in STRINGS.items():
        for key, value in table.items():
            assert value.strip(), f"{lang}.{key}"
