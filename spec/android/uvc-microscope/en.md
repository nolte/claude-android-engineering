# USB-C (UVC) Microscope Cameras

Status: draft

## Context

An external USB microscope is the cheapest way to give an Android app a magnified view of a physical subject — a leaf with suspected pest damage, a solder joint, a material sample. It is also the point where Android's ordinary camera knowledge stops being true: the platform camera framework does not reliably surface these devices, the maintained community engine has published artifacts that do not resolve, and its USB permission code crashes outright on a modern `targetSdk`. A skill that approaches this the way it approaches CameraX will produce an app that does not build, does not start, or shows a black screen.

This spec is the authoritative definition of how this portfolio's skills integrate a UVC (USB Video Class) camera: which access path is viable, how the engine dependency is supplied, the defects that must be worked around, how stills are captured, which physical controls on the microscope body are reachable, and — decisive for iteration speed — how such an app is tested at all when the peripheral occupies the device's only USB port.

Provenance: unlike the desk-research specs in this corpus, the requirements below are predominantly **measured**. They come from a complete integration built and hardware-verified on 2026-08-11 against a Generalplus `1b3f:2002` microscope (sold as a "4K WiFi Microscope") on a Pixel 7a running Android 16, with AUSBC 3.3.3. Claims marked [M] were observed on that hardware. A second marker, [I], carries what was established by reading the engine's published artifacts, bytecode and source without a running stream — the §B layer decision rests on that class, not on a measurement. Platform behavior is cited to vendor documentation and, for the USB-permission rule in §C, to AOSP source. One conclusion of the 2026-08-11 session is flagged rather than carried forward unchanged: it was measured against the AUSBC engine only, and Google has since documented native UVC support for Pixel 6 and later (including the reference Pixel 7a) [R15], so the §A access-path decision now begins with a mandatory platform-camera pre-check on the target device and the reference-device conclusion is marked as needing re-verification (§A, §Open Questions). Where a finding is specific to one device body rather than to UVC in general, the requirement says so.

Boundaries: ADB transport, install failures, and log-access mechanics are owned by `spec/android/adb-workflows/` — this spec only adds what changes when a peripheral occupies the USB port. Runtime-permission UX is owned by `spec/android/app-design-navigation/` §F and permission minimalism by `spec/android/security/` §E. Test execution strategy stays with `spec/android/test-automation/`; this spec only establishes why these tests cannot run on an emulator. Upload, storage, and image-recognition pipelines that consume a captured frame are out of scope.

Readers: authors of this repo's Android skills who add microscope or external-camera capability, and reviewers judging whether such an integration is conformant.

## Goals

- Make the access-path decision once, on evidence, so no skill re-litigates CameraX-versus-native for external cameras
- Make the dependency supply reproducible despite an upstream publication that is broken in a way that resolves partially
- Fix the integration layer once, so the wrapper's defects are designed out rather than worked around repeatedly
- Turn every known engine defect into a stated workaround with a recognizable symptom, so a skill does not debug the same crash twice
- Make capture produce an in-memory image an upload pipeline can consume, at a resolution chosen deliberately rather than inherited from the preview
- Make the physical controls on the microscope body reachable where they are wired, and honestly unavailable where they are not
- Make the device-bound development loop fast: the port conflict, the wake-state trap, and the ground-truth diagnostics are known up front

## Non-Goals

- Built-in camera work (CameraX, Camera2 on internal lenses) — ordinary camera guidance applies there and is unaffected by this spec
- Video recording, streaming, or encoding from the UVC device — this spec covers live preview and single-frame stills
- The microscope's own WiFi/access-point mode — a separate product surface that bypasses the phone's USB entirely and keeps the phone's WiFi occupied
- Upload, persistence, and downstream image processing of a captured frame
- Play-Store distribution concerns for apps declaring USB host features
- Audio from UVC/UAC composite devices

## Requirements

