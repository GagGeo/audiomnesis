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
