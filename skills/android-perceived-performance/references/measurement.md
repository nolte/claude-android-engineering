# Measurement recipes

Concrete command recipes for the MEASURE phase. All device interaction follows
`spec/android/adb-workflows/` (explicit `-s` targeting, boot gating, timeout-wrapped
hang-prone calls, animation scales at 0). Measure a **release-shaped, non-debuggable**
variant on a **physical device**; benchmarks are a scheduled lane, never the per-commit
suite (`spec/android/test-automation/` §F).

## Table of contents

- [Device preconditions](#device-preconditions)
- [Startup: quick ADB signal](#startup-quick-adb-signal)
- [Startup: Macrobenchmark (authoritative)](#startup-macrobenchmark-authoritative)
- [Jank: dumpsys gfxinfo framestats](#jank-dumpsys-gfxinfo-framestats)
- [Jank: Macrobenchmark FrameTimingMetric](#jank-macrobenchmark-frametimingmetric)
- [Perfetto system trace](#perfetto-system-trace)
- [Baseline Profiles: generation and verification](#baseline-profiles-generation-and-verification)
- [Loading-state audit (no device numbers)](#loading-state-audit-no-device-numbers)

## Device preconditions

- One `platform-tools` adb: `which -a adb`. Target explicitly: `export ANDROID_SERIAL=<serial>` or `-s <serial>` per call.
- Gate on real boot: `adb wait-for-device` then poll `sys.boot_completed` until `1`.
- Deterministic UI: `adb shell settings put global window_animation_scale 0.0` and the same for `transition_animation_scale` and `animator_duration_scale`.
- Install a release-shaped, R8-minified build (`./gradlew installRelease` for a locally-signable variant, or `bundletool` for a bundle). A debuggable build distorts every timing.
- Discard the first cold start after install (one-time dexopt/profile install); measure subsequent cold starts.

## Startup: quick ADB signal

Coarse, good for a fast read before the Macrobenchmark run:

```
adb shell am force-stop <pkg>
adb shell am start -W -n <pkg>/<launcher-activity>
```

- `TotalTime` / `WaitTime` from `am start -W` approximate **TTID** (time to initial display).
- Corroborate against logcat: the `ActivityManager: Displayed <pkg>/<activity>: +NNNms` line.
- Resolve the launcher activity when unknown: `adb shell cmd package resolve-activity --brief <pkg>`.
- **TTFD** (time to *full* display) comes from the app's own `reportFullyDrawn()`; `am start -W` cannot see it.

Repeat cold starts ≥5 times, discard the first, report the median.

## Startup: Macrobenchmark (authoritative)

Prefer `androidx.benchmark:benchmark-macro-junit4` for stable, repeatable startup numbers. A benchmark module is a separate `com.android.test` module targeting the app; scaffold it with the **Kotlin DSL and KSP**, never kapt/Groovy (REQ-9).

```kotlin
@get:Rule val rule = MacrobenchmarkRule()

@Test fun startupCold() = rule.measureRepeated(
    packageName = "<pkg>",
    metrics = listOf(StartupTimingMetric()),
    iterations = 10,
    startupMode = StartupMode.COLD,
) {
    pressHome(); startActivityAndWait()
}
```

- `StartupTimingMetric` reports `timeToInitialDisplayMs` (TTID) and, when the app calls `reportFullyDrawn()`, `timeToFullDisplayMs` (TTFD).
- Run `COLD`, `WARM`, and `HOT` startup modes; report each separately.
- Run against a release build type with `CompilationMode.Partition`/`Full` as appropriate; see the Baseline Profiles section for measuring the profile's effect.
- Run on a physical device; the run is a scheduled lane, never wired into per-commit CI.

## Jank: dumpsys gfxinfo framestats

```
adb shell dumpsys gfxinfo <pkg> reset      # reset immediately before the scenario
# ... exercise the target screen (scroll, animate) ...
adb shell dumpsys gfxinfo <pkg>            # summary: Janky frames %, percentiles
adb shell dumpsys gfxinfo <pkg> framestats # per-frame nanosecond timestamps
```

- The summary block reports `Total frames rendered`, `Janky frames` (count and %), and the 50th/90th/95th/99th percentile frame durations.
- `framestats` gives per-frame timestamps (columns documented by the platform) so you can compute per-frame GPU/CPU durations and locate the frames that blew the deadline.
- Always `reset` first — the counters accumulate across the whole process lifetime otherwise.
- Wrap the calls in `timeout` (hang-prone) per `spec/android/adb-workflows/` §E.

## Jank: Macrobenchmark FrameTimingMetric

More repeatable than `gfxinfo` for a defined interaction:

```kotlin
rule.measureRepeated(
    packageName = "<pkg>",
    metrics = listOf(FrameTimingMetric()),
    iterations = 10,
) {
    startActivityAndWait()
    // drive the scroll/animation under test via UiAutomator
}
```

- Reports `frameDurationCpuMs` and `frameOverrunMs` percentiles (P50/P90/P99). `frameOverrunMs` > 0 means the frame missed its deadline — the direct jank signal.

## Perfetto system trace

For any stutter that framestats flags, capture a system trace to locate the offending work:

```
python3 record_android_trace -o trace.perfetto-trace -t 10s -b 32mb \
  sched freq gfx view wm am binder_driver
```

- `record_android_trace` is the sanctioned boundary tool (`spec/android/adb-workflows/` §D). Open the trace in the Perfetto UI; look for long `Choreographer#doFrame` slices, main-thread work during scroll, and binder/IO stalls.
- Use the trace to attribute jank to a cause before proposing a remediation — never guess.

## Baseline Profiles: generation and verification

- Generate with `androidx.benchmark:benchmark-macro-junit4`'s `BaselineProfileRule` (a `baseline-prof.txt` covering the critical user journey and app startup). Prefer the `androidx.baselineprofile` Gradle plugin (Kotlin DSL) to wire generation and consumption.
- **Verify on a release install only.** Measure startup with a Macrobenchmark run comparing `CompilationMode.None()` vs `CompilationMode.Partial(baselineProfile)`; the profile's benefit shows only on a non-debuggable build with profile compilation. Verifying on a debug build is a false negative.

## Loading-state audit (no device numbers)

This is a code/UX audit, not a device measurement — read the composables and compare
to `references/thresholds.md`:

- Every tap has instant visual feedback; no indicator appears below ~200 ms.
- Short indeterminate waits (200 ms–5 s) show a loading indicator; waits beyond ~5–10 s show a determinate progress indicator with a cancel affordance.
- One indicator per group; the same process uses the same indicator variant app-wide; no in-place loading→determinate hand-off.
- Skeleton screens are acceptable for content that loads in place; a spinner that blocks the whole screen for a long wait is a finding.
