# Verify Loop and Spec Crosswalk

The verify phase (SKILL.md Operation 4). A green `./gradlew build` is the success criterion (REQ-1); everything else is the ordered check sequence and the acceptance-criteria map used to confirm conformance before reporting.

## Table of contents

- [1. Verify sequence](#1-verify-sequence)
- [2. On a red build](#2-on-a-red-build)
- [3. Spec acceptance-criteria crosswalk](#3-spec-acceptance-criteria-crosswalk)

## 1. Verify sequence

Run in order from the generated project root:

1. `./gradlew build` — the load-bearing gate. Compiles, runs lint, assembles debug + release. Must be green.
2. `./gradlew spotlessCheck` (or `ktlintCheck`) — formatting passes on freshly generated code (PS §G, TEST AC).
3. `./gradlew testDebugUnitTest` — the minimum viable JVM suite runs and passes (TEST §H). If product flavors exist, run the variant-aware task, not aggregate `test`.
4. Localization lint gate — confirm `HardcodedText`, `MissingTranslation`, `ExtraTranslation`, `ImpliedQuantity` are at **error** severity and clean (L10N AC). A pseudolocale pass (`en-XA`, `ar-XB`) is a debug-build SHOULD before a translation round.
5. Security lint — confirm `HardcodedDebugMode` is fatal and the exported/`TrustAllX509TrustManager` checks are clean (SEC §F AC).

The wrapper must exist for step 1: generate with `gradle wrapper --gradle-version <current-stable>` if `gradle/wrapper/gradle-wrapper.jar` is absent. If no Gradle distribution is reachable in the environment, report that `./gradlew build` could not be executed here and that the operator must run it — do not claim green without having run it.

## 2. On a red build

Per REQ-7, never leave a red build unreported and never silently patch it:

- Capture the full failing task output (the `> Task :app:… FAILED` block and the error).
- Diagnose against the blueprint: a missing catalog alias, a Compose-BOM/compiler-version mismatch, a kapt residue, a manifest missing `android:exported`, an incomplete `values/` set.
- Propose the specific fix and, at the approval gate, apply it and re-run the verify sequence.
- Only set the resume run `status: completed` once step 1 is green.

## 3. Spec acceptance-criteria crosswalk

Confirm each before reporting success. PS = project-structure, L10N = localization, SEC = security, TEST = test-automation.

| Check | Spec AC |
|---|---|
| `./gradlew build` green immediately after generation | PS |
| Root `build.gradle.kts` is plugins-only `apply false`; no `allprojects`/`subprojects` | PS |
| Every dependency/plugin resolves via `libs.versions.toml`; no hard-coded/dynamic versions | PS |
| `gradle.properties` enables config-cache/build-cache/parallel/AndroidX, no obsolete flags | PS |
| No module applies kapt; KSP only | PS |
| Compose libs BOM-managed (no per-lib versions); compiler plugin references Kotlin version | PS |
| Exactly one `:app` module unless modularization was explicitly requested | PS |
| Unit/instrumented tests in `src/test/` / `src/androidTest/` of the module under test | PS / TEST |
| Spotless/ktlint passes on generated code | PS |
| `git ls-files` shows no `local.properties`, release keystore, or `google-services.json` | PS |
| Package tree separates UI and data; screen code grouped by feature | PS |
| Screen composables split into stateful route + stateless previewable content | PS |
| `localeFilters` matches the supported set; picker changes + persists locale | L10N |
| `values/` complete in source language; `values-de/` carries the same keys | L10N |
| Every component declares `android:exported` (default false) | SEC |
| Release build non-debuggable; no secret committed; no cleartext | SEC |
| Minimal permissions; no persistent hardware identifier | SEC |
| JVM unit tests use `runTest` + `MainDispatcherRule`; fakes over mocks; no `Thread.sleep` | TEST |
| No device-matrix/retry/benchmark CI scaffolded into a fresh solo project | TEST |
| Targeted MAS profile (L1 baseline) recorded with rationale | SEC |
