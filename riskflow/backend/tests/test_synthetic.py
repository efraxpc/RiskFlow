from collections.abc import Callable

import pytest
from pydantic import ValidationError

from app.domain.enums import OrderScenario
from app.domain.models import SyntheticOrder
from app.domain.synthetic import generate_synthetic_order


@pytest.mark.parametrize("scenario", list(OrderScenario))
def test_generator_is_reproducible(scenario: OrderScenario) -> None:
    first = generate_synthetic_order(seed=42, scenario=scenario)
    second = generate_synthetic_order(seed=42, scenario=scenario)

    assert first == second
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_seed_changes_synthetic_identity() -> None:
    first = generate_synthetic_order(seed=1, scenario=OrderScenario.NORMAL)
    second = generate_synthetic_order(seed=2, scenario=OrderScenario.NORMAL)

    assert first.order_id != second.order_id
    assert first.customer_ref != second.customer_ref


def test_payment_failure_scenario_only_sets_synthetic_failure_flag() -> None:
    order = generate_synthetic_order(seed=7, scenario=OrderScenario.PAYMENT_FAILURE)

    assert order.simulate_payment_failure is True
    assert order.simulate_out_of_stock is False


def test_demo_fixture_covers_every_scenario(demo_order: SyntheticOrder) -> None:
    assert demo_order.scenario in OrderScenario
    assert demo_order.customer_ref.startswith("DEMO-")


def test_order_rejects_a_total_that_does_not_match_items(
    order_factory: Callable[[int, OrderScenario], SyntheticOrder],
) -> None:
    order = order_factory(9, OrderScenario.NORMAL)

    with pytest.raises(ValidationError, match="order_total must equal"):
        SyntheticOrder.model_validate({**order.model_dump(), "order_total": order.order_total + 1})


def test_unknown_scenario_is_rejected() -> None:
    with pytest.raises(ValueError, match="not-a-scenario"):
        generate_synthetic_order(seed=1, scenario="not-a-scenario")
