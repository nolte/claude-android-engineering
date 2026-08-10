# claude-android-engineering

[![CI](https://github.com/nolte/claude-android-engineering/actions/workflows/ci.yml/badge.svg)](https://github.com/nolte/claude-android-engineering/actions/workflows/ci.yml)
[![Release Drafter](https://github.com/nolte/claude-android-engineering/actions/workflows/release-drafter.yml/badge.svg)](https://github.com/nolte/claude-android-engineering/actions/workflows/release-drafter.yml)

Reusable, spec-based [Claude Code](https://claude.com/claude-code) skills and
agents for native Android engineering — project setup, Jetpack Compose UI,
mobile UX, perceived performance, and local debugging.

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
task setup   # install dev tooling and git hooks
task check   # aggregate quality gate (lint + test), identical to CI
```

## Structure

```text
spec/       # bilingual spec corpus (en canonical + de); android/ topic holds the Android specs
project/    # planning artifacts (requirements; mission/roadmap pending)
docs/       # MkDocs site sources, per-language trees (en/, de/)
AUDIENCES.md  # audience analysis for this repository
skills/     # plugin skills (pending — scaffolded per skill via skill-management)
```

## Related repositories

- [nolte/claude-shared](https://github.com/nolte/claude-shared) — hub plugin; portfolio-wide specs and shared skills this repository inherits
- [nolte/gh-plumbing](https://github.com/nolte/gh-plumbing) — reusable GitHub workflows and Probot commons configs wired into `.github/`
- [nolte/taskfiles](https://github.com/nolte/taskfiles) — shared Taskfile collection (not yet included here)

## Status

Early stage: spec corpus and repository structure are in place; the first
skills are not yet published.

## License

[MIT](LICENSE) — Copyright (c) 2026 nolte
