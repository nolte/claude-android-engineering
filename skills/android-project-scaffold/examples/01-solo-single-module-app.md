# Example 01 — Solo single-module app (the default path)

**Prompt:** "Erstelle ein neues Android-App-Projekt namens Notensammler, package de.nolte.notensammler, minSdk 26."

**Expected behavior:**

1. Preconditions run: git repo confirmed, `spec/android/project-structure/en.md` located, working tree checked for collisions.
2. Parameter gate: skill confirms app name `Notensammler`, `applicationId de.nolte.notensammler`, `minSdk 26`, a sensible current `targetSdk`, single-module (no modularization trigger named), languages `en` + `de`. Checkpoint written to `.resume/android-project-scaffold/<run-id>.yml`.
3. File-plan gate: skill renders the single-module blueprint (one `:app` module) and confirms it.
4. Write phase: catalog with current-stable versions resolved at scaffold time, root plugins-only build script, `:app` script with Compose BOM + KSP, manifest with explicit `android:exported` and `debuggable=false` posture, route/content `HomeScreen` split, designsystem/theme, bilingual `values/` + `values-de/`, `MainDispatcherRule` + fake + ViewModel test.
5. Verify: `./gradlew build` green, Spotless clean, unit test passes. Run set `completed`.

**Pass criteria:** exactly one `:app` module; no kapt, no Groovy DSL; `libs.versions.toml` drives every coordinate; `values/` and `values-de/` share keys; response is in German, generated file contents in English.
