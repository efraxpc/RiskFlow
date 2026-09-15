from fastapi import Request
from fastapi.responses import JSONResponse

from supportflow.models import ErrorDetail, ErrorResponse


class RequestError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(code)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retryable = retryable
        self.headers = headers or {}


def error_response(request: Request, error: RequestError) -> JSONResponse:
    request.state.result_code = error.code
    payload = ErrorResponse(
        request_id=request.state.request_id,
        error=ErrorDetail(code=error.code, message=error.message, retryable=error.retryable),
    )
    return JSONResponse(
        status_code=error.status_code,
        content=payload.model_dump(mode="json"),
        headers=error.headers,
    )
