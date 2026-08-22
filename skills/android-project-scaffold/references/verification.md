# Verify Loop and Spec Crosswalk

The verify phase (SKILL.md Operation 4). A green `./gradlew build` is the success criterion (REQ-1); a green `task check` is the test-automation §G acceptance criterion; everything else is the ordered check sequence and the acceptance-criteria map used to confirm conformance before reporting.

## Table of contents

- [1. Verify sequence](#1-verify-sequence)
- [2. On a red build](#2-on-a-red-build)
- [3. Skipped checks](#3-skipped-checks)
- [4. Spec acceptance-criteria crosswalk](#4-spec-acceptance-criteria-crosswalk)

## 1. Verify sequence

Run in order from the generated project root:

1. `./gradlew build` — the load-bearing gate. Compiles, runs lint on the single debug variant (`lintDebug` — TEST §H and the blueprint scope lint to one variant; `checkReleaseBuilds` adds only the fatal-only `lintVitalRelease` pass on the release assemble), runs the unit tests, assembles debug + release (release with the shrinker on, RR §A). Must be green.
2. `task check` — the aggregate the CI workflow runs (`lintDebug` + `spotlessCheck` + `testDebugUnitTest`); must pass locally on the first run (TEST §G AC). If Task is not installed, run the underlying Gradle tasks and report that `task check` itself was not exercised.
3. `./gradlew spotlessCheck` — formatting passes on freshly generated code (PS §G, TEST AC). Spotless is applied in `:app` with the ktlint step, so the task exists by construction.
4. `./gradlew testDebugUnitTest` — the minimum viable JVM suite runs and passes (TEST §H). If product flavors exist, run the variant-aware task, not aggregate `test`.
5. Localization lint gate — `lint.xml` sets `HardcodedText`, `MissingTranslation`, `ExtraTranslation`, `ImpliedQuantity` to **error**; confirm the debug lint report (`app/build/reports/lint-results-debug.xml`) is clean of them (L10N AC).
6. Pseudolocale pass (L10N §E MUST) — `isPseudoLocalesEnabled = true` is set in debug; when a device or emulator is attached, install the debug build, switch to `en-XA` and `ar-XB` (`adb shell settings put system system_locales en-XA` or the picker) and check the home screen for clipping/concatenation/RTL mirroring. Without a device, report the pass as skipped-and-due before the first translation round (§3).
7. Font scale — `HomeScreen.kt` carries `@PreviewFontScale`; when a device is attached, additionally set `settings put system font_scale 2.0` and check the screen at 200 % (L10N §E). Otherwise report as skipped.
8. Logging — five sub-checks, because `spec/android/logging/` §G rejects verifying the rule's presence instead of its effect. Report them individually, never step 8 wholesale: only the last needs a device.
   - **§A source** — `grep -rnE --include='*.kt' 'android\.util\.Log|System\.(out|err)|\bprintln?\(|printStackTrace' app/src` returns hits only under `app/src/main/**/core/logging/`. Three details: search `app/src`, not `app/src/main`, because the scaffold also writes `src/debug/` and `src/release/` sources; restrict to `*.kt` so the keep file, which names `android.util.Log` on the fallback path, is not itself a hit; and accept hits only under the **main** facade package, matching the detekt exclusion — the `FakeLogger` under `app/src/test/.../core/logging/` is not exempt, so a `println` there must surface here as it does in the gate.
   - **§G rule** — two parts, because presence alone is what §G rejects. The stripping rule is present where this project keeps it (`app/src/release/keepRules/*.keep` on AGP ≥ 9.3, `app/proguard-rules.pro` below that, or the recorded `-assumenosideeffects` fallback — check the location the project actually uses, not all three); **and** the toolchain was confirmed to recognise it, per blueprint §13: read what the shrinker step reports on a release assemble, or where that is inconclusive, verify by effect with a throwaway direct `Log.d`. Skipping the second part is how an older pinned toolchain passes every sub-check while stripping nothing.
   - **§G effect** — `apkanalyzer dex packages app/build/outputs/apk/release/*.apk` lists no `android.util.Log int v(` or `int d(` referenced-method line. Note the return type is `int`; and `--defined-only` would filter the framework class out entirely and pass regardless. This check alone proves little here, because the facade already guards those calls with `BuildConfig.DEBUG` — it catches a *direct* caller that survived, which is why the rule check above stands beside it.
   - **§H gate** — `docs/decisions.md` records the §A-gate decision: the carrier the operator chose, or the gate as an unmet MUST with its reason and the condition for revisiting. The scaffold does not wire a carrier itself (blueprint §6), so what this check confirms is that the decision was taken and written down, not that a gate runs.
   - **§C content** — exercise the app's major features while watching `adb logcat` and confirm no personal data appears; this is the conformance test the Play criterion itself prescribes.
9. Security lint — `lint.xml` sets `HardcodedDebugMode` fatal and `TrustAllX509TrustManager`/`ExportedContentProvider`/`MissingPermission` to error; confirm the report is clean (SEC §F AC, RR §E).
10. Release artifact — `app/build/outputs/apk/release/` exists from step 1 with `mapping.txt` under `app/build/outputs/mapping/release/` (RR §A); `unzip -l` shows no debug-only classes when in doubt.
11. Repository hygiene — `git ls-files` shows no `local.properties`, keystore, or `google-services.json`; `.github/workflows/ci.yml`, `Taskfile.yml`, `lint.xml`, `docs/decisions.md` are present.

The wrapper must exist for step 1: generate with `gradle wrapper --gradle-version <current-stable>` if `gradle/wrapper/gradle-wrapper.jar` is absent. If no Gradle distribution is reachable in the environment, report that `./gradlew build` could not be executed here and that the operator must run it — do not claim green without having run it.

## 2. On a red build

Per REQ-7, never leave a red build unreported and never silently patch it:

- Capture the full failing task output (the `> Task :app:… FAILED` block and the error).
- Diagnose against the blueprint: a missing catalog alias, a Compose-BOM/compiler-version mismatch, an `org.jetbrains.kotlin.android` application on AGP 9, a kapt residue, a manifest missing `android:exported`, an incomplete `values/` set, a lint error from `lint.xml` (fix the finding — never add a baseline, disable the check, or suppress it: RR §E).
- Propose the specific fix and, at the approval gate, apply it and re-run the verify sequence from step 1.
- Only set the resume run `status: completed` once steps 1 and 2 are green.

## 3. Skipped checks

Any step that cannot run in the current environment (no Gradle distribution, no Task binary, no device or emulator for steps 6–7 and for step 8's `adb logcat` sub-check, no `apkanalyzer` on the `PATH` for step 8's dex sub-check) is named in the final report **with its reason** — an unrunnable check is never treated as green (RR §E). The report lists: step, reason, and what the operator runs to close it.

## 4. Spec acceptance-criteria crosswalk

Confirm each before reporting success. PS = project-structure, L10N = localization, SEC = security, TEST = test-automation, RR = release-readiness.

| Check | Spec AC |
|---|---|
| `./gradlew build` green immediately after generation | PS / RR §E |
| `task check` passes locally; the CI workflow runs the same entry point | TEST §G |
| CI workflow: one debug variant's unit tests + lint, Gradle caching, JUnit XML + lint XML artifacts (`if: !cancelled()`), no device matrix/retry/benchmark lane | TEST §G/§H |
| Root `build.gradle.kts` is plugins-only `apply false`; no `allprojects`/`subprojects`/`buildscript` | PS |
| Every dependency/plugin resolves via `libs.versions.toml`; no hard-coded/dynamic versions | PS |
| `gradle.properties` enables config-cache/build-cache/parallel, no obsolete or redundant flags (`android.useAndroidX` only on AGP < 9) | PS |
| No module applies kapt or `org.jetbrains.kotlin.android` (AGP 9 built-in Kotlin); KSP only; JDK 17 toolchain | PS |
| Compose libs BOM-managed (no per-lib versions); compiler plugin references Kotlin version | PS |
| Exactly one `:app` module unless modularization was explicitly requested | PS |
| Unit/instrumented tests in `src/test/` / `src/androidTest/` of the module under test | PS / TEST |
| Spotless/ktlint passes on generated code; rules in `.editorconfig` | PS |
| `git ls-files` shows no `local.properties`, release keystore, or `google-services.json`; `distributionSha256Sum` present | PS |
| Package tree separates UI and data; screen code grouped by feature | PS |
| Screen composables split into stateful route + stateless previewable content | PS |
| One test-naming scheme, recorded in `docs/decisions.md` | PS §F |
| `localeFilters` matches the supported set; `generateLocaleConfig` + `resources.properties`; picker changes + persists locale | L10N |
| `values/` complete in source language; `values-b+de/` carries the same keys | L10N |
| Lint severities configured (`lint.xml`): `HardcodedText`/`MissingTranslation`/`ExtraTranslation`/`ImpliedQuantity` error | L10N |
| Pseudolocales enabled in debug; en-XA/ar-XB pass run or reported skipped-and-due; `@PreviewFontScale` present | L10N §E |
| Every component declares `android:exported` (default false) | SEC |
| `<application android:theme="@style/Theme.<App>">` points at `res/values/themes.xml` (`Theme.AppCompat.DayNight.NoActionBar`), so the `AppCompatActivity` starts without "You need to use a Theme.AppCompat theme"; Compose theming stays in `AppTheme` | PS / L10N §C |
| Release build non-debuggable; no secret committed; no cleartext; `HardcodedDebugMode` fatal, security checks error | SEC / RR §E |
| Minimal permissions; no persistent hardware identifier | SEC |
| Targeted MAS profile (L1 baseline) recorded with rationale in `docs/decisions.md` | SEC |
| Release: shrinker + resource shrinking + optimization on; keep rules specific and correctly located; none on debug/test | RR §A |
| StrictMode active in debug only (disk, network, leak detection); comment says fix, never suppress | RR §B |
| `compileSdk`/`targetSdk` latest stable, `minSdk` rationale recorded; 16 KB page-size note for native deps | RR §D |
| JVM unit tests use JUnit 4, `runTest` + `MainDispatcherRule`; fakes over mocks; no `Thread.sleep`; `kotlin.test` used consistently | TEST |
| No device-matrix/retry/benchmark CI scaffolded into a fresh solo project | TEST |
| Facade is the only caller of `android.util.Log`; stripping rule present where this AGP generation keeps it; no `int v(`/`int d(` in the release dex; `LogConditional` enabled; the §A-gate decision recorded in `docs/decisions.md` | LOG §A/§G/§H |
