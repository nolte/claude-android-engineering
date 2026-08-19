# Surface 2 — ADB device and deploy diagnosis

Load-triggered from `SKILL.md` when the failure is device connection, install, launch, or emulator availability. Grounded in `spec/android/adb-workflows/` §A (environment/targeting), §B (deployment), §E (scripting robustness), §F (emulator management). Diagnosis is read-only until a fix is approved.

## Table of contents

- Environment and targeting discipline
- Device-state remedies
- Deploy and INSTALL_FAILED_* decode table
- Launch and reset
- Wireless and connection recovery
- Emulator management (headless, CLI)
- Scripting robustness
- Reporting

## Environment and targeting discipline

- **One adb only.** `which -a adb` must show a single `platform-tools` adb; a second adb (often bundled with scrcpy) causes the `adb server version … doesn't match this client` kill loop. Point other tools at the one adb via `ADB=`.
- **Current platform-tools.** Compare `adb --version` with the platform-tools release notes; behavior is version-gated (shell exit-code propagation ≥ 24, ssh-style quoting ≥ 23, `adb server-status` predates 37 — 36.0.0 extended it with the mDNS state — while the `libadbmdns` default backend / Wireless Debugging 2.0 diagnosis assumes 37.0.0+; spec `adb-workflows` §A). An outdated adb is a diagnosis in itself — report it before chasing a symptom it explains.
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

## Deploy and INSTALL_FAILED_* decode table

`./gradlew installDebug` is the default build-and-install step of a dev loop (§B); raw `adb install` is the right tool when the APK is already built or a specific device is targeted. On any `INSTALL_FAILED_*` line, apply the documented fix — never retry blindly. Always pass `-r` on a repeat `adb install`.

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

## Emulator management (headless, CLI)

When no device is available or an emulator will not boot headless (§F; KVM is mandatory on Linux runners — the documented udev rule, per `test-automation` §G):

- **Create non-interactively:** `sdkmanager --install "system-images;android-<api>;google_apis;x86_64"` then `echo "no" | avdmanager create avd --force -n <name> -k "system-images;android-<api>;google_apis;x86_64"`.
- **Start headless with the established flag set:** `emulator -avd <name> -no-window -gpu software -noaudio -no-boot-anim <snapshot flag>` — `-gpu software` (emulator ≥ 36.4.9) selects the best available GLES/Vulkan software backend, with `-gpu swiftshader` as the explicit SwiftShader choice and `-gpu lavapipe` (Mesa) as the fallback when the default software renderer crashes; `swiftshader_indirect`, `swangle_indirect`, and `guest` are deprecated since emulator 36.4.9 and never written into new scaffolds (a pinned older emulator that only knows `swiftshader_indirect` records that as a dated deviation) — `adb-workflows` §F.
- **Choose the snapshot flag by purpose:** `-no-snapshot` (full cold boot) for deterministic debugging and reproduction; `-no-snapshot-save` on a snapshot-cached AVD only for CI wall-time (`test-automation` §G).
- **Port model:** console/adb pairs from 5554/5555, +2 per instance; the serial is `emulator-<console-port>`; stop headless instances with `adb -s emulator-<port> emu kill` — and re-target every subsequent command with explicit `-s` after any restart.
- Boot-gate the instance per "Scripting robustness" below before installing anything; `adb-enhanced` (`adbe`) is an optional QoL wrapper, never a dependency.

## Scripting robustness

- Boot gate: `adb wait-for-device` then poll `sys.boot_completed` until `1` — `wait-for-device` alone returns mid-boot.
- Exit codes: `adb shell` propagates device exit codes only on API ≥ 24 and never with `-x`; grep `adb install` output for `Success`/`INSTALL_FAILED` rather than trusting the exit code.
- Wrap hang-prone calls (`dumpsys`, `screencap`, `uiautomator`) in `timeout` — there is no host-side adb timeout flag.
- Screenshots go device-side then pull (`screencap -p /sdcard/x.png && adb pull …`), never `exec-out` (documented hang risk); `screenrecord` is hard-limited to 180 s and records no audio.
- Clean up leaked state with a `trap` handler: `adb forward --remove-all`, restore modified `settings` (animation scales, font scale), kill started emulators.
- `input text` is ASCII-only — Unicode goes through an IME bridge (ADBKeyBoard) or is avoided; the spec's Open Question on that dependency stays open, report it.
- Grant runtime and special permissions in automation via `pm grant <pkg> <permission>` / `pm revoke` and `appops set` (or `install -g` up front) — never by clicking through dialogs in a script.
- Remember the asymmetry: `adb forward LOCAL REMOTE` vs `adb reverse REMOTE LOCAL`.
- Never depend on `adb root` or `run-as` against a non-debuggable build — production builds are the target.

## Reporting

State the device serial and state (or the `INSTALL_FAILED_*` code) as the cited evidence, the decoded cause, and the documented fix. Apply a fix (uninstall, flag change, permission enable) only behind the `SKILL.md` step 4 gate; re-install and re-launch to verify, and when the fix touched the project (a Gradle flag, a manifest attribute) also run `./gradlew build` per `SKILL.md` step 4. If the install/launch is still red, report the new output and next step — never mark complete on a red state.
