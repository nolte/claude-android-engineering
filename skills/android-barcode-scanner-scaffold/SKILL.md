---
name: android-barcode-scanner-scaffold
description: "Builds a QR/barcode scanning surface into an existing Android app, grounded in spec/android/barcode-scanning/ — picks the access path on evidence (the Play-services code scanner needs no camera permission at all; an in-app CameraX plus ML Kit scanner is justified only by a named capability), configures the camera pipeline so detection can actually succeed (explicit ResolutionSelector against the 2-pixels-per-module budget, KEEP_ONLY_LATEST, closed ImageProxy, correct rotation), restricts formats, and puts every decoded payload behind a trust boundary before anything acts on it. Also generates the code-display side (quiet zone, error-correction level, whole-pixel module rendering). Invoke when the user asks to add barcode or QR scanning, build a scanner screen, read a code with the camera, or render a QR code. Also handles equivalent German-language requests. Supports resume on re-invocation."
tags: [ui, scaffolding, privacy]
phase: build
summary: "Builds a QR/barcode scanner into an existing app — access-path decision, a camera pipeline that can actually decode, and a trust boundary on every decoded payload."
summary_de: "Baut einen QR-/Barcode-Scanner in eine bestehende App — Wahl des Zugangswegs, eine tatsächlich dekodierfähige Kamerapipeline und eine Vertrauensgrenze für jede Nutzlast."
use_when:
  - "you want to add QR or barcode scanning to an Android app"
  - "you want a scanner screen that works on small or distant codes"
  - "you want scanned payloads validated before the app acts on them"
  - "you want to render a QR code the app's own scanners can read"
resumable: true
---

# Android Barcode Scanner Scaffold

Builds a scanning surface into an app that already exists. The authoritative rules live in
`spec/android/barcode-scanning/`; this skill operationalizes them and never restates or
contradicts them. On any conflict the spec wins — report the gap and propose a spec change
rather than deciding silently (REQ-6).

Two properties make this capability different from ordinary screen authoring, and both are
gates in the procedure below:

- **A scanner is an input channel from a stranger.** Whoever printed the sticker chooses the
  bytes. The decode is the start of the work, not the end of it (§F of the spec).
- **A scanner that never fires produces no error to debug.** Whether a code is decodable is
  decided by pixels per module, quiet zone, and focus — and CameraX's analysis default is
  bounded at VGA, which is below the budget for small or distant codes (§B/§C).

## Why this is a skill, not an agent

- **The access-path decision is an operator gate.** Choosing the no-permission code scanner
  over an in-app scanner changes the app's permission surface; it is confirmed, not inferred.
- **Persistent code output in the main context.** Generated Kotlin, manifest entries, Gradle
  coordinates, and strings land in the working tree and flow back for review.
- **Interactive and resumable.** The run spans several approval gates (path, dependencies,
  scan surface, trust boundary, verification); `resumable: true` carries an interrupted run.
- Counter-dimension considered: the payload-validation design would suit a narrow reviewing
  agent, but it is inseparable from the code being written here, so per
  `spec/claude/skill-vs-agent/` §Primary decision rule the skill wins.

## Boundary vs the neighbouring artefacts

This skill **adds a scanning capability**. It is not the general screen author: the surrounding
screen, its theming, adaptivity, and previews belong to `android-compose-ui`, and this skill
hands off to it rather than re-implementing screen authoring. Reviewing existing UI is the
read-only `android-ux-reviewer` agent. A red build or a device that will not deliver frames is
`android-debugging`. Camera work that is not scanning — photo capture, video, gallery — has no
spec yet; report the gap instead of inventing conventions.

## User-language policy

Detect the user's language and respond in it (German for this operator). Generated artifacts
stay canonical: Kotlin, resource keys, and code comments in English; user-visible copy is
externalized to `strings.xml` with a German translation per `spec/android/localization/` §A —
scanner prompts, error states, and the confirmation surface included.

## Preconditions

Before writing anything:

- Confirm the working directory is a git repository and locate the target module. This skill
  authors *into* an app scaffolded per `spec/android/project-structure/`; if no `:app` module
  exists, stop and route to `android-project-scaffold` first.
- Read `references/access-path-decision.md` in full before proposing anything — the path
  decision determines every later step, and reversing it late means discarding the pipeline.
- Confirm the module's `minSdk` is **23 or higher**. All three Google artifacts state that
  floor; below it, stop and report rather than scaffolding something that cannot resolve.
- Check for uncommitted changes in the paths to be touched (feature package, `AndroidManifest.xml`,
  version catalog, `strings.xml`). If dirty, report and ask whether to stash, commit, or abort —
  never overwrite unconfirmed work (REQ-8).

## Authoring procedure

### 1. Decide the access path — gate

Walk the decision in `references/access-path-decision.md` with the operator and record the
answer plus its reason. The default is the **Google code scanner**: it scans without the app
requesting the camera permission at all, because camera access happens inside Play services.

