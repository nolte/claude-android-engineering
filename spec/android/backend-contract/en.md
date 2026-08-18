# Backend Contract and Requirement Handoff

Status: draft

## Context

A flat view layer (`spec/android/app-architecture/`) buys its simplicity with a dependency: everything the app cannot decide, the backend has to supply. That makes two things load-bearing that a client-heavy app can be sloppy about — how the app consumes the contract, and what happens when the contract does not contain what the screen needs.

The second half is the one that goes wrong in practice. A missing field or an un-expressible filter is discovered mid-implementation, at the worst possible moment for a design conversation, and the cheapest local move is always the same: compute it on the device. That single decision is how a flat client stops being flat. This spec makes the alternative cheap instead — a fixed shape for capturing the missing capability as a requirement the backend side can pick up, so "raise it" costs less than "work around it".

The consuming half is deliberately narrow: this spec fixes what the *client* does with the contract — how it is generated, where its types are allowed to appear, how failures are classified into a closed set, and which requests may be retried. It states nothing about how the backend is built.

Provenance: desk research (August 2026) over the OpenAPI Generator Kotlin client documentation, RFC 9457 (Problem Details for HTTP APIs), the (since expired) IETF HTTPAPI `Idempotency-Key` header draft, RFC 9110 for status semantics, the OkHttp client documentation, the Android architecture and offline-first guides, and this portfolio's own consuming app (`nolte/kamerplanter-android`, an OpenAPI-generated Retrofit client in `core/network`).

Boundaries: TLS and certificate handling are owned by `spec/android/security/` §C, credential storage by its §A, and build/supply-chain and authentication-resilience obligations by its §F/§G; the rule that the backend — never the client — decides whether an action is permitted belongs to `spec/android/app-architecture/` §A; caching, staleness, write strategies, and sync are owned by `spec/android/app-architecture/` §C/§D; paging *presentation* and the Paging 3 wiring by `spec/android/long-list-scrolling/` §C; error *message wording* and empty-state UX by `spec/android/app-design-navigation/` §F; test mechanics by `spec/android/test-automation/`.

Readers: authors of this repository's Android skills who implement a feature against a backend, and reviewers judging whether a client stayed inside the contract instead of inventing around it.

## Goals

- Make the contract the single machine-readable source for wire types, so DTOs are never hand-maintained twice
- Confine generated types to one layer, so the client survives a contract regeneration
- Turn transport and protocol failures into a closed, exhaustively handled set instead of a `catch (e: Exception)`
- Make retries safe by construction rather than by hope
- Give "the backend cannot do this yet" a cheaper path than a client-side workaround
- Produce a backend requirement that a backend specialist can implement without asking the app author anything

## Non-Goals

- Backend implementation, API design authority, or the backend's own quality gates — this spec only states what the client needs and how it asks
- Transport security, authentication scheme design, and credential storage — `spec/android/security/` §A/§C/§G
- Cache, staleness, write strategy, conflict handling — `spec/android/app-architecture/` §C/§D
- Paging UI behaviour and Paging 3 mechanics — `spec/android/long-list-scrolling/` §C
- GraphQL, gRPC, and realtime transports; the requirements below assume an HTTP/JSON contract and would need extension for the others (§Open Questions)
- Choosing the backend product or hosting; the app consumes whatever the operator's backend repository exposes

## Requirements

### A. Contract-first consumption

- **MUST** consume a documented backend through a typed client generated from its published contract (OpenAPI) whenever a contract exists; hand-written DTOs that duplicate a published schema are non-conformant [R1]
- **MUST** commit the contract document (or a pinned reference to a versioned artifact) into the app repository, so a build is reproducible without a live backend, and **MUST** regenerate deliberately — generated sources are never hand-edited
- **MUST** generate into a dedicated network component (`core/network` or the single-module equivalent per `spec/android/project-structure/` §C) and **MUST** keep generated types, HTTP status codes, and serialization annotations behind the repository boundary (`spec/android/app-architecture/` §F)
- **MUST** map generated DTOs to app models in the data source or repository, never above it
- **SHOULD** configure the Kotlin generator as: `library` = `jvm-retrofit2` with `useCoroutines`, or `jvm-ktor` where a Ktor stack already exists; `serializationLibrary` = `kotlinx_serialization`; `dateLibrary` = `java8` (JVM-only apps). This is a **portfolio default**, not a vendor recommendation — the generator supports several combinations and [R1] is cited only for the option names and their accepted values. A different combination is allowed but **MUST** be recorded with its reason. Three generator facts a skill must not discover mid-run: `useCoroutines` is a `jvm-retrofit2`-only switch [R1]; `jvm-ktor` (and `multiplatform`) generate against Ktor 1.6.7 [R1], so a project on Ktor 3 records why it still uses that library (or which template override it applies) rather than assuming a current client; and `enumUnknownDefaultCase=true` makes every generated enum carry the fallback member (`unknown_default_open_api`) that §D requires, so the fallback is generated rather than hand-patched [R9]
- **MAY** hand-write the client when no contract document exists at all; in that case §E applies immediately — the absence of a contract is itself a backend requirement, and the hand-written types are an interim measure with a recorded end state
- **MUST NOT** call the backend from more than one place per resource: one data source per API area, one repository per data type (naming per `spec/android/project-structure/` §E)

