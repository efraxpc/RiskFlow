import json
import logging
import time
from uuid import uuid4

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from supportflow.errors import RequestError, error_response

logger = logging.getLogger("supportflow.requests")


class RequestTelemetryMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        state = scope.setdefault("state", {})
        state["request_id"] = uuid4()
        state["result_code"] = "HTTP_RESPONSE"
        started_at = time.monotonic()
        status_code = 500
        response_started = False

        async def send_with_headers(message: Message) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() not in (b"x-request-id", b"cache-control")
                ]
                headers.extend(
                    [
                        (b"x-request-id", str(state["request_id"]).encode("ascii")),
                        (b"cache-control", b"no-store"),
                    ]
                )
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        except Exception:
            state["result_code"] = "INTERNAL_ERROR"
            if response_started:
                raise
            response = error_response(
                Request(scope),
                RequestError(
                    500,
                    "INTERNAL_ERROR",
                    "No pudimos recibir tu mensaje. Inténtalo de nuevo más tarde.",
                    retryable=True,
                ),
            )
            await response(scope, receive, send_with_headers)
        finally:
            logger.info(
                json.dumps(
                    {
                        "request_id": str(state["request_id"]),
                        "status_code": status_code,
                        "result_code": state["result_code"],
                        "duration_ms": round((time.monotonic() - started_at) * 1000, 2),
                    }
                )
            )
