---
name: android-permissions-derive
description: "Determines which Android permissions an app genuinely needs and records them per spec/android/permissions/. Derives the set forward from user-visible features, rejects any permission a permission-free alternative serves, reads the merged manifest for library-injected permissions, and writes a justified ledger row per permission (trigger point, denial behaviour, store obligation). Then applies the declaration (bounds, flags, uses-feature, foreground-service types, removals), wires request and degradation paths, and verifies the shipped set. Operations: derive, audit (read-only report), apply. Invoke when the user asks which permissions an app needs, wants one added, removed, justified, or audited, or hits a denial or SecurityException. Also handles equivalent German-language requests. Don't use for the scanning camera path (android-barcode-scanner-scaffold) or the alerting channel (android-notification-derive). Supports resume on re-invocation."
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
  - situation: "A whole-app security audit (storage, network, components, WebView, auth) is wanted rather than a permission decision"
    alternative: android-security-reviewer
see_also:
  - android-notification-derive
  - android-feature-implement
  - android-barcode-scanner-scaffold
  - android-project-scaffold
  - android-security-reviewer
  - android-uvc-microscope-scaffold
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

Grounding specs, in the order they bind this skill: `spec/android/permissions/` (model,
derivation, declaration, runtime flow, families, verification, testing), `spec/android/security/`
§E/§D (permission minimalism, Data Safety accuracy, component hardening),
`spec/android/app-design-navigation/` §F (in-context request timing and rationale),
`spec/android/notifications-alerting/` §C/§G (the channel that implies the permission),
`spec/android/adb-workflows/` (device commands for verification and test states),
`spec/android/test-automation/` (where the permission-path tests live), and
`spec/android/release-readiness/` (what "done" means for the touched build).

## German trigger phrases

Respond to these (and equivalents) exactly as to their English counterparts; the frontmatter
`description` stays English-only per `skill-management` §Structure:

- "Welche Berechtigungen braucht die App?", "Leite die Permissions für dieses Feature ab"
- "Prüfe/auditiere die Manifest-Berechtigungen", "Begründe die Permission X", "Entferne die
  Berechtigung, die die Library mitbringt"
- "Die Permission wird verweigert / dauerhaft abgelehnt", "SecurityException wegen fehlender
  Berechtigung", "Foreground-Service-Typ / Hintergrundstandort / exakter Alarm deklarieren"

## Why this is a skill, not an agent

- **Mid-flow approval is the contract.** Admitting a permission, rejecting an alternative,
  removing a library-injected permission, and every manifest write are operator decisions with
  consequences that outlive the run (REQ-8); an agent's fire-and-forget shape cannot carry them.
- **The persistent artifact is the deliverable.** Ledger and manifest edits land in the working
  tree and are reviewed in context, not behind a structured-report boundary.
- **It composes with sibling capabilities.** Scanning access path → `android-barcode-scanner-scaffold`,
  request UI → `android-compose-ui`, red build → `android-debugging`; per
  `spec/claude/skill-vs-agent/` §Primary decision rule the orchestrator is always a skill.
- Counter-dimension considered: the read-only `audit` would suit a dedicated auditor agent
  (a candidate spec extension); it stays here because its findings are phrased as the `derive`
  rows the operator starts next, so one gate vocabulary serves both.

## Boundary vs the sibling capabilities

- `android-barcode-scanner-scaffold` owns the scanning access-path decision (REQ-18), including
  whether `CAMERA` is held at all; for code scanning, hand that decision there and take its
  result as input.
- `android-feature-implement` owns feature work across layers (REQ-19) and **calls this skill**
  for the permission step rather than deciding permissions itself.
- `android-compose-ui` owns the rationale surface, denied-state UI, and settings affordance
  (REQ-13); this skill decides *what* they must express and hands the authoring there.
- `android-project-scaffold` creates the project (REQ-12) with an empty permission set; every
  later addition comes through this skill. `android-ux-reviewer` (REQ-14) never writes a manifest.
- Notification permissions follow from an alerting channel owned by `android-notification-derive`
  (REQ-21; `spec/android/notifications-alerting/` §C); its ledger row is the input here — see
  `references/permission-decision-catalog.md` §4 Notifications. **Guard-code ownership:** the
  SDK-version guards around `canUseFullScreenIntent()` (API 34+) and
  `canPostPromotedNotifications()` (API 36+), their degradation branch, and the settings-intent
  launch (`ACTION_MANAGE_APP_USE_FULL_SCREEN_INTENT`, `ACTION_APP_NOTIFICATION_PROMOTION_SETTINGS`)
  are written by that skill's `apply` templates; this skill records the obligation in the
  ledger row and verifies its presence at step 8, but never writes the guard.
- `android-debugging` diagnoses build failures and crashes (REQ-16). A `SecurityException`
  belongs here only as evidence of a missed derivation path.

## User-language policy

Detect the operator's language and respond in it (German for this operator). Generated artifacts
stay canonical: manifest XML, Kotlin, and identifiers in English; the ledger is written in
English so it stays reviewable alongside the spec corpus; user-visible rationale copy is
externalized to `strings.xml` per `spec/android/localization/` §A.

