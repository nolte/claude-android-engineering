---
name: android-project-scaffold
description: "Scaffolds a new native Android app project conforming to spec/android/project-structure/ (localization, security, test-automation and release-readiness baselines folded in): Kotlin-DSL Gradle with a version catalog, a root plugins-only build script, AGP 9 built-in Kotlin, KSP not kapt, the Compose BOM, a JDK 17 toolchain, a single-module-default layout with a route/content composable split, an L1-security manifest, a shrunk release build, StrictMode in debug, bilingual English-source plus German (values-b+de) strings with localeFilters and a language picker, the minimum JVM test suite, plus a Taskfile and one CI workflow so task check passes locally and in CI; then verifies ./gradlew build is green. Invoke when the operator asks to create, scaffold, bootstrap, or generate a new Android app. Also handles equivalent German-language requests. Not for Compose UI authoring, UX audits, or debugging. Supports resume on re-invocation."
tags: [scaffolding]
phase: design
summary: "Scaffolds a spec-conforming, buildable native Android app project (Gradle catalog, Compose, bilingual, L1 security, CI + Taskfile) and verifies ./gradlew build."
summary_de: "Scaffoldet ein spec-konformes, baubares natives Android-App-Projekt (Gradle-Catalog, Compose, zweisprachig, L1-Security, CI + Taskfile) und verifiziert ./gradlew build."
use_when:
  - "you want to create or scaffold a new Android app project from scratch"
  - "you want a spec-conforming Gradle/Compose baseline that builds green locally and in CI"
  - "you want a bilingual (en source + de) Android project from the first screen"
dont_use_when:
  - situation: "You want to author or restyle Compose UI components in an existing app"
    alternative: android-compose-ui
  - situation: "You want to debug a failing build, install, or runtime defect in an existing Android project"
    alternative: android-debugging
  - situation: "You want to audit the UI/UX of an existing Android app"
    alternative: android-ux-reviewer
  - situation: "You want the tests or CI wiring of an existing Android project audited or completed"
    alternative: android-test-suite-apply
  - situation: "You want an existing project's toolchain, AGP, Kotlin, or targetSdk raised"
    alternative: android-toolchain-upgrade
see_also:
  - android-compose-ui
  - android-permissions-derive
  - android-debugging
  - android-ux-reviewer
  - android-test-suite-apply
  - android-security-reviewer
examples:
  - prompt: "Erstelle ein neues Android-App-Projekt namens Notensammler, package de.nolte.notensammler."
    outcome: "Single-module :app scaffold, bilingual en+de, CI workflow + Taskfile, builds green with ./gradlew build and task check."
  - prompt: "Scaffold a new Android app, modularized — we share a design system with a second app."
    outcome: "Modularized :app/:feature/:core layout with a build-logic included build, trigger recorded."
resumable: true
---

# Android Project Scaffold

Generates a new native Android app project that conforms to `spec/android/project-structure/<canonical_language>.md`, with the bilingual, security, test, and release baselines from `spec/android/localization/`, `spec/android/security/`, `spec/android/test-automation/` §G/§H, and `spec/android/release-readiness/` §A/§B/§D folded in from the first screen. The skill proposes the file plan, writes files with per-group operator consent, and verifies the result with `./gradlew build` and `task check`. It is CLI-first: no Android Studio dependency at any step.

## Why this is a skill, not an agent

- **Per-group user approval is the contract.** The operator confirms scaffold parameters, then the file plan, then each existing-file conflict; a scaffold is a sequence of approval gates that an agent's fire-and-forget shape can't carry.
- **A persistent on-disk artifact stays in the working copy.** The output is the project tree itself, not a structured report consumed once — it flows into the main conversation so the operator sees each write and the build result.
- **Resumable across gates.** A greenfield scaffold spans distinct phases (parameters → plan → write → verify) with intermediate state worth preserving on interruption; per `spec/claude/resumable-work/` that belongs to a `resumable: true` skill.
- Counter-dimension considered: a narrow agent would gain context-window protection while emitting many Gradle/Kotlin files, but the load-bearing part is the per-group approval dialogue and the in-context build verification, not the boilerplate volume; skill wins.

## German trigger phrases

Respond to these (and equivalents) exactly as to their English counterparts; the frontmatter `description` stays English-only per `skill-management` §Structure:

