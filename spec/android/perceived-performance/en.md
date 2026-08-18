# Perceived Performance — Startup and Jank

Status: draft

## Context

Perceived performance is not one property. It is three, and they fail independently: how long the app takes to become usable (**startup**), whether the frames of an interaction arrive before their deadline (**jank**), and whether an unavoidable wait is communicated honestly (**wait indication**). An app can start fast and stutter, scroll smoothly and take four seconds to show anything, or do both well and still feel broken because a two-second wait shows nothing at all.

The recurring failure is not in the fixing but in the measuring. Four mistakes produce most of the wrong conclusions, and every requirement below exists to make one of them impossible:

- **Measuring the wrong build.** A debuggable, un-minified build has different code, different compilation, and different timings. Numbers from it are fiction — they both hide real problems and invent ones that will not exist in a release.
- **Measuring the wrong thing.** Time to first frame says when *something* appeared, not when the app became usable. An app that draws an empty skeleton in 200 ms and finishes loading at 3 s has a good TTID and a bad app.
- **Reporting a median.** Jank lives in the tail. A P50 inside the deadline is compatible with a visibly stuttering screen.
- **Reporting a number without its conditions.** A frame budget without its refresh rate, or a startup number without its device, build type, and compilation mode, cannot be compared to anything — including the same app last week.

This spec fixes what is measured, under which conditions a number counts, which budgets turn a number into a finding, and in what order findings are remediated.

Provenance: desk research (August 2026) over the Android vitals launch-time and rendering documentation (the source of the excessive-startup and frozen-frame thresholds), the Macrobenchmark documentation (module setup, metrics, compilation and startup modes), the Baseline Profile documentation (generation, verification, startup profiles), the app-startup optimization guide, and the JankStats and Perfetto documentation. Where this corpus fixes a number that no vendor source fixes, the requirement says so and labels it a portfolio decision.

Boundaries: **scroll** measurement is owned by `spec/android/long-list-scrolling/` §G — its `frameOverrunMs` percentile rules, its 700 ms defect rule, and its refusal to fix a scroll pass/fail percentile are authoritative and are referenced here, never restated or overridden. The wait-indication matrix belongs to `spec/android/ui-components/` §A and the response-time perception thresholds to `spec/android/app-design-navigation/` §F; this spec consumes both and defines neither. The benchmark lane's exclusion from the per-commit suite is owned by `spec/android/test-automation/` §F; device, trace, and log mechanics by `spec/android/adb-workflows/` §D/§E; the release-build configuration a measurement runs against by `spec/android/release-readiness/` §A; main-thread and dispatcher discipline by `spec/android/app-architecture/` §E; the crash and ANR stability budget by `spec/android/release-readiness/` §C.

Readers: authors of this repository's Android skills that measure or remediate performance, and reviewers judging whether a performance claim is evidence or impression.

## Goals

- Make an unqualified performance number impossible to report
- Separate "something is on screen" from "the app is usable", and require both
- Put the tail, not the median, at the centre of every jank claim
- Give each measurement a budget, so a millisecond value becomes a pass or a finding
- Fix the remediation order so the worst user-visible failure is fixed first
- Make the fix attributable: one change, one re-measurement

## Non-Goals

- Scroll-journey measurement and its budgets — `spec/android/long-list-scrolling/` §G
- Which indicator belongs to which wait, and the perception thresholds behind it — `spec/android/ui-components/` §A and `spec/android/app-design-navigation/` §F
- CI wiring and lane composition — `spec/android/test-automation/` §F/§G
- Release-build configuration, R8, and the stability (crash/ANR) budget — `spec/android/release-readiness/` §A/§C
- Memory, battery, and network-efficiency profiling; this spec covers time-to-usable and frame timing only
- Server-side latency; the client's answer to a slow backend is a wait indication, not a benchmark

## Requirements

### A. What is measured

