# ADB Workflows

Status: draft

## Context

This repository's skills operate CLI-first (REQ-3): they deploy apps to devices and emulators, debug them, and read their logs without Android Studio. ADB (Android Debug Bridge) is the tool that carries all three, and the debugging skill (REQ-16) plus the device-access permission (REQ-4) stand directly on it. This spec is the authoritative definition of how ADB is used in this portfolio: deployment, debugging, log access, and the scripting robustness rules that make ADB reliable inside automated, agent-driven workflows.

The content is distilled from a research pass (August 2026) over three source classes: the official ADB/platform-tools documentation (developer.android.com and the AOSP sources — notably current as of platform-tools 37.x: `adb server-status`, mDNS backend `libadbmdns`, Wireless-Debugging 2.0), the official logcat/debugging/bugreport documentation (including the AOSP `logcat --help` text, which is now the authoritative option reference after the web page stopped listing options), and community/production practice (agent runbooks shipped in real repos, the canonical CI emulator action, tool status of scrcpy/pidcat/adb-enhanced, and Google's new agent-oriented `android` CLI).

Boundaries: test *execution* strategy is owned by `spec/android/test-automation/`; reading a trace for a performance verdict belongs to `spec/android/perceived-performance/` (this spec owns the capture invocation); the rules about `debuggable` in release builds are shared with `spec/android/security/` §F.

Readers: authors of this repo's Android skills (especially the debugging and project-setup skills) and reviewers judging whether a skill's device interaction is conformant.

## Goals

- Make deployment to devices and emulators deterministic: one documented install path, known failure modes with known fixes
- Make log access precise: scoped to the app under investigation, reproducible in scripts, safe (no PII in logs)
- Make debugging evidence-driven: crashes, ANRs, and app state are read from defined surfaces (logcat buffers, bugreports, dumpsys) instead of guesswork
- Make every ADB interaction scriptable and agent-safe: explicit device targeting, real exit-code handling, bounded waits, clean state

## Non-Goals

- Test execution and orchestration — owned by `spec/android/test-automation/` (this spec only provides the device plumbing underneath)
- Reading a trace for a performance verdict, and profiling depth (gfxinfo analysis) — `spec/android/perceived-performance/`; this spec owns only the capture invocation (§D)
- Play-Store deployment — out of scope for this repository; `bundletool` appears only as the local install path for app bundles
- Rooted-device and userdebug-build workflows — production builds are the target; `adb root` is documented as unavailable there and not built upon
- GUI tooling (Android Studio, scrcpy as a product) — scrcpy is referenced as the mirroring standard, but no skill depends on a GUI

## Requirements

### A. Environment, targeting, and connection

- **MUST** have exactly one `platform-tools` ADB on the `PATH` (verify with `which -a adb`); mismatched multiple installations cause the `adb server version … doesn't match this client` kill loop, and tools bundling their own adb (scrcpy) are pointed at the single one (`ADB=` env)
- **MUST** keep platform-tools current — behavior is version-gated: ssh-style argument handling since platform-tools 23 [R1]; device exit codes and stdout/stderr separation need *both* host adb ≥ 24 (the shell-v2 protocol) **and** a device on API ≥ 24 — the single rule that §E's exit-code bullet applies [R27][R30]; `adb server-status` predates 37 (36.0.0 extended it with the mDNS state) and the `libadbmdns` backend became the default in 37.0.0, with `openscreen` (and `ADB_MDNS_OPENSCREEN`) removed in 37.0.1, so a Wireless-Debugging diagnosis assumes `server-status` output with `version: "37.0.0"` or higher and `mdns_backend: LIBADBMDNS` [R1][R2]
- **MUST** target devices explicitly the moment more than one device can be attached: `-s <serial>` per call or `ANDROID_SERIAL` exported for sessions (`-s` overrides the variable); after any emulator retry/restart, all subsequent commands use explicit `-s`
- **MUST** check device state before acting and map states to remedies: `device` (note: connected ≠ fully booted), `offline` (restart server / replug), `unauthorized` (RSA dialog not accepted — reconnect and confirm on device)
- **SHOULD** use Android-11+ wireless debugging via the pairing flow (`adb pair ip:port` with the on-screen code, auto-connect afterwards); scripts connect by explicit `ip:port` and do not depend on mDNS discovery; `adb server-status` and `adb mdns track-services` are the diagnosis tools
- **MUST NOT** leave the legacy `adb tcpip 5555` mode open on shared networks — it has no pairing and accepts any host; it remains the pragmatic fallback for ≤ Android 10 and is closed with `adb usb` afterwards
- **MUST** treat `adb reverse tcp:<port> tcp:<port>` as the canonical way to reach a host-local dev server from the device (`localhost` stays a secure context; the emulator alias `10.0.2.2` does not)
- **MUST NOT** depend on `adb root`, `run-as` against non-debuggable builds, or other userdebug-only capabilities — production builds are the target, and `adb root` is documented as unavailable there [R1]

### B. Deployment

- **SHOULD** use `./gradlew installDebug` as the default build-and-install step of a dev loop; raw `adb install` is the right tool when the APK is already built or a specific device is targeted
- **MUST** pass `-r` on every repeat `adb install`; `-t` for Gradle test APKs (`testOnly`), `-g` to pre-grant all runtime permissions in hermetic runs, `-d` only for deliberate debug downgrades
- **MUST** know the `INSTALL_FAILED_*` decode table and apply the documented fix instead of retry loops: `UPDATE_INCOMPATIBLE` (signature mismatch → uninstall first), `VERSION_DOWNGRADE` (→ `-d` or uninstall), `ALREADY_EXISTS` (→ `-r`), `TEST_ONLY` (→ `-t`), `INSUFFICIENT_STORAGE` (→ `df /data`, clean up), `USER_RESTRICTED` (OEM install block — Xiaomi/MIUI "Install via USB"); split-APK sets go through `adb install-multiple`
- **MUST** install app bundles locally via `bundletool build-apks` + `bundletool install-apks` — a bundle cannot be `adb install`ed directly
- **SHOULD** launch deterministically after install: `adb shell am start -n <pkg>/<activity>`, resolving the launcher activity with `cmd package resolve-activity --brief <pkg>` when unknown; the `monkey -p <pkg> 1` idiom is the noisy fallback
- **MUST NOT** assume an "Apply Changes" CLI exists — it is IDE-only; the CLI accelerations are `--fastdeploy` and (with a v4 signature) `--incremental`
- **MUST** reset app state deliberately, knowing the difference: `pm clear <pkg>` wipes data and revokes runtime permissions (hermetic reset); `am force-stop <pkg>` kills without wiping

### C. Log access

- **MUST** scope log reads to the app under investigation: `adb logcat --pid=$(adb shell pidof -s <pkg>)` (re-resolve after process restart), or tag allowlists `adb logcat MyTag:D *:S`; device-side filtering (`-s`, tag:priority specs, `--regex`) is preferred over host-side `grep` pipes
- **MUST** use the snapshot pattern in scripts: `adb logcat -c` (per target buffer) before the scenario, `adb logcat -d [-e <regex>]` after — non-blocking, pipeable, reproducible; a bounded blocking wait is `adb logcat -e <regex> -m 1`
- **MUST** know the buffers: `main`, `system`, `crash` (part of the `default` set), `events` (binary, `-v descriptive`), `radio`; crash diagnosis reads `-b crash`
- **SHOULD** use `-v threadtime` (default) plus modifiers as needed (`color` for humans, `epoch`/`UTC` for correlation); file logging via `-f` with `-r`/`-n` rotation
- **MUST** treat `adb logcat --help` on the target device as the authoritative option reference — the current web page no longer lists the full option set
- **MUST NOT** log PII, credentials, or tokens in app code (official security guidance); release builds strip debug logs via R8 `-assumenosideeffects` on `android.util.Log` — which only happens when minification is on and the rule is present, never by default
- **SHOULD** gate verbose logging through `Log.isLoggable`-style tags togglable at runtime (`adb shell setprop log.tag.<TAG> VERBOSE`); Timber remains the de-facto app-side logging standard for Android-only apps (stable but frozen; plant trees only in debug builds)

### D. Debugging surfaces

- **MUST** read Java/Kotlin crashes from logcat's crash buffer: marker `FATAL EXCEPTION` under tag `AndroidRuntime`, exception type plus topmost own stack frame first; minified traces are resolved with `retrace` against the build's `mapping.txt`
- **MUST** obtain native-crash tombstones and ANR traces via `adb bugreport` on production devices — the zip's `FS/data/tombstones/` and `FS/data/anr/` mirror paths that direct `adb pull` cannot reach without root
- **MUST** know the ANR thresholds (5 s input dispatch, 5 s foreground broadcast, `startForegroundService` → `startForeground` within 5 s — platform facts per the authoritative vitals documentation [R8]) and the search anchors (`am_anr`, `"ANR in"`, `"VM TRACES AT LAST ANR"`); `adb shell am monitor` watches for crashes/ANRs live
- **SHOULD** use `StrictMode` (`detectAll` + `penaltyLog`, debug builds only) as ANR prevention, reading violations from logcat tag `StrictMode`
- **SHOULD** inspect app state through targeted `dumpsys` services (never bare `dumpsys`): `dumpsys activity` (+ package filter), `dumpsys meminfo <pkg>` (Private Dirty, leaked Activities/Views under Objects), `dumpsys package <pkg>` (permissions/components/userId), `dumpsys battery`/`deviceidle` for power-state simulation
- **MUST** test deep links with the documented command: `adb shell am start -W -a android.intent.action.VIEW -d "<uri>" <pkg>` (escape `&` in URIs)
- **MUST** distinguish process-death simulations: `am kill <pkg>` = system-initiated death of a backgrounded process (state restoration expected on relaunch); `am force-stop` = user-initiated kill (restoration not expected) — using `force-stop` to test restoration is a false negative
- **MAY** attach a CLI debugger via the JDWP chain (`adb jdwp` → `adb forward tcp:<port> jdwp:<pid>` → `jdb -attach`) — documented escape hatch, not the default workflow
- **MUST** capture system traces with Perfetto's `record_android_trace` helper rather than by hand-assembling a config: it records, pulls the trace, and opens it. Fetch the script from the Perfetto repository, then invoke it with an output path, a duration, a buffer size, an app filter, and the categories the question needs — `sched` and `freq` for what the CPU was doing, `view` and `input` for UI work, `am`/`wm`/`gfx` for lifecycle and rendering (`record_android_trace -o <file>.perfetto-trace -t 20s -b 32mb -a <pkg> sched freq view input am wm gfx`); `--no-open` suppresses the UI launch on a headless box [R29]. This spec owns the capture; reading the resulting trace for a performance verdict belongs to `spec/android/perceived-performance/` §D/§E

### E. Scripting and agent robustness

- **MUST** gate on real boot, not transport state: `adb wait-for-device` followed by polling `sys.boot_completed` until `1` (strip `\r` when comparing) — `wait-for-device` alone returns mid-boot
- **MUST** handle exit codes truthfully: `adb shell` propagates device exit codes only when host adb ≥ 24 *and* device API ≥ 24 hold together (the `shell,v2` service is API ≥ 24 [R30]; older hosts speak the v1 protocol [R27]) and never with `-x` [R30]; on an older device the fallback is `cmd; echo x$?` and parsing the trailer; `am instrument` always exits 0 — parse `INSTRUMENTATION_STATUS_CODE` from `-w -r` output; `adb install` output is additionally grepped for `Success`/`INSTALL_FAILED`
- **MUST** wrap hang-prone calls (`screencap`, `dumpsys`, `uiautomator`) in `timeout`; there is no host-side adb timeout flag (`-t` is a transport id)
- **SHOULD** retry transient `device not found`/`closed` errors once via `adb kill-server && adb start-server` — never in a loop
- **SHOULD** clean up leaked state with `trap` handlers: `adb forward --remove-all`, restore modified `settings`, kill started emulators
- **MUST** capture screenshots agent-safely via device file plus pull (`screencap -p /sdcard/x.png && adb pull …`), not `exec-out` (documented hang risk in production agent runbooks); `screenrecord` is bounded by a hard 180 s limit, no audio [R1]
- **MUST** disable animations for deterministic UI automation: `settings put global window_animation_scale 0.0`, `transition_animation_scale 0.0`, `animator_duration_scale 0.0`
- **MUST NOT** rely on `input text` for non-ASCII input (ASCII-only); Unicode goes through an IME bridge like ADBKeyBoard when needed
- **MUST** remember the argument-order asymmetry: `adb forward LOCAL REMOTE` vs `adb reverse REMOTE LOCAL` — the most common scripting bug
- **SHOULD** grant runtime and special permissions in automation via `pm grant`/`pm revoke` and `appops set` respectively (or `install -g` up front)

### F. Emulator management (CLI)

- **MUST** create AVDs non-interactively with `echo "no" | avdmanager create avd --force -n <name> -k "system-images;…"` after `sdkmanager --install` of the image
- **MUST** use the established headless flag set in CI/agents: `-no-window -gpu software -noaudio -no-boot-anim` plus a deliberate snapshot flag (next bullet); `-gpu software` (emulator ≥ 36.4.9) selects the best available GLES/Vulkan software backend, with `-gpu swiftshader` as the explicit SwiftShader choice and `-gpu lavapipe` (Mesa) as the fallback when the default software renderer crashes; `swiftshader_indirect`, `swangle_indirect`, and `guest` are deprecated since emulator 36.4.9 and **MUST NOT** be written into new scaffolds (a pinned older emulator that only knows `swiftshader_indirect` records that as a dated deviation) [R16][R31][R32]; KVM is mandatory for emulator jobs on GitHub-hosted Linux runners (udev rule) [R21][R28], per `spec/android/test-automation/` §G
- **MUST** choose the snapshot flag by run purpose: `-no-snapshot` (full cold boot) for deterministic debugging and reproduction runs; snapshot-cached AVDs with `-no-snapshot-save` are the sanctioned exception for CI wall-time (per `spec/android/test-automation/` §G)
- **MUST** respect the port model: console/adb port pairs from 5554/5555 (+2 per instance, serial `emulator-<console-port>`); stop headless instances with `adb -s emulator-<port> emu kill`
- **MAY** manage local-properties-style config drift via `adb-enhanced` (`adbe`) as a maintained QoL wrapper

### G. Agent-era conventions

- **SHOULD** track Google's official agent-oriented `android` CLI (`android run --apks`, `android emulator create/start/stop`, `android screen capture`, `android layout`) as a complement to adb — it standardizes deploy/launch/inspect for agents but replaces neither adb nor Gradle
- **SHOULD** encode device runbooks as agent-consumable skill documents (production precedent: repos shipping `.claude/skills/` adb runbooks with the robustness rules of §E)
- **MAY** use accessibility-tree-first device control (uiautomator dump; MCP-style bridges) with screenshot verification as fallback; goal-driven agent loops are unsuitable for regression testing (that stays with `spec/android/test-automation/`)
- Structured JSON logcat does not exist in stock adb — agents parse `-v epoch`/threadtime text or instrumentation status lines; wrapper claims otherwise are tooling, not adb

## Acceptance Criteria

The criteria below are a deliberate representative rollup of §A–§G, not a 1:1 mapping; every requirement bullet above is normative on its own.

- [ ] Every skill-issued adb command in a multi-device context carries `-s` (or a documented `ANDROID_SERIAL` export); no bare adb call follows an emulator restart
- [ ] A skill that installs repeatedly always passes `-r`, and on any `INSTALL_FAILED_*` output applies the documented fix from §B instead of retrying blindly
- [ ] Log collection in skills uses the clear-then-dump pattern (`-c` … `-d`) or `--pid`/tag scoping; no unbounded blocking `logcat` without `-m`/timeout in scripts
- [ ] No generated or skill-authored app code logs PII; release build configs carry the R8 log-stripping rule when logging beyond warnings exists
- [ ] Crash triage instructions reference the crash buffer and `retrace`; ANR triage references bugreport `FS/` paths, never a bare `adb pull /data/anr`
- [ ] Deep-link tests use `am start -W -a android.intent.action.VIEW`; state-restoration tests use `am kill`, not `am force-stop`
- [ ] Boot waits poll `sys.boot_completed`; no script treats `wait-for-device` as "booted" and no test gate reads `am instrument`'s exit code
- [ ] Hang-prone adb calls are timeout-wrapped, and screenshots go through `/sdcard` + `pull`
- [ ] UI automation runs with the three animation scales set to 0
- [ ] Emulator scaffolds use the §F headless flag set and non-interactive AVD creation, and stop instances via `adb emu kill`
- [ ] The spec's wireless guidance is followed: pairing-based wireless debugging documented as default, `tcpip 5555` only as a flagged legacy fallback that gets closed
- [ ] No skill depends on `adb root`, `run-as` against non-debuggable builds, or other userdebug-only capabilities

## Open Questions

Each question states the working default the requirements above already encode.

- Google's `android` agent CLI: adopt as a first-class dependency of the debugging skill once it stabilizes, or keep adb-only with the CLI as optional acceleration?
- Unicode input: is ADBKeyBoard (third-party IME) acceptable as a skill dependency, or should skills avoid text-input automation beyond ASCII?
- Wireless pairing automation: first-time pairing is deliberately interactive; should skills document a USB-first setup path only?

## References

All sources retrieved 2026-08-11, except [R29] (2026-08-14) and [R30]–[R32] (2026-08-19). Class markers: (P) primary/authoritative vendor or AOSP documentation, (S) secondary (maintained tool repos, engineering runbooks). Platform-behavior facts cite the single authoritative primary source; assertions that direct downstream tooling carry corroborating citations inline.

- [R1] ADB official documentation (architecture, targeting, wireless, install, shell tools): <https://developer.android.com/tools/adb>
- [R2] Platform-tools release notes (version-gated behavior; `server-status` mDNS state in 36.0.0, `libadbmdns` default in 37.0.0, `openscreen` deleted in 37.0.1; the page starts at 24.0.4 and no longer lists the 23/24 protocol changes): <https://developer.android.com/tools/releases/platform-tools>
- [R3] logcat official page (+ deferral to `adb logcat --help`): <https://developer.android.com/tools/logcat>
- [R4] AOSP logcat source/help text (authoritative option reference): <https://android.googlesource.com/platform/system/logging/+/refs/heads/main/logcat/logcat.cpp>
- [R5] dumpsys documentation: <https://developer.android.com/tools/dumpsys>
- [R6] Bug reports (zip structure, FS/ mirror): <https://developer.android.com/studio/debug/bug-report>
- [R7] Reading bug reports (search anchors): <https://source.android.com/docs/core/tests/debug/read-bug-reports>
- [R8] ANR documentation (thresholds, traces): <https://developer.android.com/topic/performance/vitals/anr>
- [R9] Crash documentation (FATAL EXCEPTION anatomy): <https://developer.android.com/topic/performance/vitals/crash>
- [R10] Native crash / tombstones: <https://source.android.com/docs/core/tests/debug/native-crash>
- [R11] retrace tool: <https://developer.android.com/tools/retrace>
- [R12] Log info disclosure risk (no PII, R8 stripping): <https://developer.android.com/privacy-and-security/risks/log-info-disclosure>
- [R13] StrictMode reference: <https://developer.android.com/reference/android/os/StrictMode>
- [R14] Deep-link testing command: <https://developer.android.com/training/app-links/deep-linking>
- [R15] Doze/App-Standby testing sequences: <https://developer.android.com/training/monitoring-device-state/doze-standby>
- [R16] Emulator command line (headless flags, ports): <https://developer.android.com/studio/run/emulator-commandline>
- [R17] avdmanager: <https://developer.android.com/tools/avdmanager>
- [R18] bundletool: <https://developer.android.com/tools/bundletool>
- [R19] Building from the command line (installDebug): <https://developer.android.com/build/building-cmdline>
- [R20] Google agent-oriented Android CLI: <https://developer.android.com/tools/agents/android-cli>
- [R21] android-emulator-runner (boot gate, animation settings, AVD cache): <https://github.com/ReactiveCircus/android-emulator-runner>
- [R22] scrcpy (mirroring standard): <https://github.com/Genymobile/scrcpy>
- [R23] adb-enhanced: <https://github.com/ashishb/adb-enhanced>
- [R24] MASTG JDWP/jdb technique (CLI debugger chain): <https://mas.owasp.org/MASTG/techniques/android/MASTG-TECH-0031/>
- [R25] Process-death simulation distinction: <https://vtsen.hashnode.dev/how-to-simulate-process-death-in-android>
- [R26] Access a host-local server from the device (`adb reverse`, secure context) (P): <https://developer.android.com/develop/ui/views/layout/webapps/access-local-server>
- [R27] AOSP issue: `adb shell` exit codes not propagated before API 24 / host adb 24 (S): <https://issuetracker.google.com/issues/36908392>
- [R28] KVM hardware acceleration GA on GitHub-hosted runners (S): <https://github.blog/changelog/2024-04-02-github-actions-hardware-accelerated-android-virtualization-now-available/>
- [R29] Perfetto system tracing — the `record_android_trace` helper, its flags, and the categories it records: <https://perfetto.dev/docs/getting-started/system-tracing>
- [R30] AOSP adb services and manpage — `shell,v2: (API>=24)` for exit codes and stdout/stderr separation, `-x` disables remote exit codes, `server-status` (P): <https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/dev/services.md>, <https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/user/adb.1.md>
- [R31] Emulator hardware acceleration — the `-gpu` value table (`auto`, `host`, `software`, `lavapipe`, `swiftshader`, `swangle`; `swiftshader_indirect`/`swangle_indirect`/`guest` deprecated in 36.4.9) (P): <https://developer.android.com/studio/run/emulator-acceleration>
- [R32] Emulator release notes — 36.4.9: `-gpu software` introduced, Lavapipe default software renderer (P): <https://developer.android.com/studio/releases/emulator>
