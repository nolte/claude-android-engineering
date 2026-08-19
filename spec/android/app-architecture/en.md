# App Architecture — The Flat View Layer

Status: draft

## Context

An Android app that belongs to a backend has one architectural question that outranks every other: *who decides*. The answer this corpus fixes is the backend — the app is a **flat view layer**. It renders what the backend states, it collects what the user enters, and it holds a local copy so it stays usable when the network is not. It does not re-derive the backend's rules, and it does not become a second, quietly diverging implementation of the domain.

Three things are routinely conflated and are kept apart throughout this spec:

- **Authority** — who decides whether something is true, allowed, or accepted. Always the backend.
- **Source of truth for rendering** — what the UI observes. Always the local store, because a screen that reads directly from the network stops working the moment the network does.
- **Rendering** — Compose, which owns no decision at all.

An app can be offline-capable and still be flat: the local database is a *replica*, not a second opinion. The failure mode this spec exists to prevent is the drift that starts with one innocent client-side rule ("we can already tell this order is not eligible") and ends with a client that contradicts the server in front of the user.

Provenance: desk research (August 2026) over the official Android architecture guide and its tiered architecture recommendations (*Strongly recommended* / *Recommended* / *Optional*), the offline-first data-layer guide, the ViewModel and lifecycle-aware collection documentation, the WorkManager guidance, and the Now in Android reference implementation. Where this spec departs from official guidance it says so and states why — see §A. Citation depth: every requirement below rests on first-party platform documentation, which for a vendor's own API is the authoritative source rather than one voice among three; this corpus applies that convention uniformly, and a requirement resting on anything less settled than shipped, documented behaviour is required to say so at the requirement itself.

Boundaries: the *structural* imprint of architecture — module and package layout, repository and data-source naming, constructor injection and Hilt, the route/content composable split, test placement — is owned by `spec/android/project-structure/` §C–§F and is not restated here; that spec explicitly defers runtime architecture behaviour to a spec of its own, and this is it. Navigation architecture and back behaviour belong to `spec/android/app-design-navigation/` §B/§D, list and paging behaviour to `spec/android/long-list-scrolling/`, everything about the wire contract and about raising a requirement against the backend to `spec/android/backend-contract/`, storage and privacy obligations of the cache to `spec/android/security/` §A/§E, test mechanics to `spec/android/test-automation/`, and release-build hardening to `spec/android/release-readiness/`.

Readers: authors of this repository's Android skills who implement a feature across layers, and reviewers judging whether a feature kept the client flat.

## Goals

- Fix a mechanical rule for what may be decided on the device and what may not
- Make the app usable offline without letting the local copy become a second authority
- Give every screen a state model that can express *stale*, *pending*, and *rejected* — the three states a flat client cannot avoid
- Make every write's failure path a designed part of the feature rather than an afterthought
- Keep the generated wire types and the storage engine out of the UI layer, so both stay replaceable
- Make every layer testable on the JVM, without a device and without a backend
- Turn a missing backend capability into a recorded requirement instead of a client-side workaround

## Non-Goals

- Module boundaries, package layout, naming conventions, DI wiring, and the route/content split — `spec/android/project-structure/` §C–§F
- Navigation graphs, back handling, deep links — `spec/android/app-design-navigation/` §B/§D/§E
- Paging mechanics, list identity, and scroll continuity — `spec/android/long-list-scrolling/`
- The HTTP contract, the generated client, error payload formats, and the backend-requirement artifact — `spec/android/backend-contract/`
- Encryption of cached data, permission policy, and log hygiene as security obligations — `spec/android/security/`
- Backend architecture itself; this spec only states what the client requires of it
- Apps with no backend at all — a purely local app inherits §B, §C, §E, and §G, and §A/§D do not apply

## Requirements

### A. The flat rule — what the device may decide

