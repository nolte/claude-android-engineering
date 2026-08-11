---
name: android-project-scaffold
description: "Scaffolds a new native Android app project conforming to spec/android/project-structure/: Kotlin-DSL Gradle with a version catalog, a root plugins-only build script, KSP not kapt, the Compose BOM, a configuration-cache gradle.properties, a single-module-default layout with a route/content composable split and a designsystem package, an L1-security manifest (explicit android:exported, debuggable=false, no cleartext, minimal permissions), bilingual English-source plus German strings with localeFilters and an in-app language picker, and the minimum viable JVM test suite; then verifies it builds green with ./gradlew build. Invoke when the operator asks to create, scaffold, bootstrap, or generate a new Android app, or start an Android project from scratch. Also handles equivalent German-language requests. Not for Compose UI authoring on an existing app, UX audits, or debugging. Supports resume on re-invocation."
tags: [scaffolding]
phase: design
summary: "Scaffolds a spec-conforming, buildable native Android app project (Gradle catalog, Compose, bilingual, L1 security) and verifies ./gradlew build."
summary_de: "Scaffoldet ein spec-konformes, baubares natives Android-App-Projekt (Gradle-Catalog, Compose, zweisprachig, L1-Security) und verifiziert ./gradlew build."
use_when:
  - "you want to create or scaffold a new Android app project from scratch"
  - "you want a spec-conforming Gradle/Compose baseline that builds green"
  - "you want a bilingual (en source + de) Android project from the first screen"
dont_use_when:
  - situation: "You want to author or restyle Compose UI components in an existing app"
    alternative: android-compose-ui
  - situation: "You want to audit or debug an already-generated Android project"
    alternative: android-project-scaffold
see_also:
  - android-compose-ui
examples:
  - prompt: "Erstelle ein neues Android-App-Projekt namens Notensammler, package de.nolte.notensammler."
    outcome: "Single-module :app scaffold, bilingual en+de, builds green with ./gradlew build."
  - prompt: "Scaffold a new Android app, modularized — we share a design system with a second app."
    outcome: "Modularized :app/:feature/:core layout with a build-logic included build, trigger recorded."
resumable: true
---

# Android Project Scaffold

Generates a new native Android app project that conforms to `spec/android/project-structure/<canonical_language>.md`, with the bilingual, security, and test baselines from `spec/android/localization/`, `spec/android/security/`, and `spec/android/test-automation/` §H folded in from the first screen. The skill proposes the file plan, writes files with per-group operator consent, and verifies the result with `./gradlew build`. It is CLI-first: no Android Studio dependency at any step.

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

Detect the operator's language and reply in it (German for this portfolio's maintainer). Generated file contents — Gradle build scripts, Kotlin sources, manifest, `strings.xml`, comments — are always written in English so tooling and cross-project consistency stay predictable. The app's *user-facing* strings ship bilingual (English source `values/` + German `values-de/`) per `spec/android/localization/`.

## Mechanisms, not versions

The specs fix **mechanisms** (version catalog, Gradle wrapper, Compose BOM, KSP, `localeFilters`), never exact versions. The generated `gradle/libs.versions.toml` pins concrete versions, but the skill resolves the current stable version of each toolchain component **at scaffold time** — AGP, the Gradle wrapper distribution, Kotlin (which also fixes the Compose compiler plugin and the matching KSP suffix), the Compose BOM, AndroidX artifacts. When network research is available, look up current stable versions before writing the catalog; when it is not, pin the newest versions known and record in the report that the operator should refresh them. Never hard-code a version the spec didn't ask for, and never pin a dynamic version (`2.+`).

## Preconditions

Before writing anything:

1. Confirm the working directory is a git repository (`git rev-parse --is-inside-work-tree`); if not, ask the operator whether to `git init` first.
2. Locate the grounding spec at `spec/android/project-structure/<canonical_language>.md` in the target repo, or fall back to the copy shipped by this plugin at `${CLAUDE_PLUGIN_ROOT}/spec/android/project-structure/<canonical_language>.md`. If neither is reachable, stop and ask which spec source to use.
3. Check whether any target path already exists (`settings.gradle.kts`, `app/`, `gradle/`, …). If the tree is non-empty in paths the scaffold touches, report the collisions and treat every one as an explicit per-file confirmation gate (Hard rules) — never overwrite silently.

## Operations

This skill has one dispatchable operation, `scaffold` (greenfield create), run as the ordered procedure below. Read `references/scaffold-blueprint.md` for the file-by-file blueprint before writing any file. Read `references/verification.md` when running the verify phase or when mapping generated artifacts back to the spec acceptance criteria.

### 1. Confirm parameters (approval gate)

Collect and confirm: app display name, `applicationId` / root package, `minSdk` and `targetSdk`, JVM/Kotlin target, single-module (default) versus modularized (only when a concrete reuse/team-scale/delivery trigger exists at creation time per §C), and the language set (default `en` source + `de`). Do not make any structural choice the spec doesn't cover — if the operator asks for one, report the gap instead of inventing it. Checkpoint after this gate.

