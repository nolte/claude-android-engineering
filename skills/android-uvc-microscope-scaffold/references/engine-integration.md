# Engine integration — manifest, permission, lifecycle, capture, controls

Templates for the libuvc-layer path (Path B) with the wrapper-fallback deltas noted. Grounded in
`spec/android/uvc-microscope/` §C–§H; on any conflict that spec wins. Kotlin, comments, and
resource keys stay English; user-visible copy is externalized to `strings.xml`.

## Table of contents

- [1. Manifest](#1-manifest)
- [2. USB grant request (targetSdk-correct)](#2-usb-grant-request-targetsdk-correct)
- [3. State model and module boundary](#3-state-model-and-module-boundary)
- [4. Guarded open sequence](#4-guarded-open-sequence)
- [5. Lifecycle and callback re-attachment](#5-lifecycle-and-callback-re-attachment)
- [6. Still capture in memory](#6-still-capture-in-memory)
- [7. Resolution strategy and mode switch](#7-resolution-strategy-and-mode-switch)
- [8. Body buttons and zoom](#8-body-buttons-and-zoom)
- [9. Unit-testable geometry](#9-unit-testable-geometry)

## 1. Manifest

```xml
<uses-feature android:name="android.hardware.usb.host" android:required="false" />
<!-- CAMERA: declared and requested per the ledger row from android-permissions-derive.
     Platform rule: from targetSdk 28 the USB permission manager grants a video-class
     interface only to an app holding CAMERA (UsbUserPermissionManager). Rationale copy names
     the microscope, never a selfie camera. -->
<uses-permission android:name="android.permission.CAMERA" />

<activity android:name=".microscope.MicroscopeActivity" android:exported="true">
    <!-- Optional attachment-driven launch. Never the only entry point: filters are per device
         and fail silently on unlisted hardware (spec §C). -->
    <intent-filter>
        <action android:name="android.hardware.usb.action.USB_DEVICE_ATTACHED" />
    </intent-filter>
    <meta-data android:name="android.hardware.usb.action.USB_DEVICE_ATTACHED"
        android:resource="@xml/device_filter" />
</activity>
```

`res/xml/device_filter.xml` lists the recorded vendor/product ID from the descriptor capture:

```xml
<resources>
    <usb-device vendor-id="6975" product-id="8194" /> <!-- 1b3f:2002, decimal per platform docs -->
</resources>
```

Hand the `CAMERA` decision (declaration, rationale, denial and permanent-denial paths, ledger
row, `<uses-feature>` pairing) to `android-permissions-derive` with the platform-rule evidence
above; apply what it returns. The USB grant is a **separate consent** — see §2 — and does not
appear in the runtime-permission flow.

## 2. USB grant request (targetSdk-correct)

The app owns the grant; the engine's `USBMonitor.register()` is never called (spec §B/§C).

```kotlin
private const val ACTION_USB_PERMISSION = "<applicationId>.USB_PERMISSION"

class UsbGrant(private val context: Context, private val usb: UsbManager) {

    fun request(device: UsbDevice) {
        // Explicit intent (setPackage) + MUTABLE: UsbManager writes EXTRA_DEVICE and
        // EXTRA_PERMISSION_GRANTED into the fill-in intent, so FLAG_IMMUTABLE breaks the flow;
        // an implicit intent with FLAG_MUTABLE throws on targetSdk >= 34 (spec §C, [R12]).
        val intent = Intent(ACTION_USB_PERMISSION).setPackage(context.packageName)
        val pending = PendingIntent.getBroadcast(
            context, 0, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE,
        )
        usb.requestPermission(device, pending)
    }

    fun register(onResult: (UsbDevice?, granted: Boolean) -> Unit): BroadcastReceiver {
        val receiver = object : BroadcastReceiver() {
            override fun onReceive(c: Context, i: Intent) {
                if (i.action != ACTION_USB_PERMISSION) return
                val device = IntentCompat.getParcelableExtra(i, UsbManager.EXTRA_DEVICE, UsbDevice::class.java)
                onResult(device, i.getBooleanExtra(UsbManager.EXTRA_PERMISSION_GRANTED, false))
            }
        }
        // Export state is mandatory on targetSdk >= 34 (spec §C, [R13]). The grant broadcast is
        // delivered through the app's own PendingIntent, so NOT_EXPORTED is the default; if the
        // result never arrives on the target device, switch to RECEIVER_EXPORTED, record the
        // device and build in the engine module, and report it (REQ-6).
        ContextCompat.registerReceiver(
            context, receiver, IntentFilter(ACTION_USB_PERMISSION), ContextCompat.RECEIVER_NOT_EXPORTED,
        )
        return receiver
    }
}
```

Attach/detach are system broadcasts (`ACTION_USB_DEVICE_ATTACHED` / `_DETACHED`), registered the
same way. Verification of this section is **a live preview on the device**, not the absence of a
crash log — the export choice and the mutability are only proven by the grant arriving.

Distinguish `usb.hasPermission(device)` (already granted, skip the dialog) from a fresh request;
"no host support" is `packageManager.hasSystemFeature(PackageManager.FEATURE_USB_HOST) == false`
and is its own state.

## 3. State model and module boundary

One Gradle module (for example `:camera-uvc`) owns every engine type; the app sees an interface
and a sealed state (spec §C/§H):

```kotlin
sealed interface MicroscopeState {
    data object NoHostSupport : MicroscopeState
    data object NoDevice : MicroscopeState
    data class PermissionPending(val device: UsbDevice) : MicroscopeState
    data class PermissionDenied(val device: UsbDevice) : MicroscopeState
    data object CameraPermissionMissing : MicroscopeState   // the CAMERA runtime permission
    data class Streaming(val mode: Mode, val fpsMeasured: Float?) : MicroscopeState
    data class Switching(val from: Mode, val to: Mode) : MicroscopeState  // surfaced wait, spec §G
    data class EngineError(val cause: String) : MicroscopeState
}

interface Microscope {
    val state: StateFlow<MicroscopeState>
    fun attachSurface(surface: SurfaceTexture, width: Int, height: Int)
    fun detachSurface()
    fun requestGrant()
    suspend fun capture(zoom: Float): CaptureResult      // in-memory JPEG, §6
    val buttonEvents: SharedFlow<ButtonEvent>            // §8
    fun close()
}
```

Every state message is a designed UI state with a next action (`strings.xml`, German mirror);
collapsing them into "camera unavailable" makes the app undiagnosable in the field (spec §C).

## 4. Guarded open sequence

Open only when a **permitted device and a live surface** both exist, re-evaluated when either
arrives, guarded against the double-open the two independent callbacks produce (spec §D):

```kotlin
private var permitted: UsbDevice? = null
private var surface: SurfaceTexture? = null
private val opening = AtomicBoolean(false)          // spec §D: both callbacks pass isOpened() otherwise
private var camera: UVCCamera? = null

private fun maybeOpen() {
    val device = permitted ?: return
    val tex = surface ?: return
    if (camera != null || !opening.compareAndSet(false, true)) return
    cameraThread.post {
        try {
            val ctrl = monitor.openDevice(device)   // depends only on the granted permission, never on register()
            val cam = UVCCamera().apply { open(ctrl) }
            val mode = choosePreviewMode(cam.supportedSizeList)   // fast enough to frame by, §7
            cam.setPreviewSize(mode.width, mode.height, UVCCamera.FRAME_FORMAT_MJPEG)
            cam.setPreviewTexture(tex)
            cam.setFrameCallback(frameSink, UVCCamera.PIXEL_FORMAT_NV21) // keeps the raw path alive for §6
            attachEngineCallbacks(cam)              // §5: bound to THIS instance
            cam.startPreview()
            camera = cam
            state.value = MicroscopeState.Streaming(mode, fpsMeasured = null)
        } catch (t: Throwable) {
            state.value = MicroscopeState.EngineError(t.message ?: t.javaClass.simpleName)
        } finally {
            opening.set(false)
        }
    }
}
```

Reading the symptom: `unsupported preview size` reported **while frames render** is the losing
half of a double open, not an unsupported mode — never change the requested resolution in
response (spec §D). Wrapper fallback: the same guard sits in front of `CameraUVC.openCamera`, and
`RenderMode.NORMAL` is set so the raw-frame callback keeps delivering.

## 5. Lifecycle and callback re-attachment

- Tear the stream down when the screen leaves composition (`DisposableEffect` on the preview
  composable → `detachSurface()` → `stopPreview`/`destroy`), re-register on return.
- A transient close during a deliberate reconfiguration (§7) is **not** device loss — do not
  transition to `NoDevice` from inside a mode switch.
- After **every** reopen, re-attach button and status callbacks to the instance the open path
  produced (`attachEngineCallbacks(cam)` above), never to a mutable field a concurrent detach can
  null out — that leaves the hardware shutter dead for the session (spec §D).
- Comment each guard with the constraint it enforces (spec §H); a reader deleting a "redundant"
  guard reintroduces a defect that costs a hardware session.

## 6. Still capture in memory

Never the engine's `captureImage()` (storage permission, DCIM file). One-shot frame callback,
encoded in process (spec §E):

```kotlin
suspend fun capture(zoom: Float): CaptureResult = captureMutex.withLock {   // serialized, §7
    val cam = camera ?: return CaptureResult.Failure.NotStreaming
    val frame = withTimeoutOrNull(FRAME_TIMEOUT_MS) { frameSink.nextFrame() }   // at 4.7 fps a bare wait looks like a hang
        ?: return CaptureResult.Failure.Timeout(FRAME_TIMEOUT_MS)
    val crop = centreCrop(frame.width, frame.height, zoom)          // even edges, §9
    val out = ByteArrayOutputStream()
    YuvImage(frame.nv21, ImageFormat.NV21, frame.width, frame.height, null)
        .compressToJpeg(crop, JPEG_QUALITY, out)
    val bytes = out.toByteArray()
    Log.i(TAG, "capture ${crop.width()}x${crop.height()} ${bytes.size} bytes (frame ${frame.width}x${frame.height})")
    CaptureResult.Success(bytes, crop.width(), crop.height())
}
```

Rules: even crop edges (NV21 chroma is 2×2 subsampled), bounded wait with a **typed** timeout
failure, captured dimensions and byte size **reported** so a silently downgraded still is visible.
Stale frames after a mode change are self-discarding because the engine drops frames whose size
does not match the active request — do not add a second filter for it.

## 7. Resolution strategy and mode switch

Preview at a mode fast enough to frame by (1080p at ~17 fps on the reference body); still at the
device's largest supported mode **only** after its detail has been measured genuine (spec §G —
halve-and-restore residual plus radial power spectrum, calibrated against a deliberately
upscaled control; the reference body passes). Query the largest mode from
`supportedSizeList`, do not hard-code it.

On the libuvc layer a switch is `stopPreview()` → `setPreviewSize(...)` → `startPreview()`
without releasing the device; on the wrapper it is a full close/reopen with a hard-coded 1 s
pause (~4–5 s up and back). Either way (spec §G):

- **serialize** captures (`captureMutex`), **surface** the wait (`Switching` state),
- **bound** the switch with a timeout and **degrade** to the live mode instead of failing,
- **always restore** the preview mode — also on cancellation — and **measure** the switch cost
  on the device instead of assuming it (record it in the run report).

Know that AUSBC negotiates with a hard-coded 10 fps minimum, which can reject an honest low-rate
mode; on the libuvc layer pass the measured minimum instead.

## 8. Body buttons and zoom

Body buttons do not arrive as key events (no HID device on the reference body). The shutter is
the UVC still-image button on the status endpoint, reached through the engine's callback — public
on `UVCCamera`, no reflection (spec §F):

```kotlin
private fun attachEngineCallbacks(cam: UVCCamera) {
    cam.setButtonCallback { button, state ->
        Log.d(TAG, "uvc button=$button state=$state")          // raw log for every event, mapped or not
        when (button to state) {
            MEASURED_SHUTTER_PRESS -> buttonEvents.tryEmit(ButtonEvent.ShutterPressed)   // 1 to 1 on 1b3f:2002
            else -> Unit                                          // unmapped: logged, never guessed
        }
    }
    cam.setStatusCallback { statusClass, event, selector, statusAttribute, data ->
        Log.d(TAG, "uvc status class=$statusClass event=$event selector=$selector attr=$statusAttribute")
    }
}
```

`MEASURED_SHUTTER_PRESS` is `1 to 1` for the reference body; a new body's indices come from the
raw log during its hardware session, never from assumption. Zoom: `cam.checkSupportFlag(UVCCamera.CTRL_ZOOM_ABS)`
decides whether a hardware zoom exists; where it does not (the reference body), on-screen zoom is
a centre crop applied identically to the preview transform (`graphicsLayer` scale on the
`AndroidView`/`TextureView`) and to the capture crop of §6, labelled **digital** in the UI, never
"magnification".

Wrapper fallback only: reach the private button-callback field reflectively, confined to the
engine module, null-guarded, with `-keepclassmembers class com.jiangdg.ausbc.camera.CameraUVC { *; }`
(or the exact field) so R8 does not rename it.

## 9. Unit-testable geometry

Keep crop rounding and encoding free of engine and view types (spec §H):

```kotlin
internal fun centreCrop(width: Int, height: Int, zoom: Float): Rect {
    require(zoom >= 1f)
    val w = ((width / zoom).toInt()) and 1.inv()     // even
    val h = ((height / zoom).toInt()) and 1.inv()
    val left = ((width - w) / 2) and 1.inv()
    val top = ((height - h) / 2) and 1.inv()
    return Rect(left, top, left + w, top + h)
}
```

Unit tests: even edges for odd inputs, `zoom = 1f` returns the full frame, crops stay inside the
frame, and the JPEG encoder round-trips a synthetic NV21 buffer with the reported dimensions.
The hardware-bound parts are covered by the device smoke test and the instrumented lane only.
