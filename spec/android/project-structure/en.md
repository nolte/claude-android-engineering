# Android Project Structure

Status: draft

## Context

This repository provides reusable Claude skills for Android app development (project setup, Compose UI authoring, mobile UX, local development and debugging). Every skill is grounded in a well-formulated spec; this spec is the authoritative definition of what a well-structured Android app project looks like. The project-setup skill generates projects conforming to it, and review/audit skills judge existing projects against it.

The content is distilled from a research pass (August 2026) over three source classes: official Google/Android guidance (developer.android.com architecture, modularization, and build documentation — which uses an explicit three-tier vocabulary of *Strongly recommended* / *Recommended* / *Optional*), Gradle's official best-practices documentation, and reference projects (Now in Android as the flagship, android/compose-samples, Tivi, DuckDuckGo Android, Signal Android). Current stable toolchain at research time: AGP 9.x (built-in Kotlin), Gradle 9.x (configuration cache as preferred execution mode), Kotlin 2.x (Compose compiler ships with Kotlin). This spec encodes mechanisms, not exact versions.

Two calibration findings shape the whole spec: (1) Google explicitly conditions modularization on codebase size — its own small samples are deliberately single-module, so `:feature:*` module taxonomies are not a universal default; (2) where reference projects diverge, they diverge on *naming schemes*, not on the underlying invariants (feature isolation, shared design-system code, centralized build logic, committed formatter config).

Readers: authors of this repo's Android skills, and reviewers judging whether a generated or audited project is conformant.

## Goals

- Define the canonical repository layout, Gradle build conventions, module strategy, package structure, source-set layout, test placement, and quality-tooling layout for an Android app project
- Encode the scaling path from a single-module app to a modularized app as an explicit, trigger-based decision instead of a dogmatic default
- Make generated projects reproducible, fast to build, and safe by default (no secrets in VCS, no deprecated build mechanisms)
- Give downstream skills (project setup, Compose UI, debugging) one structural contract to generate against and audit against

## Non-Goals

- Play Store release, app signing for distribution, and store metadata — explicitly out of scope for this repository
- CI/CD pipeline design — covered by the portfolio specs `project/continuous-integration` and `project/continuous-delivery`
- Runtime architecture behavior beyond its structural imprint — state management, layer authority, caching and write strategies belong to `spec/android/app-architecture/`, navigation-graph design to `spec/android/app-design-navigation/`, and UX patterns to their own specs under `spec/android/`
- Kotlin Multiplatform project layout — this spec targets Android-only apps; KMP restructures the top level (see Tivi) and would need its own spec
- Pinning exact tool or library versions — the spec fixes mechanisms (catalog, wrapper, BOM); versions live in the generated project's `libs.versions.toml`

## Requirements

### A. Repository root layout

- **MUST** place at the repository root: `settings.gradle.kts`, `build.gradle.kts`, `gradle.properties`, `gradle/libs.versions.toml`, `gradle/wrapper/`, `gradlew`, `gradlew.bat`, `.editorconfig`, and `.gitignore`
- **MUST** base `.gitignore` on GitHub's canonical `Android.gitignore`, covering at minimum: `.gradle/`, `build/`, `local.properties`, `.idea/` (or a selective subset), `captures/`, `.cxx/`, `*.apk`, `*.aab`, `*.jks`, `*.keystore`, `google-services.json`, `*.hprof`
- **MUST NOT** track any secret-bearing file: API keys live in the untracked `local.properties` (Google `secrets-gradle-plugin` pattern) with a committed defaults file (for example `secrets.defaults.properties`); release keystores never enter VCS. A deliberately committed *debug* keystore for reproducible debug signatures is a **MAY**
- **MUST** set `kotlin.code.style=official` in `gradle.properties`
- **SHOULD** keep architecture documentation in a `docs/` folder; per-module `README.md` files with dependency graphs are a **MAY**

### B. Gradle build conventions

