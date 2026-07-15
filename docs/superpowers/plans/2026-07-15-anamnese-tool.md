# Anamnèse Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fully local macOS Tkinter app: record an anamnesis consultation → Whisper transcription (French) → Ollama drafts the anamnesis sections of `docs/bilan-cr.docx` in the clinician's style → filled .docx + transcript .txt.

**Architecture:** Single Python package `anamnese/` with one module per pipeline stage (recorder, transcriber, ollama client, condenser, prompts, generator, docx filler) and a thin Tkinter GUI (`app.py`). Stages run sequentially (8 GB RAM budget). whisper.cpp runs as a subprocess (memory freed on exit) before any Ollama call.

**Tech Stack:** Python 3 (Homebrew, venv), Tkinter, sounddevice + soundfile (recording), whisper.cpp `whisper-cli` via Homebrew + `ggml-large-v3-turbo-q5_0` model, Ollama HTTP API (localhost) with `qwen3:8b`, python-docx, pytest, ffmpeg (already installed).

**Reference spec:** `docs/superpowers/specs/2026-07-15-anamnesis-tool-design.md`

**Verified facts about the environment (do not re-derive):**
- Apple M2, 8 GB RAM. `ollama` 0.31.2 installed with `mistral:latest`, `gemma3:1b`. `ffmpeg` in PATH. `brew` available; formula `whisper-cpp` 1.9.1 exists, not installed. System `python3` is 3.14 (Homebrew).
- `docs/bilan-cr.docx` body paragraphs (index | text) — these are the anchors:
  - 6: `Je rencontre ce jour ` — intro paragraph
  - 20: `Plaintes actuelles et retentissement fonctionnel` heading; stub 21 `Spontanément, `
  - 23: `Antécédents médicaux personnels` heading; stubs 24 `Interrogée sur ses antécédents médicaux personnels, `, 25 `Sur le plan psychiatrique au sens large, `
  - 27: `Antécédents médicaux familiaux` heading; stub 28 `Concernant ses antécédents familiaux, `
  - 31: `Développement, autonomie, mode de vie ` heading; stubs 32 `XX ne rapporte pas d’éléments…grossesse.`, 33 `Dans son enfance, `, 34 `À l’école `, 35 `Sur le plan professionnel `
  - 37: `Thymie, sommeil, appétit` heading; stubs 38 `D’un point de vue thymique `, 39 `Concernant son sommeil, `, 40 `Enfin, sur le plan de l’alimentation, `
  - Conclusions live at paragraphs 8–11 — NEVER touched.
  - Headings/stubs use the curly apostrophe `’` (U+2019) and sometimes `\xa0` before `:` — text matching MUST normalize both.
- Patient-info fields are in `document.tables[1]` (table index 1), one field per cell-paragraph: r1c0 has `NOM Prénom :`, `Date de naissance : (ans)`, `Latéralité :`, `Langue maternelle :`; r1c1 has `Statut marital :`, `Niveau d'études :`, `NSC (Barbizet) :`, `Profession :`; r2c0 has `Motif de consultation :`, `Évaluation neuropsychologique n° :`, `Accompagnant :`.
- `docs/bilan-cr_completed.docx` uses the same headings; its section bodies are the style examples (anonymized). Its body paragraphs are clean (team lists are in headers/textboxes, not body).

**Global conventions for all tasks:**
- Run everything with the project venv: `./.venv/bin/python`, `./.venv/bin/pytest`.
- All French user-facing strings; code and identifiers in English.
- Never send data anywhere except `http://127.0.0.1:11434` (Ollama).

---

### Task 1: Scaffolding, venv, .gitignore fix

**Files:**
- Modify: `.gitignore`
- Create: `requirements.txt`, `anamnese/__init__.py`, `anamnese/config.py`, `tests/__init__.py`, `tests/test_config.py`

- [ ] **Step 1: Fix .gitignore** (current one ignores `*.txt`, which would hide `requirements.txt`)

Replace the whole file with:

```gitignore
.DS_Store
.venv/
__pycache__/
*.pyc
recordings/
output/
models/
```

- [ ] **Step 2: Create requirements.txt**

```
sounddevice
soundfile
python-docx
pytest
```

- [ ] **Step 3: Create venv and install deps**

Run: `python3 -m venv .venv && ./.venv/bin/pip install -q -r requirements.txt`
Expected: exits 0. If `sounddevice` or `soundfile` fail to build on Python 3.14, retry with `python3.13 -m venv .venv` (install via `brew install python@3.13` if needed) — record which Python was used in the README later.

- [ ] **Step 4: Write config module and a smoke test**

`anamnese/__init__.py`: empty file.

`anamnese/config.py`:

```python
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = APP_DIR / "docs"
MODELS_DIR = APP_DIR / "models"
RECORDINGS_DIR = APP_DIR / "recordings"

DEFAULT_TEMPLATE = DOCS_DIR / "bilan-cr.docx"
STYLE_EXAMPLE_DOCX = DOCS_DIR / "bilan-cr_completed.docx"

WHISPER_MODEL = MODELS_DIR / "ggml-large-v3-turbo-q5_0.bin"
WHISPER_BIN = "whisper-cli"  # from `brew install whisper-cpp`

OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "qwen3:8b"
OLLAMA_NUM_CTX = 12288
OLLAMA_TIMEOUT = 900  # seconds per call; an 8 GB machine can be slow

SAMPLE_RATE = 16000  # whisper.cpp native input format
CHANNELS = 1

# Transcripts longer than this (estimated tokens, ~3 chars/token in French)
# are condensed to notes before section generation, to fit OLLAMA_NUM_CTX.
CONDENSE_TOKEN_THRESHOLD = 7000
```

`tests/__init__.py`: empty file.

`tests/test_config.py`:

```python
from anamnese import config

def test_template_files_exist():
    assert config.DEFAULT_TEMPLATE.exists()
    assert config.STYLE_EXAMPLE_DOCX.exists()

def test_ollama_url_is_localhost():
    assert config.OLLAMA_URL.startswith("http://127.0.0.1")
```

- [ ] **Step 5: Run tests**

Run: `./.venv/bin/pytest tests/ -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add .gitignore requirements.txt anamnese tests
git commit -m "feat: project scaffolding, config, venv"
```

---

### Task 2: Section definitions and text normalization

**Files:**
- Create: `anamnese/sections.py`
- Test: `tests/test_sections.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_sections.py`:

```python
from anamnese.sections import SECTIONS, INTRO_LEADIN, norm

def test_norm_handles_nbsp_and_curly_apostrophe():
    assert norm("Niveau d’études\xa0: ") == "niveau d'études :"
    assert norm("  Thymie,   sommeil, appétit ") == "thymie, sommeil, appétit"

def test_five_sections_with_keys_and_stubs():
    keys = [s.key for s in SECTIONS]
    assert keys == ["plaintes", "atcd_perso", "atcd_fam", "developpement", "thymie"]
    for s in SECTIONS:
        assert s.heading and s.purpose and s.stubs

def test_intro_leadin():
    assert norm(INTRO_LEADIN) == "je rencontre ce jour"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/bin/pytest tests/test_sections.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'anamnese.sections'`

