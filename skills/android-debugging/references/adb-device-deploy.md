# Surface 2 — ADB device and deploy diagnosis

Load-triggered from `SKILL.md` when the failure is device connection, install, or launch. Grounded in `spec/android/adb-workflows/` §A (environment/targeting), §B (deployment), §E (scripting robustness). Diagnosis is read-only until a fix is approved.

## Table of contents

- Environment and targeting discipline
- Device-state remedies
- INSTALL_FAILED_* decode table
- Launch and reset
- Wireless and connection recovery
- Scripting robustness
- Reporting

## Environment and targeting discipline

- **One adb only.** `which -a adb` must show a single `platform-tools` adb; a second adb (often bundled with scrcpy) causes the `adb server version … doesn't match this client` kill loop. Point other tools at the one adb via `ADB=`.
- **Explicit targeting.** The moment more than one device can attach, every call carries `-s <serial>` or a session `ANDROID_SERIAL` export (`-s` overrides the variable). After any emulator retry/restart, all subsequent commands use explicit `-s`.
- **Enumerate first.** `adb devices -l` lists serials and states before any action.

## Device-state remedies

Map the state from `adb devices` to its documented remedy — do not act on a non-`device` state:

| State | Meaning | Remedy |
|---|---|---|
| `device` | Connected — but **not** necessarily fully booted | Gate real work on `sys.boot_completed` = `1` (`adb -s <s> shell getprop sys.boot_completed`, strip `\r`), not on presence in the list |
| `offline` | Transport dropped | `adb kill-server && adb start-server`, or replug USB; retry once, never loop |
| `unauthorized` | RSA fingerprint dialog not accepted | Reconnect and accept the "Allow USB debugging" dialog on the device; revoke+re-authorize if stuck |
| not listed | No transport | Check cable/port, `adb usb`, driver; for wireless see the recovery section below |

## INSTALL_FAILED_* decode table

On any `INSTALL_FAILED_*` line, apply the documented fix — never retry blindly. Always pass `-r` on a repeat `adb install`.

| Code | Cause | Documented fix |
|---|---|---|
| `INSTALL_FAILED_UPDATE_INCOMPATIBLE` | Signature mismatch vs installed app | `adb uninstall <pkg>` first, then reinstall |
| `INSTALL_FAILED_VERSION_DOWNGRADE` | Installing an older versionCode | `-d` to allow downgrade, or uninstall first |
| `INSTALL_FAILED_ALREADY_EXISTS` | App already installed | Pass `-r` (reinstall keeping data) |
| `INSTALL_FAILED_TEST_ONLY` | APK built with `testOnly` | Pass `-t` |
| `INSTALL_FAILED_INSUFFICIENT_STORAGE` | No space on `/data` | `adb shell df /data`, clean up, retry |
| `INSTALL_FAILED_USER_RESTRICTED` | OEM install block (Xiaomi/MIUI) | Enable "Install via USB" in the device's developer options |
| `INSTALL_FAILED_NO_MATCHING_ABIS` | Native libs miss the device ABI | Build/install a matching ABI split |

Extra flags: `-g` pre-grants all runtime permissions (hermetic runs); split-APK sets go through `adb install-multiple`. An app **bundle** cannot be `adb install`ed — build+install locally via `bundletool build-apks` + `bundletool install-apks`. There is no CLI "Apply Changes" (IDE-only); the accelerations are `--fastdeploy` and (with a v4 signature) `--incremental`.

## Launch and reset

- Launch deterministically: `adb -s <s> shell am start -n <pkg>/<activity>`; resolve an unknown launcher with `adb shell cmd package resolve-activity --brief <pkg>`.
- Reset state deliberately: `pm clear <pkg>` wipes data **and revokes runtime permissions** (hermetic reset); `am force-stop <pkg>` kills without wiping. Choose by intent.

## Wireless and connection recovery

- Android 11+ wireless: pair once via `adb pair ip:port` with the on-screen code, then connect by explicit `ip:port`. Diagnose with `adb server-status` and `adb mdns track-services`; don't depend on mDNS discovery in scripts.
- Legacy `adb tcpip 5555` is a fallback for ≤ Android 10 only — it has no pairing and accepts any host, so never leave it open on a shared network; close it with `adb usb` afterwards.
- To reach a host-local dev server from the device: `adb reverse tcp:<port> tcp:<port>` (keeps `localhost` a secure context).

## Scripting robustness

- Boot gate: `adb wait-for-device` then poll `sys.boot_completed` until `1` — `wait-for-device` alone returns mid-boot.
- Exit codes: `adb shell` propagates device exit codes only on API ≥ 24 and never with `-x`; grep `adb install` output for `Success`/`INSTALL_FAILED` rather than trusting the exit code.
- Wrap hang-prone calls (`dumpsys`, `screencap`, `uiautomator`) in `timeout` — there is no host-side adb timeout flag.
- Screenshots go device-side then pull (`screencap -p /sdcard/x.png && adb pull …`), never `exec-out` (documented hang risk).
- Remember the asymmetry: `adb forward LOCAL REMOTE` vs `adb reverse REMOTE LOCAL`.
- Never depend on `adb root` or `run-as` against a non-debuggable build — production builds are the target.

## Reporting

State the device serial and state (or the `INSTALL_FAILED_*` code) as the cited evidence, the decoded cause, and the documented fix. Apply a fix (uninstall, flag change, permission enable) only behind the `SKILL.md` step 4 gate; re-install and re-launch to verify. If the install/launch is still red, report the new output and next step — never mark complete on a red state.
