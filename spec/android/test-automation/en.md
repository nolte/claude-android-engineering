# Android Test Automation

Status: draft

## Context

This repository's skills generate, extend, audit, and debug Android apps; every skill run must leave a project that builds green (`project/requirements/android-engineering-skills.md`, REQ-1). That guarantee is only as strong as the project's automated test suite. This spec is the authoritative definition of how automated tests in an Android app project are structured, which frameworks carry them, and how they run in CI — the foundation the test-related skills (project setup, Compose UI, debugging) generate against and audit against.

The content is distilled from a research pass (August 2026) over three source classes: official Google testing guidance (developer.android.com/training/testing, Compose testing, coroutines/Hilt testing, Gradle Managed Devices), the tools' own documentation (Roborazzi, Paparazzi, Compose Preview Screenshot Testing, kotlinx-coroutines-test, Turbine, Kover), and reference projects inspected live (Now in Android as the flagship, DuckDuckGo Android, Signal Android, Tivi, compose-samples). Where Google's guidance and production practice diverge (mocking, Turbine adoption), the spec records the divergence instead of hiding it.

Boundary to the sibling spec: `spec/android/project-structure/` §F owns test *placement* (tests live in the module under test, `src/test/` vs `src/androidTest/`, shared fixtures in `:core:testing`, consistent naming). This spec owns test *strategy, frameworks, and automation* and references placement rules instead of restating them. Performance benchmarks (Macrobenchmark/Microbenchmark) are out of scope except for their boundary to the functional suite; they belong to `spec/android/perceived-performance/`.

Readers: authors of this repo's Android skills and reviewers judging whether a generated or audited project's test suite is conformant.

## Goals

- Define a test strategy that catches defects at the cheapest layer: many fast JVM tests, few instrumented tests, deliberate escalation only when fidelity demands it
- Fix the framework stack per test kind (unit, Compose UI, screenshot, instrumented, end-to-end) so generated projects are consistent and auditable
- Make suites deterministic by construction — no sleeps, no unmanaged flakiness, virtual time and synchronization APIs instead
- Define the CI wiring (tasks, caching, artifacts, coverage, flake handling) so a local pass predicts a CI pass
- Scale honestly: name the minimum viable suite for a solo-developer app and the additive path for larger projects

## Non-Goals

- Test placement, naming schemes, and fixture-module layout — owned by `spec/android/project-structure/` §F and §C
- Performance benchmarking (Macrobenchmark/Microbenchmark, Baseline Profiles) — only the boundary is drawn here; the practice belongs to `spec/android/perceived-performance/` §F/§G
- Play-Store pre-launch reports and release-track device farms — release is out of scope for this repository
- CI pipeline architecture beyond the test jobs — owned by the portfolio CI/CD specs
- Prescribing exact tool versions — mechanisms and tool choices are fixed; versions live in the project's version catalog

## Requirements

### A. Test strategy

- **MUST** distribute tests as a pyramid: numerous small JVM tests at the base, few large end-to-end tests at the tip; for every new test, use the lowest layer that gives adequate feedback
- **MUST** treat *scope* (unit → component → feature → application) and *execution host* (local JVM vs instrumented device) as independent dimensions — a feature-level UI test may still run on the JVM (Robolectric), and escalating scope never automatically means escalating to a device
- **MUST** unit-test, at minimum: ViewModels (state production for normal *and* edge cases — errors, empty data, corrupt input), repositories and data-layer logic, use cases, and non-trivial utility code
- **MUST NOT** unit-test framework entry points (activities, services) or framework/library behavior itself; logic that would require it is moved out of the entry point instead
- **MUST** cover each screen's critical user interactions with a UI test against the stateless content composable, and the most common navigation paths with a small number of journey tests
- **SHOULD** record the project's concrete test strategy (which layers exist, what gates a merge) in a short document or the project's CLAUDE.md, per Google's strategy guidance
- **SHOULD** keep architecture testable by construction: no business logic in framework entry points, no `Context` in ViewModels, all dependencies injected behind interfaces — the architecture rules in `spec/android/project-structure/` §E are the enabler and are not restated here

### B. Local unit tests (JVM)

