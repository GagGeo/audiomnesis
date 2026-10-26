"""Report language: which language the summary is written in (fr/en).

Separate from the interface language (i18n) and from transcription — whisper
transcribes in whatever was spoken (auto-detect); this picks the language of
the generated clinical report.
"""

LANGS = ("fr", "en")

# Small, dependency-free fr/en detector. The clinic only needs to tell these
# two apart, so counting a handful of high-frequency function words is enough
# and never freezes the 8 GB machine the way a model would.
_FR = {"le", "la", "les", "un", "une", "des", "de", "du", "et", "est", "à",
       "au", "aux", "que", "qui", "pas", "plus", "pour", "dans", "avec",
       "son", "sa", "ses", "il", "elle", "je", "ne", "sur", "ce", "cette"}
_EN = {"the", "a", "an", "and", "is", "are", "to", "of", "in", "on", "with",
       "that", "this", "for", "not", "he", "she", "i", "his", "her", "it",
       "they", "was", "were", "have", "has", "but", "about", "at"}


def detect_lang(text: str, default: str = "fr") -> str:
    """Return 'fr' or 'en' from a transcript/notes text. Falls back to
    `default` when the text is empty or the two scores tie."""
    words = [w.strip(".,;:!?«»\"'()[]").lower() for w in text.split()]
    fr = sum(w in _FR for w in words)
    en = sum(w in _EN for w in words)
    if fr == en:
        return default
    return "fr" if fr > en else "en"


def resolve(selected: str, transcript: str) -> str:
    """Resolve the report language from the UI choice. 'auto' -> detect."""
    return selected if selected in LANGS else detect_lang(transcript)


def patient_title(civ: str, lang: str) -> str:
    """Anonymous patient designation used throughout the report."""
    if lang == "en":
        return "Mr XXX" if civ == "M" else "Ms XXX"
    return "Monsieur XXX" if civ == "M" else "Madame XXX"


if __name__ == "__main__":  # ponytail: one runnable check for the detector
    assert detect_lang("Le patient explique qu'il a des troubles") == "fr"
    assert detect_lang("The patient explains that he has memory trouble") == "en"
    assert detect_lang("") == "fr"
    assert resolve("en", "Le patient...") == "en"       # explicit choice wins
    assert resolve("auto", "The patient is tired") == "en"
    assert patient_title("F", "en") == "Ms XXX"
    assert patient_title("M", "fr") == "Monsieur XXX"
    print("lang ok")
