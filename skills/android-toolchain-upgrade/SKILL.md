---
name: android-toolchain-upgrade
description: "Raises an existing native Android app's toolchain and dependencies to current, compatible versions per spec/android/project-structure/ §B and release-readiness/ §D: inventories Gradle, AGP, Kotlin, KSP, Compose BOM, SDK levels, JDK; researches current versions and the AGP↔Gradle↔Kotlin↔KSP↔Compose coupling at run time; plans an ordered path gated by ./gradlew build per step; handles targetSdk behaviour changes; verifies 16 KB page-size alignment; checks Renovate and osv-scanner; logs the run. Operations: audit (read-only), plan, apply. Invoke to update or bump AGP, Gradle, Kotlin, KSP, Compose, targetSdk, or dependencies, to migrate to AGP 9 built-in Kotlin, or to check toolchain currency. Also handles equivalent German-language requests. Don't use for a new project (android-project-scaffold), a red build (android-debugging), or the full release-readiness audit (android-release-readiness-reviewer). Supports resume on re-invocation."
tags: [dependency, audit, implementation]
phase: build
summary: "Inventories, researches, plans, and applies toolchain and dependency upgrades (Gradle, AGP, Kotlin, KSP, Compose, SDK levels) for an existing Android app with a build gate per step and a recorded log."
summary_de: "Inventarisiert, recherchiert, plant und wendet Toolchain- und Abhängigkeits-Upgrades (Gradle, AGP, Kotlin, KSP, Compose, SDK-Level) einer Android-App an — mit Build-Gate je Schritt und Protokoll."
use_when:
  - "you want AGP, Gradle, Kotlin, KSP, the Compose BOM, or a library raised to a current, compatible version"
  - "you want targetSdk or compileSdk bumped and the activated behaviour changes handled first"
  - "you want to migrate a module set to AGP 9 built-in Kotlin or off kapt"
  - "you want a read-only report on how current the app's toolchain is, with severities"
  - "you want the 16 KB page-size readiness of native dependencies verified on the built artifact"
dont_use_when:
  - situation: "You want a new Android project created from scratch"
    alternative: android-project-scaffold
  - situation: "A build is red for a reason other than an upgrade you are running here, or the app crashes"
    alternative: android-debugging
  - situation: "You want the full release-readiness audit (shrinker, debug leftovers, stability, recording), not only currency"
    alternative: android-release-readiness-reviewer
  - situation: "A targetSdk bump surfaces a permission or foreground-service-type decision"
    alternative: android-permissions-derive
  - situation: "A targetSdk bump surfaces a notification channel or importance decision"
    alternative: android-notification-derive
see_also:
  - android-release-readiness-reviewer
  - android-project-scaffold
  - android-debugging
  - android-permissions-derive
  - android-notification-derive
  - android-test-suite-apply
resumable: true
---

# Android Toolchain Upgrade

Raises an existing native Android app's toolchain and dependencies to current, mutually
compatible versions — and proves it with a green build after every step. It is the executor the
read-only `android-release-readiness-reviewer` routes its §D currency findings to.

The governing idea is that a toolchain is a **coupled matrix**, not a list of independent
numbers: AGP pins a Gradle range and a Kotlin/KSP floor, the Compose compiler plugin and KSP
follow the Kotlin version, the Compose BOM follows the compiler, and a `targetSdk` level
activates behaviour that must be handled *before* the bump. Every version this skill proposes
is therefore researched at run time against its primary source (REQ-5), and every step is gated
by `./gradlew build` so a red state is never carried forward silently (REQ-1, REQ-7).

Grounding specs, in the order they bind this skill: `spec/android/project-structure/` §B (build
mechanics — built-in Kotlin, KGP/KSP floor, JDK 17 toolchain, wrapper, catalog, redundant flags,
dependency verification), `spec/android/release-readiness/` §D (platform and dependency currency
including the dated Play deadlines and 16 KB page size), §E (the gate) and §F (recording),
`spec/android/security/` §F (Renovate/Dependabot and osv-scanner), `spec/android/adb-workflows/`
§A (platform-tools currency), `spec/android/logging/` §G (an AGP move across 9.3 relocates the
log-stripping rule from `proguardFiles` to `src/<variant>/keepRules/*.keep` — carry the rule over
rather than leaving it in a file the newer DSL no longer reads), and `spec/android/screen-formats/` §B/§D plus
`spec/android/app-design-navigation/` §A for the adaptive and edge-to-edge obligations a
`targetSdk` bump activates. On any conflict the spec wins — report the gap and propose a spec
change rather than deciding silently (REQ-6).

