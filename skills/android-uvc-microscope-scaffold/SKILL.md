---
name: android-uvc-microscope-scaffold
description: "Integrates an external USB (UVC) camera (microscope, endoscope) into an existing Android app per spec/android/uvc-microscope/. Decides the access path on evidence (descriptor capture, then a Camera2 LENS_FACING_EXTERNAL probe on the target device; only if the platform does not expose the camera, the libuvc engine at the USBMonitor+UVCCamera layer, libuvc:3.2.7 pinned and resolution-proven), applies manifest and targetSdk-correct USB-permission rules, guards the open sequence, captures in-memory stills, wires body buttons and digital zoom, and runs the device loop over network ADB. Operations: scaffold, audit (read-only). Invoke when the user asks to connect a USB microscope, integrate a UVC camera, or fix its black screen or permission crash. Also handles equivalent German-language requests. Don't use for the built-in camera, barcode scanning (android-barcode-scanner-scaffold), or frame upload (android-feature-implement). Supports resume on re-invocation."
tags: [scaffolding, media, implementation]
phase: build
summary: "Integrates a USB/UVC microscope into an existing app — evidence-based access path, libuvc-layer engine, targetSdk-correct USB permission, in-memory stills, and the network-ADB device loop."
summary_de: "Bindet ein USB-/UVC-Mikroskop in eine bestehende App ein — evidenzbasierter Zugangsweg, libuvc-Engine, targetSdk-korrekte USB-Berechtigung, Stills im Speicher und die Netzwerk-ADB-Geräteschleife."
use_when:
  - "you want an app to show and capture the live view of a USB microscope or endoscope"
  - "a UVC camera shows a black screen, crashes on registration, or reports unsupported preview size"
  - "an existing UVC integration should be checked against the spec (audit)"
  - "a new microscope body needs measuring and recording in the verified-devices table"
see_also:
  - android-permissions-derive
  - android-compose-ui
  - android-feature-implement
  - android-debugging
  - android-barcode-scanner-scaffold
dont_use_when:
  - situation: "The camera is the phone's built-in camera (CameraX/Camera2 on internal lenses)"
    alternative: android-feature-implement
  - situation: "Scanning QR or barcodes with the built-in camera"
    alternative: android-barcode-scanner-scaffold
  - situation: "The CAMERA/USB permission decision, ledger row, or denial path itself needs deriving"
    alternative: android-permissions-derive
  - situation: "The preview screen's layout, theming, adaptivity, or previews are the question"
    alternative: android-compose-ui
  - situation: "Uploading, storing, or recognising the captured frame"
    alternative: android-feature-implement
  - situation: "A red build or an ADB transport problem unrelated to the peripheral"
    alternative: android-debugging
resumable: true
---

# Android UVC Microscope Scaffold

Integrates an external USB Video Class camera into an app that already exists. The authoritative
rules live in `spec/android/uvc-microscope/`; this skill operationalizes them and never restates or
contradicts them. On any conflict the spec wins — report the gap and propose a spec change rather
than deciding silently (REQ-6, REQ-27).

Three properties make this capability unlike ordinary camera work, and each is a gate below:
the platform camera framework may or may not see the device (measured per target device, §A);
the community engine's publication resolves only partially and its USB permission code crashes
on `targetSdk >= 34` (designed out by `libuvc:3.2.7` and never calling `USBMonitor.register()`,
§B/§C); and the peripheral occupies the phone's only USB port (network ADB, awake device,
`dumpsys usb` as ground truth, §I).

## Why this is a skill, not an agent

- **The access path and the engine layer are operator gates.** Choosing the platform camera over
  the libuvc engine, or the recorded wrapper fallback over the layer decision, changes the
  dependency graph and the permission surface; both are confirmed, not inferred.
- **Persistent code output in the main context.** Kotlin, manifest, catalog coordinates, a
  possible `third_party/` repository, and the verified-devices row land in the working tree.
- **Interactive, device-bound, and resumable.** A run spans a hardware session with operator
  actions (attach, grant, press the shutter); `resumable: true` carries it across.
- Counter-dimension considered: `audit` is a read-only report and would suit a narrow agent, but
  it walks the same evidence the scaffold gathers, so per `spec/claude/skill-vs-agent/` §Primary
  decision rule the skill keeps both operations.

## Boundary vs the neighbouring artefacts

This skill **adds an external-camera capability**. The **permission decision** — `CAMERA`, the
USB grant as a separate consent, ledger row, rationale, denial paths — is `android-permissions-derive`
(REQ-20); this skill hands it the platform-rule evidence (spec §C) and applies what comes back.
The **preview screen** beyond the camera-specific parts is `android-compose-ui`. **Upload,
persistence, recognition** of a frame is `android-feature-implement`. **Built-in camera** work is
`android-barcode-scanner-scaffold` (scanning) or `android-feature-implement`. A **red build or
ADB fault** unrelated to the peripheral is `android-debugging`.