### B. The closed outcome set

- **MUST** map every outcome of a call into exactly one of eight cases — one success plus seven failures — and **MUST** handle all eight for every feature (the fakes in `spec/android/app-architecture/` §G exist to prove it):
  1. **success**
  2. **offline / unreachable** — no usable connection, DNS failure, connection refused
  3. **timeout** — connect, read, or overall deadline exceeded
  4. **unauthenticated** — the credential is missing or expired; the client's answer is a refresh or a sign-in prompt, never a generic error
  5. **unauthorized** — the credential is valid and the action is not allowed; a *server decision*, rendered as such
  6. **domain rejection** — the request was understood and refused on a business rule (validation, conflict, state); carries per-field or per-rule detail where the contract provides it
  7. **server fault** — the backend failed; retryable per §C, never blamed on the user
  8. **contract mismatch** — the response could not be parsed into the generated types, or a required field was absent
- **MUST NOT** map coroutine cancellation into the set: cancellation is not an outcome of the call but the disappearance of its caller. A `CancellationException` **MUST** be rethrown, never caught into a failure case — swallowing it turns a navigated-away screen into a spurious error state and breaks structured concurrency
- **MUST** resolve the three boundaries the eight cases leave adjacent, so a client implementer never has to guess:
  - **offline vs. timeout** — decided by the failure that actually occurred (name resolution or connection refusal versus an exceeded deadline), not by how long the user waited
  - **unauthorized vs. domain rejection** — a refusal that depends on *who* is asking is unauthorized; a refusal that depends on *what* is being asked or on the resource's state is a domain rejection. Where a backend returns the same status for both, the contract's problem `type` decides; where it distinguishes neither, §E fires — the client **MUST NOT** guess, because the two cases lead to different UI answers
  - **rate limiting** — a `429` is a **server fault** for classification purposes (the request was well-formed and the user is not at fault), but the client **MUST** honour `Retry-After` where present in place of its own backoff, and **MUST NOT** count a rate-limited attempt against a retry budget as though the backend had failed
- **MUST** apply the following status mapping for the codes the eight cases leave implicit, so a skill applies a table instead of deciding per feature [R10]:
  - `304 Not Modified` on a conditional request (§C) is **success without a body**: the replica is confirmed fresh, its freshness metadata is updated, and nothing is rewritten
  - `404`/`410` on a resource the replica already holds is a **domain rejection** of the resource's *state* — the item was deleted or withdrawn server-side. The client removes or tombstones the replica row per `spec/android/app-architecture/` §D and shows a "no longer available" state, not an error banner. A `404` for an endpoint the contract documents (not for an item) is a **contract mismatch**
  - `412 Precondition Failed` on `If-Match`/`If-Unmodified-Since` is a **domain rejection** in its conflict shape: the resource changed under the client, which re-fetches and re-presents; it **MUST NOT** retry with the stale validator
  - a response the contract defines as "app version unsupported" — however encoded (some backends borrow `426 Upgrade Required`, whose RFC 9110 meaning is a *protocol* upgrade; a problem `type` is the clean carrier) — is a **domain rejection** with exactly one recovery action, *update the app*: the screen blocks on it and never retries automatically
  - `401` is unauthenticated, `403` unauthorized, `408` a timeout, `429` a server fault per the rate-limiting boundary above, and every other `4xx` not mapped here (`400`, `405`, `409`, `413`, `415`, `422`, …) is a **domain rejection**; every `5xx` is a **server fault**. A `4xx` the contract documents with a distinct meaning that this table cannot express is a §E trigger, not a local guess
