---
name: android-notification-derive
description: "Decides which alerting channel a business event gets in an Android app and implements it device-side, per spec/android/notifications-alerting/. Classifies the event on six axes, runs the ordered gate chain so the cheaper channel wins where it suffices, and records a justified row per event in project/notification-ledger.md including the rejected cheaper gate. Then applies the device-side code: channel creation with its permanent importance, the notification build, category and lock-screen visibility, grouping with summary, the cancel and update rule, and the foreground-service or Live-Update contract. Operations: derive, audit, apply. Invoke when the user asks whether or how an app should notify about something, wants existing notifications audited or justified, or reports notifications that are missed, ignored, or switched off. Also handles equivalent German-language requests. Supports resume on re-invocation."
tags: [ui, audit, implementation]
phase: build
summary: "Derives the alerting channel for a business event from its classification, records a justified ledger row, and writes the device-side notification code."
summary_de: "Leitet den Benachrichtigungskanal eines fachlichen Ereignisses aus dessen Klassifikation ab, hält ihn im Register fest und schreibt den geräteseitigen Code."
use_when:
  - "an event needs deciding: notify the user about it, or not, and how"
  - "an app's existing notifications should be audited, justified, or cleaned up"
  - "users are switching the app's notifications off, or missing the ones that matter"
  - "an ongoing activity (navigation, delivery, workout, call, playback) needs its surface"
  - "a notification channel's importance turns out to be wrong for what it carries"
dont_use_when:
  - situation: "The notification permission itself needs declaring or requesting"
    alternative: android-permissions-derive
  - situation: "An in-app surface (snackbar, dialog, inline state) is what gets built"
    alternative: android-compose-ui
  - situation: "A feature needs implementing across layers, alerting being one part of it"
    alternative: android-feature-implement
  - situation: "A notification does not appear and the cause needs diagnosing"
    alternative: android-debugging
see_also:
  - android-feature-implement
  - android-permissions-derive
  - android-compose-ui
resumable: true
---

# Android Notification Derive

Decides how an app tells a user that something happened — and, far more often than
developers expect, decides that it does not tell them at all. The channel is derived from
what the event *is*, not from what is easiest to reach for.

The governing idea is that the ability to notify is a **shared, revocable, app-wide
resource**. From Android 13 a single denial silences every channel the app has, so every
notification is spent against every future notification the app will want to post. The
cheapest channel that serves the event therefore wins, and anything more intrusive has to
beat it on evidence.

The authoritative rules live in `spec/android/notifications-alerting/`; this skill
operationalizes them and never restates or contradicts them. On any conflict the spec wins —
report the gap and propose a spec change rather than deciding silently (REQ-6).

Grounding specs, in the order they bind this skill: `spec/android/notifications-alerting/`
(the model, the classification, the gate chain, the channel catalogue, delivery,
construction, degradation, verification), `spec/android/permissions/` §F (the notification
permission family, whose derivation belongs to its own skill),
`spec/android/app-architecture/` §B/§D (where state lives, how a write reaches the backend),
`spec/android/iconography/` §D (notification icon formats), `spec/android/localization/` §A
(notification text is externalized like any other string), `spec/android/ui-components/` §A
(the in-app surface the presence gate selects), and `spec/android/test-automation/` (where
the notification tests live).

## Why this is a skill, not an agent

- **Mid-flow approval is the contract.** Admitting a channel more intrusive than the one
  below it, refusing a requested notification as out of policy, and every code write are
  operator decisions with consequences that outlive the run (REQ-8); an agent's
  fire-and-forget shape cannot carry those gates.
- **The persistent artifact is the deliverable.** The notification ledger and the channel
  code land in the working tree and are reviewed in context, not behind a structured-report
  boundary.
- **It composes with sibling capabilities.** Every permission the chosen channel implies goes
  to `android-permissions-derive`, the in-app surface to `android-compose-ui`, a
  non-appearing notification to `android-debugging`; per `spec/claude/skill-vs-agent/`
  §Primary decision rule the orchestrator is always a skill.
- Counter-dimension considered: the `audit` operation alone — reading every `notify()` call
  site, every channel creation, and the manifest — would suit an agent's context isolation,
  but its findings feed directly into the admit/refuse gates that follow, so splitting it out
  would break the interaction it exists to serve.

## Boundary vs the sibling capabilities

- `android-permissions-derive` owns every permission decision (REQ-20). `POST_NOTIFICATIONS`,
  the `FOREGROUND_SERVICE_*` pair, `USE_FULL_SCREEN_INTENT`, and
  `POST_PROMOTED_NOTIFICATIONS` are *consequences* of a channel derived here: hand the ledger
  row over and take the declaration back, never write one into the manifest here.
