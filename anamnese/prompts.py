"""Prompts for the local LLM, French and English. All calls go to the local
Ollama only. The report language (fr/en) selects the prompt set."""
from anamnese import sections

# ---------------------------------------------------------------- system -----
_SYSTEM = {
    "fr": """Tu es l'assistant de rédaction d'un neuropsychologue. Tu rédiges \
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
markdown, pas de commentaire, pas d'explication.""",
    "en": """You are the writing assistant of a neuropsychologist. You draft \
paragraphs of a neuropsychological examination report from the transcript of an \
anamnesis interview.

Absolute rules:
- NEVER write the patient's real first or last name. Always refer to them as \
"Mr XXX" or "Ms XXX".
- Invent NOTHING: use only the information present in the transcript. If a piece \
of information is not there, do not mention it.
- Write in the third person, in the present tense, in a professional clinical register.
- Quote the patient's striking expressions in double quotation marks ("...").
- Use the conventions i.e. and e.g. as in the style canvas provided.
- Reply ONLY with the drafted text: no title, no list, no markdown, no comment, \
no explanation.""",
}


def system_prompt(lang: str = "fr") -> str:
    return _SYSTEM.get(lang, _SYSTEM["fr"])


SYSTEM_PROMPT = _SYSTEM["fr"]  # back-compat default (French report)

NO_INFO = {"fr": "AUCUNE INFORMATION", "en": "NO INFORMATION"}


# ------------------------------------------------------------- skeletons -----
# Fact-free style skeletons distilled from the clinician's own reports.
# Square brackets mark slots to fill FROM THE TRANSCRIPT ONLY — the skeletons
# contain no clinical facts, so nothing can leak into a report.
_SKELETONS = {
    "fr": {
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
    },
    "en": {
        "plaintes": (
            "Spontaneously, Mr XXX first mentions difficulties [nature of the main "
            "complaint]. He indeed often explains \"[patient's expression]\", "
            "[clinical reformulation]. Mr XXX also mentions complaints [other "
            "cognitive domain], notably [detail] (i.e., [clinical term]).\n"
            "When asked about the [domain] domain, Mr XXX reports [description] "
            "(e.g., [concrete example reported by the patient]). Describing his "
            "way of functioning, he explains [description].\n"
            "Finally, asked about his use of psychoactive and/or addictive "
            "substances, Mr XXX explains [reported use, or its absence]."
        ),
        "atcd_perso": (
            "Asked about his personal medical history, Mr XXX [reported "
            "neurological history, or its absence]. He mentions [other somatic "
            "history reported].\n"
            "On the psychiatric level in the broad sense, Mr XXX reports [reported "
            "psychiatric history, with dates if mentioned]."
        ),
        "atcd_fam": (
            "Regarding his family history, Mr XXX mentions [condition] in [family "
            "member], [diagnosed or suspected]. He does not mention any other "
            "neurological and/or psychiatric family history, diagnosed and/or "
            "suspected."
        ),
        "developpement": (
            "Regarding his development, Mr XXX [elements concerning pregnancy and "
            "early childhood, or their absence]. As a child, Mr XXX [learning].\n"
            "During his schooling, Mr XXX explains [description of schooling] "
            "(e.g., [example reported]).\n"
            "On the occupational level, Mr XXX [career path and current situation]."
        ),
        "thymie": (
            "From a mood standpoint, Mr XXX reports a morale he describes as "
            "\"[patient's expression]\", [details].\n"
            "Regarding his sleep, Mr XXX [description of sleep].\n"
            "With respect to eating, Mr XXX [description of appetite and eating]."
        ),
    },
}


def skeletons(lang: str = "fr") -> dict:
    return _SKELETONS.get(lang, _SKELETONS["fr"])


STYLE_SKELETONS = _SKELETONS["fr"]  # back-compat default (French report)


# --------------------------------------------------------------- section -----
# Canvas framing: fact-free skeleton vs. the clinician's real anonymized reports.
_CANVAS = {
    "fr": {
        False: ("CANEVAS DE STYLE", "Les crochets [...] indiquent le type "
                "d'information à y placer — le canevas ne contient aucun fait : "
                "chaque fait doit provenir de la transcription."),
        True: ("EXEMPLES DE STYLE", "Ce sont des exemples anonymisés rédigés par "
               "le clinicien. Ils servent UNIQUEMENT de référence de STYLE (ton, "
               "tournures, vocabulaire). N'en copie AUCUN fait, nom, date ni "
               "contenu clinique : chaque fait doit provenir de la transcription."),
    },
    "en": {
        False: ("STYLE CANVAS", "The brackets [...] indicate the type of "
                "information to place there — the canvas contains no facts: every "
                "fact must come from the transcript."),
        True: ("STYLE EXAMPLES", "These are anonymized examples written by the "
               "clinician. They serve ONLY as a STYLE reference (tone, phrasing, "
               "vocabulary). Do NOT copy any fact, name, date or clinical content "
               "from them: every fact must come from the transcript."),
    },
}


