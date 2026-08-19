# Scaffold Blueprint

The file-by-file plan the `scaffold` operation writes. Every item traces to a `spec/android/project-structure/` (PS), `spec/android/localization/` (L10N), `spec/android/security/` (SEC), `spec/android/test-automation/` (TEST), or `spec/android/release-readiness/` (RR) requirement. This file is a **structural contract**, not a version manifest — resolve concrete versions at scaffold time per SKILL.md "Mechanisms, not versions", and apply the SKILL.md "Spec-derived defaults" (kotlin.test, Spotless+ktlint, `generateLocaleConfig`, BCP-47 dirs, JDK 17 toolchain, `docs/decisions.md`) without re-deciding them.

## Table of contents

- [1. File tree (single-module default)](#1-file-tree-single-module-default)
- [2. Repository root](#2-repository-root)
- [3. Version catalog](#3-version-catalog)
- [4. Settings and root build script](#4-settings-and-root-build-script)
- [5. The :app module build script](#5-the-app-module-build-script)
- [6. Lint configuration](#6-lint-configuration)
- [7. Manifest (L1 security baseline)](#7-manifest-l1-security-baseline)
- [8. Kotlin sources (route/content split)](#8-kotlin-sources-routecontent-split)
- [9. Design system / theme](#9-design-system--theme)
- [10. Bilingual resources](#10-bilingual-resources)
- [11. Minimum viable test suite](#11-minimum-viable-test-suite)
- [12. Taskfile and CI workflow](#12-taskfile-and-ci-workflow)
- [13. Release-readiness baseline](#13-release-readiness-baseline)
- [14. Modularization (only on an explicit trigger)](#14-modularization-only-on-an-explicit-trigger)

## 1. File tree (single-module default)

```
settings.gradle.kts
build.gradle.kts
gradle.properties
lint.xml
Taskfile.yml
.editorconfig
.gitignore
secrets.defaults.properties
renovate.json                                     # SHOULD (SEC §F); ask before writing
docs/decisions.md
.github/workflows/ci.yml
gradle/libs.versions.toml
gradle/wrapper/gradle-wrapper.properties
gradle/wrapper/gradle-wrapper.jar
gradlew
gradlew.bat
app/build.gradle.kts
app/src/release/keepRules/app.keep                # AGP >= 9.3; app/proguard-rules.pro before that
app/src/main/AndroidManifest.xml
app/src/main/res/resources.properties             # unqualifiedResLocale=en (generateLocaleConfig)
app/src/main/kotlin/<pkg>/App.kt
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
app/src/main/res/values-b+de/strings.xml
app/src/main/res/values/themes.xml                # Theme.<App>, parent Theme.AppCompat.DayNight.NoActionBar
app/src/main/res/xml/data_extraction_rules.xml
app/src/debug/kotlin/<pkg>/StrictModeSetup.kt     # installs the policies
app/src/release/kotlin/<pkg>/StrictModeSetup.kt   # no-op
app/src/test/kotlin/<pkg>/ui/home/HomeViewModelTest.kt
app/src/test/kotlin/<pkg>/data/FakeGreetingRepository.kt
app/src/test/kotlin/<pkg>/util/MainDispatcherRule.kt
```

`<pkg>` is the confirmed root package as a path. Kotlin sources live under `kotlin/`, not `java/` (PS §D). The `debug`/`release` source sets exist only because StrictMode needs them (PS §D: variant source sets only when a variant needs them).

## 2. Repository root

- `.gitignore` — based on GitHub's canonical `Android.gitignore` (PS §A [R19]); covers `.gradle/`, `build/`, `local.properties`, `.idea/` subset, `captures/`, `.cxx/`, `*.apk`, `*.aab`, `*.jks`, `*.keystore`, `google-services.json`, `*.hprof`. Add `/.resume/`. The wrapper JAR is **allowlisted** (not ignored).
- `gradle.properties` — MUST enable `org.gradle.configuration-cache=true`, `org.gradle.caching=true`, `org.gradle.parallel=true`, `kotlin.code.style=official`, and a sized `org.gradle.jvmargs` (`-Xmx` plus `-XX:MaxMetaspaceSize`). `android.useAndroidX=true` is written **only on AGP < 9** (AGP 9 defaults it to true; a redundant flag violates PS §B). MUST NOT set obsolete flags: `android.nonTransitiveRClass`, `android.enableJetifier`, `kotlin.incremental`, PNG-crunch flags, and no `android.builtInKotlin=false`/`android.newDsl=false` opt-outs (PS §B).
- `gradle/wrapper/gradle-wrapper.properties` — pin `distributionUrl` to the resolved Gradle version and add `distributionSha256Sum` (PS §B SHOULD; the checksum comes from the Gradle release checksums page); CI additionally runs wrapper validation (§12).
- `.editorconfig` — root formatting + ktlint rule config lives here (PS §G).
- `secrets.defaults.properties` — committed defaults for the `secrets-gradle-plugin` pattern; real keys live in untracked `local.properties` (PS §A, SEC §F).
- `renovate.json` — SHOULD (SEC §F; RR §D makes the *outcome* "dependencies current" a MUST): `extends: ["config:recommended"]` with the gradle manager. Offer it, and mention osv-scanner as the SHOULD vulnerability-scan lane, at the file-plan gate; both are portfolio-level tooling the operator may already centralize.
- `docs/decisions.md` — the record the specs require: MAS profile **L1** with rationale (SEC), `minSdk` with rationale and `targetSdk` (latest stable, or the recorded lag with reason and date — RR §D), the test-naming scheme (PS §F), spec-derived defaults applied, and any modularization trigger (PS §C).

## 3. Version catalog

`gradle/libs.versions.toml` with `[versions]`, `[libraries]`, `[plugins]` (`[bundles]` only if it earns its keep). Rules (PS §B):

- Every dependency and plugin coordinate lives here; module scripts reference `libs.*` accessors only — no hard-coded or dynamic versions.
- Aliases in kebab-case; central versions via `version.ref`.
- Plugins: `android-application` (`com.android.application`), `kotlin-compose` (`org.jetbrains.kotlin.plugin.compose`, `version.ref = "kotlin"`), `ksp` (`com.google.devtools.ksp`, its own version — KSP ≥ 2.3.0 is versioned independently of Kotlin and must be compatible per the KSP compatibility table; only KSP < 2.3.0 uses the Kotlin-prefixed `<kotlin>-<ksp>` scheme), `spotless` (`com.diffplug.spotless`), `foojay-resolver` (`org.gradle.toolchains.foojay-resolver-convention`). **No** `org.jetbrains.kotlin.android` alias on AGP 9 (built-in Kotlin); it would be a Hard-rules violation.
- The `kotlin` version entry exists for the Compose compiler plugin's `version.ref`; Compose libraries carry **no** individual version — they resolve through `platform(libs.androidx.compose.bom)`.
- Libraries: Compose BOM, `androidx.activity:activity-compose`, `androidx.appcompat:appcompat` (alias `androidx-appcompat`; `AppCompatActivity` + the picker's `AppCompatDelegate`), `androidx.lifecycle:lifecycle-viewmodel-compose` + `lifecycle-runtime-compose`, `androidx.core:core-ktx`, Material 3, `ui-tooling-preview` (+ `ui-tooling` on `debugImplementation`); test: `junit:junit` (JUnit 4, TEST §B MUST), `kotlinx-coroutines-test`, `kotlin-test` (`org.jetbrains.kotlin:kotlin-test-junit`).
- Annotation processing uses **KSP** (`com.google.devtools.ksp`). No kapt, no `com.android.legacy-kapt`.

## 4. Settings and root build script

- `settings.gradle.kts` — `pluginManagement { repositories { google { content { … } }; mavenCentral(); gradlePluginPortal() } }`, then `plugins { id("org.gradle.toolchains.foojay-resolver-convention") version "<catalog>" }` (the toolchain resolver; a settings plugin cannot use the catalog alias, so pin the same version string the catalog carries), set `rootProject.name`; declare repositories centrally via `dependencyResolutionManagement` with `RepositoriesMode.FAIL_ON_PROJECT_REPOS` and content filtering (`google()` scoped to `com.android.*`, `androidx.*`, `com.google.*`). Include `:app`. `enableFeaturePreview("TYPESAFE_PROJECT_ACCESSORS")` is a SHOULD. For a modularized project add `pluginManagement { includeBuild("build-logic") }` (§14).
- `build.gradle.kts` (root) — **only** a `plugins {}` block declaring every submodule plugin with `apply false` (`android-application`, `kotlin-compose`, `ksp`, `spotless`). No `allprojects {}` / `subprojects {}`, no `buildscript {}`, no other code (PS §B). Spotless is configured in `:app` (single-module) — a root-level Spotless block would be "other code".

## 5. The :app module build script

`app/build.gradle.kts` applies plugins via `alias(libs.plugins.…)`: Android application, Compose compiler, KSP, Spotless. Key points:

- `applicationId`, `minSdk`, `targetSdk`, `versionCode`, `versionName` live here, not in the manifest (PS §D); `compileSdk` = latest stable, `targetSdk` = latest verified (RR §D).
- `kotlin { jvmToolchain(17); compilerOptions { … } }` — the AGP 9 form; no `kotlinOptions {}`, no `android.kotlinOptions`. `compileOptions` source/target compatibility follow the toolchain.
- `buildFeatures { compose = true }`; add both the Compose BOM and its test-configuration BOM (`platform(libs.androidx.compose.bom)` on `implementation` and `androidTestImplementation`).
- `androidResources { localeFilters += listOf("en", "de"); generateLocaleConfig = true }` (L10N §B/§C) with `res/resources.properties` `unqualifiedResLocale=en`.
- `buildTypes`:
  - `release { isDebuggable = false; optimization { enable = true } }` on AGP ≥ 9.3 — enables code shrinking, optimization, obfuscation, and optimized resource shrinking; keep rules in `src/release/keepRules/app.keep`. On AGP < 9.3: `isMinifyEnabled = true; isShrinkResources = true; proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")` (RR §A [R1]). Never both forms.
  - `debug { isPseudoLocalesEnabled = true }` (L10N §E); no shrinker on debug/test (RR §A).
- `lint { lintConfig = rootProject.file("lint.xml"); abortOnError = true; xmlReport = true; htmlReport = true; checkReleaseBuilds = true }` — severities live in `lint.xml` (§6), reports feed CI artifacts (§12).
- `spotless { kotlin { target("src/**/*.kt"); ktlint(); }; kotlinGradle { target("*.gradle.kts"); ktlint() } }` — the ktlint version pinned through the catalog; rule config in `.editorconfig` (PS §G).
- Debug-only dependencies (`ui-tooling`, later leak detectors) go on `debugImplementation` only (RR §B).
- Prefer `implementation` over `api` (PS §B). Constructor DI; manual DI is fine for a single-module app, Hilt once modularized (PS §E).

## 6. Lint configuration

Root `lint.xml` (PS §G SHOULD "centralize"; the *severities* are MUSTs from L10N §A/§B and SEC §F, and RR §E requires the security checks at error):

```xml
<lint>
  <issue id="HardcodedText" severity="error" />
  <issue id="MissingTranslation" severity="error" />
  <issue id="ExtraTranslation" severity="error" />
  <issue id="ImpliedQuantity" severity="error" />
  <issue id="HardcodedDebugMode" severity="fatal" />
  <issue id="TrustAllX509TrustManager" severity="error" />
  <issue id="ExportedContentProvider" severity="error" />
  <issue id="MissingPermission" severity="error" />
</lint>
```

No `lint-baseline.xml` — new projects start baseline-free (PS §G, RR §E). Once `build-logic/` exists (§14) the same configuration moves into a convention plugin.

## 7. Manifest (L1 security baseline)

`app/src/main/AndroidManifest.xml` (SEC §A/§C/§D/§F):

- `<application android:name=".App" android:theme="@style/Theme.<App>">`: the `android:theme` points at the AppCompat theme from `res/values/themes.xml` (§10) — `MainActivity` is an `AppCompatActivity` (§8) and crashes at startup with "You need to use a Theme.AppCompat theme" without it; `android:allowBackup` set **explicitly**, `android:dataExtractionRules="@xml/data_extraction_rules"`, `android:supportsRtl="true"` (L10N §D), no `android:usesCleartextTraffic` (cleartext stays off), no `android:debuggable` in source (release build sets `false`).
- Every `<activity>`/`<service>`/`<receiver>` declares `android:exported` **explicitly**; the launcher activity is the only `exported="true"`, everything else `false`.
- Request only the minimum permissions in context; a fresh scaffold declares none.
- Add the `autoStoreLocales` metadata service for per-app language persistence below Android 13 (L10N §C).
- Manifest-merge conflicts (a library forcing an attribute) are resolved explicitly with `tools:replace`/`tools:remove` markers, never by weakening a security attribute (PS §D).

## 8. Kotlin sources (route/content split)

Screen-level Compose code MUST split into a stateful route and a stateless content composable (PS §E):

- `App.kt` — the `Application` subclass; `onCreate()` calls `installStrictMode()` (resolved from the `debug`/`release` source set, §13). Nothing else.
- `MainActivity.kt` — an `AppCompatActivity` (the language picker needs `AppCompatDelegate`, and `AppCompatDelegate.setApplicationLocales()` only works below API 33 from an AppCompat activity); calls `setContent { AppTheme { HomeRoute() } }`. It relies on the `android:theme` from §7 — without an AppCompat theme the activity crashes at startup.
- `HomeRoute.kt` — obtains the `HomeViewModel`, collects `uiState` (via `collectAsStateWithLifecycle`), forwards event lambdas to `HomeScreen`.
- `HomeScreen.kt` — stateless `@Composable HomeScreen(uiState: HomeUiState, onEvent lambdas)`; the `@Preview` targets this composable, lives next to it, and is named `HomeScreenPreview`. Add per-locale previews `@Preview(locale = "de")`, an RTL `@Preview(locale = "ar")` (L10N §F), and `@PreviewFontScale` (`androidx.compose.ui.tooling.preview.PreviewFontScale`, singular) — the 200 % font-scale check L10N §E requires.
- `HomeViewModel.kt` — exposes `StateFlow<HomeUiState>`; never hard-codes a dispatcher (injected, for `MainDispatcherRule` in tests). Reaches data only through `GreetingRepository` (PS §E).
- `HomeUiState.kt` — the immutable UI state model.
- `data/GreetingRepository.kt` — named `<DataType>Repository`; UI never touches a data source directly (PS §E).

## 9. Design system / theme

`designsystem/theme/` package (PS §E/§C): `Theme.kt` (the `AppTheme` composable, Material 3, dynamic color where wanted), `Color.kt`, `Type.kt`. This is the single home for theming; once modularized it becomes `:core:designsystem`. Component-level rules (spacing, tokens, specific components) belong to the compose-ui skill's specs — do **not** duplicate them here; scaffold only the theme scaffold and typed accessors.

## 10. Bilingual resources

- `res/values/strings.xml` — the **complete** English source of truth (L10N §B). Every user-visible string externalized (L10N §A); positional placeholders (`%1$s`); `<plurals>` with an `other` case for counts; `translatable="false"` on the app name/brand tokens; feature-prefixed names (`home_greeting_title`, `common_cancel`).
- `res/values-b+de/strings.xml` — German translation in a BCP-47 directory (L10N §B SHOULD), carrying the **same key set** (L10N §E). Draft translations are acceptable transiently; note in the report that visible strings need human review.
- `res/values/themes.xml` — `<style name="Theme.<App>" parent="Theme.AppCompat.DayNight.NoActionBar" />`, referenced by `android:theme` on `<application>` (§7). It only satisfies the `AppCompatActivity` requirement (window background, no action bar); all Compose theming still comes from `MaterialTheme` via `AppTheme` in `designsystem/theme/` (§9) — do not add Material colors or attributes here.
- `res/resources.properties` — `unqualifiedResLocale=en`, paired with `generateLocaleConfig = true` (L10N §C); AGP generates the locale config, so no `locales_config.xml` and no `android:localeConfig` attribute is written.
- `ui/language/LanguagePicker.kt` — in-app picker calling `AppCompatDelegate.setApplicationLocales()`/`getApplicationLocales()`, offering "system default" (`emptyLocaleList`) (L10N §C).

## 11. Minimum viable test suite

TEST §H — the solo-developer floor, in `app/src/test/` (JVM, no emulator):

- `HomeViewModelTest.kt` — JUnit 4, `runTest` + `MainDispatcherRule`, exercising at least one error/edge case, asserting against `HomeUiState` with `kotlin.test` (`assertEquals`, `assertIs`). No `Thread.sleep`, no wall-clock wait. Test names follow the recorded scheme (`` fun `emits greeting when repository succeeds`() ``).
- `FakeGreetingRepository.kt` — a **fake** (test implementation with test hooks), preferred over a mocking library (TEST §C, PS §F).
- `util/MainDispatcherRule.kt` — swaps `Dispatchers.Main` for a test dispatcher; applied in every ViewModel test.
- One assertion library (`kotlin.test`), used consistently. JVM screenshot tests (Roborazzi) are a SHOULD second layer — offer them, don't force them. MUST NOT scaffold device-matrix CI, retry machinery, or benchmark lanes into a fresh solo project.

## 12. Taskfile and CI workflow

TEST §H MUST: one CI workflow running the single-variant unit tests plus lint, with Gradle caching and XML artifacts; TEST §G: CI goes through the same entry points as local runs and `task check` passes locally and in CI on the first run.

`Taskfile.yml` (version 3):

| Task | Command | Purpose |
|---|---|---|
| `check` | deps `lint`, `test` | the aggregate gate CI runs |
| `lint` | `./gradlew lintDebug spotlessCheck` | Android Lint (one variant) + formatting |
| `test` | `./gradlew testDebugUnitTest` | exactly one debug variant, never `test` |
| `format` | `./gradlew spotlessApply` | convenience, not a gate |
| `build` | `./gradlew build` | the REQ-1 criterion (assembles release with the shrinker) |

`.github/workflows/ci.yml`:

- Triggers: `pull_request` and `push` to the default branch; `permissions: contents: read`; a `concurrency` group per ref with `cancel-in-progress`.
- One job on `ubuntu-latest`: `actions/checkout`, `actions/setup-java` (Temurin 17), `gradle/actions/wrapper-validation` (PS §B SHOULD), `gradle/actions/setup-gradle` (Gradle caching; on PRs `cache-read-only`), a Task installer (`arduino/setup-task`), then `task check`.
- Artifacts, `if: ${{ !cancelled() }}`: `app/build/test-results/testDebugUnitTest/*.xml` and `app/build/reports/lint-results-debug.xml` (+ `.html`); a JUnit report action for PR annotations is a SHOULD.
- Pin every action to a full commit SHA with a version comment (portfolio `github-actions-best-practices` spec inherited from `nolte-shared`), and resolve current major versions at scaffold time.
- **No** device matrix, emulator job, retry, coverage gate, or benchmark lane (TEST §H MUST NOT). Since no emulator job exists, no KVM step is written.

## 13. Release-readiness baseline

Greenfield subset of `spec/android/release-readiness/`; the per-change gate (§E) is owned by `android-feature-implement`.

- **Shrinker on release only** with optimization and resource shrinking (§5); keep rules specific and located per AGP generation — `src/release/keepRules/*.keep` on AGP ≥ 9.3, `proguard-rules.pro` before (RR §A). The scaffold ships an empty, commented keep file: no blanket `-keep class ** { *; }`, no `-dontobfuscate`/`-dontoptimize`.
- **`mapping.txt`** — note in `docs/decisions.md` that every release build leaving the machine retains `app/build/outputs/mapping/release/mapping.txt` (RR §A); release *publishing* stays out of scope.
- **StrictMode in debug only** (RR §B): `src/debug/.../StrictModeSetup.kt` sets a `ThreadPolicy` with `detectDiskReads/Writes` + `detectNetwork` and a `VmPolicy` with `detectLeakedClosableObjects` + `detectActivityLeaks` (leak detection), both `penaltyLog()`; `src/release/.../StrictModeSetup.kt` is a no-op. A violation is **fixed, never suppressed** — record that wording in the generated file's comment.
- **Currency** (RR §D): `compileSdk`/`targetSdk` at the latest stable, `minSdk` with rationale recorded; dependencies via the catalog and kept current (Renovate SHOULD, §2).
- **16 KB page size** — the scaffold has no native code, but the first native dependency (ML Kit, SQLCipher, …) must ship 16 KB-aligned `.so` files (Play requirement since 2025-11-01 for targetSdk ≥ 35 submissions, for all app updates from 2027-02-01); note it in `docs/decisions.md` as a checklist item and verify with the AGP/`zipalign -c -P 16` check when a native dependency lands (RR §D).
- **No development affordance in release** (RR §B): debug deps on `debugImplementation`, no non-production endpoint or hidden developer screen; the scaffold has none, the record says so.

## 14. Modularization (only on an explicit trigger)

Scaffold the three-tier taxonomy **only** when the operator names a concrete trigger at creation time (sustained build-time pain, cross-app reuse, enforced visibility boundaries, parallel ownership) and record it (PS §C):

- `:app` (top) → `:feature:*` → `:core:*`; features never depend on other features' implementations; core never depends on feature/app; no cycles.
- Share build config via a `build-logic/` included build of single-responsibility convention plugins; plugin IDs `<project>.<platform>.<module-type>[.<aspect>]`. `buildSrc` is a MAY for very small builds only — never a monolithic one. Lint (§6) and Spotless (§5) configuration move into convention plugins.
- Hilt for DI; `:core:designsystem` split from `:core:ui`; shared test fixtures in `:core:testing` (PS §E/§F).
- Do **not** apply the `:feature:x:api`/`:impl` split to solo or small projects — pure overhead (PS §C).
- `Taskfile.yml`/CI stay unchanged in shape: `lintDebug`/`testDebugUnitTest` aggregate across modules; still one variant.
