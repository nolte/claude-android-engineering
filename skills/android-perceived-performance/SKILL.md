---
name: android-perceived-performance
description: Measures UX-relevant Android performance (app-startup time, frame jank, loading-state correctness) on a physical device and remediates the findings. Invoke when the user asks to measure startup time, fix jank or dropped frames, profile app launch, add or repair Baseline Profiles, diagnose a slow or stuttering screen, or optimize perceived performance. Also handles equivalent German-language requests. Runs a MEASURE phase (Macrobenchmark TTID/TTFD, FrameTimingMetric, dumpsys gfxinfo framestats, Perfetto traces) then an interactive FIX phase (Baseline Profiles, lazy init, moving work off the main thread, corrected loading-state UI) with re-measurement. Do not use for functional-test authoring or crash/build-error debugging. Supports resume on re-invocation per spec/claude/resumable-work/.
tags: [quality-gate, ui]
phase: quality
summary: "Measures Android startup time, jank, and loading-state correctness on a physical device, then interactively remediates and re-measures."
summary_de: "Misst Android-Startzeit, Jank und Ladezustands-Korrektheit auf einem physischen Gerät und behebt Befunde interaktiv mit erneuter Messung."
use_when:
  - "you want to measure app startup time (TTID/TTFD)"
  - "you want to find and fix jank or dropped frames"
  - "you want to add or repair Baseline Profiles"
  - "you want to check loading states against the response-time thresholds"
allowed-tools: [Bash, Read, Grep, Glob]
resumable: true
---

# Android Perceived Performance

Measure UX-relevant performance on a physical device, then remediate the findings and re-measure. Two phases, in order: **MEASURE** produces numbers against fixed budgets; **FIX** applies remediations one at a time, each behind an operator approval gate, and re-measures to prove the change moved the number.

CLI-first: terminal, Gradle, and ADB are sufficient — Android Studio is never required (REQ-3). Device measurement runs over ADB per `spec/android/adb-workflows/`.

## Why this is a skill, not an agent

- **Interactivity (decisive):** the FIX phase asks the operator to approve each remediation before editing code (REQ-8 forbids unconfirmed overwrites); a fire-and-forget agent has no stable way to surface that mid-flow gate.
- **Change scope + lifecycle (decisive):** the run persists across the conversation — measure, edit, rebuild, re-measure, iterate — with edits flowing back into the main context, which is the skill bias.
- **Orchestrator role:** the measurement sweep MAY be dispatched to a sub-agent for context-window protection; the orchestrator that fans out is always a skill (`spec/claude/skill-vs-agent/` §Hybrid pattern).
- **Counter-dimension (outweighed):** the MEASURE step performs heavy device reads and trace parsing, which biases toward an isolated agent for context protection — but that isolatable step is delegable, while the interactive FIX loop keeps the whole capability a skill.

## Operating principle: no owning spec yet

There is **no** `spec/android/perceived-performance/` spec. Several sibling specs name it as a future boundary: `spec/android/test-automation/` §F (Macrobenchmark/Microbenchmark are a separate scheduled lane, never the per-commit suite), `spec/android/adb-workflows/` §D (Perfetto `record_android_trace` is the boundary), and the UX budgets in `spec/android/app-design-navigation/` §F and `spec/android/ui-components/` §A.

Consequently this skill measures and fixes with **documented tooling only** and **MUST NOT** silently invent methodology or structural conventions. When a run needs a decision no spec covers (a new budget number, a benchmark-module layout, a golden-trace convention), **report the gap and propose a `spec/android/perceived-performance/` spec** rather than deciding silently (REQ-6, REQ-17). Record the proposal in the run report; do not author the spec here.

## Hard rules

- **Measure on a physical device** for startup and jank; benchmarks run in a separate scheduled lane and **MUST NOT** be added to the per-commit CI suite (`spec/android/test-automation/` §F). An emulator is acceptable only for coarse loading-state UI checks, never for the reported startup/jank numbers.
- **Never edit code without operator approval** for that specific remediation (REQ-8). One remediation, one gate, one re-measurement.
- **Never leave the project red** without reporting it: after every FIX iteration run `./gradlew build` (REQ-1); if it fails, stop and report — do not stack further edits (REQ-7).
- **Never scaffold outdated mechanisms** (kapt, monolithic buildSrc, Groovy DSL) into a benchmark module; use KSP and the Kotlin DSL (REQ-9).
- **Classify every number against `references/thresholds.md`** — a raw millisecond value is not a finding until it is compared to its budget.
- **One change at a time.** Batching remediations destroys attribution: you cannot tell which edit moved which number.

## Phase 1 — MEASURE

Read `references/measurement.md` when you enter this phase — it holds the exact Macrobenchmark, `dumpsys gfxinfo`, and Perfetto command recipes. Read `references/thresholds.md` when you need the budget to classify a number as pass or fail.

### 1. Establish the device and target

