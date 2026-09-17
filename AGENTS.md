# Repository Guidelines

## Project Structure & Module Organization

The repository contains two runnable stacks. The root SupportFlow application keeps its FastAPI package in `src/supportflow/`, its Streamlit entry point in `streamlit_app.py`, and tests in `tests/`. Architecture diagrams, API contracts, and implementation notes live in `docs/`. The newer `riskflow/` workspace has a FastAPI backend under `riskflow/backend/app/`, backend tests under `riskflow/backend/tests/`, and a React/Vite frontend under `riskflow/frontend/src/`. Read `riskflow/AGENTS.md` and `riskflow/PLAN.md` before changing that subtree; they define product invariants and phase scope.

## Build, Test, and Development Commands

From the repository root:

- `uv sync --locked` installs the locked SupportFlow environment.
- `./run.sh` starts FastAPI on port 8010 and Streamlit on 8510.
- `uv run pytest -q` runs root tests.
- `uv run ruff check .` and `uv run ruff format --check .` lint and verify formatting.

For RiskFlow, `cd riskflow && ./run.sh start` launches both applications. Run backend checks from `riskflow/backend` with `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run mypy app`. From `riskflow/frontend`, use `npm ci`, `npm run dev`, `npm run lint`, `npm run typecheck`, `npm test -- --run`, and `npm run build`.

## Coding Style & Naming Conventions

Python uses four-space indentation, type annotations, `snake_case` functions/modules, and `PascalCase` classes. Ruff enforces imports and style with a 100-character line limit; RiskFlow also requires strict mypy. TypeScript uses two spaces, single quotes, no semicolons, `PascalCase` React components, and `camelCase` functions. Keep domain rules deterministic and independent of HTTP, persistence, and LLM adapters.

## Testing Guidelines

Use pytest files named `test_*.py` and test functions named `test_*`. Frontend tests use Vitest and Testing Library with `*.test.tsx`. Add regression tests for every behavior change, especially validation boundaries, risk thresholds, error paths, and idempotency. No numeric coverage threshold is configured; passing all checks for the affected stack is required.

## Commit & Pull Request Guidelines

Recent commits favor concise, imperative Conventional Commit subjects such as `feat: initialize frontend`. Use prefixes such as `feat:`, `fix:`, `test:`, or `docs:` and keep each commit focused. Pull requests should summarize scope, reference the relevant issue or `PLAN.md` phase, list verification commands and results, and include screenshots for visible UI changes. Never commit `.env`, credentials, real customer/payment data, or generated secrets; update `.env.example` when configuration changes.
