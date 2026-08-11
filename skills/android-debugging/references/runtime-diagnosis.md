# Surface 3 — Runtime-defect diagnosis

Load-triggered from `SKILL.md` when the app builds and installs but misbehaves at runtime (crash, ANR, native tombstone, wrong behavior, deep-link, state-restoration). Grounded in `spec/android/adb-workflows/` §C (log access), §D (debugging surfaces), `spec/android/test-automation/` (test-vs-defect boundary), and `spec/android/security/` §A (no-PII). Diagnosis is read-only until a fix is approved.

## Table of contents

- Log access (safe, scoped, no-PII)
- Java/Kotlin crashes
- Native crashes and ANRs (via bugreport)
- App-state inspection with dumpsys
- Deep links and process-death
- Test failure vs app defect
- Reporting

## Log access (safe, scoped, no-PII)

- **Scope to the app.** `adb logcat --pid=$(adb shell pidof -s <pkg>)` (re-resolve the PID after any process restart), or a tag allowlist `adb logcat MyTag:D *:S`. Prefer device-side filtering (`-s`, tag:priority, `--regex`) over host-side `grep`.
- **Clear-then-dump pattern** (reproducible, non-blocking): `adb logcat -c` before the scenario, `adb logcat -d [-e <regex>]` after. A bounded blocking wait is `adb logcat -e <regex> -m 1`. Never run an unbounded blocking `logcat` in a script.
- **Buffers:** `main`, `system`, `crash` (crash diagnosis reads `-b crash`), `events` (binary, `-v descriptive`), `radio`. Default format `-v threadtime`; add `-v epoch`/`UTC` for correlation.
- **Authoritative option reference** is `adb logcat --help` on the target device — the web page no longer lists the full option set.
- **No PII.** Redact credentials, tokens, and personal data before quoting any log line back to the operator (`security` §A, `adb-workflows` §C). Note: release builds strip debug logs via R8 only when minification is on **and** the `-assumenosideeffects` rule is present — never by default.

## Java/Kotlin crashes

- Read the crash from the crash buffer: marker `FATAL EXCEPTION` under tag `AndroidRuntime`. Cite the **exception type** plus the **topmost own stack frame** (skip framework frames) as the evidence.
- A minified/obfuscated trace is unreadable as-is — resolve it with `retrace` against the build's `mapping.txt` before analyzing frames.
- `adb shell am monitor` watches for crashes/ANRs live during a reproduction.
- `StrictMode` (`detectAll` + `penaltyLog`, debug builds only) surfaces main-thread I/O and leaks under logcat tag `StrictMode` — a cheap ANR/jank early-warning.

## Native crashes and ANRs (via bugreport)

- Native tombstones and ANR traces on production (non-debuggable) devices come from `adb bugreport <out.zip>` — the zip's `FS/data/tombstones/` and `FS/data/anr/` mirror paths that a direct `adb pull` cannot reach without root. **Never** use a bare `adb pull /data/anr`.
- ANR thresholds (platform facts): 5 s input dispatch, 5 s foreground broadcast, `startForegroundService` → `startForeground` within 5 s. Search anchors in the bugreport/logcat: `am_anr`, `"ANR in"`, `"VM TRACES AT LAST ANR"`.
- Cite the ANR subject line and the blocked main-thread frame (from the traces) as evidence; the root cause is main-thread work, not the ANR marker itself.
- A bugreport is expensive to produce — checkpoint after collecting it (`SKILL.md` step 2) so a resumed run doesn't re-pull it.

## App-state inspection with dumpsys

Use **targeted** dumpsys services (never a bare `dumpsys`), always `timeout`-wrapped:

- `dumpsys activity` (+ package filter) — activity/task state.
- `dumpsys meminfo <pkg>` — Private Dirty; leaked Activities/Views appear under `Objects`.
- `dumpsys package <pkg>` — granted permissions, components, userId.
- `dumpsys battery` / `deviceidle` — power-state simulation (Doze/App-Standby).

Cite the specific field (a leaked Activity count, a missing permission) as the evidence for the diagnosis.

## Deep links and process-death

- Test a deep link with the documented command: `adb shell am start -W -a android.intent.action.VIEW -d "<uri>" <pkg>` (escape `&` in the URI). `-W` reports whether it resolved and to which activity — that report is the evidence.
- Simulate process death correctly: `am kill <pkg>` = system-initiated death of a backgrounded process (**state restoration expected** on relaunch); `am force-stop <pkg>` = user-initiated kill (restoration **not** expected). Using `force-stop` to test restoration is a false negative.
- For deterministic UI reproduction, disable the three animation scales (`settings put global window_animation_scale 0.0`, `transition_animation_scale 0.0`, `animator_duration_scale 0.0`).

## Test failure vs app defect

When the symptom arrived as a failing test rather than an on-device defect, decide which before diagnosing (`spec/android/test-automation/`):

- **App defect** — the test correctly caught a real regression: the production code path is wrong. Route the underlying behavior through the crash/log evidence above.
- **Test defect / flake** — the test is wrong or non-deterministic: a `Thread.sleep`/wall-clock wait (banned — virtual time only), a missing `MainDispatcherRule`, a `testTag` where semantics should match, or an order-dependent assertion. Fix the test, not the app.
- **Boundary signal:** a failure that reproduces deterministically on the JVM (`runTest`) points at an app defect; one that only fails intermittently or under CI timing points at a flake. Never institutionalize a retry to hide a flake — fix it.

## Reporting

State the cited evidence (the `FATAL EXCEPTION` frame, the `am_anr` subject and blocked frame, the dumpsys field, or the `am start -W` result), the diagnosis it supports, and the documented remedy. Redact PII first. Apply a code/config fix only behind the `SKILL.md` step 4 gate; reproduce the scenario and re-read the buffer to verify. If still red, report the new evidence and the next step — never mark complete on an unresolved defect.
