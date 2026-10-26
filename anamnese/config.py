import shutil
from pathlib import Path


def _find_tool(name: str) -> str:
    """Absolute path of a CLI tool. Apps launched from Finder get a minimal
    PATH without /opt/homebrew/bin, so a bare name would not be found."""
    found = shutil.which(name)
    if found:
        return found
    for d in ("/opt/homebrew/bin", "/usr/local/bin"):
        candidate = Path(d) / name
        if candidate.exists():
            return str(candidate)
    return name  # unresolved: downstream code raises a clear error

APP_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = APP_DIR / "docs"
MODELS_DIR = APP_DIR / "models"
RECORDINGS_DIR = APP_DIR / "recordings"

DEFAULT_TEMPLATE = DOCS_DIR / "bilan-cr.docx"
DEFAULT_TEMPLATE_EN = DOCS_DIR / "bilan-cr_en.docx"  # English report template
SETTINGS_FILE = APP_DIR / ".settings.json"

WHISPER_MODEL = MODELS_DIR / "ggml-large-v3-turbo-q5_0.bin"
WHISPER_BIN = _find_tool("whisper-cli")  # from `brew install whisper-cpp`
FFMPEG_BIN = _find_tool("ffmpeg")
OLLAMA_BIN = _find_tool("ollama")

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
