# Access-path decision

The first and most consequential decision in a scanning feature: which of the three paths the
app takes. It determines whether the app holds the camera permission at all, and reversing it
late means discarding the pipeline. Grounded in `spec/android/barcode-scanning/` §A; on any
conflict that spec wins.

## Table of contents

- [1. The decision](#1-the-decision)
- [2. Path A — Google code scanner](#2-path-a--google-code-scanner)
- [3. Path B — in-app CameraX plus ML Kit](#3-path-b--in-app-camerax-plus-ml-kit)
- [4. Path C — GMS-free decoder](#4-path-c--gms-free-decoder)
- [5. Model and module supply](#5-model-and-module-supply)
- [6. What to record](#6-what-to-record)

## 1. The decision

Ask in this order and stop at the first path that fits.

1. **Is the interaction a bounded, one-shot "scan a code and come back with a value"?**
   → Path A. This is the default. It needs no camera permission.
2. **Is there a named capability Path A cannot serve?** A custom or embedded viewfinder,
   continuous scanning, an overlay drawn on the live frame, scanning combined with another
   camera feature, or an operational requirement to work where the scanner module cannot be
   downloaded → Path B.
3. **Does the target set genuinely include devices without Play services?** → Path C, added as
   an explicitly bounded second code path alongside A or B, never as a silent fallback.

Reasons that do **not** justify leaving Path A: wanting to restyle the scanner later, wanting
the app to "own" the camera, or an assumption that an in-app scanner is faster or more accurate.
Two decoders reached by accident produce two different accuracy profiles for the same feature.

| | Path A — code scanner | Path B — in-app | Path C — GMS-free |
|---|---|---|---|
| Camera permission | **none** | required | required |
| UI control | Play-services UI | full | full |
| Works without Play services | no | model-supply dependent | yes |
| Continuous scanning | no | yes | yes |
| Overlay on live frame | no | yes | yes |
| Maintenance surface | one call site | full pipeline | full pipeline |

All three Google artifacts state **API 23** as the floor. Secondary summaries circulating an
API-21 figure are wrong; do not carry it.

## 2. Path A — Google code scanner

Scans without the app requesting the camera permission, because camera access happens inside
Google Play services, which returns only the result. Image processing is stated to occur on the
device.

- Artifact: `com.google.android.gms:play-services-code-scanner`.
- It is an **unbundled** library that must be downloaded before use. Pre-request it or handle
  the not-yet-available state — see §5.
- Two options are **off by default** and both should be enabled: `allowManualInput()` (the
  accessibility fallback, already required by the spec's §H) and `enableAutoZoom()`.
- Restrict the formats to what the feature consumes.
- **Do not declare `CAMERA` in the manifest on this path.** Declaring it forfeits the property
  that justified the choice and contradicts `spec/android/security/` §E.
- Handle: user cancelled, module unavailable, and a successful result. Do not treat cancellation
  as an error state.

Caveat worth stating to the operator rather than to the user: because camera access happens
under Play services rather than the app's own permission grant, the app does not raise the
camera privacy indicator under its own identity. This follows from the delegation model and
**must not** be presented to a user as a privacy guarantee.

## 3. Path B — in-app CameraX plus ML Kit

Chosen only for a recorded reason from §1. Costs a permission prompt, a privacy indicator, and
a pipeline to maintain — in exchange for full control of the surface.

- Detector artifact: `com.google.mlkit:barcode-scanning` (bundled model) **or**
  `com.google.android.gms:play-services-mlkit-barcode-scanning` (Play-services model). See §5.
- Camera artifacts: `androidx.camera:camera-core`, `-camera2`, `-lifecycle`, plus `-view` or
  `-compose` for the viewfinder, and `-mlkit-vision` when using `MlKitAnalyzer`.
- Manifest: declare `CAMERA`, and request it **in context** at the moment the user asks to
  scan, with a rationale gated on `shouldShowRequestPermissionRationale`. Handle denial and
  permanent denial as distinct states — a permanently denied permission must be explained, not
  re-requested into a dialog the system will no longer show.
- The pipeline itself is in `scanner-pipeline.md`. The single most important line in it is the
  explicit `ResolutionSelector`.

## 4. Path C — GMS-free decoder

- Use maintained `com.google.zxing:core`, driven from the project's own CameraX pipeline.
- **Do not** reach for `com.journeyapps:zxing-android-embedded` as a new dependency without
  recording it as a known-stale choice: its last release is from October 2021 and it bundles an
  outdated ZXing core.
- Be honest about capability: on clean single codes every engine performs comparably; the gap
  appears on adversarial imagery (blurred, damaged, dense, multi-code). "Adequate for clean
  codes, weaker on damaged ones" is the accurate statement, not "the same".
- Relevant decode hints: `POSSIBLE_FORMATS` to restrict symbologies, `TRY_HARDER` for accuracy
  over speed, `ALSO_INVERTED` where light-on-dark codes must be read.

## 5. Model and module supply

An explicit decision, recorded — a first-run scan that silently fails is this decision made by
accident.

| Supply | Size impact | Availability |
|---|---|---|
| Bundled model (`com.google.mlkit:barcode-scanning`) | about 2.4 MB | immediately, no download |
| Play-services model (`…:play-services-mlkit-barcode-scanning`) | about 200 KB | after module download |
| Code scanner (`…:play-services-code-scanner`) | unbundled | after module download |

For any downloaded module: request it at install time via the
`com.google.mlkit.vision.DEPENDENCIES` manifest metadata, or explicitly through
`ModuleInstallClient`. Until the download completes, **inference requests fail**. The
not-yet-available case is a state the UI must handle, never a silent no-op.

Which options exist at all is version-bound — auto-zoom and `enableAllPotentialBarcodes` arrived
in specific releases. Check an option against the version the project actually resolves rather
than against a dated observation.

## 6. What to record

Persist to the resume state and state in the run report:

- The chosen path and the **named reason** (for Path B, the capability Path A could not serve).
- The model/module supply choice and how the pending state is handled.
- For Path C: which devices justify it, and where the second code path begins and ends.
- The resolved versions of every added artifact.
