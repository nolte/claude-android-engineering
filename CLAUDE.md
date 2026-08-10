# CLAUDE.md

Guidance for AI-assisted development in this repository.

## What this repository is

A Claude Code plugin providing reusable, **spec-based** skills for native Android
app development: project setup, Compose UI authoring, mobile-UX audit, perceived
performance, and local development/debugging. Play-Store release tooling is
explicitly out of scope.

## Load-bearing conventions

- **Spec-first:** every skill is grounded in a spec under `spec/`. When a
  structural or convention decision is not covered by any spec, report the gap
  and propose a spec extension — never decide silently
  (`project/requirements/android-engineering-skills.md`, REQ-6/REQ-17).
- **Specs are bilingual:** `spec/<topic>/<slug>/{en,de}.md`, canonical `en`,
  managed via the `nolte-shared:spec` skill. Portfolio-wide specs are inherited
  from `nolte-shared` (pinned in `spec/.spec-config.yml`) — never copied.
- **Success criterion for every skill:** output conforms to the underlying
  spec's acceptance criteria AND any generated/modified project builds green
  with `./gradlew build` (REQ-1).
- **Never leave a red state unreported; never overwrite without confirmation;
  never scaffold with outdated mechanisms** (kapt, monolithic buildSrc,
  Groovy DSL) — REQ-7/8/9.

## Layout

- `spec/` — bilingual spec corpus (`spec/README.md` is the generated index)
- `project/requirements/` — elicited requirement artifacts
- `AUDIENCES.md` — audience analysis for this repo
- `skills/`, `agents/`, `.claude-plugin/` — plugin surface (scaffolded per
  skill via `nolte-claude-dev:skill-management`; not yet present)

## Command entry points

All automation runs through the Taskfile (`task --list`):

- `task setup` — install dev tooling (pre-commit hooks)
- `task check` — aggregate quality gate (lint + test); identical in CI
- `task lint` / `task test` / `task docs` — individual targets

## Branching

`develop` is the integration branch (PRs target it, squash-merge only);
`main` tracks the released state and is fast-forwarded by release automation.