- "Erstelle ein neues Android-Projekt", "Scaffolde eine Android-App", "Lege ein Android-App-Projekt an"
- "Richte ein Android-Projekt ein", "Bootstrappe eine neue Android-App", "Generiere ein Android-Grundgerüst"
- "Neue Android-App von Grund auf", "zweisprachiges (de/en) Android-Projekt aufsetzen"

## User-language policy

Detect the operator's language and reply in it (German for this portfolio's maintainer). Generated file contents — Gradle build scripts, Kotlin sources, manifest, `strings.xml`, comments — are always written in English so tooling and cross-project consistency stay predictable. The app's *user-facing* strings ship bilingual (English source `values/` + German `values-b+de/`) per `spec/android/localization/`.

## Mechanisms, not versions

The specs fix **mechanisms** (version catalog, Gradle wrapper, Compose BOM, KSP, `localeFilters`, built-in Kotlin), never exact versions. The generated `gradle/libs.versions.toml` pins concrete versions, but the skill resolves the current stable version of each toolchain component **at scaffold time** — AGP, the Gradle wrapper distribution, Kotlin (which also fixes the Compose compiler plugin), KSP (versioned independently of Kotlin since KSP 2.3.0 — check that the release's supported Kotlin range per the KSP compatibility table covers the chosen Kotlin; the Kotlin-prefixed `<kotlin>-<ksp>` scheme applies only to KSP < 2.3.0), the Compose BOM, AndroidX artifacts, and the CI actions. When network research is available (REQ-5), look up current stable versions before writing the catalog; when it is not, pin the newest versions known and record in the report that the operator should refresh them. Never hard-code a version the spec didn't ask for, and never pin a dynamic version (`2.+`).

Reference point recorded 2026-08 — **verify at run time, never copy blindly**: AGP 9.3.1 (needs Gradle ≥ 9.5, JDK 17), Gradle 9.7.0, Kotlin 2.4.10, KSP 2.3.11, Compose BOM 2026.08.00, `gradle/actions/setup-gradle` v6. AGP 9 ships **built-in Kotlin**: `org.jetbrains.kotlin.android` is not applied (it is incompatible with the AGP 9 DSL), the Kotlin Gradle plugin arrives with AGP, and `kotlinOptions {}` becomes `kotlin { compilerOptions {} }`.

## Spec-derived defaults

Choices the specs leave to a SHOULD or a working default; each is applied as-is and recorded in the report, never re-decided silently (REQ-6):

- **Assertion library:** `kotlin.test`, used consistently (test-automation §B SHOULD; the spec's Open Question names it the working default).
- **Formatter:** Spotless with ktlint, rules in `.editorconfig` (project-structure §G SHOULD); catalog alias `spotless`, tasks `spotlessCheck`/`spotlessApply`.
- **Locale config:** `generateLocaleConfig = true` + `resources.properties` (localization §C, first-named mechanism, AGP 8.1+); no hand-written `locales_config.xml`.
- **Resource directories:** BCP-47 qualifiers for new dirs (`values-b+de/`), localization §B SHOULD.
- **Test naming:** one scheme repo-wide — `` `<unit> <condition> <expected>` `` backtick names (project-structure §F: the scheme is free, mixing is not).
- **Toolchain:** `kotlin { jvmToolchain(17) }` plus the foojay resolver in `settings.gradle.kts` (AGP 9 minimum JDK; a toolchain, not the ambient JDK).
- **Decision record:** `docs/decisions.md` in the target project holds the MAS profile (L1) with rationale, the `minSdk` rationale, the test-naming scheme, any modularization trigger, and any recorded deviation (project-structure §A `docs/`; release-readiness §D/§F).
- **Logging facade:** scaffolded per `spec/android/logging/` §A — a platform-free `Logger` interface plus an `AndroidLogger` implementation under `core/logging/`, a package boundary rather than a Gradle module because §C keeps a fresh project single-module. Exposed as an injected dependency (§A SHOULD), recorded in `docs/decisions.md`. Its release behaviour is stated as §G requires: `AndroidLogger` answers `isLoggable` from `BuildConfig.DEBUG` and guards its platform calls the same way, because the shrinker rule matches `android.util.Log` and never a facade.
- **`build-logic/`:** only on modularization (project-structure §C MUST single-module; the spec's Open Question stays open — report it, don't pre-scaffold).

## Preconditions

Before writing anything:

1. Confirm the working directory is a git repository (`git rev-parse --is-inside-work-tree`); if not, ask the operator whether to `git init` first.
2. Locate the grounding spec at `spec/android/project-structure/<canonical_language>.md` in the target repo, or fall back to the copy shipped by this plugin at `${CLAUDE_PLUGIN_ROOT}/spec/android/project-structure/<canonical_language>.md`. If neither is reachable, stop and ask which spec source to use.
3. Check whether any target path already exists (`settings.gradle.kts`, `app/`, `gradle/`, `Taskfile.yml`, `.github/workflows/`, …). If the tree is non-empty in paths the scaffold touches, report the collisions and treat every one as an explicit per-file confirmation gate (Hard rules) — never overwrite silently.

## Operations

This skill has one dispatchable operation, `scaffold` (greenfield create), run as the ordered procedure below. Read `references/scaffold-blueprint.md` for the file-by-file blueprint before writing any file. Read `references/verification.md` when running the verify phase or when mapping generated artifacts back to the spec acceptance criteria.

### 1. Confirm parameters (approval gate)

Collect and confirm: app display name, `applicationId` / root package, `minSdk` (with its rationale, release-readiness §D) and `targetSdk` (latest stable), single-module (default) versus modularized (only when a concrete reuse/team-scale/delivery trigger exists at creation time per §C), and the language set (default `en` source + `de`). Do not make any structural choice the spec doesn't cover — if the operator asks for one, report the gap instead of inventing it. Checkpoint after this gate.

### 2. Present the file plan (approval gate)

Render the full list of files to be written (the blueprint in `references/scaffold-blueprint.md`), grouped by area: root Gradle wiring, `gradle/libs.versions.toml`, `:app` build script, lint config and manifest, Kotlin sources (route/content split, designsystem/theme, ViewModel, StrictMode debug setup), bilingual resources, the minimum viable test suite, and the CI workflow + `Taskfile.yml`. Confirm the plan before writing. Checkpoint after this gate.

### 3. Write the scaffold

Write files per the confirmed plan and `references/scaffold-blueprint.md`. Resolve current stable versions into `libs.versions.toml` per "Mechanisms, not versions". Generate the Gradle wrapper via `gradle wrapper --gradle-version <current-stable>` (committing `gradle/wrapper/` including the JAR) when a Gradle distribution is reachable; otherwise write the wrapper files and note it in the report. Checkpoint after each area boundary.

### 4. Verify the build (approval gate on failure)

Run the verify loop in `references/verification.md`: `./gradlew build`, then `task check` (lint + single-variant unit tests, the same entry point CI runs), the Spotless/ktlint check, and the localization/security lint gates plus the pseudolocale and font-scale checks. A green `./gradlew build` is the success criterion; a green `task check` is the test-automation §G acceptance criterion. If anything is red, **report every failure** and propose a fix; never leave a red state unreported or silently patched. Any check that cannot run in this environment (no device, no Gradle distribution) is named as skipped with its reason (release-readiness §E). Checkpoint after the verify phase; set the run `completed` only on green.

## Examples

Three evaluation scenarios ground the skill's behavior:

- Read `examples/01-solo-single-module-app.md` when scaffolding the default single-module app from scratch.
- Read `examples/02-modularization-requested.md` when the operator requests a modularized project with a concrete trigger.
- Read `examples/03-existing-files-and-red-build.md` when target files already exist or the verify build comes back red.

## Resumability

Per `spec/claude/resumable-work/`, this skill is `resumable: true`. State persists to `.resume/android-project-scaffold/<run-id>.yml` after every approval gate (parameters, file plan, per-conflict overwrite, verify) and after each write-area boundary. On re-invocation, scan that directory for files with `status: in_progress` whose `inputs:` snapshot (target repo path, `applicationId`, module strategy) matches the current invocation; when one matches, prompt `Resume run <run_id> from phase <phase> (last checkpoint <last_checkpoint_at>)? [resume / start-new / discard]`. The state-file envelope and the fail-closed semantics on a schema or YAML error are owned by the spec — don't restate them here. Never re-ask a question whose answer already sits in `decisions:`.

## Hard rules

- **Never** write an `android.util.Log`, `System.out`, `println`, or `printStackTrace` call into generated sources outside `core/logging/` (`spec/android/logging/` §A); application code calls the generated facade.
- **Never** leave the release build without the log-stripping rule: `-maximumremovedandroidloglevel 3` in the keep file this AGP generation uses (`spec/android/logging/` §G), with the `-assumenosideeffects` fallback recorded as a deviation where the option is unrecognised.
- **Never** make a structural decision that no `spec/android/` requirement covers. Report the gap and ask; the spec is the only source of structural authority (REQ-6).
- **Never** leave a red `./gradlew build` or `task check` unreported. A failed verify is surfaced with its full output and a proposed fix, never swallowed (REQ-7).
- **Never** overwrite an existing file without explicit per-file operator confirmation. Merge into existing config rather than replacing wholesale (REQ-8).
- **Never** scaffold an outdated mechanism: no kapt (KSP only), no Groovy DSL (Kotlin DSL only), no `org.jetbrains.kotlin.android` on AGP 9 (built-in Kotlin), no monolithic `buildSrc` for build logic when a modularized project needs a `build-logic/` included build, no dynamic versions, no obsolete `gradle.properties` flags (REQ-9).
- **Never** ship a release build type without the shrinker: `optimization { enable = true }` on AGP ≥ 9.3, else `isMinifyEnabled` + `isShrinkResources` + `proguard-android-optimize.txt`; never enable it for debug/test (release-readiness §A). StrictMode is on in debug only, and a violation is **fixed, never suppressed** (§B).
- **Never** track a secret-bearing file. `local.properties`, release keystores, and `google-services.json` stay out of VCS; base `.gitignore` on GitHub's canonical `Android.gitignore` and add `/.resume/`.
- **Always** default to a single `:app` module. Only modularize when the operator names a concrete trigger at creation time (per project-structure §C), and record the trigger when taken.
- **Always** ship the security L1 baseline from the first manifest: explicit `android:exported` on every component, `debuggable=false` in release, no `usesCleartextTraffic`, minimal permissions.
- **Always** scaffold with an empty permission set — a fresh project declares no permission it has not yet earned. Every later addition goes through `android-permissions-derive` (REQ-20), which derives it from a feature and records the ledger row.
- **Always** scaffold the CI workflow and `Taskfile.yml` (test-automation §H MUST) — single-variant unit tests + lint, Gradle caching, XML artifacts; never a device matrix, retry machinery, or benchmark lane.
- When a `spec/android/` file disagrees with this skill, the **spec wins**; propose updating the skill rather than diverging silently.

## Gotchas

Per `skill-management` §Gotchas — concrete corrections to non-obvious facts the executing agent would otherwise get wrong:

- **AGP 9 owns Kotlin.** Applying `org.jetbrains.kotlin.android` next to `com.android.application` fails on AGP 9; the Compose compiler is still Kotlin-owned — apply `org.jetbrains.kotlin.plugin.compose` with `version.ref` equal to the Kotlin version, and let Compose libraries stay version-less (BOM-managed). Confirm one Kotlin Gradle plugin version resolves with `./gradlew buildEnvironment`.
- **`android.useAndroidX=true` is redundant on AGP 9** (default flipped); writing it violates project-structure §B's no-redundant-flags rule. Write it only on AGP < 9.
- **`localeFilters` replaced `resourceConfigurations`.** Use `androidResources { localeFilters += listOf("en", "de") }` (AGP 8.8+); the old `resourceConfigurations` is deprecated and must not be scaffolded.
- **Keep rules moved on AGP ≥ 9.3.** They live in `src/<variant>/keepRules/*.keep`; `proguardFiles(...)` is the pre-9.3 form. Never both.
- **Android 12+ fails the build on a missing `android:exported`.** Every `<activity>`/`<service>`/`<receiver>` needs it explicitly — this is a build-breaker, not a lint warning, so the generated manifest must set it on every component.
- **`./gradlew build` needs a valid wrapper JAR.** `gradle/wrapper/gradle-wrapper.jar` must be committed (it is in GitHub's `Android.gitignore` allowlist, unlike most `*.jar`); generate it with `gradle wrapper`, don't hand-write it.
- **The default `values/` must be complete in the source language.** A string present only in `values-b+de/` crashes English locales; `MissingTranslation`/`ExtraTranslation` lint is *configured* at error severity in `lint.xml` — a check that is merely "expected" at error severity fails silently.
- **The font-scale preview annotation is singular:** `androidx.compose.ui.tooling.preview.PreviewFontScale` (`@PreviewFontScale`), not `@PreviewFontScales`.
