#!/bin/zsh
# One-time installer. The ONLY step that touches the network.
set -e
cd "$(dirname "$0")"

echo "→ whisper.cpp (Homebrew)"
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

echo "✓ Installation terminée. Lancez l'application avec : Anamnese.command"