def section_prompt(section, transcript, example, patient_title, lang="fr",
                   example_is_real=False):
    heading = sections.heading(section, lang)
    purpose = sections.purpose(section, lang)
    stub_list = " / ".join(f"« {s} »" for s in sections.stubs(section, lang))
    label, note = _CANVAS[lang][bool(example_is_real)]
    if lang == "en":
        return f"""Here is the {label.lower()} for the section to write. {note}

--- {label} ---
{example}
--- END {label} ---

Here is the transcript (or notes) of the anamnesis interview of {patient_title}. \
It is the ONLY authorized source of information:

--- TRANSCRIPT ---
{transcript}
--- END TRANSCRIPT ---

Write the "{heading}" section of the report, concerning {patient_title}.
Expected content: {purpose}.
Follow the structure of the examples, adapting it: if the transcript provides \
nothing for a given sentence, omit it. NEVER add a fact absent from the \
transcript. When it is natural, begin your paragraphs with the following \
lead-ins: {stub_list}. Separate paragraphs with a line break.

If the transcript contains no information for this section, reply exactly: \
{NO_INFO['en']}."""
    return f"""Voici le canevas de style de la section à rédiger. {note}

--- {label} ---
{example}
--- FIN {label} ---

Voici la transcription (ou les notes) de l'entretien d'anamnèse de \
{patient_title}. C'est la SEULE source d'information autorisée :

--- TRANSCRIPTION ---
{transcript}
--- FIN DE LA TRANSCRIPTION ---

Rédige la section « {heading} » du compte-rendu, concernant {patient_title}.
Contenu attendu : {purpose}.
Suis la structure du canevas, en adaptant : si la transcription ne fournit rien \
pour une phrase du canevas, omets cette phrase. N'ajoute JAMAIS un fait absent \
de la transcription. Lorsque c'est naturel, commence tes paragraphes par les \
amorces suivantes : {stub_list}. Sépare les paragraphes par un retour à la ligne.

Si la transcription ne contient aucune information pour cette section, réponds \
exactement : {NO_INFO['fr']}."""


def intro_prompt(transcript, patient_title, lang="fr"):
    if lang == "en":
        return f"""Here is the transcript of an anamnesis interview:

--- TRANSCRIPT ---
{transcript}
--- END TRANSCRIPT ---

Write ONE single introductory sentence of the report, beginning exactly with \
"{sections.INTRO_LEADIN_EN} {patient_title}," and stating, if the transcript \
allows: the age, the context and the reason for the consultation. One sentence, \
nothing else."""
    return f"""Voici la transcription d'un entretien d'anamnèse :

--- TRANSCRIPTION ---
{transcript}
--- FIN DE LA TRANSCRIPTION ---

Rédige UNE seule phrase d'introduction du compte-rendu commençant exactement par \
« {sections.INTRO_LEADIN} {patient_title}, » et précisant, si la transcription le \
permet : l'âge, le contexte et le motif de la consultation. Une phrase, rien d'autre."""


def header_prompt(transcript, lang="fr"):
    # The JSON keys stay identical across languages (they are internal field
    # identifiers); only the instruction language and the value language change.
    keys = ('{{"laterality": "...", "langue_maternelle": "...", '
            '"statut_marital": "...", "niveau_etudes": "...", "profession": "...", '
            '"motif_consultation": "...", "accompagnant": "..."}}')
    if lang == "en":
        return f"""Here is the transcript of an anamnesis interview:

--- TRANSCRIPT ---
{transcript}
--- END TRANSCRIPT ---

Extract the following administrative information if (and only if) it is \
mentioned. Reply ONLY with a JSON object, no surrounding text, with exactly \
these keys (value null if the information is not mentioned):
{keys}
The values are short expressions in English. Never include a proper name."""
    return f"""Voici la transcription d'un entretien d'anamnèse :

--- TRANSCRIPTION ---
{transcript}
--- FIN DE LA TRANSCRIPTION ---

Extrais les informations administratives suivantes si (et seulement si) elles sont \
mentionnées. Réponds UNIQUEMENT avec un objet JSON, sans texte autour, avec \
exactement ces clés (valeur null si l'information n'est pas mentionnée) :
{keys}
Les valeurs sont de courtes expressions en français. N'inclus jamais de nom propre."""


def notes_prompt(chunk, lang="fr"):
    if lang == "en":
        return f"""Here is an excerpt of the transcript of an anamnesis interview:

--- EXCERPT ---
{chunk}
--- END EXCERPT ---

Extract, as concise notes, ALL clinically relevant information: complaints and \
concrete examples, personal and family history, development, schooling, \
occupational background, mood, sleep, eating, substance use, striking patient \
quotes in "...". One note per line, starting with "- ". Add no interpretation \
and no proper name."""
    return f"""Voici un extrait de la transcription d'un entretien d'anamnèse :

--- EXTRAIT ---
{chunk}
--- FIN DE L'EXTRAIT ---

Extrais sous forme de notes concises TOUTES les informations cliniquement \
pertinentes : plaintes et exemples concrets, antécédents personnels et familiaux, \
développement, scolarité, parcours professionnel, thymie, sommeil, alimentation, \
consommations, citations marquantes du patient entre « ». Une note par ligne, \
commençant par « - ». N'ajoute aucune interprétation ni aucun nom propre."""