- **MUST** report the three startup classes separately and never aggregate them: **cold** (process created from scratch), **warm** (process alive, activity recreated), **hot** (activity resumed from background) [R1]
- **MUST** report both display metrics for startup, because they answer different questions [R1]:
  - **TTID** (time to initial display) — the first frame is drawn. Answers "did anything happen".
  - **TTFD** (time to full display) — the app is actually usable with its content present. Answers "can the user do the thing".
- **MUST** instrument TTFD explicitly: `reportFullyDrawn()`, or in Compose `ReportDrawn` / `ReportDrawnWhen { … }` / `ReportDrawnAfter { … }`, placed where the screen's content is genuinely ready rather than where it is convenient [R1]. An app that never signals full display **MUST NOT** have a TTFD number reported for it — the absence is the finding
- **MUST** use the frame vocabulary consistently [R2]: a **janky frame** exceeds the display's deadline; a **slow frame** takes 16 ms–700 ms; a **frozen frame** takes over 700 ms and reads to the user as a hang
- **MUST** state the frame deadline the judgement is made against, since it is display-dependent — ~16.7 ms at 60 Hz, ~11.1 ms at 90 Hz, ~8.3 ms at 120 Hz [R2]
- **MUST** attach the conditions to every reported number: device model, Android version, build type, minification state, `CompilationMode`, refresh rate, and iteration count. A number without them is not comparable to any other number and **MUST NOT** be used to claim a regression or an improvement

### B. When a number counts

- **MUST** measure on a **physical device** — Macrobenchmark discourages emulators because their numbers are not representative of the end-user experience, and it raises an error on an emulator (or a low-battery device) that only an explicit `androidx.benchmark.suppressErrors=EMULATOR` instrumentation argument silences [R3][R9]. A run that needed the suppression is a smoke test of the benchmark code, not a measurement: an emulator is acceptable only for coarse loading-state UI checks, never for a reported startup or frame number
- **MUST** measure a **non-debuggable, minified, release-shaped** build with the target declared `profileable` [R3], matching the release configuration of `spec/android/release-readiness/` §A. A number from a debuggable or un-minified build **MUST NOT** be reported as a finding — the rule is the same one `spec/android/long-list-scrolling/` §G states for scroll
- **MUST** hold the compilation state constant across compared runs and state it: `CompilationMode.DEFAULT` reflects what users get once a Baseline Profile ships, `None` reflects the worst case, `Full` reflects neither [R3]
- **MUST** run enough iterations for the tail to exist — `measureRepeated` requires an explicit `iterations` value, and the five of the vendor sample is the floor, not a platform default — and **MUST** report the distribution, not a single value [R3]
- **MUST** neutralize the obvious confounders before a run: animations disabled per `spec/android/adb-workflows/` §E, device not thermally throttled, screen on, and no unrelated foreground work
- **MUST** re-measure on the same device and configuration when comparing against a baseline; a cross-device comparison is a different measurement, not a regression signal

### C. Budgets

- **MUST** treat the Android vitals excessive-startup thresholds as the **ceiling**, never the target: cold ≥ 5 s, warm ≥ 2 s, hot ≥ 1.5 s are the points at which the platform considers startup defective [R1][R8]. An app anywhere near them has a finding, not a budget
- **MUST** treat any **frozen frame** (over 700 ms) as a defect regardless of how rare it is; vendor guidance is that no frame should ever take that long [R2]. This matches, and does not restate differently from, `spec/android/long-list-scrolling/` §G
- **MUST** report frame timing at P50/P90/P95/P99 and judge on the tail; a P50 inside the deadline proves nothing [R2]
- **MUST** treat a regression against the app's own previous baseline as a finding even when the absolute number is inside budget — a 40 % startup regression that stays under the ceiling is still a defect that shipped
- **Portfolio decisions**, stated as such because no vendor source fixes them. They are this corpus's working numbers, revisable, and a skill **MUST** label **each of them** as a corpus decision when reporting rather than presenting it as a platform requirement. The vendor-sourced rules above — the vitals ceiling and the frozen-frame defect rule — are **not** in this group and **MUST NOT** be labelled as corpus decisions:
  - **TTID, cold start: ≤ 500 ms.** The device this holds for is the device the app's baseline was established on, and the report **MUST** name it: the same code can pass on one mid-range phone and fail on another, so this number is a per-app target, never a cross-device constant
  - **TTFD: judged against the app's own baseline**, not an absolute, because it is bounded by the data the screen needs — and against the wait indication its loading states owe the user (`spec/android/ui-components/` §A)
  - **Non-scroll animation paths: P95 frame duration within the deadline.** (Zero frozen frames is the vendor rule above, not part of this decision.)
