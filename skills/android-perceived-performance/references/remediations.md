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

Strongest-signal-first order:

1. **Baseline Profiles (+ Startup Profiles).** The highest-leverage startup remediation. Add a `baseline-prof.txt` covering app startup and the critical journey via `BaselineProfileRule`; wire it with the `androidx.baselineprofile` Gradle plugin (Kotlin DSL, KSP — never kapt/Groovy). Verify the gain on a **release** install only (see `references/measurement.md`).
2. **Defer app-startup work.** Move non-essential initialization out of `Application.onCreate()` and off the startup critical path. Use `androidx.startup` `Initializer`s with lazy dependencies, or defer to first-use. Audit every library initializer that runs eagerly at launch.
3. **Lazy initialization.** Replace eager singletons and eager DI graph construction on the startup path with lazy providers; construct only what the first frame needs.
4. **Report full draw.** Call `reportFullyDrawn()` (or the Compose `ReportDrawn` APIs) so TTFD is measurable and the platform can optimize; a screen that never reports full draw hides its true cost.

## Jank on scroll or animation

1. **Attribute first.** Use the Perfetto trace (`references/measurement.md`) to find the long `Choreographer#doFrame` slice before changing anything.
2. **Move work off the main thread.** Long computations, IO, DB, and image decoding on the UI thread are the dominant jank cause. Inject dispatchers and move the work to `Dispatchers.Default`/`IO`; never hard-code dispatchers (aligns with `spec/android/test-automation/` §B testability).
3. **Compose-specific:** stabilize parameters to avoid needless recomposition, hoist state, use `remember`/`derivedStateOf` for expensive derivations, use `LazyColumn` keys, and defer reads with lambda-based modifiers. Confirm with a recomposition count, not a guess.
4. **Reduce overdraw and layout cost:** flatten deep layouts, avoid full-screen redraws for local state changes.
5. **When the janky surface is a list, `spec/android/long-list-scrolling/` owns the remedy set** and is authoritative over this entry: container choice and the constructions that silently defeat laziness (§A, including the zero-size item that makes the container compose every row at once), item identity — stable domain keys, `contentType`, no derivation in an item body, `derivedStateOf` for scroll-derived booleans, no backwards writes (§B), and paging continuity (§C). Note its exclusion: **a framework change is never a valid jank remedy** — since Compose 1.9 the measured scroll-jank rate matches the View implementation, so a slow list is a data, item, or image problem.

## Main-thread stalls

- **StrictMode (debug only)** with `detectAll()` + `penaltyLog()` surfaces accidental disk/network on the main thread — read violations from the `StrictMode` logcat tag (`spec/android/adb-workflows/` §D).
- Move disk and network off the main thread; cache decoded assets; debounce high-frequency work.

## Missing or wrong loading states

Compare the composable to the wait-indication matrix in `references/thresholds.md`, then:

- Add instant tap feedback where a tap currently appears dead.
- Replace a bare spinner on a long wait with a **determinate** progress indicator plus a cancel affordance beyond ~5–10 s.
- Introduce a **skeleton screen** for content that loads in place instead of a blocking full-screen spinner.
- Remove in-place loading→determinate hand-offs; unify the indicator variant per process across the app.
- These are UI corrections; they change *perceived* performance even when the measured device numbers do not move — record both the UX fix and the (unchanged) number honestly.

## Remediation discipline

- **One change, one gate, one re-measurement.** State the finding, the files to touch, and the expected delta before editing.
- **Rebuild every iteration.** If `./gradlew build` fails, stop and report the red state (REQ-7) — do not stack further edits.
- **No outdated mechanisms** (kapt, monolithic buildSrc, Groovy DSL) in any benchmark or profile module you add (REQ-9).
- **Take the layout, budgets, and remediation order from `spec/android/perceived-performance/`** (§G benchmark module and result handling, §C budgets, §H order). When a remediation needs a decision neither that spec nor a sibling covers, stop and propose a spec extension rather than inventing it silently (REQ-6/REQ-17).
