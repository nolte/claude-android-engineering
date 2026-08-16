---
name: android-feature-implement
description: "Implements a feature in a Kotlin Android app across its layers as a flat, server-authoritative view layer per spec/android/app-architecture/: the backend decides, the local replica is what the UI observes, no domain rule runs on the device. Designs the screen state model (loading, content, empty, error, stale, pending write), the repository and data-source layer, the per-write strategy and staleness policy, and the eight-case failure handling of spec/android/backend-contract/. Captures every missing backend capability as a handoff artifact in project/backend-requirements/ with an OpenAPI proposal for a backend specialist, instead of working around it. Closes with the release-readiness gate: R8 release build, lint, tests, device smoke. Invoke when the user asks to implement an Android feature, wire a screen to an API, add offline support, or produce production-grade app code. Also handles equivalent German-language requests. Supports resume on re-invocation."
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
see_also:
  - android-compose-ui
  - android-permissions-derive
  - android-project-scaffold
  - android-debugging
resumable: true
---

# Android Feature Implement

Implements a feature in an existing native Kotlin Android app across every layer it touches,
under one governing constraint: the app is a **flat view layer**. The backend is the authority
for every domain decision, the local replica is what the UI observes, and anything the contract
cannot answer becomes a recorded requirement for the backend side — never a rule quietly
implemented on the device.

The authoritative rules live in `spec/android/`; this skill operationalizes them and never
restates or contradicts them. On any conflict the spec wins — report the gap and propose a spec
change rather than deciding silently (REQ-6).

Grounding specs, in the order they bind this skill: `spec/android/app-architecture/` (what the
device may decide, state model, cache, writes), `spec/android/backend-contract/` (contract
consumption, the closed outcome set, when and how a backend requirement is raised),
`spec/android/release-readiness/` (what "done" means),
`spec/android/user-input-validation/` (how a value is taken from the user, judged, and answered
— the four-stage chain whose fourth stage is the backend decision above), and
`spec/android/notifications-alerting/` (which channel, if any, an event the feature produces
gets), plus `spec/android/project-structure/`, `spec/android/test-automation/`, and
`spec/android/security/` for structure, tests, and obligations.

## Why this is a skill, not an agent

- **Mid-flow approval is the contract.** The design gate (state model, write strategy,
  staleness policy), the backend-requirement gate, and every file overwrite need explicit
  operator consent (REQ-8); an agent's fire-and-forget shape cannot carry those gates.
- **The output belongs in the main conversation.** Kotlin, tests, and the requirement artifact
  land in the working tree and are reviewed in context, not behind a structured-report boundary.
- **It dispatches other capabilities.** The UI step routes through `android-compose-ui` and a
  red build routes to `android-debugging`; per `spec/claude/skill-vs-agent/` §Primary decision
  rule the orchestrator is always a skill.
- Counter-dimension considered: the backend-gap analysis alone (reading the contract, the
  network component, and the existing repositories) would benefit from an agent's
  context-window isolation, but it sits mid-flow between two approval gates, so splitting it
  out would break the interaction it depends on.

## Boundary vs the sibling capabilities

- `android-compose-ui` **authors the UI surface** of a screen (REQ-13). This skill owns the
  feature across layers and **calls that skill for the UI step** rather than duplicating it. A
  request that is purely "build this screen" belongs there, not here.
- `android-ux-reviewer` reviews existing UI read-only (REQ-14); it never writes.
- `android-project-scaffold` creates the project (REQ-12); this skill requires one to exist.
- `android-debugging` diagnoses build failures and runtime defects (REQ-16); route a red state
  there instead of guessing.
- `android-permissions-derive` owns every permission decision (REQ-20). When step 2 classifies
  something as **device capability** and that capability may need a permission, hand the
  decision there instead of declaring one here — it derives the set, records the ledger row, and
  writes the declaration and the denial path.
