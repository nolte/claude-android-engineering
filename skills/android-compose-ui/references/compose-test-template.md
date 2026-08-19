# Compose test template

The Robolectric-hosted Compose test generated alongside every screen, per
`spec/android/test-automation/` §D/§E and, for input surfaces,
`spec/android/user-input-validation/` §H. It drives the stateless content composable with fake
`uiState` and no-op lambdas, matches nodes via semantics (`testTag` only where a node has no
inherent text semantics — the in-flight submit button in §7), and relies on
Compose's synchronization — auto-sync by default, `mainClock` for animations,
`waitUntil`/`waitUntilExactlyOneExists` for external work, never `Thread.sleep`. Assertions
use `kotlin.test` (`assertTrue`, `assertEquals`), the pure-JVM default of the portfolio.

## Table of contents

- [1. Placement and build config](#1-placement-and-build-config)
- [2. State-rendering test](#2-state-rendering-test)
- [3. Interaction test](#3-interaction-test)
- [4. State-restoration tests](#4-state-restoration-tests)
- [5. Configuration-variant tests](#5-configuration-variant-tests)
- [6. Animations, external work, and accessibility checks](#6-animations-external-work-and-accessibility-checks)
- [7. Input surface tests](#7-input-surface-tests)
- [8. Navigation 3 destination test](#8-navigation-3-destination-test)

## 1. Placement and build config

- Lives in `src/test/` of the module under test (feature modules host feature-level Compose
  tests on Robolectric; whole-app journey tests stay in `:app`).
- Requires `testOptions { unitTests.isIncludeAndroidResources = true }` so `stringResource`
  lookups resolve on the JVM.
- Runner: JUnit 4 with `@RunWith(RobolectricTestRunner::class)`. Robolectric is sanctioned here
  only because this is a UI-behavior test; plain logic tests (validators, ViewModels) stay
  pure-JVM with `kotlinx-coroutines-test`.

## 2. State-rendering test

Match on resource-looked-up text and content descriptions so the test is locale-safe and keeps
the app accessible. Each state is constructed directly — no ViewModel.

```kotlin
@RunWith(RobolectricTestRunner::class)
class ExampleContentTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    private val context get() = ApplicationProvider.getApplicationContext<Context>()

    @Test
    fun populatedState_showsItems() {
        composeTestRule.setContent {
            AppTheme {
                ExampleContent(
                    uiState = ExampleUiState.Success(items = fakeItems),
                    onItemClick = {}, onCreate = {}, onRetry = {},
                )
            }
        }

        composeTestRule
            .onNodeWithText(context.getString(R.string.example_title))
            .assertIsDisplayed()
        composeTestRule
            .onNodeWithContentDescription(context.getString(R.string.example_create_action))
            .assertIsDisplayed()
    }

    @Test
    fun emptyState_showsCallToAction() {
        composeTestRule.setContent {
            AppTheme {
                ExampleContent(ExampleUiState.Empty, {}, {}, {})
            }
        }
        composeTestRule
            .onNodeWithText(context.getString(R.string.example_empty_body))
            .assertIsDisplayed()
    }

    @Test
    fun errorState_showsLocalizedMessageAndRetry() {
        composeTestRule.setContent {
            AppTheme {
                ExampleContent(ExampleUiState.Error(ErrorKind.Offline), {}, {}, {})
            }
        }
        composeTestRule
            .onNodeWithText(context.getString(R.string.error_offline_retry))
            .assertIsDisplayed()
    }
}
```

## 3. Interaction test

Navigation callbacks are injected lambdas; assert the lambda fired, never a passed-around
controller.

```kotlin
@Test
fun createAction_invokesCallback() {
    var created = false
    composeTestRule.setContent {
        AppTheme {
            ExampleContent(
                uiState = ExampleUiState.Success(fakeItems),
                onItemClick = {}, onCreate = { created = true }, onRetry = {},
            )
        }
    }
    composeTestRule
        .onNodeWithContentDescription(context.getString(R.string.example_create_action))
        .performClick()
    assertTrue(created)
}
```

## 4. State-restoration tests

Verify `rememberSaveable` survival with `StateRestorationTester` where the screen holds
restorable UI-local state (scroll position, selection). `StateRestorationTester` recreates
only the composition — a ViewModel stays alive — so input the state holder owns needs a direct
`SavedStateHandle` round-trip test as well (`spec/android/user-input-validation/` §H).

```kotlin
@Test
fun scrollPosition_survivesRecreation() {
    val restorationTester = StateRestorationTester(composeTestRule)
    restorationTester.setContent {
        AppTheme { ExampleContent(ExampleUiState.Success(fakeItems), {}, {}, {}) }
    }
    // scroll / select ...
    restorationTester.emulateSavedInstanceStateRestore()
    // assert the state is preserved ...
}

// Pure-JVM, no Robolectric needed: proves the SavedStateHandle keys and savers round-trip.
@Test
fun draftInput_survivesSavedStateHandleRoundTrip() = runTest {
    val handle = SavedStateHandle()
    val first = ExampleFormViewModel(handle, repository = FakeExampleRepository())
    first.onNameChanged("Ada")
    val restored = ExampleFormViewModel(SavedStateHandle(handle.keys().associateWith { handle.get<Any>(it) }), FakeExampleRepository())
    assertEquals("Ada", restored.uiState.value.name.text.text.toString())
}
```

## 5. Configuration-variant tests

Use `DeviceConfigurationOverride` to test dark mode, font scale, locale, and forced window
size without a device. This is how the reference-matrix sizes and 200 % font scale are
verified on the JVM (`spec/android/screen-formats/` §D).

```kotlin
@Test
fun rendersAtLargeFontScale() {
    composeTestRule.setContent {
        DeviceConfigurationOverride(DeviceConfigurationOverride.FontScale(2.0f)) {
            AppTheme { ExampleContent(ExampleUiState.Success(fakeItems), {}, {}, {}) }
        }
    }
    composeTestRule
        .onNodeWithText(context.getString(R.string.example_title))
        .assertIsDisplayed() // critical UI not clipped at 200%
}

@Test
fun rendersInGermanLocale() {
    composeTestRule.setContent {
        DeviceConfigurationOverride(
            DeviceConfigurationOverride.Locales(LocaleList("de")) // androidx.compose.ui.text.intl.LocaleList,
        ) {
            AppTheme { ExampleContent(ExampleUiState.Success(fakeItems), {}, {}, {}) }
        }
    }
}

// Reference matrix: foldable 841×701, 8" 1024×640, 10.5" 1280×800, 13" 1600×900 dp.
@Test
fun listDetail_showsTwoPanesOnExpandedWindow() {
    composeTestRule.setContent {
        DeviceConfigurationOverride(
            DeviceConfigurationOverride.ForcedSize(DpSize(1280.dp, 800.dp)),
        ) {
            AppTheme { ExampleListDetailContent(ExampleUiState.Success(fakeItems), selectedId = fakeItems.first().id, {}, {}, {}) }
        }
    }
    composeTestRule.onNodeWithText(fakeItems.first().title).assertIsDisplayed()  // list pane
    composeTestRule.onNodeWithText(context.getString(R.string.example_detail_title)).assertIsDisplayed() // detail pane
}
```

## 6. Animations, external work, and accessibility checks

- Animations (`AnimatedVisibility`, the delayed loading indicator): drive time with
  `composeTestRule.mainClock` — `autoAdvance = false`, `advanceTimeBy(...)` — never sleep.
- External work (a fake repository completing on another dispatcher): `waitUntil { … }` or
  `waitUntilExactlyOneExists(matcher)`; Idling Resources only in small interop tests.
- Accessibility Test Framework: call `composeTestRule.enableAccessibilityChecks()` in setup
  (Compose ≥ 1.8) so touch-target, contrast, and content-description checks run on every
  interaction; suppress individual checks only by name with a written justification
  (`spec/android/test-automation/` §E).

```kotlin
@Before
fun setUp() {
    composeTestRule.enableAccessibilityChecks()
}

@Test
fun loadingIndicator_appearsOnlyAfter200ms() {
    composeTestRule.mainClock.autoAdvance = false
    composeTestRule.setContent {
        AppTheme { ExampleContent(ExampleUiState.Loading, {}, {}, {}) }
    }
    composeTestRule.onNode(hasProgressBarRangeInfo(ProgressBarRangeInfo.Indeterminate))
        .assertDoesNotExist()
    composeTestRule.mainClock.advanceTimeBy(250)
    composeTestRule.onNode(hasProgressBarRangeInfo(ProgressBarRangeInfo.Indeterminate))
        .assertExists()
}
```

## 7. Input surface tests

Required whenever the screen takes a value from the user
(`spec/android/user-input-validation/` §H): the timing contract, error semantics and live
region, the adversarial value set as pure-function tests, and the server-rejection path.

```kotlin
@Test
fun emailError_appearsOnlyAfterFieldLeft_andClearsOnFixingKeystroke() {
    composeTestRule.setContent { AppTheme { ExampleFormHost() } } // host wires a real holder
    val emailLabel = context.getString(R.string.form_email_label)
    val emailError = context.getString(R.string.form_email_invalid)

    composeTestRule.onNodeWithText(emailLabel).performTextInput("ada@")
    composeTestRule.onNodeWithText(emailError).assertDoesNotExist()   // no error while typing

    composeTestRule.onNodeWithText(context.getString(R.string.form_name_label)).performClick()
    composeTestRule.onNodeWithText(emailError).assertIsDisplayed()    // error after first exit
    composeTestRule.onNodeWithText(emailLabel)
        .assert(SemanticsMatcher.keyIsDefined(SemanticsProperties.Error))

    composeTestRule.onNodeWithText(emailLabel).performTextInput("example.org")
    composeTestRule.onNodeWithText(emailError).assertDoesNotExist()   // gone on fixing keystroke
}

@Test
fun submitFailure_announcesViaLiveRegion_andPreservesInput() {
    val repository = FakeExampleRepository(nextResult = ExampleResult.Rejected(field = "email", rule = Rule.Taken))
    composeTestRule.setContent { AppTheme { ExampleFormHost(repository) } }
    composeTestRule.onNodeWithText(context.getString(R.string.form_email_label)).performTextInput("ada@example.org")
    composeTestRule.onNodeWithText(context.getString(R.string.form_submit)).performClick()

    composeTestRule.onNodeWithText(context.getString(R.string.form_email_taken))
        .assertIsDisplayed()                                          // lands on the field
    composeTestRule.onNode(SemanticsMatcher.expectValue(SemanticsProperties.LiveRegion, LiveRegionMode.Polite))
        .assertExists()                                               // form-level status
    composeTestRule.onNodeWithText("ada@example.org").assertExists()  // input preserved
}

@Test
fun submit_ignoresSecondTapWhileInFlight() {
    val repository = FakeExampleRepository(delayCompletion = true)
    composeTestRule.setContent { AppTheme { ExampleFormHost(repository) } }
    // The in-flight button swaps its label for DelayedLoadingIndicator (screen-template §7), so
    // the text node disappears; the recorded testTag exception keeps the node addressable.
    composeTestRule.onNodeWithTag("form_submit").performClick()
    composeTestRule.onNodeWithTag("form_submit").performClick()   // second tap while in flight
    composeTestRule.onNodeWithTag("form_submit").assertIsNotEnabled()
    assertEquals(1, repository.submitCalls)
}

// Pure-JVM validator tests over the normalised value — one per field, at least this set.
@RunWith(Parameterized::class)
class EmailValidatorTest(private val input: String, private val expected: Rule?) {
    companion object {
        @JvmStatic @Parameterized.Parameters(name = "{0}")
        fun cases() = listOf(
            arrayOf("", Rule.Required),
            arrayOf("   ", Rule.Required),
            arrayOf("a".repeat(254) + "@x.io", null),
            arrayOf("a".repeat(255) + "@x.io", Rule.TooLong),
            arrayOf(" ada@example.org\n", null),          // pasted whitespace normalised
            arrayOf("adä@exämple.org", null),             // Unicode
            arrayOf("ada\u0301@example.org", null),      // combining marks
            arrayOf("😀@example.org", Rule.Invalid),
            arrayOf("1,5", Rule.Invalid),                  // other-locale value on a numeric field
            arrayOf("<script>alert(1)</script>", Rule.Invalid), // adversarial (scan/deep-link/paste)
        )
    }
    @Test fun validates() = assertEquals(expected, EmailValidator.check(input.normalise()))
}
```

## 8. Navigation 3 destination test

When the screen is a Navigation 3 destination, treat the back stack as plain state: build a
test `NavDisplay` with the feature's `entryProvider`, drive the injected lambdas, and assert
on the back-stack contents (`spec/android/test-automation/` §D). No `NavController` exists to
pass around.

```kotlin
@Test
fun itemClick_pushesDetailKey() {
    val backStack = mutableStateListOf<NavKey>(ExampleKey)
    composeTestRule.setContent {
        AppTheme {
            NavDisplay(
                backStack = backStack,
                onBack = { backStack.removeLastOrNull() },
                // exampleEntries (screen-template §8) registers ExampleKey and ExampleDetailKey
                // once each — never add a second entry<T> for a class the builder already holds.
                entryProvider = entryProvider {
                    exampleEntries(
                        onItemClick = { id -> backStack.add(ExampleDetailKey(id)) },
                        onCreate = {},
                    )
                },
            )
        }
    }
    composeTestRule.onNodeWithText(fakeItems.first().title).performClick()
    assertEquals(ExampleDetailKey(fakeItems.first().id), backStack.last())
}
```
