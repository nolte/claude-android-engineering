# claude-android-engineering

[![CI](https://github.com/nolte/claude-android-engineering/actions/workflows/ci.yml/badge.svg)](https://github.com/nolte/claude-android-engineering/actions/workflows/ci.yml)
[![Release Drafter](https://github.com/nolte/claude-android-engineering/actions/workflows/release-drafter.yml/badge.svg)](https://github.com/nolte/claude-android-engineering/actions/workflows/release-drafter.yml)

Reusable, spec-based [Claude Code](https://claude.com/claude-code) skills and
agents for native Android engineering — project setup, Jetpack Compose UI,
feature implementation as a flat view layer, permissions and notifications,
QR/barcode scanning, USB (UVC) cameras, localization, test suites and CI,
toolchain upgrades, perceived performance, local debugging, and read-only
UX, code, security, and release-readiness reviews.

## Purpose

- Gives Android developers (the operator, and anyone who installs the plugin)
  skills that scaffold, build, audit, and debug native Kotlin/Compose apps in
  conformance with an explicit, bilingual spec corpus under `spec/android/`.
- Every skill is grounded in a spec and closes on a green `./gradlew build`;
  when a decision is not covered by a spec, the skill reports the gap instead
  of deciding silently (`project/requirements/android-engineering-skills.md`).
- Read-only reviewer agents (UX, code, security, release readiness) surface
  findings with `file:line` and the violated spec section; the skills apply
  the fixes.
- Play-Store release tooling is out of scope; production-grade release-build
  quality of the source is in scope (`spec/android/release-readiness/`).

## Usage

Add this repository as a plugin marketplace in Claude Code and install the
plugin; the `nolte-shared` hub plugin supplies the inherited portfolio specs
and shared skills:

```shell
/plugin marketplace add nolte/claude-shared
/plugin install nolte-shared@nolte-shared
/plugin marketplace add nolte/claude-android-engineering
/plugin install claude-android-engineering@claude-android-engineering
```

Skills are then callable as `/claude-android-engineering:<name>` (for example
`/claude-android-engineering:android-project-scaffold`); the reviewer agents
are dispatched by the skills or directly via Claude Code's agent tool.

### Local development

```shell
task --yes setup   # install dev tooling and git hooks
task --yes check   # aggregate quality gate (lint + test), identical to CI
```

The Taskfile pulls shared targets from
[`nolte/taskfiles`](https://github.com/nolte/taskfiles) over the network. Task
resolves that include while parsing, so **every** target needs network access
and needs to trust the include's checksum — `--yes` grants that trust
non-interactively. You need it whenever no local `.task/` cache covers the
current upstream content: in a fresh clone, on every CI runner, and again after
the upstream file changes. Without a TTY it is not optional, because the
interactive trust prompt has nobody to answer it.

The optional `task docs:serve` preview additionally expects a `~/.venvs/docs`
environment; it tells you how to create one if it is missing.

## Structure

```text
.claude-plugin/  # plugin manifest (plugin.json)
skills/          # twelve skills: android-project-scaffold, android-compose-ui,
                 #   android-feature-implement, android-permissions-derive,
                 #   android-notification-derive, android-perceived-performance,
                 #   android-debugging, android-barcode-scanner-scaffold,
                 #   android-uvc-microscope-scaffold, android-localization-apply,
                 #   android-test-suite-apply, android-toolchain-upgrade
agents/          # read-only reviewers: android-ux-reviewer, android-code-reviewer,
                 #   android-security-reviewer, android-release-readiness-reviewer
spec/            # bilingual spec corpus (en canonical + de); android/ holds the Android specs
project/         # planning artifacts (requirements; mission/roadmap pending)
docs/            # MkDocs site sources, per-language trees (en/, de/)
scripts/         # validate_skills.py (the `task test` frontmatter gate)
AUDIENCES.md     # audience analysis for this repository
```

## Related repositories

- [nolte/claude-shared](https://github.com/nolte/claude-shared) — hub plugin; portfolio-wide specs and shared skills this repository inherits
- [nolte/gh-plumbing](https://github.com/nolte/gh-plumbing) — reusable GitHub workflows and Probot commons configs wired into `.github/`
- [nolte/taskfiles](https://github.com/nolte/taskfiles) — shared Taskfile collection included by the Taskfile (`mkdocs:*` targets)

## Status

Early stage: the spec corpus (19 Android specs, en canonical + de), twelve
skills, and four read-only reviewer agents are in place; every spec under
`spec/android/` is bound to at least one executor. The 2026-08-18 audit
remediation added the security, code, and release-readiness reviewers plus the
UVC, localization, test-suite, and toolchain-upgrade skills (REQ-22 to REQ-28,
recorded as `assumed` pending teach-back). Play-Store
release tooling is out of scope; production-grade release-build quality of the
source is covered by `spec/android/release-readiness/`.

## License

[MIT](LICENSE) — Copyright (c) 2026 nolte