- **MUST** treat contract mismatch as a defect against the contract, not as a runtime error to swallow: it is surfaced to the operator (log with the offending endpoint and field, never with the payload) and it becomes a backend requirement per §E when the backend deviates from its own document
- **MUST** consume an RFC 9457 `application/problem+json` body when the backend emits one, reading `type` and defined extension members for control flow; **MUST NOT** parse `detail` for logic and **MUST NOT** switch behaviour on `title` [R2]
- **MUST NOT** render a raw server string as a screen's primary error text; the client maps the case to its own message with a recovery action (wording per `spec/android/app-design-navigation/` §F). Server-supplied text **MAY** be shown as secondary detail when the contract states it is user-facing and localized
- **MUST** route field-level rejections back to the corresponding input fields rather than to a single banner, where the contract carries field identity
- **MUST NOT** log request or response bodies, headers carrying credentials, or any personal data (`spec/android/security/` §A); a failure log names endpoint, status, and error class only

### C. Requests: timeouts, retries, idempotency

- **MUST** set explicit connect, read, and call timeouts; the platform defaults are not a decision
- **MUST** retry automatically only where the request is idempotent — `GET`, `HEAD`, `PUT`, `DELETE` as the contract defines them — with capped exponential backoff **plus jitter** (a random share of the capped delay, never a fixed schedule), a stated maximum attempt count, and an overall deadline after which the call is reported as failed — all three recorded with the feature, and never left to a library default [R4]
- **MUST NOT** automatically retry `POST` or `PATCH` unless the request carries an idempotency key the backend honours; where the backend offers no such mechanism, the retry is manual (user-triggered) until the requirement is raised per §E [R3]
- **MUST** account for the transport's *own* transparent retries, which the rule above does not see: OkHttp's `retryOnConnectionFailure` defaults to `true` and silently re-sends a request — body included — on a stale pooled connection, an unreachable address of a multi-homed host, a `408`, or a `401`/`407` the `Authenticator` satisfies [R11]. For a non-idempotent write without an honoured idempotency key that is a duplicate write in disguise; the client therefore either disables `retryOnConnectionFailure` (on the shared client or on a dedicated write client) or marks such request bodies one-shot (`RequestBody.isOneShot() == true`), which stops OkHttp from retransmitting them [R11]. The choice is recorded; a bare default client behind non-idempotent writes is non-conformant
- **SHOULD**, where the backend supports it, send `Idempotency-Key` as a client-generated UUID that stays stable across retries of the *same* logical write and changes for a new one; the key is persisted with a queued write so it survives process death [R3][R8]. The header is specified only by an IETF draft that has since **expired** (`draft-ietf-httpapi-idempotency-key-header-07`, last revised 2025-10-15, expired 2026-04-18, no successor at the time of writing) — it is de-facto vendor practice, not a standard [R3]; so this stays a **SHOULD** conditioned on the backend actually honouring it, the header name and semantics are taken from the backend's own contract, the mechanism is nonetheless established shipped practice at several payment providers [R8], and where a backend offers none, §C's ban on automatically retrying a non-idempotent write governs instead
- **MUST** single-flight credential refresh: concurrent 401s trigger one refresh, and the waiting calls are replayed once — a refresh storm is both a defect and a rate-limit hazard
- **MUST** use the contract's own pagination mechanism (cursor-based preferred over offset) and **MUST NOT** emulate paging by requesting an unbounded page; client-side wiring follows `spec/android/long-list-scrolling/` §C
- **MUST** send conditional-request validators (`ETag`/`If-None-Match`, `If-Modified-Since`) where the contract exposes them, since the replica's freshness metadata (`spec/android/app-architecture/` §C) exists precisely to make this possible
- **SHOULD** keep one request per screen state where possible; a screen that needs three or more calls to render its first frame is a §E trigger, not a client-side orchestration exercise. Two calls are acceptable when they are independent and run in parallel; two calls where the second needs the first one's response is already a dependent chain, and a dependent chain is a §E conversation regardless of its length

### D. Living with contract change

- **MUST** configure deserialization to ignore unknown fields, so an additive backend change cannot crash a shipped app
- **MUST** give every enum a fallback member (generated via `enumUnknownDefaultCase=true`, §A) and **MUST NOT** treat an unknown enum value as a fatal error; the UI shows a neutral representation and the case is logged as a contract observation
- **MUST NOT** depend on field ordering, on an optional field being present, or on an undocumented field the backend happens to emit
- **MUST** regenerate the client in CI from the committed contract and fail the build on a compilation break, so a contract update cannot land silently half-applied
- **MUST** record the contract version (or commit) the app is built against, and **MUST** state the minimum backend version when the app requires one
- **SHOULD** treat a field the app needs but the contract marks optional as a §E clarification item rather than assuming it is always present

### E. When to raise a backend requirement