- **MUST** treat the backend as the authority for every domain decision: whether an input is acceptable, whether an action is permitted, what a status, price, eligibility, quota, or derived label is, and when a workflow may advance. The client renders those answers; it does not compute them
- **MUST** confine client-owned logic to exactly four classes, and **MUST** report anything that fits none of them as a gap per `spec/android/backend-contract/` §E rather than deciding silently:
  1. **presentation** — mapping backend data to what is drawn, formatting, sorting and filtering of already-delivered data for display — *within* a fully delivered set (a complete page, a complete list the client holds); a sort or filter that would force the client to over-fetch, or that must span pages it does not hold, is `spec/android/backend-contract/` §E, not presentation
  2. **cache and sync policy** — what is stored, when it is revalidated, how a write is retried
  3. **device capability** — camera, sensors, permissions, connectivity, file access, background execution
  4. **navigation and UI state** — which screen is shown, what is selected, what is expanded
- **MUST** place the recurring "where does this live" cases in these homes, so a skill applies the assignment instead of deciding it silently:
  - **local draft and form persistence** (an unsent form, a half-typed entry) — class 4 while the screen lives, class 2 once it must survive process death; stored locally as *unsent input*, never as domain data in the replica, and restored per §B's process-death rule
  - **feature flags and remote config** — backend-delivered values the client caches like any other data (class 2) and branches on for what it draws (class 1); a flag whose value decides eligibility, entitlement, or pricing is a domain decision the backend evaluates and delivers as a *result*, not a rule the client evaluates
  - **analytics and telemetry** — collection, batching, and dispatch are device-capability work (class 3); the client records events, never derives a business metric on the device, and the privacy obligations of what is recorded follow `spec/android/security/` §E
  - **client-version gating** ("this app is too old") — a backend decision delivered on the wire (`spec/android/backend-contract/` §B maps the unsupported-version response); the client renders the block and the update action and never compares its own version against a locally held rule
  - **presentation aggregates vs. business aggregates** — a footer sum, count, or "n of m" over the items the screen was *delivered* is presentation (class 1); a total, balance, or count that spans data the client does not hold, or that a rule could adjust (discounts, quotas), is a business aggregate the client asks the backend for
- **MUST** treat client-side input checks as *assistance only* — required-field marks, format hints, keyboard types, length caps drawn from the contract. Assistance **MUST NOT** be presented to the user as an acceptance decision, and the server's answer **MUST** win even when the client believed the input was fine
- **MUST NOT** re-implement, mirror, or pre-compute a backend rule "for a faster UI"; when a derived value is needed for rendering, the client asks for the field (`spec/android/backend-contract/` §E) instead of deriving it
- **MUST NOT** persist a locally-derived domain decision as if it were backend truth — a value the client computed is never written into the replica alongside server-provided data without being marked as unconfirmed
- **MUST** model a server rejection as a first-class UI state that names what to do next, never as a raw exception surfaced in a dialog (message rules per `spec/android/app-design-navigation/` §F)
- **Calibrated deviation:** the official architecture *recommendations* state — at the *Strongly recommended* tier — that the data layer "contains the vast majority of your app's business logic" [R2], and the architecture guide frames the layer the same way [R1]. That statement addresses apps that own their domain. In this corpus the domain lives in the backend, so the client data layer holds **client** logic only — caching, sync, retry, and mapping. The guide's layering, its SSOT and UDF principles, and its recommendations are adopted unchanged; only the *placement of domain rules* is narrowed, and a skill **MUST** apply this narrower rule

### B. UI layer and state

