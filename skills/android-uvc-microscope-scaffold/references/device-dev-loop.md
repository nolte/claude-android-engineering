# Device-bound development loop and verification

How a UVC integration is developed and tested when the peripheral occupies the phone's only USB
port. Grounded in `spec/android/uvc-microscope/` §I and `spec/android/adb-workflows/` §A–§C;
on any conflict those specs win. This file adds only what changes because a peripheral is on the
port.

## Table of contents

- [1. Network ADB before the peripheral is attached](#1-network-adb-before-the-peripheral-is-attached)
- [2. Wake state and ground truth](#2-wake-state-and-ground-truth)
- [3. Diagnostics and evidence capture](#3-diagnostics-and-evidence-capture)
- [4. The verified-devices row](#4-the-verified-devices-row)
- [5. Smoke test and test lanes](#5-smoke-test-and-test-lanes)
- [6. Logging in the code this skill writes](#6-logging-in-the-code-this-skill-writes)

## 1. Network ADB before the peripheral is attached

The microscope takes the USB-C port, so ADB runs over the network for the whole loop. Order
matters — the cable is needed to set the transport up:

```sh
which -a adb                          # exactly one platform-tools adb (adb-workflows §A)
adb devices                           # cable attached, state `device`
# Android 11+: Settings → Developer options → Wireless debugging → Pair device with pairing code
adb pair <ip>:<pairing-port>          # enter the on-screen code
adb connect <ip>:<port>
adb devices                           # both serials listed; export ANDROID_SERIAL=<ip>:<port>
# now unplug the cable and attach the microscope
```

Legacy `adb tcpip 5555` is the flagged fallback for ≤ Android 10 only; it has no pairing and is
closed with `adb usb` at the end of the session. Scripts connect by explicit `ip:port` and never
depend on mDNS discovery. From here every command targets the network serial (`-s` or
`ANDROID_SERIAL`).

Install over the network with `./gradlew installDebug` (or `adb install -r`). On a non-stock OEM
build `INSTALL_FAILED_USER_RESTRICTED` blocks both `adb install` and shell `pm install`; push the
APK and install it on-device from the file — the decode table is `adb-workflows` §B.

## 2. Wake state and ground truth

- **Keep the device awake.** A dozing or locked phone stops the preview and drops network ADB,
  which reads exactly like a peripheral failure. `adb shell svc power stayon usb` does not apply
  without a cable; use Developer options → Stay awake with the charger absent, or
  `adb shell settings put system screen_off_timeout 1800000` for the session (restore after).
- **`host_connected` is the ground truth** for whether the peripheral is attached at all —
  before interpreting any app-level symptom:

  ```sh
  adb shell dumpsys usb | grep -E "host_connected|mCurrentFunctions|UsbDevice"
  ```

- **`FEATURE_USB_HOST`** absent on the phone is its own UI state, not a bug to debug.

## 3. Diagnostics and evidence capture

Watch the engine's native tag beside the app's own — frame-allocation lines under
`libUVCCamera` prove the stream is live even when the surface renders black, separating a stream
fault from a rendering fault:

```sh
adb logcat -c
adb logcat libUVCCamera:V UvcMicroscope:D *:S          # tag allowlist, device-side filtering
adb logcat -b crash -d                                  # the PendingIntent symptom lands here
```

Symptom table:

| Symptom | Reading | Where |
|---|---|---|
| `IllegalArgumentException … FLAG_MUTABLE, an implicit Intent …` on first registration | engine `register()` called, or app's own PendingIntent implicit | `engine-integration.md` §2 |
| Grant dialog shown, no result broadcast arrives | receiver export state / intent package mismatch | `engine-integration.md` §2 |
| `unsupported preview size` while frames render | double open, not a mode problem | `engine-integration.md` §4 |
| Black surface, `libUVCCamera` allocating frames | rendering fault (surface, transform) | `android-compose-ui` for the view; §4 for the surface handshake |
| Black surface, no `libUVCCamera` lines | stream fault: permission, open, or negotiation | `engine-integration.md` §2/§4 |
| Preview stops and ADB drops together | device dozed | §2 above |
| Shutter dead after a reattach | callbacks bound to a nulled field | `engine-integration.md` §5 |
| Build fails late with a misleading artifact message | POM-only artifact (`libnative:3.3.3`) | `access-path-decision.md` §5 |

Evidence per hardware session (spec §I): `adb shell screencap -p /sdcard/uvc.png` +
`adb pull`, the log line with the captured dimensions and byte size, and the measured frame rate
per mode (count `libUVCCamera` frame lines or the app's own frame counter over 30 s). Store them
in the run report, not in the repository, unless the operator asks for an evidence folder.

Measurement obligations for an unlisted body (spec §A/§F/§G): frame rate per mode, which
button/status events arrive raw for each physical control (30-minute window is the precedent for
"emits nothing"), `checkSupportFlag(CTRL_ZOOM_ABS)`, the largest mode, and the two-test detail
measurement of that mode against a deliberately upscaled control.

## 4. The verified-devices row

For a newly measured body, append one row to `spec/android/uvc-microscope/en.md` §Verified
devices and mirror it in `de.md`. Columns are observed directly or `unknown` — never inferred
from a datasheet:

```markdown
| `<vid>:<pid>` | `<iProduct>`, UVC <version>, <power>, <format> | <modes, with "measured genuine" or "upscaled" on the top mode> | ~<fps> @ <mode> (descriptor claims <n>) | <buttons that reach USB, with index/state; or "none over USB"> | <Supported/Not supported (`CTRL_ZOOM_ABS`)> | <date>, <device> / Android <version>; access path A/B/C |
```

Also record the Path A probe result (model, build, camera ID) in the last column when it was
run — even a failed probe is a measurement the next project inherits. This is the **only** edit
this skill makes under `spec/`; any other change is proposed as a spec extension (REQ-6).

## 5. Smoke test and test lanes

The closing smoke test on the device: attach → grant dialog → live preview → one still with the
logged dimensions → one shutter press from the body where wired → detach handled as `NoDevice`.
Report each as pass/fail with the evidence from §3.

Emulators provide no USB host; these paths **cannot gate CI**, and the run report says so
explicitly rather than letting a green run imply coverage (spec §I,
`spec/android/test-automation/`). Device-bound tests go to the instrumented lane (§F there);
crop rounding and JPEG encoding are unit tests in the per-commit suite
(`engine-integration.md` §9). Then `./gradlew build` — red state reported, never left silent
(REQ-1, REQ-7).

## 6. Logging in the code this skill writes

`spec/android/logging/` binds the generated code, not just the diagnosis:

- **§A** — call the app's logging facade, never `android.util.Log`. This skill integrates into an
  app that already exists, so the facade's shape is the host project's, not this file's: the
  snippets write `log.d { … }` as a placeholder for *whatever that project already uses*. Resolve
  it before emitting code — an injected logger reachable in the class, a static facade, or Timber
  (`Timber.d("…")`, which has no lambda overload and takes the eager form). If the host app has no
  facade at all, that is a §A gap in the host: report it and hand the decision back rather than
  inventing one here. The one exception is the throwaway device probe in
  `references/access-path-decision.md`: it is never committed and never shipped, which §A names
  explicitly.
- **§D** — every log call in a frame path or a UVC event callback is lazy, so the message is built
  only when the level is enabled. `setButtonCallback` and `setStatusCallback` fire per event and
  `Log.*` arguments are constructed even when the line is filtered out; an eager string here is
  work done on every callback for output nobody reads. Lazy is necessary but not sufficient: §D
  notes that only an `inline` facade overload is genuinely allocation-free on the disabled path —
  a lambda crossing a non-inline boundary still allocates a capturing closure before the level
  check. Where the host facade's overload is not `inline`, say so in the report rather than
  implying the callback is free.
- **§C** — a frame, a buffer, or a raw descriptor payload is never logged. Log the shape instead:
  dimensions, byte count, format, and the decision taken.