### A. Access path

- **MUST NOT** attempt to reach an external UVC camera through the web platform: the origin analysis found no external camera exposed through `getUserMedia` in a WebView or PWA on Android [R7], and WebUSB cannot drive one at all because UVC streams over **isochronous** endpoints, which WebUSB does not support [R6]
- **MUST NOT** assume a React-Native or cross-platform camera wrapper covers it — `react-native-vision-camera` builds on Camera2 and external UVC devices commonly resolve to `undefined` there [R8][R9]; the USB frame grab requires native Android code regardless of the app's UI framework
- **MUST**, as the first step and before any engine dependency is added, verify on the target device whether the microscope already appears as an **external platform camera**: with the device attached, enumerate `CameraManager.getCameraIdList()` (registering a `CameraManager.AvailabilityCallback` for hot-plug) and look for a camera whose `LENS_FACING` is `LENS_FACING_EXTERNAL` and whose `INFO_SUPPORTED_HARDWARE_LEVEL` is `EXTERNAL`, then open a preview through Camera2 or CameraX and record the result — camera ID present or absent, the stream configurations offered, and whether a live preview was reached — in §Verified devices. The platform exposes external USB cameras "through the standard Android Camera2 API" wherever the OEM has enabled the external camera provider, and that enablement is device-dependent, not a property of Android [R16]; Google documents native UVC support ("Only USB cameras with USB Video Class (UVC) specification are supported") for Pixel 6 and later, Pixel 6a and later A-series, and the Pixel Tablet through its Connected Cameras feature [R15]. The help page names a set of apps that surface the camera through a system camera picker and does not state whether an arbitrary third-party app sees it via Camera2, which is exactly why the check is a *measurement* on the target hardware and not a lookup
- **SHOULD** treat Camera2's `LENS_FACING_EXTERNAL` as OEM-dependent rather than absent: the constant exists [R5], coverage for USB cameras varies by device [R16], and a skill **MUST NOT** build a required capability on it without the pre-check above having passed on that hardware — nor, conversely, integrate a native engine on the assumption that it will fail
- **MUST** integrate a `libuvc`-based native engine [R4] for a required external-camera capability **only if** the pre-check found no usable platform camera, or found one whose stream configurations or controls do not serve the feature (the pre-check result is the recorded reason); in this portfolio the engine is AUSBC (AndroidUSBCamera) [R1]. Where the pre-check passes, the platform camera is the access path, ordinary CameraX guidance applies, and §B–§G of this spec do not — the remaining sections that still hold are §C's `CAMERA` and USB-permission rules and §I's workflow constraints. The 2026-08-11 reference-device conclusion — that the Pixel 7a needs the engine — predates this pre-check and is marked for re-verification in §Open Questions; until it is re-run, the engine path stays the *measured* known-working path for that device and the platform path stays *unmeasured*, and a skill states that distinction rather than choosing silently
- **SHOULD** record the concrete target device's descriptors before designing around it — vendor/product ID, pixel format, and the mode list — because negotiation and still strategy depend on them; the reference device is `1b3f:2002`, `iProduct = "GENERAL - UVC"`, UVC 1.00, bus-powered, MJPEG, modes 3840×2160 / 2048×1024 / 1920×1080 / 1280×720 [R7]
- **MUST NOT** trust the advertised frame rate: the reference device's descriptor claims 30 fps while delivering roughly 4.7 fps at 4K and 17 fps at 1080p [R7][M]; measure before choosing a preview mode
- **MUST** record a newly measured device in §Verified devices — vendor/product ID, modes, measured rates, which body buttons reach USB, and whether the UVC zoom control is supported — so the next project inherits the measurement instead of repeating a hardware session

### B. Engine integration layer and artifact supply

