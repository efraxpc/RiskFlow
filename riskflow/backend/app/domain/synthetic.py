"""Seeded generator for the five safe demonstration scenarios."""

from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from random import Random
from uuid import NAMESPACE_URL, uuid5

from app.domain.enums import OrderScenario
from app.domain.models import OrderItem, SyntheticOrder


@dataclass(frozen=True, slots=True)
class ScenarioProfile:
    amount_range_cents: tuple[int, int]
    account_age_range: tuple[int, int]
    billing_region: str
    shipping_region: str
    payment_region: str
    orders_last_hour: int
    expedited_shipping: bool
    simulate_out_of_stock: bool = False
    simulate_payment_failure: bool = False


SCENARIO_PROFILES: dict[OrderScenario, ScenarioProfile] = {
    OrderScenario.NORMAL: ScenarioProfile(
        amount_range_cents=(2_500, 25_000),
        account_age_range=(180, 1_500),
        billing_region="ZONE_A",
        shipping_region="ZONE_A",
        payment_region="ZONE_A",
        orders_last_hour=1,
        expedited_shipping=False,
    ),
    OrderScenario.SUSPICIOUS: ScenarioProfile(
        amount_range_cents=(20_000, 75_000),
        account_age_range=(1, 20),
        billing_region="ZONE_A",
        shipping_region="ZONE_B",
        payment_region="ZONE_A",
        orders_last_hour=2,
        expedited_shipping=False,
    ),
    OrderScenario.CRITICAL: ScenarioProfile(
        amount_range_cents=(125_000, 250_000),
        account_age_range=(0, 5),
        billing_region="ZONE_D",
        shipping_region="ZONE_C",
        payment_region="ZONE_A",
        orders_last_hour=6,
        expedited_shipping=True,
    ),
    OrderScenario.PAYMENT_FAILURE: ScenarioProfile(
        amount_range_cents=(5_000, 30_000),
        account_age_range=(365, 2_000),
        billing_region="ZONE_B",
        shipping_region="ZONE_B",
        payment_region="ZONE_B",
        orders_last_hour=1,
        expedited_shipping=False,
        simulate_payment_failure=True,
    ),
    OrderScenario.REPEATED_RETRY: ScenarioProfile(
        amount_range_cents=(5_000, 30_000),
        account_age_range=(365, 2_000),
        billing_region="ZONE_C",
        shipping_region="ZONE_C",
        payment_region="ZONE_C",
        orders_last_hour=1,
        expedited_shipping=False,
    ),
}


def _stable_random(seed: int, scenario: OrderScenario) -> Random:
    material = f"riskflow:v1:{seed}:{scenario.value}".encode()
    numeric_seed = int.from_bytes(sha256(material).digest(), byteorder="big")
    return Random(numeric_seed)


def generate_synthetic_order(seed: int, scenario: OrderScenario | str) -> SyntheticOrder:
    """Create a reproducible order without names, addresses, or payment details."""

    selected_scenario = OrderScenario(scenario)
    profile = SCENARIO_PROFILES[selected_scenario]
    randomizer = _stable_random(seed, selected_scenario)
    cents = randomizer.randint(*profile.amount_range_cents)
    total = (Decimal(cents) / Decimal(100)).quantize(Decimal("0.01"))
    account_age_days = randomizer.randint(*profile.account_age_range)
    identity = f"{selected_scenario.value}:{seed}"
    customer_digest = sha256(f"customer:{identity}".encode()).hexdigest()[:12].upper()
    sku_suffix = randomizer.choice(("ALPHA", "BETA", "GAMMA", "DELTA"))

    return SyntheticOrder(
        order_id=uuid5(NAMESPACE_URL, f"riskflow:order:{identity}"),
        seed=seed,
        scenario=selected_scenario,
        customer_ref=f"DEMO-{customer_digest}",
        items=(OrderItem(sku=f"SKU-{sku_suffix}", quantity=1, unit_price=total),),
        order_total=total,
        account_age_days=account_age_days,
        billing_region=profile.billing_region,
        shipping_region=profile.shipping_region,
        payment_region=profile.payment_region,
        orders_last_hour=profile.orders_last_hour,
        expedited_shipping=profile.expedited_shipping,
        simulate_out_of_stock=profile.simulate_out_of_stock,
        simulate_payment_failure=profile.simulate_payment_failure,
    )
