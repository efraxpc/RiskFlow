# RiskFlow implementation plan

Last updated: 2026-09-16

## Status key

- `[x]` complete and verified
- `[ ]` pending

## Phase 0 — Preparation

- [x] Preserve the existing SupportFlow repository by placing RiskFlow in an isolated directory.
- [x] Create `AGENTS.md`, `PLAN.md`, `README.md`, `.env.example`, and `.gitignore`.
- [x] Create a minimal FastAPI backend and a React/Vite/TypeScript frontend.
- [x] Document installation, development, and verification commands.
- [x] Add one basic backend test and one basic frontend test.
- [x] Add and verify a combined `start`, `restart`, and `stop` project runner.

Acceptance evidence:

- FastAPI started on a temporary local port and `GET /health` returned HTTP 200.
- Vite started on a temporary local port and served the application HTML.
- The project runner completed a real `start -> restart -> stop` lifecycle without orphan processes.
- Backend: 34 tests passed; Ruff lint/format and strict mypy passed.
- Frontend: 1 component test passed; ESLint, TypeScript, production build, and npm audit passed.
- A nested Git repository was intentionally not created because the parent directory is already versioned.

## Phase 1 — Domain and risk

- [x] Define closed enums for workflow states, risk levels, actions, scenarios, and signal codes.
- [x] Define typed order, item, risk-assessment, and risk-signal models.
- [x] Define the immutable, timezone-aware workflow-event model used by later phases.
- [x] Implement a reproducible synthetic-order generator from a seed and fixed scenario.
- [x] Implement an explainable deterministic risk engine, independent of FastAPI and persistence.
- [x] Add fixtures for the five demo scenarios.
- [x] Cover reproducibility, rule weights, score caps, thresholds, and scenario outcomes with tests.

Acceptance evidence:

- All 34 backend tests passed on Python 3.12.3 on 2026-09-16.
- The same seed and scenario produce the same complete order model, including `order_id`.
- Expected scenario levels: normal/failed payment/retry are low, suspicious is medium, critical is high.

## Phase 2 — Orchestrator

- [ ] Implement the state machine and allowed transitions.
- [ ] Record one event for every transition.
- [ ] Implement idempotent inventory reservation and payment simulators.
- [ ] Compensate inventory after payment failure.

Acceptance criterion: the happy path completes and a payment failure releases its reservation.

## Phase 3 — Persistence and API

- [ ] Add SQLAlchemy tables and SQLite repositories.
- [ ] Expose the minimum order, detail, review, and retry endpoints.
- [ ] Add explicit idempotency and error handling.

Acceptance criterion: orders and pending reviews survive a server restart.

## Phase 4 — Risk analyst agent

- [ ] Integrate one specialized agent with structured output.
- [ ] Add timeout, invalid-output handling, and deterministic local fallback.
- [ ] Record whether the explanation came from the LLM or local mode.
- [ ] Force human review when the agent disagrees with deterministic rules.

Acceptance criterion: workflows work with or without `OPENAI_API_KEY`; invalid model output is safe.

## Phase 5 — Human in the loop

- [ ] Persist approve/reject decisions, reason, and timestamp.
- [ ] Resume from `AWAITING_REVIEW` exactly once.
- [ ] Reject duplicate and incompatible review actions.

Acceptance criterion: a review survives restart and can only be resolved once.

## Phase 6 — Complete frontend

- [ ] Implement generator, order inbox, detail, risk meter, and timeline.
- [ ] Implement the human-review form and failure controls.
- [ ] Add loading, empty, and error states.
- [ ] Clearly attribute rule, agent, and human decisions.

Acceptance criterion: all five fixed scenarios can be demonstrated from the UI.

## Phase 7 — Quality and evaluation

- [ ] Add state-machine, integration, persistence, and end-to-end tests.
- [ ] Add a small synthetic agreement dataset.
- [ ] Add structured logs without sensitive data.

Acceptance criterion: documented lint, type, unit, integration, and critical-flow checks pass.

## Phase 8 — Presentation

- [ ] Add screenshots and final architecture documentation.
- [ ] Complete the two-minute demo script, limitations, and next steps.
- [ ] Add Docker only after the local MVP is stable.

Acceptance criterion: a new user can clone, run, and understand the project from the README.