## German trigger phrases

Respond to these (and equivalents) exactly as to their English counterparts; the frontmatter
`description` stays English-only per `skill-management` §Structure:

- "Aktualisiere/hebe AGP, Gradle, Kotlin, KSP, Compose an", "Bringe die Abhängigkeiten auf den
  neuesten Stand", "Migriere auf AGP 9 / built-in Kotlin", "Weg von kapt"
- "Erhöhe targetSdk / compileSdk auf 36", "Was ändert sich mit targetSdk 36 für die App?"
- "Ist die Toolchain aktuell?", "Prüfe die 16-KB-Page-Size-Tauglichkeit", "Richte Renovate ein"

## Why this is a skill, not an agent

- **Per-step approval is the contract.** Each version bump, each `gradle.properties` flag change,
  and each behaviour-change fix is an operator decision applied to tracked build files (REQ-8);
  an agent's fire-and-forget shape cannot carry per-item gates.
- **The working tree is the deliverable.** Catalog, wrapper, and manifest edits land in context
  and are reviewed there, with the build output beside them.
- **It composes with sibling capabilities.** Red build → `android-debugging`; full §A–§F audit →
  `android-release-readiness-reviewer`; permission and notification consequences of a
  `targetSdk` bump → `android-permissions-derive` / `android-notification-derive`. Per
  `spec/claude/skill-vs-agent/` §Primary decision rule the orchestrator is a skill.
- Counter-dimension considered: the research phase reads many release-note pages and would suit
  an isolated agent context; it stays here because the coupling matrix it produces is the
  input every following gate is judged against, and the operator must see it in context.

## Boundary vs the sibling capabilities

- `android-release-readiness-reviewer` audits all of `spec/android/release-readiness/` §A–§F
  read-only and routes §D version findings here; it has no `Bash`, so alignment checks that need
  the built artifact (16 KB `.so` alignment) are its "Deferred scope" and this skill's job.
- `android-project-scaffold` creates a project already on the current toolchain (REQ-12); this
  skill starts where a project already exists (REQ-11) and never scaffolds.
- `android-debugging` owns diagnosis of a build that is red for reasons other than the step this
  skill just applied; a red gate here is first reverted or fixed within the step, then routed.
- `android-feature-implement` owns the six-element §E gate for feature work; this skill runs the
  static part of that gate (build, lint, unit tests, release assembly) for its own changes and
  names any element it could not run (device smoke) as skipped, never as green.
- `android-permissions-derive` and `android-notification-derive` own every permission,
  foreground-service-type, and channel decision a `targetSdk` bump surfaces; this skill lists the
  impact and hands the decision over with the behaviour-change citation.

## User-language policy

Detect the operator's language and respond in it (German for this operator). Build files, the
version catalog, the toolchain log, commit-ready text, and every command stay in English.

## Operations

Pick one at the start and say which is running. `audit` **only reports**, `plan` **decides and
records the path**, `apply` **writes** — one approved step at a time.

- **`audit`** — read-only currency report: steps 1–2, then the severity-classified findings
  procedure in `references/verification-and-log.md` §4. Writes nothing. When the operator wants
  more than currency (shrinker, debug leftovers, stability), dispatch
  `android-release-readiness-reviewer` instead and say so; when its report already exists under
  `.audits/android-release-readiness-review/`, take its §D findings as this run's input.
- **`plan`** — steps 1–3: inventory, research with recorded evidence, ordered upgrade path with
  the behaviour-change and page-size items attached. Touches no build file.
- **`apply`** — steps 4–7 on an approved plan. Refuses to start without one; an end-to-end request
  ("update everything") is `plan` then `apply`, run back-to-back with the handover named.

## Preconditions

- Confirm the working directory is a git repository holding an Android project with `gradlew`,
  `gradle/libs.versions.toml`, and at least one module applying `com.android.application` or
  `com.android.library`. Without one, stop and route to `android-project-scaffold`; a project
  without a catalog first gets one (a `plan` item, `project-structure` §B).
- Check for uncommitted changes in build files, wrapper, `gradle.properties`, and manifests. If
  dirty, report and ask whether to stash, commit, or abort — never overwrite unconfirmed work
  (REQ-8).
- Confirm `./gradlew build` is green **before** touching anything, or record the pre-existing red
  state verbatim; an upgrade never starts from an unreported red baseline (REQ-7). A red baseline
  routes to `android-debugging` first.
- Confirm network access for step 2; without it, `plan` still runs but every version is marked
  *unverified* and `apply` refuses to bump past the pinned floors of `project-structure` §B.

## Procedure

