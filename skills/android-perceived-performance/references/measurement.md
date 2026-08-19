# Measurement recipes

Concrete command recipes for the MEASURE phase. All device interaction follows
`spec/android/adb-workflows/` (explicit `-s` targeting, boot gating, timeout-wrapped
hang-prone calls, animation scales at 0). Measure a **release-shaped, non-debuggable**
variant on a **physical device**; benchmarks are a scheduled lane, never the per-commit
suite (`spec/android/test-automation/` §F).

## Table of contents

- [Benchmark module setup](#benchmark-module-setup)
- [Device preconditions and pre-flight](#device-preconditions-and-pre-flight)
- [Startup: quick ADB signal](#startup-quick-adb-signal)
- [Startup: Macrobenchmark (authoritative)](#startup-macrobenchmark-authoritative)
- [Startup: reading the trace (four cost centres)](#startup-reading-the-trace-four-cost-centres)
- [Jank: dumpsys gfxinfo framestats](#jank-dumpsys-gfxinfo-framestats)
- [Jank: Macrobenchmark FrameTimingMetric](#jank-macrobenchmark-frametimingmetric)
- [Perfetto system trace](#perfetto-system-trace)
- [Baseline Profiles: generation and verification](#baseline-profiles-generation-and-verification)
- [Baseline record](#baseline-record)
- [Loading-state audit (no device numbers)](#loading-state-audit-no-device-numbers)

## Benchmark module setup

`spec/android/perceived-performance/` §B/§G fix the infrastructure a reportable number needs. Check it before the first run; scaffold what is missing only after operator confirmation (REQ-8), Kotlin DSL and KSP only (REQ-9):

- **Target app is `profileable`.** Either in the manifest —
  `<application><profileable android:shell="true" /></application>` (scoped to the benchmark build type via a manifest overlay if the release manifest must stay clean) — or on the build type with `isProfileable = true` (AGP 7.3+ exposes it on the build type DSL).
- **A dedicated `benchmark` build type derived from `release`**, in `:app`:

  ```kotlin
  buildTypes {
      create("benchmark") {
          initWith(getByName("release"))
          signingConfig = signingConfigs.getByName("debug")   // installable locally, still R8-minified
          matchingFallbacks += listOf("release")              // library modules resolve to release
          isDebuggable = false
          isProfileable = true
      }
  }
  ```

  Library modules that only declare `debug`/`release` resolve through `matchingFallbacks`; without it a multi-module build fails variant resolution.
- **Benchmarks in a separate `com.android.test` module** (`:benchmark`), `targetProjectPath = ":app"`, `testOptions.managedDevices` unused (physical device), `experimentalProperties["android.experimental.self-instrumenting"] = true`, `androidx.benchmark:benchmark-macro-junit4` as an `implementation`. The `benchmark` build type in this module `isDebuggable = false` too. Configure the Macrobenchmark instrumentation arguments (`androidx.benchmark.suppressErrors` only for a documented reason).
- **Never in per-commit CI**: the module has its own scheduled lane (`spec/android/test-automation/` §F).
- **Never commit** the outputs: add `*.perfetto-trace`, `**/build/outputs/connected_android_test_additional_output/`, and benchmark JSON to `.gitignore` if not already covered. See §"Baseline record" for what is committed instead.

## Device preconditions and pre-flight

- One `platform-tools` adb: `which -a adb`. Target explicitly: `export ANDROID_SERIAL=<serial>` or `-s <serial>` per call.
- Gate on real boot: `adb wait-for-device` then poll `sys.boot_completed` until `1`.
- Deterministic UI: `adb shell settings put global window_animation_scale 0.0` and the same for `transition_animation_scale` and `animator_duration_scale`.
- Install the `benchmark` variant (release-shaped, R8-minified, profileable): `./gradlew :app:installBenchmark`, or `bundletool` for a bundle. A debuggable build distorts every timing.
- Discard the first cold start after install (one-time dexopt/profile install); measure subsequent cold starts.

**Confounder pre-flight (spec §B, MUST) — run before every measurement batch and record the result:**

```
adb shell dumpsys thermalservice | grep -i 'status\|throttl'   # thermal status 0 / NONE; wait if higher
adb shell dumpsys power | grep -i 'mWakefulness\|Display Power'  # screen on (Awake / state=ON)
adb shell dumpsys activity activities | grep -i 'topResumed\|ResumedActivity'  # nothing else in front
adb shell dumpsys battery | grep -i 'level\|AC powered'         # keep charger state constant across compared runs
```

- **Not thermally throttled**: status must be `NONE` (0); a device that just ran a build or a benchmark batch is often `LIGHT`/`MODERATE` — let it cool, re-check.
- **Screen on and unlocked** (`adb shell input keyevent KEYCODE_WAKEUP`, then dismiss the keyguard); a screen-off run measures nothing user-visible.
- **No unrelated foreground work**: close other apps (`am force-stop` the usual suspects), no active download, sync, or Play Store update.

**Capture the run conditions before the first measurement** — `spec/android/perceived-performance/` §A
makes a number without them unreportable, and a resumed run cannot reconstruct them:

```
adb shell getprop ro.product.model            # device model
adb shell getprop ro.build.version.release    # Android version
adb shell getprop ro.build.version.sdk        # API level
adb shell dumpsys display | grep -i 'fps\|refreshRate'   # active refresh rate -> the frame deadline
```

Record these alongside the build type, minification state, `CompilationMode`, and iteration
count, and carry them in the resume state so every later table can restate them.

## Startup: quick ADB signal

Coarse, good for a fast read before the Macrobenchmark run:

```
adb shell am force-stop <pkg>
adb shell am start -W -n <pkg>/<launcher-activity>
```

- `TotalTime` / `WaitTime` from `am start -W` approximate **TTID** (time to initial display).
- Corroborate against logcat: the `ActivityManager: Displayed <pkg>/<activity>: +NNNms` line.
- Resolve the launcher activity when unknown: `adb shell cmd package resolve-activity --brief <pkg>`.
- **TTFD** (time to *full* display) comes from the app's own `reportFullyDrawn()`; `am start -W` cannot see it. The local check is the logcat line `ActivityManager: Fully drawn <pkg>/<activity>: +NNNms` (`adb logcat -s ActivityManager | grep 'Fully drawn'`) — it only appears when the app reports full draw, so its absence is the "no TTFD instrumentation" finding, not a logging problem.

Repeat cold starts ≥5 times, discard the first, and report the distribution — median plus the slowest run — never a single value (`spec/android/perceived-performance/` §B).

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
- Run against a release build type and state the `CompilationMode`: `DEFAULT` reflects what users get once a Baseline Profile ships, `None` the worst case, `Full` neither. The spec requires holding it constant across compared runs and stating it (`spec/android/perceived-performance/` §B); it elects no default, so the choice is the operator's — see the Baseline Profiles section for measuring the profile's effect.
- Run on a physical device; the run is a scheduled lane, never wired into per-commit CI.

## Startup: reading the trace (four cost centres)

`spec/android/perceived-performance/` §D: locate a slow startup in a trace **before** proposing anything — guessing at `Application.onCreate()` is not a method. Capture a cold-start trace (`am force-stop`, then start under `record_android_trace` — invocation below), open it in the Perfetto UI, and walk the startup phases (process start → `bindApplication` → `activityStart` → first frame → `reportFullyDrawn`). Check the four documented cost centres in this order and write down which the trace shows:

1. **`Application.onCreate()` and eagerly-initialized content providers** — long slices under `bindApplication`; every library `ContentProvider` in the merged manifest runs before your first line of code.
2. **Heavy activity / first-screen initialization** — `activityStart`/`activityResume` slices, first composition, expensive `ViewModel` construction, DI graph built eagerly.
3. **Blocking I/O or bitmap decoding on the main thread** — `binder transaction`, file/DB reads, `decodeBitmap`/`ImageDecoder` slices on the main thread between process start and first frame.
4. **A custom splash-screen activity** where the platform `SplashScreen` API belongs — a second activity start visible in the trace before the real first screen.

Only after naming the cost centre(s) does the FIX phase pick a remedy — the remedy list in SKILL.md Phase 2 is ordered by this reading, not by signal strength.

## Jank: dumpsys gfxinfo framestats (coarse local check only)

**Not the source of a reported number.** `spec/android/perceived-performance/` §E scopes this
instrument to View-toolkit surfaces, following the vendor documentation, and forbids resting a
Compose jank finding on it alone. Use it to get a quick local signal or on a View-based screen;
report from `FrameTimingMetric` below.

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

The reported number for any surface, and the only admissible one for Compose
(`spec/android/perceived-performance/` §E):

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

- Reports `frameDurationCpuMs` and `frameOverrunMs` percentiles. Report **P50/P90/P95/P99**: P95 is the percentile the non-scroll animation budget is judged on (`spec/android/perceived-performance/` §C) and P99 is where the worst stutter hides. `frameOverrunMs` > 0 means the frame missed its deadline — the direct jank signal.
- Classify frames with the spec vocabulary: janky (over the deadline), slow (16–700 ms), frozen (over 700 ms — always a defect).
- **Cause family (spec §E, MUST):** every jank finding is assigned, from the trace, to exactly one of: main-thread work (I/O, binder, lock contention, allocation/GC), render-thread work (oversized bitmap uploads, expensive paths), layout/recomposition cost, or image/data work that belongs off the main thread. Perfetto's frame timeline shows which frames missed and what the main thread and RenderThread were doing at the time.

## Perfetto system trace

For any stutter the frame metric flags, capture a system trace to locate the offending work. Use the invocation shape `spec/android/adb-workflows/` §D owns — output path, duration, buffer size, app filter, categories — with the categories the question needs:

```
python3 record_android_trace -o trace.perfetto-trace -t 20s -b 32mb -a <pkg> \
  sched freq view input am wm gfx        # add binder_driver when IPC stalls are suspected
```

- `record_android_trace` is the sanctioned boundary tool (`spec/android/adb-workflows/` §D). Open the trace in the Perfetto UI; look for long `Choreographer#doFrame` slices, main-thread work during scroll, and binder/IO stalls.
- Use the trace to attribute jank to a cause before proposing a remediation — never guess.

## Baseline Profiles: generation and verification

`spec/android/perceived-performance/` §F — a profile is a MUST for any app whose startup or scroll is measured:

- Generate with the **Baseline Profile Gradle Plugin** (`androidx.baselineprofile`, Kotlin DSL) and a `BaselineProfileRule` journey in the `:benchmark`/`:baselineprofile` `com.android.test` module — never by hand-editing `baseline-prof.txt`.
- **Journey content:** startup **plus the main navigation paths plus the app's main list scroll** (the scroll journey is also required by `spec/android/long-list-scrolling/` §G). A profile that covers startup only is incomplete.
- **`androidx.profileinstaller`** is present in `:app` and current (the plugin adds it; verify the resolved version) — without it the profile is not installed on devices that need it.
- **Verify on the minified release install only** (`CompilationMode.None()` vs `CompilationMode.Partial(BaselineProfileMode.Require)`); never against the un-minified generation build. Verifying on a debug build is a false negative.
- **Regenerate** when the covered journeys change materially (new navigation graph, new main list, restructured startup); record the generation date and the journeys in the run report.
- **No post-R8 DEX-modifying tooling** (obfuscators, DEX rewriters, "optimizers" that run after R8): it invalidates the profile and the DEX layout (`spec/android/release-readiness/` §A).
- SHOULD add a **Startup Profile** alongside it (`startup-prof.txt` via the plugin's `includeInStartupProfile`) for DEX-layout optimization where the AGP version supports it.

## Baseline record

`spec/android/perceived-performance/` §G: traces and raw benchmark output are build outputs and are **never committed**. When a regression gate is wanted, commit a small record — format free, condition fields mandatory. Suggested shape (`benchmark/baseline.yml`):

```yaml
recorded_at: 2026-08-19
device: { model: "Pixel 7a", android: "16", api: 36, refresh_hz: 90 }
build: { type: benchmark, minified: true, profileable: true, compilation_mode: DEFAULT }
iterations: 10
preflight: { animations_off: true, thermal_status: NONE, screen_on: true, foreground_idle: true }
startup_ms:
  cold: { ttid_p50: 412, ttid_max: 468, ttfd_p50: 890, ttfd_max: 1010 }
  warm: { ttid_p50: 180, ttfd_p50: 350 }
  hot:  { ttid_p50: 95,  ttfd_p50: 140 }
frames:
  main_list_scroll: { overrun_ms: { p50: -3.1, p90: 0.8, p95: 2.4, p99: 9.7 }, frozen: 0, deadline_ms: 11.1 }
```

Every §A condition (device model, Android version, build type, minification, `CompilationMode`, refresh rate, iteration count) is a required field; a record missing one cannot be compared against. The report states, per number, whether it is new, compared against this record, or had no baseline.

## Loading-state audit (no device numbers)

This is a code/UX audit, not a device measurement — read the composables and compare
to the wait-indication matrix and response-time thresholds (SKILL.md Phase 1 step 4 and its
thresholds reference):

- Every tap has instant visual feedback; no indicator appears below ~200 ms.
- Short indeterminate waits (200 ms–5 s) show a loading indicator; beyond ~5 s a progress indicator, determinate as soon as progress is known (`spec/android/ui-components/` §A); beyond ~10 s additionally a cancel affordance and a backgroundable operation (`spec/android/app-design-navigation/` §F). Two thresholds, two obligations.
- One indicator per group; the same process uses the same indicator variant app-wide; no in-place loading→determinate hand-off.
- Skeleton screens are acceptable for content that loads in place; a spinner that blocks the whole screen for a long wait is a finding.
