---
name: android-test-suite-apply
description: "Brings an existing Android app's test suite and CI wiring in line with spec/android/test-automation/: audits the suite against the hygiene rules (JUnit 4, runTest plus MainDispatcherRule, fakes over mocks, no sleeps, injected dispatchers, Robolectric only for Compose UI), records the test strategy, adds the Roborazzi screenshot lane with accessibility checks and the forced-size matrix, and wires one CI workflow running single-variant unit tests plus lint with Gradle caching and JUnit XML artifacts so task check locally equals CI. Operations: audit (read-only, severity-classified), plan (writes project/test-strategy.md), apply (per-item approval, verified by ./gradlew build). Invoke when the user asks to audit, plan, harden, or wire tests, screenshot tests, or test CI. Don't use for scaffolding a new project, a feature's own tests, red-test diagnosis, or performance lanes. Also handles equivalent German-language requests. Supports resume on re-invocation."
tags: [quality-gate, audit, implementation]
phase: quality
summary: "Audits, plans, and applies an existing Android app's test suite and CI wiring per spec/android/test-automation/: hygiene rules, strategy record, Roborazzi lane, single-variant CI."
summary_de: "Prüft, plant und setzt Testsuite und CI-Verdrahtung einer bestehenden Android-App gemäß spec/android/test-automation/ um: Hygieneregeln, Strategie-Datei, Roborazzi-Lane, Ein-Varianten-CI."
use_when:
  - "an existing app's tests should be audited against the test-automation spec"
  - "the project needs a recorded test strategy and pyramid decision"
  - "JVM screenshot tests or accessibility checks should be added to the suite"
  - "CI should run the unit tests and lint the way the spec prescribes"
  - "tests use sleeps, mocks of own code, or hard-coded dispatchers and need hardening"
dont_use_when:
  - situation: "A new Android project should be created with its minimum viable suite"
    alternative: android-project-scaffold
  - situation: "A feature's own ViewModel, repository, or screen tests should be written"
    alternative: android-feature-implement
  - situation: "A Compose screen and its Robolectric content test should be authored"
    alternative: android-compose-ui
  - situation: "A test is red and the cause needs diagnosing"
    alternative: android-debugging
  - situation: "Startup, jank, or benchmark lanes are the question"
    alternative: android-perceived-performance
see_also:
  - android-project-scaffold
  - android-feature-implement
  - android-compose-ui
  - android-debugging
  - android-perceived-performance
  - android-code-reviewer
  - android-toolchain-upgrade
examples:
  - prompt: "Prüfe die Testsuite meiner Android-App gegen die Test-Spec."
    outcome: "audit: severity-classified report per test-automation section, nothing written."
  - prompt: "Add Roborazzi screenshot tests and wire the unit tests into GitHub Actions."
    outcome: "plan then apply: strategy file, screenshot lane, one CI workflow, Taskfile targets, green ./gradlew build and task check."
resumable: true
---

# Android Test Suite Apply

Brings the automated test suite and its CI wiring of an **existing** Android app in line with
`spec/android/test-automation/`. The skill decides the strategy first, records it, and only
then touches infrastructure — every write is approved per item, and the run closes on a green
`./gradlew build` and `task check` (REQ-1, REQ-7).

The governing idea is that a suite is judged as a **pyramid on two independent axes**: scope
(unit, component, feature, application) and execution host (local JVM, instrumented device).
Escalating scope never means escalating host; the JVM carries everything until a documented
device-only behaviour forces an instrumented lane. The authoritative rules live in
`spec/android/test-automation/`; this skill operationalizes them and never restates or
contradicts them. On any conflict the spec wins — report the gap and propose a spec change
rather than deciding silently (REQ-6).

Grounding specs, in the order they bind this skill: `spec/android/test-automation/` §A
(strategy), §B/§C/§D (hygiene of unit, double, and Compose tests), §E (screenshot and
accessibility lane), §F (instrumented boundary), §G/§H (CI wiring and the solo default);
`spec/android/project-structure/` §F/§G (test placement, quality-tooling layout);
`spec/android/screen-formats/` §D (the reference matrix the forced-size tests cover);
`spec/android/release-readiness/` (what "done" means for the touched build).

## Why this is a skill, not an agent

- **Per-item approval is the contract.** Recording a strategy, adding a lane, rewriting a
  sleeping test, and replacing a CI workflow are operator decisions that outlive the run
  (REQ-8); an agent's fire-and-forget shape cannot carry those gates.
- **The persistent artifacts are the deliverable.** The strategy file, test infrastructure,
  workflow, and Taskfile land in the working tree and are reviewed in context, not behind a
  structured-report boundary.
