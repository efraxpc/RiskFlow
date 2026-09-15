import asyncio
import json
from collections import deque
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from supportflow.config import Settings
from supportflow.intake import build_context
from supportflow.main import create_app
from supportflow.models import MessageRequest, normalize_message
from supportflow.rate_limit import RateLimiter


def assert_error(response, status, code):
    assert response.status_code == status
    data = response.json()
    assert set(data) == {"request_id", "error"}
    assert data["error"]["code"] == code
    assert isinstance(data["error"]["retryable"], bool)
    assert UUID(data["request_id"])
    assert response.headers["x-request-id"] == data["request_id"]
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    ("locale", "expected"),
    [("es", "Mensaje recibido"), ("en", "Message received"), ("pt", "Mensagem recebida")],
)
def test_receipt_is_not_a_classification(client, locale, expected):
    before = datetime.now(UTC)
    supplied_id = str(uuid4())
    response = client.post(
        "/api/agent/messages",
        json={"message": "No puedo iniciar sesión desde ayer.", "locale_hint": locale},
        headers={"X-Request-ID": supplied_id},
    )
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"request_id", "status", "received_at", "user_message"}
    assert data["status"] == "received"
    assert data["user_message"].startswith(expected)
    assert str(UUID(data["request_id"])) != supplied_id
    received_at = datetime.fromisoformat(data["received_at"])
    assert received_at.utcoffset().total_seconds() == 0
    assert before <= received_at <= datetime.now(UTC)
    assert response.headers["x-request-id"] == data["request_id"]
    assert response.headers["cache-control"] == "no-store"
    assert "No puedo" not in response.text


def test_default_locale_and_visible_unicode(client):
    for text in ("Hola", "á" * 4000, "😀" * 4000, "你好", "Olá", "print('hola')\n\tx = 2"):
        response = client.post("/api/agent/messages", json={"message": text})
        assert response.status_code == 200
        assert response.json()["user_message"].startswith("Mensaje recibido")


