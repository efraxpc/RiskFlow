from decimal import Decimal

import pytest

from app.domain.enums import OrderScenario, RecommendedAction, RiskLevel, RiskSignalCode
from app.domain.risk import RISK_RULES, calculate_risk, classify_score
from app.domain.synthetic import generate_synthetic_order


@pytest.mark.parametrize(
    ("score", "level", "action"),
    [
        (0, RiskLevel.LOW, RecommendedAction.AUTO_APPROVE),
        (29, RiskLevel.LOW, RecommendedAction.AUTO_APPROVE),
        (30, RiskLevel.MEDIUM, RecommendedAction.HUMAN_REVIEW),
        (69, RiskLevel.MEDIUM, RecommendedAction.HUMAN_REVIEW),
        (70, RiskLevel.HIGH, RecommendedAction.PRIORITY_REVIEW),
        (100, RiskLevel.HIGH, RecommendedAction.PRIORITY_REVIEW),
    ],
)
def test_risk_threshold_boundaries(score: int, level: RiskLevel, action: RecommendedAction) -> None:
    assert classify_score(score) == (level, action)


@pytest.mark.parametrize("score", [-1, 101])
def test_risk_threshold_rejects_unbounded_scores(score: int) -> None:
    with pytest.raises(ValueError, match="between 0 and 100"):
        classify_score(score)


def test_published_rule_weights_remain_explicit() -> None:
    weights = {rule.code: rule.points for rule in RISK_RULES}

    assert weights == {
        RiskSignalCode.NEW_ACCOUNT: 20,
        RiskSignalCode.ADDRESS_MISMATCH: 25,
        RiskSignalCode.HIGH_ORDER_VALUE: 20,
        RiskSignalCode.HIGH_VELOCITY: 25,
        RiskSignalCode.REGION_MISMATCH: 20,
        RiskSignalCode.EXPEDITED_SHIPPING: 10,
    }


@pytest.mark.parametrize(
    ("scenario", "expected_level", "expected_action"),
    [
        (OrderScenario.NORMAL, RiskLevel.LOW, RecommendedAction.AUTO_APPROVE),
        (OrderScenario.SUSPICIOUS, RiskLevel.MEDIUM, RecommendedAction.HUMAN_REVIEW),
        (OrderScenario.CRITICAL, RiskLevel.HIGH, RecommendedAction.PRIORITY_REVIEW),
        (OrderScenario.PAYMENT_FAILURE, RiskLevel.LOW, RecommendedAction.AUTO_APPROVE),
        (OrderScenario.REPEATED_RETRY, RiskLevel.LOW, RecommendedAction.AUTO_APPROVE),
    ],
)
def test_demo_scenario_has_expected_risk(
    scenario: OrderScenario,
    expected_level: RiskLevel,
    expected_action: RecommendedAction,
) -> None:
    assessment = calculate_risk(generate_synthetic_order(seed=20260916, scenario=scenario))

    assert assessment.level is expected_level
    assert assessment.recommended_action is expected_action


def test_suspicious_scenario_explains_its_score() -> None:
    assessment = calculate_risk(
        generate_synthetic_order(seed=22, scenario=OrderScenario.SUSPICIOUS)
    )

    assert assessment.score == 45
    assert [signal.code for signal in assessment.signals] == [
        RiskSignalCode.NEW_ACCOUNT,
        RiskSignalCode.ADDRESS_MISMATCH,
    ]


def test_critical_score_is_capped_but_keeps_all_signals() -> None:
    assessment = calculate_risk(generate_synthetic_order(seed=99, scenario=OrderScenario.CRITICAL))

    assert assessment.score == 100
    assert sum(signal.points for signal in assessment.signals) > assessment.score
    assert len(assessment.signals) == len(RISK_RULES)


def test_high_value_boundary_is_inclusive() -> None:
    order = generate_synthetic_order(seed=5, scenario=OrderScenario.NORMAL)
    item = order.items[0].model_copy(update={"unit_price": Decimal("1000.00")})
    boundary_order = order.model_copy(update={"items": (item,), "order_total": Decimal("1000.00")})

    assessment = calculate_risk(boundary_order)

    assert RiskSignalCode.HIGH_ORDER_VALUE in {signal.code for signal in assessment.signals}
