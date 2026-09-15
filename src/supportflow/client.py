from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from supportflow.models import ErrorResponse, ReceiptResponse


@dataclass(frozen=True)
class ChatResult:
    text: str
    is_error: bool = False


def send_message(message: str, *, api_url: str, timeout: float = 5) -> ChatResult:
    try:
        response = httpx.post(
            f"{api_url.rstrip('/')}/api/agent/messages",
            json={"message": message, "locale_hint": "es"},
            timeout=timeout,
            follow_redirects=False,
        )
    except httpx.TimeoutException:
        return ChatResult(
            "El envío tardó demasiado. Puedes enviar el mensaje de nuevo.", is_error=True
        )
    except httpx.RequestError:
        return ChatResult(
            "No pudimos conectar con el servicio. Inténtalo de nuevo más tarde.", is_error=True
        )

    try:
        if response.status_code == 200:
            receipt = ReceiptResponse.model_validate_json(response.content)
            return ChatResult(receipt.user_message)
        error = ErrorResponse.model_validate_json(response.content)
        text = error.error.message
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "")
            if retry_after.isdecimal() and len(retry_after) <= 6:
                text += f" Puedes intentarlo en {int(retry_after)} segundos."
        return ChatResult(text, is_error=True)
    except ValidationError:
        return ChatResult(
            "El servicio devolvió una respuesta inesperada. Inténtalo de nuevo más tarde.",
            is_error=True,
        )