- [ ] **Step 3: Implement**

`anamnese/sections.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/bin/pytest tests/test_sections.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add anamnese/sections.py tests/test_sections.py
git commit -m "feat: section definitions and docx text normalization"
```

---

### Task 3: Style-example extraction from the completed report

**Files:**
- Create: `anamnese/examples.py`
- Test: `tests/test_examples.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_examples.py`:

```python
from anamnese import config
from anamnese.examples import extract_examples

def test_extracts_all_five_sections_from_real_completed_docx():
    ex = extract_examples(config.STYLE_EXAMPLE_DOCX)
    assert set(ex) == {"plaintes", "atcd_perso", "atcd_fam", "developpement", "thymie"}
    assert "Spontanément" in ex["plaintes"]
    assert "Concernant ses antécédents familiaux" in ex["atcd_fam"]
    # style examples must not include next section's heading text
    assert "Antécédents médicaux personnels" not in ex["plaintes"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/bin/pytest tests/test_examples.py -v`
Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Implement**

`anamnese/examples.py`:

```python
"""Extract per-section style examples from a completed report docx."""
from pathlib import Path

import docx

from anamnese.sections import SECTIONS, norm

_HEADINGS = {norm(s.heading): s.key for s in SECTIONS}


def extract_examples(completed_docx: Path) -> dict:
    """Map section key -> example text (paragraphs joined by newline)."""
    doc = docx.Document(str(completed_docx))
    out, current = {}, None
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue
        n = norm(text)
        if n in _HEADINGS:
            current = _HEADINGS[n]
            out[current] = []
        elif current and n.isupper() is False and n == n.upper():
            current = None  # an all-caps title ends the anamnesis block
        elif current:
            out[current].append(text)
    return {k: "\n".join(v) for k, v in out.items() if v}
```

Note: the `n == n.upper()` guard stops collection at all-caps titles like
`CONCLUSIONS…`. Normalized text is lowercase, so compare against the *original*:
use `text == text.upper() and len(text) > 8` instead if the test fails —
verify against the real docx and keep whichever passes.

- [ ] **Step 4: Run tests, fix the all-caps guard if needed, until green**

Run: `./.venv/bin/pytest tests/test_examples.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add anamnese/examples.py tests/test_examples.py
git commit -m "feat: style example extraction from completed report"
```

---

### Task 4: Template filler (docx output)

**Files:**
- Create: `anamnese/docx_filler.py`
- Test: `tests/test_docx_filler.py`

- [ ] **Step 1: Write the failing tests** (they run against the REAL template)

`tests/test_docx_filler.py`:

```python
import docx
import pytest

from anamnese import config
from anamnese.docx_filler import fill_report
from anamnese.sections import norm

SECTION_TEXTS = {
    "plaintes": "Spontanément, Monsieur XXX mentionne une plainte A.\nSur demande, il précise B.",
    "atcd_perso": "Interrogé sur ses antécédents, Monsieur XXX rapporte C.",
    "atcd_fam": "Concernant ses antécédents familiaux, Monsieur XXX mentionne D.",
    "developpement": "Concernant son développement, E.\nDurant sa scolarité, F.\nSur le plan professionnel, G.",
    "thymie": None,  # section that failed / had no info: must stay as template stubs
}
HEADER = {"laterality": "Droitier", "langue_maternelle": "Français",
          "profession": "Enseignant", "accompagnant": None}


@pytest.fixture
def filled(tmp_path):
    out = tmp_path / "out.docx"
    fill_report(config.DEFAULT_TEMPLATE, out,
                intro_text="Je rencontre ce jour Monsieur XXX pour un bilan.",
                section_texts=SECTION_TEXTS, header_fields=HEADER)
    return docx.Document(str(out))


def _body(doc):
    return [p.text for p in doc.paragraphs]


def test_sections_filled_with_multiple_paragraphs(filled):
    body = _body(filled)
    assert "Spontanément, Monsieur XXX mentionne une plainte A." in body
    assert "Sur demande, il précise B." in body
    assert "Durant sa scolarité, F." in body


def test_failed_section_keeps_template_stubs(filled):
    assert any(norm(t).startswith("d'un point de vue thymique") for t in _body(filled))


def test_intro_filled(filled):
    assert "Je rencontre ce jour Monsieur XXX pour un bilan." in _body(filled)


def test_conclusions_untouched(filled):
    body = _body(filled)
    assert any(norm(t) == norm("L’examen de met en évidence ") for t in body)
    assert any(norm(t) == norm("Dans ce contexte, nous recommandons") for t in body)


def test_header_fields_filled_only_when_present(filled):
    cells = "\n".join(c.text for r in filled.tables[1].rows for c in r.cells)
    assert "Latéralité : Droitier" in cells.replace("\xa0", " ")
    assert "Profession : Enseignant" in cells.replace("\xa0", " ").replace("  ", " ")
    assert "Accompagnant :" in cells.replace("\xa0", " ")  # left blank, not "None"


def test_original_template_unmodified():
    import hashlib
    h = hashlib.sha256(config.DEFAULT_TEMPLATE.read_bytes()).hexdigest()
    assert h  # recorded before any fill in this test session
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/bin/pytest tests/test_docx_filler.py -v`
Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Implement**

`anamnese/docx_filler.py`:

