# Scanner pipeline templates

Implementation templates for the path chosen in SKILL.md step 1. Grounded in
`spec/android/barcode-scanning/` §B–§E; on any conflict that spec wins. Fill in the feature
name, state shape, and destination; keep every constraint below intact — each one is the fix
for a specific, silent failure mode.

## Table of contents

- [1. The decodability budget](#1-the-decodability-budget)
- [2. Code-scanner call site](#2-code-scanner-call-site)
- [3. In-app pipeline](#3-in-app-pipeline)
- [4. Detector configuration](#4-detector-configuration)
- [5. Zoom, torch, focus](#5-zoom-torch-focus)
- [6. The scan surface](#6-the-scan-surface)

## 1. The decodability budget

Compute this before choosing a resolution — it is what makes the difference between a scanner
and a viewfinder that never fires.

- **The hard rule:** the smallest meaningful unit of the barcode must be at least **2 pixels
  wide**, and for 2D codes 2 pixels tall.
- Worked consequences: an EAN-13 image should be at least **190 px wide**; a PDF417 ideally at
  least **1156 px wide**; a QR symbol needs twice its module count per side — at version 40's
  177×177 modules that is 354 px across the symbol alone, before the quiet zone.
- **Capture resolution is computed, not copied.** Work it out from the symbology, the physical
  code size, and the intended scanning distance, and write the computation into the run report
  and next to the selector in code:
  1. Modules per side of the largest symbol the feature must read (QR version 40 = 177; an
     EAN-13 spans 95 module widths; a compact QR version 10 = 57).
  2. Fraction of the frame width the code occupies at the intended distance (a phone held at
     arm's length over a 3 cm label typically frames it at roughly 15–25 % of the width; measure
     it on the reference device rather than assuming).
  3. Required width = `modules × 2 px ÷ frame-fraction`, then round up to the next standard
     capture size and add the quiet zone.
  Worked example: a QR version 10 (57 modules) at 20 % of the frame → `57 × 2 ÷ 0.20 = 570 px`
  → 1280×720 suffices. Version 40 at the same distance → `177 × 2 ÷ 0.20 = 1770 px` →
  1920×1080. Where the result exceeds roughly 2 MP for real-time scanning, that is a signal to
  change the distance, zoom, or symbology — beyond that, latency is paid for nothing.
- Quiet zone: 4 modules for full-size QR, 2 for Micro QR. 1D quiet zones are multiples of the
  narrow-bar width X and are not comparable with a module count.
- **Contrast is a gap, not a number.** ISO/IEC 18004 does not own contrast grading — ISO/IEC
  15415 does — and both are paywalled, so no verified threshold exists here. When a
  low-contrast fixture or an acceptance rule needs one, report the gap (REQ-6) instead of
  quoting a figure. The same applies to a scan-latency budget or a detection-rate number: no
  camera spec exists and `spec/android/perceived-performance/` fixes startup and frame budgets
  only — name the gap in the report.

## 2. Code-scanner call site

The whole of Path A. Note both options being enabled — each is off by default.

```kotlin
private val scannerOptions = GmsBarcodeScannerOptions.Builder()
    .setBarcodeFormats(Barcode.FORMAT_QR_CODE)   // only what the feature consumes
    .allowManualInput()                          // off by default; the accessibility fallback
    .enableAutoZoom()                            // off by default
    .build()

fun startScan(onResult: (ScanOutcome) -> Unit) {
    GmsBarcodeScanning.getClient(context, scannerOptions)
        .startScan()
        .addOnSuccessListener { barcode ->
            val raw = barcode.rawValue          // never displayValue
            onResult(if (raw == null) ScanOutcome.Undecodable else ScanOutcome.Decoded(raw))
        }
        .addOnCanceledListener { onResult(ScanOutcome.Cancelled) }   // not an error state
        .addOnFailureListener { onResult(ScanOutcome.Unavailable(it)) }
}
```

Handle `Unavailable` as the module-not-yet-downloaded case with a real UI state, and pair it
with an install-time module request (`com.google.mlkit.vision.DEPENDENCIES` metadata or
`ModuleInstallClient`; SKILL.md step 2).

## 3. In-app pipeline

Every constraint marked **load-bearing** below fixes a failure that produces no error message.

```kotlin
// LOAD-BEARING: without this, ImageAnalysis is bounded at VGA (640x480) — below the
// budget in §1 for small or distant codes, and the most common reason nothing decodes.
// The target size is COMPUTED from §1 — replace the inputs with the feature's own and keep
// the derivation next to the value so a later reader can re-check it:
//   largest symbol: QR version 10 = 57 modules per side
//   frame fraction at intended distance (measured on <reference device>): 0.20
//   required width = 57 * 2 px / 0.20 = 570 px  -> next standard size 1280x720
private const val MODULES_PER_SIDE = 57
private const val FRAME_FRACTION = 0.20f
private val requiredWidthPx = (MODULES_PER_SIDE * 2 / FRAME_FRACTION).toInt()   // 570
private val analysisTarget: Size = when {
    requiredWidthPx <= 1280 -> Size(1280, 720)
    requiredWidthPx <= 1920 -> Size(1920, 1080)
    else -> error("budget exceeds ~2 MP real-time ceiling — change distance, zoom, or symbology")
}

private val resolutionSelector = ResolutionSelector.Builder()
    .setResolutionStrategy(
        ResolutionStrategy(
            analysisTarget,
            ResolutionStrategy.FALLBACK_RULE_CLOSEST_HIGHER_THEN_LOWER,
        ),
    )
    .build()

private val imageAnalysis = ImageAnalysis.Builder()
    .setResolutionSelector(resolutionSelector)
    // LOAD-BEARING: a slow decode must drop frames, not queue them.
    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
    // Output format stays at the YUV_420_888 default: ML Kit consumes it directly,
    // and RGBA_8888 makes CameraX convert every frame for nothing.
    .build()
```

Do **not** use the deprecated `setTargetResolution`/`setTargetAspectRatio` pair, and never set
a target aspect ratio and a target resolution on the same use case — that throws
`IllegalArgumentException` at build time.

The analyzer, with the two mandatory disciplines:

```kotlin
// LOAD-BEARING on a rotating surface: keep targetRotation current so rotationDegrees below
// stays correct. Register at bind time; unregister on teardown. (Not needed when the activity
// is locked to one orientation — say so in the run report if you rely on that.)
private val orientationListener = object : OrientationEventListener(context) {
    override fun onOrientationChanged(orientation: Int) {
        if (orientation == ORIENTATION_UNKNOWN) return
        val rotation = when (orientation) {
            in 45 until 135 -> Surface.ROTATION_270
            in 135 until 225 -> Surface.ROTATION_180
            in 225 until 315 -> Surface.ROTATION_90
            else -> Surface.ROTATION_0
        }
        imageAnalysis.targetRotation = rotation
        // Preview's targetRotation follows the display when hosted by PreviewView/CameraXViewfinder.
    }
}
// Alternative for a surface bound to the display rather than the sensor orientation:
// DisplayManager.registerDisplayListener { display -> imageAnalysis.targetRotation = display.rotation }.

@OptIn(ExperimentalGetImage::class)
private fun analyze(imageProxy: ImageProxy) {
    val mediaImage = imageProxy.image
    if (mediaImage == null) {
        imageProxy.close()
        return
    }
    // LOAD-BEARING: a rotation mismatch degrades detection without raising an error.
    // rotationDegrees is derived from targetRotation — hence the listener above.
    val input = InputImage.fromMediaImage(mediaImage, imageProxy.imageInfo.rotationDegrees)

    scanner.process(input)
        .addOnSuccessListener { barcodes -> onBarcodes(barcodes) }
        .addOnFailureListener { onDetectionError(it) }
        // LOAD-BEARING: close on EVERY path. An unclosed proxy freezes the viewfinder
        // (it looks like a hang, not a leak). Never close the wrapped Media.Image —
        // that breaks CameraX's image-sharing mechanism.
        .addOnCompleteListener { imageProxy.close() }
}
```

Binding: one `Preview` and one `ImageAnalysis`. A combination that works at low resolution but
not at high is a real constraint, not a device quirk.

**Coordinates.** `boundingBox`/`cornerPoints` are in analysis-image space, and corner points are
explicitly *not necessarily a rectangle* because of perspective distortion — an overlay drawn
from a bounding box alone will visibly lie. Map through `MlKitAnalyzer` with
`COORDINATE_SYSTEM_VIEW_REFERENCED` via `CameraController`, or the `CoordinateTransformer`
supplied by `CameraXViewfinder` on the Compose path. Never hand-compute the transform.

Keep the analyzer off the main thread and inside the frame interval — the documented target is
under 32 ms at 30 fps.

## 4. Detector configuration

The options must be **built after `bindToLifecycle`**, not as a property initializer: the max
zoom ratio comes from the bound `Camera`, and a property initialized before binding would fall
back to `1f` and silently disable the zoom suggestion the prose below calls load-bearing.

```kotlin
// Called once, AFTER cameraProvider.bindToLifecycle(...) returned the Camera.
private fun buildScanner(camera: Camera): BarcodeScanner {
    val zoomCallback = ZoomSuggestionOptions.ZoomCallback { ratio ->
        // Always invoked on the main thread. Apply and report success.
        camera.cameraControl.setZoomRatio(ratio)
        true
    }
    val options = BarcodeScannerOptions.Builder()
        .setBarcodeFormats(Barcode.FORMAT_QR_CODE)   // faster, and narrows the input surface
        // .enableAllPotentialBarcodes()             // ONLY when small/distant codes are expected
        //                                           // and the UI guides toward a seen-not-read
        //                                           // code; off by default — see the caveat below
        .setZoomSuggestionOptions(
            ZoomSuggestionOptions.Builder(zoomCallback)
                // LOAD-BEARING: without a bound the library may suggest an unbounded
                // ratio. Read the real maximum from the bound camera — never a literal.
                .setMaxSupportedZoomRatio(
                    camera.cameraInfo.zoomState.value?.maxZoomRatio
                        ?: error("zoomState unavailable — bind the camera before building options"),
                )
                .build(),
        )
        .build()
    return BarcodeScanning.getClient(options)
}
```

Check the `ZoomCallback` signature against the version the project resolves before copying this
shape — it is not pinned by this template.

The callback body applies the suggested ratio through `CameraControl.setZoomRatio(ratio)` and
nothing else — do not add a re-detection trigger there; the next frame carries it anyway.

- Close the `BarcodeScanner` when the surface is torn down.
- `enableAllPotentialBarcodes()` returns codes that **could not be decoded**: `rawValue` and
  `rawBytes` are null, but a bounding box is present. It exists so the app can guide or zoom
  toward a code it has seen but not read — any UI built on it must distinguish "seen" from "read".
  Enable it **only** when small or distant codes are expected and the surface actually uses the
  seen-not-read state (a "move closer" hint, an auto-zoom); leave it off for a bounded near-field
  scan, where it adds work and a state nothing consumes.
- Results are **not stable frame to frame**; the vendor documentation says so. Define the
  acceptance rule (which value is acted on, and when) and the duplicate-suppression rule, and
  record both at their definition site. No vendor source states a debounce interval.
- Read `rawValue`, or `rawBytes` for binary payloads. `displayValue` may omit information and is
  for display only. Branch on `valueType` for structured payloads — then treat the parsed
  structure as untrusted anyway (SKILL.md step 6).

**Documented exclusions — never build a required capability on these.** They fail silently:
ECI-mode QR codes, FNC2/FNC3/FNC4 encodings, single-character 1D codes, ITF under six characters,
Micro QR, rMQR, Structured Append, more than 10 barcodes per call, and a Data Matrix that does
not intersect the image centre (only one Data Matrix per image is recognizable).

## 5. Zoom, torch, focus

- **Torch:** gate every affordance on `CameraInfo.hasFlashUnit()`. Without a torch,
  `enableTorch()` completes immediately with a failed result and the state stays `TorchState.OFF`
  — an ungated button is a control that does nothing. Do **not** auto-enable it: no vendor source
  defines a threshold, so an automatic trigger is an invented heuristic.
- **Zoom:** apply ML Kit's suggested ratio through `CameraControl.setZoomRatio`; the callback
  always arrives on the main thread.
- **Focus:** offer tap-to-focus via `startFocusAndMetering` built from
  `previewView.meteringPointFactory`. The action auto-cancels after 5 seconds unless overridden,
  and not every device supports all metering modes or multiple regions.

## 6. The scan surface

The surrounding screen follows `android-compose-ui` conventions. Scanner-specific rules:

- Host the viewfinder with `CameraXViewfinder` (`androidx.camera:camera-compose`) on a Compose
  surface rather than wrapping `PreviewView` in an `AndroidView`; record the CameraX version the
  choice was made against. On a View surface, `PreviewView` defaults to `PERFORMANCE` mode and
  `FILL_CENTER` scale type — a cropping scale type must not hide part of the frame the user is
  being asked to aim with.
- A framing affordance may communicate where to aim, but must not imply a crop the detector does
  not apply. The detector sees the analysis frame, not the reticle.
- Confirm success through **more than one channel**, never audio alone — a deaf user gets nothing
  from a beep and neither does a silenced device. Haptics are the documented pairing:
  `HapticFeedbackConstants.CONFIRM` / `REJECT` via `View.performHapticFeedback` (no `VIBRATE`
  permission needed), or `LocalHapticFeedback` in Compose.
- The no-detection state is a designed state with a next action — torch, manual entry, an
  explanation — not an indefinite viewfinder. Usability research puts patience at roughly 15
  seconds.
- Wait indication and message surfaces follow `spec/android/ui-components/` §A; error wording
  follows `spec/android/app-design-navigation/` §F. Do not invent scanner-specific indicators.
- **Announcements (spec §H)** — three constructions, one per event, none of them
  `announceForAccessibility`/`TYPE_ANNOUNCEMENT` (deprecated in Android 16):
  - result → **polite** live region: `Modifier.semantics { liveRegion = LiveRegionMode.Polite }`
    (View: `setAccessibilityLiveRegion(ACCESSIBILITY_LIVE_REGION_POLITE)`); never assertive;
  - surface switch (viewfinder → confirmation / manual entry) → pane title:
    `Modifier.semantics { paneTitle = stringResource(...) }` (View: `accessibilityPaneTitle`);
  - failed or rejected scan → `Modifier.semantics { error(message) }`, which emits
    `CONTENT_CHANGE_TYPE_ERROR` (View: `setError`/`setStateDescription` plus the error event).
- Every control (torch, cancel, manual entry, gallery) meets 48dp × 48dp.
