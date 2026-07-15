# Anamnèse — transcription et pré-rédaction locales

Outil 100 % local : enregistre l'entretien d'anamnèse, le transcrit (Whisper),
et pré-rédige les sections anamnestiques du compte-rendu (`docs/bilan-cr.docx`)
via un modèle de langage local (Ollama). **Aucune donnée ne quitte l'ordinateur.**

## Installation (une seule fois, avec Internet)

```bash
./install.sh
```

**Exemple de style requis :** placez un compte-rendu complété et anonymisé au
chemin `docs/bilan-cr_completed.docx`. L'application y lit vos formulations
(sections anamnestiques) pour imiter votre style. Ce fichier reste local :
il est exclu de git et ne doit jamais être publié.

## Utilisation

1. Double-cliquer sur `Anamnese.command`.
2. Choisir Monsieur/Madame, vérifier le modèle et le dossier de sortie.
3. **● Enregistrer** au début de l'entretien (consentement du patient requis),
   **■ Stop** à la fin — ou « Ouvrir un audio… » pour un fichier existant.
4. Relire/corriger la transcription, puis **Générer le compte-rendu**.
5. Sortie : `CR_<date>.docx` (modèle rempli) + `CR_<date>_transcript.txt`
   dans le dossier de sortie. Le brouillon doit être relu et corrigé : c'est une
   aide à la rédaction, pas un compte-rendu final. Les conclusions restent à
   rédiger par le clinicien.

## Confidentialité

- Transcription : whisper.cpp, processus local.
- Rédaction : Ollama sur http://127.0.0.1:11434, modèle local `gemma3:4b`.
- Fonctionne Wi-Fi coupé (test recommandé). Les enregistrements restent dans
  `recordings/` — pensez à les supprimer régulièrement.

## Notes techniques

- Python : venv local `.venv` (Python 3.14, Homebrew).
- Machine cible : Apple Silicon, 8 Go de RAM. Si la génération est trop lente,
  augmenter vers `qwen3:8b` est déconseillé sur 8 Go de RAM (gel de la machine constaté) ;
  les réglages mémoire se trouvent dans `anamnese/config.py`.