```python
"""Fill a copy of the report template with generated text, preserving layout."""
import copy
from pathlib import Path

import docx

from anamnese.sections import SECTIONS, INTRO_LEADIN, norm

# label prefix (normalized) -> header_fields key, for document.tables[1]
_HEADER_LABELS = {
    "latéralité :": "laterality",
    "langue maternelle :": "langue_maternelle",
    "statut marital :": "statut_marital",
    "niveau d'études :": "niveau_etudes",
    "profession :": "profession",
    "motif de consultation :": "motif_consultation",
    "accompagnant :": "accompagnant",
}


def _set_text(par, text):
    """Replace a paragraph's text, keeping the first run's formatting."""
    if par.runs:
        par.runs[0].text = text
        for run in par.runs[1:]:
            run._element.getparent().remove(run._element)
    else:
        par.add_run(text)


def _insert_paragraph_after(par, text):
    """Clone `par` (same style/formatting), set its text, insert after `par`."""
    new_el = copy.deepcopy(par._p)
    par._p.addnext(new_el)
    new_par = docx.text.paragraph.Paragraph(new_el, par._parent)
    _set_text(new_par, text)
    return new_par


def _find_paragraph(doc, predicate):
    for i, p in enumerate(doc.paragraphs):
        if predicate(p.text):
            return i, p
    return None, None


def _section_stub_paragraphs(doc, section):
    """Stub paragraphs = paragraphs after the heading until the next heading."""
    headings = {norm(s.heading) for s in SECTIONS}
    idx, _ = _find_paragraph(doc, lambda t: norm(t) == norm(section.heading))
    if idx is None:
        raise ValueError(f"Heading not found: {section.heading}")
    stubs = []
    for p in doc.paragraphs[idx + 1:]:
        if norm(p.text) in headings:
            break
        if p.text.strip():
            stubs.append(p)
    return stubs


def _fill_section(doc, section, text):
    stubs = _section_stub_paragraphs(doc, section)
    if not stubs:
        raise ValueError(f"No stub paragraphs under: {section.heading}")
    paras = [t.strip() for t in text.split("\n") if t.strip()]
    # remove extra stubs beyond the first, then grow from the first
    anchor = stubs[0]
    for p in stubs[1:]:
        p._p.getparent().remove(p._p)
    _set_text(anchor, paras[0])
    for t in paras[1:]:
        anchor = _insert_paragraph_after(anchor, t)


def _fill_header_fields(doc, header_fields):
    table = doc.tables[1]
    seen = set()
    for row in table.rows:
        for cell in row.cells:
            if id(cell._tc) in seen:
                continue
            seen.add(id(cell._tc))
            for p in cell.paragraphs:
                n = norm(p.text)
                for label, key in _HEADER_LABELS.items():
                    value = header_fields.get(key)
                    if value and n == label:
                        _set_text(p, p.text.rstrip() + " " + str(value))


def fill_report(template_path: Path, output_path: Path, intro_text: str,
                section_texts: dict, header_fields: dict) -> None:
    """Write output_path from template_path. Never modifies the template.

    section_texts: section key -> generated text (paragraphs separated by
    newline) or None to leave the template stubs untouched.
    """
    doc = docx.Document(str(template_path))
    if intro_text:
        _, intro_par = _find_paragraph(
            doc, lambda t: norm(t).startswith(norm(INTRO_LEADIN)))
        if intro_par is not None:
            _set_text(intro_par, intro_text)
    for section in SECTIONS:
        text = section_texts.get(section.key)
        if text:
            _fill_section(doc, section, text)
    if header_fields:
        _fill_header_fields(doc, header_fields)
    doc.save(str(output_path))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/bin/pytest tests/test_docx_filler.py -v`
Expected: 6 passed. Debug notes if failing: header labels in the docx contain
`\xa0` and trailing spaces — the `norm()` equality should absorb both; the
`Niveau d'études` label may use U+2019, also absorbed by `norm()`.

- [ ] **Step 5: Manual visual check**

Run:
```bash
./.venv/bin/python - <<'EOF'
from anamnese import config
from anamnese.docx_filler import fill_report
fill_report(config.DEFAULT_TEMPLATE, "/tmp/check.docx",
            "Je rencontre ce jour Monsieur XXX.",
            {"plaintes": "Spontanément, Monsieur XXX évoque un test.\nPar ailleurs, second paragraphe."},
            {"laterality": "Droitier"})
EOF
open /tmp/check.docx
```
Expected: letterhead, staff columns, fonts identical to the template; filled text visible under « Plaintes actuelles ».

- [ ] **Step 6: Commit**

```bash
git add anamnese/docx_filler.py tests/test_docx_filler.py
git commit -m "feat: docx template filler preserving layout"
```

---

### Task 5: Prompts

**Files:**
- Create: `anamnese/prompts.py`
- Test: `tests/test_prompts.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_prompts.py`:

```python
from anamnese.prompts import (SYSTEM_PROMPT, section_prompt, intro_prompt,
                              header_prompt, notes_prompt)
from anamnese.sections import SECTIONS

def test_system_prompt_bans_real_names():
    assert "XXX" in SYSTEM_PROMPT and "JAMAIS" in SYSTEM_PROMPT

def test_section_prompt_contains_all_parts():
    s = SECTIONS[0]
    p = section_prompt(s, "TRANSCRIPT_SENTINEL", "EXAMPLE_SENTINEL", "Madame XXX")
    for token in ("TRANSCRIPT_SENTINEL", "EXAMPLE_SENTINEL", s.heading,
                  "Madame XXX", "Spontanément,", "AUCUNE INFORMATION"):
        assert token in p

def test_header_prompt_requests_json_keys():
    p = header_prompt("T")
    for key in ("laterality", "langue_maternelle", "statut_marital",
                "niveau_etudes", "profession", "motif_consultation",
                "accompagnant"):
        assert key in p

def test_intro_and_notes_prompts():
    assert "Je rencontre ce jour" in intro_prompt("T", "Monsieur XXX")
    assert "notes" in notes_prompt("T").lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/bin/pytest tests/test_prompts.py -v`
Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Implement**

`anamnese/prompts.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/bin/pytest tests/test_prompts.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add anamnese/prompts.py tests/test_prompts.py
git commit -m "feat: French generation prompts with anonymity rules"
```

---

### Task 6: Ollama client

**Files:**
- Create: `anamnese/ollama_client.py`
- Test: `tests/test_ollama_client.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_ollama_client.py`:

```python
import json
from unittest import mock

from anamnese.ollama_client import OllamaClient, parse_json_reply


def _fake_urlopen(payload):
    resp = mock.MagicMock()
    resp.read.return_value = json.dumps(payload).encode()
    resp.__enter__ = lambda s: resp
    resp.__exit__ = mock.MagicMock(return_value=False)
    return mock.MagicMock(return_value=resp)


def test_generate_posts_to_localhost_and_returns_text():
    client = OllamaClient(model="qwen3:8b")
    fake = _fake_urlopen({"response": "  Bonjour.  "})
    with mock.patch("anamnese.ollama_client.urllib.request.urlopen", fake):
        out = client.generate("prompt", system="sys")
    assert out == "Bonjour."
    req = fake.call_args[0][0]
    assert req.full_url.startswith("http://127.0.0.1:11434")
    body = json.loads(req.data)
    assert body["stream"] is False
    assert body["think"] is False           # qwen3 thinking disabled
    assert body["options"]["num_ctx"] > 0


def test_think_flag_only_for_qwen3():
    client = OllamaClient(model="mistral:latest")
    fake = _fake_urlopen({"response": "x"})
    with mock.patch("anamnese.ollama_client.urllib.request.urlopen", fake):
        client.generate("p")
    assert "think" not in json.loads(fake.call_args[0][0].data)


def test_parse_json_reply_strips_fences_and_noise():
    raw = "Voici :\n```json\n{\"a\": 1}\n```\nmerci"
    assert parse_json_reply(raw) == {"a": 1}
    assert parse_json_reply('{"b": null}') == {"b": None}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/bin/pytest tests/test_ollama_client.py -v`
Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Implement**

`anamnese/ollama_client.py`:

```python
"""Minimal client for the local Ollama server. Localhost only, stdlib only."""
import json
import os
import subprocess
import time
import urllib.error
import urllib.request

from anamnese import config


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, model=config.OLLAMA_MODEL, url=config.OLLAMA_URL,
                 timeout=config.OLLAMA_TIMEOUT):
        self.model, self.url, self.timeout = model, url, timeout

    def is_running(self):
        try:
            with urllib.request.urlopen(self.url + "/api/tags", timeout=3):
                return True
        except (urllib.error.URLError, OSError):
            return False

    def ensure_running(self):
        """Start `ollama serve` if needed. Memory-friendly env for 8 GB Macs."""
        if self.is_running():
            return
        env = dict(os.environ,
                   OLLAMA_FLASH_ATTENTION="1", OLLAMA_KV_CACHE_TYPE="q8_0")
        subprocess.Popen(["ollama", "serve"], env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(30):
            time.sleep(1)
            if self.is_running():
                return
        raise OllamaError("Impossible de démarrer Ollama (ollama serve).")

    def generate(self, prompt, system=None, num_predict=1500):
        body = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3,
                        "num_ctx": config.OLLAMA_NUM_CTX,
                        "num_predict": num_predict},
        }
        if system:
            body["system"] = system
        if self.model.startswith("qwen3"):
            body["think"] = False
        req = urllib.request.Request(
            self.url + "/api/generate",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read())
        except (urllib.error.URLError, OSError) as e:
            raise OllamaError(f"Échec de l'appel au modèle local : {e}") from e
        return data.get("response", "").strip()