- **MUST** follow unidirectional data flow: the ViewModel exposes state through the observer pattern and receives user intent as method calls [R2]
- **MUST** expose screen state as a single `uiState` property of type `StateFlow` (several properties only for genuinely unrelated data), built with `stateIn(scope, SharingStarted.WhileSubscribed(5_000), initial)` when it derives from a data-layer stream, and collect it with `collectAsStateWithLifecycle()` [R2]
- **MUST NOT** send one-off events from the ViewModel to the UI; the event is handled in the ViewModel and its result becomes state [R2]
- **MUST** model screen state so it can express, per screen, all of: **loading**, **content**, **error with a recovery action**, **empty**, and — because the client is flat and offline-capable — **staleness** (this content is a cached copy of age *t*) and **pending write** (this content includes a change the backend has not confirmed). A **server rejection** is one shape of the error state, not a separate one: it names the rule that refused and what to do next. A screen that can be shown from cache but has no way to say so is non-conformant
- **MUST** keep the ViewModel free of `Activity`, `Context`, `Resources`, and any lifecycle-bound type, and **MUST NOT** use `AndroidViewModel` — a calibrated tightening: the recommendations page lists "Do not use `AndroidViewModel`" at the *Recommended* tier, and this corpus raises it to MUST because the flat client resolves every `Context`-dependent value in the composable [R2]; user-facing text is resolved in the composable from string resources per `spec/android/localization/` §A
- **MUST** place ViewModels at screen level only; reusable components take hoisted state and plain state-holder classes [R2]
- **MUST NOT** put a decision in a composable beyond choosing what to draw from the state it was given — no data access, no rule evaluation, no request triggering outside an effect
- **MUST** drive lifecycle-dependent work with lifecycle-aware effects (`LifecycleStartEffect`, `LifecycleResumeEffect`, `repeatOnLifecycle`) rather than overridden `Activity` callbacks [R2]
- **MUST** survive process death: any state the user would be annoyed to lose is restored from `SavedStateHandle` (ViewModel) or `rememberSaveable` (UI), and the restored screen **MUST NOT** silently discard an unsent write

### C. Data layer — the replica the UI observes