- `android-compose-ui` owns every in-app surface (REQ-13). When the silence or presence gate
  matches, this skill decides *that* the in-app path carries the event and hands the authoring
  there; it does not build screens.
- `android-feature-implement` owns the feature across layers (REQ-19) and **calls this skill**
  for the channel step. The delivery path — FCM reception, WorkManager and AlarmManager
  scheduling — stays with it as part of the data layer; this skill ends at the device-side
  notification code.
- `android-ux-reviewer` reviews UI read-only (REQ-14); notification-channel conformance is
  outside its Compose surface and is audited by the `audit` operation here.
- `android-debugging` diagnoses why a notification never appeared (REQ-16). A wrong channel is
  a decision defect and belongs here; a notification that should appear and does not is a
  runtime defect and belongs there.

## User-language policy

Detect the operator's language and respond in it (German for this operator). Generated
artifacts stay canonical: Kotlin, channel IDs, and identifiers in English; the ledger is
written in English so it stays reviewable alongside the spec corpus; user-visible notification
text is externalized to `strings.xml` per `spec/android/localization/` §A — never inlined in a
builder call.

## Operations

Pick one at the start and say which is running. All three share the gates below. The split is
deliberate: `derive` and `audit` **decide and record**, `apply` **writes**. Nothing is written
into the app before a complete ledger row exists for it.

- **`derive`** — an event exists or is planned and its channel is undecided. Runs steps 1–4
  and the ledger write of step 5. Touches no code.
- **`audit`** — an app already posts notifications and the set needs justifying. Runs step 6
  against the existing call sites, then produces findings plus the ledger rows that are
  missing. Writes only the ledger, never code.
- **`apply`** — a ledger row exists and its device-side code is to be written or corrected.
  Runs steps 5–7.

## Preconditions

Before deciding anything:

- Confirm the working directory is a git repository holding an Android project scaffolded per
  `spec/android/project-structure/`. If there is no Gradle Android module, stop and route to
  `android-project-scaffold`.
- Read `references/gate-chain.md` in full — it is the decision-time rule set distilled from
  the spec, and every event is classified against it.
- Read the existing `project/notification-ledger.md` when one exists; an event already
  recorded there is re-derived, not duplicated.
- Check for uncommitted changes in the paths to be touched. If dirty, report and ask whether
  to stash, commit, or abort — never overwrite unconfirmed work (REQ-8).

## Procedure

Run the steps in order, once per event. Confirm with the operator at each gate before writing.

### 1. State the event

Name the business event in one sentence, as something that happens to or for the user — not
as a technical trigger ("the sync job finished" is a trigger; "the user's order was shipped"
is an event). An event that cannot be stated this way is usually not an event the user needs.
Gate: confirm the statement before classifying.

### 2. Classify on the six axes

Fill all six axes from `references/gate-chain.md`: origination, presence, time sensitivity,
actionability, consequence of missing it, and continuity. Presence is a runtime property, so
record the behaviour for **each** of its three cases rather than assuming one. An axis the
operator cannot answer is a question for them, never a guess.

### 3. Run the gate chain

Walk the gates **in order** and take the first that matches. The ordering is the mechanism by
which the cheaper channel wins, so a later gate is only reached by failing every earlier one.
Record the matched gate **and** the cheaper gate that was rejected, with the reason. Two
outcomes end the run without a channel: the refusal gate (promotional, re-engagement-driven,
or celebratory — reported as out of policy) and the gap gate (a case the spec does not cover
— reported as a spec gap per REQ-6, never resolved by analogy). Gate: confirm the outcome.

### 4. Derive the channel's properties

For a channel-bearing outcome, decide and record: the channel ID and user-visible name, its
**permanent** importance, the `setCategory()` value, lock-screen visibility (with a public
version wherever the content is sensitive), the grouping key and summary behaviour, the update
and cancellation rule, and the degradation behaviour when notifications are off. Where the
outcome is the ongoing family, add its contract — foreground-service type, or the promotion
requirements of a Live Update. Gate: confirm before anything is written.

### 5. Write the ledger row

Write or update `project/notification-ledger.md` per `references/ledger-and-verification.md`:
one row per event, every column filled. An incomplete row is not admitted, and no code is
written for an event that lacks one. Hand every permission the chosen channel implies to
`android-permissions-derive` at this point.

### 6. Apply the device-side code

Read `references/channel-templates.md` and write: the channel creation (guarded by API level,
importance set at creation), the notification build through `NotificationCompat`, the group
and summary where the app can produce more than one of a kind, the cancel and update paths,
and the ongoing contract where it applies. The content intent targets its activity directly —
never a trampoline. User-visible text goes through `strings.xml`. Gate: confirm before each
file that would overwrite existing code (REQ-8).