- `android-notification-derive` owns every alerting-channel decision (REQ-21) and the notification
  ledger, the same way `android-permissions-derive` owns permissions. It does not exist yet; until
  it does, step 3 runs its derivation here as a marked interim and hands the resulting permissions
  on as above.
- `android-barcode-scanner-scaffold` and `android-perceived-performance` own their capabilities;
  when a feature needs scanning or a performance remediation, hand that part to them.

## User-language policy

Detect the operator's language and respond in it (German for this operator). Generated
artifacts stay canonical: Kotlin, identifiers, and code comments in English; user-visible copy
externalized to `strings.xml` (English source, German translation) per
`spec/android/localization/` §A. The backend-requirement artifact is written in English, since
its reader is a backend specialist in another repository.

## Preconditions

Before writing anything:

- Confirm the working directory is a git repository holding an Android project scaffolded per
  `spec/android/project-structure/`. If there is no Gradle Android module, stop and route to
  `android-project-scaffold`.
- Read `references/flat-layer-checklist.md` in full — it is the implementation-time rule set
  distilled from the three grounding specs, and every produced layer is checked against it.
- Locate the contract surface: the committed OpenAPI document (or the generated network
  component). Record its version. If none exists, note it — per
  `spec/android/backend-contract/` §A that absence is itself a backend requirement.
- Check for uncommitted changes in the paths to be touched. If dirty, report and ask whether to
  stash, commit, or abort — never overwrite unconfirmed work (REQ-8).

## Implementation procedure

Run the steps in order, once per feature. Confirm with the operator at each gate before writing.

### 1. Establish the feature contract

Restate the feature in one sentence as an outcome for the user, then agree: the screens
touched, the data types involved, the writes the user can perform, and the states each screen
must be able to show. Where a requirement artifact or feature file exists in the repository,
read it first and work from it rather than re-eliciting. Gate: confirm the restatement before
designing anything.

### 2. Apply the flat-layer test

For every rule the feature seems to need, decide where it lives, using
`spec/android/app-architecture/` §A: presentation, cache/sync policy, device capability, and
navigation state are the only four classes the device may own. Anything else is the backend's.
Produce an explicit list: *device-owned* items with their class, and *backend-owned* items with
what the contract already supplies for each. Every backend-owned item the contract does **not**
supply goes into step 4 — do not silently plan a client-side derivation. Every *device
capability* item that may need a permission goes to `android-permissions-derive` before any
manifest edit; a permission declared here without that derivation is a REQ-20 violation. Gate:
confirm the split.

### 3. Design the state and data model

Decide and record, per `references/flat-layer-checklist.md`:

- the screen state model — loading, content, empty, error with recovery action, and, wherever
  the screen can be served from cache, **staleness** and **pending write**
- the repository and data-source shape, the three model sets (network DTO, local entity, UI
  model), and their mappers
- the staleness policy per cached type (revalidation window, stale-while-revalidate, hard
  expiry behaviour)
- the write strategy per write — online-only, queued, or local-first — defaulting to
  online-only wherever the backend decides acceptance, with the pending/rollback/conflict
  answers spelled out for anything else
- for every value the feature takes from the user, which of the four stages of
  `spec/android/user-input-validation/` §A owns each check — and specifically which checks are
  *not* client-side, because the backend owns them. Field-check parameters (required, length,
  range, allowed values) come from the contract; a limit the contract does not state is a
  backend requirement in step 4, not an invented constant
- for every event the feature produces that a user might need to know about, the channel and its
  row in `project/notification-ledger.md` — obtained by handing the event to
  `android-notification-derive` (REQ-21), which owns the gate chain of
  `spec/android/notifications-alerting/` §C exactly as `android-permissions-derive` owns every
  permission decision. **Interim while that skill does not exist:** run its §B classification and
  §C chain here and record the row, but keep the outcome in the ledger rather than growing a
  second implementation of the chain in this skill. Either way a notification posted without a
  ledger row is non-conformant, and any permission the chosen channel implies goes to
  `android-permissions-derive` before any manifest edit

