# Flat-layer implementation checklist

The implementation-time rule set for a feature in a flat, server-authoritative Android client.
Distilled from `spec/android/app-architecture/`, `spec/android/backend-contract/`, and
`spec/android/release-readiness/`; the specs remain authoritative on every point.

## Contents

1. [The placement test — who decides](#1-the-placement-test--who-decides)
2. [Screen state model](#2-screen-state-model)
3. [Data layer and the replica](#3-data-layer-and-the-replica)
4. [Writes and sync](#4-writes-and-sync)
5. [Failure mapping](#5-failure-mapping)
6. [Backend-requirement triggers](#6-backend-requirement-triggers)
7. [Test coverage floor](#7-test-coverage-floor)
8. [Done gate](#8-done-gate)

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

## 3. Data layer and the replica

- [ ] UI reads only through repositories; no data source touched above the repository
- [ ] The local store is the SSOT the UI observes; a read never depends on a successful network
      round trip
- [ ] Three model sets kept apart — network DTO, local entity, UI model — with explicit mappers
- [ ] Reads are `Flow`; writes are `suspend`
- [ ] Freshness metadata stored per cached type (fetched-at plus ETag / version / sync token)
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
- [ ] Every unconfirmed write is visible; every permanently failed write is actionable (retry,
      edit, discard); nothing is dropped into a log
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

Three boundaries the table leaves adjacent, resolved per `spec/android/backend-contract/` §B:

- **Cancellation is not an outcome.** Rethrow `CancellationException`; never map it into a failure case.
- **Unauthorized vs. domain rejection.** Refused because of *who* asks → unauthorized. Refused because of *what* is asked or the resource's state → domain rejection. Same status for both and no problem `type` to separate them → §6 trigger.
- **429.** Classified as server fault, but honour `Retry-After` over your own backoff and don't spend the retry budget on it.

- [ ] Explicit connect, read, and call timeouts
- [ ] Automatic retry only for idempotent requests, or for keyed `POST`/`PATCH` where the
      backend honours `Idempotency-Key` (key persisted with a queued write)
- [ ] Credential refresh is single-flight
- [ ] `application/problem+json` read via `type` and extension members; `detail` never parsed
      for logic
- [ ] No raw server string as a screen's primary error text
- [ ] Unknown JSON fields ignored; every enum has a fallback member
- [ ] Contract pagination used (cursor preferred); conditional-request validators sent where
      available

## 6. Backend-requirement triggers

Any of these fires → write the artifact (`references/backend-requirement-template.md`), agree
the interim path, and do **not** implement a silent workaround:

- a domain decision would have to be derived on the device
- the UI needs a field the contract does not carry
- filtering, sorting, searching, or paging the API cannot express
- three or more calls for one screen's first frame, or an N+1 pattern over a list
- a multi-step write that must succeed or fail as a unit but is exposed as separate calls
- a non-idempotent write the client is expected to retry
- polling where a conditional request, push, or sync token would do
- an error case the client must distinguish but the contract does not make distinguishable
- no contract document exists at all

## 7. Test coverage floor

- [ ] JVM tests with fakes, no device, no live backend
- [ ] All eight failure cases the feature can hit
- [ ] The stale state and the pending-write state
- [ ] The recovery action on each error state
- [ ] Time and dispatchers injected — no test sleeps
- [ ] A fake per remote data source that can produce each failure case

## 8. Done gate

Six elements, per `spec/android/release-readiness/` §E. Report every red or unrunnable one.

- [ ] `./gradlew build` green
- [ ] Lint error-free on changed code, with **no new baseline entry**, security checks at error
      severity
- [ ] Unit tests green, including §7
- [ ] Release variant assembles with the shrinker on
- [ ] The touched flow exercised manually on a device from the **release** variant
- [ ] No debug library, verbose log, non-production endpoint, bypass switch, or hidden developer
      screen reachable in that variant; StrictMode clean in debug for the touched flow
