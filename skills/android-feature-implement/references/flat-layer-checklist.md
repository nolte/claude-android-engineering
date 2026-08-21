# Flat-layer implementation checklist

The implementation-time rule set for a feature in a flat, server-authoritative Android client.
Distilled from `spec/android/app-architecture/`, `spec/android/backend-contract/`,
`spec/android/release-readiness/`, `spec/android/user-input-validation/`, and
`spec/android/notifications-alerting/`, with the §B test mechanics of
`spec/android/test-automation/` and the §D platform rules of `spec/android/security/`; the
specs remain authoritative on every point.

## Contents

1. [The placement test — who decides](#1-the-placement-test--who-decides)
2. [Screen state model](#2-screen-state-model)
3. [Data layer and the replica](#3-data-layer-and-the-replica)
4. [Writes and sync](#4-writes-and-sync)
5. [Failure mapping](#5-failure-mapping)
6. [Backend-requirement triggers](#6-backend-requirement-triggers)
7. [Test coverage floor](#7-test-coverage-floor)
8. [Done gate](#8-done-gate)
9. [Input and alerting decisions](#9-input-and-alerting-decisions)
10. [Delivery path](#10-delivery-path)

## 1. The placement test — who decides

Run every candidate rule through this list. If it does not fit one of the four device classes,
it is the backend's — no exceptions, no "just for now" without an artifact (§6).

| Class | Belongs on the device | Examples |
|---|---|---|
| Presentation | yes | formatting, sorting/filtering delivered data for display, mapping to UI models |
| Cache & sync policy | yes | what is stored, when revalidated, how a write is retried |
| Device capability | yes | camera, sensors, permissions, connectivity, files, background execution |
| Navigation & UI state | yes | current screen, selection, expansion, scroll position |
| Anything else | **no** | acceptance, permission, status, eligibility, price, quota, derived labels, workflow transitions |

- [ ] Client-side input checks exist only as assistance (required marks, format hints, keyboard
      types); the server's answer wins even when the client believed the input was valid
- [ ] No derived value is computed locally when the backend could carry it as a field
- [ ] No locally-derived decision is persisted next to server data without being marked
      unconfirmed
- [ ] A server rejection is a designed UI state with a next step, not a raw exception dialog
- [ ] No domain layer hosts a rule that belongs to the backend; a use case exists only to reuse
      *client* orchestration across ViewModels, and no trivial pass-through use case exists
      (`spec/android/app-architecture/` §F, `spec/android/project-structure/` §E)

## 2. Screen state model

- [ ] One `uiState` property per screen, type `StateFlow`, built with
      `stateIn(scope, SharingStarted.WhileSubscribed(5_000), initial)` when derived from a
      data-layer stream, collected with `collectAsStateWithLifecycle()`
- [ ] States expressible: **loading**, **content**, **empty**, **error with a recovery action**
- [ ] Plus, wherever the screen can be served from cache: **stale** (age or "last updated") and
      **pending write** (unconfirmed change included)
- [ ] No ViewModel→UI event channel; an event is handled in the ViewModel and becomes state
- [ ] No `Activity`, `Context`, `Resources`, or lifecycle type held in the ViewModel; no
      `AndroidViewModel`
- [ ] ViewModel at screen level only; reusable components take hoisted state
- [ ] User input and unsent writes survive process death (`SavedStateHandle` / `rememberSaveable`)
- [ ] No network or database work starts from composition; a request is triggered from state
      collection, an effect, or a user-intent callback (`spec/android/app-architecture/` §E)
- [ ] Work that must outlive the screen but not the process runs in an application-scoped
      `CoroutineScope`; work that must survive process death runs in WorkManager; nothing in
      `GlobalScope`

## 3. Data layer and the replica

- [ ] UI reads only through repositories; no data source touched above the repository
- [ ] The local store is the SSOT the UI observes; a read never depends on a successful network
      round trip
- [ ] Three model sets kept apart — network DTO, local entity, UI model — with explicit mappers
- [ ] Where a contract exists, the client is **generated** from it into `core/network` (or the
      single-module equivalent) — `openapi-generator` `kotlin`, `library=jvm-retrofit2`,
      `useCoroutines=true`, `serializationLibrary=kotlinx_serialization`, `dateLibrary=java8`,
      `enumUnknownDefaultCase=true`; a deviation is recorded with its reason. No hand-written
      DTO duplicates a published schema; generated sources are never hand-edited
      (`spec/android/backend-contract/` §A)
- [ ] The generated package is imported nowhere outside the network component — checked by grep
      in §8 (`spec/android/backend-contract/` §G)
- [ ] Reads are `Flow`; writes are `suspend`
- [ ] Freshness metadata stored per cached type (fetched-at plus ETag / version / sync token);
      a `304 Not Modified` refreshes that metadata and rewrites nothing
- [ ] A staleness policy declared per cached type: revalidation window, stale-while-revalidate
      behaviour, what the UI shows past hard expiry
- [ ] User-scoped cached data deleted or re-keyed on sign-out and account switch
- [ ] Local read errors emit a safe state (`catch`), never cancel the UI's collection
- [ ] No `SharedPreferences` in new code; Room for queryable replicas, DataStore for scalars,
      files for binaries

## 4. Writes and sync

Pick exactly one strategy per write and record it:

| Strategy | Choose when | Obligations |
|---|---|---|
| Online-only (default) | acceptance depends on a backend rule | affordance disabled offline with a stated reason |
| Queued | failure is tolerable, user must not be blocked | pending visible, permanent failure actionable |
| Local-first | user-created data that must not be lost | pending visible, designed rollback, backend conflict answer |

- [ ] Queued and local-first drains run in WorkManager unique work with a connectivity
      constraint and exponential backoff — never in `viewModelScope`
- [ ] Every automatic retry uses **capped exponential backoff plus jitter, a stated maximum
      attempt count, and an overall deadline** after which the call is reported as failed — all
      recorded with the feature (`spec/android/backend-contract/` §C); `Retry-After` is honoured
      in place of that policy and does not count against the budget
- [ ] Every unconfirmed write is visible; every permanently failed write is actionable (retry,
      edit, discard); nothing is dropped into a log
- [ ] OkHttp's transparent retry (`retryOnConnectionFailure`, default `true`) is accounted for:
      behind a non-idempotent write without an honoured idempotency key it is either disabled
      (shared or dedicated write client) or the request body is one-shot
      (`RequestBody.isOneShot() == true`); the choice is recorded — a bare default client is
      non-conformant (`spec/android/backend-contract/` §C)
- [ ] Conflict resolution comes from the backend against a validator the client sends; no
      client-side merge; no older local state overwriting newer server state
- [ ] Any automatically retried write is idempotent-safe on the wire (§5); otherwise the retry
      is user-triggered
- [ ] One reconciliation entry point per data area rather than per-screen ad-hoc refreshes

## 5. Failure mapping

Map every call outcome to exactly one case; handle all eight per feature.

| # | Case | Client answer |
|---|---|---|
| 1 | success | render content |
| 2 | offline / unreachable | serve replica, mark stale, offer retry |
| 3 | timeout | retry policy per §4, then an error state with an action |
| 4 | unauthenticated | single-flight refresh, else sign-in prompt |
| 5 | unauthorized | render as a server decision, not a bug |
| 6 | domain rejection | route field-level detail back to the fields |
| 7 | server fault | retry if idempotent; never blame the user |
| 8 | contract mismatch | surface as a contract defect; log endpoint + field, never the payload |

The boundaries the table leaves adjacent, resolved per `spec/android/backend-contract/` §B:

- **Cancellation is not an outcome.** Rethrow `CancellationException`; never map it into a failure case.
- **Unauthorized vs. domain rejection.** Refused because of *who* asks → unauthorized. Refused because of *what* is asked or the resource's state → domain rejection. Same status for both and no problem `type` to separate them → §6 trigger.
- **429.** Classified as server fault, but honour `Retry-After` over your own backoff and don't spend the retry budget on it.
- **The status table, per §B.** `304` on a conditional request → *success without a body* (freshness metadata refreshed, nothing rewritten); `401` unauthenticated; `403` per the boundary above; `408` timeout; `429` server fault; `404`/`410` on a resource the replica holds → a domain rejection whose answer is *replica cleanup* (remove or tombstone the row, "no longer available" state) — a `404` for a documented endpoint is a contract mismatch; `412` → a domain rejection carrying a *conflict* (re-fetch, never retry the stale validator); "app version unsupported" — `426` or the problem `type` the contract defines — → a domain rejection with the single recovery action *update the app*; every other `4xx` a domain rejection read through the problem `type`; every `5xx` a server fault. **Skill refinement beyond §B:** `409` is also mapped to the *conflict* shape (the spec lists it only among the generic domain rejections) — record that with the feature. A `4xx` the contract documents with a meaning the table cannot express is a §6 trigger, not a local guess.

- [ ] Explicit connect, read, and call timeouts
- [ ] Automatic retry only for idempotent requests, or for keyed `POST`/`PATCH` where the
      backend honours `Idempotency-Key` (key persisted with a queued write)
- [ ] Credential refresh is single-flight
- [ ] `application/problem+json` read via `type` and extension members; `detail` never parsed
      for logic
- [ ] No raw server string as a screen's primary error text
- [ ] `ContractMismatch` is never folded into a generic branch: it is surfaced as a contract
      defect (endpoint + field, never payload) and raises a §6 trigger when the backend deviates
      from its own document
- [ ] Unknown JSON fields ignored; every enum has a fallback member
- [ ] Contract pagination used (cursor preferred); conditional-request validators sent where
      available, and `304` handled as success without a body (a `304 -> Success(NotModified)`
      branch before the `isSuccessful` check — Retrofit raises `HttpException` for it)

## 6. Backend-requirement triggers

Any of these fires → write the artifact per SKILL.md step 4 (the nine-section template it names),
agree the interim path, and do **not** implement a silent workaround:

- a domain decision would have to be derived on the device
- the UI needs a field the contract does not carry
- filtering, sorting, searching, or paging the API cannot express
- three or more calls for one screen's first frame, or an N+1 pattern over a list
- a multi-step write that must succeed or fail as a unit but is exposed as separate calls
- a non-idempotent write the client is expected to retry
- polling where a conditional request, push, or sync token would do
- an error case the client must distinguish but the contract does not make distinguishable
- no contract document exists at all
- a pushed ledger row (§10) whose server-side event contract — endpoint, payload schema,
  collapse key — does not exist yet
- the backend deviated from its own contract (a `ContractMismatch` observed in the wild)

## 7. Test coverage floor

- [ ] JVM tests with fakes, no device, no live backend
- [ ] All eight outcome cases the feature can hit (seven of them failures)
- [ ] The stale state and the pending-write state
- [ ] The recovery action on each error state
- [ ] Time and dispatchers injected — no test sleeps
- [ ] A fake per remote data source that can produce each failure case
- [ ] Where the feature takes input: a field-identified rejection lands on its field with the
      entered values preserved, and the restoration path is asserted at both levels
      (`spec/android/user-input-validation/` §H)

Mechanics, fixed by `spec/android/test-automation/` §B:

- [ ] JUnit 4 test classes; JUnit 5 is not assumed by generated code
- [ ] Every coroutine test body in `runTest`; one `TestScheduler` shared by all `TestDispatcher`s
- [ ] ViewModel tests install a `MainDispatcherRule` (`TestWatcher` around
      `Dispatchers.setMain`/`resetMain`); production classes take injected dispatchers
- [ ] A `stateIn(WhileSubscribed)` flow under test has a collector launched in `backgroundScope`
      before the first assertion on `value`
- [ ] Waiting only via `advanceUntilIdle`/`advanceTimeBy`; no `Thread.sleep`, no wall clock
- [ ] `kotlin.test` assertions (or the one library the project already standardised on)
- [ ] No Robolectric in these pure unit tests
- [ ] No unit test targets a framework entry point (`FirebaseMessagingService`, worker shell,
      activity); the logic behind it is tested through the repository or a plain class

## 8. Done gate

The six elements of `spec/android/release-readiness/` §E, then the acceptance criteria of that
spec a feature change can break. Report every red, unrunnable, or skipped one with its reason.

Six-element gate (§E):

- [ ] `./gradlew build` green
- [ ] Lint error-free on changed code, with **no new baseline entry**, security checks at error
      severity
- [ ] Unit tests green, including §7
- [ ] Release variant assembles with the shrinker on
- [ ] The touched flow exercised manually on a device from the **release** variant
- [ ] No debug library, verbose log, non-production endpoint, bypass switch, or hidden developer
      screen reachable in that variant; `android:debuggable` is false and no variant reaching
      production data weakens TLS trust; StrictMode clean in debug for the touched flow

Acceptance criteria of the same spec (its "done" definition):

- [ ] The touched flow survives **process death** and configuration change without losing user
      input or unsent writes — verified with *Don't keep activities* or a background kill
      (`adb shell am kill <package>` while backgrounded), not by inspection
- [ ] No **empty `catch` block** in changed code; no swallowed `CancellationException`
- [ ] **Keep rules** for anything the change made reflective or serialized are specific and live
      in the module owning the class; no blanket keep, `-dontobfuscate`, or `-dontoptimize` added
- [ ] **`mapping.txt`** of the release build is retained (uploaded or archived) — the artifact
      never leaves the machine without it
- [ ] No blocking work on the main thread in the touched flow
- [ ] No generated type crosses the repository boundary — the mechanical check
      (`spec/android/backend-contract/` §G): `grep -rn "<generated package>" --include=*.kt`
      outside `core/network` returns nothing
- [ ] Where UI changed: instrumented and screenshot lanes run per `spec/android/test-automation/`
      §G (SHOULD — a skip is reported, never silently green)
- [ ] Artifact size delta and any likely startup or scroll regression stated; a suspected
      regression routes to `android-perceived-performance`
- [ ] No lint baseline entry, check disablement, or suppression added to pass any of the above

## 9. Input and alerting decisions

Recorded with the feature alongside the write strategy and staleness policy, per
`spec/android/app-architecture/` §H — in the feature's requirement or feature file under
`project/`, never only in a commit message. Both are decisions, not implementation details: they
are made at the step-3 gate and reviewed there. Write strategy, staleness policy, input-stage
split, and channel plus delivery path (§10) are the **four recorded decisions** the step-7 report
names, alongside every `BR-<n>` raised.

### Input, where the feature takes a value from the user

- [ ] Every check is assigned to one of the four stages of `spec/android/user-input-validation/`
      §A — shaping, field check, form check, server decision — and none answers a later stage's
      question
- [ ] Field-check parameters (required, length, range, allowed values) come from the backend
      contract; a limit the contract does not state is a backend requirement, not a constant
- [ ] Each field's state carries a **touched** flag alongside its value, error, and submission
      state — without it the timing rules of §D cannot hold
- [ ] Raw, normalised, and transmitted representations of each value stay distinguishable

### Alerting, where the feature produces an event a user might need to know about

- [ ] The channel comes from `android-notification-derive` (REQ-21), which owns the gate chain —
      this skill hands the event over rather than choosing a channel
- [ ] The resulting row exists in `project/notification-ledger.md` before any notification code
      is written, and names the matched gate plus the rejected cheaper gate
- [ ] Every permission the chosen channel implies went to `android-permissions-derive` before
      any manifest edit
- [ ] The row's **delivery path** is recorded by this skill (§10)

## 10. Delivery path

Owned by this skill as data-layer work (`spec/android/notifications-alerting/` §E,
`spec/android/security/` §D). The channel is the input; nothing here is built without a
ledger row.

- [ ] Every ledger row with a channel records exactly one delivery path — **local**,
      **scheduled**, or **pushed**; a `none` row records `none` and skips the rest
- [ ] *Scheduled* work runs in WorkManager wherever it is deferrable; `AlarmManager` only where
      the **time itself** is the user-visible point (a reminder the user set), and its exact-alarm
      permission went to `android-permissions-derive`
- [ ] *Pushed* events arrive as FCM **data messages** whenever the app must control channel,
      grouping, localisation, styling, or any §F rule; a notification message only where the
      presentation genuinely needs no app decision (and that choice is recorded on the row)
- [ ] `priority: high` is reserved for messages that produce a user-visible notification or an
      immediate interaction; sync-only pushes stay at normal priority
- [ ] `onMessageReceived()` reads the payload, enqueues WorkManager work (expedited for high
      priority) and returns — it never fetches, writes the replica, or posts a notification
      itself; the `FirebaseMessagingService` holds no logic worth a unit test
- [ ] Push is a hint, not delivery: a **missed-message sync** runs on next foreground and on
      `onNewToken`, and the replica — not the push payload — is what the UI observes
- [ ] The notification tap `PendingIntent` is `FLAG_IMMUTABLE`, uses an explicit intent, and
      targets the destination activity directly (a deep link with a synthetic back stack); no
      service or broadcast-receiver trampoline
- [ ] A deep link carried by a push payload or a tap intent is validated before navigation —
      scheme *and* host by exact match, a known destination, typed arguments; verified App
      Links (`autoVerify`) preferred; no intent forwarded from untrusted extras without a
      resolve check (`spec/android/security/` §D)
- [ ] Every component added for delivery declares `android:exported` explicitly, `false` unless
      the platform requires otherwise; a receiver that must be exported is permission-protected
- [ ] Doze / app-standby deferral of the pushed or scheduled row was exercised (`adb shell dumpsys
      deviceidle force-idle`) — the SHOULD of §E, reported when skipped
- [ ] Notification text is composed on the device from an event key plus parameters; a
      server-rendered string, where unavoidable, is recorded on the row with its language

## Logging

Per `spec/android/logging/`, three rules bind a feature implementation:

- **§A** — call the project's logging facade, never `android.util.Log`. Domain and data code
  depends on the facade's platform-free interface; only its implementation module knows Android.
- **§C** — no personal data, credential, or token reaches a log line. The trap to close while
  writing model types is the Kotlin `data class` auto-`toString()`: a sensitive field is rendered
  in full whenever the instance is interpolated, logged, or lands in an exception message. Either
  the field is a masking wrapper type, or the class overrides `toString()`.
- **§E** — cancellation is normal control flow, never an error. Write the `Flow.onCompletion`
  predicate as `cause != null && cause !is CancellationException`, rethrow a `CancellationException`
  caught by a broad `catch`, and carry correlation on a `CoroutineContext.Element` rather than on
  `CoroutineName`, which R8 strips from release builds.
