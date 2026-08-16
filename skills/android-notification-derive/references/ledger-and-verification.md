# Notification ledger and verification

The persistent artifact and the proof. Distilled from `spec/android/notifications-alerting/`
§C (ledger), §G (degradation), and §H (verification); the spec wins on any conflict.

## The ledger

Path: `project/notification-ledger.md`, alongside `project/permissions-ledger.md` and
`project/backend-requirements/`. One row per business event. **A row with an empty column is
not admitted, and no code is written for an event that lacks a row.**

A row whose outcome is **no channel** carries `none` in every column that presupposes one
(channel, category, delivery, grouping, dismissal, degradation) and is still complete: a
silence, presence, or ambient row on its classification, gate, in-app path, and test hook; a
refusal or gap row on its classification and gate alone, because nothing is implemented and
there is nothing to hook a test to.

### Column contract

| Column | Content |
|---|---|
| `Event` | the business event in one sentence, stated as something that happens to or for the user |
| `Classification` | all six axes from `references/gate-chain.md`, comma-separated |
| `Gate` | the gate that matched |
| `Rejected` | the cheaper gate *above* the matched one that was rejected **and the reason** — `n/a` for gates 1, 3, 8, and 9, which either are the cheap outcome (silence, presence) or produce nothing by policy (refusal, gap) |
| `Channel` | channel ID, user-visible name, and importance (or `none` for a no-channel outcome) |
| `Category` | the `setCategory()` constant |
| `Delivery` | `local`, `scheduled`, or `pushed` |
| `Presence behaviour` | what happens in each of the three presence cases |
| `Grouping` | group key and summary behaviour, or `single` |
| `Dismissal` | auto-cancel, timeout, or explicit cancel — and what makes the notification stale |
| `Degradation` | what the user sees when notifications are off or the channel is blocked |
| `In-app path` | where the same information lives in the app, independently of the notification |
| `Permissions` | those handed to `android-permissions-derive`, or `none` |
| `Test hook` | the test that proves this row |

### Row template

```markdown
| Column | Value |
|---|---|
| Event | Order shipped |
| Classification | third-party origination; out-of-app presence; soon; acknowledgement; mild inconvenience; point event |
| Gate | 6 — Await |
| Rejected | 3 — Presence: the user is not in the app when the courier scans the parcel; 5 — Interrupt was not reached because a shipping update has no minutes-scale consequence, so the chain fell through to 6 |
| Channel | `orders_shipping` / "Shipping updates" / `IMPORTANCE_DEFAULT` |
| Category | `CATEGORY_STATUS` |
| Delivery | pushed (data message; a missed message is recovered by the order sync on next foreground) |
| Presence behaviour | on the order screen: inline state only, no notification. Elsewhere in the app: notification, silent. Out of app: notification with sound. |
| Grouping | `orders` group with a constant-ID summary; `GROUP_ALERT_SUMMARY` |
| Dismissal | auto-cancel on tap; cancelled when the order screen is opened; stale once delivered |
| Degradation | the order list shows the shipping state with a "notifications are off" hint and a settings route |
| In-app path | order detail screen, shipping section |
| Permissions | `POST_NOTIFICATIONS` — handed over 2026-08-16 |
| Test hook | `OrderNotificationTest#shippedEvent_postsToShippingChannel_andLandsOnOrderDetail` |
```

### Retirement rows

Importance is immutable after channel creation, so a reclassification is a **new** channel.
Record the retirement in the same file so a later reader does not resurrect it:

```markdown
| Column | Value |
|---|---|
| Event | Order shipped (retired 2026-08-16) |
| Retired channel | `orders_shipping_v1` / `IMPORTANCE_HIGH` |
| Reason | reclassified from interrupt to await: missing a shipping update within minutes has no safety, money, or data consequence |
| Successor | `orders_shipping` |
```

## Verification

Run all of these for every row before reporting the operation complete.

### Required states (rows that carry a channel)

| State | How to establish | Expected |
|---|---|---|
| granted, delivered | `adb shell pm grant <pkg> android.permission.POST_NOTIFICATIONS` | notification appears on the declared channel with the declared importance |
| permission denied | `adb shell pm revoke <pkg> android.permission.POST_NOTIFICATIONS` | no notification; the row's in-app path carries the information |
| channel blocked | set the channel to "None" in system settings, or read back `getImportance()` after the user disabled it | `notify()` succeeds silently; the app detects it and degrades per the row |

The permission-flag commands are owned by `spec/android/adb-workflows/` and specified for this
permission in `spec/android/permissions/` §I. `pm clear-permission-flags` returns the
permission to its never-asked state.

### Delivery states (scheduled and pushed rows)

```bash
adb shell dumpsys deviceidle force-idle     # enter Doze
# … trigger the event; assert the notification is late, not lost
adb shell dumpsys deviceidle unforce
adb shell am set-inactive <pkg> true        # app standby
adb shell am set-inactive <pkg> false
```

The assertion is **not lost, only late**: a pushed row recovers a missed message by state sync
on next foreground, so the test drives the app to foreground and asserts the state is correct
even when the message never arrived.

### Foreground-service rows

```bash
adb shell cmd activity stop-app <pkg>       # simulates the Task Manager Stop
```

Stopping sends no callback; detect it afterwards via `ApplicationExitInfo` with
`REASON_USER_REQUESTED`, and assert no orphaned work remains. Where the type is `dataSync` or
`mediaProcessing`, make the six-hour budget testable in minutes:

```bash
adb shell am compat enable FGS_INTRODUCE_TIME_LIMITS <pkg>
adb shell device_config put activity_manager data_sync_fgs_timeout_duration <ms>
```

Assert that `onTimeout()` stops the service; failing to stop within a few seconds crashes the
app with a `RemoteServiceException`.

### Instrumented assertions

UI Automator is the only supported framework that sees system UI outside the app under test —
use it to assert the notification appears, carries its actions, and opens the right
destination. Where the assertion target is the app's own *decision* rather than the system
rendering, test the channel-selection function directly as a pure unit instead; it is faster
and it is the part that encodes the gate chain.

Verify the content intent's destination as a navigation test per
`spec/android/test-automation/`: a notification that opens the wrong screen fails silently in
production.

### What does not count

- A manual observation on one device is not coverage for a row whose classification claims a
  time-critical consequence.
- A green `notify()` call is not evidence of delivery: a blocked channel accepts it and shows
  nothing.
