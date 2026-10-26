"""Interface strings, French and English.

The generated REPORT stays in French regardless of the interface language —
it is a French clinical document. Only the UI is translated.
"""
from anamnese import settings

STRINGS = {
    "fr": {
        "app_title": "Audiomnesis — session locale",
        "subtitle_prefix": "TRANSCRIPTION & PRÉ-RÉDACTION · ",
        "subtitle_local": "100 % LOCAL",
        "record": "●  Enregistrer",
        "stop": "Arrêter",
        "open_audio": "♪  Ouvrir un audio…",
        "open_text": "🗎  Ouvrir un texte…",
        "monsieur": "Monsieur",
        "madame": "Madame",
        "template_label": "MODÈLE",
        "output_label": "SORTIE",
        "report_lang_label": "LANGUE DU CR",
        "report_lang_auto": "Auto",
        "examples_label": "EXEMPLES DE STYLE",
        "examples_warn": ("⚠ Les comptes-rendus déposés ici doivent être "
                          "ANONYMISÉS : ils sont envoyés tels quels au modèle "
                          "local comme référence de style (format .docx)."),
        "filter_folder": "Dossier",
        "status_ready": "Prêt. Rappel : le patient doit avoir consenti à l'enregistrement.",
        "transcript_head": "TRANSCRIPTION — RELISEZ ET CORRIGEZ AVANT DE GÉNÉRER",
        "words": "mots",
        "placeholder": ("La transcription apparaîtra ici. Démarrez un enregistrement "
                        "ou ouvrez un fichier audio pour commencer…"),
        "privacy_note": ("Traitement effectué localement — aucune donnée ne quitte "
                         "cet appareil."),
        "generate": "✎  Générer le compte-rendu",
        "status_recording": "Enregistrement en cours → {name}",
        "status_transcribing": ("Transcription en cours… (plusieurs minutes pour "
                                "une consultation complète)"),
        "status_transcribed": ("Transcription terminée. Relisez, corrigez, puis "
                               "générez le compte-rendu."),
        "status_ollama": "Démarrage du modèle local (Ollama)…",
        "done_title": "Terminé",
        "error_title": "Erreur",
        "done_msg": "Compte-rendu écrit :\n{path}",
        "done_no_info": "Sections sans information dans l'entretien :",
        "done_failed": "Sections en échec (à rédiger à la main) :",
        "warn_empty_title": "Vide",
        "warn_empty": "Aucune transcription à traiter.",
        "err_template_title": "Modèle introuvable",
        "err_mic_title": "Micro indisponible",
        "err_mic": ("Impossible d'accéder au micro. Vérifiez :\nRéglages Système "
                    "→ Confidentialité et sécurité → Microphone,\npuis autorisez "
                    "Audiomnesis.\n\nDétail : {error}"),
        "filter_audio": "Audio",
        "filter_text": "Texte",
        "filter_all": "Tous",
        "filter_word": "Word",
    },
    "en": {
        "app_title": "Audiomnesis — local session",
        "subtitle_prefix": "TRANSCRIPTION & DRAFTING · ",
        "subtitle_local": "100 % LOCAL",
        "record": "●  Record",
        "stop": "Stop",
        "open_audio": "♪  Open audio…",
        "open_text": "🗎  Open text…",
        "monsieur": "Mr",
        "madame": "Ms",
        "template_label": "TEMPLATE",
        "output_label": "OUTPUT",
        "report_lang_label": "REPORT LANGUAGE",
        "report_lang_auto": "Auto",
        "examples_label": "STYLE EXAMPLES",
        "examples_warn": ("⚠ Reports placed here must be ANONYMIZED: they are "
                          "sent as-is to the local model as a style reference "
                          "(.docx format)."),
        "filter_folder": "Folder",
        "status_ready": "Ready. Reminder: the patient must have consented to the recording.",
        "transcript_head": "TRANSCRIPT — PROOFREAD AND CORRECT BEFORE GENERATING",
        "words": "words",
        "placeholder": ("The transcript will appear here. Start a recording or "
                        "open an audio file to begin…"),
        "privacy_note": "Processed locally — no data ever leaves this device.",
        "generate": "✎  Generate the report",
        "status_recording": "Recording → {name}",
        "status_transcribing": ("Transcribing… (takes several minutes for a full "
                                "consultation)"),
        "status_transcribed": ("Transcription finished. Proofread, correct, then "
                               "generate the report."),
        "status_ollama": "Starting the local model (Ollama)…",
        "done_title": "Done",
        "error_title": "Error",
        "done_msg": "Report written:\n{path}",
        "done_no_info": "Sections with no information in the interview:",
        "done_failed": "Failed sections (to write by hand):",
        "warn_empty_title": "Empty",
        "warn_empty": "No transcript to process.",
        "err_template_title": "Template not found",
        "err_mic_title": "Microphone unavailable",
        "err_mic": ("Cannot access the microphone. Check:\nSystem Settings → "
                    "Privacy & Security → Microphone,\nthen allow Audiomnesis."
                    "\n\nDetail: {error}"),
        "filter_audio": "Audio",
        "filter_text": "Text",
        "filter_all": "All",
        "filter_word": "Word",
    },
}


def load_lang() -> str:
    return settings.get("lang", "fr")


def save_lang(lang: str) -> None:
    settings.set("lang", lang)
