# AGENTS.md

## Purpose
This repository hosts the delivery artifacts for the `AI-Powered Investment Advisor`, a SaaS platform for algorithmic analysis and investment simulation focused on B3-listed assets.

This file is the default operating manual for any coding agent working in this repository. Read it before making changes, and treat it as binding unless a more specific task file explicitly narrows the scope.

## Source Of Truth Hierarchy
1. `docs/ef/Especificacao_Funcional_AI_Investment_Advisor.docx`
2. `docs/adr/*.md`
3. Executable specs in `specs/`
4. Task files in `backlog/**/task-*.md`
5. Existing code and tests

If any lower-level artifact conflicts with a higher-level artifact, stop and update the lower-level artifact or ask for guidance instead of inventing a compromise in code.

## Product Boundaries
- Phase 1 is simulation only. Do not implement broker order routing or real-money execution.
- Do not generate or expose personalized investment recommendations in a way that would characterize regulated advisory activity.
- All user-facing signal, insight, or explanation surfaces must preserve the legal disclaimer and anti-recommendation posture defined in the functional specification.
- Historical analysis must be point-in-time safe. Never use data that would not have been available at the simulated timestamp.

## Expected Repository Layout
- `docs/ef/`: functional specification and business summaries
- `docs/adr/`: architecture decision records
- `docs/domain/`: bounded-context notes
- `docs/runbooks/`: operational runbooks
- `specs/`: executable contracts such as OpenAPI, GraphQL, event schemas, and SQL DDL
- `backlog/`: vertical-slice tasks
- `services/`: deployable services
- `packages/`: shared libraries
- `tests/unit`, `tests/contract`, `tests/e2e`: automated verification layers

## Working Model For Agents
- Start by reading the relevant task file in `backlog/`.
- Read all applicable ADRs before writing code.
- Prefer implementing against a contract in `specs/` instead of inventing interfaces ad hoc.
- Keep changes scoped to the current vertical slice.
- If a task requires changing an approved executable spec, stop and surface that dependency explicitly.

## Required Engineering Standards
- Keep commits in Conventional Commits style, for example: `feat(ingestion-market): normalize provider ticks`
- Prefer strict typing and schema-first contracts.
- Preserve tenant isolation on every user-scoped entity and query.
- Preserve immutability for facts such as ticks, candles, news, trades, and audit events.
- Add or update automated tests with every behavior change.
- Favor small, reviewable changes over broad scaffolding not tied to an acceptance criterion.

## Guardrails

### Anti-Recommendation Policy
- Forbidden in user-facing copy unless part of a legal disclaimer, test fixture, or quoted regulatory text:
  - `compre`
  - `venda`
  - `invista`
  - `aplique agora`
  - `entrada garantida`
  - `lucro certo`
- Prefer descriptive phrasing such as:
  - `cenario historicamente associado`
  - `sinal compativel com`
  - `probabilidade estimada`
  - `simulacao sugere`
- Add or maintain an automated check that fails when forbidden verbs appear in UI copy or templated narratives.

### Point-In-Time Safety
- Every query against historical or derived market data must flow through an explicit `as_of(timestamp)` access pattern or equivalent repository/helper.
- Derived features must store both reference time and availability time when applicable.
- Backtests and paper-trading replays must not join against future revisions of fundamentals, news, or model features.
- Maintain at least one automated leakage test in `tests/contract/` or `tests/e2e/` for each domain that replays historical inputs.

## What Not To Do
- Do not add broker integrations for execution in Phase 1.
- Do not rewrite approved ADR decisions inside implementation code.
- Do not alter `specs/` casually to make tests pass.
- Do not introduce direct access paths that bypass tenancy, audit, or point-in-time controls.
- Do not add persuasive or imperative investment language to the UI, reports, or assistant outputs.
- Do not build large horizontal layers without a linked task or acceptance criteria.

## Delivery Definition
For any non-trivial task, the working definition of done is:
- Relevant unit tests added or updated
- Contract tests added or updated when a spec exists
- `make check` or equivalent repo-wide verification passes
- Docs updated when behavior, contracts, or decisions change
- Scope stays inside the task file

## Verification Commands
The implementation stack is not finalized yet. Until the stack ADR is concretized, every service or package added to the repo must expose a repo-level check entrypoint that can be wired into the command below.

Preferred commands once the toolchain is committed:
- `make lint`
- `make typecheck`
- `make test`
- `make contract-test`
- `make check`

If these commands do not yet exist, create them before relying on ad hoc local commands.

## Migrations And Data Changes
- All schema evolution must be versioned.
- Facts are append-only by default. Corrections should create new versions, not overwrite prior facts.
- Financial, fiscal, and risk parameter changes must be time-versioned and auditable.

## Task Prompt Pattern
Use `docs/templates/task-prompt.md` as the default prompt scaffold when handing a slice to an implementation agent.