## Operations

Pick one at the start and say which is running. The split is deliberate: `derive` **decides and
records**, `audit` **only reports**, `apply` **writes**. Nothing is written into the app before
a complete ledger row exists for it.

- **`derive`** — a capability exists or is planned and its permission consequence is unknown.
  Runs steps 1–5 and ends with the ledger row. Touches no manifest and no code.
- **`audit`** — an app already declares permissions and the set needs justifying, reducing, or
  proving. Runs the audit procedure in `references/ledger-and-verification.md` §4 and **writes
  nothing at all** — not the ledger, not the manifest, not tests: it produces a
  severity-classified findings report (`Critical` / `Warning` / `Suggestion` / `Info` per
  `spec/claude/review-plan/`) naming the ledger rows the app owes; turning a finding into a row
  is a `derive` run, the removal or declaration it implies an `apply` run. (Changed from the
  earlier revision, in which `audit` wrote ledger rows and tests; it now mirrors
  `android-notification-derive`'s read-only `audit`.)
- **`apply`** — a `derive` result exists and is being written into the app. Runs steps 6–8.
  Refuses to start when the ledger has no complete row for the permission at hand.

An end-to-end request ("add this capability") is `derive` then `apply`, run back-to-back with
the handover named, so the operator sees the ledger before anything is written.

## Preconditions

Before writing anything:

- Confirm the working directory is a git repository holding an Android project with a Gradle
  application module and an `AndroidManifest.xml`. Without one, stop and route to
  `android-project-scaffold`.
- Read `references/permission-decision-catalog.md` in full — the decision surface distilled
  from `spec/android/permissions/` §A/§C/§D/§E/§F; entries marked *spec-extension proposed
  (REQ-6)* are provisional.
- Establish the app's `minSdk` and `targetSdk` from the module's build script; nearly every
  rule in §D and §F is version-conditional.
- Check for uncommitted changes in the manifest and build scripts. If dirty, report and ask
  whether to stash, commit, or abort — never overwrite unconfirmed work (REQ-8).

## Procedure

Run the steps in order. Confirm with the operator at each gate before writing.

### 1. State the capability as a user-visible feature

Restate what the app will do, in one sentence, as an outcome for a user — "the user picks a
photo to attach" is derivable; "the app needs storage access" is already a conclusion. Where a
requirement artifact or feature file exists, work from it. Gate: confirm the restatement.

### 2. Run the alternatives gate

Consult the alternatives table in `references/permission-decision-catalog.md` §1 and establish
whether the platform offers a documented path to the same outcome without a permission. Present
the alternative, its cost, and what taking the permission gives up. A permission passes only
when the alternative provably does not serve the feature, and the reason is recorded verbatim
in the ledger — "more convenient" and "the SDK does it that way" are not reasons. Gate: confirm
each admission or adoption.

### 3. Classify and trace each admitted permission to its API

For every permission that survived step 2, classify its type per `spec/android/permissions/` §A
(install-time normal, signature, runtime, special — catalog §0) and note which permission-model
surface the user meets (Privacy Dashboard, indicators, sensor toggles). Then establish the exact
API call that requires it from an authoritative source — the reference documentation or the
`@RequiresPermission` annotation, reading `allOf` / `anyOf` / `conditional` precisely — never
from memory or by name-matching. A version-conditional requirement records its API-level
boundary; it becomes the `maxSdkVersion` in step 6. Where no spec and no primary source settles
the requirement, stop and report the gap with a proposed spec extension (REQ-6).

### 4. Read the merged manifest

Build the variant and read the merged permission set (commands in
`references/ledger-and-verification.md` §2), never the hand-written manifest — library and
merger-injected permissions appear only there. Diff it against the derived set: **in merged,
not derived** is a library contribution or leftover, adopted with a written reason or removed
in step 6 with `tools:node="remove"`; **in derived, not merged** is a declaration that lands
in step 6. Gate: confirm the classification of every difference before any removal.

### 5. Decide trigger point, degradation, and store obligation — then write the row

Before any row is written, decide and confirm per admitted permission: the **trigger point**
(the in-context user action at which the request is made, incremental per §E — foreground
location before background, never a startup bundle; for a special or non-runtime notification
permission, the explicit user step at which the settings route is offered); the **degradation
on denial** (what the user sees and what still works, including the permanently denied state
with explanation plus settings route, and the sensor-toggle case of §A that is not a denial —
a denial that leaves no usable path is a derivation error: return to step 2); and the
**store-side obligation** (catalog §5 — recorded and handed to the operator, never filed here).

Then write or update `project/permissions-ledger.md` from the template in
`references/ledger-and-verification.md` §1 — one row per admitted permission and one per
permission deliberately removed. Gate: confirm the row; `derive` ends here.

### 6. Write the declaration

Precondition: the ledger row from step 5 is complete. Apply, per
`references/permission-decision-catalog.md` §2: `<uses-permission>` with `android:maxSdkVersion`
wherever the requirement ends at an API level and `neverForLocation` on `BLUETOOTH_SCAN` /
`NEARBY_WIFI_DEVICES` wherever no location is derived; `<uses-feature android:required="false">`
plus the `hasSystemFeature()` check for optional hardware; the foreground-service triple (type
on the `<service>`, `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_*`) plus the runtime permission
the type presupposes; `<queries>` for package visibility (`QUERY_ALL_PACKAGES` only with a
recorded justification); `tools:node="remove"` (narrowed with `tools:selector`) for every
unwanted contribution from step 4; a custom permission only at `signature` level on the
component it guards. Gate: confirm before each manifest write (REQ-8).

### 7. Wire the runtime flow and the degradation path

For every runtime permission, put in place the flow of `spec/android/permissions/` §E:
`checkSelfPermission` immediately before each protected access (never cached), the
`shouldShowRequestPermissionRationale` gate read together with the request history, the request
through `ActivityResultContracts.RequestPermission` / `RequestMultiplePermissions`, the branch
on the result, and the degraded path decided in step 5; permanent denial gets an explanation
plus a settings route, never a re-request. Where the Compose wrappers are used, keep the
`@ExperimentalPermissionsApi` opt-in confined to one wrapper type, and apply the
`VIEW_PERMISSION_USAGE` and `revokeSelfPermissionOnKill` rules (catalog §3). A special
permission takes its own path: dedicated check method, rationale that explains the settings
step, settings intent, `onResume()` re-check. For the two non-runtime notification permissions
the guard code is owned by `android-notification-derive` (§Boundary) — confirm it is present
rather than writing it. Hand the rationale surface, denied-state UI, and settings affordance to
`android-compose-ui` with what each must express.

### 8. Verify, test, and hand off

- Verify the shipped set from the merged manifest and, where an artifact exists,
  `apkanalyzer manifest permissions`: no permission without a ledger row, no row without a
  declaration, every runtime guard the ledger records present in the code.
- Ensure Android Lint runs with `MissingPermission` as an error (`spec/android/security/` §F).
- Cover granted, denied, and permanently denied as tests for every permission in the ledger,
  with the state established through ADB, never by tapping dialogs (`GrantPermissionRule` only
  grants). Fill the row's **Declared as** and **Tests** lines.
- Report, in the operator's language: the admitted set with justifications, alternatives
  adopted, permissions removed and from which library, declarations written, degradation per
  permission, test states covered, every store-side obligation the operator must file, and any
  spec gap. Never leave a red, skipped, or unrunnable element unreported (REQ-1, REQ-7).

Where this run touched a build, close on the release-readiness gate of
`spec/android/release-readiness/` §E as `android-feature-implement` does; route a red build to
`android-debugging` rather than guessing.

## Reference files

- `references/permission-decision-catalog.md` before step 2 — type classification, the
  alternatives gate, declaration and runtime-flow details, per-family rules, store obligations.
- `references/gotchas.md` before step 2 as well — the platform facts that silently produce a
  wrong permission set.
- `references/ledger-and-verification.md` in steps 4, 5, and 8 and for `audit` — the ledger
  format, the merged-manifest and artifact commands, the ADB test-state commands, and the
  read-only audit procedure.

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

- **Never** admit a permission not traced forward from a named user-visible feature through a
  concrete API call, and **never** derive the set from what the manifest already contains.
- **Never** declare a permission where a documented permission-free alternative serves the
  feature — and never "just in case", which for `CAMERA` breaks `ACTION_IMAGE_CAPTURE`.
- **Never** establish an API's permission requirement from memory; read the reference
  documentation or the `@RequiresPermission` annotation.
- **Never** judge the set from the hand-written manifest — only the merged manifest and the
  built artifact are evidence.
- **Never** cache a permission check across a protected access, never build logic on
  permission-group membership, never re-request a permanently denied permission, never leave a
  denial as a dead end, never request a startup bundle or background location before a
  foreground grant.
- **Never** declare `QUERY_ALL_PACKAGES`, `MANAGE_EXTERNAL_STORAGE`, `USE_EXACT_ALARM`, or a
  broad media permission as a convenience — each needs the recorded justification of §G.
- **Never** remove a library-injected permission without confirming the app does not depend on
  the library path that needs it, and never remove or overwrite anything without operator
  confirmation (REQ-8).
- **Never** file, edit, or simulate a Play Console declaration; record the obligation and hand
  it to the operator (§G). **Never** write anything in `audit`.
- **Always** complete a permission's ledger row — trigger point, denial behaviour, and store
  obligation included — before that permission is written into the manifest; step 7 implements
  those decisions rather than discovering them.
- **Always** report a capability whose permission requirement no spec and no primary source
  settles, with a proposed spec extension, instead of deciding silently (REQ-6).
- When `spec/android/permissions/` disagrees with this skill, the spec wins.

## Gotchas

Read `references/gotchas.md` before step 2 — it carries the full set. The three that most often
produce a wrong result: declaring `CAMERA` breaks the permission-free `ACTION_IMAGE_CAPTURE`
path; `shouldShowRequestPermissionRationale()` returning `false` means "ask" before the first
request and "permanently denied" after one, and only grant state plus request history separate
them; and the merged manifest — not the source manifest — is where permissions come from, which
is why the check re-runs after every dependency change.
