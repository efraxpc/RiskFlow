"""Explainable deterministic risk rules.

This module deliberately has no dependency on FastAPI, databases, or an LLM. Its
numeric score is authoritative throughout the future workflow.
"""

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from app.domain.enums import RecommendedAction, RiskLevel, RiskSignalCode
from app.domain.models import RiskAssessment, RiskSignal, SyntheticOrder


@dataclass(frozen=True, slots=True)
class RiskRule:
    code: RiskSignalCode
    points: int
    matches: Callable[[SyntheticOrder], bool]


RISK_RULES: tuple[RiskRule, ...] = (
    RiskRule(RiskSignalCode.NEW_ACCOUNT, 20, lambda order: order.account_age_days < 30),
    RiskRule(
        RiskSignalCode.ADDRESS_MISMATCH,
        25,
        lambda order: order.billing_region != order.shipping_region,
    ),
    RiskRule(
        RiskSignalCode.HIGH_ORDER_VALUE,
        20,
        lambda order: order.order_total >= Decimal("1000.00"),
    ),
    RiskRule(RiskSignalCode.HIGH_VELOCITY, 25, lambda order: order.orders_last_hour >= 4),
    RiskRule(
        RiskSignalCode.REGION_MISMATCH,
        20,
        lambda order: order.billing_region != order.payment_region,
    ),
    RiskRule(
        RiskSignalCode.EXPEDITED_SHIPPING,
        10,
        lambda order: order.expedited_shipping,
    ),
)


def classify_score(score: int) -> tuple[RiskLevel, RecommendedAction]:
    """Map a bounded score to the published RiskFlow thresholds."""

    if not 0 <= score <= 100:
        raise ValueError("risk score must be between 0 and 100")
    if score <= 29:
        return RiskLevel.LOW, RecommendedAction.AUTO_APPROVE
    if score <= 69:
        return RiskLevel.MEDIUM, RecommendedAction.HUMAN_REVIEW
    return RiskLevel.HIGH, RecommendedAction.PRIORITY_REVIEW


def calculate_risk(order: SyntheticOrder) -> RiskAssessment:
    """Evaluate all rules, cap the score, and retain every matching signal."""

    signals = tuple(
        RiskSignal(code=rule.code, points=rule.points) for rule in RISK_RULES if rule.matches(order)
    )
    score = min(sum(signal.points for signal in signals), 100)
    level, action = classify_score(score)
    return RiskAssessment(
        score=score,
        level=level,
        recommended_action=action,
        signals=signals,
    )
