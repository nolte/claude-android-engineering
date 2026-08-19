# Access-path decision and engine supply

The first and most consequential decision in a UVC integration: whether the platform already
exposes the camera, and if not, at which layer the libuvc engine is integrated and how its
artifacts are supplied. Grounded in `spec/android/uvc-microscope/` §A and §B; on any conflict
that spec wins.

## Table of contents

- [1. Capture the device evidence](#1-capture-the-device-evidence)
- [2. Probe the platform camera first](#2-probe-the-platform-camera-first)
- [3. The decision](#3-the-decision)
- [4. Path A — platform external camera](#4-path-a--platform-external-camera)
- [5. Path B — libuvc layer (default engine path)](#5-path-b--libuvc-layer-default-engine-path)
- [6. Path C — recorded wrapper fallback](#6-path-c--recorded-wrapper-fallback)
- [7. What to record](#7-what-to-record)

## 1. Capture the device evidence

Before designing anything, with the peripheral attached and the phone awake:

```sh
adb shell dumpsys usb            # host_connected, attached devices, VID:PID, interface classes
lsusb -v -d <vid>:<pid>          # from a host machine: UVC version, formats, frame descriptors
```

Record: vendor/product ID, `iProduct`, UVC version, bus- or self-powered, pixel format (MJPEG or
uncompressed), and the mode list. Do not trust the descriptor's frame rate — the reference body
claims 30 fps and delivers ~4.7 fps at 4K, ~17 fps at 1080p (spec §A). Rates are measured in
step 7 of the skill.

If the body is already in the spec's §Verified devices, inherit its row; otherwise the run owes a
new row (`references/device-dev-loop.md` §4).

## 2. Probe the platform camera first

Camera2's `LENS_FACING_EXTERNAL` exists, but its coverage for USB cameras is OEM-dependent
(spec §A). Recent Pixel generations document native UVC support; the answer for the target
device is measured, not assumed — in either direction. Run this probe **on the target device**
with the microscope attached and the system USB grant given (a debug activity or an instrumented
test is enough; it is not shipped):

```kotlin
val manager = context.getSystemService(CameraManager::class.java)
val external = manager.cameraIdList.filter { id ->
    val chars = manager.getCameraCharacteristics(id)
    chars.get(CameraCharacteristics.LENS_FACING) == CameraCharacteristics.LENS_FACING_EXTERNAL &&
        chars.get(CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL) ==
            CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL_EXTERNAL // uvc-microscope §A: both criteria
}
external.forEach { id ->
    val map = manager.getCameraCharacteristics(id)
        .get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP)
    Log.i("UvcProbe", "external camera $id: jpeg=${map?.getOutputSizes(ImageFormat.JPEG)?.toList()} " +
        "yuv=${map?.getOutputSizes(ImageFormat.YUV_420_888)?.toList()}")
}
Log.i("UvcProbe", "external cameras: $external (model=${Build.MODEL}, build=${Build.DISPLAY})")
```

Also useful as ground truth: `adb shell dumpsys media.camera` lists every camera the HAL
exposes; an external camera appears there only when the OEM's HAL supports it. Also register
`CameraManager.AvailabilityCallback` in the probe — an external camera can appear a moment after
attach.

Enumeration alone is not the measurement spec §A asks for. For every enumerated external camera
the probe **MUST** then attempt a live preview — CameraX with a `CameraSelector` filtering on
`LENS_FACING_EXTERNAL` bound to a `Preview` use case, or Camera2 `openCamera` plus a
`CaptureRequest.TEMPLATE_PREVIEW` session on a `SurfaceTexture` — and record whether frames
actually arrived (first `onSurfaceTextureUpdated` / `Preview` frame within a bounded timeout):

```kotlin
val selector = CameraSelector.Builder()
    .addCameraFilter { infos -> infos.filter { Camera2CameraInfo.from(it).getCameraCharacteristic(
        CameraCharacteristics.LENS_FACING) == CameraCharacteristics.LENS_FACING_EXTERNAL } }
    .build()
val preview = Preview.Builder().build().also { it.setSurfaceProvider(previewView.surfaceProvider) }
provider.bindToLifecycle(lifecycleOwner, selector, preview)
// pass = a frame reached the surface within the timeout; log the outcome
```

The probe **passes** only when a `LENS_FACING_EXTERNAL` camera is enumerated, exposes a
stream configuration usable for preview and a still (JPEG or YUV output sizes matching the
descriptor's mode list), **and** the preview attempt reached live frames. An enumerated camera
with no usable sizes, one whose preview never delivers a frame (open error, session failure,
black surface past the timeout), or one that disappears on reattach, is recorded as a failed
probe.

Record model, OS build, camera ID, formats, sizes, and the preview outcome (reached / not
reached, with the error if any) in the run and in the verified-devices row — spec §A requires
all three facts (ID present or absent, stream configurations, live preview reached).

## 3. The decision

Ask in this order and stop at the first path that fits.

1. **Did the platform probe pass on the target device?** → Path A. The capability is built on
   CameraX/Camera2 with an external-lens selector, and no engine dependency is added.
2. **Otherwise** → Path B, the libuvc layer. This is the engine default of spec §B.
3. **Is the runtime proof of the §B layer decision still outstanding for this project, or is the
   codebase already committed to `libausbc`?** → Path C, the wrapper fallback, with the case
   recorded in the engine module. Only these two cases qualify.

Non-paths (spec §A): WebView `getUserMedia` (no external camera exposed), WebUSB (no isochronous
transfers), React-Native or other cross-platform camera wrappers (Camera2-based, external devices
resolve to `undefined`). A non-native UI still needs a native frame grab.

| | Path A — platform | Path B — libuvc layer | Path C — wrapper fallback |
|---|---|---|---|
| Engine dependency | none | `libuvc:3.2.7` | `libausbc:3.3.3` + vendored `libuvc`/`libnative` |
| USB grant | system dialog on the platform's terms | app-owned via `UsbManager` | app-owned via `UsbManager`, `register()` avoided or patched |
| Button callback | not reachable through Camera2 | direct (`setButtonCallback`) | reflective, confined, keep rule |
| Mode change | CameraX use-case rebind | `stopPreview` → `setPreviewSize` → `startPreview` | full restart, ~1 s hard-coded pause |
| Coverage | OEM-dependent, measured per device | any OTG host | any OTG host |

## 4. Path A — platform external camera

Only reachable after a passed probe. Build with CameraX where the app already uses it, selecting
the external lens (`CameraSelector.Builder().addCameraFilter { … LENS_FACING_EXTERNAL … }`), or
with Camera2 on the enumerated ID. `Preview` plus `ImageCapture` (in memory via
`OnImageCapturedCallback`, no storage permission) cover preview and stills. Handle detach as
camera unavailability, not as a crash.

What Path A does **not** give: the UVC status endpoint. Body buttons (spec §F) are not reachable
through Camera2, so the shutter is on-screen only — record that limitation honestly in the run
and the verified-devices row (`Body buttons over USB: not reachable on Path A`).

The spec has no Path A capture recipe beyond the §A caveat; report it as a spec extension
proposal per REQ-6, do not invent conventions beyond CameraX defaults.

## 5. Path B — libuvc layer (default engine path)

Integrate at `USBMonitor` + `UVCCamera` (package `com.serenegiant.usb`, the 3.2.x line), not
through AUSBC's `CameraUVC` wrapper (spec §B). What it costs — an own camera thread, surface
handling, mode negotiation — is roughly 150 lines against the 200 the wrapper displaces.

**Version catalog:**

```toml
[versions]
libuvc = "3.2.7"

[libraries]
uvc-libuvc = { module = "com.github.jiangdongguo.AndroidUSBCamera:libuvc", version.ref = "libuvc" }
```

with the JitPack repository declared in `settings.gradle.kts` and constrained:

```kotlin
maven("https://jitpack.io") {
    content { includeGroup("com.github.jiangdongguo.AndroidUSBCamera") }
}
```

**Resolution proof — mandatory before pinning** (spec §B): a resolving POM is not evidence.
Prove every artifact of the graph downloads as an AAR:

```sh
./gradlew :camera-uvc:dependencies --configuration releaseRuntimeClasspath | grep -i uvc
./gradlew :camera-uvc:assembleRelease --refresh-dependencies      # fails late on a 404 AAR
```

Expected graph for `libuvc:3.2.7`: `libuvccommon`, `appcompat`, `xlog` — complete, no
`libnative`, no vendoring needed. If any artifact resolves as POM-only, stop and re-decide;
do not paper over it with a vendored repository (that is Path C's tool, for Path C's cases).

**API the skill relies on** (verified by inspection of the published artifact, spec §B):
`USBMonitor.hasPermission`, `USBMonitor.openDevice` (returns `UsbControlBlock`),
`UVCCamera.open`, `setPreviewSize`, `setPreviewTexture`/`setPreviewDisplay`,
`setFrameCallback`, `startPreview`, `stopPreview`, `setButtonCallback`, `setStatusCallback`,
`getSupportedSizeList`, `checkSupportFlag`. Verify the signatures against the resolved AAR when
writing the module — the runtime proof of this layer is still an open question in the spec, and
the skill reports the outcome of its device run against it (REQ-6).

Also on this path: **never call `USBMonitor.register()`** — it is the sole carrier of the
`targetSdk`-34 `PendingIntent` defect (spec §C), while `hasPermission`, `openDevice`, and the
`UsbControlBlock` constructor depend only on the granted permission and the `UsbManager` handle.
The app acquires the grant itself (`references/engine-integration.md` §2).

Note the ABI packaging: the AAR ships native libraries; check 16 KB page-size alignment per
`spec/android/release-readiness/` §D and report the result rather than assuming it.

## 6. Path C — recorded wrapper fallback

Legal only in the two cases of §3, and then the project owes all of the following (spec §B):

- The case is **recorded** in the module that owns the engine (a comment at the dependency
  declaration or a `README` in the module), and the two lines are never mixed —
  `com.serenegiant.usb` (3.2.x) and `com.jiangdg.*` (3.3.x) are different packages.
- **Vendored Maven repository** under `third_party/` holding the artifacts JitPack never
  published (`libuvc:3.3.3`, `libnative:3.3.3`) under their original coordinates, with a `README`
  recording per artifact where the bytes came from, why that source is acceptable, and what
  retires it. Declared **before** the remote repository and both constrained:

  ```kotlin
  maven(url = uri("$rootDir/third_party/m2")) {
      content { includeModule("com.github.jiangdongguo.AndroidUSBCamera", "libuvc")
                includeModule("com.github.jiangdongguo.AndroidUSBCamera", "libnative") }
  }
  maven("https://jitpack.io") {
      content { includeModule("com.github.jiangdongguo.AndroidUSBCamera", "libausbc") }
  }
  ```

  Building the engine from source in CI is not warranted (it imports the NDK problem that broke
  the upstream publication).
- `libuvc` added as an **explicit compile dependency** alongside `libausbc` — the POM scopes it
  `runtime`, but `IDeviceConnectCallBack` and `USBMonitor.UsbControlBlock` appear in the API a
  caller must implement.
- Either the app still acquires the USB grant itself and never calls `register()`, or — where the
  wrapper's flow cannot be bypassed — the vendored artifact is **patched** along the two lines of
  spec §C (explicit intent, export flag), and the patch is recorded in the `third_party/` README.
- The §D open guard, the §F reflection rules (confined, null-guarded, `-keepclassmembers`), and
  the §G restart cost (~4–5 s per switch up and back) are accepted and surfaced.
- `RenderMode.NORMAL` so the raw-frame callback stays alive for capture (spec §D).

## 7. What to record

In the run's `decisions:` (resume envelope) and in the run report:

- Descriptors from §1 and whether the body was already verified.
- Probe result from §2: model, build, external camera IDs, formats and sizes, pass/fail.
- The path (A/B/C) with the reason; for C, which of the two cases applies and where it is
  recorded in the module.
- The artifact resolution proof: the pinned coordinates and the command output showing each
  AAR resolved.
- Every spec gap met (Path A capture recipe, runtime proof of the §B layer, receiver export
  evidence) as a proposed spec extension (REQ-6).
