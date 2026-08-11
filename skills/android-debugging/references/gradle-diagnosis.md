# Surface 1 — Gradle build-error diagnosis

Load-triggered from `SKILL.md` when the failing symptom is the build itself (a red `./gradlew …`, a configuration-cache/KSP/dependency-resolution error, or a wrapper/daemon problem). Grounded in `spec/android/project-structure/` §B (Gradle conventions) and `spec/android/test-automation/` §G (CI test tasks). Diagnosis is read-only until a fix is approved.

## Table of contents

- Evidence sources
- Read the failure correctly
- Common failure classes and documented remedies
- Configuration cache and daemon state
- Test-task failures
- Reporting

## Evidence sources

Run the failing task through the committed wrapper (never a system `gradle`) and widen the output deliberately:

- `./gradlew <task> --stacktrace` — the exception chain; the **first** `Caused by:` from the bottom is usually the root.
- `./gradlew <task> --info` — task-level reasoning (why a task ran, what inputs changed); `--debug` only as a last resort (very noisy).
- `./gradlew <task> --scan` — a build scan when one is available; otherwise skip.
- `./gradlew :app:dependencies` / `:app:dependencyInsight --dependency <name>` — for version-conflict and resolution failures.

Always name the **exact failing task** (`:app:compileDebugKotlin`, `:app:processDebugManifest`, `:app:kspDebugKotlin`) and the top message line as the cited evidence.

## Read the failure correctly

- The last line Gradle prints (`BUILD FAILED`) is not the cause; scroll up to the first `* What went wrong:` block and the deepest `Caused by:`.
- A `FAILURE: Build completed with N failures` header means multiple independent failures — diagnose each, don't stop at the first.
- Distinguish **configuration-time** failures (in a `build.gradle.kts`, a plugin apply, the version catalog) from **execution-time** failures (compilation, manifest merge, KSP). Configuration failures reproduce with `./gradlew help`.

## Common failure classes and documented remedies

| Symptom in output | Likely cause | Documented remedy |
|---|---|---|
| `Could not resolve <group:artifact:version>` | Missing/typo'd coordinate, repo not declared, offline | Check `gradle/libs.versions.toml` alias + version; confirm the repo is declared centrally in `settings.gradle.kts` `dependencyResolutionManagement`; retry without `--offline` |
| `Could not find <artifact>` only for one module | `FAIL_ON_PROJECT_REPOS` + a module-level `repositories {}` | Remove the project-level repo block; repositories are declared centrally only (§B) |
| Duplicate class / version conflict | Two versions on the classpath | `./gradlew :app:dependencyInsight --dependency <name>`; pin via the catalog, prefer `implementation` over `api` |
| `Manifest merger failed` | Conflicting attribute across manifests | Read the merger report the message points to; resolve with `tools:replace`/`tools:remove`, never by weakening security attributes |
| `Attribute android:exported ... must be explicitly declared` | Android 12+ build-breaker | Add explicit `android:exported` to every `<activity>`/`<service>`/`<receiver>` (`security` §D) |
| KSP error in `:app:kspDebugKotlin` | Annotation-processor misuse or stale generated code | Read the KSP message; never fall back to kapt (§B: KSP only); `./gradlew clean` if generated sources are stale |
| `Unresolved reference` in `compile…Kotlin` | Missing dependency or wrong import, not a Gradle fault | This is a code defect — locate the symbol, add/fix the dependency or import |
| `Compose compiler` / version mismatch | Compose compiler pinned wrong | Apply `org.jetbrains.kotlin.plugin.compose` with `version.ref` = the Kotlin version; Compose libs carry no individual versions (BOM-managed) |
| `Unsupported class file major version` / JDK error | Toolchain/JDK mismatch | Align the Gradle JDK and the module's `jvmTarget`/`compileOptions`; use the toolchain, not the ambient JDK |
| OutOfMemory / slow GC in build | Undersized daemon heap | Raise `org.gradle.jvmargs` heap and set `-XX:MaxMetaspaceSize` (§B) |

## Configuration cache and daemon state

- When an error looks impossible or references stale state, retry once with `--no-configuration-cache`. If the build then passes, the failure was a stale/invalid cache entry — report that, don't chase the original message.
- A corrupt daemon surfaces as intermittent, non-reproducible failures. `./gradlew --stop` then re-run once; never loop.
- `./gradlew clean` clears build outputs and generated sources; use it for stale-KSP/stale-R-class symptoms, not as a blanket first move (it discards incremental state).
- Never silence a real failure by disabling the configuration cache permanently — the flag stays on in `gradle.properties` (§B); the diagnosis is the stale entry, the fix is invalidating it.

## Test-task failures

- Run exactly one debug variant's task (`./gradlew testDebug`, never the all-variant `test` aggregate) — matches CI (`test-automation` §G) and halves the surface.
- A red `testDebug` is a **test failure**, not necessarily an app defect; apply the boundary in `references/runtime-diagnosis.md` (§Test failure vs app defect) before treating it as a runtime bug.
- JUnit XML under `build/test-results/…/` is the authoritative per-test evidence; cite the failing test class and assertion, not just "tests failed".

## Reporting

State the failing task, the cited root-cause line, the failure class, and the documented remedy. Propose the concrete edit (a catalog version, a manifest attribute, a `gradle.properties` flag) and apply it only behind the `SKILL.md` step 4 approval gate. Re-run the same task to verify green; if still red, report the new output and the next step — never mark complete on a red build.
