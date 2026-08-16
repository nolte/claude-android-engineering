---
name: android-permissions-derive
description: "Determines which Android permissions an app genuinely needs and records them conformantly, per spec/android/permissions/. Derives the set forward — feature to capability to API call to permission — rejects any permission a documented permission-free alternative serves (photo picker, capture intents, code scanner, SAF), reads the merged manifest to catch library-injected permissions, and writes a justified ledger row per permission. Then applies the declaration (maxSdkVersion, neverForLocation, uses-feature, foreground-service types, queries, tools:node=remove), wires the runtime request, denial, and degradation paths, verifies the shipped set, and hands store-side declaration obligations to the operator. Operations: derive, audit, apply. Invoke when the user asks which permissions an app needs, wants one added, removed, or justified, wants the manifest set audited, or hits a denial or a SecurityException. Also handles equivalent German-language requests. Supports resume on re-invocation."
tags: [privacy, audit, implementation]
phase: build
summary: "Derives an Android app's required permission set from its features, rejects permissions a permission-free alternative serves, and records the result in manifest, runtime flow, ledger, and tests."
summary_de: "Ermittelt die nötigen Android-Berechtigungen aus den Features, verwirft Berechtigungen mit berechtigungsfreier Alternative und hinterlegt das Ergebnis in Manifest, Laufzeitablauf, Register, Tests."
use_when:
  - "a new capability needs a permission decision before any code is written"
  - "an existing app's manifest permission set should be audited, justified, or cleaned up"
  - "a permission is denied, permanently denied, or throws a SecurityException at runtime"
  - "a dependency added a permission nobody asked for"
  - "a foreground service, background location, or exact alarm needs its declaration set correctly"
dont_use_when:
  - situation: "The camera-access path for scanning codes needs deciding"
    alternative: android-barcode-scanner-scaffold
  - situation: "A feature needs implementing across layers, permissions being one part of it"
    alternative: android-feature-implement
  - situation: "Permission prompt wording, placement, or screen design is the question"
    alternative: android-compose-ui
  - situation: "A build failure or crash needs diagnosing rather than a permission decision"
    alternative: android-debugging
see_also:
  - android-feature-implement
  - android-barcode-scanner-scaffold
  - android-project-scaffold
resumable: true
---

# Android Permissions Derive

Determines which permissions an Android app genuinely needs, and records them so the manifest,
the runtime request, the degradation path, and the store-facing justification all say the same
thing.

The governing idea is directional: a permission set is **derived forward** from what the app
does for a user — feature, capability, API call, permission — and never read backward off the
manifest that happens to exist. A permission that cannot be traced along that chain does not
enter the set, and a permission for which the platform offers a documented permission-free path
is rejected in favour of that path.

The authoritative rules live in `spec/android/permissions/`; this skill operationalizes them and
never restates or contradicts them. On any conflict the spec wins — report the gap and propose a
spec change rather than deciding silently (REQ-6).

Grounding specs, in the order they bind this skill: `spec/android/permissions/` (the model, the
derivation, the declaration, the runtime flow, the families, verification, testing),
`spec/android/security/` §E/§D (permission minimalism as a security obligation, Data Safety
accuracy, component hardening), `spec/android/app-design-navigation/` §F (in-context request
timing and rationale), `spec/android/notifications-alerting/` §C/§G (the channel
that implies the permission), `spec/android/adb-workflows/` (the device commands used for verification
and test-state setup), `spec/android/test-automation/` (where the permission-path tests live),
and `spec/android/release-readiness/` (what "done" means for the touched build).

## Why this is a skill, not an agent

- **Mid-flow approval is the contract.** Admitting a permission, rejecting an alternative as
  insufficient, removing a library-injected permission, and every manifest write are operator
  decisions with consequences that outlive the run (REQ-8); an agent's fire-and-forget shape
  cannot carry those gates.
- **The persistent artifact is the deliverable.** The permission ledger and the manifest edits
  land in the working tree and are reviewed in context, not behind a structured-report boundary.
- **It composes with sibling capabilities.** The scanning access-path decision belongs to
  `android-barcode-scanner-scaffold`, the request UI to `android-compose-ui`, a red build to
  `android-debugging`; per `spec/claude/skill-vs-agent/` §Primary decision rule the orchestrator
  is always a skill.
