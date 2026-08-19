# Test strategy record

The decision list walked in SKILL.md step 2 and the file layout written in step 3 to
`project/test-strategy.md`, per `spec/android/test-automation/` §A ("record the project's
concrete test strategy") and §H ("each addition is recorded as a deliberate strategy change,
not accreted silently"). The file is written in English, lives in the project repository, and
is the precondition every `apply` item is checked against.

## Table of contents

- [1. Decisions](#1-decisions)
- [2. File layout](#2-file-layout)
- [3. Editing an existing file](#3-editing-an-existing-file)

## 1. Decisions

Confirm each with the operator; a decision that has no answer stays open in the file rather
than being invented (REQ-6).

1. **Guarantee** — one sentence: what a green merge gate proves.
2. **Layers present** (§A pyramid, scope × host): for each of unit, component, feature UI,
   whole-app journey, instrumented, end-to-end — present / planned / deferred, with the host
   (JVM, Robolectric, device) and the tool.
3. **Runner** — JUnit 4 (§B MUST). JUnit 5 is a §B MAY on both hosts (local JVM via
   `useJUnitPlatform()`, instrumented via the community `android-junit5` plugin); record the choice.
4. **Coroutines** — `kotlinx-coroutines-test`, `runTest`, `MainDispatcherRule`, injected
   dispatchers (§B MUST). Turbine: adopted or not (§B MAY; open question in the spec).
5. **Assertion library** — `kotlin.test` by default; an existing single library stays. Mixed
   usage names the survivor and the migration path (§B SHOULD).
6. **Test doubles** — fakes; mocking library permitted only at the named system boundaries
   (§C). Where shared fakes live (`:core:testing` once modularized, project-structure §F).
7. **Compose hosting** — Robolectric in `src/test` with `isIncludeAndroidResources`; the
   documented device-only cases that escalate to `src/androidTest` (§D/§F).
8. **Configuration matrix** — which screens run the forced-size reference matrix
   (screen-formats §D), font scale, locales, dark mode (§D SHOULD).
9. **Screenshot lane** — Roborazzi (default), Paparazzi (design-system module only), or
   deferred; record platform (CI/Linux), golden placement per module, verify on every PR (§E).
10. **Accessibility checks** — `enableAccessibilityChecks()` in Compose tests and/or the ATF
    hook in the screenshot helper; the suppression policy (named and justified in code) (§E).
11. **CI lanes** — per-PR: `<variant>` unit tests + lint via `task check`, XML artifacts,
    Gradle caching; screenshot verify once the lane exists; scheduled lanes: none by default;
    KVM rule only when an emulator job exists (§G).
12. **Coverage** — Kover measurement yes/no; gate deferred by default with the trigger that
    would introduce one (§G SHOULD/MAY).
13. **Deferred additions** (§H) — instrumented suite, emulator matrix, retries, coverage gate,
    E2E/Maestro, benchmark lane (owned by `android-perceived-performance`): each with the
    trigger that would justify it.
14. **Open spec questions touching this project** — assertion library, screenshot tool,
    Turbine, coverage thresholds, Maestro — and the interim choice taken.

## 2. File layout

```markdown
# Test strategy

Status: active · Last change: <YYYY-MM-DD> · Governing spec: spec/android/test-automation/

## Guarantee

<one sentence>

## Layers

| Layer | Host | Tool | Status | Gates merge |
|---|---|---|---|---|
| Unit (ViewModel, repository, use case) | JVM | JUnit 4 + kotlinx-coroutines-test | present | yes |
| Feature UI (content composables) | Robolectric | Compose test rule | present | yes |
| Screenshot | Robolectric | Roborazzi + ATF | planned | yes, once goldens exist |
| Whole-app journey | Robolectric | Compose test rule, real navigation | planned | yes |
| Instrumented | device | AndroidX Test | deferred | — |
| End-to-end | device | — | deferred | — |

## Tool decisions

- Runner: JUnit 4
- Coroutines: runTest, MainDispatcherRule, injected dispatchers and clock; Turbine: no
- Assertions: kotlin.test
- Doubles: fakes; mocking permitted only at: <boundaries or "none">
- Shared fakes: <module>
- Compose hosting: Robolectric, isIncludeAndroidResources = true; device-only cases: <list or "none">
- Configuration matrix: <screens>; sizes 841×701, 1024×640, 1280×800, 1600×900 dp; font scale 2.0; locales en, de
- Screenshot tool: Roborazzi; goldens per module under src/test/screenshots/; recorded on CI/Linux only
- Accessibility checks: enableAccessibilityChecks(); suppressions justified inline
- Coverage: Kover report, no gate

## CI lanes

- Per PR: `task --yes check` → `<variant>` unit tests + lint (+ verifyRoborazzi<Variant> once goldens exist); JUnit XML, lint, and roborazzi outputs uploaded `if: !cancelled()`; Gradle caching
- Scheduled: none

## Deferred additions

| Addition | Trigger that would justify it |
|---|---|
| Instrumented suite | <documented device-only behavior> |
| Emulator matrix | <first PR-blocking instrumented test> |
| Coverage gate | <team size / defect trend> |
| E2E / Maestro | <device-real journey with recurring regressions> |
| Benchmark lane | owned by android-perceived-performance; never per-commit |

## Open questions

- <spec open question> — interim choice: <choice>, reason: <reason>

## Change log

| Date | Change | Reason | Run |
|---|---|---|---|
| <YYYY-MM-DD> | initial strategy | <reason> | <run_id> |
```

## 3. Editing an existing file

- Append a change-log row for every `plan` run that changes a decision; never delete rows.
- Update only the sections the new decisions touch; leave the rest verbatim.
- A "deferred" entry that gains a trigger moves to Layers or CI lanes and keeps its history in
  the change log.
- Confirm the diff with the operator before writing (REQ-8).
