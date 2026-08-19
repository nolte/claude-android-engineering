# Budgets and thresholds

The pass/fail budgets that turn a raw measurement into a finding. A number is not a
finding until it is compared to its budget here. Every budget below is owned by a spec:
the response-time and wait-indication values by `spec/android/app-design-navigation/` §F
and `spec/android/ui-components/` §A, the startup and frame budgets by
`spec/android/perceived-performance/` §C, and scroll measurement by
`spec/android/long-list-scrolling/` §G. This file restates them for quick reference; on
any divergence the spec wins.

## Table of contents

- [Response-time perception thresholds](#response-time-perception-thresholds)
- [Wait-indication matrix](#wait-indication-matrix)
- [Frame / jank budget](#frame-jank-budget)
- [Startup targets](#startup-targets)
- [What is still deliberately unfixed](#what-is-still-deliberately-unfixed)

## Response-time perception thresholds

The three classic perception boundaries — Nielsen Norman Group's response-time limits (0.1 s / 1 s / 10 s), cited as [R29] by `spec/android/app-design-navigation/`, whose §F turns them into the feedback semantics below. They are usability research, not a platform requirement, and the spec carries them as a SHOULD:

- **~0.1 s (100 ms):** the limit for feeling that the system reacts instantly (NN/g). Every tap must produce feedback within this window. The separate "no loading indicator below ~200 ms" rule is `spec/android/ui-components/` §A's matrix, not the NN/g figure.
- **~1 s:** the limit for uninterrupted flow of thought (NN/g). Below this, no indicator is needed beyond the instant tap feedback; the user still feels in control.
- **~10 s:** the limit for keeping attention (NN/g). Beyond this the user will switch tasks; `app-design-navigation` §F requires progress indication **with cancel** here, and the operation should be backgroundable.

The **~5 s** boundary in the matrix below is a different rule from a different owner: `spec/android/ui-components/` §A switches from the loading indicator to a progress indicator (determinate as soon as progress is known) beyond ~5 s. Keep the two apart — ~5 s = progress indicator, ~10 s = cancel.

## Wait-indication matrix

Per `spec/android/ui-components/` §A — apply consistently:

| Wait duration | Required indication |
|---|---|
| below ~200 ms | nothing — no indicator |
| ~200 ms – 5 s (indeterminate) | loading indicator (also the pull-to-refresh surface) |
| beyond ~5 s | progress indicator, **determinate as soon as progress is known** |
| beyond ~10 s | determinate progress **with cancel**; operation should be backgroundable |

Rules: one indicator per group; the same process uses the same indicator variant across
the app; **never** a loading→determinate hand-off in place. Instant feedback on every tap
regardless of the wait class.

## Frame / jank budget

- **Frame deadline:** 16.67 ms on a 60 Hz display; 11.11 ms at 90 Hz; 8.33 ms at 120 Hz. Report the deadline for the device's actual refresh rate — a frame that passes at 60 Hz can be jank at 120 Hz.
- **Janky frame:** a rendered frame whose duration exceeds the deadline (Macrobenchmark `frameOverrunMs` > 0; `gfxinfo` "Janky frames").
- **Slow frame:** 16 ms–700 ms (`spec/android/perceived-performance/` §A vocabulary; the Android vitals slow-rendering class). Reported as a class of its own, after ANRs/frozen frames and startup in the §H remediation order.
- **Budget (`spec/android/perceived-performance/` §C):** on a non-scroll animation path, **P95 frame duration within the deadline** — a labelled portfolio decision, reported as a corpus decision rather than a platform requirement. Zero frozen frames is the separate, vendor-backed rule below and is **not** labelled that way. **Neither budget applies to a scrolling list** — see below.
- **Frozen frames:** any single frame over 700 ms is a user-visible freeze and is always a defect regardless of the aggregate percentage — vendor-backed, and spec-fixed by both `spec/android/perceived-performance/` §C and `spec/android/long-list-scrolling/` §G.
- **Scrolling lists are owned by `spec/android/long-list-scrolling/` §G**, which overrides this section for that surface: measure with `FrameTimingMetric` over a scroll journey on a non-debuggable release build, read `frameOverrunMs` at P50/P90/P95/P99, and always state the refresh-rate deadline. That spec **deliberately refuses** to fix a pass/fail percentile for scroll jank — so **do not** classify a scroll measurement against the P95 budget above. Report the number with its percentile tail and state that no pass/fail percentile is fixed. This is a decision, not a gap — do not open a spec-extension proposal for it (see below).

## Startup targets

Owned by `spec/android/perceived-performance/` §C:

- **Ceiling (Android vitals, vendor-fixed):** cold ≥ 5 s, warm ≥ 2 s, hot ≥ 1.5 s is the point at which the platform considers startup defective. This is the ceiling, never the target.
- **TTID cold start (portfolio decision, label it as such):** ≤ 500 ms on the device the app's baseline was taken on; above that is a finding. Name that device in the report — the number is a per-app target, never a cross-device constant.
- **TTFD:** no absolute target — judged against the app's own baseline and against the wait indication its loading states owe the user.
- Report cold, warm, and hot separately; a regression against the app's own baseline is a finding even when the absolute number is under target.

## What is still deliberately unfixed

Two numbers stay open by decision, not by omission — do not invent either:

- **The scroll pass/fail percentile.** `spec/android/long-list-scrolling/` §Open Questions states that no vendor source fixes one, and `spec/android/perceived-performance/` §C inherits that refusal explicitly. Report the tail; claim no verdict.
- **A portfolio-wide reference device for cold TTID.** `spec/android/perceived-performance/` §C scopes the target to the app's own baseline device and requires the report to name it, so no run is blocked; cross-app comparison of the absolute number is explicitly not claimed.

Everything else this file lists is spec-owned. Benchmark-module layout and result handling
are `spec/android/perceived-performance/` §G; when a run needs a decision no spec covers,
surface the gap and propose a spec extension (REQ-6/REQ-17).
