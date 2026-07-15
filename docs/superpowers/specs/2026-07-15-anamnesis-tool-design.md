# Anamnèse — Local transcription & report tool — Design

**Date:** 2026-07-15
**Status:** Approved by user

## Purpose

A fully local macOS desktop tool for a clinician (neuropsychologist). It records an
anamnesis consultation, transcribes it to French text, and drafts the anamnesis
sections of the clinician's report template (`docs/bilan-cr.docx`) in the
clinician's own writing style. Goal: eliminate blank-page and typing time. The
clinician always reviews and polishes the draft.

**Hard constraint: 100% local.** No patient data (audio, transcript, report) ever
leaves the machine. No network calls at runtime; models are downloaded once at
install time. The app must work with Wi-Fi off.

## Environment

- Apple M2, 8 GB RAM, macOS (Darwin 25.5.0)
- Ollama installed (has `mistral:latest`, `gemma3:1b`; will add `qwen3:8b`)
- ffmpeg installed via Homebrew
- Python available via Homebrew (system python3 is 3.14; app will use a
  dedicated virtualenv with whatever Python version its dependencies support)

## User flow

1. Double-click the app to open. Main window:
   - Big **● Enregistrer / ■ Stop** toggle button with elapsed-time counter
   - **« Ouvrir un audio… »** button to load an existing recording instead
   - Template path field (pre-filled with `docs/bilan-cr.docx`, changeable)
   - Output folder + base-name picker
2. Stop recording → transcription runs with a progress indicator
   (rough expectation: 5–15 min for a 60-min consultation on M2).
3. Transcript appears in an **editable text box**; the clinician can correct it.
4. Click **« Générer le compte-rendu »** → section-by-section generation with
   progress indicator.
5. Output written:
   - `CR_<date>.docx` — a filled copy of the template
   - `CR_<date>_transcript.txt` — the (possibly edited) transcript

## Architecture

Single Python application, Tkinter GUI (matches the user's existing tooling).
Pipeline stages run sequentially to respect the 8 GB RAM budget:

```
microphone ──► WAV on disk ──► whisper.cpp (large-v3-turbo, lang=fr)
                                      │
                              transcript (editable in UI)
                                      │
                     Ollama qwen3:8b, one call per template section
                                      │
                python-docx fills a copy of bilan-cr.docx + saves .txt
```

### Components

1. **Recorder** — captures the default input device to a WAV file, writing to
   disk continuously (crash-safe: a crash mid-consultation loses nothing; the
   partial WAV can be reopened via « Ouvrir un audio… »). Recordings are kept
   in a local `recordings/` folder until manually deleted.
2. **Transcriber** — Whisper `large-v3-turbo` via whisper.cpp (Apple-Silicon
   optimized, quantized model fits the RAM budget). Language forced to French.
   Merged transcript, no speaker diarization.
3. **Report generator** — one Ollama call per anamnesis section. Each prompt
   contains: the transcript, the section's purpose, and the corresponding
   section of the completed example (`docs/bilan-cr_completed.docx`) as a style
   model. Hard rule in every prompt: never output a real name — always
   « Monsieur/Madame XXX ». Whisper must be unloaded before Ollama runs.
4. **Header-field extractor** — one additional Ollama call extracts the
   patient-info header fields when mentioned in conversation (latéralité,
   langue maternelle, statut marital, niveau d'études, profession, motif de
   consultation, accompagnant); unmentioned fields stay blank. Names are never
   filled.
5. **Template filler** — python-docx opens a *copy* of the template and inserts
   generated text at the existing section anchors, preserving letterhead,
   styles, and layout. The original template is never modified. The
   conclusions section (« CONCLUSIONS DE L'ÉVALUATION NEUROPSYCHOLOGIQUE »)
   is left untouched — clinical judgment stays with the clinician.

### Template sections (anchors in `bilan-cr.docx`)

- « Plaintes actuelles et retentissement fonctionnel » (lead-in: « Spontanément, »)
- « Antécédents médicaux personnels » (lead-ins: « Interrogée sur ses antécédents
  médicaux personnels, » / « Sur le plan psychiatrique au sens large, »)
- « Antécédents médicaux familiaux » (lead-in: « Concernant ses antécédents familiaux, »)
- « Développement, autonomie, mode de vie »
- « Thymie, sommeil, appétit »
- Intro paragraph « Je rencontre ce jour » (brief context of the encounter)

## Error handling

- Ollama not running → app starts it automatically.
- Microphone permission missing → clear instructions (System Settings path).
- A section's generation fails → report is still produced with that section left
  as in the template; the UI names the failed section. Partial draft > crash.
- Disk-space and template-not-found checks before starting.

## Testing

- Unit tests for template filling against the real `bilan-cr.docx`
  (anchors found, formatting preserved, conclusions untouched).
- End-to-end test with a short French test recording.
- Privacy check: full run with networking disabled.

## Explicitly out of scope

- Speaker diarization (revisit only if merged transcripts prove insufficient)
- Filling the conclusions/test-results sections
- Real names anywhere in output (always M./Mme XXX; clinician substitutes later)
- Any cloud or network processing

## Known limitations (accepted)

- An 8B local model drafts at "good first draft" quality, not ready-to-sign.
- Recording a consultation requires patient consent (clinician's responsibility;
  the UI may include a small reminder).