Run the steps in order. Confirm with the operator at each gate before writing.

### 1. Inventory the current toolchain

Read `references/inventory-and-research.md` §1 for where each value lives, then record: Gradle
wrapper version and `distributionSha256Sum`, AGP, Kotlin, KSP, Compose BOM, Compose compiler
plugin, `compileSdk`/`targetSdk`/`minSdk` (with the `minSdk` rationale, `release-readiness` §D),
JDK toolchain declaration and resolver, `gradle.properties` flags, whether
`org.jetbrains.kotlin.android` or any kapt plugin is still applied, `useLegacyPackaging`, native
dependencies, Renovate/Dependabot and osv-scanner presence, and the local `platform-tools`
version (`adb --version`, `adb-workflows` §A). Note the effective `targetSdk` (AGP 9 defaults it
to `compileSdk` when unset). Gate: confirm the inventory.

### 2. Research current versions and the coupling matrix (REQ-5)

Read `references/inventory-and-research.md` §2 for the primary sources and the evidence record.
With WebSearch/WebFetch, establish for each inventoried item the current stable version and the
constraints it imposes on its neighbours — AGP↔Gradle range, AGP↔KGP/KSP floor, Kotlin↔Compose
compiler plugin (same version) and Kotlin↔KSP (per the KSP compatibility table — the
`<kotlin>-<ksp>` prefix scheme applies only to KSP < 2.3.0; from 2.3.0 KSP is versioned
independently and each release names its supported Kotlin range), Compose BOM↔compiler, the AGP 9
built-in-Kotlin migration rules, the K2 status of the Kotlin line, `targetSdk` deadlines and the
16 KB page-size dates the release-readiness spec carries. Record every fact with URL and date;
where a source and the spec disagree, the spec wins and the disagreement is reported. Never
carry a version from memory into the plan. Gate: confirm the matrix.

### 3. Plan the upgrade path

Read `references/upgrade-playbook.md` §1 for the canonical order and the per-step content. Lay
the path out as ordered steps — wrapper, AGP, Kotlin line (KGP, KSP, Compose compiler, BOM),
built-in-Kotlin migration and kapt removal, JDK toolchain, `gradle.properties` cleanup,
`compileSdk`/`targetSdk`, then libraries — each with its target version, its evidence row, the
files it touches, and its `./gradlew build` gate. Attach the behaviour-change list for the new
`targetSdk` (`references/upgrade-playbook.md` §2) with each impact routed, and the page-size and
hygiene items of `references/verification-and-log.md` §1–§2. Gate: confirm the plan; `plan`
ends here.

### 4. Apply the toolchain steps

For each approved step: propose the diff, apply after confirmation, run `./gradlew build`, and
stop on red. On red, fix within the step when the cause is the step itself (a removed API, a
renamed flag), otherwise revert the step and route to `android-debugging` with the full output;
never continue on top of a red gate. Checkpoint after every green step. The AGP 9 built-in-Kotlin
migration and the `com.android.legacy-kapt` interim follow `references/upgrade-playbook.md` §1
exactly; a remaining `legacy-kapt` application is recorded with processor, reason, and removal
condition (`project-structure` §B).

### 5. Bump `targetSdk` and handle its behaviour changes

Before raising `targetSdk`, walk the behaviour-changes page for the new level (fetched in step
2) and, per `references/upgrade-playbook.md` §2, resolve every impact: predictive back,
edge-to-edge, orientation and resizability, foreground-service types, permission changes,
notification changes, and the level's remaining items. Permission and foreground-service-type
items are handed to `android-permissions-derive`, channel and importance items to
`android-notification-derive`, screen-format items are fixed here per `screen-formats` §B/§D.
The bump itself is applied only when every impact is resolved or recorded as an interim per
`release-readiness` §F, then gated by `./gradlew build`.

### 6. Verify 16 KB page size and dependency hygiene

Per `references/verification-and-log.md` §1: `useLegacyPackaging = false`, then the alignment
check on the built release APK/AAB (`check_elf_alignment.sh` or `zipalign -c -P 16 -v 4`) for
every native library, and a boot on a 16 KB emulator image where one is available. Per §2:
Renovate (or Dependabot) configuration present and osv-scanner run against the lockfile or the
resolved graph — both SHOULD (`security` §F), so their absence is a Warning offered as a step, not
a silent addition; dependency verification metadata is refreshed, never disabled.

### 7. Close on the gate and record the run

