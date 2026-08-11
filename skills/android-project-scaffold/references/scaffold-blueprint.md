# Scaffold Blueprint

The file-by-file plan the `scaffold` operation writes. Every item traces to a `spec/android/project-structure/` (PS), `spec/android/localization/` (L10N), `spec/android/security/` (SEC), or `spec/android/test-automation/` (TEST) requirement. This file is a **structural contract**, not a version manifest — resolve concrete versions at scaffold time per SKILL.md "Mechanisms, not versions".

## Table of contents

- [1. File tree (single-module default)](#1-file-tree-single-module-default)
- [2. Repository root](#2-repository-root)
- [3. Version catalog](#3-version-catalog)
- [4. Settings and root build script](#4-settings-and-root-build-script)
- [5. The :app module build script](#5-the-app-module-build-script)
- [6. Manifest (L1 security baseline)](#6-manifest-l1-security-baseline)
- [7. Kotlin sources (route/content split)](#7-kotlin-sources-routecontent-split)
- [8. Design system / theme](#8-design-system--theme)
- [9. Bilingual resources](#9-bilingual-resources)
- [10. Minimum viable test suite](#10-minimum-viable-test-suite)
- [11. Modularization (only on an explicit trigger)](#11-modularization-only-on-an-explicit-trigger)

## 1. File tree (single-module default)

```
settings.gradle.kts
build.gradle.kts
gradle.properties
.editorconfig
.gitignore
secrets.defaults.properties
gradle/libs.versions.toml
gradle/wrapper/gradle-wrapper.properties
gradle/wrapper/gradle-wrapper.jar
gradlew
gradlew.bat
app/build.gradle.kts
app/src/main/AndroidManifest.xml
app/src/main/kotlin/<pkg>/MainActivity.kt
app/src/main/kotlin/<pkg>/ui/home/HomeRoute.kt
app/src/main/kotlin/<pkg>/ui/home/HomeScreen.kt
app/src/main/kotlin/<pkg>/ui/home/HomeViewModel.kt
app/src/main/kotlin/<pkg>/ui/home/HomeUiState.kt
app/src/main/kotlin/<pkg>/data/GreetingRepository.kt
app/src/main/kotlin/<pkg>/designsystem/theme/Theme.kt
app/src/main/kotlin/<pkg>/designsystem/theme/Color.kt
app/src/main/kotlin/<pkg>/designsystem/theme/Type.kt
app/src/main/kotlin/<pkg>/ui/language/LanguagePicker.kt
app/src/main/res/values/strings.xml
app/src/main/res/values-de/strings.xml
app/src/main/res/xml/locales_config.xml            # or generateLocaleConfig=true
app/src/main/res/xml/data_extraction_rules.xml
app/src/test/kotlin/<pkg>/ui/home/HomeViewModelTest.kt
app/src/test/kotlin/<pkg>/data/FakeGreetingRepository.kt
app/src/test/kotlin/<pkg>/util/MainDispatcherRule.kt
```

`<pkg>` is the confirmed root package as a path. Kotlin sources live under `kotlin/`, not `java/` (PS §D).

## 2. Repository root

- `.gitignore` — based on GitHub's canonical `Android.gitignore` (PS §A [R19]); covers `.gradle/`, `build/`, `local.properties`, `.idea/` subset, `captures/`, `.cxx/`, `*.apk`, `*.aab`, `*.jks`, `*.keystore`, `google-services.json`, `*.hprof`. Add `/.resume/`. The wrapper JAR is **allowlisted** (not ignored).
- `gradle.properties` — MUST enable `org.gradle.configuration-cache=true`, `org.gradle.caching=true`, `org.gradle.parallel=true`, `android.useAndroidX=true`, `kotlin.code.style=official`, and a sized `org.gradle.jvmargs` (`-Xmx` plus `-XX:MaxMetaspaceSize`). MUST NOT set obsolete flags: `android.nonTransitiveRClass`, `android.enableJetifier`, `kotlin.incremental`, PNG-crunch flags (PS §B).
- `.editorconfig` — root formatting + ktlint rule config lives here (PS §G).
- `secrets.defaults.properties` — committed defaults for the `secrets-gradle-plugin` pattern; real keys live in untracked `local.properties` (PS §A, SEC §F).

## 3. Version catalog

`gradle/libs.versions.toml` with `[versions]`, `[libraries]`, `[plugins]` (`[bundles]` only if it earns its keep). Rules (PS §B):

- Every dependency and plugin coordinate lives here; module scripts reference `libs.*` accessors only — no hard-coded or dynamic versions.
- Aliases in kebab-case; central versions via `version.ref`.
- The Compose compiler plugin (`org.jetbrains.kotlin.plugin.compose`) uses `version.ref` = the Kotlin version. Compose libraries carry **no** individual version — they resolve through `platform(libs.androidx.compose.bom)`.
- Annotation processing uses **KSP** (`com.google.devtools.ksp`), whose version suffix tracks the Kotlin version. No kapt.

## 4. Settings and root build script

- `settings.gradle.kts` — set `rootProject.name`; declare repositories centrally via `dependencyResolutionManagement` with `RepositoriesMode.FAIL_ON_PROJECT_REPOS` and content filtering (`google()` scoped to `com.android.*`, `androidx.*`, `com.google.*`). Include `:app`. `enableFeaturePreview("TYPESAFE_PROJECT_ACCESSORS")` is a SHOULD. For a modularized project add `pluginManagement { includeBuild("build-logic") }` (§11).
- `build.gradle.kts` (root) — **only** a `plugins {}` block declaring every submodule plugin with `apply false`. No `allprojects {}` / `subprojects {}`, no other code (PS §B).

## 5. The :app module build script

`app/build.gradle.kts` applies plugins via `alias(libs.plugins.…)`: Android application, Kotlin Android, Compose compiler, KSP. Key points:

- `applicationId`, `minSdk`, `targetSdk`, `versionCode`, `versionName` live here, not in the manifest (PS §D).
- `buildFeatures { compose = true }`; add both the Compose BOM and its test-configuration BOM (`platform(libs.androidx.compose.bom)` on `implementation` and `androidTestImplementation`).
- `androidResources { localeFilters += listOf("en", "de") }` (L10N §B) and `generateLocaleConfig = true` with `resources.properties` `unqualifiedResLocale=en`, or a manual `locales_config.xml` (L10N §C).
- `buildTypes { release { isDebuggable = false; isMinifyEnabled = true … } debug { isPseudoLocalesEnabled = true } }` (SEC §F/§G, L10N §E).
- Prefer `implementation` over `api` (PS §B). Constructor DI; manual DI is fine for a single-module app, Hilt once modularized (PS §E).

## 6. Manifest (L1 security baseline)

`app/src/main/AndroidManifest.xml` (SEC §A/§C/§D/§F):

- `<application>`: `android:allowBackup` set **explicitly**, `android:dataExtractionRules="@xml/data_extraction_rules"`, `android:supportsRtl="true"` (L10N §D), no `android:usesCleartextTraffic` (cleartext stays off), no `android:debuggable` in source (release build sets `false`).
- Every `<activity>`/`<service>`/`<receiver>` declares `android:exported` **explicitly**; the launcher activity is the only `exported="true"`, everything else `false`.
- Request only the minimum permissions in context; a fresh scaffold typically declares none.
- Add the `autoStoreLocales` metadata service for per-app language persistence below Android 13 (L10N §C).

## 7. Kotlin sources (route/content split)

Screen-level Compose code MUST split into a stateful route and a stateless content composable (PS §E):

- `HomeRoute.kt` — obtains the `HomeViewModel`, collects `uiState` (via `collectAsStateWithLifecycle`), forwards event lambdas to `HomeScreen`.
- `HomeScreen.kt` — stateless `@Composable HomeScreen(uiState: HomeUiState, onEvent lambdas)`; the `@Preview` targets this composable, lives next to it, and is named `HomeScreenPreview`. Add per-locale previews `@Preview(locale = "de")` and an RTL `@Preview(locale = "ar")` (L10N §F).
- `HomeViewModel.kt` — exposes `StateFlow<HomeUiState>`; never hard-codes a dispatcher (injected, for `MainDispatcherRule` in tests). Reaches data only through `GreetingRepository` (PS §E).
- `HomeUiState.kt` — the immutable UI state model.
- `data/GreetingRepository.kt` — named `<DataType>Repository`; UI never touches a data source directly (PS §E).

## 8. Design system / theme

`designsystem/theme/` package (PS §E/§C): `Theme.kt` (the `AppTheme` composable, Material 3, dynamic color where wanted), `Color.kt`, `Type.kt`. This is the single home for theming; once modularized it becomes `:core:designsystem`. Component-level rules (spacing, tokens, specific components) belong to the compose-ui skill's specs — do **not** duplicate them here; scaffold only the theme scaffold and typed accessors.

## 9. Bilingual resources

- `res/values/strings.xml` — the **complete** English source of truth (L10N §B). Every user-visible string externalized (L10N §A); positional placeholders (`%1$s`); `<plurals>` with an `other` case for counts; `translatable="false"` on the app name/brand tokens.
- `res/values-de/strings.xml` — German translation carrying the **same key set** (L10N §E). Draft translations are acceptable transiently; note in the report that visible strings need human review.
- `ui/language/LanguagePicker.kt` — in-app picker calling `AppCompatDelegate.setApplicationLocales()`/`getApplicationLocales()`, offering "system default" (`emptyLocaleList`) (L10N §C). Host activity is an `AppCompatActivity` even in a Compose app.
- `res/xml/locales_config.xml` — supported-locale list wired via `android:localeConfig` (or `generateLocaleConfig = true`).

## 10. Minimum viable test suite

TEST §H — the solo-developer floor, in `app/src/test/` (JVM, no emulator):

- `HomeViewModelTest.kt` — `runTest` + `MainDispatcherRule`, exercising at least one error/edge case, asserting against `HomeUiState`. No `Thread.sleep`, no wall-clock wait.
- `FakeGreetingRepository.kt` — a **fake** (test implementation with test hooks), preferred over a mocking library (TEST §C, PS §F).
- `util/MainDispatcherRule.kt` — swaps `Dispatchers.Main` for a test dispatcher; applied in every ViewModel test.
- One assertion library, used consistently. JVM screenshot tests (Roborazzi) are a SHOULD second layer — offer them, don't force them. MUST NOT scaffold device-matrix CI, retry machinery, or benchmark lanes into a fresh solo project.

## 11. Modularization (only on an explicit trigger)

Scaffold the three-tier taxonomy **only** when the operator names a concrete trigger at creation time (sustained build-time pain, cross-app reuse, enforced visibility boundaries, parallel ownership) and record it (PS §C):

- `:app` (top) → `:feature:*` → `:core:*`; features never depend on other features' implementations; core never depends on feature/app; no cycles.
- Share build config via a `build-logic/` included build of single-responsibility convention plugins; plugin IDs `<project>.<platform>.<module-type>[.<aspect>]`. `buildSrc` is a MAY for very small builds only — never a monolithic one.
- Hilt for DI; `:core:designsystem` split from `:core:ui`; shared test fixtures in `:core:testing` (PS §E/§F).
- Do **not** apply the `:feature:x:api`/`:impl` split to solo or small projects — pure overhead (PS §C).