### 7. Verify and report

Run the verification of `references/ledger-and-verification.md`: the granted, denied, and
channel-blocked states as tests; the Doze and app-standby behaviour for any scheduled or
pushed row; the user-stop and timeout paths for a foreground-service row. Then `./gradlew
build` green (REQ-1). Report, in the operator's language: the events derived and their
matched and rejected gates, the ledger rows written, the permissions handed over, each
verification element that was green, red, or unrunnable and why, and any spec gap found.
Never leave a red or skipped element unreported (REQ-7).

## Reference files

- Read `references/gate-chain.md` before step 2 for the six axes, the ordered gates, and the
  channel catalogue's trade-offs in decision form.
- Read `references/ledger-and-verification.md` in step 5 for the ledger's column contract and
  in step 7 for the verification and test matrix.
- Read `references/channel-templates.md` in step 6 for the channel-creation, notification,
  grouping, foreground-service, and Live-Update templates.

## Resumability

Per `spec/claude/resumable-work/`, this skill is `resumable: true`. State is persisted to
`.resume/android-notification-derive/<run-id>.yml` after every gate and at each named step
boundary. On re-invocation, scan `.resume/android-notification-derive/*.yml` for files with
`status: in_progress` whose `inputs:` snapshot (repository + event name) matches the current
request; when one matches, prompt
`Resume run <run_id> from phase <phase> (last checkpoint <last_checkpoint_at>)? [resume / start-new / discard]`.
`resume` re-hydrates and re-asks no answered gate; `start-new` leaves the old file intact;
`discard` deletes it. Fail closed on unparseable or higher-`schema_version` files. The envelope
keys and lifecycle are load-bearing in the spec and are not duplicated here.

## Hard rules

- **Never** create a channel or write a notification before a complete ledger row exists for
  its event (REQ-21).
- **Never** implement a promotional, re-engagement-driven, or celebratory notification. The
  refusal gate reports it as out of policy — including when the operator asks for it directly,
  in which case the report names the policy rather than complying (REQ-21).
- **Never** change the importance of an existing channel in place; it is immutable after
  creation. A reclassification is a **new** channel, with the old one's retirement recorded in
  the ledger (REQ-21).
- **Never** declare a notification-related permission here. `POST_NOTIFICATIONS`, the
  `FOREGROUND_SERVICE_*` pair, `USE_FULL_SCREEN_INTENT`, and `POST_PROMOTED_NOTIFICATIONS` go
  to `android-permissions-derive` with the ledger row as their justification (REQ-21).
- **Never** post a notification for a surface the user is currently looking at, and never
  demote an ongoing activity to the in-app path because it happened to start on that surface —
  the ongoing gate is evaluated before the presence gate for exactly that reason.
- **Never** route a notification tap through a service or broadcast receiver that then starts
  an activity; the content intent targets the activity directly.
- **Never** ship a custom notification layout, and never let an event exist only as a
  notification — the in-app path is part of every ledger row.
- **Never** resolve a gap-gate outcome by analogy to a neighbouring event; report it (REQ-6).
- **Always** record the matched gate *and* the rejected cheaper gate; a row without the
  rejection is not a derivation, only a preference.
- **Always** end with the verification of step 7 and an explicit report of every red or
  unrunnable element (REQ-7).
- When a spec under `spec/android/` disagrees with this skill, the spec wins — report the gap
  and propose a spec change (REQ-6).

## Gotchas

Concrete corrections to non-obvious facts the executing agent would otherwise get wrong:

- **A channel's behaviour is frozen at creation, not at first use.** Importance, sound,
  vibration, and group membership can never be changed by the app afterwards — only name and
  description can. Getting the importance wrong is not a tuning mistake; it costs a channel.
- **Deleted channels stay visible.** The system settings show a count of deleted channels as a
  spam signal, so churning through channel IDs to fix a wrong importance is itself a cost the
  user sees. On a development device, reinstalling or clearing app data is the way to reset
  test channels.
- **A notification posted to a blocked channel succeeds silently.** `notify()` does not throw
  and returns nothing useful; the notification simply never appears. Only
  `areNotificationsEnabled()` plus the channel's own `getImportance()` distinguish "delivered"
  from "accepted and discarded".
- **A foreground-service notification may not appear for ten seconds.** Android 12 and higher
  defer it, which is right for short work and wrong when the user is waiting to see it —
  `setForegroundServiceBehavior(FOREGROUND_SERVICE_IMMEDIATE)` is the opt-out.
- **Rapid updates are dropped, not queued.** Re-posting the same notification ID many times a
  second is throttled by the system; a progress notification that updates per percent will
  visibly stutter or lag. Update on meaningful change, with `setOnlyAlertOnce(true)`.
