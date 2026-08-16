# Gate chain — classification and channel decision

The decision-time rule set, distilled from `spec/android/notifications-alerting/` §B–§D. This
is a working digest, not a source of truth: on any conflict the spec wins.

## Table of contents

- [The six axes](#the-six-axes) — §B
- [The gates, in order](#the-gates-in-order) — §C
- [What each channel buys and costs](#what-each-channel-buys-and-costs) — §D
- [Refusal and gap outcomes](#refusal-and-gap-outcomes) — §C gates 8 and 9

## The six axes

Fill all six before naming any channel. An axis the operator cannot answer is a question for
them, never a guess.

1. **Origination** — did the user start this (they tapped "upload"), did the app's own
   schedule start it (nightly sync), or did a third party (a colleague replied, a courier
   moved)?
2. **Presence** — is the user in the app on the affected surface, in the app elsewhere, or out
   of the app? This is a runtime property: record the behaviour for **all three**, never for
   the one that happens to be true while writing the code.
3. **Time sensitivity** — must the user act now (within a minute), soon (within the day), or
   never on a deadline?
4. **Actionability** — does the event need a decision, an acknowledgement, or nothing?
5. **Consequence of missing it** — safety, money, or data loss; mild inconvenience; or none?
6. **Continuity** — a point event, or an ongoing activity with a distinct start and end that
   the user tracks while it runs?

Two classifications settle themselves and never reach the gates:

- An event that changes nothing the user would do differently gets **no channel**. It updates
  app state and waits to be found.
- A **recoverable** failure — a retry fixes it, the user cannot help — is silent by
  definition. Only a failure whose resolution needs the user continues.

## The gates, in order

Take the **first** gate that matches. The ordering is the mechanism by which the cheaper
channel wins; a later gate is reached only by failing every earlier one. Record the matched
gate *and* the cheaper gate that was rejected, with the reason.

| # | Gate | Matches when | Outcome |
|---|---|---|---|
| 1 | **Silence** | nothing the user would do differently changes | no channel; app state only |
| 2 | **Ongoing activity** | user-initiated activity with a start and end, tracked while it runs — navigation, a ride, a delivery, a workout, playback; **not** a call, which is third-party-initiated and belongs to gate 4 | foreground-service notification, `ProgressStyle` / Live Update, or media notification |
| 3 | **Presence** | a **point event** *and* the user is on the affected surface | in-app surface only (`android-compose-ui`) |
| 4 | **Conversation** | real-time interpersonal communication | `MessagingStyle` + long-lived shortcut, or `CallStyle` — this gate also owns the call's full-screen intent, checked with `canUseFullScreenIntent()` before use |
| 5 | **Interrupt** | missing it within minutes costs safety, money, or data **and** the user can act | high-importance channel (heads-up); a full-screen intent here only for an **alarm**, the calling half belonging to gate 4 |
| 6 | **Await** | relevant today, no interruption warranted | default- or low-importance channel, silent where the user did not initiate it |
| 7 | **Ambient** | a state to glance at repeatedly, not an occurrence to be told about | a widget, plus a badge only where the app's own navigation carries it — a launcher badge is a consequence of a posted notification and is never the outcome for an out-of-app event; where no widget is placed, the outcome is gate 1's |
| 8 | **Refusal** | promotional, re-engagement-driven, or celebratory | no channel; reported as out of policy |
| 9 | **Gap** | nothing above matched and it is not a policy violation | no channel; reported as a spec gap (REQ-6) |

**Why ongoing sits before presence.** An ongoing activity is almost always started from the
very screen it affects. Classifying by presence first would route navigation, workouts, and
deliveries into the in-app path — exactly the activities the ongoing family exists for — and
the decision is never revisited when the user leaves that screen a second later.

**Why presence is restricted to point events.** Presence is evaluated once, but it changes
constantly. An event whose relevance outlives the current session is not decided by where the
user happens to be looking right now.

## What each channel buys and costs

Ordered from cheapest to most intrusive. Each entry is the short form of the spec's §D
catalogue; read that section when an entry's trade-off is what the decision turns on.

- **No channel** — costs the user nothing, cannot be revoked, cannot be wrong; the user learns
  of it when they next open the app. The default outcome.
- **In-app surface** — full presentation control, no permission, no revocation risk; reaches
  nobody who is not in the app right now, and needs its own accessibility path.
- **Badge** — persistent, ambient, silent; carries no content, no timing, no action. On the
  launcher it is a *consequence* of a posted notification, so it stands alone only inside the
  app's own navigation.
- **Widget** — persistent glanceable state, user-placed and therefore consented; tells nobody
  anything at the moment the event happens, and must be built and kept fresh.
- **Low / minimum importance** — persists in the drawer, carries content and actions, makes no
  sound; minimum importance stays out of the status bar. Spends the app-wide permission budget
  and is easily unseen for hours. **The correct default for the await gate.**
- **Default importance** — adds a sound; an interruption in contexts the app cannot see.
- **High importance (heads-up)** — appears over the foreground app; the highest revocation
  risk in the catalogue. The interrupt gate only, and rarely.
- **Group + summary** — keeps a multi-event stream legible and confines alerting to the
  summary; needs a constant summary ID and update discipline. Mandatory as soon as the app can
  produce more than one notification of a kind at once.
- **Conversation (`MessagingStyle` + shortcut)** — the conversation section, direct reply,
  bubbles, correct ranking; requires publishing and maintaining long-lived sharing shortcuts.
- **`CallStyle`** — call-shaped layout with system-managed actions and top-of-shade ranking;
  legitimate only for actual calls, and needs a foreground service to rank correctly on older
  versions.
- **Full-screen intent** — takes over the screen; since Android 14 granted by default only to
  calling and alarm apps. Treat a design that needs it as a misclassification until proven
  otherwise.
- **Foreground-service notification** — the app keeps running and the notification makes that
  visible; the heaviest option (type declaration, permission pair, background-start
  restrictions, Task-Manager stop, dismissible since Android 14, six-hour daily budget for
  `dataSync` and `mediaProcessing`). Only where work must continue *and* be noticeable now.
- **Live Update / `ProgressStyle`** — promoted placement plus a status-bar chip; needs
  `POST_PROMOTED_NOTIFICATIONS`, an explicit promotion request, ongoing flag, content title, a
  permitted style, and forbids custom layouts, group summaries, colorization, and minimum
  importance. Only for user-initiated, ongoing, continuously time-sensitive activity.
- **Media notification** — the system media carousel; requires a real `MediaSession`.
- **Out-of-band (email, SMS, push to another device)** — reaches a user who revoked
  notifications, but is outside the app and outside this repository's scope: capture it as a
  backend requirement, never as a workaround for a denial.

## Refusal and gap outcomes

Both end the run without a channel, and they are **not** the same thing.

**Refusal (gate 8).** The event is promotional, re-engagement-driven, or celebratory. The
platform's own design guidance and Play policy both put it out of bounds. Report it as out of
policy — including when the operator asks for it directly. The report names the rule, offers
the legitimate alternative where one exists (an in-app surface, a widget, an email the backend
sends), and does not implement the notification.

**Gap (gate 9).** The event matched nothing above and is not a policy violation either: it is
a case the spec does not cover. Report it as a spec gap per REQ-6 and propose the spec
extension. Do **not** pick the nearest-looking gate by analogy — that is how a corpus silently
grows a rule nobody wrote down.