- **MUST NOT** apply any percentile budget to a **scroll** journey: `spec/android/long-list-scrolling/` §G deliberately refuses to fix one because no vendor source does, and inventing one here would override an owning spec. Report the scroll number with its tail and say that no pass/fail percentile is fixed

### D. Startup methodology

- **MUST** produce the reported startup number with a Macrobenchmark `StartupTimingMetric` run [R3]; `am start -W` and the `ActivityManager: Displayed` logcat line are a quick local check only, they measure TTID alone, and they **MUST NOT** be the basis of a reported finding. The local TTFD counterpart is the `ActivityManager: Fully drawn <pkg>/.<Activity>: +<time>` logcat line the system prints once the app has signalled full display [R1] — the same status applies: a check that the §A instrumentation fires and roughly when, never a reported number, and its absence after the screen is visibly ready is itself the §A finding
- **MUST** cover cold as the primary case, since optimizing cold improves warm and hot [R1], and report warm and hot alongside it rather than instead of it
- **MUST** locate a slow startup before fixing it rather than guessing at `Application.onCreate()`: capture a Perfetto trace with the invocation `spec/android/adb-workflows/` §D owns, and read it against the documented startup phases [R1][R5]. Capture mechanics are that spec's; the reading and the verdict are this one's
- **MUST** check the four documented startup cost centres before proposing anything else [R1]: work in `Application.onCreate()` and in eagerly-initialized content providers, heavy activity/first-screen initialization, blocking I/O or bitmap decoding on the main thread, and a custom splash-screen activity where the platform `SplashScreen` API belongs
- **SHOULD** prefer the App Startup library or explicit lazy initialization over a content provider per dependency, and `by lazy` over eager singletons [R1][R7]

### E. Jank methodology

- **MUST** produce a reported jank number with Macrobenchmark `FrameTimingMetric` [R3], reading `frameOverrunMs` where available, as `spec/android/long-list-scrolling/` §G already requires for scroll
- **MUST NOT** base a jank finding on `dumpsys gfxinfo framestats` alone, Compose surface or not: the vendor documentation scopes that instrument to apps drawing through the `View`-based toolkit (`Canvas`/View hierarchy — which includes Compose, whose `AndroidComposeView` renders through the same HWUI pipeline) and states that render statistics are unavailable for Vulkan, Unity, Unreal, and OpenGL surfaces [R2]. The instrument therefore *does* see a Compose screen; the reason it stays a coarse local signal is what it is, not what it covers — a per-process histogram without the per-frame overrun, iteration control, compilation-state, and condition record that §A/§B require. The reported number comes from `FrameTimingMetric` [R3]; a Vulkan/GL surface has no `gfxinfo` signal at all
- **MUST** locate the cause with a trace before remediating — Perfetto's frame timeline shows which frames missed and what the main thread was doing [R2][R5]. A jank remedy proposed without a trace is a guess
- **MUST** classify the cause into the documented families rather than reporting "it is slow" [R2]: main-thread work (I/O, binder calls, lock contention, allocation and GC pressure), rendering-thread work (oversized bitmap uploads, expensive paths), layout and recomposition cost, and image or data work that belongs off the main thread
- **MUST** route a scroll surface's measurement and interpretation to `spec/android/long-list-scrolling/` §G, including its rule that a framework change is never the remedy for a slow list

### F. Baseline and startup profiles