## Operations

Name one at the start: **`scaffold`** — add the capability (steps 1–8); **`audit`** — a read-only
conformance report against `references/audit-checklist.md`, writing nothing and handing fixes to
a `scaffold` follow-up. Both end with the run report; `scaffold` also with `./gradlew build` and
a device smoke test.

## User-language policy

Detect the user's language and respond in it (German for this operator). Generated artifacts stay
canonical: Kotlin, resource keys, comments, and the verified-devices row in English; user-visible
copy (the state messages of spec §C included) is externalized to `strings.xml` with a German
translation per `spec/android/localization/` §A.

## Preconditions

Before writing anything:

- Confirm the working directory is a git repository and locate the target module. This skill
  authors *into* an app scaffolded per `spec/android/project-structure/`; if no `:app` module
  exists, stop and route to `android-project-scaffold` first.
- Confirm a physical, OTG-capable device is reachable over ADB (`adb devices`), and that
  platform-tools is the single ADB on the `PATH`, per `spec/android/adb-workflows/` §A. An
  emulator does not qualify — it has no USB host (spec §I); say so and stop if that is all there is.
- Establish **network ADB before the microscope is attached**: cable in, pair per
  `adb-workflows` §A (Android 11+ pairing; `tcpip 5555` only as the flagged fallback closed with
  `adb usb` afterwards), verify the wireless connection, then unplug and attach the peripheral.
  Read `references/device-dev-loop.md` §1 first.
- Read `references/access-path-decision.md` in full before proposing anything — the path
  decision determines every later step, and reversing it late means discarding the engine module.
- Check for uncommitted changes in the paths to be touched (camera module, `AndroidManifest.xml`,
  version catalog, `settings.gradle.kts`, `strings.xml`, `spec/android/uvc-microscope/en.md`).
  If dirty, report and ask whether to stash, commit, or abort — never overwrite unconfirmed
  work (REQ-8).

## Authoring procedure

### 1. Capture the device evidence — gate

With the peripheral attached and the device awake, record the descriptors before designing
anything (spec §A): `adb shell dumpsys usb` (`host_connected`, vendor/product ID, interfaces) and,
from a host machine, `lsusb -v` for the format and frame descriptors — vendor/product ID,
`iProduct`, UVC version, power mode, pixel format, mode list. Compare against §Verified devices
in the spec: a listed body inherits its measurements; an unlisted body opens the measurement
obligations of steps 6 and 7.

Gate: confirm the recorded descriptors and whether the body is already verified.

### 2. Decide the access path on evidence — gate

Walk `references/access-path-decision.md` §1–§3 in order:

1. **Probe the platform first.** Run the Camera2 `LENS_FACING_EXTERNAL` probe from
   `references/access-path-decision.md` §2 on the target device with the microscope attached and
   permitted. Recent Pixel generations document native UVC support; other OEMs may not. If the
   probe enumerates the device with a usable stream configuration, the capability is built on
   CameraX/Camera2 with an external-lens selector, and steps 3–4 shrink to the platform path
   described there. The probe result — device model, OS build, camera ID, formats — is recorded
   in the run and in the verified-devices row.
2. **Only if the platform does not expose it**, integrate the libuvc engine at the
   `USBMonitor` + `UVCCamera` layer (spec §B). Pin `libuvc:3.2.7`, prove that every artifact of
   the graph resolves as an AAR (a POM alone is not evidence), and never call
   `USBMonitor.register()`.
3. **The wrapper fallback** (`libausbc` `CameraUVC`) is legal in exactly the two cases the spec
   names, and then only with the case recorded in the engine module, the vendored
   `third_party/` repository ordered before the remote with `content { includeModule(...) }` and
   per-artifact provenance, `libuvc` added as an explicit compile dependency, and the reflection
   and restart costs of §F/§G accepted. Never mix the two paths.

The web platform, WebUSB, and cross-platform camera wrappers are not paths (spec §A) — if the
app's UI is not native, the frame grab still is.

Gate: confirm the path, its evidence, and — on the fallback — which of the two cases applies.

### 3. Manifest, permissions, and attachment — gate

Apply spec §C through `references/engine-integration.md` §1–§2:

- `<uses-feature android:name="android.hardware.usb.host" android:required="false" />` — never
  `required="true"`; the app installs on non-OTG phones and shows the "no USB host" state.
- **Hand the permission decision to `android-permissions-derive`** with this evidence: on
  `targetSdk >= 28` the platform's `UsbUserPermissionManager` requires the app to hold `CAMERA`
  before it grants access to a video-class USB interface — a platform rule, not an engine
  quirk — so the app declares and holds `CAMERA` before opening, with a rationale that names the
  microscope; the USB grant is a **separate second consent** issued by the system USB dialog per
  device, and its denial is a distinct state. Apply the declaration and request flow that skill
  returns; do not derive the ledger row here.
