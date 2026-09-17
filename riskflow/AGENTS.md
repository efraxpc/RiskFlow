# RiskFlow project instructions

## Product rules

- Use only synthetic customer and payment data.
- The deterministic risk engine is authoritative for the numeric score.
- The LLM may explain or recommend but must not directly perform payment or inventory mutations.
- Medium and high risk require a durable human-review state.
- A payment failure after reservation must release inventory.
- All side-effecting operations must be idempotent.

## Engineering rules

- Follow `PLAN.md` and implement one phase at a time.
- Keep domain logic independent from FastAPI, database, and LLM adapters.
- Use typed models and closed enums for states and risk levels.
- Never commit secrets; update `.env.example` when configuration changes.
- Prefer small modules and explicit interfaces over premature abstractions.
- Keep the scope to one specialized risk analyst agent.

## Verification

- Run backend formatting, lint, type checks, and pytest after backend changes.
- Run frontend lint, type checks, and tests after frontend changes.
- Add or update tests whenever business behavior changes.
- Before finishing a phase, report changed files, commands run, results, and remaining risks.