- Confirm exactly one `platform-tools` adb (`which -a adb`) and target the device explicitly (`-s <serial>` or `ANDROID_SERIAL`) per `spec/android/adb-workflows/` §A.
- Build and install a **non-debuggable release-shaped** variant for measurement (a debuggable build distorts startup and frame timings). Disable animations for deterministic runs (`settings put global window_animation_scale 0.0` and the two siblings) per `spec/android/adb-workflows/` §E.

### 2. Measure startup (TTID/TTFD)

- Cold-start with `am start -W` and read `TotalTime` / `WaitTime`; corroborate with the `ActivityManager: Displayed` logcat line (TTID). Report TTFD from the app's `reportFullyDrawn()` when instrumented.
- Prefer a Macrobenchmark `StartupTimingMetric` run (cold/warm/hot) for stable, repeatable numbers. See `references/measurement.md`.

### 3. Measure jank

- Reset with `dumpsys gfxinfo <pkg> reset`, exercise the target screen, then read `dumpsys gfxinfo <pkg> framestats` (or a Macrobenchmark `FrameTimingMetric` run) and compute the janky-frame percentage and P50/P90/P99 frame durations against the budget in `references/thresholds.md`.
- Capture a Perfetto trace with `record_android_trace` for any scroll/animation stutter that framestats flags, to locate the offending work on the main thread.

### 4. Audit loading-state correctness

- Against `references/thresholds.md`, verify the response-time feedback semantics and the wait-indication matrix: instant feedback on tap, no indicator below ~200 ms, a loading indicator for short indeterminate waits (200 ms–5 s), a determinate progress indicator with cancel beyond ~5–10 s, one indicator per group, and no in-place loading→determinate hand-off.

### 5. Checkpoint the baseline

- Write the measured numbers and their pass/fail verdicts to the resume state (see Resume below). This baseline is what every FIX iteration is compared against.

## Phase 2 — FIX

Read `references/remediations.md` when a finding needs a fix — it maps each finding class to its concrete remediation. Apply remediations strongest-signal-first.

### 1. Propose one remediation

- Pick the single finding with the largest budget gap. State the remediation, the files it will touch, and the expected effect on the number. Common remediations: Baseline Profiles (+ Startup Profiles), lazy/deferred initialization of app-startup work, moving work off the main thread, and correcting the loading-state UI to the wait-indication matrix.

### 2. Get approval, then edit

- Ask the operator to approve **this** remediation. On approval, apply the edit; on decline, record the decision and move to the next finding. Never overwrite existing code or config without this approval (REQ-8).
- Checkpoint the decision immediately (see Resume).

### 3. Rebuild and re-measure

- Run `./gradlew build`. If it fails, stop and report the red state (REQ-7); do not proceed.
- Re-run only the measurement that this remediation targeted (step 2/3/4 of MEASURE) and compare against the baseline. Record the delta.

### 4. Iterate or conclude

- Repeat from FIX step 1 for the next finding until every number is within budget or the remaining findings need a spec decision (then report the gap per the operating principle).

## Report

Conclude with: the baseline table (number, budget, verdict), the remediations applied with their before/after deltas, the final `./gradlew build` status, any red state left behind, and any `spec/android/perceived-performance/` gap surfaced during the run.

## Resume

This skill is `resumable: true` (multi-phase with per-remediation approval gates), per `spec/claude/resumable-work/`.

- Write checkpoints to `.resume/android-perceived-performance/<run-id>.yml` (never elsewhere). Checkpoint after the baseline is captured and after every approval gate, appending each approval to `decisions:` (never rewriting earlier entries).
- **Resume detection on re-invocation:** scan `.resume/android-perceived-performance/*.yml` for `status: in_progress` matching the current inputs (target package + variant). When one matches, prompt the operator with `resume` / `start-new` / `discard`; never resume from a checkpoint without that confirmation.
- Model the payload under `state:` with the baseline numbers, the applied remediations, and the last completed phase (`measured`, `awaiting-approval-<n>`, `fixed`, `re-measured`).

## German trigger phrases

Also invoke on equivalent German requests, and reply to the operator in German (instructions in this file stay English):

- "Miss die Startzeit der App" / "App-Start profilieren"
- "Behebe das Ruckeln" / "Jank / abgehackte Frames beheben"
- "Warum ist der Screen so langsam / hakelig?"
- "Baseline Profiles hinzufügen oder reparieren"
- "Gefühlte Performance optimieren"
- "Prüfe die Ladeindikatoren gegen die Reaktionszeit-Schwellen"

## Gotchas

- A **debuggable** build measures far slower and janktier than release; always measure a release-shaped, R8-minified variant, or the numbers are drift by construction.
- `am start -W` `TotalTime` is TTID, not TTFD; a screen that shows a spinner "quickly" can still be slow to become useful — report TTFD from `reportFullyDrawn()` where it matters.
- `dumpsys gfxinfo` accumulates until reset; always `reset` immediately before the scenario or the percentages fold in prior activity.
- Baseline Profiles only take effect on a **release** install performed through the normal install path with profile compilation; verifying them on a debug build shows no gain and is a false negative.
- The first cold start after install includes one-time work (dexopt, profile install); discard it and measure subsequent cold starts.
