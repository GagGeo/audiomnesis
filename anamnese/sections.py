"""Anamnesis section definitions matching docs/bilan-cr.docx anchors.

Each section carries its French anchor (the default, matching bilan-cr.docx)
and an English anchor (matching bilan-cr_en.docx). Helper accessors pick the
right one by report language.
"""
from dataclasses import dataclass


def norm(s: str) -> str:
    """Normalize docx text for matching: nbsp, curly apostrophes, case, spaces."""
    s = s.replace("\xa0", " ").replace("’", "'").replace("‘", "'")
    return " ".join(s.split()).lower()


@dataclass(frozen=True)
class Section:
    key: str
    heading: str          # French heading (normalized match against FR template)
    purpose: str          # French description used in the generation prompt
    stubs: tuple          # French lead-in prefixes of the stub paragraphs
    heading_en: str       # English heading (matches EN template)
    purpose_en: str       # English description used in the English prompt
    stubs_en: tuple       # English lead-in prefixes


INTRO_LEADIN = "Je rencontre ce jour"
INTRO_LEADIN_EN = "I am seeing today"


def heading(section: "Section", lang: str) -> str:
    return section.heading_en if lang == "en" else section.heading


def purpose(section: "Section", lang: str) -> str:
    return section.purpose_en if lang == "en" else section.purpose


def stubs(section: "Section", lang: str) -> tuple:
    return section.stubs_en if lang == "en" else section.stubs


def leadin(lang: str) -> str:
    return INTRO_LEADIN_EN if lang == "en" else INTRO_LEADIN


SECTIONS = [
    Section(
        key="plaintes",
        heading="Plaintes actuelles et retentissement fonctionnel",
        purpose=(
            "les plaintes actuelles du patient (cognitives : mémoire, attention, "
            "fonctions exécutives, cognition sociale, sphère instrumentale), leur "
            "retentissement en vie quotidienne et professionnelle, le mode de "
            "fonctionnement du patient, ses intérêts et habitudes, et sa "
            "consommation éventuelle de substances psychoactives"
        ),
        stubs=("Spontanément,",),
        heading_en="Current complaints and functional impact",
        purpose_en=(
            "the patient's current complaints (cognitive: memory, attention, "
            "executive functions, social cognition, instrumental sphere), their "
            "impact on daily and occupational life, the patient's way of "
            "functioning, their interests and habits, and any use of psychoactive "
            "substances"
        ),
        stubs_en=("Spontaneously,",),
    ),
    Section(
        key="atcd_perso",
        heading="Antécédents médicaux personnels",
        purpose=(
            "les antécédents médicaux personnels : d'abord neurologiques, puis "
            "psychiatriques au sens large (diagnostics, suivis, traitements)"
        ),
        stubs=(
            "Interrogée sur ses antécédents médicaux personnels,",
            "Sur le plan psychiatrique au sens large,",
        ),
        heading_en="Personal medical history",
        purpose_en=(
            "the personal medical history: first neurological, then psychiatric "
            "in the broad sense (diagnoses, follow-up, treatments)"
        ),
        stubs_en=(
            "Asked about their personal medical history,",
            "On the psychiatric level in the broad sense,",
        ),
    ),
    Section(
        key="atcd_fam",
        heading="Antécédents médicaux familiaux",
        purpose=(
            "les antécédents médicaux familiaux neurologiques et/ou "
            "psychiatriques, diagnostiqués ou suspectés"
        ),
        stubs=("Concernant ses antécédents familiaux,",),
        heading_en="Family medical history",
        purpose_en=(
            "the family medical history, neurological and/or psychiatric, "
            "diagnosed or suspected"
        ),
        stubs_en=("Regarding their family history,",),
    ),
    Section(
        key="developpement",
        heading="Développement, autonomie, mode de vie",
        purpose=(
            "la grossesse et le développement précoce, les apprentissages, la "
            "scolarité, le parcours professionnel, l'autonomie et le mode de vie"
        ),
        stubs=(
            "XX ne rapporte pas",
            "Dans son enfance,",
            "À l'école",
            "Sur le plan professionnel",
        ),
        heading_en="Development, autonomy, lifestyle",
        purpose_en=(
            "the pregnancy and early development, learning, schooling, "
            "occupational background, autonomy and lifestyle"
        ),
        stubs_en=(
            "XX does not report",
            "In childhood,",
            "At school",
            "On the occupational level",
        ),
    ),
    Section(
        key="thymie",
        heading="Thymie, sommeil, appétit",
        purpose="la thymie (moral, anxiété), le sommeil, l'appétit et l'alimentation",
        stubs=(
            "D'un point de vue thymique",
            "Concernant son sommeil,",
            "Enfin, sur le plan de l'alimentation,",
        ),
        heading_en="Mood, sleep, appetite",
        purpose_en="mood (morale, anxiety), sleep, appetite and eating",
        stubs_en=(
            "From a mood standpoint",
            "Regarding their sleep,",
            "Finally, with respect to eating,",
        ),
    ),
]
