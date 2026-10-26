"""Tiny JSON settings store (.settings.json). Reads merge, writes never clobber
other keys. A failed read/write must never break the clinic app."""
import json

from anamnese import config


def load() -> dict:
    try:
        return json.loads(config.SETTINGS_FILE.read_text())
    except Exception:
        return {}


def get(key, default=None):
    return load().get(key, default)


def set(key, value) -> None:
    data = load()
    data[key] = value
    try:
        config.SETTINGS_FILE.write_text(json.dumps(data))
    except OSError:
        pass  # a failed preference save must never break the app
