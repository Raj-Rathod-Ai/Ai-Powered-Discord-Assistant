import tools


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_open_source_search_filters_unlicensed_repositories(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured.update(kwargs)
        return FakeResponse({
            "items": [
                {"full_name": "example/no-license", "description": "No license"},
                {"full_name": "example/mit-project", "license": {"spdx_id": "MIT"}, "html_url": "https://github.com/example/mit-project"},
                {"full_name": "example/noassertion", "license": {"spdx_id": "NOASSERTION"}},
            ]
        })

    monkeypatch.setattr(tools.requests, "get", fake_get)
    result = tools.search_github_repositories("Find open-source RAG projects using Python", 10)

    assert captured["params"]["per_page"] == 100
    assert [item["full_name"] for item in result] == ["example/mit-project"]