- Counter-dimension considered: the audit operation alone — reading the merged manifest,
  enumerating declared permissions, tracing call sites — would suit an agent's context
  isolation, but its findings feed directly into the admit/reject gates that follow, so
  splitting it out would break the interaction it exists to serve.

## Boundary vs the sibling capabilities

- `android-barcode-scanner-scaffold` owns the scanning access-path decision (REQ-18), including
  whether `CAMERA` is held at all. When the capability under derivation is code scanning, hand
  that decision there and take its result as input.
- `android-feature-implement` owns feature work across layers (REQ-19) and **calls this skill**
  for the permission step rather than deciding permissions itself.
- `android-compose-ui` owns the rationale surface, the denied-state UI, and the settings-route
  affordance (REQ-13); this skill decides *what* those surfaces must express and hands the
  authoring there.
- `android-project-scaffold` creates the project (REQ-12); a scaffolded app starts with an empty
  permission set, and every later addition comes through this skill.
- `android-ux-reviewer` reviews UI read-only (REQ-14) and never writes a manifest.
- Notification permissions follow from an alerting channel derived in
  `android-feature-implement` (`spec/android/notifications-alerting/` §C); its ledger row is the
  input here — see `references/permission-decision-catalog.md` §Notifications.
- `android-debugging` diagnoses build failures and crashes (REQ-16). A `SecurityException`
  belongs here only as evidence of a missed derivation path; a crash that needs diagnosing first
  goes there.

## User-language policy

Detect the operator's language and respond in it (German for this operator). Generated artifacts
stay canonical: manifest XML, Kotlin, and identifiers in English; the ledger is written in
English so it stays reviewable alongside the spec corpus; user-visible rationale copy is
externalized to `strings.xml` per `spec/android/localization/` §A.

## Operations

Pick one at the start and say which is running. All three share the gates below. The split is
deliberate: `derive` and `audit` **decide and record**, `apply` **writes**. Nothing is written
into the app before a complete ledger row exists for it.

- **`derive`** — a capability exists or is planned and its permission consequence is unknown.
  Runs steps 1–4, then step 7's ledger write. Touches no manifest and no code.
- **`audit`** — an app already declares permissions and the set needs justifying, reducing, or
  proving. Runs steps 2–4 against the existing set — treating every declared permission as a
  candidate that must earn its row — then step 7 in full (ledger, verification, report).
- **`apply`** — a `derive` or `audit` result exists and is being written into the app. Runs
  steps 5–7. Refuses to start when the ledger has no complete row for the permission at hand.

An end-to-end request ("add this capability") is `derive` followed by `apply`; run them
back-to-back in one invocation and say when the handover happens, so the operator sees the
ledger before anything is written.

## Preconditions

Before writing anything:

- Confirm the working directory is a git repository holding an Android project with a Gradle
  application module and an `AndroidManifest.xml`. Without one, stop and route to
  `android-project-scaffold`.
- Read `references/permission-decision-catalog.md` in full. It is the decision surface distilled
  from `spec/android/permissions/` §C/§D/§F — the alternatives gate, the declaration details,
  and the families whose rules differ — and every admitted permission is checked against it.
- Establish the app's `minSdk` and `targetSdk` from the module's build script. Nearly every rule
  in §D and §F is version-conditional, and a derivation run without these two numbers produces
  declarations that are wrong on some devices.
- Check for uncommitted changes in the manifest and build scripts. If dirty, report and ask
  whether to stash, commit, or abort — never overwrite unconfirmed work (REQ-8).

## Procedure

Run the steps in order. Confirm with the operator at each gate before writing.

### 1. State the capability as a user-visible feature

Restate what the app will do, in one sentence, as an outcome for a user — not as a technical
capability. "The user picks a photo to attach" is derivable; "the app needs storage access" is
already a conclusion and skips the step that matters. Where a requirement artifact or feature
file exists in the repository, read it first and work from it. Gate: confirm the restatement.

### 2. Run the alternatives gate

For the stated feature, consult the alternatives table in
`references/permission-decision-catalog.md` and establish whether the platform offers a
documented path that reaches the same outcome without a permission. Present the alternative, its
cost, and what would be given up by taking the permission instead.

A permission is admitted past this gate only when the alternative provably does not serve the
feature — and the reason is recorded verbatim in the ledger. "It is more convenient" and "the
SDK does it that way" are not reasons. Gate: confirm each admission or adoption.