- **MUST** integrate at the `libuvc` layer — `USBMonitor` plus `UVCCamera` — rather than through AUSBC's `CameraUVC` convenience wrapper. The wrapper's cost is concrete and cumulative: it hides the button callback behind a private field (§F), owns an open sequence that races (§D), and implements a mode change as a full restart with a hard-coded one-second pause (§G). Integrating one layer down removes all three, and what it costs — an own camera thread, surface handling, and mode negotiation — is roughly 150 lines against the 200 the wrapper displaces [I]
- **MAY** stay on AUSBC's `CameraUVC` wrapper in exactly two cases: while the runtime proof named in §Open Questions is still outstanding, or where an existing codebase is already committed to `libausbc`. A project on that fallback then owes the vendoring rules below, §C's patch, §D's guard, §F's reflection and §G's restart cost, **MUST** record which of the two cases applies in the module that owns the engine, and **MUST NOT** mix the two paths
- **MUST** acquire the USB permission through the platform `UsbManager` and never call `USBMonitor.register()`: `register()` is the sole carrier of the `targetSdk`-34 defect in §C, while `hasPermission()`, `openDevice()`, and the `UsbControlBlock` constructor depend only on the granted permission and the `UsbManager` handle. Not calling it removes the defect instead of patching around it [I]
- **MUST** verify that every artifact of the chosen version resolves before pinning it, and **MUST** treat a resolving POM as insufficient evidence — AUSBC 3.3.3 is published incompletely (JitPack's build of that tag fails in `:libuvc:ndkClean` for lack of an NDK), so `libausbc` exists while `libuvc` and `libnative` were never published, and `libnative:3.3.3` serves a POM whose AAR returns 404, making resolution fail late and with a misleading message [R2][M]
- **SHOULD** pin `libuvc:3.2.7`, whose graph (`libuvccommon`, `appcompat`, `xlog`) resolves completely and which carries the full API this spec needs — `openDevice`, `setButtonCallback`, `setStatusCallback`, `setPreviewSize`, `setFrameCallback`, `setPreviewTexture`, `checkSupportFlag` [I]; taking it instead of `libausbc` drops `libnative` from the graph entirely and makes vendoring unnecessary
- **MUST** note that the 3.2.x line uses the original `com.serenegiant.usb` package while 3.3.x renamed to `com.jiangdg.*` — the two generations are not mixable, which is precisely why a project on `libausbc:3.3.3` cannot substitute a published `libuvc` and is forced into vendoring [I]
- **SHOULD**, only where a wrapper dependency is unavoidable, close a publication gap with a vendored, version-controlled Maven repository under `third_party/` holding the missing artifacts under their original coordinates, with a README recording for each artifact where the bytes came from, why that source is acceptable, and what would retire it; the repository **MUST** be declared **before** the remote one and both constrained with `content { includeModule(...) }`. Building the engine from source in CI is **not** warranted: it would import the same NDK toolchain problem that broke the upstream publication, to serve a dependency the layer decision above removes
- **SHOULD**, in that same fallback case, add `libuvc` as an explicit compile dependency alongside `libausbc` — the published POM scopes it `runtime`, yet its types (`IDeviceConnectCallBack`, `USBMonitor.UsbControlBlock`) appear in the API a caller must implement, so the build fails to compile without it [M]

### C. Manifest, permissions, and attachment

- **MUST** declare `<uses-feature android:name="android.hardware.usb.host" android:required="false" />` — `required="true"` would exclude every non-OTG device from installing an app that should still run with a clear "no USB host" message [R3]
- **MUST** declare the `CAMERA` runtime permission and hold it before opening the stream. This is a **platform** rule, not an engine quirk: the system's `UsbUserPermissionManager` refuses both `hasPermission()` and `requestPermission()` for any USB device that reports video capture unless the calling app targets below API 28 or holds `CAMERA` — it logs "Camera permission required for USB video class devices", answers a request with `EXTRA_PERMISSION_GRANTED = false` without showing the dialog, and additionally treats the device-wide camera privacy toggle as a denial [R14]. It therefore applies identically to §B's direct `libuvc` path and to AUSBC's wrapper, whose refusal at `targetSdk >= 28` was the measured symptom [M]; a UVC device with a microphone is still granted, but with a warning where `RECORD_AUDIO` is not held [R14]. The rationale shown to the user **MUST** explain the microscope, not a selfie camera
- **MUST** handle the USB permission grant as a separate, second consent: it is issued by the system USB dialog per device, not by the Android runtime-permission flow, and a denial is a distinct state from a denied `CAMERA` permission [R3]
- **MUST** build the permission request `targetSdk`-correctly when writing it: the intent behind the `PendingIntent` has to be **explicit** (`setPackage`) while **staying** mutable — `UsbManager` attaches the grant extras, so `FLAG_IMMUTABLE` breaks the flow — and a receiver for the custom permission action has to declare its export state, which `targetSdk` 34 enforces [R12][R13]
- **MUST** know the symptom for the case where an engine gets this wrong, because it is fatal and immediate rather than degraded: `USBMonitor.register()` in AUSBC 3.3.3 wraps an implicit intent in a mutable `PendingIntent` and throws `IllegalArgumentException: … disallows creating or retrieving a PendingIntent with FLAG_MUTABLE, an implicit Intent …` on the first registration under `targetSdk >= 34` [R12][M]. The §B layer decision avoids that method entirely; a project that cannot **MUST** patch the vendored artifact along the two lines above
- **SHOULD** offer attachment-driven launch via an `android.hardware.usb.action.USB_DEVICE_ATTACHED` intent filter with a `device_filter.xml` listing the target vendor/product ID [R3], and **MUST NOT** make the app's only entry point depend on it — filters are per-device and fail silently on unlisted hardware
- **MUST** expose a state model that distinguishes the failure modes a user can act on: no device attached, device attached but USB permission pending, USB permission denied, host mode unsupported by the phone, and engine error — collapsing these into one "camera unavailable" makes the app undiagnosable in the field

### D. Stream lifecycle

- **MUST** guard the open sequence with a concurrency flag, whoever owns it. The hazard is generic — a permitted device and a live surface arrive from independent callbacks — but AUSBC makes it acute by flipping `isCameraOpened()` only at the end of its open sequence, so both callbacks pass the check; the losing call cannot claim the busy device and posts a **misleading** `ERROR "unsupported preview size"` while the winning stream renders normally [M]
- **MUST** read that symptom correctly: `unsupported preview size` reported while frames are visibly rendering means a double open, not an unsupported mode — changing the requested resolution in response is the wrong fix [M]
- **MUST** open only when both preconditions hold — a permitted device **and** a live preview surface — and re-evaluate on whichever arrives second, since their order is not guaranteed
- **SHOULD** keep the raw-frame callback alive on whichever preview path it chooses, because that callback is what §E captures from and a pure GL render path does not feed it. On the §B fallback path this means `RenderMode.NORMAL` rather than the OpenGL mode, which delivers frames only with `isRawPreviewData`/`isCaptureRawImage` set [I]
- **MUST** tear the stream down when the screen leaves composition and re-register on return, and **MUST NOT** treat a transient close during a deliberate reconfiguration as device loss
- **MUST** re-attach any engine-level callbacks after every reopen, binding to the camera instance the state callback hands over rather than to a mutable field — a concurrent detach can clear the field and silently leave the hardware button dead for the rest of the session [M]

### E. Still capture

- **SHOULD NOT** use AUSBC's own `captureImage()` for an upload pipeline: it requires `WRITE_EXTERNAL_STORAGE` and writes into DCIM, which contradicts permission minimalism (`spec/android/security/` §E) and puts a file between the camera and the consumer [M]
- **MUST** instead grab a single frame through a one-shot preview-data callback and encode it in process with `YuvImage.compressToJpeg` [R10], which also accepts the crop rectangle a digital zoom needs
- **MUST** round every crop edge to an even pixel: NV21 subsamples chroma 2×2, so an odd boundary shifts the colour planes against the luma plane
- **MUST** bound the frame wait with a timeout and surface a typed failure — at 4.7 fps a naive wait looks identical to a hang
- **SHOULD** rely on the engine dropping frames whose size does not match the active request, which makes stale frames after a mode change self-discarding rather than a corruption source [M]
- **MUST** report the captured dimensions and byte size back to the caller or the log; without them a silently downgraded capture is invisible [M]

### F. Physical controls on the microscope body

- **MUST NOT** expect the body's buttons to arrive as Android key events: the reference device registers no HID input device at all, so nothing reaches `onKeyDown` [M]
- **MUST** read the shutter from the UVC **status endpoint** instead, via the engine's button callback — measured on the reference device as `button=1, state=1` on press and `state=0` on release, matching UVC's standard still-image button [R11][M]
- **MUST NOT** need reflection for this under the §B layer decision: `setButtonCallback` and `setStatusCallback` are public on `UVCCamera` [M]. Only a project stuck on AUSBC's `CameraUVC`, which hides them behind a private field, **MAY** reach them reflectively — and then **MUST** confine the reflection to the module that owns the engine, guard it against a null instance, and add a matching `-keepclassmembers` rule, since R8 would otherwise rename the field in release builds
- **MUST NOT** assume the remaining buttons are wired to USB. The reference device's zoom rocker emits nothing over USB — no button event and no control-change event across a 30-minute measurement window — and the device additionally reports no support for the UVC zoom control; those keys drive its standalone WiFi firmware only [M]
- **MUST** verify per device rather than mapping button indices speculatively, and **SHOULD** log every unmapped button and status event raw so an unknown body can be mapped from evidence in a single hardware session
- **SHOULD** provide on-screen zoom as the substitute where the hardware path is absent, implemented as a centre crop applied to both the preview transform and the captured frame so the photo matches what the user framed; a skill **MUST** describe such zoom as digital and **MUST NOT** present it as magnification

### G. Resolution strategy

- **SHOULD** keep the preview at a mode fast enough to frame by and raise resolution only for the still — at 4.7 fps a 4K preview is unusable for aiming a microscope, while the frame rate is irrelevant to a single shot [R7][M]
- **MUST** budget for what a mode change costs and **MUST** measure it rather than assume it: AUSBC's `updateResolution` is a full close-and-reopen with a hard-coded one-second pause, which makes a switch up and back freeze the preview for roughly four to five seconds [M]. Driving `UVCCamera` directly (§B) allows the cheaper `stopPreview` → `setPreviewSize` → `startPreview` sequence without releasing the device; either way a skill **MUST** surface the wait in the UI and **MUST** serialize captures so two cannot overlap
- **MUST** degrade rather than fail: if the switch does not take within a bounded timeout, capture at the live resolution instead of returning an error, and restore the preview mode even when the capture was cancelled
- **SHOULD** query the device's largest supported mode instead of hard-coding one, so the same code adapts across bodies; measured on the reference device this yields 3840×2160 at roughly 673 kB of JPEG against 130 kB at 1080p [M]
- **MUST** verify that a device's top mode carries real detail before paying its latency, and **MUST** verify it by measurement rather than by eye: photograph a subject with fine texture, then (a) downscale the capture by half and back up and take the residual against the original, and (b) compare the radially averaged power spectrum above half of Nyquist against the mid band. Firmware upscaling collapses both — a small residual and a steep drop with a knee at exactly half of Nyquist. Calibrate the thresholds by running the same two tests on the capture deliberately downscaled and re-upscaled; that control is what separates upscaling from JPEG noise [M]
- **SHOULD** treat "cheap microscope, therefore interpolated" as a hypothesis to test rather than a fact: the reference device passes. Measured 2026-08-11, halving and restoring its 4K capture loses 17.5% of image contrast against 3.5% for a deliberately upscaled control, and the power spectrum falls only 1.25 decades into the high band with no knee at half of Nyquist against 3.07 decades for the control — so its top mode resolves detail 1080p cannot, and defaulting stills to the largest mode is justified here [M]
- **SHOULD** know that AUSBC negotiates with a hard-coded 10 fps minimum, which succeeds on devices whose descriptors overstate their frame rate but can reject an honest low-rate mode [I]

### H. Architecture and isolation

- **MUST** place the engine behind an app-owned interface and confine every engine type, including the reflective access of §F, to a single module — the engine is a replaceable implementation detail and its API is neither stable nor well documented
- **SHOULD** express the camera's condition as a sealed state type with the distinguishable failures of §C rather than nullable fields and booleans
- **MUST** keep the geometry and encoding logic (crop rounding, JPEG encoding) free of engine and Android-view types so it is unit-testable without a device — the hardware-bound parts cannot be, which makes the parts that can be worth isolating
- **SHOULD** record every non-obvious workaround from §B–§G as a comment stating the constraint at the point it is imposed; a future reader deleting a guard because it "looks redundant" reintroduces a defect that costs a hardware session to rediscover

### I. Development and test workflow

- **MUST** plan for the port conflict as the primary workflow constraint: the microscope occupies the phone's only USB-C port, so ADB **MUST** run over the network for the entire development loop [M] — cable first to install and enable network ADB, then unplug and attach the peripheral
- **MUST** follow `spec/android/adb-workflows/` §A for that transport: Android 11+ pairing is the default and legacy `tcpip 5555` is a flagged fallback that gets closed with `adb usb` afterwards
- **MUST** keep the device awake during a session: on a dozing or locked phone the preview stops and network ADB becomes unreachable, which reads exactly like a peripheral failure [M]
- **SHOULD** use `adb shell dumpsys usb` and its `host_connected` field as the ground truth for whether the peripheral is attached at all, before interpreting any app-level symptom [M]
- **SHOULD** watch the engine's native tag alongside the app's own: frame-allocation lines from the `libUVCCamera` tag prove the stream is live even when the surface renders black, which separates a stream fault from a rendering fault [M]
- **MUST** budget for OEM install restrictions when the test device is not a stock build — MIUI's `INSTALL_FAILED_USER_RESTRICTED` blocks `adb install` and shell `pm install` alike, leaving on-device installation from a pushed file as the fallback [M]; the decode table lives in `spec/android/adb-workflows/` §B
- **MUST NOT** plan emulator coverage for this capability: emulators provide no USB host, so a physical OTG-capable device is required and these paths cannot gate CI (`spec/android/test-automation/`). A skill **MUST** state that limitation rather than leaving a green CI run to imply the capability was tested
- **SHOULD** capture evidence with `screencap` plus the log line reporting captured dimensions, so a hardware session produces a reviewable artifact instead of a verbal report [M]

## Verified devices

Each row is one hardware session. A device is listed only after the listed columns were observed directly; an unmeasured column is `unknown`, never inferred from a datasheet. The 2026-08-11 session predates §A's platform-camera pre-check: the row below is a measurement of the `libuvc` path on the Pixel 7a, not evidence that the platform path is absent there — that check is outstanding (§Open Questions), and a new row records its result alongside the columns below.

| USB ID | Descriptor | Modes | Measured rate | Body buttons over USB | UVC zoom control | Verified |
| --- | --- | --- | --- | --- | --- | --- |
| `1b3f:2002` | `GENERAL - UVC`, UVC 1.00, bus-powered, MJPEG | 3840×2160 (measured genuine, not upscaled) / 2048×1024 / 1920×1080 / 1280×720 | ~4.7 fps @ 4K, ~17 fps @ 1080p (descriptor claims 30) | Shutter only, as UVC button index 1; zoom rocker sends nothing | Not supported (`CTRL_ZOOM_ABS` absent) | 2026-08-11, Pixel 7a / Android 16 |

## Acceptance Criteria

The criteria below are a deliberate representative rollup of §A–§I, not a 1:1 mapping; every requirement bullet above is normative on its own.

- [ ] No skill proposes a WebView, WebUSB, or cross-platform-wrapper path for an external UVC camera; the platform-camera pre-check (`LENS_FACING_EXTERNAL` / hardware level `EXTERNAL`, preview attempted) was run on the target device and its result recorded before any engine dependency was added, and none makes a required capability depend on either path without that measurement
- [ ] The integration sits at the `libuvc` layer and the USB permission is acquired through the platform `UsbManager`, with `USBMonitor.register()` never called — unless the project has recorded a §B fallback condition, in which case the vendoring, patching and reflection criteria below apply in its place
- [ ] Every transitive artifact of the pinned version resolves, verified by AAR and not by POM alone; a vendored repository exists only where a wrapper dependency forced it, ordered before the remote one with content filtering and carrying per-artifact provenance
- [ ] The manifest declares USB host as `required="false"`, the app holds `CAMERA` before opening on either access path — as the platform's `UsbUserPermissionManager` requires for video-class devices at `targetSdk >= 28` — and the USB grant is modelled as a separate consent
- [ ] The USB permission request is `targetSdk`-current: an explicit, still-mutable `PendingIntent` and a receiver registered with an export flag — verified by the app reaching a live preview rather than crashing on registration
- [ ] The app distinguishes no-device, permission-pending, permission-denied, no-host-support, and engine-error states in its UI
- [ ] The open path is guarded against concurrent opens, and the codebase contains no resolution change made in response to a spurious "unsupported preview size"
- [ ] Capture returns an in-memory JPEG without requiring storage permissions, with even crop edges, a bounded wait, and dimensions reported
- [ ] Engine callbacks are re-attached after every reopen using the instance supplied by the state callback
- [ ] The codebase reaches the button and status callbacks directly; any reflective engine access that remains is justified by a wrapper dependency, confined to the owning module, null-guarded, and covered by a ProGuard keep rule
- [ ] Button mapping is evidence-based: only measured indices are mapped, unmapped events are logged raw, and no UI offers a hardware control the device does not report
- [ ] Zoom presented to the user is labelled digital where it is a crop, and applies identically to preview and capture
- [ ] A resolution switch for stills is serialized, surfaced in the UI, bounded by a timeout, degrades to the live mode on failure, and always restores the preview mode
- [ ] Every engine type, including any reflective access, is confined to the one module that owns the engine, and the crop and encoding logic is unit-tested without a device
- [ ] The skill's test instructions establish network ADB before the peripheral is attached, name the wake-state requirement, and state that emulators cannot cover this capability

## Open Questions

All questions are parking-lot class: each states the working default the requirements above already encode.

- The §B layer decision is settled on evidence — the published `libuvc:3.2.7` carries the required API, and `openDevice`/`hasPermission`/`UsbControlBlock` provably do not depend on `register()` — but it is verified by source and binary inspection, not yet by a running stream. The remaining step is a runtime proof on the reference device; until it exists, the wrapper-based path documented in §C–§G stays the known-working fallback.
- The reference-device access-path conclusion needs re-verification. The 2026-08-11 session integrated the engine directly and never ran §A's platform-camera pre-check; Google has since documented native UVC support for Pixel 6 and later, including the A-series from the 6a and therefore the Pixel 7a, surfaced through a system camera picker for a named set of apps [R15], and AOSP describes the Camera2 exposure of external cameras as OEM-enabled [R16]. Whether the `1b3f:2002` microscope enumerates as `LENS_FACING_EXTERNAL` for a third-party app on the Pixel 7a — and, if it does, whether its 4K MJPEG mode and the UVC status-endpoint button (§F) are reachable through Camera2 — is unmeasured. Working default until measured: the engine path stays authoritative for that device because it is the only measured one; the pre-check is mandatory for every new project and for the next hardware session on the reference device, and its result is recorded in §Verified devices either way. The measured findings of §D–§G remain valid for the engine path regardless of the outcome.

## References

Sources retrieved 2026-08-11. Class markers: (P) primary/authoritative vendor or standards documentation, (S) secondary (maintained tool repositories, their build logs, and upstream issue trackers), (M) measured — first-party observation from the hardware-verified integration described in §Context, cited inline as [M]; (I) inspected — first-party reading of the engine's published artifacts, bytecode or source, with no running stream behind it, cited inline as [I].

- [R1] AndroidUSBCamera (AUSBC) — the `libuvc`-based engine used in this portfolio (S): <https://github.com/jiangdongguo/AndroidUSBCamera>
- [R2] JitPack build log for AUSBC 3.3.3, showing the `:libuvc:ndkClean` failure behind the incomplete publication (S): <https://jitpack.io/com/github/jiangdongguo/AndroidUSBCamera/3.3.3/build.log>
- [R3] USB host overview — host-mode manifest declaration, device filters, and the per-device permission dialog (P): <https://developer.android.com/develop/connectivity/usb/host>
- [R4] libuvc — the cross-platform UVC implementation the Android engines wrap (S): <https://github.com/libuvc/libuvc>
- [R5] `CameraMetadata.LENS_FACING_EXTERNAL` reference (P): <https://developer.android.com/reference/android/hardware/camera2/CameraMetadata#LENS_FACING_EXTERNAL>
- [R6] WebUSB API specification — transfer types supported, isochronous excluded (P): <https://wicg.github.io/webusb/>
- [R7] Origin device analysis — descriptors, mode list, measured frame rates, and the ruled-out access paths for the reference microscope (S): <https://github.com/nolte/kamerplanter-android/issues/1>
- [R8] react-native-vision-camera issue 1407 — external USB cameras undefined (S): <https://github.com/mrousavy/react-native-vision-camera/issues/1407>
- [R9] react-native-vision-camera issue 2131 — external USB cameras undefined (S): <https://github.com/mrousavy/react-native-vision-camera/issues/2131>
- [R10] `YuvImage` reference — NV21 to JPEG with a crop rectangle (P): <https://developer.android.com/reference/android/graphics/YuvImage>
- [R11] USB Device Class Definition for Video Devices — status endpoint and still-image button semantics (P): <https://www.usb.org/document-library/video-class-v15-document-set>
- [R12] Android 14 behavior changes — mutable `PendingIntent` with an implicit intent is rejected for `targetSdk >= 34` (P): <https://developer.android.com/about/versions/14/behavior-changes-14#security>
- [R13] Android 14 behavior changes — runtime-registered receivers must declare export state (P): <https://developer.android.com/about/versions/14/behavior-changes-14#runtime-receivers-exported>
- [R14] AOSP `UsbUserPermissionManager` — `CAMERA` required for video-class USB devices at `targetSdk >= 28` in `hasPermission()` and `requestPermission()`, camera privacy toggle, microphone warning (P): <https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/services/usb/java/com/android/server/usb/UsbUserPermissionManager.java>
- [R15] Pixel Phone Help — Connected Cameras: UVC-only USB camera support for Pixel 6 and later, Pixel 6a and later A-series, and the Pixel Tablet; the system camera picker and the named apps (P): <https://support.google.com/pixelphone/answer/15985851>
- [R16] AOSP — External USB cameras: exposure through Camera2 with the `EXTERNAL` hardware level, OEM-side enablement of the external camera provider, `android.hardware.usb.host` prerequisite (P): <https://source.android.com/docs/core/camera/external-usb-cameras>
