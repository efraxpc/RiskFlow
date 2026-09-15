from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from supportflow.client import send_message

APP_PATH = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def receipt_response():
    return httpx.Response(
        200,
        json={
            "request_id": str(uuid4()),
            "status": "received",
            "received_at": datetime.now(UTC).isoformat(),
            "user_message": "Mensaje recibido.",
        },
    )


@pytest.fixture
def calls(monkeypatch):
    requests = []
    monkeypatch.setenv("SUPPORTFLOW_API_URL", "http://127.0.0.1:8010")

    def post(url, **kwargs):
        requests.append({"url": url, **kwargs})
        return receipt_response()

    monkeypatch.setattr("supportflow.client.httpx.post", post)
    return requests


def test_chat_sends_only_new_messages_and_never_resends_on_rerun(calls):
    app = AppTest.from_file(APP_PATH).run()
    assert not app.exception
    assert calls == []
    app.chat_input[0].set_value("Primera consulta").run()
    assert not app.exception
    assert len(app.chat_message) == 2
    assert app.chat_message[1].text[0].value == "Mensaje recibido."
    app.run()
    assert len(calls) == 1
    assert len(app.chat_message) == 2
    app.chat_input[0].set_value("Segunda consulta").run()
    assert len(app.chat_message) == 4
    assert [call["json"] for call in calls] == [
        {"message": "Primera consulta", "locale_hint": "es"},
        {"message": "Segunda consulta", "locale_hint": "es"},
    ]
    for call in calls:
        assert call["url"] == "http://127.0.0.1:8010/api/agent/messages"
        assert call["timeout"] == 40
        assert call["follow_redirects"] is False
    app.sidebar.button[0].click().run()
    assert not app.exception
    assert len(app.chat_message) == 0
    assert len(calls) == 2
    assert app.session_state.messages == []


def test_sessions_do_not_share_history(calls):
    first = AppTest.from_file(APP_PATH).run()
    first.chat_input[0].set_value("Mi consulta privada").run()
    second = AppTest.from_file(APP_PATH).run()
    assert len(second.chat_message) == 0
    assert len(first.session_state.messages) == 2
    assert len(calls) == 1


def test_ui_treats_user_text_as_plain_text(calls):
    message = "![imagen](https://example.com/tracker) <script>alert(1)</script>"
    app = AppTest.from_file(APP_PATH).run()
    app.chat_input[0].set_value(message).run()
    assert app.chat_message[0].text[0].value == message
    assert not app.chat_message[0].markdown


@pytest.mark.parametrize("exception", [httpx.ConnectError, httpx.ReadTimeout])
def test_connection_failures_are_visible_and_do_not_retry(monkeypatch, exception):
    calls = []

    def post(*args, **kwargs):
        calls.append(kwargs)
        raise exception("private-connection-detail")

    monkeypatch.setattr("supportflow.client.httpx.post", post)
    app = AppTest.from_file(APP_PATH).run()
    app.chat_input[0].set_value("Hola").run()
    assert not app.exception
    assert app.error
    assert "private-connection-detail" not in app.error[0].value
    app.run()
    app.sidebar.button[0].click().run()
    assert len(calls) == 1


@pytest.mark.parametrize("status", [422, 429, 500])
def test_api_errors_are_shown_in_chat(monkeypatch, status):
    def post(*args, **kwargs):
        return httpx.Response(
            status,
            headers={"Retry-After": "12"},
            json={
                "request_id": str(uuid4()),
                "error": {"code": "EXAMPLE", "message": "No se pudo recibir.", "retryable": True},
            },
        )

    monkeypatch.setattr("supportflow.client.httpx.post", post)
    app = AppTest.from_file(APP_PATH).run()
    app.chat_input[0].set_value("Hola").run()
    assert not app.exception
    assert "No se pudo recibir." in app.error[0].value
    if status == 429:
        assert "12 segundos" in app.error[0].value


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="not json"),
        httpx.Response(200, json={}),
        httpx.Response(503, text="private-details"),
    ],
)
def test_unexpected_server_responses_do_not_expose_body(monkeypatch, response):
    monkeypatch.setattr("supportflow.client.httpx.post", lambda *args, **kwargs: response)
    result = send_message("Hola", api_url="http://127.0.0.1:8010/")
    assert result.is_error
    assert "respuesta inesperada" in result.text
    assert "private-details" not in result.text


def test_api_url_configuration(monkeypatch):
    monkeypatch.setenv("SUPPORTFLOW_API_URL", "http://localhost:9000/prefix/")
    calls = []

    def post(url, **kwargs):
        calls.append(url)
        return receipt_response()

    monkeypatch.setattr("supportflow.client.httpx.post", post)
    app = AppTest.from_file(APP_PATH).run()
    app.chat_input[0].set_value("Hola").run()
    assert not app.exception
    assert calls == ["http://localhost:9000/prefix/api/agent/messages"]


def test_invalid_configuration_is_safe(monkeypatch):
    monkeypatch.setenv("SUPPORTFLOW_API_URL", "private-invalid-setting")
    app = AppTest.from_file(APP_PATH).run()
    assert not app.exception
    assert "no está configurado" in app.error[0].value
    assert "private-invalid-setting" not in app.error[0].value
    assert not app.chat_input


def test_chat_integrates_with_fastapi_validation(monkeypatch, client):
    calls = []

    def post(url, *, json, timeout, follow_redirects):
        calls.append(json)
        return client.post("/api/agent/messages", json=json)

    monkeypatch.setattr("supportflow.client.httpx.post", post)
    app = AppTest.from_file(APP_PATH).run()
    app.chat_input[0].set_value("No puedo iniciar sesión.").run()
    assert not app.exception
    assert "Mensaje recibido" in app.chat_message[-1].text[0].value
    app.chat_input[0].set_value("\u200b\u2060").run()
    assert not app.exception
    assert "mensaje visible" in app.error[0].value
    assert len(calls) == 2