- Build the USB grant request `targetSdk`-correctly (spec §C): an **explicit** intent
  (`setPackage`) inside a **mutable** `PendingIntent` — `UsbManager` fills in the grant extras,
  so `FLAG_IMMUTABLE` breaks the flow — and a receiver registered with an explicit export flag
  (Android 14 enforces it). Verify by reaching a live preview, not by the absence of a crash log.
- Offer attachment-driven launch (`USB_DEVICE_ATTACHED` filter plus `device_filter.xml`) as an
  option, never as the only entry point; model the state as a sealed type distinguishing no
  device, permission pending, permission denied, no host support, and engine error (spec §C/§H).

Gate: confirm the manifest diff and the state model before writing engine code.

### 4. Engine module, open sequence, and lifecycle

Read `references/engine-integration.md` §3–§5 when writing code. Every engine type lives in one
module behind an app-owned interface (spec §H). Open only when a permitted device **and** a live
surface both exist, re-evaluate on whichever arrives second, guard with a concurrency flag —
`unsupported preview size` while frames render is a double open, never an unsupported mode
(spec §D). Tear down when the screen leaves composition, re-register on return, and re-attach
button and status callbacks after **every** reopen to the instance the state callback supplies.
Keep the raw-frame callback alive (`RenderMode.NORMAL` on the wrapper fallback). Comment every
non-obvious guard with the constraint it enforces (spec §H).

### 5. Still capture and resolution strategy — gate

Read `references/engine-integration.md` §6–§7. Capture is a one-shot frame callback encoded in
process with `YuvImage.compressToJpeg` — never the engine's `captureImage()`, which needs storage
permission and writes DCIM (spec §E). Round every crop edge to an even pixel, bound the frame
wait with a timeout surfacing a typed failure, and report captured dimensions and byte size.
Preview stays at a mode fast enough to frame by; the still is taken at the device's largest
supported mode only after its detail has been **measured** as genuine per spec §G (halve-and-
restore residual plus radial power spectrum, calibrated against a deliberately upscaled control).
A mode switch is serialized, surfaced in the UI, bounded by a timeout, degrades to the live mode,
and always restores the preview mode; measure its cost rather than assuming it.

Gate: confirm the still resolution and the measured mode-switch cost.

### 6. Physical controls and zoom

Read `references/engine-integration.md` §8. Body buttons do not arrive as key events; the shutter
comes from the UVC status endpoint through the engine's button callback, reached directly on the
libuvc layer (reflection only on the recorded wrapper fallback, confined, null-guarded, with a
`-keepclassmembers` rule). Map only measured indices, log every unmapped button and status event
raw, and never offer a hardware control the device does not report. Where the zoom rocker or the
UVC zoom control is absent, provide on-screen zoom as a centre crop applied identically to the
preview transform and the captured frame, and label it **digital**.

### 7. Device-bound verification and the verified-devices record

Read `references/device-dev-loop.md` §2–§4. Keep the device awake; use `dumpsys usb`
`host_connected` as ground truth before interpreting any app symptom; watch the `libUVCCamera`
tag beside the app's own to separate stream faults from rendering faults. Capture evidence —
`screencap` plus the log line with the captured dimensions — and measure frame rate per mode,
button events, and the UVC zoom flag. Then **append a row to `spec/android/uvc-microscope/en.md`
§Verified devices** (and its `de.md` mirror) for a newly measured body, `unknown` for anything
not observed. That row is the one spec edit this skill performs; every other spec change is
proposed, not made. State plainly that emulators cannot cover this capability and CI stays green
without evidencing it; device-bound tests live in the instrumented lane
(`spec/android/test-automation/` §F), crop rounding and encoding are unit-tested without a device.

### 8. Build green and smoke on the device — gate

Finish with `./gradlew build` and the device smoke test (attach, grant, live preview, one still
with reported dimensions, one body shutter press where wired). Report a red state rather than
leaving it silent (REQ-1, REQ-7). Report by name every gap the spec does not cover — the Path A
capture recipe, a preview-latency budget, the runtime proof of the §B layer decision — and
propose the spec extension (REQ-6).

## Reference files

- `references/access-path-decision.md` — before step 2: descriptor capture, the Camera2
  external-camera probe, the libuvc-layer recipe with the artifact-resolution proof, the
  bounded wrapper fallback with its vendoring rules.
- `references/engine-integration.md` — steps 3–6: manifest and grant-request templates, sealed
  state model, guarded open sequence, capture, resolution switch, buttons, zoom.
- `references/device-dev-loop.md` — preconditions and step 7: network ADB before attach, wake
  state, diagnostics, evidence capture, the verified-devices row.
