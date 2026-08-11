# Compose test template

The Robolectric-hosted Compose test generated alongside every screen, per
`spec/android/test-automation/` §D. It drives the stateless content composable with fake
`uiState` and no-op lambdas, matches nodes via semantics (not `testTag`), and relies on
Compose's auto-synchronization (never `Thread.sleep`).

## Table of contents

- [1. Placement and build config](#1-placement-and-build-config)
- [2. State-rendering test](#2-state-rendering-test)
- [3. Interaction test](#3-interaction-test)
- [4. State-restoration test](#4-state-restoration-test)
- [5. Configuration-variant test](#5-configuration-variant-test)

## 1. Placement and build config

- Lives in `src/test/` of the module under test (feature modules host feature-level Compose
  tests on Robolectric; whole-app journey tests stay in `:app`).
- Requires `testOptions { unitTests.isIncludeAndroidResources = true }` so `stringResource`
  lookups resolve on the JVM.
- Runner: JUnit 4 with `@RunWith(RobolectricTestRunner::class)`. Robolectric is sanctioned here
  only because this is a UI-behavior test; plain logic tests stay pure-JVM.

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
    assertThat(created).isTrue()
}
```

## 4. State-restoration test

Verify `rememberSaveable` survival with `StateRestorationTester` where the screen holds
restorable UI state (scroll position, input, selection).

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
```

## 5. Configuration-variant test

Use `DeviceConfigurationOverride` to test dark mode, font scale, and locale without a device.
This is how the reference-matrix sizes and 200% font scale are verified on the JVM
(`spec/android/screen-formats/` §D).

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
            DeviceConfigurationOverride.Locales(LocaleList.forLanguageTags("de")),
        ) {
            AppTheme { ExampleContent(ExampleUiState.Success(fakeItems), {}, {}, {}) }
        }
    }
}
```