An **in-app CameraX plus ML Kit** scanner requires a named capability the code scanner cannot
serve — a custom or embedded viewfinder, continuous scanning, an overlay on the live frame,
scanning combined with another camera feature, or an operational need to work where the
scanner module cannot be downloaded. "We might want to style it later" is not such a reason.

A **GMS-free decoder** is added only when the target set genuinely includes devices without
Play services, and then as an explicitly bounded second code path — never a silent fallback.

Gate: confirm the path and its reason before touching dependencies.

### 2. Wire dependencies, manifest, and module supply

Add coordinates through the version catalog (never a literal in a build script). On the in-app
path, decide the ML Kit model supply explicitly — the bundled model ships in the APK and works
immediately; the Play-services model is far smaller but must be downloaded, and **inference
requests fail until that download completes**. Pre-request the module (install-time metadata or
`ModuleInstallClient`) and handle the not-yet-available case as a real state.

Declare the camera permission **only** on the in-app path. On the code-scanner path, declaring
it forfeits the entire benefit that justified the choice.

Gate: confirm the dependency set and the manifest diff.

### 3. Build the pipeline for the chosen path

Read `references/scanner-pipeline.md` when writing code.

**Code-scanner path:** a small call site — options with the formats restricted, `allowManualInput()`
and `enableAutoZoom()` enabled (both are off by default), the result handled, the module-missing
and user-cancelled cases handled.

**In-app path:** `Preview` plus one `ImageAnalysis`, and every one of these is load-bearing —
an explicit `ResolutionSelector` sized against the pixel budget (never the VGA default),
`STRATEGY_KEEP_ONLY_LATEST`, `close()` on the `ImageProxy` on every path including the error
path, `rotationDegrees` passed into the `InputImage`, the `YUV_420_888` default kept, and
detection coordinates mapped through `MlKitAnalyzer` or the viewfinder's `CoordinateTransformer`
rather than by hand. Wire ML Kit's zoom suggestion — bounded by the camera's real maximum ratio
— instead of inventing a zoom heuristic.

Gate: confirm before writing.

### 4. Configure the detector

Restrict the accepted formats to exactly what the feature consumes: it is faster, and an
unrestricted scanner also accepts symbologies the feature has no meaning for. Act on `rawValue`
(or `rawBytes` for binary), never on `displayValue`, which may omit information. Branch on
`valueType` for structured payloads. Define the acceptance rule for a continuous scanner —
results can differ from frame to frame, so "the first frame that decodes" is not a rule — and
record the duplicate-suppression rule at its definition site.

### 5. Build the scan surface

Hand the surrounding screen to `android-compose-ui` conventions. This skill fixes the
scanner-specific parts: a framing affordance that does not imply a crop the detector does not
apply, a torch control gated on `hasFlashUnit()`, a manual-entry path, the no-detection state
as a designed state with a next action, and success confirmed through **more than one channel**
— never audio alone, with haptics as the documented pairing.

### 6. Put the payload behind the trust boundary — gate

Read `references/payload-trust.md` and apply it before any code path acts on a decoded value.
The decoded destination is shown and an explicit user action is required; nothing auto-dials,
auto-joins a network, auto-sends, or auto-submits. URLs are scheme-allowlisted and host-checked;
no scanned string reaches `Intent.parseUri`, `startActivity` as an intent URI, a WebView, a
query interpreter, or an unbounded field.

Gate: confirm the validation rules and the rejection behaviour with the operator — this is the
step where a scanner becomes safe or does not.

### 7. Accessibility pass

A camera-based flow excludes anyone who cannot aim a camera, so the non-camera path from step 5
is an accessibility obligation, not a convenience. Announce results through a polite live region
— **not** `announceForAccessibility`, deprecated in Android 16 — keep every scanner control at
48dp, and keep the decoded content on the confirmation surface readable by a screen reader,
since that is where the user makes the trust decision.

### 8. Verify and build green

Generate tests against real code fixtures including the adversarial cases (damaged, low-contrast,
angled, at the edge of the pixel budget) and the rejection payloads from step 6, plus the
permission-denied and permanently-denied paths. Use the emulator's virtual-scene image import for
the mechanical layer, and state plainly that focus, low light, distance, and torch behaviour are
**not** evidenced by an emulator run. Finish with `./gradlew build`; report a red state rather
than leaving it silent (REQ-1, REQ-7).

## Generating codes

When the request is to *display* a code rather than read one, read `references/payload-trust.md`
§"Generating a readable code". The load-bearing trap: encoding UTF-8 correctly requires an ECI
designator, and **ML Kit does not recognize ECI-mode QR codes at all** — so a code encoded
"properly" for non-Latin text is unreadable by the scanner this skill just built. Restrict the
payload and record the restriction, or record the conflict; never decide it silently.

## Reference files

