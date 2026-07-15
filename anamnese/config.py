from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = APP_DIR / "docs"
MODELS_DIR = APP_DIR / "models"
RECORDINGS_DIR = APP_DIR / "recordings"

DEFAULT_TEMPLATE = DOCS_DIR / "bilan-cr.docx"

WHISPER_MODEL = MODELS_DIR / "ggml-large-v3-turbo-q5_0.bin"
WHISPER_BIN = "whisper-cli"  # from `brew install whisper-cpp`

OLLAMA_URL = "http://127.0.0.1:11434"
# gemma3:4b: small enough for this 8 GB machine (the 8b-class models freeze
# macOS), and non-thinking — qwen3's reasoning mode cannot be disabled on
# current Ollama builds and eats the whole token budget before answering.
OLLAMA_MODEL = "gemma3:4b"
OLLAMA_NUM_CTX = 8192
OLLAMA_TIMEOUT = 900  # seconds per call; an 8 GB machine can be slow

SAMPLE_RATE = 16000  # whisper.cpp native input format
CHANNELS = 1

# Transcripts longer than this (estimated tokens, ~3 chars/token in French)
# are condensed to notes before section generation, to fit OLLAMA_NUM_CTX.
CONDENSE_TOKEN_THRESHOLD = 4500
