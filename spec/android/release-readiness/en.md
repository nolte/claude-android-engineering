# Release Readiness of the Source

Status: draft

## Context

"It works" and "it is ready to ship" are different claims, and the gap between them is almost entirely invisible on a debug build. The debug build keeps every class name, ships the leak detector, logs everything, talks to the staging host, and never runs the optimizer that will rewrite the code users actually execute. A feature verified only there has been verified in a configuration nobody will ever run.

This spec fixes the properties an app's *source and build* must have before the work is called done: the release build is optimized and actually exercised, no development affordance survives into it, the app's stability and platform currency are inside stated budgets, and one quality gate says green.

Scope boundary, stated once and load-bearing: this repository's requirements put Play-Store *release* out of scope — signing keys and their custody, store metadata, listings, screenshots, release tracks, staged rollouts, and the Data Safety questionnaire are the operator's, not a skill's. What is in scope is everything that makes the *code* production-grade, which is exactly what determines whether a store release would survive contact with users. A skill **MUST NOT** interpret this spec as permission to touch the store process.

Provenance: desk research (August 2026) over the R8 shrinking, obfuscation, and optimization documentation, the Android core app quality guidelines and their testable criterion IDs, the Android vitals thresholds (the quantified stability ceiling), the StrictMode reference, and the Gradle/AGP build documentation. Version-bound statements name their AGP boundary; this spec encodes mechanisms, not exact versions.

Boundaries: security obligations of the release build — `android:debuggable=false`, no committed secrets, dependency vulnerability scanning, the "R8 is not a security control" rule — are owned by `spec/android/security/` §F/§G and are referenced, not restated — with one deliberate exception, the `debuggable` rule, which §B restates so the §E gate can be walked without opening a second spec. Build-file structure, the version catalog, and quality-tooling layout belong to `spec/android/project-structure/` §B/§G; what a test lane *is* to `spec/android/test-automation/` §A/§D–§F and its CI wiring to that spec's §G; scroll-performance measurement to `spec/android/long-list-scrolling/` §G; device and log mechanics to `spec/android/adb-workflows/`.

Readers: authors of this repository's Android skills who must decide whether a change is finished, and reviewers judging a claim of "done".

## Goals

- Make the release build, not the debug build, the configuration in which a change is finally verified
- Keep every development affordance — debug library, verbose log, staging endpoint, bypass flag — out of the shipped binary
- Give stability a number instead of an impression
- Keep the app current with the platform and its dependencies, deliberately rather than by drift
- Define one gate whose green state is what "done" means, and make a red state impossible to leave unreported

## Non-Goals

- Signing key material and custody, store metadata, listings, screenshots, release tracks, staged rollout, and the Data Safety questionnaire — out of this repository's scope by requirement
- Security controls of the release build — `spec/android/security/` §F/§G
- Test-lane composition — `spec/android/test-automation/` §A/§D–§F; CI workflow authoring and runner setup — that spec's §G
- Startup-time and jank measurement methodology, and Baseline Profile authoring — no spec owns these yet (§Open Questions); the budgets below reference them without defining the method
- Versioning schemes and changelog generation — a portfolio-level release concern, not an Android one
- App size optimization beyond the shrinker defaults

## Requirements

### A. The release build is a real build

- **MUST** enable code shrinking, optimization, obfuscation, and resource shrinking for the release build type: on AGP ≥ 9.3 through the `optimization { enable = true }` block, on earlier AGP through `isMinifyEnabled = true` plus `isShrinkResources = true` with `proguard-android-optimize.txt` as the default file [R1]
- **MUST NOT** enable the shrinker for debug or test build types, and **MUST NOT** disable it for release to make a failure go away — a failure under R8 is a defect in the keep configuration or in reflective code, and it is fixed there [R1]
- **MUST** keep keep-rules specific and located per the AGP generation in use (`src/<variant>/keepRules/*.keep` on AGP ≥ 9.3, `proguardFiles` before that); blanket rules (`-keep class ** { *; }`, `-dontobfuscate`, `-dontoptimize`) are non-conformant except as a documented, dated, and ticketed interim [R1]
- **MUST** retain the `mapping.txt` of every release build that leaves the machine, so a stack trace from that build can be retraced [R1]
- **MUST** verify the change on an actual release build before calling the work done — install the release variant on a device and exercise the touched flow. R8 rewrites code, and reflection-based and serialization-based failures appear only there [R1]
- **MUST** ensure the release variant assembles (`assembleRelease`, or `bundleRelease` where a bundle is the artifact) as part of the gate in §E; producing the artifact is in scope, publishing it is not
- **SHOULD** keep a startup profile and Baseline Profile in place where one exists, and **MUST NOT** insert post-R8 DEX-modifying tooling that would invalidate it [R1]