- **MUST** write tests as JUnit 4 test classes — the runner path Google's guidance and AndroidX Test document [R5]. JUnit 5 is a **MAY**, and the mechanics differ by host: *local JVM* unit tests need no third-party plugin — AGP's local unit-test tasks are Gradle `Test` tasks (`testOptions.unitTests.all { it.useJUnitPlatform() }`) [R27][R28]; *instrumented* tests on JUnit 5 need the community `android-junit5` plugin plus its runner support, and the device floor it documents (Android 8.0/API 26 for JUnit 5, API 35 for JUnit 6) [R29]. Generated code **MUST NOT** assume JUnit 5 in either host
- **MUST** use `kotlinx-coroutines-test`: every coroutine test body runs in `runTest`, with exactly one `TestScheduler` shared by all `TestDispatcher`s in a test
- **MUST** replace the Main dispatcher in ViewModel tests via a `MainDispatcherRule` (TestWatcher wrapping `Dispatchers.setMain`/`resetMain`); **MUST** inject dispatchers into production classes instead of hard-coding `Dispatchers.IO`/`Default`
- **MUST NOT** call `Thread.sleep` or wait wall-clock time in any test; virtual time (`advanceUntilIdle`, `advanceTimeBy`) and synchronization APIs are the only waiting mechanisms
- **SHOULD** assert on `StateFlow.value` for state-holder tests (treating StateFlow as a data holder); when a `stateIn(WhileSubscribed)` flow is under test, a collector must be active before asserting
- **MAY** use Turbine for emission-ordering and hot-flow tests; it is convenience, not baseline — reference projects mostly assert via `first()`/`value`
- **MUST NOT** use Robolectric for plain unit tests — it is a last resort for legacy code or Android-class dependencies; its sanctioned roles are UI-behavior tests and screenshots (§D, §E)
- **SHOULD** pick exactly one assertion library and use it consistently repo-wide; `kotlin.test` is the default for Kotlin-first projects (current flagship-sample practice), `assertk` or Truth are acceptable alternatives

### C. Test doubles

- **MUST** prefer fakes over mocks: hand-written test implementations behind the same interface, with test-only hooks (for example a fake repository backed by a `MutableSharedFlow(replay = 1)` plus an imperative `send…` method)
- **MUST NOT** mock the project's own business logic, data classes, or repositories; **MAY** use a mocking library (MockK/Mockito) at true system boundaries where interaction verification is the point — production apps demonstrably do, and the spec permits it there only
- **MUST NOT** build deep mock graphs ("complex mocks") or spies; a dependency that is hard to fake indicates a seam problem to fix in the design
- **MUST** construct ViewModels directly with fakes in unit tests (manual constructor injection); Hilt is not used in unit tests
- **MUST**, in Hilt-based integration/UI tests, use `@HiltAndroidTest` + `HiltAndroidRule(order = 0)` with a Hilt test runner, and replace bindings via `@TestInstallIn` (default), `@UninstallModules`, or `@BindValue` per replacement scope
- Placement of shared fakes, rules, and test data in a `:core:testing`-style module is governed by `spec/android/project-structure/` §F

### D. Compose UI tests

- **MUST** test screen UI against the stateless content composable with fake `uiState` values and no-op event lambdas — every UI state (loading, populated, error) is constructible without a ViewModel; the route/content split from `spec/android/project-structure/` §E is the enabler
- **MUST** match nodes primarily via semantics (text through resource lookup, content descriptions, roles/states); `testTag` is a last resort for containers with no inherent semantics — semantic matching keeps the app accessible and the test locale-safe
- **MUST** rely on Compose's test synchronization: auto-sync by default, `mainClock` control for animations, `waitUntil`/`waitUntilExactlyOneExists` for external work — never sleeps, and Idling Resources only in small interop tests
- **SHOULD** host feature-level Compose tests on Robolectric (`src/test/`, `isIncludeAndroidResources = true`) — officially supported for Compose, fast, and CI-cheap; known limits (no real screen, no WebView, no system UI, reduced rendering fidelity) escalate those specific cases to instrumented tests
- **SHOULD** keep a small number of whole-app integration tests (real Activity, Hilt, real navigation) in the `:app` module; feature modules stay at the `ComponentActivity`/fake-state level
- **SHOULD**, in Hilt projects, provide an `@AndroidEntryPoint ComponentActivity` in a tiny dedicated test-manifest module (the `ui-test-hilt-manifest` pattern) so Compose tests can host Hilt-injected content
- **SHOULD** verify `rememberSaveable` state restoration with `StateRestorationTester`; **MAY** cover activity recreation via `ActivityScenario.recreate()` and full process death via UI Automator where the risk warrants it
- **SHOULD** use `DeviceConfigurationOverride` (forced size, dark mode, font scale, locales) to test configuration variants without devices
- **MUST**, when testing Navigation 3 screens, treat the back stack as plain state: build a test `NavDisplay` with the feature's `entryProvider` and assert on the back-stack contents; navigation callbacks stay injected lambdas, never a passed-around controller

