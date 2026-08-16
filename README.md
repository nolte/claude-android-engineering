# claude-android-engineering

[![CI](https://github.com/nolte/claude-android-engineering/actions/workflows/ci.yml/badge.svg)](https://github.com/nolte/claude-android-engineering/actions/workflows/ci.yml)
[![Release Drafter](https://github.com/nolte/claude-android-engineering/actions/workflows/release-drafter.yml/badge.svg)](https://github.com/nolte/claude-android-engineering/actions/workflows/release-drafter.yml)

Reusable, spec-based [Claude Code](https://claude.com/claude-code) skills and
agents for native Android engineering — project setup, Jetpack Compose UI,
feature implementation as a flat view layer, mobile UX, perceived performance,
QR/barcode scanning, and local debugging.

## Purpose

<!-- TODO(audience-doc-author): replace with two to six bullets describing the
problem this repository solves, naming the primary audiences from
AUDIENCES.md (android-dev-operator, public-plugin-consumers). -->

Replace this with two to six bullets describing the problem this repository
solves and who its intended consumers are.

## Usage

<!-- TODO(audience-doc-author): document the plugin install path once the
distribution channel (marketplace vs git reference) is decided. -->

```shell
# TODO: plugin installation command (distribution channel pending)
```

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
skills/          # eight skills: android-project-scaffold, android-compose-ui,
                 #   android-feature-implement, android-permissions-derive,
                 #   android-notification-derive, android-perceived-performance,
                 #   android-debugging, android-barcode-scanner-scaffold
agents/          # android-ux-reviewer (read-only UI audit)
spec/            # bilingual spec corpus (en canonical + de); android/ holds the Android specs
project/         # planning artifacts (requirements; mission/roadmap pending)
docs/            # MkDocs site sources, per-language trees (en/, de/)
scripts/         # validate_skills.py (the `task test` frontmatter gate)
AUDIENCES.md     # audience analysis for this repository
```

## Related repositories

- [nolte/claude-shared](https://github.com/nolte/claude-shared) — hub plugin; portfolio-wide specs and shared skills this repository inherits
- [nolte/gh-plumbing](https://github.com/nolte/gh-plumbing) — reusable GitHub workflows and Probot commons configs wired into `.github/`
- [nolte/taskfiles](https://github.com/nolte/taskfiles) — shared Taskfile collection (not yet included here)

## Status

Early stage: the spec corpus, repository structure, and the first skills
(project scaffold, Compose UI, feature implementation, perceived performance,
debugging, barcode scanner) plus the UX-review agent are in place. Play-Store
release tooling is out of scope; production-grade release-build quality of the
source is covered by `spec/android/release-readiness/`.

## License

[MIT](LICENSE) — Copyright (c) 2026 nolte
