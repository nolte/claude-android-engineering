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
- [7. Data Safety handoff and native-library check](#7-data-safety-handoff-and-native-library-check)

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
- It is an **unbundled** library that must be downloaded before use. Pre-request it **and**
  handle the not-yet-available state — both, not either. Pre-requesting narrows the window; it
  does not close it. See §5.
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
- Manifest and permission handling: this path needs `CAMERA`. The declaration, the ledger row,
  the `<uses-feature>` pairing, and the denial and permanent-denial paths belong to
  `android-permissions-derive` per `spec/android/permissions/` — hand them over rather than
  deciding them here. What stays here is the trigger point: the request happens **in context**,
  at the moment the user asks to scan, and the manual-entry fallback is what the degraded path
  degrades to.
- The pipeline itself is SKILL.md step 3 (and its pipeline reference). The single most important
  line in it is the explicit, computed `ResolutionSelector`.

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
- Manifest and permission handling: like Path B, this path drives the app's own camera and
  therefore needs `CAMERA` — declared and handed to `android-permissions-derive` exactly as in
  §3, with the same in-context trigger and manual-entry degradation. Only Path A is
  permission-free.

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
`ModuleInstallClient`. Until the download completes, **inference requests fail**. Pre-requesting
is required *and* so is handling the not-yet-available case as a real UI state — never a silent
no-op. The two are not alternatives: a pre-request that has not finished still leaves the user
on a screen that must say something.

Which options exist at all is version-bound — auto-zoom and `enableAllPotentialBarcodes` arrived
in specific releases. Check an option against the version the project actually resolves rather
than against a dated observation.

## 6. What to record

Persist to the resume state and state in the run report:

- The chosen path and the **named reason** (for Path B, the capability Path A could not serve).
- The model/module supply choice and how the pending state is handled.
- For Path C: which devices justify it, and where the second code path begins and ends.
- The resolved versions of every added artifact, and — for the bundled ML Kit model — the
  16 KB page-size check result (`spec/android/release-readiness/` §D).
- **The payload/frame data flow** (on-device only, or transmitted to a backend or third-party
  SDK) and, wherever it leaves the device, the store-side Data Safety declaration obligation
  handed to the operator. Never an asserted exemption for on-device processing (spec §G). See §7.

## 7. Data Safety handoff and native-library check

**Data Safety (spec §G).** Establish, and record in the run report, what happens to the decoded
payload and to the camera frame: on-device only, or transmitted to a backend or a third-party
SDK (analytics, crash reporting with breadcrumbs, a lookup service). Wherever payload or frame
**leaves the device**, record the store-side Data Safety declaration obligation and hand it to
the operator — the same handoff category `android-permissions-derive` uses for its §G
obligations: discovery is this skill's, filing is the operator's, and no skill edits the Play
Console or the Data Safety questionnaire. Never assert an exemption for on-device-only
processing; no source states one (spec §G / §Open Questions) — say "no declaration obligation
was found" at most, never "none applies". `spec/android/security/` §E owns the general
obligation.

**16 KB page size (`spec/android/release-readiness/` §D).** The bundled ML Kit model artifact
(`com.google.mlkit:barcode-scanning`) ships native libraries inside the APK — the Play-services
model, the code scanner, and pure-JVM ZXing core do not. Verify the resolved version's `.so`
files are 16 KB-aligned (`zipalign -c -P 16 -v 4 <apk>`, or the APK Analyzer check) and report a
non-aligned artifact as a finding with the version that fixes it — never bump silently.