def parse_json_reply(raw: str) -> dict:
    """Extract the first JSON object from a possibly noisy model reply."""
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise ValueError(f"Pas de JSON dans la réponse : {raw[:200]!r}")
    return json.loads(raw[start:end + 1])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/bin/pytest tests/test_ollama_client.py -v`
Expected: 3 passed.

- [ ] **Step 5: Live smoke test against the real Ollama (mistral, small prompt)**

Run:
```bash
./.venv/bin/python - <<'EOF'
from anamnese.ollama_client import OllamaClient
c = OllamaClient(model="mistral:latest")
c.ensure_running()
print(c.generate("Réponds uniquement : OK", num_predict=10))
EOF
```
Expected: prints something containing "OK" within ~30 s.

- [ ] **Step 6: Commit**

```bash
git add anamnese/ollama_client.py tests/test_ollama_client.py
git commit -m "feat: local Ollama client with auto-start and JSON parsing"
```

---

### Task 7: Condenser (long transcripts → notes)

**Files:**
- Create: `anamnese/condenser.py`
- Test: `tests/test_condenser.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_condenser.py`:

```python
from anamnese.condenser import estimate_tokens, chunk_text, prepare_source

class FakeClient:
    def __init__(self):
        self.calls = []
    def generate(self, prompt, system=None, num_predict=1500):
        self.calls.append(prompt)
        return f"- note {len(self.calls)}"

def test_estimate_tokens_roughly_chars_over_three():
    assert estimate_tokens("a" * 3000) == 1000

def test_chunk_text_splits_with_overlap():
    words = " ".join(f"w{i}" for i in range(5000))
    chunks = chunk_text(words, chunk_words=2200, overlap_words=200)
    assert len(chunks) == 3
    assert chunks[1].split()[0] == "w2000"  # overlap: starts 200 words back

def test_prepare_source_passthrough_when_short():
    client = FakeClient()
    assert prepare_source("court texte", client) == "court texte"
    assert client.calls == []

def test_prepare_source_condenses_when_long():
    client = FakeClient()
    long_text = " ".join(["mot"] * 9000)  # ~36k chars -> ~12k tokens
    out = prepare_source(long_text, client)
    assert "- note 1" in out and len(client.calls) >= 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/bin/pytest tests/test_condenser.py -v`
Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Implement**

`anamnese/condenser.py`:

```python
"""Condense long transcripts into clinical notes so prompts fit num_ctx."""
from anamnese import config
from anamnese.prompts import notes_prompt


def estimate_tokens(text: str) -> int:
    return len(text) // 3  # ~3 chars/token in French


def chunk_text(text: str, chunk_words=2200, overlap_words=200):
    words = text.split()
    chunks, start = [], 0
    while start < len(words):
        chunks.append(" ".join(words[start:start + chunk_words]))
        if start + chunk_words >= len(words):
            break
        start += chunk_words - overlap_words
    return chunks


def prepare_source(transcript: str, client, progress_cb=None) -> str:
    """Return the text to feed section prompts: the transcript itself when it
    fits, otherwise per-chunk clinical notes produced by the local model."""
    if estimate_tokens(transcript) <= config.CONDENSE_TOKEN_THRESHOLD:
        return transcript
    chunks = chunk_text(transcript)
    notes = []
    for i, chunk in enumerate(chunks, 1):
        if progress_cb:
            progress_cb(f"Condensation {i}/{len(chunks)}")
        notes.append(client.generate(notes_prompt(chunk), num_predict=1200))
    return "\n".join(notes)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/bin/pytest tests/test_condenser.py -v`
Expected: 4 passed. (Check the overlap arithmetic in the second test against the
implementation: chunk 2 starts at word index 2000 = 2200 − 200.)

- [ ] **Step 5: Commit**

```bash
git add anamnese/condenser.py tests/test_condenser.py
git commit -m "feat: transcript condenser for long consultations"
```

---

### Task 8: Report generator (orchestration)

**Files:**
- Create: `anamnese/generator.py`
- Test: `tests/test_generator.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_generator.py`:

```python
from anamnese.generator import generate_report, ReportResult

class FakeClient:
    """Returns canned replies; can fail or return no-info for chosen prompts."""
    def __init__(self, fail_on=(), no_info_on=()):
        self.fail_on, self.no_info_on = fail_on, no_info_on
    def generate(self, prompt, system=None, num_predict=1500):
        if '"laterality"' in prompt:
            return '{"laterality": "Gaucher", "langue_maternelle": null, '\
                   '"statut_marital": null, "niveau_etudes": null, '\
                   '"profession": null, "motif_consultation": "bilan", '\
                   '"accompagnant": null}'
        if "Je rencontre ce jour" in prompt:
            return "Je rencontre ce jour Monsieur XXX, âgé de 30 ans."
        for key in self.fail_on:
            if f"« {key}" in prompt:
                raise RuntimeError("boom")
        for key in self.no_info_on:
            if f"« {key}" in prompt:
                return "AUCUNE INFORMATION"
        return "Paragraphe généré.\nSecond paragraphe."

EXAMPLES = {k: "exemple" for k in
            ("plaintes", "atcd_perso", "atcd_fam", "developpement", "thymie")}


def test_happy_path_fills_everything():
    r = generate_report("transcript", FakeClient(), EXAMPLES, "Monsieur XXX")
    assert isinstance(r, ReportResult)
    assert set(r.section_texts) == set(EXAMPLES)
    assert all(v for v in r.section_texts.values())
    assert r.header_fields["laterality"] == "Gaucher"
    assert r.intro_text.startswith("Je rencontre ce jour")
    assert r.failed == [] and r.no_info == []