### E. Screenshot and accessibility tests

- **SHOULD** run screenshot tests on the JVM (no devices): the default tool for a Robolectric-based stack is Roborazzi (`@GraphicsMode(NATIVE)`, record/verify/compare Gradle tasks); Paparazzi is a **MAY** for pure design-system modules with no runtime needs; Google's Compose Preview Screenshot Testing is a **MAY** while it remains alpha (`com.android.compose.screenshot` 0.0.1-alpha15 at research time — its full IDE integration needs AGP ≥ 9.0 and Kotlin ≥ 2.2.10, the Gradle tasks alone AGP ≥ 8.5.0; APIs may still change substantially) [R21]
- **MUST** record goldens on exactly one platform (CI/Linux) — text rendering differs across OSes; a workstation-recorded golden set is drift by construction. Goldens are committed per module (placement per `spec/android/project-structure/` §F)
- **MUST** verify screenshots in CI on every PR once screenshot tests exist; comparison images are uploaded as build artifacts; an auto-record commit bot for same-repo PRs is a **MAY**
- **SHOULD** integrate Accessibility Test Framework checks into the suite: `enableAccessibilityChecks()`/`tryPerformAccessibilityChecks()` in Compose tests (Compose ≥ 1.8) or ATF hooks in the screenshot helper, with named, justified suppressions only
- **MUST NOT** treat automated accessibility checks as a replacement for manual TalkBack/Accessibility-Scanner passes; the automation is a regression net, not an audit

### F. Instrumented and end-to-end tests

