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


def section_prompt(section, transcript, example, patient_title):
    stubs = " / ".join(f"« {s} »" for s in section.stubs)
    return f"""Voici la transcription (ou les notes) d'un entretien d'anamnèse :

--- TRANSCRIPTION ---
{transcript}
--- FIN DE LA TRANSCRIPTION ---

Rédige la section « {section.heading} » du compte-rendu, concernant {patient_title}.
Contenu attendu : {section.purpose}.
Lorsque c'est naturel, commence tes paragraphes par les amorces suivantes : {stubs}.
Sépare les paragraphes par un retour à la ligne.

Exemple de style, issu d'un AUTRE patient — imite uniquement le style, ne reprends \
aucun élément de son contenu :
--- EXEMPLE DE STYLE ---
{example}
--- FIN DE L'EXEMPLE ---

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