def test_one_section_failure_does_not_stop_others():
    r = generate_report("t", FakeClient(fail_on=("Antécédents médicaux familiaux",)),
                        EXAMPLES, "Monsieur XXX")
    assert r.section_texts["atcd_fam"] is None
    assert r.failed == ["Antécédents médicaux familiaux"]
    assert r.section_texts["plaintes"]  # others still generated


def test_no_info_section_reported_and_left_blank():
    r = generate_report("t", FakeClient(no_info_on=("Thymie, sommeil, appétit",)),
                        EXAMPLES, "Monsieur XXX")
    assert r.section_texts["thymie"] is None
    assert r.no_info == ["Thymie, sommeil, appétit"]


def test_header_extraction_failure_is_non_fatal():
    class BadJson(FakeClient):
        def generate(self, prompt, system=None, num_predict=1500):
            if '"laterality"' in prompt:
                return "pas du json"
            return super().generate(prompt, system, num_predict)
    r = generate_report("t", BadJson(), EXAMPLES, "Monsieur XXX")
    assert r.header_fields == {}
    assert r.section_texts["plaintes"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/bin/pytest tests/test_generator.py -v`
Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Implement**

`anamnese/generator.py`:

```python
"""Orchestrates section-by-section report generation from a transcript."""
from dataclasses import dataclass, field

from anamnese.condenser import prepare_source
from anamnese.ollama_client import parse_json_reply
from anamnese.prompts import (SYSTEM_PROMPT, header_prompt, intro_prompt,
                              section_prompt)
from anamnese.sections import SECTIONS

_HEADER_KEYS = ("laterality", "langue_maternelle", "statut_marital",
                "niveau_etudes", "profession", "motif_consultation",
                "accompagnant")


@dataclass
class ReportResult:
    intro_text: str = ""
    section_texts: dict = field(default_factory=dict)
    header_fields: dict = field(default_factory=dict)
    failed: list = field(default_factory=list)     # section headings that errored
    no_info: list = field(default_factory=list)    # headings with no transcript info


def generate_report(transcript, client, examples, patient_title,
                    progress_cb=None) -> ReportResult:
    """examples: section key -> style example text (from examples.py).
    patient_title: "Monsieur XXX" or "Madame XXX" (chosen in the UI)."""
    def progress(msg):
        if progress_cb:
            progress_cb(msg)

    result = ReportResult()
    source = prepare_source(transcript, client, progress_cb)

    progress("Extraction des informations administratives")
    try:
        raw = client.generate(header_prompt(source), system=SYSTEM_PROMPT,
                              num_predict=300)
        data = parse_json_reply(raw)
        result.header_fields = {k: data.get(k) for k in _HEADER_KEYS
                                if data.get(k)}
    except Exception:
        result.header_fields = {}

    for i, section in enumerate(SECTIONS, 1):
        progress(f"Rédaction {i}/{len(SECTIONS)} : {section.heading}")
        try:
            text = client.generate(
                section_prompt(section, source, examples.get(section.key, ""),
                               patient_title),
                system=SYSTEM_PROMPT)
            if "AUCUNE INFORMATION" in text.upper():
                result.section_texts[section.key] = None
                result.no_info.append(section.heading)
            else:
                result.section_texts[section.key] = text
        except Exception:
            result.section_texts[section.key] = None
            result.failed.append(section.heading)

    progress("Rédaction de l'introduction")
    try:
        result.intro_text = client.generate(
            intro_prompt(source, patient_title), system=SYSTEM_PROMPT,
            num_predict=200)
    except Exception:
        result.intro_text = ""

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/bin/pytest tests/test_generator.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add anamnese/generator.py tests/test_generator.py
git commit -m "feat: section-by-section report generator with graceful failures"
```

---

### Task 9: Transcriber (whisper.cpp wrapper)

**Files:**
- Create: `anamnese/transcriber.py`
- Test: `tests/test_transcriber.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_transcriber.py`:

```python
import shutil
from pathlib import Path
from unittest import mock

import pytest

from anamnese import config
from anamnese.transcriber import build_command, transcribe, to_whisper_wav


def test_build_command_french_txt_output(tmp_path):
    cmd = build_command(tmp_path / "a.wav", tmp_path / "out")
    s = " ".join(str(c) for c in cmd)
    assert config.WHISPER_BIN in s and "-l fr" in s and "--output-txt" in s
    assert str(config.WHISPER_MODEL) in s


def test_transcribe_reads_txt_output(tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"fake")
    def fake_run(cmd, **kw):
        # whisper-cli writes <output-file>.txt
        out_base = cmd[cmd.index("--output-file") + 1]
        Path(str(out_base) + ".txt").write_text("Bonjour docteur.\n")
        return mock.MagicMock(returncode=0, stderr=b"")
    with mock.patch("anamnese.transcriber.subprocess.run", fake_run):
        assert transcribe(wav) == "Bonjour docteur."


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg required")
def test_to_whisper_wav_converts_to_16k_mono(tmp_path):
    import soundfile as sf
    import numpy as np
    src = tmp_path / "in.wav"
    sf.write(src, np.zeros(44100, dtype="int16"), 44100)  # 1 s at 44.1 kHz
    out = to_whisper_wav(src, tmp_path)
    info = sf.info(str(out))
    assert info.samplerate == 16000 and info.channels == 1


@pytest.mark.skipif(shutil.which(config.WHISPER_BIN) is None
                    or not config.WHISPER_MODEL.exists(),
                    reason="whisper-cli + model required (installed by install.sh)")
def test_real_transcription_of_synthesized_french(tmp_path):
    import subprocess
    aiff = tmp_path / "t.aiff"
    subprocess.run(["say", "-v", "Thomas",
                    "Bonjour, je viens consulter pour des troubles de la mémoire.",
                    "-o", str(aiff)], check=True)
    wav = to_whisper_wav(aiff, tmp_path)
    text = transcribe(wav).lower()
    assert "mémoire" in text
```

Note: if the French voice `Thomas` is unavailable, `say -v ?` lists voices; any
`fr_FR` voice works — adjust the test, or let it fail visibly (it is an
integration test that only runs post-install).

- [ ] **Step 2: Run tests to verify unit tests fail, integration tests skip**

Run: `./.venv/bin/pytest tests/test_transcriber.py -v`
Expected: FAIL with ModuleNotFoundError (and later, 2 skipped until install.sh has run).

- [ ] **Step 3: Implement**

`anamnese/transcriber.py`:

```python
"""Transcription via whisper.cpp (whisper-cli subprocess, exits when done)."""
import subprocess
import tempfile
from pathlib import Path

from anamnese import config


class TranscriptionError(RuntimeError):
    pass


def to_whisper_wav(audio_path: Path, workdir: Path) -> Path:
    """Convert any audio file to 16 kHz mono 16-bit WAV via ffmpeg."""
    out = Path(workdir) / (Path(audio_path).stem + "_16k.wav")
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", str(audio_path),
         "-ar", str(config.SAMPLE_RATE), "-ac", "1", "-c:a", "pcm_s16le",
         str(out)],
        capture_output=True)
    if r.returncode != 0:
        raise TranscriptionError(
            f"Conversion audio échouée : {r.stderr.decode(errors='replace')[-400:]}")
    return out