Run `./gradlew build` (which already runs lint and the unit tests through `check` — do not
invoke them again separately) and the release assembly; name any element that could not run
and why (`release-readiness` §E). Update the local `platform-tools`
when the inventory found it behind (`adb-workflows` §A). Write the run into
`project/toolchain-log.md` from the template in `references/verification-and-log.md` §3 — one
dated entry per run with the before/after matrix, evidence URLs, interims, and skipped elements.
No spec names this file; report it as a spec gap with a proposed extension (REQ-6) alongside the
report. Report, in the operator's language: versions before and after, steps applied and
gated, behaviour changes handled and handed over, page-size and hygiene results, interims
recorded, and every red or skipped element (REQ-7).

## Reference files

- `references/inventory-and-research.md` in steps 1–2 — where each version lives, the primary
  sources per component, and the evidence-record format.
- `references/upgrade-playbook.md` in steps 3–5 — the canonical upgrade order with per-step
  content and gates, the built-in-Kotlin migration, and the `targetSdk` behaviour-change walk.
- `references/verification-and-log.md` in steps 6–7 and for `audit` — 16 KB page-size checks,
  Renovate and osv-scanner, the toolchain-log template, and the read-only audit procedure.

## Resumability

Per `spec/claude/resumable-work/`, this skill is `resumable: true`. State is persisted to
`.resume/android-toolchain-upgrade/<run-id>.yml` after every gate and after each green build in
step 4. On re-invocation, scan `.resume/android-toolchain-upgrade/*.yml` for files with
`status: in_progress` whose `inputs:` snapshot (repository + operation + inventory hash) matches
the current request; when one matches, prompt
`Resume run <run_id> from phase <phase> (last checkpoint <last_checkpoint_at>)? [resume / start-new / discard]`.
`resume` re-hydrates the evidence matrix and re-asks no answered gate; `start-new` leaves the
old file intact; `discard` deletes it. Fail closed on unparseable or higher-`schema_version`
files. Never redo the research of step 2 whose result already sits in `state:`. Ensure
`/.resume/` is gitignored in the target project.

## Hard rules

- **Never** carry a version, deadline, or compatibility claim from memory into the plan; every
  value has an evidence row with URL and date, or is marked *unverified* and not applied.
- **Never** apply a step on top of a red gate, and **never** leave the run with a red build,
  lint, or test state unreported (REQ-1, REQ-7).
- **Never** bump `targetSdk` before every activated behaviour change is resolved or recorded as
  a dated interim with its removal condition (`release-readiness` §D/§F).
- **Never** apply `org.jetbrains.kotlin.android` or `org.jetbrains.kotlin.kapt` on AGP 9, never
  set `android.builtInKotlin=false` or `android.newDsl=false` except as a dated, recorded
  interim, and **never** introduce kapt where none was (REQ-9, `project-structure` §B).
- **Never** use a dynamic version, add a Compose library version beside the BOM, or write a
  coordinate outside the catalog.
- **Never** downgrade Gradle wrapper integrity: keep or add `distributionSha256Sum`, refresh
  `gradle/verification-metadata.xml` on a bump, and never disable verification to go green.
- **Never** add or refresh a lint baseline, disable a check, or annotate a suppression to pass
  the closing gate (`release-readiness` §E).
- **Never** overwrite or delete anything without operator confirmation, and **never** write in
  `audit` (REQ-8).
- **Always** report a convention no spec covers as a gap with a proposed extension instead of
  deciding silently (REQ-6); the toolchain-log location is spec-fixed
  (`spec/android/release-readiness/` §F), not a gap.
- When a `spec/android/` file disagrees with this skill, the spec wins.

## Gotchas

- **`org.jetbrains.kotlin.android` breaks AGP 9 with the new DSL** — remove it rather than
  pinning `android.newDsl=false`; the KGP still exists in the catalog for the Compose plugin.
- **KSP and the Compose compiler plugin follow Kotlin, not AGP.** A Kotlin bump without a
  compatible KSP (Kotlin-prefixed only below KSP 2.3.0; independently versioned from 2.3.0 —
  check the release's supported Kotlin range) and `org.jetbrains.kotlin.plugin.compose`
  (same version as Kotlin) is a red build.
- **AGP 9 defaults `targetSdk` to `compileSdk`.** Raising `compileSdk` on a project that never
  set `targetSdk` silently bumps the effective `targetSdk` — a behaviour-change walk is due.
- **`useLegacyPackaging = false` is not alignment.** A prebuilt `.so` from a dependency can still
  be 4 KB aligned; only the artifact check on the release build proves 16 KB readiness.
- **The configuration cache turns a stale state into a confusing failure.** After a plugin bump,
  retry once with `--no-configuration-cache` before treating the error as the upgrade's fault.
