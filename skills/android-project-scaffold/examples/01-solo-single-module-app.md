# Example 01 — Solo single-module app (the default path)

**Prompt:** "Erstelle ein neues Android-App-Projekt namens Notensammler, package de.nolte.notensammler, minSdk 26."

**Expected behavior:**

1. Preconditions run: git repo confirmed, `spec/android/project-structure/en.md` located, working tree checked for collisions.
2. Parameter gate: skill confirms app name `Notensammler`, `applicationId de.nolte.notensammler`, `minSdk 26`, a sensible current `targetSdk`, single-module (no modularization trigger named), languages `en` + `de`. Checkpoint written to `.resume/android-project-scaffold/<run-id>.yml`.
3. File-plan gate: skill renders the single-module blueprint (one `:app` module) and confirms it.
4. Write phase: catalog with current-stable versions resolved at scaffold time (AGP 9 built-in Kotlin — no `org.jetbrains.kotlin.android`), root plugins-only build script, `:app` script with Compose BOM + KSP + Spotless, JDK 17 toolchain, shrunk release build with keep rules, `lint.xml` severities, manifest with explicit `android:exported` and `debuggable=false` posture, `App` with StrictMode in the debug source set, route/content `HomeScreen` split (with `@PreviewFontScale`), designsystem/theme, bilingual `values/` + `values-b+de/`, `MainDispatcherRule` + fake + ViewModel test (`kotlin.test`), `Taskfile.yml` + `.github/workflows/ci.yml`, `docs/decisions.md` (MAS L1, minSdk 26 rationale, naming scheme).
5. Verify: `./gradlew build` green, `task check` green, Spotless clean, unit test passes; pseudolocale/font-scale device passes reported as skipped-and-due when no device is attached. Run set `completed`.

**Pass criteria:** exactly one `:app` module; no kapt, no Groovy DSL; `libs.versions.toml` drives every coordinate; `values/` and `values-b+de/` share keys; CI workflow runs single-variant unit tests + lint only; response is in German, generated file contents in English.
