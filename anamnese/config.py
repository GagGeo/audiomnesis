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
