---
name: android-feature-implement
description: "Implements a feature in a Kotlin Android app across its layers as a flat, server-authoritative view layer per spec/android/app-architecture/: the backend decides, the local replica is what the UI observes. Designs the screen state model (loading, content, empty, error, stale, pending write), repository and data sources, write strategy and staleness policy, the eight-case failure handling of spec/android/backend-contract/, and the delivery path (FCM data messages, WorkManager, AlarmManager) of events whose channel android-notification-derive decided. Captures missing backend capabilities as handoff artifacts in project/backend-requirements/ instead of working around them. Closes with the release-readiness gate (R8 release build, lint, tests, device smoke, process death). Invoke to implement an Android feature, wire a screen to an API, or add offline support. Also handles equivalent German-language requests. Supports resume on re-invocation."
tags: [implementation, fullstack, ui]
phase: build
summary: "Implements an Android feature across layers as a flat, server-authoritative view layer, turns missing backend capabilities into handoff artifacts, and closes on the release-readiness gate."
summary_de: "Setzt ein Android-Feature schichtübergreifend als flachen, serverautoritativen View Layer um, überführt fehlende Backend-Fähigkeiten in Übergabeartefakte und schließt mit der Release-Reife-Schranke."
use_when:
  - "you want a feature implemented across UI, ViewModel, repository, and data sources"
  - "you want a screen wired to a backend API with every failure case handled"
  - "you want offline reads or queued writes without business logic on the device"
  - "you want missing backend capabilities captured as requirements for a backend specialist"
  - "you want production-grade Kotlin verified on a release build, not a debug build"
dont_use_when:
  - situation: "You only want the Compose UI of a screen authored, with no data or backend work"
    alternative: android-compose-ui
  - situation: "You want to create a new Android project from scratch"
    alternative: android-project-scaffold
  - situation: "You want to diagnose a build failure, crash, or ANR"
    alternative: android-debugging
  - situation: "You want existing UI reviewed rather than changed"
    alternative: android-ux-reviewer
  - situation: "You want changed Kotlin/Compose code reviewed read-only against the architecture and contract specs"
    alternative: android-code-reviewer
see_also:
  - android-notification-derive
  - android-compose-ui
  - android-permissions-derive
  - android-project-scaffold
  - android-debugging
  - android-perceived-performance
  - android-ux-reviewer
  - android-code-reviewer
resumable: true
---

# Android Feature Implement

Implements a feature in an existing native Kotlin Android app across every layer it touches,
under one governing constraint: the app is a **flat view layer**. The backend decides, the
local replica is what the UI observes, and anything the contract cannot answer becomes a
recorded requirement for the backend side — never a rule quietly implemented on the device.
The authoritative rules live in `spec/android/`; this skill operationalizes them. On any
conflict the spec wins — report the gap and propose a spec change (REQ-6).

Grounding specs, in binding order: `spec/android/app-architecture/`,
`spec/android/backend-contract/`, `spec/android/release-readiness/`,
`spec/android/user-input-validation/`, `spec/android/notifications-alerting/` (the channel is
decided by `android-notification-derive`; its §E delivery path is implemented here), plus
`spec/android/project-structure/`, `spec/android/test-automation/`, `spec/android/security/`
— eight specs, distilled in `references/flat-layer-checklist.md`.

## Why this is a skill, not an agent

- **Mid-flow approval is the contract.** Design gate, backend-requirement gate, and every file
  overwrite need explicit operator consent (REQ-8).
- **The output belongs in the main conversation** — Kotlin, tests, and the requirement artifact
  land in the working tree and are reviewed in context.
- **It dispatches other capabilities** (`android-compose-ui`, `android-debugging`); per
  `spec/claude/skill-vs-agent/` §Primary decision rule the orchestrator is always a skill.
- Counter-dimension: the backend-gap analysis alone would suit an agent's context isolation,
  but it sits between two approval gates.

## Boundary vs the sibling capabilities

- `android-compose-ui` **authors the UI surface** (REQ-13); this skill **calls it for the UI
  step**. A purely "build this screen" request belongs there.
- `android-ux-reviewer` reviews UI read-only (REQ-14); `android-project-scaffold` creates the
  project (REQ-12) this skill requires; `android-debugging` takes every red state (REQ-16).
- `android-permissions-derive` owns every permission decision (REQ-20): a **device capability**
  from step 2 that may need one is handed there — derivation, ledger row, declaration, denial path.
- `android-notification-derive` owns every alerting-channel decision (REQ-21) and the ledger,
  ending at the device-side notification code. The **delivery path** (FCM reception,
  WorkManager/AlarmManager scheduling, missed-message sync) is data-layer work and stays
  **here** (step 3, 5.3, `references/layer-templates.md` §5); its ledger row is the input.