Two traps to apply rather than rediscover: declaring `CAMERA` while relying on
`ACTION_IMAGE_CAPTURE` turns a permission-free path into a `SecurityException`, and a
third-party SDK's permission appears to the user as the app's own request.

### 3. Trace each admitted permission to its API

For every permission that survived step 2, establish the exact API call that requires it, and
establish the requirement from an authoritative source — the API's reference documentation or
its `@RequiresPermission` annotation, reading `allOf` / `anyOf` / `conditional` precisely. Never
from memory, and never by pattern-matching a permission name to a capability name. Where the
requirement is version-conditional, record the API-level boundary; it becomes the
`maxSdkVersion` in step 5.

Where a capability's permission requirement is settled by no spec and no primary source, stop
and report the gap with a proposed spec extension (REQ-6).

### 4. Read the merged manifest

Build the variant and read the merged permission set, not the hand-written manifest — library
contributions and merger-injected implicit permissions appear only there. Use the commands in
`references/ledger-and-verification.md`.

Diff the merged set against the derived set and classify every difference:

- **in merged, not derived** — a library contribution or a leftover. Each one is either adopted
  with a written reason or removed in step 5 with `tools:node="remove"`.
- **in derived, not merged** — a declaration still missing; it lands in step 5.

Gate: confirm the classification of every difference before any removal.

### 5. Write the declaration

Precondition, not a formality: the permission's ledger row is **complete before this step
writes anything** — including its trigger point and its behaviour on denial. Step 6 implements
those two decisions; it does not discover them. A permission whose denial behaviour is still
unknown is not ready to be declared, and the run returns to step 2.

Apply, per `references/permission-decision-catalog.md` §Declaration:

1. `<uses-permission>` for every admitted permission, with `android:maxSdkVersion` wherever the
   requirement ends at an API level, and `android:usesPermissionFlags="neverForLocation"` on
   `BLUETOOTH_SCAN` wherever the app does not derive location from scan results.
2. `<uses-feature android:required="false">` for every hardware-bound permission the app can
   live without, plus the runtime `hasSystemFeature()` check at the call site.
3. Foreground services: `android:foregroundServiceType` on the `<service>`, the base
   `FOREGROUND_SERVICE` permission, the type-specific `FOREGROUND_SERVICE_*` permission, and the
   runtime permission the type presupposes.
4. `<queries>` for package visibility; `QUERY_ALL_PACKAGES` only with a recorded justification
   that targeted queries cannot express the need.
5. `tools:node="remove"` (narrowed with `tools:selector` when only one library is meant) for
   every unwanted contribution from step 4, with the removal recorded so a later dependency bump
   does not silently reinstate it.

Gate: confirm before each manifest write (REQ-8).

### 6. Wire the runtime flow and the degradation path

For every runtime permission, put in place the flow of `spec/android/permissions/` §E:
`checkSelfPermission` immediately before each protected access (never cached), the
`shouldShowRequestPermissionRationale` gate, the request through
`ActivityResultContracts.RequestPermission` / `RequestMultiplePermissions`, the branch on the
result, and the degraded path. Permanent denial is detected and answered with an explanation
plus a route into the app's settings — never a re-request into a dialog the system will not
show.

For every special permission, use its own path instead: the dedicated check method, a rationale
that explains what to do in settings, the settings intent, and a re-check in `onResume()`.

Requests are incremental and in context — foreground location before background, never a
startup bundle. Hand the rationale surface, the denied-state UI, and the settings affordance to
`android-compose-ui`; this skill supplies what each must express and the state model behind it.

Then state, per permission, what the app does when the answer is no. A permission whose denial
leaves no usable path is a derivation error from step 2, not a UX problem — return to that gate
rather than shipping a dead end.

### 7. Verify, test, and hand off

- Verify the shipped set from the merged manifest and, where an artifact exists,
  `apkanalyzer manifest permissions`. Confirm no permission lacks a ledger row and no ledger row
  lacks a declaration.
- Ensure Android Lint runs with `MissingPermission` as an error, per
  `spec/android/security/` §F.
- Cover granted, denied, and permanently denied as tests for every permission in the ledger,
  with the state established through ADB rather than by tapping dialogs. `GrantPermissionRule`
  only grants and cannot revoke — it is not the mechanism for denial coverage.
- Write or update the permission ledger at `project/permissions-ledger.md` from the template in
  `references/ledger-and-verification.md` — including a row for every permission deliberately
  removed, so a later dependency bump cannot reinstate it unnoticed.
