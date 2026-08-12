# Scanner pipeline templates

Implementation templates for the path chosen in `access-path-decision.md`. Grounded in
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
- **Capture resolution:** 1280×720 or 1920×1080 where codes are scanned at a distance. Do not
  exceed roughly 2 MP for real-time scanning — beyond that latency is paid for nothing.
- Quiet zone: 4 modules for full-size QR, 2 for Micro QR. 1D quiet zones are multiples of the
  narrow-bar width X and are not comparable with a module count.

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
with an install-time module request per `access-path-decision.md` §5.

## 3. In-app pipeline

Every constraint marked **load-bearing** below fixes a failure that produces no error message.

```kotlin
// LOAD-BEARING: without this, ImageAnalysis is bounded at VGA (640x480) — below the
// budget in §1 for small or distant codes, and the most common reason nothing decodes.
private val resolutionSelector = ResolutionSelector.Builder()
    .setResolutionStrategy(
        ResolutionStrategy(
            Size(1280, 720),
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
@OptIn(ExperimentalGetImage::class)
private fun analyze(imageProxy: ImageProxy) {
    val mediaImage = imageProxy.image
    if (mediaImage == null) {
        imageProxy.close()
        return
    }
    // LOAD-BEARING: a rotation mismatch degrades detection without raising an error.
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

```kotlin
private val options = BarcodeScannerOptions.Builder()
    .setBarcodeFormats(Barcode.FORMAT_QR_CODE)   // faster, and narrows the input surface
    .enableAllPotentialBarcodes()                // optional; see the caveat below
    .setZoomSuggestionOptions(
        // The ZoomCallback receives the suggested ratio and is always invoked on the
        // main thread. Check its exact signature against the version the project
        // resolves before copying this call shape — it is not pinned by this template.
        ZoomSuggestionOptions.Builder(zoomCallback)
            // LOAD-BEARING: without a bound the library may suggest an unbounded ratio.
            .setMaxSupportedZoomRatio(camera.cameraInfo.zoomState.value?.maxZoomRatio ?: 1f)
            .build(),
    )
    .build()
```

The callback body applies the suggested ratio through `CameraControl.setZoomRatio(ratio)` and
nothing else — do not add a re-detection trigger there; the next frame carries it anyway.

- Close the `BarcodeScanner` when the surface is torn down.
- `enableAllPotentialBarcodes()` returns codes that **could not be decoded**: `rawValue` and
  `rawBytes` are null, but a bounding box is present. It exists so the app can guide or zoom
  toward a code it has seen but not read — any UI built on it must distinguish "seen" from "read".
- Results are **not stable frame to frame**; the vendor documentation says so. Define the
  acceptance rule (which value is acted on, and when) and the duplicate-suppression rule, and
  record both at their definition site. No vendor source states a debounce interval.
- Read `rawValue`, or `rawBytes` for binary payloads. `displayValue` may omit information and is
  for display only. Branch on `valueType` for structured payloads — then treat the parsed
  structure as untrusted anyway (`payload-trust.md`).

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
- Every control (torch, cancel, manual entry, gallery) meets 48dp × 48dp.
