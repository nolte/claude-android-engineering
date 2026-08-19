# Verification and Log

The checks that prove an upgrade beyond `./gradlew build` — 16 KB page-size readiness of native
code, dependency hygiene — the toolchain-log template, and the read-only `audit` procedure. Play
submission dates and the AGP floor for page size are owned by `spec/android/release-readiness/`
§D and re-verified in research; this file holds the commands.

## Table of contents

- [1. 16 KB page-size verification](#1-16-kb-page-size-verification) — packaging flag,
  artifact alignment check, emulator boot
- [2. Dependency hygiene](#2-dependency-hygiene) — Renovate/Dependabot, osv-scanner,
  verification metadata
- [3. The toolchain log](#3-the-toolchain-log) — location (release-readiness §F), entry template
- [4. Audit procedure (operation `audit`)](#4-audit-procedure-operation-audit) — read-only,
  severity-classified report

---

## 1. 16 KB page-size verification

Due whenever the inventory found a `.so` under `jniLibs` or a dependency that bundles native
code; an app with no native code records "no native code — not applicable" in the log.

1. **Packaging flag.** In the app module: `packaging { jniLibs { useLegacyPackaging = false } }`
   (uncompressed, page-aligned libraries). Requires the AGP floor `release-readiness` §D names;
   on an older AGP the flag alone is not enough — the AGP bump comes first (`upgrade-playbook.md`
   §1 step 2).
2. **Own native code.** NDK r28+ builds 16 KB aligned by default; on r27
   `-Wl,-z,max-page-size=16384` (ndk-build `APP_SUPPORT_FLEXIBLE_PAGE_SIZES := true`, CMake
   `ANDROID_SUPPORT_FLEXIBLE_PAGE_SIZES=ON`). Confirm the `ndkVersion` in the module.
3. **Artifact check** on the *release* artifact:
   - `./gradlew :app:assembleRelease` (or `bundleRelease` and extract the universal APK with
     `bundletool build-apks --mode=universal`).
   - Run `check_elf_alignment.sh <apk>` from the Android platform tooling (fetch the script
     location from the page-size guide during research), or without it:
     `zipalign -c -P 16 -v 4 <apk>` from build-tools plus, per extracted `.so`,
     `objdump -p lib.so | grep LOAD` — every `LOAD` segment `align` must be `2**14` or higher.
   - Any `UNALIGNED`/`2**12` hit names the library and its owning dependency; the remedy is a
     dependency version that ships 16 KB builds (research its release page), never repackaging
     the `.so` — a hit without an available fix is a recorded interim (`release-readiness` §F).
4. **Boot test** where an emulator image with 16 KB pages is installed
   (`sdkmanager --list | grep 16k` for the system image): install the release build with
   `adb -s <serial> install -r <apk>`, launch, and exercise the native path; on a 4 KB device
   the check is the artifact check only — say so in the report.

## 2. Dependency hygiene

Both are **SHOULD** in `spec/android/security/` §F; `release-readiness` §D strengthens the
*outcome* (dependencies current) to a MUST, so their absence is a Warning offered as a plan
step, never a silent addition.

- **Renovate/Dependabot.** Look for `renovate.json`, `renovate.json5`, `.renovaterc*`,
  `.github/renovate.json*`, or `.github/dependabot.yml`. When absent and the operator accepts the
  step, add a minimal Renovate config that extends the shared preset the repository family uses
  (ask which; do not invent one) with the Gradle version catalog and wrapper managers enabled,
  grouped AndroidX/Kotlin updates, and no auto-merge. Record the choice as a spec gap when no
  spec names the preset (REQ-6).
- **osv-scanner.** osv-scanner reads Gradle inputs only from files it parses — a
  `gradle.lockfile` / `buildscript-gradle.lockfile` (produced by Gradle dependency locking:
  `dependencyLocking { lockAllConfigurations() }` plus `./gradlew dependencies --write-locks`)
  or `gradle/verification-metadata.xml`; it does **not** read the text output of
  `./gradlew dependencies`. Run `osv-scanner scan --lockfile gradle/verification-metadata.xml`
  when verification metadata exists, `osv-scanner scan --lockfile <module>/gradle.lockfile`
  (or `osv-scanner scan -r .`, which discovers those files) when dependency locking is enabled;
  when neither exists, enable dependency locking first (a plan step with confirmation) and only
  then scan. Report findings by severity and route a vulnerable version into
  `upgrade-playbook.md` §1 step 8. When absent from CI and the operator accepts, add the step
  to the workflow the project already has (`android-test-suite-apply` owns the CI layout).
- **Verification metadata.** When `gradle/verification-metadata.xml` exists, refresh it after every
  bump with `./gradlew --write-verification-metadata sha256 help` and review the diff; never
  disable verification (`project-structure` §B). When absent, offer bootstrapping as a SHOULD step.

## 3. The toolchain log

**Location:** `project/toolchain-log.md` — named normatively by `spec/android/release-readiness/`
§F, beside `project/permissions-ledger.md` and `project/notification-ledger.md`, the repository's
existing convention for decision records that outlive a run.

Create the file with the header below when absent (confirm first, REQ-8); append one entry per
run, newest first.

```markdown
# Toolchain log

One entry per `android-toolchain-upgrade` run: the before/after matrix, the evidence each target
version rests on, the interims recorded, and the gate result. Convention proposed for
`spec/android/release-readiness/` §F (REQ-6).

## <YYYY-MM-DD> — <one-line scope, e.g. "AGP 8.7 → 9.0, Kotlin 2.1 → 2.2, targetSdk 35 → 36">

| Component | Before | After | Source URL | Fetched |
|---|---|---|---|---|
| Gradle | … | … | … | … |
| AGP | … | … | … | … |
| Kotlin / Compose compiler | … | … | … | … |
| KSP | … | … | … | … |
| Compose BOM | … | … | … | … |
| compileSdk / targetSdk / minSdk | … | … | … | … |
| JDK toolchain | … | … | … | … |
| platform-tools | … | … | … | … |

- **Behaviour changes handled (targetSdk <n>):** <row → fixed here / handed to <skill> / n.a.>
- **16 KB page size:** <not applicable | verified on <artifact> with <tool> | interim: <library>, <removal condition>>
- **Dependency hygiene:** <Renovate present/added, osv-scanner result, verification metadata refreshed>
- **Interims recorded (`release-readiness` §F):** <item — reason — removal condition — date>
- **Gate:** build ✓ | lint ✓ | unit tests ✓ | release assembly ✓ | device smoke: <run | skipped: reason>
- **Spec gaps reported (REQ-6):** <list>
```

## 4. Audit procedure (operation `audit`)

Read-only: no file is written, no build is run beyond `./gradlew --version` and
`./gradlew :app:dependencies` (read-only queries). Runs SKILL.md steps 1–2, then classifies each
inventory item against the evidence and reports in the operator's language. Severity follows
`spec/claude/review-plan/` keyed on the RFC-2119 strength of the violated bullet:

| Finding | Severity |
|---|---|
| `targetSdk` below the Play requirement whose deadline (`release-readiness` §D, re-verified) has passed | Critical |
| `targetSdk` below the requirement within 90 days of the deadline; `compileSdk` below latest stable; `minSdk` without rationale | Warning |
| `org.jetbrains.kotlin.android` applied on AGP ≥ 9; any kapt other than a recorded `com.android.legacy-kapt` interim; KSP release whose supported Kotlin range excludes the project's Kotlin (KSP < 2.3.0: prefix ≠ Kotlin); Compose compiler plugin ≠ Kotlin; dynamic version; coordinate outside the catalog; Compose version beside the BOM | Critical |
| A recorded `com.android.legacy-kapt` interim (its removal condition checked: processor now has a KSP path → Critical) | Warning |
| AGP below the range its Gradle wrapper supports or vice versa; JDK toolchain undeclared or resolver absent; wrapper without `distributionSha256Sum` | Warning |
| Native code with `useLegacyPackaging = true`, or AGP below the page-size floor | Critical |
| Native code with alignment unverified (no artifact available read-only) | Warning ("verify in `apply` step 6") |
| Redundant or obsolete `gradle.properties` flag; unrecorded `android.builtInKotlin=false`/`android.newDsl=false` | Warning |
| Renovate/Dependabot or osv-scanner absent; verification metadata absent | Warning / Info respectively |
| Component behind current stable with no coupling constraint blocking the bump | Suggestion |
| Local platform-tools behind current, or more than one adb on `PATH` | Warning |
| Clean item | Info (state what was checked and the evidence row) |

Report shape: the inventory table with a `Target` and `Severity` column, the evidence rows, the
findings grouped by severity, and a closing line "Apply with `android-toolchain-upgrade plan`"
or, when the operator asked for more than currency, "Full §A–§F audit →
`android-release-readiness-reviewer`". When a report from that agent already exists under
`.audits/android-release-readiness-review/`, cross-reference its §D findings by line instead of
duplicating them.
