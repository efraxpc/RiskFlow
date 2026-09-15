import unicodedata
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_MESSAGE_CHARS = 4_000
Locale = Literal["es", "en", "pt"]


def normalize_message(text: str) -> str:
    return unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n")).strip()


class StrictModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class MessageRequest(StrictModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    locale_hint: Locale = "es"

    @field_validator("message", mode="before")
    @classmethod
    def validate_message(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("El mensaje debe ser texto.")
        text = normalize_message(value)
        if any(unicodedata.category(char) == "Cs" for char in text):
            raise ValueError("El mensaje debe contener Unicode válido.")
        if not any(unicodedata.category(char)[0] in "LNPS" for char in text):
            raise ValueError("El mensaje debe tener contenido visible.")
        return text


class ReceiptResponse(StrictModel):
    request_id: UUID
    status: Literal["received", "answered"] = "received"
    received_at: datetime
    user_message: str = Field(min_length=1)


class ErrorDetail(StrictModel):
    code: str
    message: str
    retryable: bool


class ErrorResponse(StrictModel):
    request_id: UUID
    error: ErrorDetail


class AnonymousPrincipal(StrictModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    kind: Literal["anonymous"] = "anonymous"
    subject_id: None = None
    permissions: tuple[Literal["public:read"], ...] = ("public:read",)


class RequestContext(StrictModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    request_id: UUID
    channel: Literal["api"] = "api"
    principal: AnonymousPrincipal = Field(default_factory=AnonymousPrincipal)
    text: str
    locale_hint: Locale
    received_at: datetime
