# Anamnèse — transcription et pré-rédaction locales

Outil 100 % local : enregistre l'entretien d'anamnèse, le transcrit (Whisper),
et pré-rédige les sections anamnestiques du compte-rendu (`docs/bilan-cr.docx`)
via un modèle de langage local (Ollama). **Aucune donnée ne quitte l'ordinateur.**

## Installation (une seule fois, avec Internet)

```bash
./install.sh
```

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
- Rédaction : Ollama sur http://127.0.0.1:11434, modèle local `qwen3:8b`.
- Fonctionne Wi-Fi coupé (test recommandé). Les enregistrements restent dans
  `recordings/` — pensez à les supprimer régulièrement.

## Notes techniques

- Python : venv local `.venv` (Python 3.14, Homebrew).
- Machine cible : Apple Silicon, 8 Go de RAM. Si la génération est trop lente,
  réduire `OLLAMA_NUM_CTX` à 8192 et `CONDENSE_TOKEN_THRESHOLD` à 4500 dans
  `anamnese/config.py`, ou passer `OLLAMA_MODEL` à `qwen3:4b`.