def build_command(wav_path: Path, output_base: Path) -> list:
    return [config.WHISPER_BIN,
            "-m", str(config.WHISPER_MODEL),
            "-l", "fr",
            "-f", str(wav_path),
            "--output-txt",
            "--output-file", str(output_base),
            "--no-timestamps"]


def transcribe(wav_path: Path) -> str:
    """Run whisper-cli on a 16 kHz mono WAV; return the transcript text."""
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "transcript"
        r = subprocess.run(build_command(wav_path, base), capture_output=True)
        if r.returncode != 0:
            raise TranscriptionError(
                f"whisper-cli a échoué : {r.stderr.decode(errors='replace')[-400:]}")
        txt = Path(str(base) + ".txt")
        if not txt.exists():
            raise TranscriptionError("whisper-cli n'a pas produit de fichier texte.")
        return txt.read_text(encoding="utf-8").strip()
```

- [ ] **Step 4: Run tests to verify unit tests pass**

Run: `./.venv/bin/pytest tests/test_transcriber.py -v`
Expected: 2–3 passed (ffmpeg test passes since ffmpeg is installed), 1 skipped
(real whisper) until install.sh has run.

- [ ] **Step 5: Commit**

```bash
git add anamnese/transcriber.py tests/test_transcriber.py
git commit -m "feat: whisper.cpp transcriber wrapper with ffmpeg conversion"
```

---

### Task 10: Recorder

**Files:**
- Create: `anamnese/recorder.py`
- Test: `tests/test_recorder.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_recorder.py`:

```python
import time

import numpy as np
import soundfile as sf

from anamnese.recorder import Recorder


class FakeStream:
    """Mimics sounddevice.InputStream: fires the callback from start()."""
    def __init__(self, samplerate, channels, dtype, callback, blocksize=0):
        self.callback = callback
    def start(self):
        block = np.zeros((16000, 1), dtype="int16")  # 1 s of silence
        for _ in range(3):
            self.callback(block, 16000, None, None)
    def stop(self): pass
    def close(self): pass


def test_recorder_writes_wav_continuously(tmp_path):
    rec = Recorder(out_dir=tmp_path, stream_factory=FakeStream)
    path = rec.start()
    time.sleep(0.3)  # let the writer thread drain the queue
    rec.stop()
    info = sf.info(str(path))
    assert info.samplerate == 16000 and info.channels == 1
    assert info.frames == 3 * 16000
    assert path.parent == tmp_path


def test_elapsed_seconds_increases(tmp_path):
    rec = Recorder(out_dir=tmp_path, stream_factory=FakeStream)
    rec.start()
    time.sleep(0.05)
    assert rec.elapsed_seconds() >= 0
    rec.stop()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/bin/pytest tests/test_recorder.py -v`
Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Implement**

`anamnese/recorder.py`:

```python
"""Crash-safe microphone recorder: audio hits the disk continuously."""
import datetime
import queue
import threading
import time
from pathlib import Path

import soundfile as sf

from anamnese import config


def _default_stream_factory(samplerate, channels, dtype, callback, blocksize=0):
    import sounddevice as sd  # imported lazily: not needed for file-based flows
    return sd.InputStream(samplerate=samplerate, channels=channels,
                          dtype=dtype, callback=callback, blocksize=blocksize)


class Recorder:
    def __init__(self, out_dir=config.RECORDINGS_DIR,
                 stream_factory=_default_stream_factory):
        self.out_dir = Path(out_dir)
        self._factory = stream_factory
        self._queue = queue.Queue()
        self._stream = None
        self._writer = None
        self._stop_flag = threading.Event()
        self._started_at = None
        self.path = None

    def start(self) -> Path:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.path = self.out_dir / f"enregistrement_{stamp}.wav"
        self._stop_flag.clear()
        self._writer = threading.Thread(target=self._write_loop, daemon=True)
        self._writer.start()
        self._stream = self._factory(
            samplerate=config.SAMPLE_RATE, channels=config.CHANNELS,
            dtype="int16", callback=self._callback)
        self._stream.start()
        self._started_at = time.monotonic()
        return self.path

    def _callback(self, indata, frames, time_info, status):
        self._queue.put(bytes(indata))  # copy: PortAudio reuses the buffer

    def _write_loop(self):
        with sf.SoundFile(str(self.path), mode="w",
                          samplerate=config.SAMPLE_RATE,
                          channels=config.CHANNELS, subtype="PCM_16") as f:
            while not (self._stop_flag.is_set() and self._queue.empty()):
                try:
                    data = self._queue.get(timeout=0.2)
                except queue.Empty:
                    continue
                import numpy as np
                f.write(np.frombuffer(data, dtype="int16").reshape(-1, 1))
                f.flush()  # crash-safe: data lands on disk as we go

    def elapsed_seconds(self) -> int:
        return int(time.monotonic() - self._started_at) if self._started_at else 0

    def stop(self) -> Path:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._stop_flag.set()
        if self._writer is not None:
            self._writer.join(timeout=10)
        return self.path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/bin/pytest tests/test_recorder.py -v`
Expected: 2 passed.

- [ ] **Step 5: Full-suite check + commit**

Run: `./.venv/bin/pytest tests/ -v` — all green (integration tests may skip).

```bash
git add anamnese/recorder.py tests/test_recorder.py
git commit -m "feat: crash-safe streaming WAV recorder"
```

---

### Task 11: Tkinter GUI

**Files:**
- Create: `app.py`

No unit tests for the GUI (logic lives in the tested modules); Step 3 is a manual checklist.

- [ ] **Step 1: Implement**

`app.py`:

```python
"""Anamnèse — local transcription & report drafting. 100% local processing."""
import queue
import threading
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import (Tk, Frame, Button, Label, Entry, Text, StringVar,
                     Radiobutton, filedialog, messagebox, DISABLED, NORMAL, END)

from anamnese import config
from anamnese.docx_filler import fill_report
from anamnese.examples import extract_examples
from anamnese.generator import generate_report
from anamnese.ollama_client import OllamaClient
from anamnese.recorder import Recorder
from anamnese.transcriber import to_whisper_wav, transcribe

POLL_MS = 200


