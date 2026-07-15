"""French prompts for the local LLM. All calls go to the local Ollama only."""

SYSTEM_PROMPT = """Tu es l'assistant de rédaction d'un neuropsychologue. Tu rédiges \
des paragraphes de compte-rendu d'examen neuropsychologique à partir de la \
transcription d'un entretien d'anamnèse.

Règles absolues :
- N'écris JAMAIS le nom ou le prénom réel du patient. Désigne-le toujours par \
« Monsieur XXX » ou « Madame XXX ».
- N'invente RIEN : n'utilise que les informations présentes dans la transcription. \
Si une information n'y figure pas, ne la mentionne pas.
- Rédige à la troisième personne, au présent, dans un registre clinique professionnel.
- Reprends les expressions marquantes du patient entre guillemets français (« ... »).
- Utilise les conventions i.e. et e.g. comme dans l'exemple de style fourni.
- Réponds UNIQUEMENT avec le texte rédigé : pas de titre, pas de liste, pas de \
markdown, pas de commentaire, pas d'explication."""


# Fact-free style skeletons distilled from the clinician's own reports.
# Square brackets mark slots to fill FROM THE TRANSCRIPT ONLY — the skeletons
# contain no clinical facts, so nothing can leak into a report.
STYLE_SKELETONS = {
    "plaintes": (
        "Spontanément, Monsieur XXX mentionne en premier lieu des difficultés "
        "[nature de la plainte principale]. Il explique en effet souvent "
        "« [expression du patient] », [reformulation clinique]. Monsieur XXX "
        "mentionne également des plaintes [autre sphère cognitive], avec "
        "notamment [précision] (i.e., [terme clinique]).\n"
        "Sur demande et interrogé sur la sphère [sphère], Monsieur XXX rapporte "
        "[description] (e.g., [exemple concret rapporté par le patient]). "
        "Précisant son mode de fonctionnement, il explique [description].\n"
        "Enfin, interrogé sur sa consommation de substances psychoactives et/ou "
        "addictives, Monsieur XXX explique [consommations rapportées, ou leur absence]."
    ),
    "atcd_perso": (
        "Interrogé sur ses antécédents médicaux personnels, Monsieur XXX "
        "[antécédents neurologiques rapportés, ou leur absence]. Il mentionne "
        "[autres antécédents somatiques rapportés].\n"
        "Sur le plan psychiatrique au sens large, Monsieur XXX rapporte "
        "[antécédents psychiatriques rapportés, avec dates si mentionnées]."
    ),
    "atcd_fam": (
        "Concernant ses antécédents familiaux, Monsieur XXX mentionne "
        "[antécédent] chez [membre de la famille], [diagnostiqué ou suspecté]. "
        "Il ne mentionne pas d'autres antécédents familiaux neurologiques et/ou "
        "psychiatriques, diagnostiqués et/ou suspectés."
    ),
    "developpement": (
        "Concernant son développement, Monsieur XXX [éléments concernant la "
        "grossesse et la petite enfance, ou leur absence]. Enfant, Monsieur XXX "
        "[apprentissages].\n"
        "Durant sa scolarité, Monsieur XXX explique [description de la "
        "scolarité] (e.g., [exemple rapporté]).\n"
        "Sur le plan professionnel, Monsieur XXX [parcours et situation "
        "professionnelle]."
    ),
    "thymie": (
        "D'un point de vue thymique, Monsieur XXX rapporte un moral qu'il "
        "qualifie de « [expression du patient] », [précisions].\n"
        "Concernant son sommeil, Monsieur XXX [description du sommeil].\n"
        "Sur le plan alimentaire, Monsieur XXX [description de l'appétit et de "
        "l'alimentation]."
    ),
}


def section_prompt(section, transcript, example, patient_title):
    stubs = " / ".join(f"« {s} »" for s in section.stubs)
    return f"""Voici le canevas de style de la section à rédiger. Les crochets \
[…] indiquent le type d'information à y placer — le canevas ne contient aucun \
fait : chaque fait doit provenir de la transcription.

--- CANEVAS DE STYLE ---
{example}
--- FIN DU CANEVAS ---

Voici la transcription (ou les notes) de l'entretien d'anamnèse de \
{patient_title}. C'est la SEULE source d'information autorisée :

--- TRANSCRIPTION ---
{transcript}
--- FIN DE LA TRANSCRIPTION ---

Rédige la section « {section.heading} » du compte-rendu, concernant {patient_title}.
Contenu attendu : {section.purpose}.
Suis la structure du canevas, en adaptant : si la transcription ne fournit rien \
pour une phrase du canevas, omets cette phrase. N'ajoute JAMAIS un fait absent \
de la transcription. Lorsque c'est naturel, commence tes paragraphes par les \
amorces suivantes : {stubs}. Sépare les paragraphes par un retour à la ligne.

Si la transcription ne contient aucune information pour cette section, réponds \
exactement : AUCUNE INFORMATION."""


def intro_prompt(transcript, patient_title):
    return f"""Voici la transcription d'un entretien d'anamnèse :

--- TRANSCRIPTION ---
{transcript}
--- FIN DE LA TRANSCRIPTION ---

Rédige UNE seule phrase d'introduction du compte-rendu commençant exactement par \
« Je rencontre ce jour {patient_title}, » et précisant, si la transcription le \
permet : l'âge, le contexte et le motif de la consultation. Une phrase, rien d'autre."""


def header_prompt(transcript):
    return f"""Voici la transcription d'un entretien d'anamnèse :

--- TRANSCRIPTION ---
{transcript}
--- FIN DE LA TRANSCRIPTION ---

Extrais les informations administratives suivantes si (et seulement si) elles sont \
mentionnées. Réponds UNIQUEMENT avec un objet JSON, sans texte autour, avec \
exactement ces clés (valeur null si l'information n'est pas mentionnée) :
{{"laterality": "Droitier|Gaucher|Ambidextre ou null",
"langue_maternelle": "...", "statut_marital": "...", "niveau_etudes": "...",
"profession": "...", "motif_consultation": "...", "accompagnant": "..."}}
Les valeurs sont de courtes expressions en français. N'inclus jamais de nom propre."""


def notes_prompt(chunk):
    return f"""Voici un extrait de la transcription d'un entretien d'anamnèse :

--- EXTRAIT ---
{chunk}
--- FIN DE L'EXTRAIT ---

Extrais sous forme de notes concises TOUTES les informations cliniquement \
pertinentes : plaintes et exemples concrets, antécédents personnels et familiaux, \
développement, scolarité, parcours professionnel, thymie, sommeil, alimentation, \
consommations, citations marquantes du patient entre « ». Une note par ligne, \
commençant par « - ». N'ajoute aucune interprétation ni aucun nom propre."""