- `android-barcode-scanner-scaffold` owns scanning; `android-perceived-performance` owns
  performance remediation and measures any regression the step-7 report suspects.

## German trigger phrases

Respond to these (and equivalents) as to their English counterparts; the frontmatter
`description` stays English-only per `skill-management` §Structure:

- "Implementiere das Feature", "Verdrahte den Screen mit der API", "Mach die App
  offlinefähig", "Was fehlt im Backend dafür?", "Push-Nachricht empfangen und synchronisieren"

## User-language policy

Detect the operator's language and respond in it (German for this operator). Generated
artifacts stay canonical: Kotlin, identifiers, comments in English; user-visible copy in
`strings.xml` (English source, German translation) per `spec/android/localization/` §A; the
backend-requirement artifact in English.

## Operations

One operation, **`implement`** — the seven-step procedure below, run once per feature or
resumed per §Resumability. No read-only variant exists (UI review is `android-ux-reviewer`,
defects are `android-debugging`).

## Preconditions

Before writing anything:

- Confirm a git repository holding an Android project per `spec/android/project-structure/`;
  with no Gradle Android module, stop and route to `android-project-scaffold`.
- Read `references/flat-layer-checklist.md` in full — every produced layer is checked against it.
- Locate the contract surface (committed OpenAPI document, generated network component) and
  record its version. Per `spec/android/backend-contract/` §A: contract **and** client →
  consume, regenerate, never hand-edit; contract but **no client** → generate one in step 5.1
  with the portfolio `openapi-generator` config of checklist §3 (`jvm-retrofit2`,
  `kotlinx_serialization`, `enumUnknownDefaultCase=true`, into `core/network`), replacing
  hand-written DTOs; **no contract** → itself a backend requirement (step 4).
- If the paths to be touched are dirty, ask whether to stash, commit, or abort — never
  overwrite unconfirmed work (REQ-8).

## Implementation procedure

Run the steps in order; confirm with the operator at each gate before writing.

### 1. Establish the feature contract

Restate the feature in one sentence as an outcome for the user, then agree the screens touched,
the data types, the writes the user can perform, and the states each screen must show. Where a
requirement artifact or feature file exists, work from it. Gate: confirm the restatement.

### 2. Apply the flat-layer test

For every rule the feature seems to need, decide where it lives per
`spec/android/app-architecture/` §A: presentation, cache/sync policy, device capability, and
navigation state are the only device-owned classes; anything else is the backend's. List
*device-owned* items with their class and *backend-owned* items with what the contract supplies;
every unsupplied backend item goes into step 4 — never a silent client-side derivation — and
every *device capability* that may need a permission goes to `android-permissions-derive`
before any manifest edit (REQ-20). Gate: confirm the split.

### 3. Design the state and data model

Decide and record, per `references/flat-layer-checklist.md`:

- the screen state model — loading, content, empty, error with recovery action, plus
  **staleness** and **pending write** wherever the screen can be served from cache
- the repository and data-source shape, the three model sets (DTO, entity, UI model), mappers
- the staleness policy per cached type (revalidation window, stale-while-revalidate, hard expiry)
- the write strategy per write — online-only (default wherever the backend decides
  acceptance), queued, or local-first — with pending/rollback/conflict answers for the latter two
- for every value taken from the user, which of the four stages of
  `spec/android/user-input-validation/` §A owns each check, and which are *not* client-side;
  field-check parameters come from the contract, a missing limit is a step-4 requirement
- for every event a user might need to know about, the channel and its row in
  `project/notification-ledger.md` — obtained from `android-notification-derive` (REQ-21),
  which owns the §C gate chain; never run it here. Any implied permission goes to
  `android-permissions-derive` first
- for every ledger row with a channel, the **delivery path** per
  `spec/android/notifications-alerting/` §E — exactly one of **local**, **scheduled**,
  **pushed** — recorded on the row. This decision is this skill's; checklist §10 carries the
  rules (WorkManager vs `AlarmManager`, data vs notification message, `priority: high` reserve,
  missed-message sync), step 5.3 implements them. A pushed row without a server-side event
  contract is a step-4 trigger

Gate: confirm the design before generating code. The **four recorded decisions** — write
strategy per write, staleness policy per cached type, input-stage split, channel plus delivery
path per event — go, with every step-4 backend gap, into the feature's requirement or feature
file under `project/` (or a `## Decisions` note next to the feature package), never only into
a commit message (`spec/android/app-architecture/` §H). A case no spec covers is reported with
a proposed spec extension (REQ-6), never decided silently.

