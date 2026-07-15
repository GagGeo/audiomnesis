# Anamnèse — transcription et pré-rédaction locales

Outil 100 % local : enregistre l'entretien d'anamnèse, le transcrit (Whisper),
et pré-rédige les sections anamnestiques du compte-rendu (`docs/bilan-cr.docx`)
via un modèle de langage local (Ollama). **Aucune donnée ne quitte l'ordinateur.**

## Installation (une seule fois, avec Internet)

```bash
./install.sh
```

**Style de rédaction :** le style du clinicien (amorces « Spontanément, … »,
conventions i.e./e.g., guillemets) est encodé sous forme de canevas sans aucun
fait clinique dans `anamnese/prompts.py` (`STYLE_SKELETONS`). Aucun compte-rendu
réel n'est nécessaire ni utilisé par l'application — c'est volontaire : un vrai
compte-rendu dans le contexte du modèle risquait de faire fuir les faits d'un
patient dans le rapport d'un autre.

## Utilisation

1. Double-cliquer sur **`Anamnese.app`** (l'application doit rester dans le
   dossier du projet ; vous pouvez la glisser dans le Dock pour un accès rapide).
   `Anamnese.command` reste disponible si vous préférez lancer depuis le Terminal.
   Si l'app provient d'un téléchargement GitHub : clic droit → Ouvrir la
   première fois (application non signée).
2. Choisir Monsieur/Madame, vérifier le modèle et le dossier de sortie.
3. Trois entrées possibles :
   - **● Enregistrer** au début de l'entretien (consentement du patient requis),
     **■ Stop** à la fin ;
   - **« Ouvrir un audio… »** pour un enregistrement existant ;
   - **« Ouvrir un texte… »** (ou coller directement dans la zone de texte)
     pour une transcription ou des notes déjà écrites.
4. Relire/corriger le texte, puis **Générer le compte-rendu**.
5. Sortie : un dossier `CR_<date>/` est créé dans le dossier de sortie,
   contenant `CR_<date>.docx` (modèle rempli) et `CR_<date>_transcript.txt`.
   Le brouillon doit être relu et corrigé : c'est une aide à la rédaction,
   pas un compte-rendu final. Les conclusions restent à rédiger par le clinicien.

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
