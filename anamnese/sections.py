"""Anamnesis section definitions matching docs/bilan-cr.docx anchors."""
from dataclasses import dataclass


def norm(s: str) -> str:
    """Normalize docx text for matching: nbsp, curly apostrophes, case, spaces."""
    s = s.replace("\xa0", " ").replace("’", "'").replace("‘", "'")
    return " ".join(s.split()).lower()


@dataclass(frozen=True)
class Section:
    key: str
    heading: str        # exact heading paragraph text (normalized match)
    purpose: str        # French description used in the generation prompt
    stubs: tuple        # lead-in prefixes of the stub paragraphs after the heading


INTRO_LEADIN = "Je rencontre ce jour"

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
    ),
    Section(
        key="atcd_fam",
        heading="Antécédents médicaux familiaux",
        purpose=(
            "les antécédents médicaux familiaux neurologiques et/ou "
            "psychiatriques, diagnostiqués ou suspectés"
        ),
        stubs=("Concernant ses antécédents familiaux,",),
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
    ),
]
