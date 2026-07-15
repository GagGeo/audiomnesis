#!/bin/zsh
cd "$(dirname "$0")"
export OLLAMA_FLASH_ATTENTION=1
export OLLAMA_KV_CACHE_TYPE=q8_0
exec ./.venv/bin/python app.py