@pytest.mark.parametrize("text", ["  cafe\u0301\r\n\tx = 1\r  ", "Hola", "¿Configurar?", "😀"])
def test_normalization_and_server_context(text):
    payload = MessageRequest(message=text)
    assert normalize_message(payload.message) == payload.message
    context = build_context(payload, uuid4())
    assert context.text == normalize_message(text)
    assert context.channel == "api"
    assert context.principal.kind == "anonymous"
    assert context.principal.subject_id is None
    assert context.principal.permissions == ("public:read",)
    with pytest.raises(ValidationError):
        context.principal.kind = "admin"
    if "cafe" in text:
        assert context.text == "café\n\tx = 1"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        [],
        None,
        42,
        {"message": None},
        {"message": 42},
        {"message": True},
        {"message": []},
        {"message": {}},
        {"message": ""},
        {"message": " \r\n\t "},
        {"message": "\u200b\ufeff\u2060"},
        {"message": "\x00\x01"},
        {"message": "\ufe0f"},
        {"message": "\ud800"},
        {"message": "a" * 4001},
        {"message": "Hola", "locale_hint": "fr"},
        {"message": "Hola", "locale_hint": None},
        {"message": "Hola", "locale_hint": 1},
        {"message": "Hola", "permissions": ["admin"]},
        {"message": "Hola", "principal": {"kind": "admin"}},
        {"message": "Hola", "channel": "web"},
        {"message": "Hola", "request_id": str(uuid4())},
        {"message": "Hola", "received_at": "2026-09-14"},
    ],
)
def test_strict_invalid_requests(client, payload):
    # ensure_ascii permite probar incluso un sustituto Unicode inválido por HTTP.
    response = client.post(
        "/api/agent/messages",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    assert_error(response, 422, "INVALID_REQUEST")


def test_length_is_checked_after_normalization(client):
    text = " " * 20 + "e\u0301" * 4000 + "\r\n"
    response = client.post("/api/agent/messages", json={"message": text})
    assert response.status_code == 200


@pytest.mark.parametrize(
    "body",
    [
        b"{",
        b"",
        b"\xff",
        b'{"message":"Hola","message":"Otro"}',
        b'{"message":"Hola","extra":{"a":1,"a":2}}',
        b'{"message":NaN}',
        b'{"message":Infinity}',
        b'{"message":"Hola"} trailing',
        b"[" * 1200 + b"0",
    ],
    ids=[
        "incomplete",
        "empty",
        "invalid-utf8",
        "duplicate",
        "nested-duplicate",
        "nan",
        "infinity",
        "trailing",
        "nested-incomplete",
    ],
)
def test_malformed_json_and_duplicate_keys(client, body):
    response = client.post(
        "/api/agent/messages", content=body, headers={"Content-Type": "application/json"}
    )
    assert_error(response, 400, "MALFORMED_JSON")


@pytest.mark.parametrize("credentials", ["Bearer invalid", "Basic invalid", ""])
def test_credentials_are_never_ignored(client, credentials):
    response = client.post(
        "/api/agent/messages",
        json={"message": "Hola"},
        headers={"Authorization": credentials},
    )
    assert_error(response, 401, "INVALID_CREDENTIALS")
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("media_type", [None, "text/plain", "application/octet-stream"])
def test_media_type_is_required(client, media_type):
    headers = {"Content-Type": media_type} if media_type else {}
    response = client.post("/api/agent/messages", content='{"message":"Hola"}', headers=headers)
    assert_error(response, 415, "UNSUPPORTED_MEDIA_TYPE")


def test_json_with_charset_is_accepted(client):
    response = client.post(
        "/api/agent/messages",
        content='{"message":"Hola"}',
        headers={"Content-Type": "application/json; charset=utf-8", "Content-Encoding": "identity"},
    )
    assert response.status_code == 200


@pytest.mark.parametrize("encoding", ["gzip", "br", "deflate"])
def test_compressed_bodies_are_rejected(client, encoding):
    response = client.post(
        "/api/agent/messages", json={"message": "Hola"}, headers={"Content-Encoding": encoding}
    )
    assert_error(response, 415, "UNSUPPORTED_CONTENT_ENCODING")


def test_oversized_body(client):
    response = client.post(
        "/api/agent/messages",
        content=b" " * 16_385,
        headers={"Content-Type": "application/json"},
    )
    assert_error(response, 413, "BODY_TOO_LARGE")


@pytest.mark.parametrize("declared_length", [None, b"1"])
def test_fragmented_body_is_limited_before_parse(declared_length, monkeypatch):
    app = create_app(Settings(_env_file=None, max_body_bytes=1024))
    headers = [(b"content-type", b"application/json")]
    if declared_length is not None:
        headers.append((b"content-length", declared_length))
    chunks = deque([b"x" * 600, b"x" * 600, b"unread"])
    responses = []

    def unexpected_parse(*args, **kwargs):
        pytest.fail("Un cuerpo excesivo no debe llegar al parser JSON.")

    monkeypatch.setattr("supportflow.intake.json.loads", unexpected_parse)

    async def run_request():
        async def receive():
            chunk = chunks.popleft()
            return {"type": "http.request", "body": chunk, "more_body": bool(chunks)}

        async def send(message):
            responses.append(message)

        await app(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "POST",
                "scheme": "http",
                "path": "/api/agent/messages",
                "raw_path": b"/api/agent/messages",
                "query_string": b"",
                "root_path": "",
                "headers": headers,
                "client": ("127.0.0.1", 1234),
                "server": ("127.0.0.1", 8010),
            },
            receive,
            send,
        )

    asyncio.run(run_request())
    assert responses[0]["status"] == 413
    assert len(chunks) == 1


