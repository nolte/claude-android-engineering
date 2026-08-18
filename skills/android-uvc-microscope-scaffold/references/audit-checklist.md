# Audit checklist — `audit` operation

A read-only conformance report of an existing UVC integration against
`spec/android/uvc-microscope/`. The operation writes nothing; every finding names the file and
line, the violated spec section, a severity, and the `scaffold` step that fixes it. Severities:
**Critical** — the app crashes, does not build, or violates a MUST with a user-visible failure;
**Warning** — a MUST/SHOULD violated without immediate failure; **Suggestion** — SHOULD/MAY.

Where the evidence needs a device (probe, live preview, button events), state whether it was
gathered in this run or is `unverified` — never infer a device result from code.

| # | Check | Evidence to inspect | Spec | Severity if failed | Fix in |
|---|---|---|---|---|---|
| 1 | No WebView/WebUSB/cross-platform path; Camera2 `LENS_FACING_EXTERNAL` used only after a recorded device probe | camera module, run notes, verified-devices row | §A | Critical | step 2 |
| 2 | Platform probe was performed and recorded before an engine was integrated | run report / module README | §A, REQ-27 | Warning | step 2 |
| 3 | Descriptors of the target body recorded; body listed in §Verified devices | spec table, module README | §A | Warning | steps 1, 7 |
| 4 | Engine at `USBMonitor` + `UVCCamera` (`com.serenegiant.usb`), or fallback case recorded in the engine module; paths not mixed | build files, imports | §B | Critical | step 2 |
| 5 | `USBMonitor.register()` never called (or vendored artifact patched on the recorded fallback) | grep the module | §B/§C | Critical | step 3 |
| 6 | Pinned version's every artifact resolves as AAR; `libuvc:3.2.7` or a vendored `third_party/` repo only on the fallback, ordered before the remote, content-filtered, with per-artifact provenance | version catalog, `settings.gradle.kts`, `third_party/README` | §B | Critical | step 2 |
| 7 | Fallback: `libuvc` explicit compile dependency beside `libausbc` | build file | §B | Warning | step 2 |
| 8 | `usb.host` `required="false"` | merged manifest | §C | Critical | step 3 |
| 9 | `CAMERA` declared, held before open, rationale names the microscope; ledger row exists (`android-permissions-derive`) | manifest, ledger, request flow | §C | Critical | step 3 |
| 10 | USB grant is a separate consent with its own denied state | state model | §C | Warning | step 3 |
| 11 | `PendingIntent` explicit (`setPackage`) and mutable; receiver registered with an explicit export flag | grant code | §C | Critical | step 3 |
| 12 | Attachment filter, if present, is not the only entry point | manifest | §C | Warning | step 3 |
| 13 | State model distinguishes no-device / pending / denied / no-host / engine error | sealed type, UI strings | §C/§H | Warning | step 3 |
| 14 | Open guarded by a concurrency flag; opens only with permitted device **and** live surface; no resolution change in response to `unsupported preview size` | open path, git history | §D | Critical | step 4 |
| 15 | Raw-frame callback alive on the chosen preview path (`RenderMode.NORMAL` on the fallback) | preview setup | §D | Warning | step 4 |
| 16 | Teardown on leaving composition, re-register on return; transient close in a switch not treated as loss | lifecycle code | §D | Warning | step 4 |
| 17 | Engine callbacks re-attached after every reopen to the instance the state callback supplied | open path | §D | Critical | step 5 |
| 18 | Capture via one-shot frame callback + `YuvImage`, not `captureImage()`; no storage permission | capture code, merged manifest | §E | Critical | step 5 |
| 19 | Even crop edges, bounded wait with typed timeout, dimensions and byte size reported | capture code, tests | §E | Warning | step 5 |
| 20 | Preview at a frame-able mode; still resolution chosen from the queried largest mode after the measured detail test | mode selection, run report | §G | Warning | step 5 |
| 21 | Mode switch serialized, surfaced, bounded, degrading, always restoring the preview mode; cost measured | switch code, run report | §G | Warning | step 5 |
| 22 | Button and status callbacks reached directly; any reflection confined, null-guarded, `-keepclassmembers` present | engine module, ProGuard rules | §F | Warning (Critical if reflection unguarded in release) | step 6 |
| 23 | Only measured button indices mapped; unmapped events logged raw; no hardware control offered the device does not report | button mapping, UI | §F | Warning | step 6 |
| 24 | Zoom labelled digital where it is a crop; same crop on preview and capture | UI strings, crop code | §F | Warning | step 6 |
| 25 | Engine types confined to one module behind an app-owned interface; geometry/encoding unit-tested without a device | module graph, tests | §H | Warning | steps 4, 7 |
| 26 | Non-obvious guards commented with their constraint | code | §H | Suggestion | step 4 |
| 27 | Test instructions: network ADB before attach, wake state named, emulator limitation stated | README / test docs / run report | §I | Warning | step 7 |
| 28 | Native libraries checked for 16 KB page-size alignment | release-readiness §D report | `release-readiness` §D | Warning | step 2 |

Report format: the table's failed rows as findings (`file:line`, section, severity, fix step),
followed by the `unverified` device checks and the spec gaps met (proposed extensions, REQ-6).
Never propose an edit inside the `audit` run itself; hand the fixes to a `scaffold` follow-up.