- Report, in the operator's language: the admitted set with its justifications, every
  alternative adopted, every permission removed and from which library, the declarations
  written, the degradation behaviour per permission, the test states covered, every store-side
  declaration obligation the operator must file, and any spec gap found. Never leave a red,
  skipped, or unrunnable element unreported (REQ-1, REQ-7).

Where this run touched a build, close on the release-readiness gate of
`spec/android/release-readiness/` §E as `android-feature-implement` does; route a red build to
`android-debugging` rather than guessing.

## Reference files

- Read `references/permission-decision-catalog.md` before step 2 — the alternatives gate, the
  declaration details, and the per-family rules (location, media, notifications, Bluetooth,
  exact alarms, health, package visibility, local network, policy-restricted).
- Read `references/gotchas.md` before step 2 as well — the non-obvious platform facts that
  silently produce a wrong permission set.
- Read `references/ledger-and-verification.md` in steps 4, 6, and 7 — the ledger format, the
  merged-manifest and artifact commands, and the ADB state-setup commands for the test states.

## Resumability

Per `spec/claude/resumable-work/`, this skill is `resumable: true`. State is persisted to
`.resume/android-permissions-derive/<run-id>.yml` after every gate and at each named step
boundary. On re-invocation, scan `.resume/android-permissions-derive/*.yml` for files with
`status: in_progress` whose `inputs:` snapshot (repository + operation + capability) matches the
current request; when one matches, prompt
`Resume run <run_id> from phase <phase> (last checkpoint <last_checkpoint_at>)? [resume / start-new / discard]`.
`resume` re-hydrates and re-asks no answered gate; `start-new` leaves the old file intact;
`discard` deletes it. Fail closed on unparseable or higher-`schema_version` files. The envelope
keys and lifecycle are load-bearing in the spec and are not duplicated here.

## Hard rules

- **Never** admit a permission that was not traced forward from a named user-visible feature
  through a concrete API call, and **never** derive the set from what the manifest already
  contains.
- **Never** declare a permission where a documented permission-free alternative serves the
  feature — and never declare one "just in case", which for `CAMERA` actively breaks
  `ACTION_IMAGE_CAPTURE`.
- **Never** establish an API's permission requirement from memory; read the reference
  documentation or the `@RequiresPermission` annotation.
- **Never** judge the permission set from the hand-written manifest — only the merged manifest
  and the built artifact are evidence.
- **Never** cache a permission check result across a protected access, and never build logic on
  permission-group membership.
- **Never** re-request a permanently denied permission, and never leave a denial as a dead end
  or a generic block.
- **Never** request permissions as a startup bundle, and never request background location
  before a foreground grant.
- **Never** declare `QUERY_ALL_PACKAGES`, `MANAGE_EXTERNAL_STORAGE`, `USE_EXACT_ALARM`, or a
  broad media permission as a convenience — each is policy-restricted and needs the recorded
  justification of §G.
- **Never** remove a library-injected permission without confirming the app does not depend on
  the library path that needs it, and never remove or overwrite anything without operator
  confirmation (REQ-8).
- **Never** file, edit, or simulate a Play Console declaration; record the obligation and hand
  it to the operator (`spec/android/permissions/` §G).
- **Always** complete a permission's ledger row — trigger point and denial behaviour included —
  before that permission is written into the manifest; step 6 implements those decisions rather
  than discovering them.
- **Always** report a capability whose permission requirement no spec and no primary source
  settles, with a proposed spec extension, instead of deciding silently (REQ-6).
- When `spec/android/permissions/` disagrees with this skill, the spec wins.

## Gotchas

Read `references/gotchas.md` before step 2 — it carries the full set. The three that most often
produce a wrong result:

- **Declaring a permission can break the permission-free path.** With `CAMERA` declared but not
  granted, `ACTION_IMAGE_CAPTURE` raises a `SecurityException` instead of handing off to the
  system camera. The defensive declaration is the defect.
- **`shouldShowRequestPermissionRationale()` returning `false` is ambiguous by position.**
  Before the first request it means "ask"; after a completed request on a not-granted
  permission it means "permanently denied". Only grant state plus request history separate them.
- **The merged manifest is where permissions actually come from.** A dependency bump can add a
  permission with no source-manifest edit — which is why the check is re-run after every
  dependency change.