- `references/audit-checklist.md` — the `audit` operation: acceptance criteria as checkable
  evidence with severity and fix step.

## Resumability

Per `spec/claude/resumable-work/`, this skill is `resumable: true`. State persists to
`.resume/android-uvc-microscope-scaffold/<run-id>.yml` after every approval gate (device
evidence, access path, manifest, resolution, verification) and after each named step boundary.
On re-invocation, scan that directory for `status: in_progress` runs whose `inputs:` snapshot
(target module + operation + vendor/product ID) matches; when one matches, prompt
`Resume run <run_id> from phase <phase> (last checkpoint <last_checkpoint_at>)? [resume / start-new / discard]`.
Never re-ask a decision already in `decisions:` — the access path and the fallback case in
particular. Fail closed on unparseable or higher-`schema_version` files. The envelope keys and
lifecycle are owned by the spec and are not duplicated here.

## Hard rules

- **Never** build on Camera2 `LENS_FACING_EXTERNAL` without the probe having passed on the
  target device — and never skip the probe: it is the first step of the access-path decision.
- **Never** propose WebView `getUserMedia`, WebUSB, or a cross-platform camera wrapper.
- **Never** call `USBMonitor.register()`; acquire the USB grant through the platform `UsbManager`
  with an explicit, mutable `PendingIntent` and an explicitly exported-or-not receiver.
- **Never** pin an engine version whose artifacts have not each been resolved as an AAR;
  a resolving POM is not evidence. `libuvc:3.2.7` is the default; `libausbc:3.3.3` only on the
  recorded fallback, and never mixed with the 3.2.x line.
- **Never** vendor a `third_party/` repository outside the recorded fallback case, nor without
  provenance, ordering before the remote, and `content { includeModule(...) }`.
- **Never** declare `usb.host` as `required="true"`, and never derive the `CAMERA` decision or
  its ledger row here — hand the platform-rule evidence to `android-permissions-derive`.
- **Never** change the requested resolution in response to `unsupported preview size` while
  frames are rendering — that symptom is a double open.
- **Never** capture through the engine's `captureImage()`; stills are in-memory JPEGs from a
  one-shot frame callback with even crop edges, a bounded wait, and reported dimensions.
- **Never** map a body button by assumption, offer a hardware zoom the device does not report, or
  present a crop as optical magnification.
- **Never** report device claims from an emulator run or let a green CI imply the capability
  was tested; **never** edit `spec/android/uvc-microscope/` beyond appending a verified-devices row.
- **Always** establish network ADB before attaching the peripheral, keep the device awake, and
  end with `./gradlew build` plus the device smoke test; report a red state rather than hiding it.
- When `spec/android/uvc-microscope/` disagrees with this skill, the spec wins — report the gap
  and propose a spec change (REQ-6).

## German trigger phrases

Also invoke on equivalent German requests, and reply to the operator in German (instructions in
this file stay English):

- "USB-Mikroskop anbinden / einbinden" / "UVC-Kamera einbinden"
- "Externe USB-Kamera in der App anzeigen"
- "Das Mikroskop zeigt nur ein schwarzes Bild" (step 7 — `libUVCCamera` tag first)
- "Die App stürzt beim Anfordern der USB-Berechtigung ab" (step 3 — the `PendingIntent` symptom)
- "Foto vom Mikroskop aufnehmen" (step 5) / "Der Auslöser am Mikroskop macht nichts" (step 6)
- "Bestehende UVC-Integration prüfen" (operation `audit`)

## Gotchas

Concrete corrections to non-obvious facts the executing agent would otherwise get wrong (the
full symptom table is `references/device-dev-loop.md` §3):

- **`FLAG_IMMUTABLE` is the wrong fix for the `PendingIntent` crash.** The intent must become
  explicit and **stay mutable** — `UsbManager` writes the grant extras into it. The crash itself
  is the engine's `register()`; the fix is not calling it.
- **The `CAMERA` requirement is the platform's, not the engine's** — the USB permission manager
  gates video-class interfaces on `CAMERA` from `targetSdk` 28.
- **A resolving `libnative:3.3.3` POM is a trap** (AAR 404, late misleading failure), and
  `com.serenegiant.usb` (3.2.x) is not mixable with `com.jiangdg.*` (3.3.x).
- **Descriptor frame rates are claims** (30 fps claimed, ~4.7 fps at 4K measured), and a cheap
  body's 4K is **not automatically interpolated** — the reference body passes the detail test.
- **The zoom rocker may drive only the WiFi firmware**; the only USB body event on the reference
  body is the shutter, `button=1, state=1/0`.
- **A dozing phone looks exactly like a dead peripheral**, and **`unsupported preview size`
  with a rendering preview is a double open.**
