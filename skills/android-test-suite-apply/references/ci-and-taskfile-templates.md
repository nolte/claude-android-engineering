# CI and Taskfile templates

The wiring the `apply` operation writes in SKILL.md step 6, per `spec/android/test-automation/`
§G/§H: exactly one workflow, one debug variant's unit tests plus lint, Gradle caching, JUnit
XML artifacts, and local↔CI parity through the Taskfile targets of `spec/project/taskfile/`.
Action references are shown by major tag; pin them the way the project's CI conventions
require (SHA pins where the portfolio's GitHub-Actions spec asks for them) and resolve current
versions at apply time (REQ-5). An existing workflow is merged hunk by hunk with confirmation,
never replaced (REQ-8).

This file is the **canonical** Taskfile/CI template; `android-project-scaffold`'s
`references/scaffold-blueprint.md` §12 keeps only a summary and points here — change the
templates in this file, not there.

## Table of contents

- [1. Taskfile targets](#1-taskfile-targets)
- [2. The single CI workflow](#2-the-single-ci-workflow)
- [3. Screenshot record and verify](#3-screenshot-record-and-verify)
- [4. What is deliberately absent](#4-what-is-deliberately-absent)
- [5. Verification checklist](#5-verification-checklist)

## 1. Taskfile targets

Canonical names from `spec/project/taskfile/`; `<Variant>` is the single debug variant
established in the preconditions (`Debug`, or `<Flavor>Debug` with product flavors — never the
aggregate `test`).

```yaml
version: "3"

vars:
  VARIANT: Debug          # the one debug variant CI and local runs share

tasks:
  setup:
    desc: One-command onboarding (git hooks, wrapper check)
    cmds:
      - ./gradlew --version

  lint:
    desc: Android Lint plus the formatting check
    cmds:
      - ./gradlew lint{{.VARIANT}} spotlessCheck

  test:
    desc: JVM unit tests of the single debug variant
    cmds:
      - ./gradlew test{{.VARIANT}}UnitTest

  test:screenshot:verify:
    desc: Compare screenshots against the committed goldens (CI-recorded)
    cmds:
      - ./gradlew verifyRoborazzi{{.VARIANT}}

  test:screenshot:record:
    desc: Record goldens — run on CI/Linux only; workstation renders drift
    cmds:
      - ./gradlew recordRoborazzi{{.VARIANT}}

  check:
    desc: Aggregate quality gate — what CI runs
    # Serial cmds, not deps: go-task runs deps in parallel, and two concurrent
    # ./gradlew invocations serialize on the Gradle project lock and spawn a
    # second daemon JVM.
    cmds:
      - task: lint
      - task: test

  build:
    desc: Full build, the REQ-1 success criterion
    cmds:
      - ./gradlew build
```

Once goldens are committed, `check` gains `- task: test:screenshot:verify` as a third serial
command (same Gradle-lock rationale — never a parallel dep). `spotlessCheck`
is present only when the project applies Spotless (project-structure §G SHOULD); drop it from
`lint` otherwise rather than adding the plugin here — quality tooling is its own decision.
Existing targets are extended, not renamed.

## 2. The single CI workflow

`.github/workflows/ci.yml` — one workflow, one job for the per-PR gate. It calls the Taskfile
targets so the local gate and the CI gate cannot drift (taskfile spec §CI parity).

```yaml
name: ci

on:
  pull_request:
  push:
    branches: [develop]

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read       # least privilege; add `checks: write` only together with the
                       # optional JUnit-annotation step below

jobs:
  check:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4

      - uses: gradle/actions/wrapper-validation@v4   # verify gradle-wrapper.jar checksum before any Gradle call

      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: "17"          # match the project's toolchain

      - uses: gradle/actions/setup-gradle@v4   # Gradle caching + build scans off
        with:
          cache-read-only: ${{ github.ref != 'refs/heads/develop' }}

      - uses: arduino/setup-task@v2
        with:
          version: 3.x

      - name: Quality gate (same target as local)
        run: task --yes check

      # Concrete paths when the variant is fixed (the scaffold's single-module
      # `Debug` shown here); multi-module or renamed-variant projects use the
      # glob fallback "**/build/test-results/test*UnitTest/TEST-*.xml".
      - name: Upload JUnit XML
        if: ${{ !cancelled() }}
        uses: actions/upload-artifact@v4
        with:
          name: junit-xml
          path: app/build/test-results/testDebugUnitTest/TEST-*.xml
          if-no-files-found: warn

      # Glob fallback: "**/build/reports/lint-results-*.{xml,html}"
      - name: Upload lint reports
        if: ${{ !cancelled() }}
        uses: actions/upload-artifact@v4
        with:
          name: lint-reports
          path: |
            app/build/reports/lint-results-debug.xml
            app/build/reports/lint-results-debug.html
          if-no-files-found: ignore

      # OPTIONAL — SHOULD (§G): surface results as PR annotations. This step is
      # the sole reason to widen permissions: include it only together with
      # `checks: write`; omit both when annotations are not wanted.
      - name: JUnit annotations
        if: ${{ !cancelled() }}
        uses: mikepenz/action-junit-report@v5
        with:
          report_paths: app/build/test-results/testDebugUnitTest/TEST-*.xml
```

Notes:

- `cache-read-only` on non-default branches keeps the cache from churning per PR; the
  `develop` push writes it. Adjust the branch name to the project's integration branch.
- The Gradle invocation must be the variant-aware task; `task check` carries it, so the
  workflow never names a Gradle task directly.
- Configuration cache and build cache are `gradle.properties` decisions from
  `spec/android/project-structure/` §B; the workflow assumes they are on and adds nothing.
- Java version and distribution match the project's toolchain declaration; do not introduce
  a second one here.

## 3. Screenshot record and verify

§E: goldens are recorded on CI/Linux only and verified on every PR once they exist.

Verify (added to the `check` job once goldens are committed — via `task check`, no extra
step) plus the comparison artifact:

```yaml
      - name: Upload screenshot comparisons
        if: ${{ !cancelled() }}
        uses: actions/upload-artifact@v4
        with:
          name: roborazzi-compare
          path: "**/build/outputs/roborazzi/"
          if-no-files-found: ignore
```

Record — a manually dispatched workflow, or a job that runs when a PR carries the label
`record-screenshots`; it records and commits goldens on same-repo branches (the auto-record
commit bot is a §E MAY, offered, not forced):

```yaml
name: record-screenshots
on:
  workflow_dispatch:
jobs:
  record:
    runs-on: ubuntu-latest
    permissions: { contents: write }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with: { distribution: temurin, java-version: "17" }
      - uses: gradle/actions/setup-gradle@v4
      - uses: arduino/setup-task@v2
        with: { version: 3.x }
      - run: task --yes test:screenshot:record
      - name: Commit goldens
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add "**/src/test/screenshots/*.png"
          git diff --cached --quiet || git commit -m "test: record screenshot goldens on CI"
          git push
```

The first record run is the operator's action after `apply` — the skill wires it and reports
that the goldens are pending; it never records them on the workstation.

## 4. What is deliberately absent

§H MUST NOT for a solo project, and §F/§G boundaries — each appears only when
`project/test-strategy.md` records its trigger:

- **Emulator / device-matrix jobs** (`reactivecircus/android-emulator-runner`, Gradle Managed
  Devices, API-level `matrix`). When one is admitted: the KVM udev rule step first
  (`echo 'KERNEL=="kvm", GROUP="kvm", MODE="0666", OPTIONS+="static_node=kvm"' | sudo tee
  /etc/udev/rules.d/99-kvm4all.rules && sudo udevadm control --reload-rules && sudo udevadm
  trigger --name-match=kvm`), disabled animations, AVD snapshot caching, a small API matrix,
  Test Orchestrator with `clearPackageData` (§G/§F).
- **Retry machinery** (`nick-fields/retry`, Gradle test-retry plugin, `@FlakyTest` runners) —
  a bridge for big/instrumented tests only, never for `src/test`, and always with a tracked
  flake record (§F).
- **Benchmark lanes** — Macro-/Microbenchmark are a scheduled lane owned by
  `android-perceived-performance`; never in this workflow (§F).
- **Coverage gates** — Kover measurement (`koverXmlReport`) may run and upload; a threshold
  gate is a §G MAY whose wiring is reviewed when introduced.
- **The all-variant `test` task**, `./gradlew build` as the PR gate (it assembles every
  variant and multiplies wall-clock), and any second workflow doing the same job.

## 5. Verification checklist

After writing, before reporting (SKILL.md step 7):

- `task check` passes locally and its Gradle tasks are `test<Variant>UnitTest` and
  `lint<Variant>` (plus `verifyRoborazzi<Variant>` once goldens exist).
- `./gradlew build` is green (REQ-1).
- The workflow calls `task --yes check` and nothing Gradle-specific inline; XML and lint
  artifacts upload `if: !cancelled()`.
- No matrix, retry, benchmark, or emulator step exists without a strategy-file trigger; when
  an emulator step exists, the KVM rule precedes it.
- Existing workflows were merged, not replaced; the operator confirmed every hunk.
- The report names the goldens still to be recorded and the workflow that records them.
