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
