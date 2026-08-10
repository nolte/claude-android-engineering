# Audiences — claude-android-engineering

<!--
Produced via the `audience-identify` skill, following
spec/project/audience-identification/.
Do not add audiences without first declaring the bounded context below.
-->

## Bounded context

- **What it is:** The entire repository `claude-android-engineering` as a Claude Code plugin — reusable, spec-based skills for Android app development (project setup, Compose UI, UX audit, perceived performance, local debugging) plus its spec corpus under `spec/android/`.
- **Boundary:** The plugin artifacts (skills, agents, specs, docs). The Android apps built *with* the skills are targets of the skills, not part of this context.
- **Explicitly outside:** Play-Store release tooling, the `nolte-shared` hub plugin itself, and the operator's individual app repositories.

## Audiences

Each entry: label, relationship category, interaction surface, expectation,
documentation `track` (`user-docs` or `developer-docs` per
spec/project/docs-audience-tracks/), open questions, `confirmed` or `assumed`,
criticality (primary / secondary / peripheral).

Portfolio-baseline track defaults applied: `user` → `user-docs`; `contributor` /
`operator` / `release-manager` → `developer-docs`.

### Direct consumers

- **Operator as Android developer (nolte)** — _id_: `android-dev-operator` · _category_: direct-consumer · _surface_: skill invocations in Claude Code sessions; specs as authoring reference · _expects_: skills that scaffold, build, audit, and debug Android projects in conformance with their underlying specs, leaving green builds (REQ-1) · _track_: `user-docs` · _status_: `confirmed` (self-identified by the operator in this run) · _criticality_: primary
  - Open questions: none
- **Public plugin consumers** — _id_: `public-plugin-consumers` · _category_: direct-consumer · _surface_: plugin installation, README/onboarding docs, skill invocations · _expects_: portable skills without operator-specific hardcoding; clear onboarding; documented conventions (REQ-10) · _track_: `user-docs` · _status_: `assumed` (no real external representative validated yet) · _criticality_: secondary
  - Open questions: primary docs language for external users (repo docs are bilingual en/de, canonical en); which distribution channel (marketplace vs git reference) they will install through

### Operators

- **Plugin maintainer in operations mode (nolte)** — _id_: `maintainer-operations` · _category_: operator · _surface_: GitHub Actions, release workflow, Renovate, spec-inherit pin maintenance (`nolte-shared@v0.1.11`), portfolio audits · _expects_: green CI, low-friction release flow, visible drift signals · _track_: `developer-docs` · _status_: `confirmed` (self-identified by the operator in this run) · _criticality_: secondary
  - Open questions: none

### Contributors / maintainers

- **Maintainer (nolte)** — _id_: `maintainer` · _category_: contributor-maintainer · _surface_: authoring skills/specs, merging PRs, review plans · _expects_: spec corpus and skill conventions that make authoring deterministic · _track_: `developer-docs` · _status_: `confirmed` (self-identified by the operator in this run) · _criticality_: secondary
  - Open questions: none
- **External OSS contributors** — _id_: `external-contributors` · _category_: contributor-maintainer · _surface_: GitHub PRs, issues, CONTRIBUTING docs · _expects_: contribution guidance, spec-first workflow explained, reviewable artifact conventions · _track_: `developer-docs` · _status_: `assumed` (hypothetical until the first external PR) · _criticality_: peripheral
  - Open questions: is CONTRIBUTING documentation needed before the first external PR arrives?
- **Claude Code agents** — _id_: `claude-agents` · _category_: contributor-maintainer · _surface_: the specs under `spec/` and `CLAUDE.md` as machine-readable guardrails; skill/agent definitions they execute · _expects_: unambiguous, complete specs (their only "documentation"); no undocumented conventions (REQ-6) · _track_: `developer-docs` · _status_: `assumed` (operator included them; promote once agent-authored artifacts demonstrably rely on the guardrails) · _criticality_: secondary
  - Open questions: none

### Governing parties

- **Portfolio governance (nolte-shared spec layer + portfolio audits)** — _id_: `portfolio-governance` · _category_: governing-party · _surface_: inherited portfolio-scope specs (pinned `v0.1.11` in `spec/.spec-config.yml`), `portfolio-audit` / `portfolio-inflight-triage` runs · _expects_: conformance to portfolio conventions; declared overrides instead of silent divergence · _track_: `developer-docs` · _status_: `assumed` (inheritance is declared in-repo; drift-check not yet exercised) · _criticality_: peripheral
  - Open questions: none

### Indirect audiences

- **End users of apps built with these skills** — _id_: `app-end-users` · _category_: indirect · _surface_: none toward this repo — they experience the UX/quality standards the specs encode, without ever seeing the plugin · _expects_: fluid, accessible, well-performing apps (motivates the UX-audit and perceived-performance skills) · _track_: `user-docs` (nominal — override rationale: this audience never reads this repository's docs; the entry exists to ground design decisions, not documentation) · _status_: `assumed` · _criticality_: peripheral
  - Open questions: none

## Open questions (cross-cutting)

- When (and with whom) to validate the `assumed` public-consumer entry with a real external representative — currently all external-facing expectations are author inference.
- Whether the bilingual docs convention (en canonical, de translation) is the right cut for public consumers or whether English-only docs would serve them better.

## Revisit triggers

- Plugin gets published to a marketplace or referenced by an external repo (first real public consumers)
- First external contributor PR arrives
- Team adoption (multiple developers using the skills in shared projects)
- Scope extension beyond the five confirmed areas (for example Play-Store release or KMP)
- Spec-inherit pin moves to a new major hub release with changed governance rules
