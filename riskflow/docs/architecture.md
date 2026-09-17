# RiskFlow architecture

## Design constraints

- The deterministic risk engine owns the numeric score.
- The future LLM adapter may explain and recommend, but it cannot mutate inventory or payments.
- Critical transitions belong to the workflow orchestrator.
- Medium and high risk must enter a durable human-review state.
- Every side effect uses `order_id` as its idempotency key.
- A payment failure after inventory reservation must produce a release/compensation operation.

## Target component view

```text
React UI
   |
FastAPI API
   |
WorkflowOrchestrator
   |-- order validation              pure deterministic service
   |-- risk calculation              pure deterministic service
   |-- RiskAnalystAgent              LLM adapter or local fallback
   |-- human review                  durable decision
   |-- inventory simulator           idempotent side effect
   `-- payment simulator             idempotent side effect
              |
       SQLite repositories + event log
```

Only the FastAPI shell, domain models, seeded generator, and risk calculation exist after phase 1. The empty adapter packages mark future boundaries without introducing placeholder abstractions.

## Domain flow

```text
RECEIVED -> VALIDATED -> RISK_ASSESSED

low risk:       RISK_ASSESSED -> APPROVED
medium/high:    RISK_ASSESSED -> AWAITING_REVIEW -> APPROVED | REJECTED
approved:       APPROVED -> INVENTORY_RESERVED -> PAYMENT_COMPLETED -> COMPLETED
payment error:  INVENTORY_RESERVED -> FAILED -> COMPENSATED
```

The closed state enum already exists so later phases cannot silently invent workflow states. Transition validation and events deliberately wait for phase 2.

## Safe synthetic data

Generated orders contain a UUID, a `DEMO-*` reference, SKU, amount, abstract billing/shipping/payment regions, account age, velocity, and simulator flags. They never contain a real name, postal address, email, card number, or payment credential.
