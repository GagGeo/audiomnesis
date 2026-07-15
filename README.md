# Audiomnesis

**FR** — Outil 100 % local pour cliniciens : enregistre l'entretien d'anamnèse,
le transcrit (Whisper), et pré-rédige les sections anamnestiques d'un
compte-rendu Word à partir d'un modèle, via un modèle de langage local
(Ollama). **Aucune donnée ne quitte l'ordinateur.**

**EN** — Fully local tool for clinicians: records the anamnesis interview,
transcribes it (Whisper), and pre-drafts the anamnesis sections of a Word
report from a template, using a local language model (Ollama). **No data ever
leaves the computer.** The interface is available in French and English
(FR/EN switch in the app); the generated report is French clinical prose.

## Prérequis / Requirements

- macOS (Apple Silicon), ≥ 8 Go RAM, ~5 Go d'espace disque pour les modèles
- [Homebrew](https://brew.sh)
- [Ollama](https://ollama.com/download)
- Outils de développement Apple : `xcode-select --install`

## Installation (une seule fois, avec Internet)

```bash
git clone https://github.com/GagGeo/audiomnesis.git
cd audiomnesis
./install.sh
```

`install.sh` installe ffmpeg et whisper.cpp (Homebrew), crée l'environnement
Python, télécharge les deux modèles (Whisper ~570 Mo, gemma3:4b ~3,3 Go),
lance les tests et construit l'application.

## Utilisation

1. Double-cliquer sur **`Audiomnesis.app`** (l'application doit rester dans le
   dossier du projet ; glissez-la dans le Dock pour un accès rapide).
   Première ouverture d'une copie téléchargée : clic droit → Ouvrir
   (application non signée). Autorisez l'accès au micro et au dossier
   Documents quand macOS le demande. `Audiomnesis.command` reste disponible
   pour lancer depuis le Terminal.
2. Vérifier le modèle Word et le dossier de sortie ; choisir Monsieur/Madame.
3. Trois entrées possibles :
   - **● Enregistrer** au début de l'entretien (consentement du patient
     requis), **Arrêter** à la fin ;
   - **Ouvrir un audio…** pour un enregistrement existant ;
   - **Ouvrir un texte…** (ou coller directement) pour des notes déjà écrites.
4. Relire/corriger le texte, puis **Générer le compte-rendu**.
5. Sortie : un dossier `CR_<date>/` contenant le `.docx` rempli et la
   transcription `.txt`. **Le brouillon doit être relu et corrigé** : c'est une
   aide à la rédaction, pas un compte-rendu final. Les conclusions restent à
   rédiger par le clinicien.

## Adapter à votre pratique / Adapting to your practice

- **Modèle de compte-rendu** : remplacez `docs/bilan-cr.docx` par le vôtre.
  Les ancres de sections attendues sont définies dans `anamnese/sections.py`.
- **Style de rédaction** : le style est encodé sous forme de canevas SANS
  aucun fait clinique dans `anamnese/prompts.py` (`STYLE_SKELETONS`).
  N'y mettez jamais un vrai compte-rendu : un petit modèle local recopie des
  faits d'un patient dans le rapport d'un autre.
- **Modèle de langage** : `anamnese/config.py` (`OLLAMA_MODEL`). Sur 8 Go de
  RAM, restez sur un modèle ~4b sans mode « thinking » (gel de la machine
  constaté avec les 8b ; fuite du raisonnement dans le texte avec qwen3).

## Confidentialité / Privacy

- Transcription : whisper.cpp, processus local. Rédaction : Ollama sur
  `http://127.0.0.1:11434`. Fonctionne Wi-Fi coupé (test recommandé).
- Les enregistrements restent dans `recordings/` — supprimez-les
  régulièrement. Aucun fichier clinique ne doit être commité dans git.
- Consentement du patient requis pour l'enregistrement (RGPD).
