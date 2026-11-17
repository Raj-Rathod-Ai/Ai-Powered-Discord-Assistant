import pytest
import tools


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_github_search_requests_ranked_ten_and_normalizes_fields(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse({
            "items": [{
                "full_name": "example/rag-project",
                "description": "A Python RAG project",
                "stargazers_count": 1234,
                "language": "Python",
                "license": {"spdx_id": "MIT"},
                "updated_at": "2026-11-16T10:00:00Z",
                "html_url": "https://github.com/example/rag-project",
            }]
        })

    monkeypatch.setattr(tools.requests, "get", fake_get)
    result = tools.search_github_repositories("RAG language:Python", 99)

    assert captured["url"] == "https://api.github.com/search/repositories"
    assert captured["params"]["q"] == "RAG language:Python is:public fork:false"
    assert captured["params"]["per_page"] == 10
    assert captured["params"]["sort"] == "stars"
    assert captured["params"]["order"] == "desc"
    assert result == [{
        "full_name": "example/rag-project",
        "description": "A Python RAG project",
        "stars": 1234,
        "language": "Python",
        "license": "MIT",
        "updated_at": "2026-11-16T10:00:00Z",
        "url": "https://github.com/example/rag-project",
    }]


def test_github_search_clamps_minimum_limit(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured.update(kwargs)
        return FakeResponse({"items": []})

    monkeypatch.setattr(tools.requests, "get", fake_get)
    assert tools.search_github_repositories("RAG", 0) == []
    assert captured["params"]["per_page"] == 1


def test_github_search_handles_missing_license_and_description(monkeypatch):
    def fake_get(url, **kwargs):
        return FakeResponse({"items": [{"full_name": "example/repo"}]})

    monkeypatch.setattr(tools.requests, "get", fake_get)
    result = tools.search_github_repositories("RAG")

    assert result[0]["license"] == "Not specified"
    assert result[0]["description"] == "No description"
    assert result[0]["stars"] == 0


def test_github_search_propagates_http_errors(monkeypatch):
    class BrokenResponse:
        def raise_for_status(self):
            raise tools.requests.HTTPError("rate limited")

    monkeypatch.setattr(tools.requests, "get", lambda *args, **kwargs: BrokenResponse())
    with pytest.raises(tools.requests.HTTPError):
        tools.search_github_repositories("RAG")


def test_normalize_natural_language_search_query():
    assert tools.normalize_github_repository_query(
        "Find the top 10 open-source RAG projects using Python"
    ) == "RAG language:Python is:public fork:false"
