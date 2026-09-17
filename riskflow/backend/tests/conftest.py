"""Shared pytest fixtures for RiskFlow's fixed demo scenarios."""

from collections.abc import Callable

import pytest

from app.domain.enums import OrderScenario
from app.domain.models import SyntheticOrder
from app.domain.synthetic import generate_synthetic_order


@pytest.fixture
def order_factory() -> Callable[[int, OrderScenario], SyntheticOrder]:
    return generate_synthetic_order


@pytest.fixture(params=list(OrderScenario), ids=lambda scenario: scenario.value)
def demo_order(request: pytest.FixtureRequest) -> SyntheticOrder:
    scenario = OrderScenario(request.param)
    return generate_synthetic_order(seed=20260916, scenario=scenario)
