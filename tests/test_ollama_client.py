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


def test_unload_requests_zero_keep_alive_and_never_raises():
    client = OllamaClient(model="qwen3:4b")
    fake = _fake_urlopen({"done": True})
    with mock.patch("anamnese.ollama_client.urllib.request.urlopen", fake):
        client.unload()
    body = json.loads(fake.call_args[0][0].data)
    assert body["keep_alive"] == 0
    # network failure must be swallowed
    boom = mock.MagicMock(side_effect=OSError("down"))
    with mock.patch("anamnese.ollama_client.urllib.request.urlopen", boom):
        client.unload()  # no exception


def test_parse_json_reply_strips_fences_and_noise():
    raw = "Voici :\n```json\n{\"a\": 1}\n```\nmerci"
    assert parse_json_reply(raw) == {"a": 1}
    assert parse_json_reply('{"b": null}') == {"b": None}
