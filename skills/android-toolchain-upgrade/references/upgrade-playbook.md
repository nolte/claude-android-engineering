# Upgrade Playbook

The canonical order in which an Android toolchain is raised, what each step touches, how it is
gated, and how a `targetSdk` bump is walked before it is applied. Every version referenced here
is a placeholder for the evidence row from `inventory-and-research.md` §2 — the playbook orders
the work; the research fixes the numbers.

## Table of contents

- [1. Canonical upgrade order](#1-canonical-upgrade-order) — steps, files touched, gate, and
  the built-in-Kotlin migration and kapt exit
- [2. The `targetSdk` behaviour-change walk](#2-the-targetsdk-behaviour-change-walk) — impact
  classes, where each is fixed or handed over, and the walk procedure
- [3. Handling a red gate](#3-handling-a-red-gate) — fix-in-step vs revert-and-route

---

## 1. Canonical upgrade order

The order minimizes the number of red states: each step lands on a toolchain the next step
requires. Skip a step whose current value already equals its target; never reorder steps 1–3.
Every step ends with `./gradlew build` (add `--no-configuration-cache` once when the failure is
implausible, then re-run with the cache), a checkpoint, and — for the plan — one line
`<step> | <files> | <target> | <evidence row> | gate: ./gradlew build`.

| # | Step | Touches | Notes |
|---|---|---|---|
| 1 | Gradle wrapper | `gradle/wrapper/gradle-wrapper.properties` via `./gradlew wrapper --gradle-version <v> --gradle-distribution-sha256-sum <sha>` (run twice so the wrapper JAR and scripts update too) | Target = a version inside the *target* AGP's supported range; never edit the properties file by hand (`project-structure` §B). Refresh `gradle/verification-metadata.xml` if present. |
| 2 | AGP | `libs.versions.toml` `[versions]` | Read the AGP release notes for removed properties and DSL renames before bumping; a major bump (8 → 9) proceeds one major at a time when the notes list migration steps. On AGP 9 also apply the redundant-flag cleanup of step 6 immediately if a flag now errors. |
| 3 | Kotlin line | `[versions]` for KGP, `org.jetbrains.kotlin.plugin.compose`, KSP; Compose BOM in `[libraries]` | Bump KGP, Compose compiler plugin (= Kotlin), and KSP (a release whose compatibility table covers the new Kotlin; the `<kotlin>-<ksp>` prefix scheme applies only to KSP < 2.3.0) in **one** step — they do not build apart. Then the BOM to the entry mapped to that compiler. A pre-2.0 project still on `composeOptions.kotlinCompilerExtensionVersion` first adopts `org.jetbrains.kotlin.plugin.compose` and deletes `composeOptions` (`project-structure` §B). |
| 4 | Built-in Kotlin and kapt exit | every module `plugins {}` block, `gradle.properties`, `libs.versions.toml` `[plugins]` | See the migration list below. |
| 5 | JDK toolchain | root convention plugin or each module; `settings.gradle.kts` for the Foojay resolver | One declaration (`jvmToolchain(17)` or `java.toolchain`), resolver present, per-module `sourceCompatibility`/`jvmTarget` removed. Local JDK aligned or provisioned by the resolver. |
| 6 | `gradle.properties` cleanup | `gradle.properties` | Remove flags redundant on the AGP generation now in use and obsolete flags; keep configuration cache, build cache, parallel, sized `jvmargs`. Each removal is its own confirmed diff — a flag may be read by a downstream tool (§B records the reason when kept). |
| 7 | `compileSdk`, then `targetSdk` | app module or convention plugin | `compileSdk` to the latest stable the BOM and libraries accept; `targetSdk` only after the walk in §2 — and, on AGP 9, state `targetSdk` explicitly rather than inheriting `compileSdk` when the verified level is lower. Record a lagging `targetSdk` with reason and date (`release-readiness` §D/§F). |
| 8 | Libraries | `[versions]`/`[libraries]` | Group by owner (AndroidX, Kotlinx, Hilt/Room via KSP, networking, media). Bump one group per gate; read each release page for behaviour changes and `minSdk`/`compileSdk` floors; a behaviour-changing bump is verified on the release build (`release-readiness` §D). |
| 9 | platform-tools | operator machine (`sdkmanager --install "platform-tools"` or the SDK's own updater) | Only when step 1 of `SKILL.md` found it behind; verify `which -a adb` still lists exactly one (`adb-workflows` §A). |

**Crossing AGP 9.3 (part of step 2, independent of step 4):**

This one runs whenever the AGP bump crosses 9.3 — including for a project already on built-in
Kotlin that skips the migration list below entirely. AGP 9.3 relocates the shrinker configuration,
and rules left behind are read by nothing: the build stays green while they silently stop applying.

- Move keep rules from `proguardFiles(...)` to `src/<variant>/keepRules/*.keep`, and switch
  activation from `isMinifyEnabled`/`isShrinkResources` to `optimization { enable = true }`
  (`release-readiness` §A). Carry every rule over, not just the ones you recognise.
- The log-stripping rule is the one whose loss is invisible in a green build:
  `-maximumremovedandroidloglevel 3` (or the project's `-assumenosideeffects` fallback) must arrive
  in the new location. Prove it by reading the new keep file; whether the dex check adds anything
  depends on which of §G's two conforming facade variants the project uses. Where the facade drops
  the low levels in a release implementation (a `BuildConfig.DEBUG` guard), `android.util.Log int v(`
  / `int d(` are absent from the release dex whether or not the keep rule survived the move — a
  green dex check proves nothing there. Where the facade instead relies on a stripping rule for its
  own class, a rule left behind in `proguardFiles` does bring those methods back and §H's dex check
  catches it. Run it either way; just do not read a green result as proof on the guarded variant.

**Built-in-Kotlin migration (step 4), in this order, one gate each:**

1. Confirm AGP ≥ 9 landed (step 2) and KGP/KSP are at or above the floor AGP's notes pin.
2. Remove `alias(libs.plugins.kotlin.android)` (`org.jetbrains.kotlin.android`) from every
   Android module's `plugins {}`; keep the KGP catalog entry for `org.jetbrains.kotlin.plugin.compose`
   and any `org.jetbrains.kotlin.jvm` module. Do **not** add `android.newDsl=false` to make it
   compile — that is the recorded-interim path, only when the operator accepts the interim.
3. Move `kotlinOptions { jvmTarget }` and similar KGP DSL to the AGP-owned equivalents the
   migration guide names (`kotlin { }` block inside `android { }` where the guide says so);
   the JDK toolchain of step 5 supersedes `jvmTarget` in most modules.
4. kapt exit: for each `kapt(...)` processor, switch to its KSP artefact
   (`ksp(libs.<processor>.compiler)`) — Room, Hilt, Moshi, Glide all have one. Where a processor
   has no KSP path, apply `com.android.legacy-kapt` (same version as AGP), never
   `org.jetbrains.kotlin.kapt`, and record processor, reason, and removal condition
   (`project-structure` §B; REQ-9). Delete `kapt { }` configuration blocks that KSP does not read.
5. Re-run the build with `--warning-mode all` once and clear the AGP 9 deprecation output
   relevant to the migration (variant API removals `applicationVariants`/`libraryVariants`,
   `getDefaultProguardFile("proguard-android.txt")` → `proguard-android-optimize.txt`).

## 2. The `targetSdk` behaviour-change walk

The bump is applied only after every impact is resolved, handed over with the citation, or
recorded as a dated interim with a removal condition (`release-readiness` §D/§F). Walk **every**
level between current and target — a jump from 34 to 36 owes the 35 walk as well.

**Procedure:** fetch the behaviour-changes page of the level (URL pattern in
`inventory-and-research.md` §2), read only the *"apps targeting Android N"* section (the *"all
apps"* section is runtime behaviour on the new OS, noted but not gating), and for each entry
decide: *not applicable* (state why — no such API, no such component), *fix here*, or *hand
over*. Present the list as one table with a decision per row; the operator confirms it before
the bump diff.

| Impact class | Typical entries (verify against the fetched page; authoring view as of 2026-08) | Resolved by |
|---|---|---|
| Predictive back | 36: enabled by default — `onBackPressed()` and `KeyEvent.KEYCODE_BACK` no longer called; `android:enableOnBackInvokedCallback="false"` is the temporary opt-out | Fix here: migrate to `OnBackPressedCallback`/`BackHandler`; an opt-out is a recorded interim |
| Edge-to-edge and insets | 35: enforced for targeting apps, `windowOptOutEdgeToEdgeEnforcement` temporary; 36: opt-out removed | Fix here per `screen-formats` §B/§D and `app-design-navigation` §A; UI restyling → `android-compose-ui` |
| Orientation, resizability, aspect ratio | 36: `screenOrientation`, `resizeableActivity="false"`, min/max aspect ratio ignored on large screens (opt-out per activity, temporary) | Fix here per `screen-formats` §D; a locked-orientation exception is a recorded interim |
| Foreground services | 34+: type per FGS mandatory; 35: `dataSync`/`mediaProcessing` timeouts, `BOOT_COMPLETED` launch restrictions per type; 36: further per-type restrictions | Hand over: type declaration and permission pair → `android-permissions-derive`; the service's alerting contract → `android-notification-derive` |
| Permissions | new runtime permissions, restricted or removed permissions, `SCHEDULE_EXACT_ALARM` defaults, media and photo-picker changes | Hand over → `android-permissions-derive` with the page citation |
| Notifications | channel and importance changes, full-screen-intent restrictions, promoted/progress-centric notifications and their permission (36) | Hand over → `android-notification-derive` (the permission part again → `android-permissions-derive`) |
| Intents and components | 35: safer intents (implicit intents must match a filter; `Intent` without action), `PendingIntent` mutability, `BOOT_COMPLETED` restrictions | Fix here or → `android-feature-implement` when the fix crosses layers |
| Non-SDK interfaces | list additions per level | Fix here: remove the access; StrictMode `detectNonSdkApiUsage()` in debug detects it (`release-readiness` §D) |
| Media, camera, Bluetooth, sensors | per-level API restrictions | Route by owner: scanning → `android-barcode-scanner-scaffold`, otherwise `android-feature-implement` |
| Text, locale, layout | 35: elegant text height default, locale preferences; deprecations turned errors | Fix here or → `android-compose-ui` |
| Security | 35: restricted `TLS` versions, `MediaProjection` consent, private space | Fix here; when it touches network config → `security` §C obligations |

Each hand-over carries: the impact row, the fetched page URL and section, and the affected files.
The bump diff (`targetSdk = <n>`) is one gate of its own, followed by `./gradlew build` and the
release assembly of the closing gate.

## 3. Handling a red gate

- **Cause is the step itself** (removed API, renamed DSL, a processor without KSP path, a BOM
  entry needing a higher `compileSdk`): fix within the step, re-run, checkpoint. State the fix.
- **Cause is unclear or outside the step**: revert the step (`git checkout -- <files>` after
  confirmation, or the operator's stash), confirm green, then route to `android-debugging` with
  the full output and the evidence row. Never continue on top of red (REQ-7).
- **Cause is a pre-existing red the baseline check missed**: stop, report, route; the run
  resumes from the checkpoint once the baseline is green.
- **`--no-configuration-cache` makes it green**: the configuration cache is stale or the plugin
  bump broke cache compatibility; report which, and clear `.gradle/configuration-cache` only after
  confirmation.
