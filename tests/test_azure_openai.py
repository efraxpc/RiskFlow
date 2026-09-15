import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from supportflow.azure_openai import AzureOpenAIResponder, ModelFailure
from supportflow.config import Settings
from supportflow.main import create_app

AZURE_ENDPOINT = "https://example.services.ai.azure.com/"
AZURE_DEPLOYMENT = "support-model"


class FakeResponder:
    def __init__(self, *, answer: str = "Prueba estos pasos.", failure: str | None = None) -> None:
        self.answer = answer
        self.failure = failure
        self.calls = []
        self.closed = False

    async def respond(self, text, locale):
        self.calls.append((text, locale))
        if self.failure is not None:
            raise ModelFailure(self.failure)
        return self.answer

    async def close(self):
        self.closed = True


def azure_settings(**overrides):
    values = {
        "azure_openai_enabled": True,
        "azure_openai_endpoint": AZURE_ENDPOINT,
        "azure_openai_deployment": AZURE_DEPLOYMENT,
        "rate_limit": 1000,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_fastapi_returns_the_azure_answer_and_closes_the_client():
    responder = FakeResponder(answer="Restablece la contraseña desde tu perfil.")
    with TestClient(create_app(azure_settings(), responder=responder)) as client:
        response = client.post(
            "/api/agent/messages",
            json={"message": "No puedo iniciar sesión", "locale_hint": "es"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "answered"
        assert response.json()["user_message"] == "Restablece la contraseña desde tu perfil."
        assert client.get("/health").json()["response_mode"] == "azure_openai"
        assert responder.calls == [("No puedo iniciar sesión", "es")]
    assert responder.closed


@pytest.mark.parametrize(
    ("failure", "status", "code"),
    [
        ("timeout", 504, "MODEL_TIMEOUT"),
        ("unavailable", 503, "MODEL_UNAVAILABLE"),
        ("invalid_response", 502, "MODEL_INVALID_RESPONSE"),
    ],
)
def test_model_failures_have_safe_retryable_responses(failure, status, code):
    responder = FakeResponder(failure=failure)
    with TestClient(create_app(azure_settings(), responder=responder)) as client:
        response = client.post("/api/agent/messages", json={"message": "detalle privado"})
    assert response.status_code == status
    assert response.json()["error"] == {
        "code": code,
        "message": "El asistente no está disponible temporalmente. Inténtalo de nuevo.",
        "retryable": True,
    }
    assert "detalle privado" not in response.text


def test_azure_configuration_requires_a_secure_complete_endpoint():
    invalid = (
        {"azure_openai_enabled": True},
        {
            "azure_openai_enabled": True,
            "azure_openai_endpoint": "http://example.services.ai.azure.com",
            "azure_openai_deployment": AZURE_DEPLOYMENT,
        },
        {
            "azure_openai_enabled": True,
            "azure_openai_endpoint": "https://example.com",
            "azure_openai_deployment": AZURE_DEPLOYMENT,
        },
        {
            "azure_openai_enabled": True,
            "azure_openai_endpoint": AZURE_ENDPOINT,
            "azure_openai_deployment": AZURE_DEPLOYMENT,
            "azure_openai_auth": "api_key",
        },
    )
    for values in invalid:
        with pytest.raises(ValidationError):
            Settings(_env_file=None, **values)


def test_azure_client_uses_v1_responses_and_keeps_instructions_separate(monkeypatch):
    captured = {}

    class FakeResponses:
        async def create(self, **kwargs):
            captured["request"] = kwargs
            return SimpleNamespace(status="completed", output_text="  Respuesta segura.  ")

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.responses = FakeResponses()

        async def close(self):
            captured["closed"] = True

    monkeypatch.setattr("supportflow.azure_openai.AsyncOpenAI", FakeOpenAI)
    settings = azure_settings(azure_openai_auth="api_key", azure_openai_api_key="secret")
    responder = AzureOpenAIResponder(settings)

    async def exercise():
        answer = await responder.respond("texto de usuario", "es")
        await responder.close()
        return answer

    answer = asyncio.run(exercise())

    assert answer == "Respuesta segura."
    assert captured["client"]["base_url"] == AZURE_ENDPOINT + "openai/v1/"
    assert captured["client"]["max_retries"] == 0
    assert captured["request"]["model"] == AZURE_DEPLOYMENT
    assert captured["request"]["input"] == "texto de usuario"
    assert "texto de usuario" not in captured["request"]["instructions"]
    assert captured["closed"] is True