class App:
    def __init__(self, root):
        self.root = root
        root.title("Anamnèse — transcription locale")
        root.geometry("820x640")
        self.events = queue.Queue()
        self.recorder = None
        self.audio_path = None

        top = Frame(root); top.pack(fill="x", padx=12, pady=8)
        self.record_btn = Button(top, text="●  Enregistrer", fg="red",
                                 font=("Helvetica", 16, "bold"),
                                 command=self.toggle_record)
        self.record_btn.pack(side="left")
        self.timer_var = StringVar(value="00:00")
        Label(top, textvariable=self.timer_var,
              font=("Helvetica", 16)).pack(side="left", padx=10)
        Button(top, text="Ouvrir un audio…",
               command=self.open_audio).pack(side="left", padx=10)
        self.title_var = StringVar(value="Monsieur XXX")
        Radiobutton(top, text="Monsieur", variable=self.title_var,
                    value="Monsieur XXX").pack(side="left", padx=(20, 0))
        Radiobutton(top, text="Madame", variable=self.title_var,
                    value="Madame XXX").pack(side="left")

        paths = Frame(root); paths.pack(fill="x", padx=12)
        Label(paths, text="Modèle :").grid(row=0, column=0, sticky="w")
        self.template_var = StringVar(value=str(config.DEFAULT_TEMPLATE))
        Entry(paths, textvariable=self.template_var, width=70).grid(row=0, column=1)
        Button(paths, text="…", command=self.pick_template).grid(row=0, column=2)
        Label(paths, text="Sortie :").grid(row=1, column=0, sticky="w")
        default_out = Path.home() / "Documents" / "CR-anamnese"
        self.outdir_var = StringVar(value=str(default_out))
        Entry(paths, textvariable=self.outdir_var, width=70).grid(row=1, column=1)
        Button(paths, text="…", command=self.pick_outdir).grid(row=1, column=2)

        self.status_var = StringVar(
            value="Prêt. Rappel : le patient doit avoir consenti à l'enregistrement.")
        Label(root, textvariable=self.status_var, anchor="w",
              fg="gray25").pack(fill="x", padx=12, pady=4)

        Label(root, text="Transcription (relisez et corrigez avant de générer) :"
              ).pack(anchor="w", padx=12)
        self.transcript = Text(root, wrap="word", height=18)
        self.transcript.pack(fill="both", expand=True, padx=12, pady=4)

        self.generate_btn = Button(root, text="Générer le compte-rendu",
                                   font=("Helvetica", 14, "bold"),
                                   state=DISABLED, command=self.generate)
        self.generate_btn.pack(pady=8)
        root.after(POLL_MS, self.poll)

    # ---------- UI helpers ----------
    def set_status(self, msg):
        self.events.put(("status", msg))

    def poll(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "status":
                    self.status_var.set(payload)
                elif kind == "transcript":
                    self.transcript.delete("1.0", END)
                    self.transcript.insert("1.0", payload)
                    self.generate_btn.config(state=NORMAL)
                    self.status_var.set("Transcription terminée. Relisez, "
                                        "corrigez, puis générez le compte-rendu.")
                elif kind == "done":
                    self.generate_btn.config(state=NORMAL)
                    messagebox.showinfo("Terminé", payload)
                elif kind == "error":
                    self.generate_btn.config(state=NORMAL)
                    messagebox.showerror("Erreur", payload)
        except queue.Empty:
            pass
        if self.recorder is not None:
            s = self.recorder.elapsed_seconds()
            self.timer_var.set(f"{s // 60:02d}:{s % 60:02d}")
        self.root.after(POLL_MS, self.poll)

    def run_bg(self, fn):
        def wrapper():
            try:
                fn()
            except Exception:
                self.events.put(("error", traceback.format_exc(limit=3)))
        threading.Thread(target=wrapper, daemon=True).start()

    # ---------- actions ----------
    def pick_template(self):
        p = filedialog.askopenfilename(filetypes=[("Word", "*.docx")])
        if p:
            self.template_var.set(p)

    def pick_outdir(self):
        p = filedialog.askdirectory()
        if p:
            self.outdir_var.set(p)

    def toggle_record(self):
        if self.recorder is None:
            try:
                self.recorder = Recorder()
                self.audio_path = self.recorder.start()
            except Exception as e:
                self.recorder = None
                messagebox.showerror(
                    "Micro indisponible",
                    "Impossible d'accéder au micro. Vérifiez :\nRéglages Système"
                    " → Confidentialité et sécurité → Microphone,\npuis autorisez"
                    f" Terminal/Python.\n\nDétail : {e}")
                return
            self.record_btn.config(text="■  Stop")
            self.set_status(f"Enregistrement en cours → {self.audio_path.name}")
        else:
            rec, self.recorder = self.recorder, None
            wav = rec.stop()
            self.record_btn.config(text="●  Enregistrer")
            self.transcribe_file(wav, already_16k=True)

    def open_audio(self):
        p = filedialog.askopenfilename(
            filetypes=[("Audio", "*.wav *.mp3 *.m4a *.aiff *.aac *.ogg *.flac")])
        if p:
            self.transcribe_file(Path(p), already_16k=False)

    def transcribe_file(self, path, already_16k):
        self.set_status("Transcription en cours… (plusieurs minutes pour une "
                        "consultation complète)")
        self.generate_btn.config(state=DISABLED)
        def job():
            wav = path if already_16k else to_whisper_wav(path, config.RECORDINGS_DIR)
            self.events.put(("transcript", transcribe(wav)))
        self.run_bg(job)

    def generate(self):
        text = self.transcript.get("1.0", END).strip()
        if not text:
            messagebox.showwarning("Vide", "Aucune transcription à traiter.")
            return
        template = Path(self.template_var.get())
        if not template.exists():
            messagebox.showerror("Modèle introuvable", str(template))
            return
        outdir = Path(self.outdir_var.get())
        outdir.mkdir(parents=True, exist_ok=True)
        title = self.title_var.get()
        self.generate_btn.config(state=DISABLED)

        def job():
            stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
            (outdir / f"CR_{stamp}_transcript.txt").write_text(
                text, encoding="utf-8")
            self.set_status("Démarrage du modèle local (Ollama)…")
            client = OllamaClient()
            client.ensure_running()
            examples = extract_examples(config.STYLE_EXAMPLE_DOCX)
            result = generate_report(text, client, examples, title,
                                     progress_cb=self.set_status)
            out_docx = outdir / f"CR_{stamp}.docx"
            fill_report(template, out_docx, result.intro_text,
                        result.section_texts, result.header_fields)
            msg = f"Compte-rendu écrit :\n{out_docx}"
            if result.no_info:
                msg += "\n\nSections sans information dans l'entretien :\n- " \
                       + "\n- ".join(result.no_info)
            if result.failed:
                msg += "\n\nSections en échec (à rédiger à la main) :\n- " \
                       + "\n- ".join(result.failed)
            self.events.put(("done", msg))
        self.run_bg(job)


if __name__ == "__main__":
    root = Tk()
    App(root)
    root.mainloop()
```

- [ ] **Step 2: Sanity-launch** (app opens even without whisper/qwen3 installed)

Run: `./.venv/bin/python app.py` — window opens; close it. Any traceback = fix before proceeding.

- [ ] **Step 3: Manual test checklist** (record actual results)

1. Launch → window shows Record button, timer, template pre-filled, consent reminder in status bar.
2. « Ouvrir un audio… » with a small file → status changes, then transcript appears (requires whisper install — defer to Task 13 if not yet installed).
3. « Générer » with empty transcript → warning dialog, no crash.
4. Template path pointing to a missing file → error dialog, no crash.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: Tkinter GUI wiring the full pipeline"
```

---

### Task 12: Installer, launcher, README

**Files:**
- Create: `install.sh`, `Anamnese.command`, `README.md`

- [ ] **Step 1: Write install.sh**

```bash
#!/bin/zsh
# One-time installer. The ONLY step that touches the network.
set -e
cd "$(dirname "$0")"

echo "→ whisper.cpp (Homebrew)"
brew list whisper-cpp >/dev/null 2>&1 || brew install whisper-cpp

echo "→ Python venv + dépendances"
[ -d .venv ] || python3 -m venv .venv
./.venv/bin/pip install -q -r requirements.txt

echo "→ Modèle Whisper (french-ready, ~570 Mo, téléchargé une seule fois)"
mkdir -p models
MODEL=models/ggml-large-v3-turbo-q5_0.bin
[ -f "$MODEL" ] || curl -L -o "$MODEL" \
  "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin"

echo "→ Modèle de rédaction (Ollama qwen3:8b, ~5 Go, téléchargé une seule fois)"
ollama list | grep -q "qwen3:8b" || ollama pull qwen3:8b

echo "→ Tests"
./.venv/bin/pytest tests/ -q

echo "✓ Installation terminée. Lancez l'application avec : Anamnese.command"
```

Run: `chmod +x install.sh`

- [ ] **Step 2: Write the double-clickable launcher**

`Anamnese.command`:

```bash
#!/bin/zsh
cd "$(dirname "$0")"
export OLLAMA_FLASH_ATTENTION=1
export OLLAMA_KV_CACHE_TYPE=q8_0
exec ./.venv/bin/python app.py
```

Run: `chmod +x Anamnese.command`

- [ ] **Step 3: Write README.md** — short French quickstart:

```markdown
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
2. Choisir Monsieur/Madame, vérifier modèle et dossier de sortie.
3. **● Enregistrer** au début de l'entretien (consentement du patient requis),
   **■ Stop** à la fin — ou « Ouvrir un audio… » pour un fichier existant.
4. Relire/corriger la transcription, puis **Générer le compte-rendu**.
5. Sortie : `CR_<date>.docx` (modèle rempli) + `CR_<date>_transcript.txt`
   dans le dossier de sortie. Le brouillon doit être relu et corrigé : c'est une
   aide à la rédaction, pas un compte-rendu final. Les conclusions restent à
   rédiger par le clinicien.

## Confidentialité
- Transcription : whisper.cpp, processus local.
- Rédaction : Ollama sur http://127.0.0.1:11434, modèle local qwen3:8b.
- Fonctionne Wi-Fi coupé (test recommandé). Les enregistrements restent dans
  `recordings/` — les supprimer régulièrement.
```

- [ ] **Step 4: Run the installer for real**

Run: `./install.sh`
Expected: whisper-cpp installed, model downloaded (~570 MB), qwen3:8b pulled
(~5 GB — this takes a while), full test suite green including the previously
skipped whisper integration test.

- [ ] **Step 5: Commit**

```bash
git add install.sh Anamnese.command README.md
git commit -m "feat: installer, launcher, French README"
```

---

### Task 13: End-to-end verification

**Files:** none (verification only). Use the superpowers:verification-before-completion skill.

- [ ] **Step 1: Synthesize a fake consultation audio**

```bash
say -v Thomas -o /tmp/e2e_consult.aiff "Bonjour docteur. Je viens vous voir parce que j'oublie beaucoup de choses depuis un an. Je perds mes clés, je rate des rendez-vous. Je suis droitier, ma langue maternelle est le français, je travaille comme comptable. Je suis marié. Côté famille, ma mère a eu la maladie d'Alzheimer. Je dors mal en ce moment et j'ai peu d'appétit. Mon moral est plutôt bas depuis quelques mois."
```
(If `Thomas` is missing: `say -v '?' | grep fr_` and use any French voice.)

- [ ] **Step 2: Full pipeline through the GUI**

Launch `Anamnese.command` → « Ouvrir un audio… » → `/tmp/e2e_consult.aiff` →
verify transcript mentions memory complaints → « Générer le compte-rendu ».

Expected: a `CR_<date>.docx` opens in Word with: intro sentence, plaintes
mentioning memory/keys/appointments, family history mentioning Alzheimer (mother),
thymie/sommeil filled, header fields (Latéralité : Droitier, Profession :
comptable…), letterhead intact, conclusions untouched, and **no real name anywhere**.

- [ ] **Step 3: Record-button smoke test**

Record ~20 s of speech via the mic → Stop → transcript appears → generate.
Also verify the WAV exists in `recordings/` *during* the recording (crash safety).

- [ ] **Step 4: Privacy verification (the core promise)**

1. Turn Wi-Fi off.
2. Repeat Step 2 end-to-end.
Expected: everything works identically. If anything fails offline, that's a bug — fix it.

- [ ] **Step 5: Final commit & report results to the user**

```bash
git add -A && git commit -m "chore: e2e verification complete" --allow-empty
```

Report: what was tested, timings observed (transcription and generation
durations for the test audio), and any caveats (e.g. French voice quality of
`say` limits transcription realism — first real consultation is the true test).

---

## Self-review notes (done at plan-writing time)

- Spec coverage: recording (T10), crash-safety (T10 flush + T13.3), open-audio
  (T9/T11), French transcription (T9), editable transcript gate (T11), section
  generation with style examples (T3/T5/T8), anonymity rule (T5, verified T13.2),
  header fields (T5/T8/T4), conclusions untouched (T4 test), partial-failure
  handling (T8 tests + T11 dialog), Ollama auto-start (T6), mic-permission
  message (T11), offline guarantee (T12 README + T13.4), consent reminder (T11
  status bar). Out-of-scope items (diarization, conclusions) have no tasks — correct.
- Types/signatures consistent: `generate_report(transcript, client, examples,
  patient_title, progress_cb)` matches app.py call; `fill_report(template_path,
  output_path, intro_text, section_texts, header_fields)` matches tests and app.py;
  `ReportResult` fields used identically in T8 and T11.
- Known risk flagged for the executor: qwen3:8b + 12288 ctx on 8 GB RAM may be
  slow (partial CPU offload). If generation exceeds ~3 min/section in T13,
  lower `OLLAMA_NUM_CTX` to 8192 and `CONDENSE_TOKEN_THRESHOLD` to 4500, or
  switch `OLLAMA_MODEL` to `qwen3:4b` — both are config-only changes.