### B. No development affordance survives

- **MUST** confine debug-only dependencies (leak detectors, network inspectors, debug UI overlays, test-only libraries) to `debugImplementation`/`testImplementation`; a debug library reachable from the release variant is non-conformant [R2]
- **MUST** remove verbose and debug logging from the release build — either by stripping it in the shrinker (which only works with minification enabled and the rule present, per `spec/android/security/` §A) or by routing logging through a release-safe implementation that drops those levels
- **MUST NOT** log personal data, credentials, tokens, or request/response payloads at any level (`spec/android/security/` §A, `spec/android/backend-contract/` §B)
- **MUST NOT** leave a non-production endpoint, a feature bypass, a fake-data switch, or a hidden developer screen reachable in the release variant; environment selection happens through build types or flavors, resolved at build time, never through a runtime toggle shipped to users
- **MUST** enable StrictMode in debug builds only, with disk and network detection on the thread policy and leak detection on the VM policy, and **MUST** fix a violation rather than suppress it — a StrictMode hit in the touched flow is a defect, not a warning [R3][R2]
- **MUST NOT** ship `android:debuggable=true`, and **MUST NOT** weaken TLS trust for convenience in any variant that can reach production data (`spec/android/security/` §C/§F)

### C. Stability budget

- **MUST** treat the Android vitals bad-behaviour thresholds as the ceiling, not the target: user-perceived crash rate 1.09 % and user-perceived ANR rate 0.47 % overall, 8 % per device model [R4]. An app whose crash-free rate is unknown has not met this requirement — the measurement path (in-app telemetry or the console) is a precondition, not an optional extra
- **MUST NOT** manufacture stability by swallowing exceptions: every caught exception is either turned into a user-visible state with a recovery action or rethrown; an empty catch block is non-conformant
- **MUST** keep the main thread free of blocking work, since the ANR budget is spent there — IO, database, and network work run on injected dispatchers (`spec/android/app-architecture/` §E)
- **MUST** survive process death and configuration change without losing user input or unsent writes (`spec/android/app-architecture/` §B), and **MUST** verify this explicitly for the touched flow — the "don't keep activities" developer option or a background-kill is the mechanical check
- **SHOULD** wire a crash-reporting path for released builds; where one exists it **MUST** respect the privacy rules (no personal data in breadcrumbs) and its symbol/mapping upload **MUST** be part of the release build, or the reports are unreadable

### D. Platform and dependency currency

- **MUST** keep `compileSdk` at the latest stable SDK and `targetSdk` at the latest stable SDK the app has been verified against; a lagging `targetSdk` is recorded with a reason and a date, never left implicit [R2]
- **MUST** record `minSdk` with its rationale, and **MUST** re-verify the touched flow on the newest platform version the app claims to support [R2]
- **MUST NOT** use non-SDK (hidden) interfaces; the lint check is the mechanical detector [R2]
- **MUST** declare dependencies through the version catalog (`spec/android/project-structure/` §B) and **MUST** keep them current. The automation and the vulnerability scan that make currency practical — Renovate/Dependabot plus a scanner in CI — are owned by `spec/android/security/` §F, which states them as a **SHOULD**; this spec deliberately strengthens the *outcome* (dependencies are current) to a MUST while leaving that spec's choice of *mechanism* recommended rather than required. A dependency bump that changes behaviour is verified on the release build like any other change
- **MUST** handle platform behaviour changes that the new `targetSdk` activates before raising it — the adaptive and edge-to-edge obligations are owned by `spec/android/screen-formats/` §B/§D and `spec/android/app-design-navigation/` §A, and are a precondition of the bump, not a follow-up

### E. The gate

- **MUST** treat this gate as the definition of "done" for any change to an Android project, and **MUST** report — never silently accept — any red element (repository REQ-1, REQ-7):
  1. `./gradlew build` is green
  2. Android Lint reports no error-severity finding in changed code, and **no new baseline entry was added** to achieve that; the security checks named in `spec/android/security/` §F are enforced at error severity — that spec states the enforcement as a SHOULD, and this gate requires it, so a project that never elevated them raises them before claiming the gate
  3. Unit tests pass, including the failure-mode coverage required by `spec/android/app-architecture/` §G and `spec/android/backend-contract/` §G
  4. The release variant assembles with the shrinker on (§A)
  5. The touched flow was exercised manually on a device running the **release** variant (§A)
  6. Every §B item is true of that variant