- **It composes with sibling capabilities.** Feature tests belong to
  `android-feature-implement`, screen tests to `android-compose-ui`, a red test to
  `android-debugging`; per `spec/claude/skill-vs-agent/` §Primary decision rule the
  orchestrator is always a skill.
- Counter-dimension considered: the `audit` operation alone — scanning every test source and
  workflow — would suit an agent's context isolation, but its findings feed directly into the
  `plan` decisions and the per-item `apply` gates, so splitting it out would break the
  interaction it exists to serve.

## Boundary vs the sibling capabilities

- `android-project-scaffold` (REQ-12) writes the minimum viable suite of §H into a **new**
  project. This skill never scaffolds; it starts where a project already exists.
- `android-feature-implement` (REQ-19) and `android-compose-ui` (REQ-13) author the tests of
  a feature or screen. This skill owns the **infrastructure** those tests stand on (rules,
  fakes module, lanes, CI) and the strategy that says which tests exist at all.
- `android-debugging` (REQ-16) diagnoses a red test. This skill reports red tests it finds or
  causes and routes them there; it never guesses at a failure.
- `android-perceived-performance` (REQ-15) owns Macro-/Microbenchmark lanes. This skill only
  enforces §F's boundary: no benchmark in the per-commit lane.
- `android-ux-reviewer` (REQ-14) audits UI read-only; the accessibility checks this skill wires
  are a regression net, never a substitute for that audit (§E).

## German trigger phrases

Respond to these (and equivalents) exactly as to their English counterparts; the frontmatter
`description` stays English-only per `skill-management` §Structure:

- "Prüfe / auditiere die Testsuite", "Entsprechen die Tests der Test-Spec?"
- "Lege eine Teststrategie fest", "Welche Testebenen braucht die App?"
- "Füge Screenshot-Tests hinzu", "Richte Roborazzi ein", "Accessibility-Checks in die Tests"
- "Verdrahte die Tests in CI", "GitHub-Actions-Workflow für Unit-Tests und Lint"
- "Entferne die Sleeps / Mocks aus den Tests", "Härte die Testsuite"

## User-language policy

Detect the operator's language and respond in it (German for this operator). Generated
artifacts stay canonical: Kotlin, Gradle, YAML, and identifiers in English; the strategy file
and the audit report are written in English so they stay reviewable alongside the spec corpus.

## Operations

Pick one at the start and say which is running. The split is deliberate: `audit` **only
reports**, `plan` **decides and records**, `apply` **writes**. Nothing is written into the
project before a recorded strategy covers it.

- **`audit`** — the suite and CI exist and their conformance is unknown. Runs the audit
  procedure below and **writes nothing at all**: it produces a severity-classified findings
  report on the canonical `Critical` / `Warning` / `Suggestion` / `Info` scale of
  `spec/claude/review-plan/`. When the operator wants the report on disk, it goes to
  `.audits/android-test-suite/<date>.md`, nowhere else.
- **`plan`** — the strategy is undecided or a change is intended. Runs steps 1–3 and writes
  `project/test-strategy.md` after operator approval. Touches no test, build script, or
  workflow.
- **`apply`** — a recorded strategy exists and infrastructure is to be added or patched. Runs
  steps 4–7. Refuses to start when `project/test-strategy.md` is absent or does not cover the
  item at hand — run `plan` first.

An end-to-end request ("get the tests in shape") is `audit`, `plan`, `apply` back-to-back in
one invocation; say when each handover happens so the operator sees the report and the
strategy before anything is written.

## Preconditions

Before deciding anything:

- Confirm the working directory is a git repository holding an Android project with a Gradle
  application module. Without one, stop and route to `android-project-scaffold`.
- Read `references/suite-hygiene-rules.md` in full — it is the rule set of §B/§C/§D/§F
  distilled into detectable findings with their severities, and every audit finding cites it.
- Establish the module graph, the DI mechanism, the product flavors and the resulting debug
  variant name (`testDebugUnitTest` versus `test<Flavor>DebugUnitTest`), and whether a
  `Taskfile.yml` and a CI workflow already exist. Nearly every §G rule is variant-aware.
- Read `project/test-strategy.md` where it exists; a recorded deferral is a decision, not a
  finding, and is never re-asked.
- Check for uncommitted changes in test sources, build scripts, `.github/`, and `Taskfile.yml`.
  If dirty, report and ask whether to stash, commit, or abort — never overwrite unconfirmed
  work (REQ-8).

## Audit procedure (operation `audit`)

Read-only throughout. Nothing is written — not a test, not a build script, not a workflow.

1. **Enumerate the surface.** Every `src/test/` and `src/androidTest/` source set per module,
   the test dependencies in the version catalog, `testOptions` blocks, existing goldens, the
   CI workflows under `.github/workflows/`, and the Taskfile targets.
