from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.enums import WorkflowState
from app.domain.models import WorkflowEvent


def test_workflow_event_accepts_an_auditable_transition() -> None:
    order_id = uuid4()
    event = WorkflowEvent(
        event_id=uuid4(),
        order_id=order_id,
        occurred_at=datetime(2026, 9, 16, 12, 0, tzinfo=UTC),
        previous_state=WorkflowState.RECEIVED,
        new_state=WorkflowState.VALIDATED,
        reason="Synthetic order passed validation",
    )

    assert event.order_id == order_id
    assert event.previous_state is WorkflowState.RECEIVED
    assert event.new_state is WorkflowState.VALIDATED


def test_workflow_event_rejects_a_naive_timestamp() -> None:
    with pytest.raises(ValidationError, match="must include a timezone"):
        WorkflowEvent(
            event_id=uuid4(),
            order_id=uuid4(),
            occurred_at=datetime(2026, 9, 16, 12, 0),
            previous_state=None,
            new_state=WorkflowState.RECEIVED,
            reason="Synthetic order received",
        )