- **MUST NOT** add or refresh a lint baseline, disable a check, or annotate a suppression to make the gate pass on new code; a baseline entry is for pre-existing legacy findings only (`spec/android/project-structure/` §G)
- **MUST** state, when a gate element cannot be run (no device attached, no backend reachable), which one was skipped and why, in the run's final report — an unrunnable element is never silently treated as green
- **SHOULD** run the instrumented and screenshot lanes per `spec/android/test-automation/` §G where the change touches UI
- **SHOULD** report the artifact size delta and any startup or scroll regression the change is likely to have caused, using the measurement paths of `spec/android/long-list-scrolling/` §G

### F. Recording

- **MUST** record, with the change, any interim deviation this spec allows (a blanket keep rule, a lagging `targetSdk`, a skipped gate element) together with the reason and the condition for removing it
- **MUST** report an unspecified case rather than deciding silently (repository REQ-6)

## Acceptance Criteria

The criteria are a representative rollup of §A–§F, not a 1:1 mapping; every requirement bullet above is normative on its own.

- [ ] The release build type enables code and resource shrinking with optimization; debug and test build types do not
- [ ] Keep rules are specific and correctly located; no blanket keep, `-dontobfuscate`, or `-dontoptimize` exists without a dated, ticketed justification
- [ ] `mapping.txt` is retained for every release build that leaves the machine
- [ ] The touched flow was installed and exercised on a device from the release variant, and the release artifact assembles
- [ ] No debug-only dependency, verbose log, non-production endpoint, bypass switch, or hidden developer screen is reachable in the release variant
- [ ] The release variant is non-debuggable, no variant reaching production data weakens TLS trust, and no personal data, credential, token, or request/response payload is logged at any level
- [ ] No blocking work runs on the main thread in the touched flow
- [ ] StrictMode is active in debug with disk, network, and leak detection, and the touched flow produces no violation
- [ ] Crash-free and ANR rates are measurable and inside the vitals thresholds; no empty catch block exists in changed code
- [ ] The touched flow survives process death and configuration change without losing user input or unsent writes, verified with "don't keep activities" or a background-kill rather than by inspection
- [ ] Dependencies are declared in the version catalog and current, and any platform behaviour change activated by the `targetSdk` in use was handled before that SDK was adopted
- [ ] `compileSdk` is the latest stable, `targetSdk` is the latest verified (any lag recorded with reason and date), `minSdk` carries a rationale, and no non-SDK interface is used
- [ ] The six-element gate of §E is green, or every red or skipped element is named in the final report with its reason
- [ ] No lint baseline entry, check disablement, or suppression was added to pass the gate on new code

## Open Questions

Each question states the working default the requirements above already encode.

- App-wide startup (TTID/TTFD) and jank measurement methodology has no spec in this corpus; the perceived-performance capability operates without one. Should it get its own spec, or should §E gain quantified startup budgets? Default: §E requires a regression *report*, not a fixed number
- Should crash reporting be a MUST rather than a SHOULD for the operator's own apps, given the vitals budget cannot be verified without it? Default: SHOULD, because the measurement path may also be the Play Console
- Should the gate require a fresh-install run in addition to an upgrade-install run (migration paths break only on the latter)? Default: not required; §E's manual step does not fix the install mode
- Is a size-delta threshold worth fixing (for example, flag any change adding more than *n* KB), or does the report suffice? Default: report only

## References

- [R1] Shrink, obfuscate, and optimize your app (R8) — enabling the shrinker, keep rules, resource shrinking, `mapping.txt`, "always test the release build", DEX-modifying tooling caveat: <https://developer.android.com/build/shrink-code>
- [R2] Core app quality guidelines — testable criteria including `Production_Build_Quality`, `StrictMode_Compliance`, `Target_SDK_Version`, `Compile_SDK_Version`, `Non_SDK_Interfaces`, `SDK_Maintenance`, `Sensitive_Data_Logging`: <https://developer.android.com/docs/quality-guidelines/core-app-quality>
- [R3] StrictMode — thread and VM policies, penalties, debug-only guidance: <https://developer.android.com/reference/android/os/StrictMode>
- [R4] Android vitals — core vitals and bad-behaviour thresholds (user-perceived crash rate 1.09 %, ANR rate 0.47 %, 8 % per device; 28-day rolling window): <https://developer.android.com/topic/performance/vitals>
- [R5] Android Lint — running lint, severities, and baselines: <https://developer.android.com/studio/write/lint>
- [R6] Configure build variants — build types, flavors, and variant-scoped dependencies: <https://developer.android.com/build/build-variants>