- **MUST** have the UI layer read exclusively through repositories; composables and ViewModels never touch a database, DataStore, network client, or system data provider directly [R2]
- **MUST** make the local store the single source of truth the UI observes, and the backend the authority it is reconciled against; a repository read **MUST NOT** depend on a network round trip succeeding
- **MUST** keep three model sets apart — network DTO, local entity, and the model exposed to the UI layer — with mapping functions at each boundary [R3]; the generated wire types **MUST NOT** appear in a repository's public signature
- **MUST** expose reads as `Flow` and writes as `suspend` functions [R3]
- **MUST** store freshness metadata with every cached data type (fetched-at timestamp, and the contract's own validator — ETag, version, or sync token — where one exists), because staleness cannot be displayed or revalidated without it
- **MUST** declare, per cached data type, a staleness policy naming three things: the revalidation window, whether stale content is shown while revalidating, and what the UI shows once the data is past hard expiry. "Cache forever, never say so" is non-conformant
- **MUST** delete or re-key all user-scoped cached data on sign-out and on account switch; storage obligations for that data follow `spec/android/security/` §A
- **SHOULD** choose the local store by shape: a relational or queryable replica in Room, small scalar preferences in DataStore, large binaries as files with a row referencing them — and **MUST NOT** use `SharedPreferences` for new code
- **MUST** handle a read error from the local store by emitting a safe state (`catch` into an error or empty state), never by letting the exception cancel the UI's collection [R3]

### D. Writes and synchronization

- **MUST** choose, per write, exactly one of three strategies and record the choice with the feature [R3]:
  - **online-only** — the write goes to the backend and is only then reflected locally; offline, the affordance is disabled with a stated reason
  - **queued** — the write is recorded locally and drained later; the user is not blocked and failure is tolerable
  - **local-first (lazy)** — the write is applied to the replica immediately, queued, and reconciled on sync
- **MUST** default to **online-only** for any write whose acceptance depends on a backend rule — which, under §A, is most of them. Local-first is chosen only when the feature explicitly pays for its cost: a visible pending state, a designed rollback when the backend rejects the change, and a conflict answer from §D below
- **MUST** perform queued and local-first drains with WorkManager unique work under a connectivity constraint with exponential backoff [R3] — WorkManager's floor is `WorkRequest.MIN_BACKOFF_MILLIS` (10 s; the default is 30 s exponential), so a drain never retries faster than that, and a write that needs sub-10-second retry is not WorkManager work but an in-process retry within `spec/android/backend-contract/` §C [R9]; a retry loop tied to `viewModelScope` is non-conformant for work that must outlive the screen
- **MUST** make every unconfirmed write visible in the UI (pending) and every permanently failed write actionable (retry, edit, discard) — a write **MUST NOT** be dropped silently, and its failure **MUST NOT** be reported only in a log
- **MUST** obtain conflict resolution from the backend: the client sends the validator it holds (version, ETag, or timestamp) and renders the backend's verdict. The client **MUST NOT** invent a merge, and **MUST NOT** silently overwrite a newer server state with an older local one [R3]
- **MUST** make any automatically retried write idempotent-safe on the wire per `spec/android/backend-contract/` §C; where the backend offers no such mechanism, automatic retry of that write is forbidden until the requirement is raised and answered
- **MUST** define, per synced data area, what a server-side deletion and a broken sync position do to the replica, and name both in the staleness policy of §C: a `404`/`410` on refresh of an item the replica holds (`spec/android/backend-contract/` §B) removes or tombstones that row and its screen shows "no longer available" rather than an error; a sync token or validator the backend rejects as unknown or invalid triggers a **full resync** of that data area — the replica is replaced, not merged — with the UI showing the stale copy meanwhile only if the policy allows it
- **SHOULD** prefer one scheduled reconciliation entry point (a sync worker per data area) over per-screen ad-hoc refreshes, so freshness is a property of the replica rather than of whichever screen was opened last

### E. Threading and execution

- **MUST** communicate between layers with coroutines and flows [R2]
- **MUST** inject dispatchers rather than referencing `Dispatchers.*` inside a class that is under test, and **MUST** perform IO on an IO dispatcher — never on the main thread (verified in debug per `spec/android/release-readiness/` §B)
- **MUST** scope work to its lifetime: `viewModelScope` for screen-bound work, an application-scoped coroutine scope for fire-and-forget work that must finish after the screen leaves, and WorkManager for work that must survive process death
- **MUST NOT** start network or database work directly from composition; requests are triggered from state collection, an effect, or a user-intent callback

### F. Keeping the layers replaceable

- **MUST** keep the generated or hand-written HTTP client behind the repository boundary; nothing above it imports a generated type, an HTTP status, or a serialization annotation
- **MUST** keep storage types (Room entities, DAOs, DataStore keys) below the same boundary
- **MUST NOT** introduce a domain layer to host rules that belong to the backend; use cases exist only to reuse *client* orchestration across ViewModels, and trivial pass-through use cases stay forbidden per `spec/android/project-structure/` §E
- **SHOULD** keep feature packages free of dependencies on other feature packages; data shared across features moves to a core/data component

### G. Testability

- **MUST** make every layer exercisable on the JVM without a device and without a live backend: ViewModel state tests over a fake repository, repository tests over fake data sources, mapper tests over fixtures. Mechanics, placement, and the fakes-over-mocks rule are owned by `spec/android/test-automation/` §B/§C
- **MUST** provide, for every remote data source, a fake that can produce **every** case of the closed set defined in `spec/android/backend-contract/` §B — success, offline, timeout, unauthenticated, unauthorized, domain rejection (a conflict is one of its shapes), server fault, and contract mismatch. Subsetting that list is non-conformant: the two authentication cases are the ones a hand-written fake set omits by habit, and they are the ones whose UI answer differs most
- **MUST** keep time injectable wherever staleness, expiry, or backoff is computed — a test that has to sleep is a design defect
- **MUST** cover, for every screen that can be shown from cache, at least the stale and the pending-write states; these are the states that only exist because the client is flat and are therefore the ones nobody writes by habit

### H. Recording the decisions

- **MUST** record, for each implemented feature, the write strategy per write (§D), the staleness policy per cached type (§C), and any backend gap raised (`spec/android/backend-contract/` §E–§F). The record lives with the feature — its requirement or feature file — not only in a commit message
- **MUST**, when a case is not covered by this spec, report the gap and propose a spec extension rather than deciding silently (repository REQ-6)

## Acceptance Criteria

The criteria are a representative rollup of §A–§H, not a 1:1 mapping; every requirement bullet above is normative on its own.

- [ ] No domain decision (acceptance, permission, status, eligibility, derived label) is computed on the device; client-side input checks exist only as assistance and never override the server's answer
- [ ] Every piece of client-owned logic falls into one of the four classes of §A, and anything that fits none of them was reported as a gap rather than implemented; drafts, feature flags, telemetry, version gating, and aggregates sit in the homes §A assigns, and no client-side sort or filter forces an over-fetch
- [ ] No composable performs data access, evaluates a rule, or triggers a request outside an effect; lifecycle-dependent work uses lifecycle-aware effects rather than overridden `Activity` callbacks, and no network or database work starts from composition
- [ ] Every ViewModel exposes a single `uiState` `StateFlow`, collected with `collectAsStateWithLifecycle`, with no ViewModel→UI event channel and no lifecycle-bound type held
- [ ] Every screen state can express loading, content, empty, error-with-action, staleness, and pending write; a cache-backed screen shows its staleness
- [ ] The UI never touches a data source; every read goes through a repository, reads are `Flow`, writes are `suspend`
- [ ] Network DTOs, local entities, and UI models are separate types with explicit mappers; no generated wire type or storage type appears above the repository boundary
- [ ] Every cached data type carries freshness metadata and a declared staleness policy that also names the server-deletion and full-resync behaviour; user-scoped cached data is cleared on sign-out and account switch
- [ ] Every write names one of the three strategies; non-online-only writes drain through WorkManager with a connectivity constraint and backoff, are visible while pending, and are actionable when permanently failed
- [ ] No client-side merge exists; conflicts are resolved by the backend against a validator the client sends, and automatic retry exists only where the wire contract makes the write idempotent-safe
- [ ] Dispatchers and time are injected; no IO runs on the main thread; work that must survive process death runs in WorkManager
- [ ] A restored screen (process death, configuration change) loses neither user input nor an unsent write
- [ ] Every layer has JVM tests with fakes covering the full closed set of failure modes, including the stale and pending-write screen states
- [ ] Write strategy, staleness policy, and raised backend gaps are recorded with the feature

## Open Questions

Each question states the working default the requirements above already encode.

- Should the "unconfirmed write" and "stale content" indicators be standardized as shared components in the design system (a `spec/android/ui-components/` extension), or stay per-screen? Default: per-screen, with §B fixing only that the state exists
- Should a repository expose a single `Result`-shaped read that folds the closed error set, or keep separate content and error streams? Default: unfixed — §B fixes the *state model*, not the transport of errors between layers
- Is Room warranted for a replica of only a handful of records, or is a DataStore-serialized snapshot sufficient? Default: §C's shape rule decides; no size threshold is fixed
- Should an app that is offline-capable be required to run a periodic background sync, or only sync on foreground entry? Default: not fixed; §D requires only a single reconciliation entry point per data area

## References

- [R1] Guide to app architecture — separation of concerns, drive UI from data models, SSOT, UDF, layer responsibilities: <https://developer.android.com/topic/architecture>
- [R2] Architecture recommendations (Strongly recommended / Recommended / Optional tiers) — data layer holds "the vast majority of your app's business logic" (Strongly recommended), "Do not use `AndroidViewModel`" (Recommended), UDF, `uiState`/`StateFlow`/`WhileSubscribed(5000)`, `collectAsStateWithLifecycle`, no VM→UI events, screen-level ViewModels, lifecycle-aware effects, DI, testing: <https://developer.android.com/topic/architecture/recommendations>
- [R3] Build an offline-first app — local source of truth, model separation, read/write strategies (online-only, queued, lazy), conflict resolution, WorkManager sync: <https://developer.android.com/topic/architecture/data-layer/offline-first>
- [R4] Data layer — repositories, data sources, and their responsibilities: <https://developer.android.com/topic/architecture/data-layer>
- [R5] UI layer and UI state — state holders, state modelling, unidirectional data flow: <https://developer.android.com/topic/architecture/ui-layer>
- [R6] ViewModel overview and `SavedStateHandle`: <https://developer.android.com/topic/libraries/architecture/viewmodel>
- [R7] WorkManager — persistent work, unique work, constraints, backoff: <https://developer.android.com/topic/libraries/architecture/workmanager>
- [R8] Now in Android — reference implementation of the offline-first replica and sync worker: <https://github.com/android/nowinandroid>
- [R9] WorkManager — define work requests: retry and backoff policy (`MIN_BACKOFF_MILLIS` = 10 s minimum, default `EXPONENTIAL` with 30 s): <https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work>