- **MUST** ship a Baseline Profile for any app whose startup or scrolling is measured; it is the highest-leverage single change available, with vendor-reported improvements around 30 % in code execution from first launch [R4]
- **MUST** generate it with the Baseline Profile Gradle Plugin and a `BaselineProfileRule` journey — never by hand-editing `baseline-prof.txt` — and **MUST** cover startup, the main navigation paths, and the app's main list scroll (the scroll journey is already required by `spec/android/long-list-scrolling/` §G) [R4]
- **MUST** verify the profile against the **minified release** build, and **MUST NOT** verify it against the un-minified generation build [R4]
- **MUST** keep `androidx.profileinstaller` present and current, and **MUST NOT** introduce post-R8 DEX-modifying tooling that would invalidate the profile or the DEX layout (`spec/android/release-readiness/` §A) [R4]
- **SHOULD** add a Startup Profile alongside it for DEX-layout optimization where the AGP version supports it [R4]
- **MUST** regenerate the profile when the journeys it covers change materially; a profile describing last year's navigation optimizes code the app no longer runs

### G. Benchmark module and result handling

- **MUST** keep benchmarks in a separate `com.android.test` module with its own `benchmark` build type derived from `release` (non-debuggable, minified, `matchingFallbacks` set for multi-module projects), and the target app declared `profileable` [R3]
- **MUST NOT** add the benchmark lane to the per-commit CI suite — it is a separate scheduled lane per `spec/android/test-automation/` §F
- **MUST NOT** commit trace files or raw benchmark output to the repository; they are build outputs [R3]. What is committed, when a regression gate is wanted, is a small baseline record carrying the numbers **and** the §A conditions they were measured under; the file's format is free, its condition fields are not
- **MUST** state in the run report which numbers are new, which are compared against a baseline, and which had no baseline to compare against

### H. Remediation order and attribution

- **MUST** remediate in user-impact order, not in the order findings were discovered [R2]: ANRs and frozen frames first, then startup against §C, then slow frames, then everything else
- **MUST** apply **one** remediation at a time and re-measure the metric it targeted before applying the next; batching destroys attribution and is how a regression gets shipped alongside an improvement
- **MUST** record the before/after delta with the conditions of both runs, and **MUST** report a remediation that did not move its number as such rather than keeping it because it seemed reasonable
- **MUST** report a red build or a failed measurement rather than stacking further edits on top of it (repository REQ-1, REQ-7)
- **MUST** report a gap and propose a spec extension when a decision this spec does not cover is needed, rather than deciding silently (repository REQ-6)

### I. Field measurement

- **SHOULD** wire JankStats for field frame timing, since lab measurement covers the devices and journeys someone thought to test and field data covers the rest [R2][R6]
- **MUST**, where field telemetry exists, keep personal data out of performance events entirely. This is this spec's own rule: `spec/android/security/` §A bans logging sensitive data and its §E governs the disclosure duty for third-party SDK data flows, but neither states a telemetry-payload rule, so it is fixed here
- The crash-free and ANR budgets that field data is judged against are owned by `spec/android/release-readiness/` §C and are not restated here

## Acceptance Criteria

The criteria are a representative rollup of §A–§I, not a 1:1 mapping; every requirement bullet above is normative on its own.