- **MUST** reserve instrumented tests for behavior that genuinely requires a device or emulator (system UI, WebView, hardware rendering, real process death, release-build verification); everything else runs on the JVM first
- **MUST** run instrumented suites through AndroidX Test with `AndroidJUnitRunner` (or the project's Hilt runner); **SHOULD** enable the Android Test Orchestrator with `clearPackageData` so each test runs in its own invocation with clean state
- **SHOULD** use UI Automator (2.4+ API) for cross-app and system-surface interactions and for release-build (minified) verification; it is not a replacement for in-process Compose tests
- **MAY** add a handful of Maestro smoke journeys for device-real flows — additive convenience outside the Gradle/JUnit ecosystem (no test doubles, no Hilt), never the primary UI-test layer
- **MUST** fix flaky tests instead of institutionalizing retries: retries are a **SHOULD** for big/instrumented tests as a productivity bridge and a **MUST NOT** as a permanent substitute for a fix; flake tracking follows the portfolio workflow-health conventions
- **MUST** draw the performance boundary: Macrobenchmark/Microbenchmark runs are a separate, scheduled (nightly) lane on physical devices — never part of the per-commit functional suite

### G. CI automation

- **MUST** run, on every PR: the unit tests of exactly one debug variant (variant-aware task, for example `testDebug` — never the all-variant `test` aggregate) plus lint; the invocation goes through the same Taskfile/Gradle entry points used locally
- **MUST** upload JUnit XML results as build artifacts (`if: !cancelled()`); **SHOULD** surface them as PR annotations via a report action
- **MUST**, for emulator jobs on GitHub-hosted Linux runners, enable KVM (the documented udev rule) — hardware acceleration is available since 2024 and unaccelerated emulators are a flake source
- **SHOULD** run PR-blocking instrumented tests (when they exist) via the emulator-runner action with a small API-level matrix, disabled animations, and AVD snapshot caching; Gradle Managed Devices are a **MAY** — preferred for reproducible API matrices and scheduled lanes, second choice for PR-blocking jobs given CI stability reports; ATD images speed suites up but cannot host hardware-rendering screenshot tests
- **SHOULD** shard large instrumented suites (runner sharding, GMD shards, or a device farm's smart sharding) instead of letting one job's wall-clock grow unbounded
- **SHOULD** measure coverage with Kover for Kotlin multi-module JVM suites (aggregation built in); Jacoco remains the fallback whenever instrumented coverage must be merged; coverage *gates* are a **MAY** and, when present, the gate wiring itself is reviewed — a reference project currently ships a dead gate behind a stale matrix condition, proving gates rot like code
- **MUST** keep every test task green-by-default in the generated project: a freshly scaffolded project's `task check` passes locally and in CI on the first run (REQ-1, REQ-7)

### H. Scaling: solo default and team additions

- **MUST** ship as the minimum viable suite for a new solo-developer app: JVM unit tests for ViewModels/use cases/data logic (runTest + MainDispatcherRule + fakes) and one CI workflow running the single-variant unit tests plus lint with Gradle caching and XML artifacts
- **SHOULD** add JVM screenshot tests (Roborazzi) as the second layer — they buy UI regression coverage without any emulator job
- **MAY** defer instrumented suites, emulator matrices, coverage gates, and E2E lanes until team size, codebase size, or observed defects justify them; each addition is recorded as a deliberate strategy change, not accreted silently
- **MUST NOT** generate device-matrix CI jobs, retry machinery, or benchmark lanes into a fresh solo project by default — that is large-team machinery with real maintenance cost

## Acceptance Criteria

The criteria are a representative rollup of §A–§H, not a 1:1 mapping; every requirement bullet above is normative on its own.

- [ ] A generated project's test sources contain JVM unit tests for every ViewModel and repository the generator produced, covering at least one error/edge case each
- [ ] Every coroutine test uses `runTest`; a `MainDispatcherRule` (or equivalent) is present and applied in every ViewModel test; no production class hard-codes a dispatcher
- [ ] No test in the repository calls `Thread.sleep` or an equivalent wall-clock wait
- [ ] No mocking-library usage targets a project-owned interface with an available fake; fakes live per `spec/android/project-structure/` §F
- [ ] Compose screen tests target stateless content composables with fake state; no test instantiates a ViewModel through Hilt in a unit test
- [ ] Compose node matching uses semantics first; every `testTag` usage is on a container without inherent text semantics
- [ ] Feature-level Compose tests run in `src/test/` under Robolectric; instrumented tests exist only for documented device-only behavior
- [ ] When screenshot tests exist: goldens are committed per module, recorded on CI/Linux only, and `verifyRoborazzi…` (or the chosen tool's verify task) runs on every PR
- [ ] Accessibility checks (ATF) run inside the Compose or screenshot test layer, with suppressions individually justified in code
- [ ] CI runs exactly one debug variant's unit tests plus lint per PR through the same entry points as local runs, uploads JUnit XML artifacts, and any emulator job on a GitHub-hosted Linux runner enables KVM
- [ ] Retry mechanisms, where present, apply only to instrumented/big tests, and every known flaky test is tracked per the workflow-health conventions rather than silently retried
- [ ] No benchmark (Macro-/Microbenchmark) task runs in the per-commit CI lane
- [ ] A freshly generated project's full `task check` (including its test tasks) passes locally and in CI without manual intervention
- [ ] The project's chosen assertion library is used consistently (single library across all test sources)
- [ ] A freshly generated solo project ships the §H minimum suite and nothing more: no device-matrix CI job, no retry machinery, and no benchmark lane exists unless the project recorded the strategy change that added it

## Open Questions

Each question states the working default the requirements above already encode.

- Assertion library default: `kotlin.test` (flagship-sample practice) vs `assertk` (production-app favorite) — pick one when the first skill generates test code
- Screenshot tool commitment: Roborazzi is the default here; revisit when Google's Compose Preview Screenshot Testing leaves alpha (shared open question with `spec/android/project-structure/`)
- Turbine: adopt as standard for Flow-emission tests or keep as opt-in convenience?
- Coverage thresholds: whether generated projects get a Kover gate at all, and at what numbers — deferred until the quality-gate skill takes shape
- JUnit 5/6 on Android: revisit if Google ever documents JUnit 5+ as the AndroidX Test runner path; until then the JUnit 4 MUST stands and JUnit 5 remains the §B MAY (JVM without plugin, instrumented with the community plugin)
- Maestro smoke journeys: worth scaffolding as an optional template for device-real flows, or left entirely to per-project decisions?

## References

- [R1] Testing fundamentals — scope/host dimensions, testable architecture: <https://developer.android.com/training/testing/fundamentals>
- [R2] What to test — unit/UI priorities, low-value tests to avoid: <https://developer.android.com/training/testing/fundamentals/what-to-test>
- [R3] Testing strategies — pyramid, five layers, lowest-layer rule, strategy document: <https://developer.android.com/training/testing/fundamentals/strategies>
- [R4] Test doubles — fakes preferred, spies discouraged: <https://developer.android.com/training/testing/fundamentals/test-doubles>
- [R5] Local tests — JUnit 4, mocking cautions: <https://developer.android.com/training/testing/local-tests>
- [R6] Robolectric positioning — last resort for unit tests, sanctioned UI/screenshot roles, limits: <https://developer.android.com/training/testing/local-tests/robolectric>
- [R7] Coroutines testing — runTest, TestDispatchers, single scheduler, injected dispatchers: <https://developer.android.com/kotlin/coroutines/test>
- [R8] Flow testing — first()/value, WhileSubscribed collector rule, Turbine as third-party convenience: <https://developer.android.com/kotlin/flow/test>
- [R9] Hilt testing — no Hilt in unit tests, @HiltAndroidTest, @TestInstallIn: <https://developer.android.com/training/dependency-injection/hilt-testing>
- [R10] Compose testing — semantics-first matching, rules, synchronization: <https://developer.android.com/develop/ui/compose/testing>
- [R11] Compose testing common patterns — stateless testing, StateRestorationTester, DeviceConfigurationOverride: <https://developer.android.com/develop/ui/compose/testing/common-patterns>
- [R12] Compose accessibility testing — ATF integration in Compose ≥ 1.8: <https://developer.android.com/develop/ui/compose/accessibility/testing>
- [R13] Instrumented tests — when to use, AndroidX Test stack: <https://developer.android.com/training/testing/instrumented-tests>
- [R14] AndroidJUnitRunner and Test Orchestrator — isolation, clearPackageData, sharding: <https://developer.android.com/training/testing/instrumented-tests/androidx-test-libraries/runner>
- [R15] Instrumented-test stability — no sleeps, retry-but-fix, wait-until over Idling Resources: <https://developer.android.com/training/testing/instrumented-tests/stability>
- [R16] UI Automator — cross-app scope, 2.4 API, benchmark interactions: <https://developer.android.com/training/testing/other-components/ui-automator>
- [R17] Gradle Managed Devices — ATD images, headless-CI GPU flag, FTL integration: <https://developer.android.com/studio/test/gradle-managed-devices>
- [R18] CI automation and features — device options, retry matrix, sharding, benchmark cadence: <https://developer.android.com/training/testing/continuous-integration/automation>
- [R19] Roborazzi — record/verify tasks, ATF checks, threshold options: <https://github.com/takahirom/roborazzi>
- [R20] Paparazzi — layoutlib rendering, AGP coupling, status: <https://cashapp.github.io/paparazzi/>
- [R21] Compose Preview Screenshot Testing (alpha) — src/screenshotTest source set, plugin 0.0.1-alpha15, AGP/Kotlin requirements for Gradle-only vs IDE integration: <https://developer.android.com/studio/preview/compose-screenshot-testing>
- [R22] KVM on GitHub-hosted runners (GA 2024): <https://github.blog/changelog/2024-04-02-github-actions-hardware-accelerated-android-virtualization-now-available/>
- [R23] android-emulator-runner action — AVD caching pattern: <https://github.com/ReactiveCircus/android-emulator-runner>
- [R24] Kover — Kotlin-first coverage, multi-module aggregation, no instrumented coverage: <https://kotlin.github.io/kotlinx-kover/gradle-plugin/>
- [R25] Now in Android testing surfaces — MainDispatcherRule, Test\*Repository fakes, screenshot helper, Build workflow: <https://github.com/android/nowinandroid>
- [R26] Navigation 3 — back stack as state (test basis): <https://developer.android.com/guide/navigation/navigation-3>
- [R27] Advanced test setup — `testOptions.unitTests.all {}` exposes local unit-test tasks as Gradle `Test` tasks (P): <https://developer.android.com/studio/test/advanced-test-setup>
- [R28] Gradle Java testing — `useJUnitPlatform()` on a `Test` task (P): <https://docs.gradle.org/current/userguide/java_testing.html>
- [R29] android-junit5 community plugin — JUnit 5 for Android unit and instrumented tests, device API floor per JUnit generation (S): <https://github.com/mannodermaus/android-junit5>