- **MUST** use the Kotlin DSL (`.gradle.kts`) for all build files — the default since AGP/Studio Giraffe and Gradle 8
- **MUST** build on AGP's built-in Kotlin support (AGP ≥ 9.0, `android.builtInKotlin=true` by default) and **MUST NOT** apply `org.jetbrains.kotlin.android` (`kotlin-android`) in any module — that plugin is incompatible with the new DSL that AGP 9 enables by default (`android.newDsl=true`) and applying it breaks the build [R21][R22]. The Kotlin Gradle plugin still appears in the catalog for `org.jetbrains.kotlin.plugin.compose`, `org.jetbrains.kotlin.jvm` (plain JVM modules), and as the version AGP's runtime dependency is aligned to; AGP 9.0 pins KGP ≥ 2.2.10 and KSP ≥ 2.2.10-2.0.2 and upgrades lower versions itself, so the catalog states versions at or above that floor [R21]; the KSP version is compatible per the KSP compatibility table — the Kotlin-prefixed `<kotlin>-<ksp>` scheme applies only to KSP < 2.3.0, from 2.3.0 KSP is versioned independently and each release states its supported Kotlin range [R27]. `android.builtInKotlin=false` is a temporary, dated, recorded migration opt-out, never a scaffold default [R22]
- **MUST** compile against one declared JDK toolchain: JDK 17 is AGP 9's minimum and default, the toolchain is declared once (`java { toolchain { languageVersion = JavaLanguageVersion.of(17) } }`, or `kotlin { jvmToolchain(17) }` — a shared convention plugin once `build-logic/` exists) and provisioned via a toolchain resolver (`org.gradle.toolchains.foojay-resolver-convention` in `settings.gradle.kts`) so a missing local JDK is downloaded instead of silently compiling with whatever runs Gradle [R21][R23][R24]. `sourceCompatibility`/`jvmTarget` scattered per module are the pattern this replaces
- **MUST** run builds exclusively through the committed wrapper (`gradlew`, `gradle/wrapper/` including the JAR); upgrade only via `./gradlew wrapper --gradle-version <v>`; **SHOULD** protect wrapper integrity via `distributionSha256Sum` and/or wrapper validation in CI
- **MUST** declare all dependency and plugin coordinates in a single version catalog `gradle/libs.versions.toml`: sections `[versions]`/`[libraries]`/`[plugins]` (optionally `[bundles]`, used sparingly), central versions referenced via `version.ref`, aliases in kebab-case, plugins applied via `alias(libs.plugins.…)`
- **MUST NOT** use dynamic dependency versions (for example `2.+`)
- **MUST** declare repositories centrally in `settings.gradle.kts` via `dependencyResolutionManagement`; **SHOULD** set `RepositoriesMode.FAIL_ON_PROJECT_REPOS` and use repository content filtering (for example `google()` scoped to `com.android.*`, `androidx.*`, `com.google.*`)
- **MUST** set `rootProject.name` explicitly in `settings.gradle.kts`
- **MUST** keep the root `build.gradle.kts` free of code except a `plugins {}` block declaring all submodule plugins with `apply false` (uniform build-script classpath); **MUST NOT** use `allprojects {}` / `subprojects {}` cross-project configuration
- **MUST** prefer `implementation` over `api`; `api` only when the type is part of the module's public ABI
- **MUST** manage Compose versions through the Compose BOM (`platform(libs.androidx.compose.bom)`, also on test configurations); Compose libraries in the catalog carry no individual versions; **MUST** apply the Compose compiler via the Kotlin-owned plugin `org.jetbrains.kotlin.plugin.compose` with `version.ref` = the Kotlin version
- **MUST** use KSP instead of kapt (kapt is in maintenance mode); no module may retain a kapt application. Where an annotation processor still has no KSP path, the *only* admissible interim is AGP's `com.android.legacy-kapt` plugin (same version as AGP — `org.jetbrains.kotlin.kapt`/`kotlin-kapt` is incompatible with built-in Kotlin), recorded with the processor, the reason, and the removal condition; a scaffold never emits it [R11][R22]
- **MUST** enable in `gradle.properties`: `org.gradle.configuration-cache=true`, `org.gradle.caching=true`, `org.gradle.parallel=true`, and an adequately sized `org.gradle.jvmargs` (raise heap when GC exceeds ~15 % of build time; set `-XX:MaxMetaspaceSize`); `android.useAndroidX=true` is required only on AGP < 9 — AGP 9 defaults it to `true`, so on AGP 9 it falls under the redundant-flag rule below [R17][R21]
- **MUST NOT** set redundant or obsolete flags: `android.nonTransitiveRClass` (AGP 8+ default), `android.enableJetifier` (legacy support-library only), `kotlin.incremental` (default), debug PNG-crunching flags, and — on AGP 9 — `android.useAndroidX`, `android.builtInKotlin`, `android.newDsl`, `android.r8.strictFullModeForKeepRules`, `android.proguard.failOnMissingFiles`, `android.sdk.defaultTargetSdkToCompileSdkIfUnset` set to their new `true` defaults [R17][R21]. Where the scaffold nevertheless needs one of these written out (a downstream tool that reads it), the reason is recorded next to it
- **MUST** know the AGP 9 defaults a generated build inherits and treat them as behaviour, not noise [R21]: the new DSL is on (`android.newDsl=true` — the old variant API `applicationVariants`/`libraryVariants` is gone), R8 runs in strict full mode for keep rules (`android.r8.strictFullModeForKeepRules=true` — a kept class no longer implicitly keeps its default constructor, so keep rules name what they need), a keep file named in the DSL that is missing on disk fails the build (`android.proguard.failOnMissingFiles=true`), `targetSdk` defaults to `compileSdk` when unset (`android.sdk.defaultTargetSdkToCompileSdkIfUnset=true` — the release-readiness spec's `targetSdk` obligations in `spec/android/release-readiness/` §D therefore apply to the *effective* value, and an app that wants a lower verified `targetSdk` states it explicitly), and `getDefaultProguardFile("proguard-android.txt")` is no longer supported — only `proguard-android-optimize.txt` (`spec/android/release-readiness/` §A). Gradle ≥ 9.1 and JDK ≥ 17 are the floor
- **SHOULD** enable typesafe project accessors (`enableFeaturePreview("TYPESAFE_PROJECT_ACCESSORS")`) and reference modules as `implementation(projects.core.data)` — still incubating, hence not a MUST
- **SHOULD** enable Gradle dependency verification with a committed `gradle/verification-metadata.xml` (checksums at minimum, PGP signatures where the publisher signs; bootstrapped with `--write-verification-metadata sha256`, refreshed deliberately on every dependency bump, never disabled to make a red build green) — the supply-chain counterpart to the wrapper checksum above [R25]
- **SHOULD** be able to produce a software bill of materials from the build (for example the CycloneDX Gradle plugin, community-maintained, no official Android endorsement) so the dependency currency and vulnerability scan owned by `spec/android/security/` §F have a machine-readable input; the SBOM is a build output, not a committed file [R26]
- **MAY** add dependency-hygiene tooling: Dependency Guard baselines or the Dependency Analysis Gradle Plugin (community standard, no official endorsement)
- **MAY** use `testFixtures` (`android.testFixtures.enable`, `testFixtures/` source set) to share fakes and builders between a module's own tests and its consumers' tests in modularized projects; it complements, not replaces, the `:core:testing` module of §F [R14]

### C. Module strategy and taxonomy

- **MUST** start a new app project single-module (`:app` only) unless a concrete reuse, team-scale, or delivery requirement exists at creation time — Google conditions modularization on codebase size, and its own small samples are single-module
- **MUST** record the modularization decision (trigger and intended split) when it is taken; recognized triggers: sustained build-time pain, code reuse across apps/variants, enforced visibility boundaries, parallel ownership
- **MUST**, once modularized, follow the three-tier taxonomy `:app` / `:feature:*` / `:core:*` with these dependency rules: feature modules never depend on other feature modules' implementations; core modules never depend on feature or app modules; the app module sits on top depending on features and required core modules; no dependency cycles
- **MUST**, once modularized, share build configuration through convention plugins in a `build-logic/` included build (`pluginManagement { includeBuild("build-logic") }`) with single-responsibility, composable plugins; plugin IDs follow `<project>.<platform>.<module-type>[.<aspect>]` (for example `myapp.android.library.compose`); `buildSrc` remains a **MAY** for very small multi-module builds
- **SHOULD** prefer plain Kotlin/JVM modules over Android library modules wherever no Android resources or manifest are needed
- **SHOULD** separate `:core:designsystem` (data-agnostic components, theme, icons) from `:core:ui` (composite components that may depend on data-layer models)
- **SHOULD** pass simple IDs, not objects, as navigation arguments across features (single source of truth)
- **MAY** split features into `:feature:x:api` (navigation keys) and `:feature:x:impl` (screens, ViewModels) — the current Now in Android / Navigation 3 pattern for large projects; **MUST NOT** apply this split to solo or small projects where it is pure overhead

### D. Package structure and source sets

- **MUST** keep layer boundaries visible in the package tree: UI code and data code never share a package; a single-module app starts with top-level `ui` (or `feature`) and `data` packages
- **SHOULD** group UI code by feature (`feature.<name>` or `ui.<feature>` packages holding screen composables, the ViewModel, and navigation code together) rather than one flat layer package — "feature by module or package, layer inside"
- **MUST** use the standard source-set layout `src/main/`, `src/test/`, `src/androidTest/` (Kotlin sources under `kotlin/`); build-type/flavor source sets follow the standard priority order and are added only when a variant actually needs them
- **MUST** keep `minSdk`, `targetSdk`, and `applicationId` in build files, not in the manifest; resolve manifest-merge conflicts explicitly with `tools:` markers
- **MUST**, in modularized projects, keep each module's public surface minimal (`internal` by default; expose only the essentials)

### E. Architecture — structural imprint

- **MUST** separate a UI layer and a data layer; UI-layer code never accesses data sources (database, DataStore, network, sensors) directly — access goes through repositories, even single-source ones
- **MUST** name repositories `<DataType>Repository` and data sources `<DataType><Remote|Local>DataSource` (never after implementation details)
- **MAY** introduce a domain layer (use cases named `<VerbPresentTense><Noun>UseCase`) — officially optional, warranted by complexity or reuse; **MUST NOT** force trivial pass-through use cases
- **MUST** use constructor-based dependency injection; Hilt for modularized apps, manual DI acceptable for small single-module apps
- **MUST** structure screen-level Compose code as a thin stateful route composable (obtains the ViewModel, collects state) delegating to a stateless content composable taking `uiState` plus event lambdas; previews target the stateless composable, live next to it, and are named `<Composable>Preview`
- **SHOULD** keep theming/design-system code in one dedicated place (a `designsystem`/`theme` package in single-module apps; `:core:designsystem` once modularized): theme function, typed accessors, core components

### F. Testing structure

- **MUST** place unit tests in the same module as the code under test (`src/test/`) and instrumented tests in `src/androidTest/`; no central test module for per-module tests
- **MUST** prefer fakes over mocks (test implementations with test-only hooks); **SHOULD** avoid a mocking library entirely
- **SHOULD**, once modularized, put shared test fixtures (rules, fake repositories, test data, test runner) into a `:core:testing` module
- **MAY** add JVM screenshot tests (Roborazzi or Paparazzi) in `src/test/` with goldens committed per module under `src/test/screenshots/`
- **MUST** follow one consistent test-naming scheme per repository (the scheme itself is free; mixing schemes is not)
- **SHOULD**, when product flavors exist, run variant-aware test tasks (for example `testDemoDebug`) instead of the aggregate `test`

### G. Quality-tooling layout

- **MUST** commit a root `.editorconfig`; ktlint rule configuration lives there
- **SHOULD** orchestrate formatting through Spotless with ktlint as the Kotlin formatter; license-header templates in a root `spotless/` folder are a **MAY**
- **SHOULD** centralize Android Lint configuration (a convention plugin once `build-logic/` exists, else a root `lint.xml`); per-module `lint-baseline.xml` files are for legacy findings only — new projects start baseline-free
- **MAY** add detekt (config under `config/detekt/detekt.yml`) — widespread in the community, absent from Google's reference projects
- **MAY** enforce formatting via git hooks (for example lefthook)

## Acceptance Criteria

The criteria are a representative rollup of §A–§G, not a 1:1 mapping; every requirement bullet above is normative on its own.

- [ ] A freshly generated project builds green with `./gradlew build` immediately after generation
- [ ] The repository root contains every §A file (`settings.gradle.kts`, `build.gradle.kts`, `gradle.properties`, `gradle/libs.versions.toml`, `gradle/wrapper/` with its JAR, `gradlew`, `gradlew.bat`, `.editorconfig`, `.gitignore`), and `gradle.properties` sets `kotlin.code.style=official`
- [ ] No module applies `org.jetbrains.kotlin.android`; Kotlin compiles through AGP's built-in support with the KGP/KSP catalog versions at or above AGP's floor, and exactly one JDK 17 toolchain declaration plus a toolchain resolver exists
- [ ] The root `build.gradle.kts` contains only a `plugins {}` block with `apply false` declarations; no `allprojects`/`subprojects` blocks exist anywhere
- [ ] Every dependency and plugin in module build files resolves through `libs.versions.toml` accessors; no hard-coded coordinates or dynamic versions
- [ ] `gradle.properties` enables configuration cache, build cache, and parallel execution, and contains none of the flags listed as redundant or obsolete in §B for the AGP generation in use
- [ ] No module applies kapt; annotation processing uses KSP — any `com.android.legacy-kapt` interim is recorded with processor, reason, and removal condition
- [ ] Compose libraries carry no individual versions (BOM-managed), and the Compose compiler plugin version references the Kotlin version
- [ ] A newly generated project contains exactly one `:app` module unless modularization was explicitly requested; when modularized, the module graph honors every dependency rule in §C
- [ ] Unit and instrumented tests live in `src/test/` / `src/androidTest/` of the module under test
- [ ] A formatting check (Spotless/ktlint) passes on freshly generated code
- [ ] `git ls-files` shows no `local.properties`, release keystore, or `google-services.json`
- [ ] The package tree separates UI and data layers, and screen code is grouped by feature
- [ ] Screen composables are split into stateful route and stateless, previewable content composables

## Open Questions

Each question states the working default the requirements above already encode.

- detekt adoption: Google's reference projects skip it, the community embraces it — decide when this repo's quality-gate/audit skill takes shape
- Threshold for the `:feature:x:api`/`:impl` split: at what project size does the Navigation-3-style split pay off?
- Should the project-setup skill scaffold `build-logic/` from day one (cheap while empty) or only on first modularization (single-module purity)?
- Screenshot-testing tool choice: Roborazzi vs Paparazzi vs Google's newer Compose Preview Screenshot Testing (`src/screenshotTest` source set)
- Kotlin Multiplatform: if KMP ever enters scope, the top-level layout changes fundamentally (see Tivi) and needs its own spec

## References

- [R1] Android app architecture guide — layers, separation of concerns, SSOT, UDF: <https://developer.android.com/topic/architecture>
- [R2] Architecture recommendations (Strongly recommended / Recommended / Optional tiers): <https://developer.android.com/topic/architecture/recommendations>
- [R3] Modularization overview — when (not) to modularize: <https://developer.android.com/topic/modularization>
- [R4] Common modularization patterns — module types, dependency rules, api vs implementation: <https://developer.android.com/topic/modularization/patterns>
- [R5] Now in Android — Modularization Learning Journey (feature api/impl split, core taxonomy): <https://github.com/android/nowinandroid/blob/main/docs/ModularizationLearningJourney.md>
- [R6] Now in Android — build-logic convention plugins: <https://github.com/android/nowinandroid/blob/main/build-logic/README.md>
- [R7] Gradle best practices — structuring builds: <https://docs.gradle.org/current/userguide/best_practices_structuring_builds.html>
- [R8] Gradle best practices — dependencies: <https://docs.gradle.org/current/userguide/best_practices_dependencies.html>
- [R9] Gradle version catalogs: <https://docs.gradle.org/current/userguide/version_catalogs.html>
- [R10] Migrate to version catalogs (Android): <https://developer.android.com/build/migrate-to-catalogs>
- [R11] Migrate from kapt to KSP: <https://developer.android.com/build/migrate-to-ksp>
- [R12] Compose compiler Gradle plugin (ships with Kotlin 2.x): <https://developer.android.com/develop/ui/compose/compiler>
- [R13] Compose Bill of Materials: <https://developer.android.com/develop/ui/compose/bom>
- [R14] Build variants and source sets: <https://developer.android.com/build/build-variants>
- [R15] Manifest merging: <https://developer.android.com/build/manage-manifests>
- [R16] Compose previews and stateless-composable guidance: <https://developer.android.com/develop/ui/compose/tooling/previews>
- [R17] Optimize your build (gradle.properties flags, obsolete flags): <https://developer.android.com/build/optimize-your-build>
- [R18] Navigation 3 modularization (feature api/impl): <https://developer.android.com/guide/navigation/navigation-3/modularize>
- [R19] GitHub canonical Android.gitignore: <https://github.com/github/gitignore/blob/main/Android.gitignore>
- [R20] Secrets Gradle Plugin (local.properties pattern): <https://github.com/google/secrets-gradle-plugin>
- [R21] Android Gradle plugin 9.0 release notes — built-in Kotlin on by default, `org.jetbrains.kotlin.android` incompatible with `android.newDsl=true`, KGP 2.2.10 / KSP 2.2.10-2.0.2 floor, new `true` defaults (`android.newDsl`, `android.builtInKotlin`, `android.useAndroidX`, `android.r8.strictFullModeForKeepRules`, `android.proguard.failOnMissingFiles`, `android.sdk.defaultTargetSdkToCompileSdkIfUnset`), `proguard-android.txt` dropped, Gradle 9.1 / JDK 17 minimum (P): <https://developer.android.com/build/releases/agp-9-0-0-release-notes>
- [R22] Migrate to built-in Kotlin — remove `kotlin-android`, `kotlin-kapt` → `com.android.legacy-kapt` only when KSP is not yet possible, `android.builtInKotlin=false` as temporary opt-out (P): <https://developer.android.com/build/migrate-to-built-in-kotlin>
- [R23] Java versions in Android builds — toolchain declaration, JDK 17 for AGP, `JAVA_HOME` alignment (P): <https://developer.android.com/build/jdks>
- [R24] Gradle toolchains and the Foojay toolchain-resolver convention plugin (P): <https://docs.gradle.org/current/userguide/toolchains.html>, <https://github.com/gradle/foojay-toolchains>
- [R25] Gradle dependency verification — `gradle/verification-metadata.xml`, checksum and signature verification, bootstrapping (P): <https://docs.gradle.org/current/userguide/dependency_verification.html>
- [R26] CycloneDX Gradle plugin — SBOM generation from the Gradle dependency graph (S): <https://github.com/CycloneDX/cyclonedx-gradle-plugin>
- [R27] KSP releases — from 2.3.0 the KSP version is decoupled from the Kotlin version (no `<kotlin>-<ksp>` prefix); each release states its supported Kotlin range (P): <https://github.com/google/ksp/releases>
