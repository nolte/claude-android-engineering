# Inventory and Research

Where each toolchain value lives in a `spec/android/project-structure/`-conforming project, the
primary sources that settle its current version and coupling (REQ-5), and the evidence record
every plan and log entry carries. Deadline and page-size *values* are owned by
`spec/android/release-readiness/` §D; this file names where to re-verify them, never their numbers.

## Table of contents

- [1. Inventory: where each value lives](#1-inventory-where-each-value-lives) — file and key
  per component, plus the drift signals to note
- [2. Research: primary sources and the coupling matrix](#2-research-primary-sources-and-the-coupling-matrix)
  — source per component, the coupling rules to extract, the evidence-record format
- [3. Reading the AGP 9 built-in-Kotlin state](#3-reading-the-agp-9-built-in-kotlin-state) —
  the four signals that classify a project as migrated, mid-migration, or legacy

---

## 1. Inventory: where each value lives

Read files; do not infer. Where a value is absent, record *unset* and the effective default that
applies for the AGP generation in use (`project-structure` §B lists AGP 9's `true` defaults).

| Component | Where | Drift signal to note |
|---|---|---|
| Gradle wrapper | `gradle/wrapper/gradle-wrapper.properties` → `distributionUrl`, `distributionSha256Sum` | missing checksum (§B SHOULD); `-bin` vs `-all` |
| AGP | `gradle/libs.versions.toml` `[versions]` referenced by `com.android.application` / `com.android.library` (`[plugins]`) | inline version in a build file (§B MUST catalog) |
| Kotlin (KGP) | `[versions]` referenced by `org.jetbrains.kotlin.plugin.compose`, `org.jetbrains.kotlin.jvm`, and — legacy — `org.jetbrains.kotlin.android` | `org.jetbrains.kotlin.android` applied in any module on AGP ≥ 9 |
| KSP | `[versions]` referenced by `com.google.devtools.ksp` | release's supported Kotlin range excludes the project's Kotlin (KSP < 2.3.0: prefix ≠ Kotlin version) |
| kapt | any `org.jetbrains.kotlin.kapt` / `kotlin("kapt")` / `com.android.legacy-kapt` application, any `kapt(...)` dependency | present at all (§B, REQ-9) |
| Compose BOM | `[libraries]` `androidx.compose:compose-bom` version, `platform(libs.androidx.compose.bom)` in modules and test configurations | Compose artefact with an individual version |
| Compose compiler | `org.jetbrains.kotlin.plugin.compose` `version.ref` | ≠ Kotlin `version.ref`; the legacy `composeOptions.kotlinCompilerExtensionVersion` still present |
| `compileSdk` / `targetSdk` / `minSdk` | app module `android { }` or the `build-logic/` convention plugin | `targetSdk` unset on AGP 9 (defaults to `compileSdk`); `minSdk` without a rationale comment or `project/` record (`release-readiness` §D) |
| JDK toolchain | `java { toolchain { languageVersion } }` or `kotlin { jvmToolchain(…) }` once; `org.gradle.toolchains.foojay-resolver-convention` in `settings.gradle.kts` | scattered `sourceCompatibility`/`jvmTarget`; no resolver |
| `gradle.properties` | configuration cache, build cache, parallel, `jvmargs`; AGP 9 redundant flags (`android.useAndroidX`, `android.builtInKotlin`, `android.newDsl`, `android.r8.strictFullModeForKeepRules`, `android.proguard.failOnMissingFiles`, `android.sdk.defaultTargetSdkToCompileSdkIfUnset`), obsolete flags (`android.nonTransitiveRClass`, `android.enableJetifier`, `kotlin.incremental`) | a redundant flag set to its default; an opt-out (`android.builtInKotlin=false`, `android.newDsl=false`) without a dated record |
| Native packaging | `packaging { jniLibs { useLegacyPackaging } }` in the app module | `true`, or unset on AGP < 8.5.1 |
| Native dependencies | `src/*/jniLibs/**/*.so`; dependencies known to bundle native code (SQLCipher, Realm, image codecs, ML Kit bundled models, Play Core, media/ExoPlayer extensions, Rust/Go bindings) | any hit → 16 KB verification is due (`verification-and-log.md` §1) |
| Dependency verification | `gradle/verification-metadata.xml`; `dependencyLocking` in `settings.gradle.kts`/modules | absent (§B SHOULD) |
| Update automation and scanner | `renovate.json*`, `.renovaterc*`, `.github/renovate.json5`, `.github/dependabot.yml`; an `osv-scanner` step in `.github/workflows/*.yml` or the Taskfile | absent (`security` §F SHOULD) |
| platform-tools | `adb --version` on the operator machine; `which -a adb` for duplicates | more than one adb; version behind the current release (`adb-workflows` §A) |
| Local JDK | `java -version`, `JAVA_HOME`, `./gradlew --version` | below the declared toolchain, resolver absent |

Also record: `./gradlew --version` (Gradle, JVM, OS), the module list from `settings.gradle.kts`,
and whether a `build-logic/` included build exists — the convention plugin is where several of
the values above are set once.

## 2. Research: primary sources and the coupling matrix

Fetch the sources with WebFetch (WebSearch only to locate a moved page); read the release notes
of the *target* version, not only the index. Every fact enters the evidence record below.

| Component | Primary source | Coupling facts to extract |
|---|---|---|
| AGP | AGP release notes (`developer.android.com/build/releases/gradle-plugin`) and the version-specific page (`…/agp-<major>-<minor>-<patch>-release-notes`) | required Gradle range; minimum JDK; KGP and KSP floor; new `true` defaults and removed properties; deprecations that turn into errors; built-in-Kotlin notes; minimum `compileSdk`/build-tools |
| Gradle | Gradle releases page and the compatibility matrix (`docs.gradle.org/current/userguide/compatibility.html`) | JDK compatibility; Kotlin DSL embedded Kotlin version; wrapper checksum for `distributionSha256Sum` |
| Kotlin | Kotlin releases (`kotlinlang.org/docs/releases.html`) and the "what's new" page of the target line | K2 status; deprecation cycle; Gradle range KGP supports; language-version defaults |
| Compose compiler plugin | Compose-Kotlin compatibility map (`developer.android.com/jetpack/androidx/releases/compose-kotlin`) | plugin version = Kotlin version since Kotlin 2.0; pre-2.0 projects still on `composeOptions` map to the listed compiler |
| KSP | KSP releases (`github.com/google/ksp/releases`) | supported Kotlin range of the release (KSP ≥ 2.3.0 is versioned independently of Kotlin; the `<kotlin>-<ksp>` prefix scheme applies only to KSP < 2.3.0); KSP2 default and its known processor gaps |
| Compose BOM | Compose BOM mapping (`developer.android.com/develop/ui/compose/bom/bom-mapping`) | which library versions a BOM pins; minimum `compileSdk` the pinned libraries need |
| Platform SDK levels | Android API-level table and the release's behaviour-changes page (`developer.android.com/about/versions/<n>/behavior-changes-<n>`) | current stable API level; the *targeting apps* section for the bump walk (`upgrade-playbook.md` §2) |
| Play target-API policy | Play Console help "Meet Google Play's target API level requirement" | the deadline and extension dates that `release-readiness` §D records; confirm the spec value, report a mismatch |
| 16 KB page size | Android 16 KB page-size guide (`developer.android.com/guide/practices/page-sizes`) | AGP floor, `useLegacyPackaging`, the alignment check script, the submission dates `release-readiness` §D records |
| Built-in Kotlin | "Migrate to built-in Kotlin" (`developer.android.com/build/migrate-to-built-in-kotlin`) | plugin removals, `com.android.legacy-kapt`, temporary opt-out, DSL renames |
| platform-tools | SDK Platform Tools release notes (`developer.android.com/tools/releases/platform-tools`) | current version and the version-gated behaviours `adb-workflows` §A cites |
| Libraries | each library's release page or Maven Central listing | breaking changes; minimum `compileSdk`/`minSdk`; Kotlin or coroutine floor |

**Coupling rules to fill in the matrix** — every arrow is a fact with a source, never assumed:
AGP → Gradle range; AGP → minimum JDK; AGP → KGP floor and KSP floor; Kotlin = Compose compiler
plugin; Kotlin within the KSP release's supported range (prefix = Kotlin only for KSP < 2.3.0); Compose BOM → minimum `compileSdk`; `compileSdk` ≥ `targetSdk`;
`targetSdk` → behaviour-changes page; libraries → minimum `compileSdk`/`minSdk`.

**Evidence record** — one row per fact, kept in the run state and copied into the toolchain log:

```
| Component | Current | Target | Constraint (verbatim) | Source URL | Fetched |
|---|---|---|---|---|---|
| AGP | 8.7.3 | <target> | "requires Gradle <range>, JDK <n>" | <url> | 2026-08-19 |
```

Mark a fact `unverified` when the fetch failed or the page did not state it; an `unverified`
target is not applied in step 4. When the fetched value contradicts a value in
`spec/android/release-readiness/` §D or `spec/android/project-structure/` §B, the spec wins for
the run and the contradiction is reported as a proposed spec update (REQ-6).

## 3. Reading the AGP 9 built-in-Kotlin state

Classify before planning; the class picks the migration items in `upgrade-playbook.md` §1.

| Signal | Migrated | Mid-migration (recorded interim) | Legacy |
|---|---|---|---|
| AGP major | ≥ 9 | ≥ 9 | < 9 |
| `org.jetbrains.kotlin.android` | absent | absent | applied |
| `android.builtInKotlin` / `android.newDsl` | unset (defaults `true`) | `false` with a dated record | absent or irrelevant |
| kapt | none | `com.android.legacy-kapt` with processor, reason, removal condition | `org.jetbrains.kotlin.kapt` |

A project that applies `org.jetbrains.kotlin.android` on AGP ≥ 9 with `android.newDsl` unset
does not build; that is not a mid-migration state but a broken one — the migration is the first
`apply` step, not a later one.