- **MUST** raise a backend requirement — and **MUST NOT** implement a silent client-side workaround — as soon as delivering the feature would require any of:
  - deriving a domain decision on the device (the §A rule of `spec/android/app-architecture/`)
  - a field the UI must display that the contract does not carry
  - filtering, sorting, searching, or paging the API cannot express, forcing the client to over-fetch and post-process
  - three or more calls to render one screen's first frame, or an N+1 call pattern over a list
  - a multi-step write that must succeed or fail as a unit but is exposed only as separate calls
  - a non-idempotent write that the client is expected to retry (§C)
  - polling where a conditional request, a push, or a sync token would do
  - an error case the client must distinguish but the contract does not make distinguishable (for example: everything is a 400 with a prose message)
- **MUST**, having raised it, agree the interim client behaviour with the operator rather than choosing it alone: wait, ship the feature without the affected part, or implement a time-boxed interim path that is recorded in the artifact and removed when the backend lands (repository REQ-6, REQ-8)
- **MUST NOT** let an interim path become permanent silently — the artifact's status (§F) is the tracking mechanism

### F. The handoff artifact

- **MUST** write the requirement to `project/backend-requirements/<YYYY-MM-DD>-<slug>.md` in the *app* repository, with a stable identifier `BR-<n>` that code comments, commits, and issues can reference
- **MUST** contain these sections, in this order, so the backend side can implement without a follow-up conversation:
  1. **Trigger** — the feature, screen, and user step that produced the need
  2. **Need** — one sentence, phrased as a capability, not as an implementation
  3. **Consumer scenario** — what the app renders with the answer, including the loading, empty, and error states it must be able to show
  4. **Proposed contract** — endpoint(s), method, request shape, response shape, and the error cases the client will distinguish, as an OpenAPI fragment (paths + schemas + responses), explicitly marked **proposal, not authoritative** — the backend owns the final design
  5. **Non-functional needs** — latency budget for the consuming screen, expected page size and ordering, authentication scope, idempotency needs, cacheability and validators, data volume, and the app-side urgency: what is blocked without this capability and by when the app needs it, so the backend can sequence it against its own queue
  6. **Acceptance criteria** — testable from the backend side alone, one bullet per criterion
  7. **Interim client behaviour** — what the app does until this lands, and what must be removed afterwards
  8. **Open questions** — every point the app side could not decide
  9. **Status** — one of `draft` → `proposed` → `accepted` → `implemented` → `consumed`, with the date of the last transition
- **MUST** use synthetic examples only; no production personal data, no credentials, no real user identifiers. This is this spec's own rule and it exists because the artifact is a cross-repository document: data pasted into it leaves the app's storage boundary entirely, which is a different exposure from the on-device obligations `spec/android/security/` §A/§E governs
- **MUST** state the *why* behind every field requested — a field list without the rendering purpose invites a backend design that satisfies the letter and misses the screen
- **MUST** record, when the status reaches `accepted`, the contract version that will carry the change, and when it reaches `consumed`, remove the interim path and say so in the artifact
- **MAY**, after explicit operator confirmation, open an issue in the backend repository whose body is derived from the artifact and links back to it; the artifact stays the source of truth and the issue link is recorded in it. Opening the issue without confirmation is forbidden (repository REQ-8)
- **SHOULD** keep one artifact per capability; a second screen needing the same capability extends the existing artifact rather than filing a duplicate

### G. Verification

- **MUST** cover all eight outcome cases of §B — the success case and the seven failures — with fakes in JVM tests before a feature is called done (`spec/android/test-automation/` §B/§C)
- **MUST** verify that no generated type crosses the repository boundary — a grep for the generated package outside the network component is the mechanical check
- **MUST** verify that retried writes are idempotent-safe (§C), by test where a key is used and by inspection otherwise
- **MUST** report a raised-but-unanswered backend requirement in the run's final report rather than closing the work silently (repository REQ-6, REQ-7)

## Acceptance Criteria

The criteria are a representative rollup of §A–§G, not a 1:1 mapping; every requirement bullet above is normative on its own.