Gate: confirm the design before generating code. These four decisions are recorded with the
feature per `spec/android/app-architecture/` §H.

### 4. Capture backend requirements

Walk the §E trigger list of `spec/android/backend-contract/` against the feature. For each
trigger that fires, read `references/backend-requirement-template.md` and write
`project/backend-requirements/<YYYY-MM-DD>-<slug>.md` with all nine sections, a stable `BR-<n>`
identifier, an OpenAPI fragment marked as a proposal, and synthetic examples only. Then agree
the interim client behaviour with the operator — wait, ship without the affected part, or a
time-boxed interim path recorded in the artifact. Gate: confirm the artifact and the interim
choice; opening an issue in the backend repository happens only on explicit confirmation
(REQ-8). Never proceed by implementing the missing capability on the device.

### 5. Implement, bottom-up

Write the data layer first, then the state holder, then the UI:

1. **Data source and mapping** — generated types stay inside the network component; the DTO is
   mapped at the boundary. Local entities and DAOs stay below the repository.
2. **Repository** — reads as `Flow` from the local replica, writes as `suspend`; freshness
   metadata stored; the eight outcome cases of `spec/android/backend-contract/` §B mapped into
   the app's own result type; timeouts explicit; retries only where the request is idempotent
   or carries an idempotency key.
3. **Sync** — queued or local-first drains run in WorkManager unique work with a connectivity
   constraint and backoff; never in `viewModelScope`.
4. **ViewModel** — a single `uiState` `StateFlow` built with
   `stateIn(..., WhileSubscribed(5_000), ...)`, no ViewModel→UI event channel, no lifecycle-bound
   type held, injected dispatchers and clock.
5. **UI** — invoke the `android-compose-ui` skill for the screen or component so the UX,
   theming, adaptivity, localization, and accessibility rules are applied by their owner; hand
   it the state model from step 3. Only wire the route to the ViewModel here.

Gate: confirm before each file that would overwrite existing code (REQ-8).

### 6. Test the states that only exist because the client is flat

Add JVM tests per `spec/android/test-automation/` §B/§C with fakes, covering: every one of the
eight outcome cases the feature can hit, the stale state, the pending-write state, and the
recovery action on each error. Where the feature takes input, add the paths of
`spec/android/user-input-validation/` §H: a field-identified domain rejection lands on its field
with the entered values preserved, and the restoration path is asserted rather than assumed. Time and dispatchers are injected, never slept on. A feature
whose offline and rejection paths are untested is not implemented, only demonstrated.

### 7. Run the release-readiness gate and report

Run the six-element gate of `spec/android/release-readiness/` §E: `./gradlew build` green; lint
error-free on changed code with no new baseline entry; unit tests green; the release variant
assembles with the shrinker on; the touched flow exercised manually on a device from the
**release** variant; and every §B item true of that variant. Route a red build or a runtime
defect to `android-debugging` rather than guessing. Report, in the operator's language: the
files written, the four recorded decisions from step 3, every `BR-<n>` raised and its status,
each gate element that was green, red, or unrunnable and why, and any spec gap found. Never
leave a red or skipped element unreported (REQ-1, REQ-7).

## Reference files

- Read `references/flat-layer-checklist.md` before step 2 for the implementation-time rule set
  (what the device may decide, state model, cache and writes, failure mapping, gate).
- Read `references/backend-requirement-template.md` in step 4 for the nine-section artifact and
  its OpenAPI-fragment shape.
- Read `references/layer-templates.md` in step 5 for the result type, repository, sync worker,
  and ViewModel templates.

## Resumability