2. **Walk the hygiene rules.** Apply every detection heuristic in
   `references/suite-hygiene-rules.md` to the enumerated sources: runner, `runTest` and
   `MainDispatcherRule`, hard-coded dispatchers in production code, sleeps and wall-clock
   waits, mocks of project-owned interfaces, Robolectric on plain unit tests, tests on
   activities or services, single assertion library, semantics-first Compose matching,
   `testTag` on containers only.
3. **Judge the pyramid.** Map what exists onto §A: which layers have tests, which ViewModels
   and repositories have none, whether critical screen interactions and the common journeys
   are covered, and whether any instrumented test lacks a documented device-only reason (§F).
4. **Check the lanes.** Screenshot lane present or not; goldens committed per module and
   recorded on one platform only; `verifyRoborazzi…` on every PR; ATF checks with justified
   suppressions (§E). Then the CI contract of §G/§H: exactly one debug variant's unit tests
   plus lint per PR through the Taskfile entry points, Gradle caching, JUnit XML uploaded with
   `if: !cancelled()`, KVM enabled on any emulator job, no benchmark task and no device
   matrix or retry machinery unless the strategy file records them.
5. **Report** on the canonical scale: `Critical` for a breached MUST or MUST NOT, `Warning` for
   a breached SHOULD, `Suggestion` for a MAY worth adopting or a SHOULD the strategy file
   explicitly defers, `Info` for a surface scanned clean. Each finding carries the file and
   line, the spec section, and the operation that would fix it. Where a finding rests on a
   choice no spec settles, report the gap with a proposed extension (REQ-6).

## Procedure (operations `plan` and `apply`)

Run the steps in order. Confirm with the operator at each gate before writing.

### 1. State the strategy question in one sentence

Restate what the operator wants the suite to guarantee — "a merge is blocked when a ViewModel
regresses or a screen's rendering drifts" is answerable; "better tests" is not. Where an
`audit` report from this or a previous run exists, work from it. Gate: confirm the restatement.

### 2. Decide the pyramid and the tool set

Walk `references/test-strategy-template.md` §Decisions with the operator: which layers exist
per §A, what gates a merge, and one choice each for runner (JUnit 4), coroutine testing
(`kotlinx-coroutines-test`), assertion library (`kotlin.test` by default; an existing single
library stays), test doubles (fakes, mocking only at true system boundaries), screenshot tool
(Roborazzi by default; an existing Paparazzi setup in a pure design-system module stays),
coverage (Kover, gate deferred by default), and the CI lanes. Every §H addition beyond the solo
default — instrumented suite, emulator matrix, coverage gate, E2E lane — is admitted only with
a named trigger and is otherwise recorded as deferred. Gate: confirm each decision.

### 3. Record the strategy

Write `project/test-strategy.md` from `references/test-strategy-template.md`. The location is
fixed by `spec/android/test-automation/` §A. When a file exists, append to its change log and
update the affected sections — never rewrite the history (REQ-8). Gate: confirm the write.
`plan` ends here.

### 4. Build the apply plan

Precondition, not a formality: the strategy file covers every item about to be written. Derive
the item list from the audit findings and the strategy: build-script changes (`testOptions`,
catalog entries), shared test infrastructure (`MainDispatcherRule`, fake skeletons, a
`:core:testing` module once modularized per `spec/android/project-structure/` §F), Compose test
hosting on Robolectric, the forced-size matrix helper, the Roborazzi lane with ATF checks,
hygiene fixes in existing tests, the CI workflow, and the Taskfile targets. Present the list
with the files each item touches. Gate: confirm the list; the operator may drop items.

### 5. Apply infrastructure and lanes

Per item, from `references/test-infrastructure-templates.md`: add or patch the file, resolve
concrete versions at apply time into the version catalog ("mechanisms, not versions" — never
a hard-coded or dynamic version), and confirm before every write that touches an existing file
(REQ-8). Existing tests are patched only for the hygiene finding named in the plan — a sleep
replaced by virtual time, a mock of an own repository replaced by a fake — and never rewritten
wholesale. Goldens are **not** recorded on the workstation: the first record run happens in CI
per §E; locally the lane is wired and compiles. Checkpoint after each item.

### 6. Wire CI and the Taskfile

From `references/ci-and-taskfile-templates.md`: exactly one workflow that runs the project's
Taskfile targets (`task --yes check`), single-variant unit tests plus lint, Gradle caching,
JUnit XML and lint reports uploaded with `if: !cancelled()`, screenshot verification with the
comparison images as artifacts once the lane exists. Taskfile targets follow the portfolio
vocabulary (`lint`, `test`, `check`) so `task check` locally is what CI runs. No device
matrix, retry step, or benchmark job appears unless the strategy file records it. An existing
workflow is merged into, not replaced, and every hunk is confirmed. Checkpoint after the write.

