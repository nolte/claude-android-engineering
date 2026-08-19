# CLAUDE.md

Guidance for AI-assisted development in this repository.

## What this repository is

A Claude Code plugin providing reusable, **spec-based** skills for native Android
app development: project setup, Compose UI authoring, feature implementation
across layers, mobile-UX audit, perceived performance, and local
development/debugging. Play-Store release *tooling* is explicitly out of scope;
production-grade release-build quality of the source is in scope
(`spec/android/release-readiness/`).

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
- `.claude-plugin/plugin.json` — plugin manifest
- `skills/` — `android-project-scaffold` (REQ-12), `android-compose-ui`
  (REQ-13), `android-perceived-performance` (REQ-15), `android-debugging`
  (REQ-16), `android-barcode-scanner-scaffold` (REQ-18),
  `android-feature-implement` (REQ-19), `android-permissions-derive` (REQ-20),
  `android-notification-derive` (REQ-21), `android-test-suite-apply` (REQ-25),
  `android-toolchain-upgrade` (REQ-26), `android-uvc-microscope-scaffold`
  (REQ-27), `android-localization-apply` (REQ-28);
  each grounded in the matching `spec/android/` spec
- `agents/` — read-only reviewers that return a review-plan report the caller
  persists under `.audits/<review-type>/`: `android-ux-reviewer` (REQ-14),
  `android-security-reviewer` (REQ-22), `android-release-readiness-reviewer`
  (REQ-23), `android-code-reviewer` (REQ-24)
- `scripts/validate_skills.py` — frontmatter contract check wired as `task test`;
  scope one target with `python3 scripts/validate_skills.py skills/<name>/`. Only
  `Critical` findings fail CI (exit 1); Warning/Suggestion/Info are advisory.
- `docs/{en,de}/` — bilingual MkDocs site (`mkdocs.yml`), built strictly in CI

## Command entry points

All automation runs through the Taskfile (`task --list`):

- `task setup` — install dev tooling (pre-commit hooks)
- `task check` — aggregate quality gate (lint + test)
- `task lint` / `task test` / `task docs` — individual targets
- `task docs:serve` — local MkDocs preview with live reload on
  `http://localhost:8001/` (preview only, not part of any gate)
- CI runs `task check` **and** `task docs` (strict MkDocs build) as separate
  steps (`.github/workflows/ci.yml`) — a green local gate means both pass
- The Taskfile includes the shared `nolte/taskfiles` collection (`mkdocs:*`).
  Task resolves includes while parsing, so the remote-taskfiles experiment gates
  *every* target, not just the ones consuming the collection; the checked-in
  `.taskrc.yml` enables it, so no environment variable is needed. `task --yes`
  is still required wherever no include cache exists (every CI runner) to accept
  the checksum prompt unattended
- Gate targets (`lint`, `docs`) and `setup` stay on their local commands: the
  collection's targets source `~/.venvs/{development,docs}`, which CI lacks, and
  `pre-commit:install` never installs pre-commit itself. Only `docs:serve`
  (preview, never a gate) consumes a collection target

## Branching

`develop` is the integration branch (PRs target it, squash-merge only);
`main` tracks the released state and is fast-forwarded by release automation.
