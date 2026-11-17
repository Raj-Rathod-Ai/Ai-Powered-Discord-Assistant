from pathlib import Path

import pytest

from tools import _calculate, _safe_url, create_art_qr


def test_calculator_supports_basic_arithmetic():
    import ast
    assert _calculate(ast.parse("(12 + 8) * 2", mode="eval")) == 40


def test_calculator_rejects_code_execution():
    import ast
    with pytest.raises(ValueError):
        _calculate(ast.parse("__import__('os').system('echo unsafe')", mode="eval"))


def test_url_validation_accepts_public_web_urls():
    assert _safe_url("https://example.com/path") == "https://example.com/path"


@pytest.mark.parametrize("url", ["file:///etc/passwd", "http://localhost", "http://127.0.0.1"])
def test_url_validation_rejects_local_or_non_web_urls(url):
    with pytest.raises(ValueError):
        _safe_url(url)


def test_qr_generator_creates_png(tmp_path, monkeypatch):
    import tools
    monkeypatch.setattr(tools, "OUTPUT_DIR", tmp_path)
    output = Path(create_art_qr("https://example.com", "ocean"))
    assert output.exists()
    assert output.suffix == ".png"
