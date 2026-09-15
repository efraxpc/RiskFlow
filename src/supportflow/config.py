from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SUPPORTFLOW_", env_file=".env", extra="ignore")

    api_url: AnyHttpUrl = AnyHttpUrl("http://127.0.0.1:8010")
    http_timeout_seconds: float = Field(default=40, gt=0, le=60)
    max_body_bytes: int = Field(default=16_384, gt=0)
    rate_limit: int = Field(default=10, gt=0)
    rate_window_seconds: float = Field(default=60, gt=0)
    azure_openai_enabled: bool = False
    azure_openai_endpoint: AnyHttpUrl | None = None
    azure_openai_deployment: str | None = Field(default=None, min_length=1, max_length=128)
    azure_openai_auth: Literal["entra", "api_key"] = "entra"
    azure_openai_api_key: SecretStr | None = None
    azure_openai_timeout_seconds: float = Field(default=30, gt=0, le=120)
    azure_openai_max_output_tokens: int = Field(default=512, ge=128, le=4_096)

    @model_validator(mode="after")
    def validate_azure_openai(self) -> Settings:
        if not self.azure_openai_enabled:
            return self
        if self.azure_openai_endpoint is None:
            raise ValueError("azure_openai_endpoint es obligatorio cuando Azure está habilitado")
        if self.azure_openai_endpoint.scheme != "https":
            raise ValueError("azure_openai_endpoint debe usar HTTPS")
        hostname = self.azure_openai_endpoint.host or ""
        allowed_hosts = (".openai.azure.com", ".services.ai.azure.com")
        if not hostname.endswith(allowed_hosts):
            raise ValueError("azure_openai_endpoint debe ser un endpoint de Azure OpenAI")
        if not self.azure_openai_deployment:
            raise ValueError("azure_openai_deployment es obligatorio cuando Azure está habilitado")
        if self.azure_openai_auth == "api_key" and self.azure_openai_api_key is None:
            raise ValueError("azure_openai_api_key es obligatorio con autenticación api_key")
        return self

    @property
    def azure_openai_base_url(self) -> str:
        if self.azure_openai_endpoint is None:
            raise RuntimeError("Azure OpenAI no está configurado")
        endpoint = str(self.azure_openai_endpoint).rstrip("/")
        if not endpoint.endswith("/openai/v1"):
            endpoint += "/openai/v1"
        return endpoint + "/"
