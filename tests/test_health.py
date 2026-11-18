import http.client
import threading
from http.server import ThreadingHTTPServer

import bot


class FakeDiscordClient:
    def __init__(self, ready):
        self.ready = ready

    def is_ready(self):
        return self.ready


def request_health(monkeypatch, method, path, *, discord_ready=False, commands_ready=False):
    monkeypatch.setattr(bot, "client", FakeDiscordClient(discord_ready))
    monkeypatch.setattr(bot, "commands_synced", commands_ready)

    server = ThreadingHTTPServer(("127.0.0.1", 0), bot.HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
        connection.request(method, path)
        response = connection.getresponse()
        result = (response.status, response.read(), response.getheader("Content-Length"))
        connection.close()
        return result
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_head_root_returns_200_without_body(monkeypatch):
    status, body, content_length = request_health(monkeypatch, "HEAD", "/")

    assert status == 200
    assert body == b""
    assert int(content_length) > 0


def test_health_get_returns_200_while_discord_is_disconnected(monkeypatch):
    status, body, _ = request_health(monkeypatch, "GET", "/health")

    assert status == 200
    assert b'"status":"ok"' in body


def test_ready_requires_discord_and_command_sync(monkeypatch):
    status, _, _ = request_health(
        monkeypatch, "GET", "/ready", discord_ready=True, commands_ready=False
    )
    assert status == 503

    status, body, _ = request_health(
        monkeypatch, "GET", "/ready", discord_ready=True, commands_ready=True
    )
    assert status == 200
    assert b'"commands_synced": true' in body