### 7. Verify, and hand off

- Run `./gradlew build`, then `task check`. Both must be green; report every failure with its
  output and route a red test to `android-debugging` rather than guessing (REQ-7).
- Re-run the audit heuristics over the touched surface and confirm no `Critical` remains.
- Report, in the operator's language: the strategy decisions, every item applied or dropped,
  the verification results, the goldens the first CI run will record, every hygiene fix made
  to an existing test, and any spec gap found. Never leave a red, skipped, or unrunnable
  element unreported (REQ-1, REQ-7).

## Reference files

- Read `references/suite-hygiene-rules.md` before the audit and before step 4 — the
  detectable findings of §B/§C/§D/§F, each with its heuristic, severity, and fix.
- Read `references/test-strategy-template.md` in steps 2 and 3 — the decision list and the
  file layout of `project/test-strategy.md`.
- Read `references/test-infrastructure-templates.md` in step 5 — `MainDispatcherRule`, fake
  and ViewModel-test skeletons, Robolectric hosting, the forced-size matrix, and the Roborazzi
  lane with ATF checks.
- Read `references/ci-and-taskfile-templates.md` in step 6 — the workflow, the Taskfile
  targets, and the artifact and caching wiring.

## Resumability

Per `spec/claude/resumable-work/`, this skill is `resumable: true`. State is persisted to
`.resume/android-test-suite-apply/<run-id>.yml` after every gate and at each named step
boundary. On re-invocation, scan `.resume/android-test-suite-apply/*.yml` for files with
`status: in_progress` whose `inputs:` snapshot (repository + operation + module set) matches
the current request; when one matches, prompt
`Resume run <run_id> from phase <phase> (last checkpoint <last_checkpoint_at>)? [resume / start-new / discard]`.
`resume` re-hydrates and re-asks no answered gate; `start-new` leaves the old file intact;
`discard` deletes it. Fail closed on unparseable or higher-`schema_version` files. The envelope
keys and lifecycle are load-bearing in the spec and are not duplicated here.

## Hard rules

- **Never** write a test, build script, workflow, or Taskfile change in `audit`, and never
  write infrastructure in `apply` that `project/test-strategy.md` does not cover.
- **Never** generate a device-matrix job, retry machinery, coverage gate, or benchmark lane
  without a trigger recorded in the strategy file (§H); never let a benchmark task into the
  per-commit lane (§F).
- **Never** run the all-variant `test` aggregate in CI; exactly one debug variant's unit tests
  plus lint, through the same Taskfile targets used locally (§G).
- **Never** record screenshot goldens on the workstation; the record run happens on CI/Linux
  and goldens are committed per module (§E).
- **Never** introduce a sleep, a wall-clock wait, a mock of a project-owned interface, a
  Robolectric runner on a plain unit test, or a unit test on an activity or service — and never
  leave one found in place unreported (§B/§C).
- **Never** rewrite an existing test wholesale, overwrite an existing workflow, or change a
  test's assertion library without per-file confirmation (REQ-8).
- **Never** pin a version the spec did not ask for, and never a dynamic one; resolve current
  stable versions at apply time (REQ-5) and record them only in the version catalog.
- **Never** scaffold a new project or its minimum viable suite; route to
  `android-project-scaffold`. Never write a feature's own tests; route to
  `android-feature-implement` or `android-compose-ui`.
- **Always** report a strategy or tooling choice no spec settles — Turbine, coverage
  thresholds, Maestro — as a gap with a proposed extension instead of deciding silently
  (REQ-6). JUnit 5 is *not* such a gap: §B settles it as a MAY on both hosts; record the
  project's choice in the strategy file.
- **Always** close `apply` on green `./gradlew build` and `task check`, and route a red test to
  `android-debugging` (REQ-7).
- When `spec/android/test-automation/` disagrees with this skill, the spec wins.

## Gotchas

Read `references/suite-hygiene-rules.md` §Gotchas for the full set. The three that most often
produce a wrong result:

- **`runTest` does not make `Dispatchers.Main` available.** A ViewModel touching `Main`
  without a `MainDispatcherRule` fails with "Module with the Main dispatcher had failed to
  initialize"; the rule, not `Dispatchers.setMain` scattered per test, is the fix.
- **A `stateIn(WhileSubscribed)` flow is not evaluated without a collector.** Asserting on
  `.value` before a collector runs reads the initial value and passes for the wrong reason;
  start a `backgroundScope` collector first.
- **The Roborazzi verify task compares against goldens rendered on one OS.** A golden set
  recorded on macOS fails on Linux CI on font antialiasing alone; the first record run belongs
  to CI, and `compareRoborazzi…` output is the artifact to read on a diff.