def test_quota_ignores_forwarded_headers_and_expires(client, app):
    now = [100.0]
    app.state.rate_limiter = RateLimiter(2, 60, clock=lambda: now[0])
    for fake_ip in ("1.1.1.1", "2.2.2.2"):
        response = client.post(
            "/api/agent/messages",
            json={"message": "Hola"},
            headers={"X-Forwarded-For": fake_ip, "Forwarded": f"for={fake_ip}"},
        )
        assert response.status_code == 200
    blocked = client.post("/api/agent/messages", json={"message": "Hola"})
    assert_error(blocked, 429, "RATE_LIMITED")
    assert blocked.headers["retry-after"] == "60"
    assert blocked.json()["error"]["retryable"] is True
    now[0] += 10.1
    blocked = client.post("/api/agent/messages", json={"message": "Hola"})
    assert blocked.headers["retry-after"] == "50"
    now[0] = 160.0
    assert client.post("/api/agent/messages", json={"message": "Hola"}).status_code == 200


def test_quota_is_reserved_before_json_parse(client, app):
    app.state.rate_limiter = RateLimiter(1, 60)
    assert client.post("/api/agent/messages", json={"message": ""}).status_code == 422
    response = client.post(
        "/api/agent/messages", content="bad json", headers={"Content-Type": "application/json"}
    )
    assert_error(response, 429, "RATE_LIMITED")


def test_default_quota_is_ten_and_health_is_exempt():
    from fastapi.testclient import TestClient

    with TestClient(create_app(Settings(_env_file=None))) as client:
        for _ in range(10):
            assert client.post("/api/agent/messages", json={"message": "Hola"}).status_code == 200
        assert_error(
            client.post("/api/agent/messages", json={"message": "Hola"}), 429, "RATE_LIMITED"
        )
        assert client.get("/health").json() == {"status": "ok", "response_mode": "receipt"}
        assert client.get("/docs").status_code == 200


def test_distinct_ips_have_separate_quotas():
    limiter = RateLimiter(1, 60)
    limiter.check("127.0.0.1")
    limiter.check("127.0.0.2")
    from supportflow.errors import RequestError

    with pytest.raises(RequestError) as error:
        limiter.check("127.0.0.1")
    assert error.value.status_code == 429


def test_openapi_documents_receipts_and_strict_input(client):
    schema = client.get("/openapi.json").json()
    operation = schema["paths"]["/api/agent/messages"]["post"]
    payload = operation["requestBody"]["content"]["application/json"]["schema"]
    assert payload["additionalProperties"] is False
    assert payload["required"] == ["message"]
    assert payload["properties"]["message"]["maxLength"] == 4000
    assert (
        "ReceiptResponse"
        in operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    )
    assert set(schema["components"]["schemas"]["ReceiptResponse"]["properties"]) == {
        "request_id",
        "status",
        "received_at",
        "user_message",
    }


def test_logs_and_validation_errors_do_not_include_user_content(client, caplog):
    secret = "private-token-example-123"
    with caplog.at_level("INFO", logger="supportflow.requests"):
        valid = client.post("/api/agent/messages", json={"message": secret})
        invalid = client.post("/api/agent/messages", json={"message": secret, "extra": secret})
    assert secret not in caplog.text
    assert secret not in valid.text
    assert secret not in invalid.text
    records = [
        json.loads(record.message)
        for record in caplog.records
        if record.name == "supportflow.requests"
    ]
    assert [record["result_code"] for record in records] == ["RECEIVED", "INVALID_REQUEST"]
    for record in records:
        assert set(record) == {"request_id", "status_code", "result_code", "duration_ms"}


def test_internal_error_has_safe_envelope_and_headers(client, app, caplog):
    @app.get("/explode")
    async def explode():
        raise RuntimeError("private-provider-detail")

    with caplog.at_level("INFO", logger="supportflow.requests"):
        response = client.get("/explode")
    assert_error(response, 500, "INTERNAL_ERROR")
    assert "private-provider-detail" not in response.text + caplog.text


def test_configuration_is_validated():
    for values in (
        {"rate_limit": 0},
        {"max_body_bytes": 0},
        {"http_timeout_seconds": 0},
        {"api_url": "invalid"},
    ):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, **values)
