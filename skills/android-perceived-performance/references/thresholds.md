# Budgets and thresholds

The pass/fail budgets that turn a raw measurement into a finding. A number is not a
finding until it is compared to its budget here. The response-time and wait-indication
values are grounded in `spec/android/app-design-navigation/` §F and
`spec/android/ui-components/` §A; the startup and jank targets are documented tooling
conventions (Android vitals / Macrobenchmark), flagged below where no owning spec fixes
an exact number — those are candidates for the proposed `spec/android/perceived-performance/`.

## Table of contents

- [Response-time perception thresholds](#response-time-perception-thresholds)
- [Wait-indication matrix](#wait-indication-matrix)
- [Frame / jank budget](#frame-jank-budget)
- [Startup targets](#startup-targets)
- [Spec-gap markers](#spec-gap-markers)

## Response-time perception thresholds

The three classic perception boundaries (research-backed, per `spec/android/app-design-navigation/` §F):

- **~0.1 s (100 ms):** the limit for feeling that the system reacts instantly. Every tap must produce feedback within this window. No loading indicator below ~200 ms.
- **~1 s:** the limit for uninterrupted flow of thought. Below this, no indicator is needed beyond the instant tap feedback; the user still feels in control.
- **~10 s:** the limit for keeping attention. Beyond this the user will switch tasks; a determinate progress indicator with a cancel affordance is required, and the operation should be backgroundable.

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
- **Budget (documented convention, not spec-fixed):** target **< 1 %** janky frames on a critical scrolling/animation path; P99 frame duration within the deadline. Treat a screen above this as a finding.
- **Freeze frames:** any single frame over ~700 ms is a user-visible freeze and is always a finding regardless of the aggregate percentage.

## Startup targets

Documented-convention targets (Android vitals guidance); no owning spec fixes exact
numbers for this repository yet:

- **TTID cold start:** flag as slow above ~500 ms; aim well below. Warm/hot starts should be substantially faster.
- **TTFD:** measure and report; it is the honest "time to useful," but no fixed budget is spec-fixed. Compare against the app's own prior baseline rather than an absolute number.
- Report cold, warm, and hot separately; a regression against the app's own baseline is a finding even when the absolute number is under target.

## Spec-gap markers

The following numbers are **documented-tooling conventions, not spec-fixed** for this
repository. When a run depends on pinning any of them, surface the gap and propose
`spec/android/perceived-performance/` per the skill's operating principle (REQ-6/REQ-17):

- The exact janky-frame percentage budget (< 1 % is the working default).
- The exact TTID/TTFD absolute targets (vs. baseline-relative regression).
- The freeze-frame threshold (~700 ms working default).
- Any benchmark-module layout or golden-trace storage convention.
