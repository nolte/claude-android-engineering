# Remediation catalog

Maps each finding class to its concrete remediation. Apply one remediation at a time,
behind an operator approval gate (REQ-8), then rebuild (`./gradlew build`, REQ-1/REQ-7)
and re-measure the targeted number before proposing the next. Never batch — batching
destroys attribution.

## Table of contents

- [Slow cold start (high TTID/TTFD)](#slow-cold-start-high-ttidttfd)
- [Jank on scroll or animation](#jank-on-scroll-or-animation)
- [Main-thread stalls](#main-thread-stalls)
- [Missing or wrong loading states](#missing-or-wrong-loading-states)
- [Remediation discipline](#remediation-discipline)

## Slow cold start (high TTID/TTFD)

**Trace-first order** (`spec/android/perceived-performance/` §D): the Perfetto cold-start trace has already been read against the four documented cost centres (SKILL.md Phase 1 step 2). Remediate the cost centre the trace named, in this order — a Baseline Profile is added afterwards, and never as a substitute for removing traced work:

1. **`Application.onCreate()` and eager content providers (cost centre 1).** Move non-essential initialization out of `Application.onCreate()` and off the startup critical path; replace per-library `ContentProvider` initializers with `androidx.startup` `Initializer`s with lazy dependencies, or defer to first use. Audit every library initializer that runs eagerly at launch (merged-manifest `<provider>` entries).
2. **Heavy first-screen initialization (cost centre 2).** Replace eager singletons and eager DI graph construction on the startup path with lazy providers (`by lazy`); construct only what the first frame needs; keep the first composition small.
3. **Blocking I/O or bitmap decoding on the main thread (cost centre 3).** Move disk, DB, network, and `decodeBitmap`/`ImageDecoder` work off the main thread before the first frame; pre-size or defer images; inject dispatchers, never hard-code them.
4. **Custom splash activity (cost centre 4).** Replace it with the platform `SplashScreen` API (`androidx.core:core-splashscreen`) — one activity start fewer in the trace.
5. **Report full draw.** Call `reportFullyDrawn()` (or the Compose `ReportDrawn` APIs) where the content is genuinely ready, so TTFD is measurable and the platform can optimize; a screen that never reports full draw hides its true cost.
6. **Baseline Profile (+ Startup Profile).** Required for any measured app and the highest-leverage *code-execution* change (~30 % vendor-reported) — but it optimizes the work that remains, so it comes after the traced cost centre is removed. Journey covers startup, main navigation, and the main list scroll; plugin-generated (`androidx.baselineprofile`, Kotlin DSL — never kapt/Groovy, never hand-edited); `androidx.profileinstaller` present; verified on the **minified release** install only; regenerated when journeys change; no post-R8 DEX-modifying tooling. Generation and verification recipe: SKILL.md Phase 1 (its measurement recipes).

## Jank on scroll or animation

Every jank finding already carries its **cause family** from the trace (SKILL.md Phase 1 step 3): main-thread work, render-thread work, layout/recomposition, or image/data work off-main. The family selects the entry:

1. **Attribute first.** Use the Perfetto trace captured in SKILL.md Phase 1 step 3 to find the long `Choreographer#doFrame` slice and name the family before changing anything.
2. **Main-thread work / off-main image and data work.** Long computations, IO, DB, and image decoding on the UI thread are the dominant jank cause. Inject dispatchers and move the work to `Dispatchers.Default`/`IO`; never hard-code dispatchers (aligns with `spec/android/test-automation/` §B testability). Binder calls and lock contention on the main thread belong here too.
3. **Layout and recomposition cost (Compose-specific):** stabilize parameters to avoid needless recomposition, hoist state, use `remember`/`derivedStateOf` for expensive derivations, use `LazyColumn` keys, and defer reads with lambda-based modifiers. Confirm with a recomposition count, not a guess.
4. **Render-thread work:** oversized bitmap uploads (decode to display size, not source size), expensive paths and shadows, overdraw — flatten deep layouts, avoid full-screen redraws for local state changes.
5. **When the janky surface is a list, `spec/android/long-list-scrolling/` owns the remedy set** and is authoritative over this entry: container choice and the constructions that silently defeat laziness (§A, including the zero-size item that makes the container compose every row at once), item identity — stable domain keys, `contentType`, no derivation in an item body, `derivedStateOf` for scroll-derived booleans, no backwards writes (§B), and paging continuity (§C). Note its exclusion: **a framework change is never a valid jank remedy** — since Compose 1.9 the measured scroll-jank rate matches the View implementation, so a slow list is a data, item, or image problem.

## Main-thread stalls

- **StrictMode (debug only)** with `detectAll()` + `penaltyLog()` surfaces accidental disk/network on the main thread — read violations from the `StrictMode` logcat tag (`spec/android/adb-workflows/` §D).
- Move disk and network off the main thread; cache decoded assets; debounce high-frequency work.

## Missing or wrong loading states

Compare the composable to the wait-indication matrix (SKILL.md Phase 1 step 4 and its thresholds reference), then:

- Add instant tap feedback where a tap currently appears dead.
- Replace a bare spinner beyond ~5 s with a progress indicator that is **determinate as soon as progress is known** (`spec/android/ui-components/` §A); beyond ~10 s add a **cancel affordance** and make the operation backgroundable (`spec/android/app-design-navigation/` §F). Two thresholds, two obligations — never "5–10 s".
- Introduce a **skeleton screen** for content that loads in place instead of a blocking full-screen spinner.
- Remove in-place loading→determinate hand-offs; unify the indicator variant per process across the app.
- These are UI corrections; they change *perceived* performance even when the measured device numbers do not move — record both the UX fix and the (unchanged) number honestly.

## Remediation discipline

- **One change, one gate, one re-measurement.** State the finding, the files to touch, and the expected delta before editing.
- **Rebuild every iteration.** If `./gradlew build` fails, stop and report the red state (REQ-7) — do not stack further edits.
- **No outdated mechanisms** (kapt, monolithic buildSrc, Groovy DSL) in any benchmark or profile module you add (REQ-9).
- **Take the layout, budgets, and remediation order from `spec/android/perceived-performance/`** (§G benchmark module and result handling, §C budgets, §H order). When a remediation needs a decision neither that spec nor a sibling covers, stop and propose a spec extension rather than inventing it silently (REQ-6/REQ-17).
