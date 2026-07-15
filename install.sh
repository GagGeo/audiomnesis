#!/bin/zsh
# One-time installer. The ONLY step that touches the network.
set -e
cd "$(dirname "$0")"

echo "→ Vérification des prérequis"
if ! command -v brew >/dev/null; then
  echo "✗ Homebrew est requis : https://brew.sh" >&2; exit 1
fi
if ! command -v ollama >/dev/null; then
  echo "✗ Ollama est requis : https://ollama.com/download (ou : brew install ollama)" >&2; exit 1
fi
if ! command -v clang >/dev/null; then
  echo "✗ Outils de développement requis : xcode-select --install" >&2; exit 1
fi

echo "→ ffmpeg + whisper.cpp (Homebrew)"
brew list ffmpeg >/dev/null 2>&1 || brew install ffmpeg
brew list whisper-cpp >/dev/null 2>&1 || brew install whisper-cpp

echo "→ Python venv + dépendances"
[ -d .venv ] || python3 -m venv .venv
./.venv/bin/pip install -q -r requirements.txt

echo "→ Modèle Whisper (~570 Mo, téléchargé une seule fois)"
mkdir -p models
MODEL=models/ggml-large-v3-turbo-q5_0.bin
[ -f "$MODEL" ] || curl -L -o "$MODEL" \
  "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin"

echo "→ Modèle de rédaction (Ollama gemma3:4b, ~3,3 Go, téléchargé une seule fois)"
ollama list | grep -q "gemma3:4b" || ollama pull gemma3:4b

echo "→ Tests"
./.venv/bin/pytest tests/ -q

echo "→ Application (compilation du lanceur + signature ad hoc)"
clang -O2 -o Audiomnesis.app/Contents/MacOS/Audiomnesis app_src/launcher.c
codesign --force --deep -s - Audiomnesis.app

echo "✓ Installation terminée. Lancez l'application : Audiomnesis.app"
