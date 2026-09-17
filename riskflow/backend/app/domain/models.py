"""Typed immutable models for synthetic orders and risk assessments."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.enums import (
    OrderScenario,
    RecommendedAction,
    RiskLevel,
    RiskSignalCode,
    WorkflowState,
)


class DomainModel(BaseModel):
    """Base configuration used by immutable domain values."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class OrderItem(DomainModel):
    sku: str = Field(pattern=r"^SKU-[A-Z0-9-]+$", max_length=32)
    quantity: int = Field(ge=1, le=20)
    unit_price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)

    @property
    def subtotal(self) -> Decimal:
        return self.unit_price * self.quantity


class SyntheticOrder(DomainModel):
    """An order containing only synthetic, non-personal attributes."""

    order_id: UUID
    seed: int
    scenario: OrderScenario
    customer_ref: str = Field(pattern=r"^DEMO-[A-F0-9]{12}$")
    items: tuple[OrderItem, ...] = Field(min_length=1, max_length=10)
    order_total: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    currency: str = Field(default="USD", pattern=r"^USD$")
    account_age_days: int = Field(ge=0, le=3650)
    billing_region: str = Field(pattern=r"^ZONE_[A-D]$")
    shipping_region: str = Field(pattern=r"^ZONE_[A-D]$")
    payment_region: str = Field(pattern=r"^ZONE_[A-D]$")
    orders_last_hour: int = Field(ge=0, le=100)
    expedited_shipping: bool
    simulate_out_of_stock: bool = False
    simulate_payment_failure: bool = False

    @model_validator(mode="after")
    def total_matches_items(self) -> "SyntheticOrder":
        calculated_total = sum((item.subtotal for item in self.items), start=Decimal("0"))
        if calculated_total != self.order_total:
            raise ValueError("order_total must equal the sum of item subtotals")
        return self


class RiskSignal(DomainModel):
    code: RiskSignalCode
    points: int = Field(gt=0, le=100)


class RiskAssessment(DomainModel):
    score: int = Field(ge=0, le=100)
    level: RiskLevel
    recommended_action: RecommendedAction
    signals: tuple[RiskSignal, ...]


class WorkflowEvent(DomainModel):
    """Auditable record shape used by the orchestrator from phase 2 onward."""

    event_id: UUID
    order_id: UUID
    occurred_at: datetime
    previous_state: WorkflowState | None
    new_state: WorkflowState
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("occurred_at")
    @classmethod
    def occurred_at_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone")
        return value
