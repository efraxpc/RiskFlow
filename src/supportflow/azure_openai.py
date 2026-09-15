from typing import Literal, Protocol

from azure.core.exceptions import ClientAuthenticationError
from azure.identity import CredentialUnavailableError
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from supportflow.config import Settings
from supportflow.models import Locale

MAX_RESPONSE_CHARS = 8_000
AZURE_TOKEN_SCOPE = "https://ai.azure.com/.default"

INSTRUCTIONS = {
    "es": (
        "Eres el asistente de soporte técnico de SupportFlow. Responde en español de forma "
        "clara, breve y práctica. Si falta un dato esencial, haz una sola pregunta concreta. "
        "No afirmes que creaste tickets, cambiaste cuentas o ejecutaste acciones externas."
    ),
    "en": (
        "You are SupportFlow's technical support assistant. Reply in clear, concise, practical "
        "English. If essential information is missing, ask one specific question. Do not claim "
        "that you created tickets, changed accounts, or performed external actions."
    ),
    "pt": (
        "Você é o assistente de suporte técnico do SupportFlow. Responda em português de forma "
        "clara, breve e prática. Se faltar um dado essencial, faça uma única pergunta objetiva. "
        "Não afirme que criou chamados, alterou contas ou executou ações externas."
    ),
}


class ModelResponder(Protocol):
    async def respond(self, text: str, locale: Locale) -> str: ...

    async def close(self) -> None: ...


class ModelFailure(Exception):
    def __init__(self, kind: Literal["timeout", "unavailable", "invalid_response"]) -> None:
        super().__init__(kind)
        self.kind = kind


class AzureOpenAIResponder:
    def __init__(self, settings: Settings) -> None:
        if not settings.azure_openai_enabled or settings.azure_openai_deployment is None:
            raise RuntimeError("Azure OpenAI no está habilitado")

        self.deployment = settings.azure_openai_deployment
        self.max_output_tokens = settings.azure_openai_max_output_tokens
        self.credential: DefaultAzureCredential | None = None

        if settings.azure_openai_auth == "api_key":
            if settings.azure_openai_api_key is None:
                raise RuntimeError("Falta la clave de Azure OpenAI")
            authentication = settings.azure_openai_api_key.get_secret_value()
        else:
            self.credential = DefaultAzureCredential()
            authentication = get_bearer_token_provider(self.credential, AZURE_TOKEN_SCOPE)

        self.client = AsyncOpenAI(
            base_url=settings.azure_openai_base_url,
            api_key=authentication,
            timeout=settings.azure_openai_timeout_seconds,
            max_retries=0,
        )

    async def respond(self, text: str, locale: Locale) -> str:
        try:
            response = await self.client.responses.create(
                model=self.deployment,
                instructions=INSTRUCTIONS[locale],
                input=text,
                reasoning={"effort": "low"},
                max_output_tokens=self.max_output_tokens,
            )
        except APITimeoutError:
            raise ModelFailure("timeout") from None
        except (
            APIConnectionError,
            APIStatusError,
            ClientAuthenticationError,
            CredentialUnavailableError,
        ):
            raise ModelFailure("unavailable") from None

        answer = response.output_text.strip()
        if response.status != "completed" or not answer or len(answer) > MAX_RESPONSE_CHARS:
            raise ModelFailure("invalid_response")
        return answer

    async def close(self) -> None:
        await self.client.close()
        if self.credential is not None:
            await self.credential.close()


def create_model_responder(settings: Settings) -> ModelResponder | None:
    if not settings.azure_openai_enabled:
        return None
    return AzureOpenAIResponder(settings)
