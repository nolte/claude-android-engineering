# Suite hygiene rules

The rules of `spec/android/test-automation/` §A/§B/§C/§D/§F, distilled into findings the
`audit` operation can detect and the `apply` operation can fix. Every row names its spec
section; the spec, not this table, is normative. Severity follows the canonical scale of
`spec/claude/review-plan/`: `Critical` for a breached MUST or MUST NOT, `Warning` for a
breached SHOULD, `Suggestion` for a MAY worth adopting or a SHOULD the strategy file records
as deferred, `Info` for a surface scanned clean.

The heuristics are grep-grade starting points over `src/test/**`, `src/androidTest/**`, and
`src/main/**`; every hit is read in context before it becomes a finding.

## Table of contents

- [1. Strategy and pyramid (§A, §F)](#1-strategy-and-pyramid-a-f)
- [2. Local unit tests (§B)](#2-local-unit-tests-b)
- [3. Test doubles (§C)](#3-test-doubles-c)
- [4. Compose UI tests (§D)](#4-compose-ui-tests-d)
- [5. Screenshot and accessibility lane (§E)](#5-screenshot-and-accessibility-lane-e)
- [6. Assertion library consistency](#6-assertion-library-consistency)
- [7. Gotchas](#7-gotchas)

## 1. Strategy and pyramid (§A, §F)

| Rule | Detection heuristic | Severity | Fix (operation) |
|---|---|---|---|
| Every ViewModel, repository, use case, and non-trivial utility has a JVM unit test with at least one error/edge case (§A MUST) | List `*ViewModel.kt`, `*Repository.kt`, `*UseCase.kt` under `src/main`; match against `src/test` classes by name; read the matched test for an error/empty/corrupt-input case | Critical when a class has no test at all; Warning when only the happy path is covered | route to `android-feature-implement` (feature tests) — this skill reports, it does not write feature tests |
| No unit test on activities, services, or framework behavior (§A MUST NOT) | Test class names ending in `ActivityTest`/`ServiceTest` under `src/test`; `Robolectric.buildActivity(` in a non-UI test | Critical | move the logic out of the entry point (`android-feature-implement`); delete the test only with confirmation |
| Each screen's critical interactions have a content-composable UI test; the common journeys have a few journey tests (§A MUST) | Compose screens (`*Screen.kt`/`*Content.kt`) without a matching `*Test.kt` calling `createComposeRule()`/`createAndroidComposeRule()` | Warning (screens), Suggestion (journeys) | route to `android-compose-ui` |
| Strategy recorded (§A SHOULD) | `project/test-strategy.md` present, or a "Test strategy" section in `CLAUDE.md` | Warning | `plan` |
| Instrumented tests only for device-only behavior (§F MUST) | Every class under `src/androidTest` is checked for a documented reason (KDoc, strategy file entry); one that only drives a Compose content composable belongs on Robolectric | Critical | move to `src/test` under Robolectric (per-file confirmation) |
| No benchmark task in the per-commit lane (§F MUST) | `benchmark`, `macrobenchmark`, `connectedBenchmark` in `.github/workflows/*` PR triggers or in `task check` | Critical | remove from the PR lane; hand the scheduled lane to `android-perceived-performance` |
| Retries only for big/instrumented tests, never permanent (§F MUST NOT) | `retry`, `rerun`, `flaky` in workflows or Gradle test config; `@FlakyTest`, `RetryRule` in `src/test` | Critical in `src/test`; Warning without a tracked flake record for `src/androidTest` | remove or track per the workflow-health conventions |

## 2. Local unit tests (§B)

| Rule | Detection heuristic | Severity | Fix (operation) |
|---|---|---|---|
| JUnit 4 runner; JUnit 5 not assumed (§B MUST) | `org.junit.jupiter` imports, `de.mannodermaus` plugin, `useJUnitPlatform()` in an Android module | Critical in an Android module; Info in a pure-JVM module (record the MAY in the strategy file) | migrate per class with confirmation, or record the pure-JVM MAY |
| Coroutine tests run in `runTest` (§B MUST) | `runBlocking {` or `GlobalScope` in `src/test`; `suspend` test bodies without `runTest` | Critical | replace with `runTest` |
| `MainDispatcherRule` present and applied in every ViewModel test (§B MUST) | `Dispatchers.setMain(` outside a `TestWatcher`; `*ViewModelTest` classes without `@get:Rule val … = MainDispatcherRule()` | Critical | add the rule from `references/test-infrastructure-templates.md` §1 |
| Dispatchers injected, never hard-coded (§B MUST) | `Dispatchers.IO`, `Dispatchers.Default`, `Dispatchers.Main` in `src/main` outside a DI module or a dispatcher-provider class | Critical | inject a `CoroutineDispatcher` (production change, per-file confirmation) |
| No `Thread.sleep` or wall-clock wait (§B MUST NOT) | `Thread.sleep(`, `SystemClock.sleep(`, `delay(` outside virtual time, `CountDownLatch.await(` with a timeout, `Awaitility` | Critical | virtual time (`advanceUntilIdle`, `advanceTimeBy`), Compose `waitUntil`, Turbine |
| Injected clock for time-dependent logic (§B MUST via injected dependencies) | `System.currentTimeMillis()`, `Clock.systemUTC()`, `LocalDateTime.now()` in `src/main` outside a clock provider | Warning | inject `kotlinx.datetime.Clock`/`java.time.Clock` |
| StateFlow asserted on `.value`; `WhileSubscribed` flows have a collector (§B SHOULD) | `stateIn(` with `WhileSubscribed` in `src/main` and a test asserting `.value` with no `backgroundScope.launch { … collect() }` | Warning | add the collector (see §7) |
| Robolectric not on plain unit tests (§B MUST NOT) | `@RunWith(RobolectricTestRunner::class)` or `AndroidJUnit4::class` on a class with no `createComposeRule`/`ApplicationProvider`/resource access | Critical | drop the runner |
| Turbine, if used, is convenience not baseline (§B MAY) | `app.cash.turbine` in the catalog | Info | none; record in the strategy file |

## 3. Test doubles (§C)

| Rule | Detection heuristic | Severity | Fix (operation) |
|---|---|---|---|
| Fakes over mocks; no mock of project-owned logic, data, or repositories (§C MUST / MUST NOT) | `mockk<`, `mockk(`, `Mockito.mock(`, `@Mock`, `@MockK` where the type is declared under the project's own package | Critical | write a fake per `references/test-infrastructure-templates.md` §2 (per-file confirmation) |
| Mocking only at true system boundaries (§C MAY) | mocking of platform or third-party types (`Context`, an HTTP client, a sensor manager) | Info | none; the strategy file names the permitted boundaries |
| No deep mock graphs or spies (§C MUST NOT) | `spyk(`, `Mockito.spy(`, `RETURNS_DEEP_STUBS`, chained `every { a.b.c }` | Critical | fix the seam; write a fake |
| ViewModels constructed directly with fakes; no Hilt in unit tests (§C MUST) | `@HiltAndroidTest`, `HiltAndroidRule`, `hiltViewModel()` under `src/test` for a plain unit test | Critical | construct the ViewModel directly |
| Hilt UI/integration tests use `@HiltAndroidTest` + `HiltAndroidRule(order = 0)` + Hilt runner + `@TestInstallIn` (§C MUST) | Hilt test classes lacking the rule order, or `testInstrumentationRunner` not the Hilt runner; `@UninstallModules` used where `@TestInstallIn` would do | Critical (rule/runner), Suggestion (`@TestInstallIn` preference) | patch with confirmation |
| Shared fakes in `:core:testing` once modularized (project-structure §F SHOULD) | fakes duplicated across two or more modules' `src/test` | Warning | add `:core:testing` (`apply`) |

## 4. Compose UI tests (§D)

| Rule | Detection heuristic | Severity | Fix (operation) |
|---|---|---|---|
| Screen tests target the stateless content composable with fake `uiState` (§D MUST) | `setContent { … Route( … viewModel` or `hiltViewModel()` inside a `src/test` Compose test | Critical | test the `*Content` composable; route the split itself to `android-compose-ui` |
| Semantics-first matching; `testTag` only on containers (§D MUST) | `onNodeWithTag(` whose target node has text or a content description; hard-coded English text in `onNodeWithText("…")` instead of a resource lookup | Warning (tag), Warning (locale-unsafe text) | match on `getString(R.string…)`, content description, role |
| Compose synchronization, never sleeps; Idling Resources only in interop (§D MUST) | `Thread.sleep(` in a Compose test; `IdlingRegistry` outside a View-interop test | Critical | `mainClock`, `waitUntil`, `waitUntilExactlyOneExists` |
| Feature-level Compose tests on Robolectric in `src/test` with `isIncludeAndroidResources = true` (§D SHOULD) | Compose content tests under `src/androidTest` with no device-only reason; `testOptions.unitTests.isIncludeAndroidResources` absent | Warning | move + set the option (`apply`) |
| A few whole-app integration tests in `:app`; feature modules at `ComponentActivity`/fake-state level (§D SHOULD) | feature modules with `createAndroidComposeRule<MainActivity>` | Warning | restructure with confirmation |
| Hilt-hosted Compose tests use a tiny test-manifest module (§D SHOULD) | Hilt project whose Compose tests declare a test Activity in each feature module's test manifest | Suggestion | add the `ui-test-hilt-manifest` module (`apply`) |
| `rememberSaveable` state verified with `StateRestorationTester` (§D SHOULD) | screens holding `rememberSaveable` and no `StateRestorationTester` in their tests | Warning | route to `android-compose-ui` |
| Configuration variants via `DeviceConfigurationOverride` (§D SHOULD); reference matrix per screen-formats §D | adaptive screens with no `ForcedSize`/`FontScale`/`Locales`/`DarkMode` override tests | Warning | add the matrix helper (`apply`, `references/test-infrastructure-templates.md` §4) |
| Navigation 3 back stack tested as state (§D MUST) | tests asserting through a passed-around controller instead of a test `NavDisplay` with the feature's `entryProvider` | Critical | route to `android-compose-ui` |

## 5. Screenshot and accessibility lane (§E)

| Rule | Detection heuristic | Severity | Fix (operation) |
|---|---|---|---|
| Screenshot lane on the JVM, Roborazzi default (§E SHOULD; §H SHOULD as second layer) | no `io.github.takahirom.roborazzi` (or Paparazzi in a design-system-only module) in the catalog | Warning, downgraded to Suggestion when the strategy file records the deferral | `apply` |
| Goldens recorded on exactly one platform, committed per module (§E MUST) | golden PNGs present but no CI record job; goldens under a central directory instead of the module's `src/test/screenshots/` | Critical | move + record on CI (`apply`) |
| Screenshot verification on every PR; comparison images uploaded (§E MUST) | Roborazzi present but `verifyRoborazzi…` absent from the PR lane, or no `outputs/roborazzi` artifact step | Critical | `apply` (`references/ci-and-taskfile-templates.md`) |
| ATF checks in the Compose or screenshot layer with justified suppressions (§E SHOULD) | no `enableAccessibilityChecks()` and no ATF hook in the screenshot helper; suppressions without a comment naming the reason | Warning | `apply` |
| Automated a11y checks are not the manual audit (§E MUST NOT) | strategy file or CLAUDE.md claiming ATF replaces TalkBack/Scanner passes | Warning | correct the record; point to `android-ux-reviewer` |

## 6. Assertion library consistency

§B SHOULD: exactly one assertion library repo-wide, `kotlin.test` by default. Count imports
across `src/test`/`src/androidTest`: `kotlin.test.*`, `org.junit.Assert.*`, `com.google.common.truth`,
`assertk`, `org.hamcrest`. Two or more in use → Warning with the counts; the strategy file picks
the survivor (the majority library, or `kotlin.test` when the project has none), and migration
happens per file with confirmation. `org.junit.Assert` next to `kotlin.test` in the same class
counts as mixing.

## 7. Gotchas

- **`runTest` provides no `Dispatchers.Main`.** Without `MainDispatcherRule` a ViewModel that
  launches on `viewModelScope` fails with "Module with the Main dispatcher had failed to
  initialize"; the fix is the rule, not a `Dispatchers.setMain` per test method.
- **A `stateIn(WhileSubscribed)` flow reads its initial value until collected.** Assert only
  after `backgroundScope.launch { viewModel.uiState.collect() }`; `UnconfinedTestDispatcher`
  in the rule lets the collector start eagerly.
- **`advanceUntilIdle` needs one scheduler.** A `StandardTestDispatcher()` created without
  passing the test's `testScheduler` runs on its own clock and never advances; every
  `TestDispatcher` in a test shares the `TestScope`'s scheduler.
- **`isIncludeAndroidResources = true` is per module.** A Robolectric Compose test in a module
  without it fails on the first `stringResource` with a resource-not-found error, not a compile
  error.
- **Roborazzi goldens are OS-specific.** Antialiasing differs between macOS and Linux; a
  workstation-recorded set fails CI on the first pixel diff. Record on CI, and read
  `build/outputs/roborazzi/*_compare.png` when a verify fails.
- **`GrantPermissionRule` grants only.** It cannot model denial; permission-path tests set the
  state through ADB per `android-permissions-derive`.
- **The all-variant `test` task multiplies wall-clock by variant count.** With flavors,
  `testDebugUnitTest` does not exist — the variant-aware task is `test<Flavor>DebugUnitTest`,
  and CI must name it (§G).