- [ ] Every reported number carries its device, Android version, build type, minification state, `CompilationMode`, refresh rate, and iteration count
- [ ] Startup is reported as cold, warm, and hot separately, with both TTID and TTFD; an app without full-display instrumentation is reported as such instead of getting a TTFD number
- [ ] Every reported number comes from a physical device running a non-debuggable, minified, profileable build; no emulator or debug-build number is presented as a finding
- [ ] Startup numbers come from `StartupTimingMetric` and frame numbers from `FrameTimingMetric`; `am start -W`, the `Displayed`/`Fully drawn` logcat lines, and `gfxinfo` appear only as local checks, and no jank finding rests on `gfxinfo` alone
- [ ] Frame timing is reported at P50/P90/P95/P99 with the deadline stated; no scroll journey is judged against an invented percentile budget
- [ ] Any frozen frame is reported as a defect; startup is judged against the vitals ceiling and the corpus target, and **each** §C portfolio decision is labelled as a corpus decision in the report while the vendor-sourced rules are not
- [ ] Compared runs hold `CompilationMode` constant and state it, run on the same device and configuration, and were taken with animations disabled on a thermally unthrottled device
- [ ] Every jank finding names its cause family (main thread, render thread, layout/recomposition, or off-main-thread work) rather than reporting that a screen is slow
- [ ] A regression against the app's own baseline is reported as a finding even when the absolute value is inside budget
- [ ] A Baseline Profile exists, is plugin-generated from a journey covering startup, navigation, and the main list scroll, and is verified against the minified release build
- [ ] Benchmarks live in a separate `com.android.test` module on a release-derived `benchmark` build type and are absent from the per-commit CI suite
- [ ] No trace file or raw benchmark output is committed; any committed baseline record carries the §A conditions
- [ ] Remediations are applied one at a time, each re-measured against the metric it targeted, with the delta and both runs' conditions recorded — including remediations that did not help
- [ ] Where field performance telemetry (JankStats or equivalent) exists, its event payloads carry no personal data — no identifiers, free text, or screen content beyond the metric, the screen or journey name, and the §A conditions

## Open Questions

Each question states the working default the requirements above already encode.

- The scroll pass/fail percentile stays unfixed, inherited from `spec/android/long-list-scrolling/` §Open Questions: no vendor source fixes one. Default: report the tail, claim no verdict. Fixing it would require this corpus's own measurements across devices
- Should the corpus name one reference device so cold-TTID numbers compare across apps? Parking-lot: §C resolves the ambiguity by scoping the target to the device an app's own baseline was taken on and requiring the report to name it, so no run is blocked. Naming a portfolio-wide reference device would need hardware this corpus does not have; until then, cross-app comparison of the absolute number is explicitly not claimed
- Should a committed baseline record be mandatory rather than conditional on wanting a regression gate? Default: conditional — §G fixes its content, not its existence
- Should field JankStats be a MUST for the operator's own apps? Default: SHOULD, since a solo app may legitimately have no telemetry pipeline

## References

- [R1] App startup time — cold/warm/hot, TTID and TTFD, `reportFullyDrawn` and the Compose `ReportDrawn*` APIs, the vitals excessive-startup thresholds, and the documented startup cost centres: <https://developer.android.com/topic/performance/vitals/launch-time>
- [R2] Slow rendering — janky, slow, and frozen frame definitions and thresholds, the per-refresh-rate deadline, the measurement instruments and their scope, and the documented jank cause families: <https://developer.android.com/topic/performance/vitals/render>
- [R3] Macrobenchmark overview — separate `com.android.test` module, release-derived benchmark build type, profileable target, `StartupTimingMetric`/`FrameTimingMetric`, `CompilationMode`, `StartupMode`, iterations, emulator discouraged (error unless suppressed), and trace output location: <https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview>
- [R4] Baseline Profiles overview — generation via the Gradle plugin and `BaselineProfileRule`, journey coverage, minified-release verification, startup profiles, and `ProfileInstaller` requirements: <https://developer.android.com/topic/performance/baselineprofiles/overview>
- [R5] Perfetto — trace capture and the frame timeline used to locate missed frames and startup phases: <https://perfetto.dev/docs/>
- [R6] JankStats — field frame-timing collection: <https://developer.android.com/topic/performance/jankstats>
- [R7] App Startup library — replacing per-dependency content providers with explicit initialization order: <https://developer.android.com/topic/libraries/app-startup>
- [R8] Android vitals — the metric set and thresholds the platform judges an app by: <https://developer.android.com/topic/performance/vitals>
- [R9] Macrobenchmark instrumentation arguments — `androidx.benchmark.suppressErrors` and the `EMULATOR`/`LOW-BATTERY` error classes it silences: <https://developer.android.com/topic/performance/benchmarking/macrobenchmark-instrumentation-args>
