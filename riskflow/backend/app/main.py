"""FastAPI entry point for the phase 0 application shell."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Stable response returned by the service health check."""

    status: Literal["ok"]
    service: Literal["riskflow"]
    phase: int


app = FastAPI(
    title="RiskFlow API",
    description="Auditable workflow for synthetic e-commerce orders.",
    version="0.1.0",
)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Report that the API process is ready to accept requests."""

    return HealthResponse(status="ok", service="riskflow", phase=1)
