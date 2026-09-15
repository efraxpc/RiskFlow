import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from supportflow.azure_openai import ModelFailure, ModelResponder, create_model_responder
from supportflow.config import Settings
from supportflow.errors import RequestError, error_response
from supportflow.intake import build_context, read_message
from supportflow.models import ErrorResponse, MessageRequest, ReceiptResponse
from supportflow.rate_limit import RateLimiter
from supportflow.telemetry import RequestTelemetryMiddleware

CONFIRMATIONS = {
    "es": "Mensaje recibido. Esta versión solo confirma la recepción de tu consulta.",
    "en": "Message received. This version only confirms receipt of your request.",
    "pt": "Mensagem recebida. Esta versão apenas confirma o recebimento da sua consulta.",
}


def create_app(
    settings: Settings | None = None, *, responder: ModelResponder | None = None
) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        try:
            yield
        finally:
            model_responder = application.state.model_responder
            if model_responder is not None:
                await model_responder.close()

    api = FastAPI(
        title="SupportFlow",
        version="0.1.0",
        description="Recepción validada y respuestas de soporte mediante Azure OpenAI.",
        lifespan=lifespan,
    )
    api.state.settings = settings
    api.state.rate_limiter = RateLimiter(settings.rate_limit, settings.rate_window_seconds)
    api.state.model_responder = responder or create_model_responder(settings)
    api.add_middleware(RequestTelemetryMiddleware)

    @api.exception_handler(RequestError)
    async def handle_request_error(request: Request, error: RequestError):
        return error_response(request, error)

    @api.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, error: RequestValidationError):
        return error_response(
            request,
            RequestError(422, "INVALID_REQUEST", "La solicitud no tiene un formato válido."),
        )

    @api.exception_handler(HTTPException)
    async def handle_http_error(request: Request, error: HTTPException):
        return error_response(
            request,
            RequestError(
                error.status_code,
                "HTTP_ERROR",
                "La ruta o el método solicitado no está disponible.",
                headers=error.headers,
            ),
        )

    @api.get("/health", tags=["Servicio"])
    async def health() -> dict[str, str]:
        mode = "azure_openai" if api.state.model_responder is not None else "receipt"
        return {"status": "ok", "response_mode": mode}

    @api.post(
        "/api/agent/messages",
        response_model=ReceiptResponse,
        tags=["Mensajes"],
        summary="Validar un mensaje y generar una respuesta de soporte",
        responses={
            status: {"model": ErrorResponse}
            for status in (400, 401, 413, 415, 422, 429, 500, 502, 503, 504)
        },
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": MessageRequest.model_json_schema()}},
            }
        },
    )
    async def receive_message(
        request: Request, payload: Annotated[MessageRequest, Depends(read_message)]
    ) -> ReceiptResponse:
        context = build_context(payload, request.state.request_id)
        responder = request.app.state.model_responder
        if responder is not None:
            try:
                user_message = await responder.respond(context.text, context.locale_hint)
            except ModelFailure as error:
                status_code = 504 if error.kind == "timeout" else 502
                if error.kind == "unavailable":
                    status_code = 503
                raise RequestError(
                    status_code,
                    f"MODEL_{error.kind.upper()}",
                    "El asistente no está disponible temporalmente. Inténtalo de nuevo.",
                    retryable=True,
                ) from None
            request.state.result_code = "ANSWERED"
            return ReceiptResponse(
                request_id=context.request_id,
                status="answered",
                received_at=context.received_at,
                user_message=user_message,
            )

        request.state.result_code = "RECEIVED"
        return ReceiptResponse(
            request_id=context.request_id,
            received_at=context.received_at,
            user_message=CONFIRMATIONS[context.locale_hint],
        )

    return api


request_logger = logging.getLogger("supportflow.requests")
request_logger.setLevel(logging.INFO)
if not request_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    request_logger.addHandler(handler)
app = create_app()
