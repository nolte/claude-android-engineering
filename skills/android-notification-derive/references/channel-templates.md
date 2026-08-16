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
feature areas: `NotificationChannelGroup(groupId, groupName)` and `setGroup(groupId)` before
registration.

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

## Grouping and summary

Mandatory as soon as the app can produce more than one notification of a kind concurrently.
Do not rely on the platform's automatic grouping — its behaviour varies by version and device.

**Promoted Live Updates are the exception and are never grouped** — not even with `setGroup()`
alone. The promotion contract forbids a group summary, so two concurrent Live Updates of a kind
stay two separate promoted notifications.

```kotlin
private const val GROUP_ORDERS = "com.example.app.ORDERS"
private const val SUMMARY_ID = 1  // constant, so the summary is updated rather than stacked

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

NotificationManagerCompat.from(context).apply {
    notify(orderNotificationId, child)
    notify(SUMMARY_ID, summary)
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
if (notificationManager.canUseFullScreenIntent()) {
    builder.setFullScreenIntent(fullScreenPendingIntent, true)
} else {
    // No grant: the CallStyle notification alone must remain answerable.
    // Route the user to Settings.ACTION_MANAGE_APP_USE_FULL_SCREEN_INTENT only on an
    // explicit user step, never as a startup interruption.
}
```

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
must hold before promotion is requested:

```kotlin
val notification = NotificationCompat.Builder(context, channelId)   // not IMPORTANCE_MIN
    .setSmallIcon(R.drawable.ic_navigation)
    .setContentTitle(context.getString(R.string.delivery_en_route))  // required
    .setOngoing(true)                                                // required
    .setRequestPromotedOngoing(true)                                 // required
    .setShortCriticalText(context.getString(R.string.eta_minutes, eta))
    .setDeleteIntent(dismissedIntent)                                // required: never re-post
    .build()
```

Forbidden on a promoted notification: custom layouts, `setGroupSummary(true)`,
`setColorized(true)`, a minimum-importance channel. Check `canPostPromotedNotifications()`
before relying on the surface, and keep a working non-promoted fallback — OEMs may enforce
additional criteria. A Live Update the user dismissed is **never** re-posted.

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
