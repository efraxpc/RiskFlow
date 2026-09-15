import json
from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from pydantic import ValidationError

from supportflow.errors import RequestError
from supportflow.models import MessageRequest, RequestContext


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Clave duplicada.")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("Constante JSON no permitida.")


async def read_message(request: Request) -> MessageRequest:
    settings = request.app.state.settings
    client_ip = request.client.host if request.client else "unknown"
    request.app.state.rate_limiter.check(client_ip)

    if "authorization" in request.headers:
        raise RequestError(
            401,
            "INVALID_CREDENTIALS",
            "Esta versión solo admite consultas anónimas. Envía el mensaje sin credenciales.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    media_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if media_type != "application/json":
        raise RequestError(415, "UNSUPPORTED_MEDIA_TYPE", "Envía el mensaje como JSON.")
    encoding = request.headers.get("content-encoding", "identity").strip().lower()
    if encoding != "identity":
        raise RequestError(
            415, "UNSUPPORTED_CONTENT_ENCODING", "No se admiten cuerpos comprimidos."
        )

    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > settings.max_body_bytes:
            raise RequestError(
                413, "BODY_TOO_LARGE", "El cuerpo de la solicitud es demasiado grande."
            )
        body.extend(chunk)

    try:
        payload = json.loads(
            body.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant
        )
    except ValueError, RecursionError:
        raise RequestError(
            400, "MALFORMED_JSON", "El JSON no es válido o contiene claves duplicadas."
        ) from None

    try:
        return MessageRequest.model_validate(payload)
    except ValidationError:
        raise RequestError(
            422,
            "INVALID_REQUEST",
            "Envía un mensaje visible de 1 a 4.000 caracteres y un idioma válido (es, en o pt). "
            "Solo se admiten los campos message y locale_hint.",
        ) from None


def build_context(payload: MessageRequest, request_id: UUID) -> RequestContext:
    return RequestContext(
        request_id=request_id,
        text=payload.message,
        locale_hint=payload.locale_hint,
        received_at=datetime.now(UTC),
    )