### 4. Capture backend requirements

Walk the §E trigger list of `spec/android/backend-contract/` against the feature. For each
trigger that fires, read `references/backend-requirement-template.md` and write
`project/backend-requirements/<YYYY-MM-DD>-<slug>.md` — nine sections, a stable `BR-<n>`, an
OpenAPI fragment marked as a proposal, synthetic examples only. Agree the interim client
behaviour (wait, ship without the part, or a time-boxed interim path recorded in the artifact).
Gate: confirm artifact and interim choice; a backend-repository issue is opened only on explicit
confirmation (REQ-8). Never implement the missing capability on the device.

### 5. Implement, bottom-up

Data layer first, then the state holder, then the UI:

1. **Data source and mapping** — the client is generated from the contract (Preconditions),
   its types stay in the network component, the DTO is mapped at the boundary, entities and
   DAOs stay below the repository. No domain layer, no pass-through use case (§F).
2. **Repository** — reads as `Flow` from the replica, writes as `suspend`; freshness metadata
   stored; the eight §B outcome cases of `spec/android/backend-contract/` mapped into the app's
   own result type (`ContractMismatch` on its own branch, never in an `else`); explicit
   timeouts; retries only for idempotent or keyed requests, with **capped exponential backoff
   plus jitter, a stated maximum attempt count, and an overall deadline** (§C), `Retry-After`
   honoured over that policy, not counted against the budget; OkHttp's transparent retry
   accounted for behind non-idempotent writes (§C).
3. **Sync and delivery path** — queued or local-first drains run in WorkManager unique work with a
   connectivity constraint and backoff, never in `viewModelScope`; fire-and-forget work that
   must outlive the screen runs in an application-scoped `CoroutineScope` (§E). The step-3
   delivery path becomes data-layer components per `references/layer-templates.md` §5 — a
   `FirebaseMessagingService` that only enqueues WorkManager work (expedited for
   `priority: high`), the missed-message sync on foreground and `onNewToken`, WorkManager or
   (time-is-the-point only) `AlarmManager` for scheduled rows, immutable explicit
   activity-targeting tap `PendingIntent`s, explicit `android:exported` on every added
   component (`spec/android/security/` §D). Notification construction stays with
   `android-notification-derive`.
4. **ViewModel** — a single `uiState` `StateFlow` via `stateIn(..., WhileSubscribed(5_000), ...)`,
   no ViewModel→UI event channel, no lifecycle-bound type held, injected dispatchers and clock;
   no network or database work from composition (§E) — hand that rule to `android-compose-ui`.
5. **UI** — invoke `android-compose-ui` with the step-3 state model, so its owner applies the
   UX, theming, adaptivity, localization, and accessibility rules; only wire the route here.

Gate: confirm before overwriting any existing file (REQ-8).

### 6. Test the states that only exist because the client is flat

Add JVM tests per `spec/android/test-automation/` §B/§C with fakes, covering every one of the
eight outcome cases the feature can hit, the stale state, the pending-write state, and the
recovery action on each error. Where the feature takes input, add the
`spec/android/user-input-validation/` §H paths: a field-identified rejection lands on its field
with the entered values preserved, and the restoration path is asserted. Untested offline and
rejection paths mean the feature is demonstrated, not implemented.

Mechanics per §B (checklist §7, templates §7): **JUnit 4**, `runTest`, `MainDispatcherRule`,
a collector in `backgroundScope` before asserting on a `stateIn(WhileSubscribed)` flow,
virtual time only, `kotlin.test`, **no Robolectric**, **no unit test for a framework entry
point** (`FirebaseMessagingService`, worker shell, activity).

### 7. Run the release-readiness gate and report

Run the six-element gate of `spec/android/release-readiness/` §E: `./gradlew build` green; lint
error-free on changed code, no new baseline entry; unit tests green; release variant assembles
with the shrinker on; the touched flow exercised on a device from the **release** variant; every
§B item true of that variant (incl. `debuggable` false, no TLS trust weakened). Then the
acceptance criteria of that spec a feature change can break (checklist §8):
**process death** survived without losing input or unsent writes (*Don't keep activities* or a
background kill, not inspection); **no empty `catch`**; specific, correctly located **keep
rules**; **`mapping.txt` retained**; the §G grep of `spec/android/backend-contract/` clean;
instrumented and screenshot lanes where UI changed (SHOULD — say so when skipped); size delta
and likely startup/scroll regressions.

Route a red build or runtime defect to `android-debugging`. Report, in the operator's
language: files written; the four step-3 decisions and where they live; every `BR-<n>` and its
status; each gate element and criterion green, red, unrunnable, or skipped — **and why**; any
spec gap (REQ-1, REQ-7).

