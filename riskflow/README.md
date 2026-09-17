# RiskFlow

RiskFlow is a portfolio project for processing synthetic e-commerce orders through an auditable workflow. The target MVP combines deterministic validation and risk rules, one LLM risk analyst, durable human review, idempotent inventory/payment simulators, and compensation after payment failure.

This repository currently implements **phases 0 and 1**: the local application skeleton, typed domain models, reproducible synthetic scenarios, and the deterministic risk engine. The workflow, persistence, API operations, and LLM adapter are intentionally deferred to the next phases tracked in [`PLAN.md`](PLAN.md).

Only fictitious identifiers and synthetic operational attributes are generated. No customer names, addresses, cards, or real payments are used.

## Current architecture

```text
React/Vite UI (phase 0 shell)       FastAPI (health endpoint)
                                              |
                                  domain models + generator
                                              |
                                  deterministic risk rules
```

The future boundaries and transition ownership are documented in [`docs/architecture.md`](docs/architecture.md).

## Requirements

- [uv](https://docs.astral.sh/uv/) (it installs/uses Python 3.12 for the backend)
- Node.js 20 or newer
- npm 10 or newer

An OpenAI key is **not required**. `OPENAI_API_KEY` is reserved for phase 4; the future application will default to a deterministic local explanation whenever it is absent.

## Backend

```bash
cd riskflow/backend
uv sync --all-groups
uv run uvicorn app.main:app --reload --port 8000
```

Open <http://127.0.0.1:8000/health>. Verification commands:

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

## Frontend

In another terminal:

```bash
cd riskflow/frontend
npm ci
npm run dev
```

Open <http://127.0.0.1:5173>. Verification commands:

```bash
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

## Synthetic scenarios

The backend exposes five fixed scenario profiles through `generate_synthetic_order(seed, scenario)`:

| Scenario | Expected risk | Purpose |
| --- | --- | --- |
| `normal` | low | automatic happy path in a later phase |
| `suspicious` | medium | durable human approval |
| `critical` | high | prioritized human review/rejection |
| `payment_failure` | low | future reservation and compensation path |
| `repeated_retry` | low | future idempotency demonstration |

The seed changes synthetic amounts and identifiers without changing a scenario's intended behavior. The complete generated model is reproducible across repeated calls.

## Configuration

Copy `.env.example` to `.env` only when configuration is needed. Never commit `.env` or secrets.

## Project layout

```text
riskflow/
  backend/       FastAPI shell and independent domain package
  frontend/      React/Vite shell
  docs/          architecture and demo notes
  AGENTS.md      persistent product and engineering rules
  PLAN.md        phase status and acceptance criteria
```

## Next step

Implement only phase 2: the state machine, transition event log, idempotent inventory/payment simulators, and payment-failure compensation. See [`PLAN.md`](PLAN.md) before changing scope.