Per `spec/claude/resumable-work/`, this skill is `resumable: true`. State is persisted to
`.resume/android-feature-implement/<run-id>.yml` after every gate and at each named step
boundary. On re-invocation, scan `.resume/android-feature-implement/*.yml` for files with
`status: in_progress` whose `inputs:` snapshot (repository + feature name) matches the current
request; when one matches, prompt
`Resume run <run_id> from phase <phase> (last checkpoint <last_checkpoint_at>)? [resume / start-new / discard]`.
`resume` re-hydrates and re-asks no answered gate; `start-new` leaves the old file intact;
`discard` deletes it. Fail closed on unparseable or higher-`schema_version` files. The envelope
keys and lifecycle are load-bearing in the spec and are not duplicated here.

## Hard rules

- **Never** compute a domain decision on the device — acceptance, permission, status,
  eligibility, price, quota, or a derived label. Client-side input checks are assistance only
  and never override the server's answer (`spec/android/app-architecture/` §A).
- **Never** work around a missing backend capability in the client without a `BR-<n>` artifact
  and an operator-agreed interim path (`spec/android/backend-contract/` §E).
- **Never** let a generated wire type, HTTP status, or storage type cross the repository
  boundary.
- **Never** collapse failures into a generic error: all eight cases of
  `spec/android/backend-contract/` §B are distinguished and handled, and a contract mismatch is
  reported as a contract defect.
- **Never** log a request or response body, a credential, or personal data — a failure log
  names endpoint, status, and error class only (`spec/android/security/` §A).
- **Never** auto-retry a `POST` or `PATCH` without an idempotency key the backend honours.
- **Never** drop a failed write silently, and never show cached content without the screen
  being able to say it is cached.
- **Never** lose what the user entered on a rejection, a failed submission, or process death,
  and never let a client-side check present itself as the acceptance decision
  (`spec/android/user-input-validation/` §A/§B).
- **Never** post a notification for an event that has no ledger row, that the user is currently
  looking at, or that the gate chain routed to the in-app path — and never choose a channel by
  analogy when the chain reaches its gap gate (`spec/android/notifications-alerting/` §B/§C).
- **Never** send a one-off event from the ViewModel to the UI, hold a `Context` in a ViewModel,
  or run IO on the main thread.
- **Never** declare the work done from a debug build, and never add a lint baseline entry,
  suppression, or check disablement to pass the gate on new code
  (`spec/android/release-readiness/` §A/§E).
- **Never** overwrite an existing file, or open an issue in another repository, without explicit
  confirmation (REQ-8).
- **Always** record the write strategy, staleness policy, and raised backend gaps with the
  feature (`spec/android/app-architecture/` §H).
- **Always** end with the §E gate and an explicit report of every red or unrunnable element
  (REQ-7).
- When a spec under `spec/android/` disagrees with this skill, the spec wins — report the gap
  and propose a spec change (REQ-6).

## Gotchas

Concrete corrections to non-obvious facts the executing agent would otherwise get wrong:

- **The official architecture guide says the data layer holds "the vast majority of your app's
  business logic".** That guidance addresses apps that own their domain. This corpus narrows it
  deliberately: the client data layer holds caching, sync, retry, and mapping only
  (`spec/android/app-architecture/` §A, "Calibrated deviation"). Do not cite the guide against
  the flat rule.
- **Offline-capable is not the opposite of flat.** The local store is the SSOT the UI
  *observes*; the backend stays the authority that *decides*. Both statements are true at once,
  and conflating them is how a second implementation of the domain gets written.
- **A local-first write is a UX commitment, not a convenience.** It requires a visible pending
  state, a designed rollback when the backend rejects it, and a conflict answer from the
  backend. When the feature will not pay for those, the write is online-only.
- **`WhileSubscribed(5_000)` is not decoration.** Without it, a rotation tears down and restarts
  the upstream flow; with a plain `Lazily`/`Eagerly` the collection outlives the screen.
- **R8 failures are invisible until the release build runs.** Reflection- and
  serialization-based breakage appears only there, which is why the gate installs the release
  variant rather than trusting a green debug build.
- **An unknown enum value is a normal event, not an error.** Contracts grow; a missing fallback
  member turns an additive backend change into a crash on an already-shipped app.
