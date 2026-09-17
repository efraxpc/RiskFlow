# Two-minute demo script (draft)

This script describes the final MVP and is not yet executable end to end. `PLAN.md` is the source of truth for current status.

1. Enter a seed and create the `normal` scenario. Show the low deterministic score and automatic completion.
2. Create `suspicious`. Explain its `NEW_ACCOUNT` and `ADDRESS_MISMATCH` signals, then approve it with a required reason.
3. Create `critical`. Compare rule evidence with the analyst summary, then reject it.
4. Create `payment_failure`. Show inventory reservation, payment failure, and the compensation event that releases stock.
5. Retry the same operation twice and show that the idempotency key prevents duplicate effects.
6. Close by showing the complete event timeline and whether each decision came from rules, the analyst, or a human.

Current phase 1 demonstration: run the backend tests to show that all five scenarios are reproducible and map to the intended deterministic risk level.