- Read `references/access-path-decision.md` before step 1 — the three-path decision, what each
  path costs, and the dependency/manifest recipe per path.
- Read `references/scanner-pipeline.md` in step 3 — the CameraX plus ML Kit templates and the
  code-scanner call site.
- Read `references/payload-trust.md` in step 6 — payload classes, validation rules, rejection
  behaviour, and the code-generation rules.

## Resumability

Per `spec/claude/resumable-work/`, this skill is `resumable: true`. State persists to
`.resume/android-barcode-scanner-scaffold/<run-id>.yml` after every approval gate (path,
dependencies, pipeline, trust boundary, verification) and after each named step boundary. On
re-invocation, scan that directory for `status: in_progress` runs whose `inputs:` snapshot
(target module + access path) matches; when one matches, prompt
`Resume run <run_id> from phase <phase> (last checkpoint <last_checkpoint_at>)? [resume / start-new / discard]`.
Never re-ask a decision already in `decisions:` — the access path in particular. The envelope
keys and fail-closed semantics are owned by the spec and are not duplicated here.

## Hard rules

- **Never** request or declare the `CAMERA` permission on the code-scanner path — that is the
  path's defining property, and requesting it anyway contradicts `spec/android/security/` §E.
- **Never** accept CameraX's default `ImageAnalysis` resolution. It is bounded at VGA
  (640×480); against the 2-pixels-per-module budget that is the single most common reason a
  viewfinder never fires on a small or distant code.
- **Never** act on a decoded payload without showing the destination and taking an explicit
  user action — no `ACTION_CALL`, no auto-join, no auto-submit. `ACTION_DIAL` is the only
  conformant way to reach a `tel:` payload.
- **Never** pass a scanned string to `Intent.parseUri` or `startActivity` as an intent URI, or
  interpolate it into SQL, a shell, HTML, a WebView `loadUrl`, or an unencoded URL component.
- **Never** leave an `ImageProxy` unclosed, and never call `close()` on the wrapped
  `Media.Image` — the first freezes the viewfinder, the second breaks CameraX's image sharing.
- **Never** build a required capability on a documented ML Kit exclusion: ECI-mode QR, FNC2/3/4,
  single-character 1D, sub-six-character ITF, Micro QR, rMQR, Structured Append, more than 10
  codes per call, or an off-centre Data Matrix.
- **Never** report a scan claim about focus, low light, distance, or torch from an emulator run.
- **Always** offer a path to the same outcome that does not require aiming a camera.
- **Always** end with `./gradlew build` and report a red state rather than leaving it silent.
- When `spec/android/barcode-scanning/` disagrees with this skill, the spec wins — report the
  gap and propose a spec change (REQ-6).

## German trigger phrases

Also invoke on equivalent German requests, and reply to the operator in German (instructions in
this file stay English):

- "Füge einen QR-Scanner hinzu" / "Barcode-Scanner einbauen"
- "Einen Scan-Screen bauen"
- "Code mit der Kamera einlesen"
- "Der Scanner erkennt nichts" (route to step 3 — usually the resolution default)
- "QR-Code anzeigen / rendern"

## Gotchas

Concrete corrections to non-obvious facts the executing agent would otherwise get wrong:

- **The code scanner needing no camera permission is not a styling trade-off.** It is a
  permission-surface decision. Reaching for the in-app path for cosmetic reasons buys a
  permission prompt, a privacy indicator, and a pipeline that must be maintained.
- **`displayValue` is not `rawValue` with nicer formatting.** It may omit information encoded
  in the barcode. Anything the app acts on reads `rawValue`.
- **Detection results are not stable frame to frame.** The vendor documentation says so
  explicitly. A continuous scanner without an acceptance rule will act on a value it would not
  have produced one frame later.
- **`enableAllPotentialBarcodes()` returns codes it could not decode** — `rawValue` is null but
  a bounding box exists. It is for guiding or zooming toward a code, and any UI built on it must
  distinguish "seen" from "read".
- **A quiet zone is a property of the symbology, not a margin taste.** Four modules for
  full-size QR, two for Micro QR; 1D quiet zones are multiples of the narrow-bar width X and are
  not numerically comparable with a module count.
- **The "code size ≈ distance ÷ 10" rule and the 2 cm minimum are folklore.** No normative
  source states them. Derive physical size from the 2-pixels-per-module rule and the target
  device's capture resolution instead.
- **A `WIFI:` payload carries the network password in plaintext inside the code** and is a
  de-facto ZXing convention, not a standard. Where the project controls provisioning, Wi-Fi Easy
  Connect (DPP) is Android's own cryptographically secured QR path.
- **`zxing-android-embedded` looks like the obvious ZXing wrapper and is stale** — its last
  release is from 2021 and it bundles an outdated ZXing core. Drive maintained
  `com.google.zxing:core` from the project's own CameraX pipeline instead.
