# Channel and notification templates

Device-side code shapes for the `apply` operation. Distilled from
`spec/android/notifications-alerting/` §F; the spec wins on any conflict. Every user-visible
string goes through `strings.xml` per `spec/android/localization/` §A — the literals below are
placeholders for resource lookups, not a licence to inline text.

## Table of contents

- [Channel creation](#channel-creation)
- [The notification build](#the-notification-build)
- [Grouping and summary](#grouping-and-summary)
- [Conversation and call (gate 4)](#conversation-and-call-gate-4)
- [Update, cancel, and staleness](#update-cancel-and-staleness)
- [Foreground-service notification](#foreground-service-notification)
- [Live Update / ProgressStyle](#live-update--progressstyle)
- [Checking before relying on the channel](#checking-before-relying-on-the-channel)

## Channel creation

Create every channel before its first use, at app start or at feature entry. Importance is
fixed here **permanently** — the ledger row's importance column is what this argument reads.
**One channel per type of event the user would want to control separately** — never one per
notification site, and never one per feature module; the channel set stays small and semantic
(spec §C).

```kotlin
object NotificationChannels {
    const val ORDERS_SHIPPING = "orders_shipping"

    fun ensureCreated(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = context.getSystemService(NotificationManager::class.java) ?: return
        manager.createNotificationChannel(
            NotificationChannel(
                ORDERS_SHIPPING,
                context.getString(R.string.channel_orders_shipping_name),
                NotificationManager.IMPORTANCE_DEFAULT,
            ).apply {
                description = context.getString(R.string.channel_orders_shipping_description)
                setShowBadge(true)
            },
        )
    }
}
```

Re-creating an existing channel with unchanged values is a no-op and safe. Changing the
importance argument on an existing ID does **nothing** — that is why a reclassification needs
a new ID plus a retirement row.

Channel *groups* exist for parallel account or profile scopes, not for organizing an app's own
feature areas. Register the group **before** the channel that joins it —
`manager.createNotificationChannelGroup(NotificationChannelGroup(groupId, groupName))`, then
`channel.setGroup(groupId)` before `createNotificationChannel`. Calling `setGroup()` with an
unregistered group ID raises no error; the channel simply appears ungrouped, and nobody notices
until a user opens notification settings.

## The notification build

```kotlin
// The tap lands on the content AND leaves a plausible back stack behind it — back from a
// notification must not drop the user out of the app (spec §E, app-design-navigation §E).
val contentIntent = TaskStackBuilder.create(context)
    .addNextIntentWithParentStack(
        Intent(context, MainActivity::class.java).apply {
            data = orderDeepLink(orderId)  // deep link to the content the notification is about
        },
    )
    .getPendingIntent(
        requestCode,
        PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
    )

val notification = NotificationCompat.Builder(context, NotificationChannels.ORDERS_SHIPPING)
    .setSmallIcon(R.drawable.ic_notification_order)      // alpha-only, iconography §D
    .setContentTitle(context.getString(R.string.order_shipped_title))
    .setContentText(context.getString(R.string.order_shipped_text, orderNumber))
    .setCategory(NotificationCompat.CATEGORY_STATUS)
    .setVisibility(NotificationCompat.VISIBILITY_PRIVATE)
    .setPublicVersion(publicVersion)                     // wherever content is sensitive
    .setPriority(NotificationCompat.PRIORITY_DEFAULT)    // legacy devices, matches importance
    .setContentIntent(contentIntent)
    .setAutoCancel(true)
    .build()
```

Rules the template encodes:

- The content intent targets the **activity directly**. Routing through a service or receiver
  that then calls `startActivity()` is blocked from Android 12 (notification trampoline).
- The destination carries a synthetic back stack (`TaskStackBuilder`, or the navigation
  library's equivalent) so Back from the notification walks up the hierarchy instead of leaving
  the app — the deep-link rules of `spec/android/app-design-navigation/` §E apply unchanged.
- `PendingIntent` is immutable unless a direct reply genuinely needs otherwise
  (`spec/android/security/` §D).
- At most three actions, none duplicating the tap action.
- No `setCustomContentView()`: the system re-decorates custom layouts into a standard template
  from Android 12, and the Live-Update surface rejects them outright.
- Title under 30 characters, preview text under 40, and never the app name — the system renders
  it already (spec §F SHOULD). Longer content goes into `BigTextStyle`, not the title.
- Lock-screen visibility per the ledger's `Visibility` column: `VISIBILITY_PRIVATE` plus
  `setPublicVersion()` for sensitive content, `VISIBILITY_SECRET` where even the presence is
  sensitive; the public version is also what screen sharing shows.
- `setLocalOnly(true)` for a notification meaningful only on the producing device (a
  foreground-service progress the wearable cannot act on); otherwise let bridging to a paired
  Wear OS device happen and control it by bridge tags rather than disabling it globally.
- Accessibility: from Android 16 (API 36) `announceForAccessibility()` and `TYPE_ANNOUNCEMENT`
  are deprecated — an in-app surface chosen at the presence gate carries its own accessibility
  path (live region, pane title, error semantics), never an announcement of the event.

## Grouping and summary

Mandatory as soon as the app can produce more than one notification of a kind concurrently.
Do not rely on the platform's automatic grouping — its behaviour varies by version and device.

**Promoted Live Updates are the exception and are never grouped** — not even with `setGroup()`
alone. The promotion contract forbids a group summary, so two concurrent Live Updates of a kind
stay two separate promoted notifications.

```kotlin
private const val GROUP_ORDERS = "com.example.app.ORDERS"
// Constant, so the summary is updated rather than stacked — and **reserved**: per-item IDs
// must never collide with it, or the child overwrites the summary and one of the two is lost.
// Derive item IDs from a range that excludes the summary IDs (or from a stable hash offset).
private const val SUMMARY_ID = 1

val child = NotificationCompat.Builder(context, channelId)
    .setGroup(GROUP_ORDERS)
    .setGroupAlertBehavior(NotificationCompat.GROUP_ALERT_SUMMARY)
    // …
    .build()

val summary = NotificationCompat.Builder(context, channelId)
    .setSmallIcon(R.drawable.ic_notification_order)
    .setStyle(
        NotificationCompat.InboxStyle()
            .setBigContentTitle(context.getString(R.string.orders_summary_title))
            .setSummaryText(context.getString(R.string.orders_summary_text)),
    )
    .setGroup(GROUP_ORDERS)
    .setGroupSummary(true)
    .build()

// POST_NOTIFICATIONS is a runtime permission on API 33+; NotificationManagerCompat.notify is
// @RequiresPermission — guard every call (lint MissingPermission is error-level per the permission skill).
if (Build.VERSION.SDK_INT < 33 || ContextCompat.checkSelfPermission(
        context, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) {
    NotificationManagerCompat.from(context).apply {
        notify(orderNotificationId, child)
        notify(SUMMARY_ID, summary)
    }
}
```

## Update, cancel, and staleness

```kotlin
// update: same ID, alert only once
NotificationManagerCompat.from(context).notify(
    orderNotificationId,
    builder.setOnlyAlertOnce(true).setProgress(100, percent, false).build(),
)

// self-expiring
builder.setTimeoutAfter(TimeUnit.HOURS.toMillis(6))

// explicit: the event was handled elsewhere
NotificationManagerCompat.from(context).cancel(orderNotificationId)
```

The ledger's `Dismissal` column names what makes this row stale — the offer expired, the user
acted in the app, the order arrived. Cancelling then is not politeness: a drawer full of
irrelevant notifications is what precedes an app-wide block.

Rapid updates are throttled by the system. Update on meaningful change, not per frame or per
percent.

## Conversation and call (gate 4)

A gate-4 row is **not** served by the standard build above. Without a long-lived shortcut the
notification is not a conversation notification at all on Android 11 and higher, whatever style
it carries.

```kotlin
// 1. Publish the long-lived sharing shortcut the notification will bind to.
val shortcut = ShortcutInfoCompat.Builder(context, conversationId)
    .setLongLived(true)
    .setShortLabel(partner.displayName)
    .setPerson(partner.toPerson())
    .setCategories(setOf("com.example.category.SHARE_TARGET"))
    .setIntent(conversationIntent(conversationId))
    .build()
ShortcutManagerCompat.pushDynamicShortcut(context, shortcut)

// 2. Bind it, and use MessagingStyle for messages …
val notification = NotificationCompat.Builder(context, NotificationChannels.MESSAGES)
    .setSmallIcon(R.drawable.ic_notification_message)
    .setShortcutId(conversationId)          // required — this is what makes it a conversation
    .addPerson(partner.toPerson())
    .setStyle(
        NotificationCompat.MessagingStyle(self.toPerson())
            .addMessage(message.text, message.timestamp, partner.toPerson()),
    )
    .addAction(replyAction)                 // RemoteInput: expected, not optional
    .build()

// … or CallStyle for calls, which the ongoing gate hands here.
val incoming = NotificationCompat.Builder(context, NotificationChannels.CALLS)
    .setSmallIcon(R.drawable.ic_notification_call)
    .setStyle(NotificationCompat.CallStyle.forIncomingCall(caller, declineIntent, answerIntent))
    .addPerson(caller)
    .setOngoing(true)
    .build()
```

A call additionally runs a foreground service so it ranks correctly on older versions, and its
full-screen intent — the one surface the platform still grants to calling apps — is guarded:

```kotlin
// canUseFullScreenIntent() exists from API 34; below it the declared permission is simply held.
val fullScreenAllowed = Build.VERSION.SDK_INT < Build.VERSION_CODES.UPSIDE_DOWN_CAKE ||
    notificationManager.canUseFullScreenIntent()
if (fullScreenAllowed) {
    builder.setFullScreenIntent(fullScreenPendingIntent, true)
} else {
    // No grant: the CallStyle notification alone must remain answerable (high importance).
    // Offer the settings route only on an explicit user step, never as a startup interruption:
    // Intent(Settings.ACTION_MANAGE_APP_USE_FULL_SCREEN_INTENT, Uri.parse("package:$packageName"))
}
```

This guard, its degradation branch, and the settings-intent launch are **owned here** (the
`apply` operation); `android-permissions-derive` records the same obligation in its
`USE_FULL_SCREEN_INTENT` ledger row and verifies the guard exists, but does not write it.

## Foreground-service notification

```kotlin
val notification = NotificationCompat.Builder(context, NotificationChannels.TRACKING)
    .setSmallIcon(R.drawable.ic_notification_tracking)
    .setContentTitle(context.getString(R.string.tracking_active))
    .addAction(R.drawable.ic_stop, context.getString(R.string.stop), stopIntent)  // required
    .setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE)
    .setOngoing(true)
    .build()

ServiceCompat.startForeground(
    this,
    NOTIFICATION_ID,           // positive, never 0
    notification,
    ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION,
)
```

- The notification carries a **stop affordance**; the user must be able to end the work from it.
- `FOREGROUND_SERVICE_IMMEDIATE` opts out of the ten-second deferral — correct when the user is
  waiting to see it, wrong for short work that will finish before it matters.
- The service handles being stopped from the Task Manager (Android 13+) and its notification
  being dismissed (Android 14+) without leaving orphaned work.
- The service type and its permission pair come from `android-permissions-derive`.

## Live Update / ProgressStyle

Only for a user-initiated, ongoing, continuously time-sensitive activity. The full contract
must hold before promotion is requested. Permitted styles: the standard (no-style) template,
`BigTextStyle`, `CallStyle`, `ProgressStyle` (Android 16), and `MetricStyle` (Android 17 — up
to three metrics and three actions, with semantic colours via `createSemanticStyleAnnotation()`);
every other style disqualifies the notification from promotion. Compat path: `NotificationCompat.ProgressStyle`
and `setRequestPromotedOngoing()` ship in `androidx.core:core` 1.17+ and no-op below API 36,
so one build serves every version; for `MetricStyle`, check whether the `androidx.core`
release in use wraps it — until it does, build it behind `SDK_INT >= 37` with `ProgressStyle`
or the standard template as the fallback (skill refinement; spec §D names `MetricStyle`, the
compat handling is proposed as a spec extension, REQ-6).

```kotlin
val notification = NotificationCompat.Builder(context, channelId)   // not IMPORTANCE_MIN
    .setSmallIcon(R.drawable.ic_navigation)
    .setContentTitle(context.getString(R.string.delivery_en_route))  // required
    .setOngoing(true)                                                // required
    .setRequestPromotedOngoing(true)                                 // required
    .setStyle(NotificationCompat.ProgressStyle().setProgress(percent)) // a permitted style
    .setShortCriticalText(context.getString(R.string.eta_minutes, eta))
    .setDeleteIntent(dismissedIntent)                                // required: never re-post
    .build()

// canPostPromotedNotifications() exists from API 36; below it there is no promoted surface.
val promotable = Build.VERSION.SDK_INT >= 36 && notificationManager.canPostPromotedNotifications()
if (!promotable) {
    // post the same event as an ordinary ongoing notification (the working fallback);
    // offer the settings route only on an explicit user step, and only if a handler exists —
    // the Settings reference warns that a matching activity may be absent (permissions spec §F [R32]):
    // val intent = Intent(Settings.ACTION_APP_NOTIFICATION_PROMOTION_SETTINGS)
    //     .putExtra(Settings.EXTRA_APP_PACKAGE, packageName)
    // if (intent.resolveActivity(packageManager) != null) startActivity(intent)
}
```

Forbidden on a promoted notification: custom layouts, `setGroupSummary(true)`,
`setColorized(true)`, a minimum-importance channel. Keep the non-promoted fallback working —
OEMs may enforce additional criteria. A Live Update the user dismissed is **never** re-posted.
The SDK guard, its fallback branch, and the settings-intent launch are **owned here**;
`android-permissions-derive` records the obligation in its `POST_PROMOTED_NOTIFICATIONS`
ledger row and verifies the guard exists, but does not write it.

## Checking before relying on the channel

```kotlin
val manager = NotificationManagerCompat.from(context)
val enabled = manager.areNotificationsEnabled()
// Channels exist only from API 26. Below it, getNotificationChannel() always returns null,
// so treating null as IMPORTANCE_NONE would report "notifications are off" on every
// pre-O device that is in fact working.
val channelBlocked = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O &&
    manager.getNotificationChannel(channelId)?.importance == NotificationManager.IMPORTANCE_NONE

if (!enabled || channelBlocked) {
    // degrade per the ledger row: the in-app path carries the information,
    // the app says what is unavailable, and offers a settings route
}
```

Settings routes: `Settings.ACTION_APP_NOTIFICATION_SETTINGS` for the app level,
`Settings.ACTION_CHANNEL_NOTIFICATION_SETTINGS` with `EXTRA_CHANNEL_ID` for one channel. The
app does not re-prompt into a dialog the system will no longer show.

The `POST_NOTIFICATIONS` request itself is derived and wired by `android-permissions-derive`;
what this skill supplies is the trigger and the rationale text: tied to the first moment the
user opts into an event class, and the **rationale names that event class** ("get told when
your order ships"), never a generic "allow notifications". Where the channel model alone is too
coarse — frequency, quiet hours, per-topic subscription — expose the app's own notification
preferences (spec §G SHOULD) and keep them consistent with the system channels rather than
duplicating them; the preference screen is authored by `android-compose-ui`.