## Reference files

- Read `references/flat-layer-checklist.md` before step 2 — placement test, state model, cache
  and writes, failure mapping, tests, gate, delivery path.
- Read `references/backend-requirement-template.md` in step 4 — the nine-section artifact.
- Read `references/layer-templates.md` in step 5 — result type, repository, sync worker,
  delivery path, ViewModel — and in step 6 for the fake and test-rule shapes.

## Resumability

Per `spec/claude/resumable-work/`, this skill is `resumable: true`. State is persisted to
`.resume/android-feature-implement/<run-id>.yml` after every gate and named step boundary. On
re-invocation, scan `.resume/android-feature-implement/*.yml` for `status: in_progress` files
whose `inputs:` snapshot (repository + feature name) matches; on a match prompt
`Resume run <run_id> from phase <phase> (last checkpoint <last_checkpoint_at>)? [resume / start-new / discard]`.
`resume` re-hydrates and re-asks no answered gate; `start-new` leaves the old file intact;
`discard` deletes it. Fail closed on unparseable or higher-`schema_version` files; envelope
keys and lifecycle live in the spec.

## Hard rules

- **Never** compute a domain decision on the device — acceptance, permission, status,
  eligibility, price, quota, derived label (`spec/android/app-architecture/` §A); never work
  around a missing backend capability without a `BR-<n>` artifact and an agreed interim path
  (`spec/android/backend-contract/` §E).
- **Never** let a generated type, HTTP status, or storage type cross the repository boundary;
  never hand-write a DTO that duplicates a published schema (§A); never introduce a domain
  layer or a pass-through use case; never start network or database work from composition
  (`spec/android/app-architecture/` §E/§F).
- **Never** collapse failures into a generic error — all eight §B cases handled, a contract
  mismatch never lumped with rejections; never log a body, credential, or personal data
  (`spec/android/security/` §A).
- **Never** auto-retry a `POST`/`PATCH` without an honoured idempotency key, and never retry
  without capped exponential backoff, jitter, a maximum attempt count, and a deadline (§C).
- **Never** drop a failed write silently, show cached content the screen cannot mark as cached,
  lose user input on rejection or process death, or let a client-side check pose as acceptance
  (`spec/android/user-input-validation/` §A/§B).
- **Never** post a notification without a ledger row, for a **point event** on the surface the
  user is looking at, or for an event routed in-app; never choose a channel by analogy
  (`spec/android/notifications-alerting/` §B/§C).
- **Never** treat a push as guaranteed delivery or as the source of truth, never work inside
  `onMessageReceived()` — enqueue — and never route a tap through a service or receiver
  trampoline; the `PendingIntent` is immutable, explicit, and targets the activity
  (`spec/android/notifications-alerting/` §E, `spec/android/security/` §D).
- **Never** send a one-off event from the ViewModel to the UI, hold a `Context` there, or run
  IO on the main thread; never assume JUnit 5 or use Robolectric in a pure unit test
  (`spec/android/test-automation/` §B).
- **Never** declare the work done from a debug build, never add a lint baseline entry,
  suppression, or check disablement to pass the gate (`spec/android/release-readiness/` §A/§E),
  and never overwrite a file or open an issue elsewhere without explicit confirmation (REQ-8).
- **Always** record the four step-3 decisions and raised backend gaps in the feature's
  requirement or feature file (`spec/android/app-architecture/` §H), and end with the §E gate,
  the process-death check, and an explicit report of every red, unrunnable, or skipped element
  (REQ-7). When a spec disagrees with this skill, the spec wins (REQ-6).

## Gotchas

- **The official architecture guide says the data layer holds "the vast majority of your app's
  business logic".** That addresses apps that own their domain; this corpus narrows it to
  caching, sync, retry, and mapping (`spec/android/app-architecture/` §A).
- **Offline-capable is not the opposite of flat.** The local store is what the UI *observes*;
  the backend *decides*. A local-first write is a UX commitment, not a convenience.
- **`WhileSubscribed(5_000)` is not decoration**, and a test on it without a collector reads
  the initial value forever — launch one in `backgroundScope` first.
- **R8 failures are invisible until the release build runs**; `enumUnknownDefaultCase=true`
  supplies the fallback member an unknown enum value needs.
- **`Result.retry()` cannot honour `Retry-After`** — honour it inside the drain
  (`references/layer-templates.md` §4). **An FCM notification message never runs your code in
  the background** — anything the app must control is a data message. **"Don't keep
  activities" is the only honest process-death test** — rotation covers configuration only.
