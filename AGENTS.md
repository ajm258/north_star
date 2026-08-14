# Codex / Agent Instructions

## Project

Portfolio Intelligence is a long-term investment portfolio decision-support and early-warning application.

It is NOT a trading bot and must not issue automated Buy/Sell decisions.

## Non-negotiable principles

- Preserve financial history; do not silently overwrite historical records.
- Transactions are the source of truth for portfolio accounting where transaction data exists.
- Holdings are derived state.
- Financial calculations must be deterministic and independently tested.
- Never delegate arithmetic, P&L, allocation, return, volume, or valuation calculations to an LLM.
- External providers must be abstracted behind interfaces.
- LLM outputs must be structured and schema-validated.
- Separate facts, interpretation, and uncertainty in LLM analysis.
- The system must detect both positive and negative developments.
- The application should surface information for human decisions, not make the investment decision.
- Avoid real-time trading features; the intended decision horizon starts at the next day and extends to medium/long-term investing.
- Do not introduce technical trading strategies as a core feature.

## Change-first philosophy

The system is primarily interested in meaningful change versus:
- the previous observation,
- recent history,
- historical baselines,
- the investment thesis,
- the portfolio context.

## Escalation philosophy

A small daily movement should normally receive only brief context. Persistent or material movements should trigger deeper investigation. Fundamental changes can trigger investigation even without large price movements.

## Engineering expectations

- Prefer a modular monolith initially.
- Keep components independently testable.
- Use migrations for schema changes.
- Add tests with every financial calculation or business rule.
- Avoid unrelated refactors in feature branches.
- Update documentation when behavior or architecture changes.
- Never hard-code API keys or secrets.
- Handle provider rate limits, missing data, retries, and stale data explicitly.
- Record source/provider and timestamps for externally collected data where practical.

## Definition of done

Before completing a task:
1. Implementation is complete.
2. Relevant tests are added or updated.
3. Existing tests pass.
4. Formatting/linting checks pass where configured.
5. Database migrations are included when needed.
6. Documentation is updated when behavior/architecture changes.
7. The git diff contains no unrelated changes.
8. Known limitations are reported.

## When blocked

If an implementation requires a product or accounting decision not defined in the specification, stop and flag the decision rather than silently inventing semantics.

Examples:
- cost-basis method
- tax treatment
- currency conversion semantics
- dividend treatment
- stock split treatment
- broker reconciliation semantics
- signal thresholds with material consequences

Read the relevant documents in `docs/` before making implementation decisions.
