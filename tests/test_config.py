from anamnese import config

def test_template_file_exists():
    assert config.DEFAULT_TEMPLATE.exists()

def test_ollama_url_is_localhost():
    assert config.OLLAMA_URL.startswith("http://127.0.0.1")