### 2. Present the file plan (approval gate)

Render the full list of files to be written (the blueprint in `references/scaffold-blueprint.md`), grouped by area: root Gradle wiring, `gradle/libs.versions.toml`, `:app` build script and manifest, Kotlin sources (route/content split, designsystem/theme, ViewModel), bilingual resources, and the minimum viable test suite. Confirm the plan before writing. Checkpoint after this gate.

### 3. Write the scaffold

Write files per the confirmed plan and `references/scaffold-blueprint.md`. Resolve current stable versions into `libs.versions.toml` per "Mechanisms, not versions". Generate the Gradle wrapper via `gradle wrapper --gradle-version <current-stable>` (committing `gradle/wrapper/` including the JAR) when a Gradle distribution is reachable; otherwise write the wrapper files and note it in the report. Checkpoint after each area boundary.

### 4. Verify the build (approval gate on failure)

Run the verify loop in `references/verification.md`: `./gradlew build`, then the Spotless/ktlint format check, the JVM unit tests, and the pseudolocale/security-lint checks. A green `./gradlew build` is the success criterion. If the build is red, **report every failure** and propose a fix; never leave a red build unreported or silently patched. Checkpoint after the verify phase; set the run `completed` only on green.

## Examples

Three evaluation scenarios ground the skill's behavior:

- Read `examples/01-solo-single-module-app.md` when scaffolding the default single-module app from scratch.
- Read `examples/02-modularization-requested.md` when the operator requests a modularized project with a concrete trigger.
- Read `examples/03-existing-files-and-red-build.md` when target files already exist or the verify build comes back red.

## Resumability

Per `spec/claude/resumable-work/`, this skill is `resumable: true`. State persists to `.resume/android-project-scaffold/<run-id>.yml` after every approval gate (parameters, file plan, per-conflict overwrite, verify) and after each write-area boundary. On re-invocation, scan that directory for files with `status: in_progress` whose `inputs:` snapshot (target repo path, `applicationId`, module strategy) matches the current invocation; when one matches, prompt `Resume run <run_id> from phase <phase> (last checkpoint <last_checkpoint_at>)? [resume / start-new / discard]`. The state-file envelope and the fail-closed semantics on a schema or YAML error are owned by the spec — don't restate them here. Never re-ask a question whose answer already sits in `decisions:`.

## Hard rules

- **Never** make a structural decision that no `spec/android/` requirement covers. Report the gap and ask; the spec is the only source of structural authority (REQ-6).
- **Never** leave a red `./gradlew build` unreported. A failed verify is surfaced with its full output and a proposed fix, never swallowed (REQ-7).
- **Never** overwrite an existing file without explicit per-file operator confirmation. Merge into existing config rather than replacing wholesale (REQ-8).
- **Never** scaffold an outdated mechanism: no kapt (KSP only), no Groovy DSL (Kotlin DSL only), no monolithic `buildSrc` for build logic when a modularized project needs a `build-logic/` included build, no dynamic versions, no obsolete `gradle.properties` flags (REQ-9).
- **Never** track a secret-bearing file. `local.properties`, release keystores, and `google-services.json` stay out of VCS; base `.gitignore` on GitHub's canonical `Android.gitignore` and add `/.resume/`.
- **Always** default to a single `:app` module. Only modularize when the operator names a concrete trigger at creation time (per project-structure §C), and record the trigger when taken.
- **Always** ship the security L1 baseline from the first manifest: explicit `android:exported` on every component, `debuggable=false` in release, no `usesCleartextTraffic`, minimal permissions.
- When a `spec/android/` file disagrees with this skill, the **spec wins**; propose updating the skill rather than diverging silently.

## Gotchas

Per `skill-management` §Gotchas — concrete corrections to non-obvious facts the executing agent would otherwise get wrong:

- **The Compose compiler is Kotlin-owned, not AGP-owned.** Apply `org.jetbrains.kotlin.plugin.compose` with `version.ref` equal to the Kotlin version; Compose libraries carry no individual versions (BOM-managed). A version pinned on a Compose library is a spec violation.
- **`localeFilters` replaced `resourceConfigurations`.** Use `androidResources { localeFilters += listOf("en", "de") }` (AGP 8.8+); the old `resourceConfigurations` is deprecated and must not be scaffolded.
- **Android 12+ fails the build on a missing `android:exported`.** Every `<activity>`/`<service>`/`<receiver>` needs it explicitly — this is a build-breaker, not a lint warning, so the generated manifest must set it on every component.
- **`./gradlew build` needs a valid wrapper JAR.** `gradle/wrapper/gradle-wrapper.jar` must be committed (it is in GitHub's `Android.gitignore` allowlist, unlike most `*.jar`); generate it with `gradle wrapper`, don't hand-write it.
- **The default `values/` must be complete in the source language.** A string present only in `values-de/` crashes English locales; `MissingTranslation`/`ExtraTranslation` lint stays at error severity as the completeness gate.
