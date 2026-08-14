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
allowed-tools: [Bash, Read, Grep, Glob, Edit, Write]
resumable: true
---

# Android Perceived Performance

Measure UX-relevant performance on a physical device, then remediate the findings and re-measure. Two phases, in order: **MEASURE** produces numbers against fixed budgets; **FIX** applies remediations one at a time, each behind an operator approval gate, and re-measures to prove the change moved the number.

CLI-first: terminal, Gradle, and ADB are sufficient — Android Studio is never required (REQ-3). Device measurement runs over ADB per `spec/android/adb-workflows/`.

## Why this is a skill, not an agent

- **Interactivity (decisive):** the FIX phase asks the operator to approve each remediation before editing code (REQ-8 forbids unconfirmed overwrites); a fire-and-forget agent has no stable way to surface that mid-flow gate.
- **Change scope + lifecycle (decisive):** the run persists across the conversation — measure, edit, rebuild, re-measure, iterate — with edits flowing back into the main context, which is the skill bias.
- **Orchestrator role:** the measurement sweep is the kind of step that would be dispatched to a sub-agent for context-window protection, and the orchestrator that fans out is always a skill (`spec/claude/skill-vs-agent/` §Hybrid pattern). No such measurement agent exists in this plugin today, and the declared `allowed-tools` carries no dispatch tool — adding one is a change to both.
- **Counter-dimension (outweighed):** the MEASURE step performs heavy device reads and trace parsing, which biases toward an isolated agent for context protection — but that step is the isolatable one, while the interactive FIX loop keeps the whole capability a skill.

## Operating principle: the spec owns the methodology

`spec/android/perceived-performance/` is the authoritative source for this capability and this skill operationalizes it without restating or contradicting it. It fixes what is measured (§A), the conditions under which a number counts at all (§B), the budgets that turn a number into a finding (§C), the startup and jank methodology (§D/§E), Baseline Profiles (§F), the benchmark module and result handling (§G), and the remediation order (§H).

Neighbouring ownership still holds and is referenced, never duplicated: `spec/android/long-list-scrolling/` §G owns **list-scroll measurement** and its deliberate refusal to fix a scroll pass/fail percentile; `spec/android/test-automation/` §F owns the lane split; `spec/android/adb-workflows/` §D/§E owns Perfetto and device mechanics; the wait-indication matrix and response-time thresholds live in `spec/android/ui-components/` §A and `spec/android/app-design-navigation/` §F; the release-build configuration a measurement runs against is `spec/android/release-readiness/` §A.

On any conflict the spec wins. When a run needs a decision no spec covers, report the gap and propose a spec extension rather than deciding silently (REQ-6, REQ-17).

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
- **Capture the run conditions now**, before any measurement: device model, Android version, build type, minification state, `CompilationMode`, refresh rate, iteration count (`references/measurement.md` §"Device preconditions" has the `getprop`/`dumpsys display` calls). `spec/android/perceived-performance/` §A makes a number without them unreportable, and they go into the resume state so a resumed run does not have to re-measure to restate them.

### 2. Measure startup (TTID/TTFD)

- Produce the reported number with a Macrobenchmark `StartupTimingMetric` run; `am start -W` and the `ActivityManager: Displayed` logcat line are a quick local check only, measure TTID alone, and per `spec/android/perceived-performance/` §D **MUST NOT** be the basis of a reported finding. Report TTFD from the app's `reportFullyDrawn()`/`ReportDrawn*` instrumentation, and report its absence as the finding when there is none.
- Run cold, warm, and hot and report each separately; cold is the primary case. See `references/measurement.md`.

### 3. Measure jank

- Produce the reported number with a Macrobenchmark `FrameTimingMetric` run and read `frameOverrunMs` at P50/P90/P95/P99 against `references/thresholds.md`. `dumpsys gfxinfo` is a coarse local check and, per `spec/android/perceived-performance/` §E, **MUST NOT** carry a jank finding for a Compose surface on its own — the vendor documentation scopes it to View-toolkit apps.
- **For a scrolling list, follow `spec/android/long-list-scrolling/` §G rather than this skill's general recipe:** measure with `FrameTimingMetric` over a scroll journey, read `frameOverrunMs` as the primary number, report the P95/P99 tail (a healthy P50 proves nothing), and always state the refresh-rate deadline the budget is set against. A jank claim from a debug build is not a finding.
- Capture a Perfetto trace with the `record_android_trace` invocation `spec/android/adb-workflows/` §D owns, for any stutter the frame metric flags, and read it to locate the offending work on the main thread (`spec/android/perceived-performance/` §E).

### 4. Audit loading-state correctness

- Against `references/thresholds.md`, verify the response-time feedback semantics and the wait-indication matrix: instant feedback on tap, no indicator below ~200 ms, a loading indicator for short indeterminate waits (200 ms–5 s), a determinate progress indicator with cancel beyond ~5–10 s, one indicator per group, and no in-place loading→determinate hand-off.

### 5. Checkpoint the baseline

- Write the measured numbers and their pass/fail verdicts to the resume state (see Resume below). This baseline is what every FIX iteration is compared against.

## Phase 2 — FIX

Read `references/remediations.md` when a finding needs a fix — it maps each finding class to its concrete remediation. Apply them in the user-impact order `spec/android/perceived-performance/` §H fixes, not by signal strength.

### 1. Propose one remediation

- Pick the next finding in the user-impact order `spec/android/perceived-performance/` §H fixes — ANRs and frozen frames, then startup, then slow frames, then the rest — and within a category the largest budget gap. State the remediation, the files it will touch, and the expected effect on the number. Common remediations: Baseline Profiles (+ Startup Profiles), lazy/deferred initialization of app-startup work, moving work off the main thread, and correcting the loading-state UI to the wait-indication matrix.

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

Every number in that table carries the conditions `spec/android/perceived-performance/` §A requires — device model, Android version, build type, minification state, `CompilationMode`, refresh rate, iteration count — and every verdict drawn against a §C **portfolio decision** says so, so the operator can tell a corpus target from a platform requirement. A number without its conditions is not reportable.

## Resume

This skill is `resumable: true` (multi-phase with per-remediation approval gates), per `spec/claude/resumable-work/`.

- Write checkpoints to `.resume/android-perceived-performance/<run-id>.yml` (never elsewhere). Checkpoint after the baseline is captured and after every approval gate, appending each approval to `decisions:` (never rewriting earlier entries).
- **Resume detection on re-invocation:** scan `.resume/android-perceived-performance/*.yml` for `status: in_progress` matching the current inputs (target package + variant). When one matches, prompt the operator with `resume` / `start-new` / `discard`; never resume from a checkpoint without that confirmation.
- Model the payload under `state:` with the run conditions from MEASURE step 1, the baseline numbers, the applied remediations, and the last completed phase (`measured`, `awaiting-approval-<n>`, `fixed`, `re-measured`). Conditions are part of the checkpoint, not re-derived on resume.

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
