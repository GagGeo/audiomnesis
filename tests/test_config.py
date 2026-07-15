from anamnese import config

def test_template_files_exist():
    assert config.DEFAULT_TEMPLATE.exists()
    assert config.STYLE_EXAMPLE_DOCX.exists()

def test_ollama_url_is_localhost():
    assert config.OLLAMA_URL.startswith("http://127.0.0.1")
