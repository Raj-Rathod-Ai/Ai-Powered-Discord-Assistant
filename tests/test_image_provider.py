import pytest

import agent


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self.text = str(payload)

    def json(self):
        return self.payload


def test_generate_image_uses_configured_flux_model(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "test-account")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-token")
    monkeypatch.setenv("CLOUDFLARE_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell")

    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse({"success": True, "result": {"image": "aGVsbG8="}})

    monkeypatch.setattr(agent.requests, "post", fake_post)

    result = agent.generate_image.invoke({"prompt": "A superhero flying above a city"})

    assert result == "aGVsbG8="
    assert captured["url"].endswith(
        "/ai/run/@cf/black-forest-labs/flux-1-schnell"
    )
    assert captured["json"] == {"prompt": "A superhero flying above a city"}
    assert captured["timeout"] == (15, 180)


def test_generate_image_reports_cloudflare_error_message(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "test-account")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-token")
    monkeypatch.setenv("CLOUDFLARE_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell")

    def fake_post(url, **kwargs):
        return FakeResponse(
            {"success": False, "errors": [{"code": 1000, "message": "Invalid model"}]},
            status_code=400,
        )

    monkeypatch.setattr(agent.requests, "post", fake_post)

    with pytest.raises(RuntimeError, match="HTTP 400: Invalid model"):
        agent.generate_image.invoke({"prompt": "A flying superhero"})


@pytest.mark.parametrize("prompt", ["", "   ", "x" * 2049])
def test_generate_image_rejects_invalid_prompt_before_api_call(monkeypatch, prompt):
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "test-account")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "test-token")
    monkeypatch.setenv("CLOUDFLARE_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell")

    def should_not_be_called(*args, **kwargs):
        pytest.fail("Cloudflare API must not be called for an invalid prompt")

    monkeypatch.setattr(agent.requests, "post", should_not_be_called)

    with pytest.raises(ValueError):
        agent.generate_image.invoke({"prompt": prompt})