- [ ] The wire client is generated from a committed contract document; no hand-maintained DTO duplicates a published schema, and no generated source is hand-edited
- [ ] Generated types, HTTP statuses, and serialization annotations appear only inside the network component; the repository exposes app models
- [ ] Every call outcome maps to one of the eight cases in §B, and every feature handles all eight, proven by fakes in JVM tests
- [ ] Contract mismatch is reported as a contract defect, not swallowed; no payload, credential, or personal data is logged
- [ ] Problem-details bodies are read via `type` and extension members; `detail` is never parsed for logic; no raw server string is a screen's primary error text
- [ ] Timeouts are explicit; automatic retries exist only for idempotent requests or keyed writes, with jitter, a maximum attempt count, and a deadline; OkHttp's transparent retry is disabled or the bodies are one-shot for non-idempotent writes; credential refresh is single-flight
- [ ] Pagination uses the contract's mechanism; conditional-request validators are sent where available
- [ ] Unknown fields and unknown enum values are tolerated; CI regenerates the client from the committed contract and fails on a compilation break
- [ ] The consumed contract version is recorded with the build, and a required minimum backend version is stated where one exists
- [ ] Coroutine cancellation is rethrown rather than mapped into the outcome set, and the offline/timeout, unauthorized/domain-rejection, and rate-limiting boundaries are resolved as §B fixes them
- [ ] The §B status table is applied: `304` updates freshness only, `404`/`410` on a cached resource cleans the replica and shows a "no longer available" state, `412` re-fetches without retrying the stale validator, an unsupported-version response blocks with an update action, and unmapped `4xx` are domain rejections
- [ ] Every §E trigger produced a `BR-<n>` artifact under `project/backend-requirements/` with all nine sections, synthetic examples only, and a current status
- [ ] Every field the artifact requests states the rendering purpose it serves, and the artifact names what is blocked without the capability
- [ ] A raised but unanswered backend requirement is named in the run's final report rather than left implicit
- [ ] Every interim client path is recorded in its artifact and removed when the artifact reaches `consumed`
- [ ] A backend-repository issue exists only where the operator confirmed it, and links back to the artifact

## Open Questions

Each question states the working default the requirements above already encode.

- Should the app repository also hold a generated, human-readable diff of contract changes between versions, or is the committed contract plus git history enough? Default: git history is enough
- Should `BR-<n>` numbering be per repository or portfolio-wide? Default: per repository, since the artifact lives in the app repo
- GraphQL and gRPC backends: extend this spec with a transport-neutral §A/§B, or write a sibling spec? Default: out of scope until a portfolio project needs one
- Should the client ever be allowed to ship a compatibility shim for a known backend defect (rather than raising a requirement)? Default: only as an interim path per §E, always recorded, never permanent

## References

- [R1] OpenAPI Generator — Kotlin client generator options (`library`, `serializationLibrary`, `dateLibrary`, `useCoroutines`): <https://openapi-generator.tech/docs/generators/kotlin/>
- [R2] RFC 9457 — Problem Details for HTTP APIs (`application/problem+json`, `type`/`title`/`status`/`detail`/`instance`, extension members, "consumers SHOULD NOT parse `detail`"): <https://www.rfc-editor.org/rfc/rfc9457.html>
- [R3] IETF HTTPAPI WG — The Idempotency-Key HTTP Header Field (Internet-Draft, **expired** — `-07` of 2025-10-15, expired 2026-04-18; client key generation, server duplicate/concurrent handling, 409/422 semantics): <https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/>
- [R4] Build an offline-first app — network error handling, exponential backoff, sync via WorkManager: <https://developer.android.com/topic/architecture/data-layer/offline-first>
- [R5] Guide to app architecture — data layer, repositories, data sources: <https://developer.android.com/topic/architecture/data-layer>
- [R6] kotlinx.serialization — JSON configuration (`ignoreUnknownKeys`, default values, unknown enum handling): <https://github.com/Kotlin/kotlinx.serialization/blob/master/docs/json.md>
- [R7] OpenAPI Specification 3.1: <https://spec.openapis.org/oas/latest.html>
- [R8] Stripe API — idempotent requests (shipped vendor practice corroborating the draft header in [R3]): <https://docs.stripe.com/api/idempotent_requests>
- [R9] OpenAPI Generator — `enumUnknownDefaultCase` option (adds `unknown_default_open_api` to every enum; honoured by the kotlin-client `enum_class` template): <https://github.com/OpenAPITools/openapi-generator/blob/master/modules/openapi-generator/src/main/resources/kotlin-client/enum_class.mustache>
- [R10] RFC 9110 — HTTP Semantics (§15.4.5 `304`, §15.5.5 `404`, §15.5.11 `410`, §15.5.13 `412`, §15.5.22 `426`): <https://www.rfc-editor.org/rfc/rfc9110.html>
- [R11] OkHttp — `OkHttpClient.Builder.retryOnConnectionFailure` (default true; silent recovery from unreachable addresses, stale pooled connections, proxies) and `RequestBody.isOneShot` (retransmission cases: stale connection, 408, 401/407, 503 with `Retry-After: 0`, 421): <https://github.com/square/okhttp/blob/master/okhttp/src/commonJvmAndroid/kotlin/okhttp3/OkHttpClient.kt>
