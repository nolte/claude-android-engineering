# Test infrastructure templates

The infrastructure the `apply` operation adds or patches (SKILL.md step 5). Every template
traces to `spec/android/test-automation/` §B/§C/§D/§E; feature-specific tests are not here —
they belong to `android-feature-implement` and `android-compose-ui`. Coordinates are named,
versions are not: resolve current stable versions at apply time into `libs.versions.toml`
(REQ-5; never a hard-coded or dynamic version in a build script). Confirm the artifact
coordinates against the vendor documentation when adding them — they are stated from the
research pass of the spec, not from memory.

## Table of contents

- [1. MainDispatcherRule](#1-maindispatcherrule)
- [2. Fake and ViewModel-test skeletons](#2-fake-and-viewmodel-test-skeletons)
- [3. Robolectric hosting for Compose tests](#3-robolectric-hosting-for-compose-tests)
- [4. Forced-size configuration matrix](#4-forced-size-configuration-matrix)
- [5. Roborazzi screenshot lane](#5-roborazzi-screenshot-lane)
- [6. Accessibility checks](#6-accessibility-checks)
- [7. Shared testing module](#7-shared-testing-module)

## 1. MainDispatcherRule

§B: a `TestWatcher` that swaps `Dispatchers.Main`, applied in every ViewModel test. Lives in
the module's `src/test/` (single module) or in `:core:testing` (§7). `UnconfinedTestDispatcher`
is the default so `WhileSubscribed` collectors start eagerly; a test that needs manual
scheduling passes `StandardTestDispatcher(testScheduler)` and drives it with `advanceUntilIdle`.

```kotlin
class MainDispatcherRule(
    private val testDispatcher: TestDispatcher = UnconfinedTestDispatcher(),
) : TestWatcher() {
    override fun starting(description: Description) = Dispatchers.setMain(testDispatcher)
    override fun finished(description: Description) = Dispatchers.resetMain()
}
```

Production classes take a `CoroutineDispatcher` (or a dispatcher-provider interface) through
their constructor; the DI module supplies `Dispatchers.IO`/`Default`, the test supplies the
`TestDispatcher` — the only place `Dispatchers.IO` may appear in `src/main` is that provider.

## 2. Fake and ViewModel-test skeletons

§C: a fake is a hand-written implementation behind the production interface with test-only
hooks; a hot flow with `replay = 1` plus an imperative `send…` method is the standard shape.

```kotlin
class FakeGreetingRepository : GreetingRepository {
    private val greetings = MutableSharedFlow<List<Greeting>>(replay = 1)
    override fun observeGreetings(): Flow<List<Greeting>> = greetings
    fun sendGreetings(value: List<Greeting>) = greetings.tryEmit(value)
    var failNextRefresh: Throwable? = null
    override suspend fun refresh() { failNextRefresh?.let { failNextRefresh = null; throw it } }
}
```

```kotlin
class HomeViewModelTest {
    @get:Rule val mainDispatcherRule = MainDispatcherRule()
    private val repository = FakeGreetingRepository()
    private val viewModel = HomeViewModel(repository)   // direct construction, no Hilt

    @Test
    fun uiState_isError_whenRefreshFails() = runTest {
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.uiState.collect() }
        repository.failNextRefresh = IOException("offline")
        viewModel.refresh()
        assertIs<HomeUiState.Error>(viewModel.uiState.value)   // kotlin.test
    }
}
```

Assertions come from the single library the strategy file names (`kotlin.test` by default:
`assertEquals`, `assertIs`, `assertTrue`). Replacing a `mockk<OwnRepository>()` with a fake is
a per-file change confirmed with the operator; the mock stays only when the type is a true
system boundary the strategy file lists.

## 3. Robolectric hosting for Compose tests

§D SHOULD: feature-level Compose tests run in `src/test/` under Robolectric. Module build
script:

```kotlin
android {
    testOptions {
        unitTests.isIncludeAndroidResources = true   // stringResource lookups on the JVM
        unitTests.isReturnDefaultValues = false      // keep failures loud
    }
}
dependencies {
    testImplementation(libs.junit4)
    testImplementation(libs.kotlinx.coroutines.test)
    testImplementation(libs.robolectric)
    testImplementation(libs.androidx.test.core)
    testImplementation(platform(libs.androidx.compose.bom))
    testImplementation(libs.androidx.compose.ui.test.junit4)
    debugImplementation(libs.androidx.compose.ui.test.manifest)   // hosts ComponentActivity
}
```

Test class shape: `@RunWith(RobolectricTestRunner::class)`, `createComposeRule()`,
`setContent { AppTheme { <Screen>Content(uiState = …, on… = {}) } }`, semantic matching through
`context.getString(R.string.…)`. The full test template lives in
`android-compose-ui/references/compose-test-template.md` and is not repeated here. Robolectric
is sanctioned only for these UI-behavior tests and screenshots (§B); a plain logic test keeps
the default runner.

Only a documented device-only reason (system UI, WebView, hardware rendering, real process
death, release-build verification — §F) moves a test to `src/androidTest/`; the reason is
recorded in the strategy file.

## 4. Forced-size configuration matrix

§D SHOULD, executing `spec/android/screen-formats/` §D: the reference matrix — foldable
841×701 dp, 8" tablet 1024×640 dp, 10.5" tablet 1280×800 dp, 13" 1600×900 dp — plus a compact
phone size, 200 % font scale, the supported locales, and dark mode, all on the JVM.
`DeviceConfigurationOverride` needs a Compose UI test artifact from a BOM that ships it (Compose
UI ≥ 1.7).

```kotlin
object ReferenceMatrix {
    val compactPhone = DpSize(360.dp, 800.dp)
    val foldable = DpSize(841.dp, 701.dp)
    val tablet8 = DpSize(1024.dp, 640.dp)
    val tablet10 = DpSize(1280.dp, 800.dp)
    val desktop13 = DpSize(1600.dp, 900.dp)
    val all = listOf(compactPhone, foldable, tablet8, tablet10, desktop13)
}

fun ComposeContentTestRule.setContentAt(size: DpSize, content: @Composable () -> Unit) =
    setContent {
        DeviceConfigurationOverride(DeviceConfigurationOverride.ForcedSize(size)) { AppTheme(content = content) }
    }
```

A screen test iterates `ReferenceMatrix.all` (JUnit 4 `Parameterized` runner, or one test per
size) and asserts the canonical-layout expectation of screen-formats §C — for example that a
list-detail screen shows both panes at `foldable` and above and one pane at `compactPhone`.
Combine with `DeviceConfigurationOverride.then(…)` for `FontScale(2f)`, `Locales(…)`, and
`DarkMode(true)`. Which screens run the matrix is a strategy-file decision (§8 there); this
helper is the infrastructure. Robolectric qualifiers (`@Config(qualifiers = "w841dp-h701dp")`)
are the fallback where a screen reads `LocalConfiguration` directly.

## 5. Roborazzi screenshot lane

§E: JVM screenshots with Roborazzi as the default; goldens per module under
`src/test/screenshots/`, recorded on CI/Linux only, verified on every PR.

Root build script (`plugins { alias(libs.plugins.roborazzi) apply false }`) and per module:

```kotlin
plugins { alias(libs.plugins.roborazzi) }
roborazzi { outputDir.set(file("src/test/screenshots")) }
dependencies {
    testImplementation(libs.roborazzi)
    testImplementation(libs.roborazzi.compose)
    testImplementation(libs.roborazzi.junit.rule)
}
```

Catalog entries: plugin `io.github.takahirom.roborazzi`; libraries
`io.github.takahirom.roborazzi:roborazzi`, `…:roborazzi-compose`, `…:roborazzi-junit-rule`
(and `…:roborazzi-accessibility-check` for the ATF hook of §6). Screenshot test shape:

```kotlin
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [<one pinned API level>], qualifiers = RobolectricDeviceQualifiers.Pixel5)
class HomeContentScreenshotTest {
    @get:Rule val composeTestRule = createComposeRule()

    @Test
    fun populated() {
        composeTestRule.setContent { AppTheme { HomeContent(HomeUiState.Success(fakeItems), {}, {}, {}) } }
        composeTestRule.onRoot().captureRoboImage()
    }
}
```

Tasks: `recordRoborazzi<Variant>` (writes goldens), `verifyRoborazzi<Variant>` (fails on
diff, writes `*_compare.png` under `build/outputs/roborazzi/`), `compareRoborazzi<Variant>`.
One `sdk` and one qualifier set are pinned in the annotation so the render is deterministic;
Robolectric's `@GraphicsMode(NATIVE)` is mandatory for real rendering. Wire
`verifyRoborazzi<Variant>` into `task test` only after the first CI record run has committed
goldens — before that the verify task fails on missing files. Paparazzi (`app.cash.paparazzi`)
stays where a project already uses it in a pure design-system module (§E MAY); do not migrate
it silently.

## 6. Accessibility checks

§E SHOULD: Accessibility Test Framework checks as a regression net inside the Compose or
screenshot layer — never a replacement for the manual TalkBack pass (`android-ux-reviewer`).

Compose ≥ 1.8: add the Compose accessibility test artifact
(`androidx.compose.ui:ui-test-junit4-accessibility`, BOM-managed) and enable the checks on the
rule:

```kotlin
@get:Rule val composeTestRule = createAndroidComposeRule<ComponentActivity>()

@Before fun enableChecks() { composeTestRule.enableAccessibilityChecks() }
// checks run on every action; call composeTestRule.onRoot().tryPerformAccessibilityChecks() where a
// pure-assertion test performs no action (the extension lives on SemanticsNodeInteraction)
```

Suppressions: `AccessibilityValidator.setSuppressingResultMatcher(...)` with a comment naming
the check, the node, and the reason — one matcher per justified case, never a blanket
suppression. In the screenshot lane the ATF hook is Roborazzi's
`roborazzi-accessibility-check` (`RoborazziRule` with an ATF `AccessibilityCheckStrategy`
option), applied in the shared screenshot helper so every capture is checked. Which layer
carries the checks is a strategy-file decision (§10 there).

## 7. Shared testing module

`spec/android/project-structure/` §F SHOULD: once modularized, `MainDispatcherRule`, fakes,
test data, the screenshot helper, and the forced-size helper move to `:core:testing`
(`com.android.library`, `implementation` on JUnit 4, coroutines-test, Compose UI test, and the
production `:core:*` interfaces the fakes implement); modules consume it via
`testImplementation(projects.core.testing)`. Single-module projects keep the same files under
`app/src/test/…/testing/`. Hilt projects additionally get the tiny `ui-test-hilt-manifest`
module (a `@AndroidEntryPoint` `ComponentActivity` in a test manifest) so Compose tests can host
injected content (§D SHOULD).
