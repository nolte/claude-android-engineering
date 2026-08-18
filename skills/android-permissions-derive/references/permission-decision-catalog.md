# Permission Decision Catalog

The decision surface for `android-permissions-derive`, distilled from
`spec/android/permissions/` §A (the model), §C (alternatives), §D (declaration), §E (runtime
flow), and §F (families). The spec is authoritative; this file is the working form. Every entry
carries the spec section that governs it so a disagreement is resolved upward rather than
locally. Entries marked **spec-extension proposed (REQ-6)** are not yet in the spec: they are
platform facts this skill needs and has reported as a proposed spec extension; treat them as
provisional and verify against the primary source at run time.

## Table of contents

- [0. Type classification and the model (§A)](#0-type-classification-and-the-model-a)
- [1. The alternatives gate (§C)](#1-the-alternatives-gate-c)
- [2. Declaration details (§D)](#2-declaration-details-d)
- [3. Runtime-flow details (§E)](#3-runtime-flow-details-e)
- [4. Families whose rules differ (§F)](#4-families-whose-rules-differ-f)
- [5. Store-side declaration obligations (§G)](#5-store-side-declaration-obligations-g)

---

## 0. Type classification and the model (§A)

Classify every candidate before reasoning about it — the type decides the whole handling and is
the `Type` column of the ledger row:

| Type | Protection level | Granted by | Handling |
| --- | --- | --- | --- |
| install-time normal | `normal` | the system at install | declaration only; no request, no denial path |
| install-time signature | `signature` | only to apps signed with the defining certificate | declaration only; custom permissions live here (§2) |
| runtime | `dangerous` | the user through the system prompt | full §E flow: check → rationale → request → branch → degrade |
| special | `appop` | only through the Special App Access settings page | dedicated check method, settings intent, `onResume()` re-check |

Two non-runtime notification permissions (`USE_FULL_SCREEN_INTENT`, `POST_PROMOTED_NOTIFICATIONS`)
are declared at install time but behave like special permissions at runtime — see §4
Notifications.

Record, per row, which permission-model surface the user meets (§A SHOULD): the Privacy
Dashboard timeline, the camera and microphone indicators, and the device-wide sensor toggles
(Android 12+) that hand the app a blank camera feed or silent audio rather than an error — a
granted `CAMERA` with the toggle off is not a denial, and the degradation path must not report
it as one.

---

## 1. The alternatives gate (§C)

Consult this table for the stated feature **before** any permission is admitted. A permission is
admitted only when the alternative provably does not serve the feature, and the reason is
recorded in the ledger.

| Feature, stated as a user outcome | Permission-free path | Permission avoided |
| --- | --- | --- |
| The user picks photos or videos | Android photo picker (temporary access to the selection) | `READ_MEDIA_IMAGES`, `READ_MEDIA_VIDEO` |
| The user picks a document or non-media file | Storage Access Framework | storage permissions |
| The app reads or writes files it created itself | App-specific storage or `MediaStore` | storage permissions |
| The user takes a photo | `ACTION_IMAGE_CAPTURE` to the system camera app | `CAMERA` |
| The user records a video | `ACTION_VIDEO_CAPTURE` to the system camera app | `CAMERA` |
| The user scans a code | Google code scanner — decision owned by `spec/android/barcode-scanning/` §A | `CAMERA` |
| The user needs one precise location, once | System location button | `ACCESS_FINE_LOCATION` |
| The app needs a rough area | `ACCESS_COARSE_LOCATION`, or an address the user types | `ACCESS_FINE_LOCATION` |
| The app must recognise this install | `UUID.randomUUID()` persisted in app storage, or a Firebase Installations ID (the Instance ID library it replaces is deprecated) | hardware-identifier permissions |
| The user pairs a companion device | Companion Device Pairing | location and Bluetooth-admin permissions |
| A one-time passcode is entered automatically | SMS Retriever API | `READ_SMS` |
| The user's phone number is verified or prefilled | Digital Credentials API, or Phone Number Hint | `READ_PHONE_STATE` |
| Spam calls are filtered | `CallScreeningService` | `READ_PHONE_STATE` |
| Playback pauses on an interruption | `onAudioFocusChange()` handler | `READ_PHONE_STATE` |
| The user places a call | `ACTION_DIAL` (user confirms) | `CALL_PHONE` |
| The user picks one or a few contacts | Contact Picker (Android 17, API 37: `ContactsPickerSessionContract.ACTION_PICK_CONTACTS`, requested fields as MIME types, temporary read grant on the result) — the system picker returns only the selected entries (spec §C [R35]); below API 37 keep `Intent.ACTION_PICK` on the contacts provider as the permission-free path | `READ_CONTACTS` |
| The user picks a device on the local network | `NsdManager` discovery with `DiscoveryRequest.FLAG_SHOW_PICKER` (Android 17: the system picker returns the chosen service) or the Output Switcher for media routes (spec §F [R31][R33]) | `ACCESS_LOCAL_NETWORK` |
| A payment card is captured | The Google payment-card recognition path (`getPaymentCardRecognitionIntent`), which returns the result without the app opening a camera — **not** card-scan SDKs in general, most of which do require `CAMERA` — **spec-extension proposed (REQ-6)** | `CAMERA`, on that path only |

**Two traps to apply, not rediscover:**

- Declaring `CAMERA` while relying on `ACTION_IMAGE_CAPTURE` makes that intent raise a
  `SecurityException` when the permission is not granted. The defensive declaration is the
  defect.
- A third-party SDK's permission requirement reaches the user as the app's own request. Audit
  the SDK, replace it, or remove its permission per §D — never adopt it by default.

---

## 2. Declaration details (§D)

### Scoping attributes

| Situation | Declaration |
| --- | --- |
| Permission needed only up to an API level | `android:maxSdkVersion="<level>"` on the `<uses-permission>` |
| Bluetooth scanning that never derives location | `android:usesPermissionFlags="neverForLocation"` on `BLUETOOTH_SCAN`; add `ACCESS_FINE_LOCATION` bounded at `maxSdkVersion="30"` **only** when the app still supports API ≤ 30 — at `minSdk` 31+ it is omitted entirely |
| Wi-Fi device discovery that never derives location | `android:usesPermissionFlags="neverForLocation"` on `NEARBY_WIFI_DEVICES` (Android 13+); `ACCESS_FINE_LOCATION` bounded at `maxSdkVersion="32"` only while the app still supports API ≤ 32 and only for APIs that need no location on 33+ (see §4 Nearby Wi-Fi devices) |
| Legacy Bluetooth on old devices | `BLUETOOTH` and `BLUETOOTH_ADMIN` at `maxSdkVersion="30"` |
| Legacy external storage write | `WRITE_EXTERNAL_STORAGE` at `maxSdkVersion="29"` |
| Hardware the app can live without | `<uses-feature android:name="…" android:required="false" />` plus a `PackageManager.hasSystemFeature()` check at the call site |

Cost to state when applying `neverForLocation`: some BLE beacons are filtered out of scan
results, and on Wi-Fi the APIs that reveal scan results or the connected network's identity stay
location-gated regardless of the flag. It is the right default for non-location nearby-device
use and still a behaviour change.

### Foreground services — three declarations plus a prerequisite

```xml
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_LOCATION" />
<!-- plus the runtime permission the type presupposes, here a location permission -->
<service
    android:name=".TrackingService"
    android:foregroundServiceType="location"
    android:exported="false" />
```

Prerequisites per type — the spec (§D, §F) names `camera`, `microphone`, and `location`; the
rest of this list is **spec-extension proposed (REQ-6)** and is verified against the
foreground-service-types reference at run time: `camera` → `CAMERA`; `microphone` →
`RECORD_AUDIO`; `location` → a granted location permission; `connectedDevice` → one of the
Bluetooth, NFC, USB, or network-state permissions; `health` → a health or activity-recognition
permission; `phoneCall` → `MANAGE_OWN_CALLS` or the dialer role; `dataSync`, `mediaPlayback`,
`mediaProcessing`, `remoteMessaging` → none; `shortService` → none, and no type permission
either; `specialUse` → `FOREGROUND_SERVICE_SPECIAL_USE` plus the
`PROPERTY_SPECIAL_USE_FGS_SUBTYPE` property explaining the case.

Targeting Android 14+, a missing type raises `MissingForegroundServiceTypeException` and a
missing type permission raises `SecurityException`, both at `startForeground()`. Both are
declaration errors that only surface at runtime.

### Package visibility

```xml
<queries>
    <package android:name="com.example.partnerapp" />
    <intent>
        <action android:name="android.intent.action.SEND" />
        <data android:mimeType="text/plain" />
    </intent>
</queries>
```

`QUERY_ALL_PACKAGES` only with a recorded justification that targeted queries cannot express the
need; it is Play-restricted and needs approval.

### Removing a library-injected permission

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:tools="http://schemas.android.com/tools">

    <uses-permission
        android:name="android.permission.ACCESS_FINE_LOCATION"
        tools:node="remove"
        tools:selector="com.example.analyticssdk" />
</manifest>
```

Omit `tools:selector` to remove every contribution of that permission; keep it when only one
library's contribution is meant. Record the removal in the ledger so a dependency bump does not
silently reinstate it.

### Custom permissions

Only to restrict access to the app's own components, and only at
`android:protectionLevel="signature"`. A `normal`-level custom permission is granted to every
app that asks, and the naming-collision and definition-ordering pitfalls make weaker levels
unsafe. Where such a permission guards a component it is applied as `android:permission` on
the `<activity>` / `<service>` / `<receiver>`, or as `android:readPermission` /
`android:writePermission` on a `<provider>`. **Broadcast-receiver trap:** a denied broadcast is
simply not delivered — the receiver's permission check never raises an error, so a test that
waits for an exception proves nothing. The surrounding component hardening (`android:exported`,
`PendingIntent` immutability, explicit intents) belongs to `spec/android/security/` §D.

---

## 3. Runtime-flow details (§E)

The flow itself is stated in `SKILL.md` step 7; these are the details that make it conformant.

- **`@ExperimentalPermissionsApi` containment (MUST where used).** Where the Compose wrappers
  `rememberPermissionState` / `rememberMultiplePermissionsState` are used, the opt-in is
  confined to **one** wrapper type in one file (a module-local `PermissionRequester` or
  equivalent); it does not leak into feature modules, screens, or ViewModels via
  `@OptIn` annotations spread across call sites. The wrapper also cannot distinguish a first
  request from a permanent denial on its own — the request history the wrapper records is what
  does.
- **State holder, not composition.** Permission state lives in a ViewModel or equivalent and
  requests are driven from user events (SHOULD).
- **Data-access rationale activity (SHOULD).** Where the app accesses location, camera, or
  microphone in ways a user may not expect, expose an activity handling
  `android.intent.action.VIEW_PERMISSION_USAGE` (and `VIEW_PERMISSION_USAGE_FOR_PERIOD` for the
  Privacy Dashboard entry) that explains the access. Record the decision in the ledger row.
- **`revokeSelfPermissionOnKill()` / `revokeSelfPermissionsOnKill()` (MAY, Android 13+).**
  Proactively drop a permission the app no longer needs; the call is asynchronous and kills the
  app's processes, and clearing a group's user-visible state requires revoking every permission
  in that group. Record it as a removal row.

---

## 4. Families whose rules differ (§F)

### Location

- `ACCESS_COARSE_LOCATION` unless precision is functionally required; handle the case where the
  user grants approximate although precise was requested, and upgrade only on an explicit user
  step.
- `ACCESS_BACKGROUND_LOCATION` is separate from Android 10 (API 29), requested **only after** a
  foreground grant, and Play-restricted — the store obligation goes in the ledger.
- Continuous foreground access runs in a `location`-typed foreground service.

### Media and storage

- The app's own media needs no permission under scoped storage (targeting Android 10+).
- Other apps' media: `READ_MEDIA_IMAGES` / `READ_MEDIA_VIDEO` / `READ_MEDIA_AUDIO` (Android
  13+), with `READ_MEDIA_VISUAL_USER_SELECTED` for the partial-access grant (Android 14+). On
  Android 16+ with partial access, the app's own photos are pre-selected in the picker.
- **Below API 33 the granular permissions do not exist.** An app whose `minSdk` is lower must
  additionally declare `READ_EXTERNAL_STORAGE` at `maxSdkVersion="32"` for those devices;
  declaring only the granular set fails with a `SecurityException` on every device below 33.
- `ACCESS_MEDIA_LOCATION` only for unredacted EXIF location metadata.
- `MANAGE_EXTERNAL_STORAGE` is a special permission restricted by Play to core file-management
  functionality — never a convenience.
- `android:requestLegacyExternalStorage="true"` is a temporary opt-out, not a design.

### Notifications

- `POST_NOTIFICATIONS` is a runtime permission from Android 13 (API 33), covering all channels
  including foreground-service notifications.
- Targeting API 33+, the app chooses the moment — after the user has met the value the
  notifications serve, never at first launch. Targeting 32 or lower, the system shows the dialog
  itself when a channel is created and an activity starts; that is a reason to target 33+, not a
  behaviour to rely on.
- **The channel decision comes first.** `POST_NOTIFICATIONS`, a `FOREGROUND_SERVICE_*` pair,
  `USE_FULL_SCREEN_INTENT`, and `POST_PROMOTED_NOTIFICATIONS` are each a *consequence* of an
  alerting channel already derived through the gate chain of
  `spec/android/notifications-alerting/` §C, owned by `android-notification-derive` (REQ-21),
  which produces a row in `project/notification-ledger.md`. Take that row as the input to the
  §B derivation: the named event it carries *is* the user-visible feature the permission traces
  back to. Deriving one of these without it is the backward derivation §B forbids — there is no
  feature to name, only a manifest entry someone wanted.
- **In an `audit` of an existing app** the notification-ledger row will often be missing
  entirely: that is a finding, not a dead end. Report it as a `Critical` finding naming the
  notification the manifest implies and the missing channel derivation as the follow-up the app
  owes (a `derive` run of `android-notification-derive` first, then of this skill) — never admit
  the permission on the strength of the manifest that already contains it. The `derive` run
  that follows writes the ordinary ledger row (no new row shape) with the feature column naming
  the notification and the alternative column naming the channel derivation it rests on.
- The channel also decides *which* of them applies, so the gate chain's outcome is worth reading
  before the derivation: an in-app outcome needs no permission at all, and neither does a badge
  the app draws in its own navigation — a *launcher* badge is a consequence of a posted
  notification and therefore carries that notification's permission; an ordinary notification
  needs only `POST_NOTIFICATIONS`; an ongoing activity adds the foreground-service type and its
  permission pair (`spec/android/notifications-alerting/` §D); a promoted Live Update adds
  `POST_PROMOTED_NOTIFICATIONS`; and a full-screen intent is admissible only for calling and
  alarm surfaces, whose rule lives in `spec/android/notifications-alerting/` §C (gate 4 for
  calls, gate 5 for alarms).
- **The two non-runtime notification permissions behave like special permissions at runtime.**
  `USE_FULL_SCREEN_INTENT`: declared at install time; for apps targeting Android 14+ Play
  revokes the default grant from every app that is not a calling or alarm app; check
  `NotificationManager.canUseFullScreenIntent()` (API 34+) immediately before use, degrade to an
  ordinary high-importance notification, and route to
  `Settings.ACTION_MANAGE_APP_USE_FULL_SCREEN_INTENT` only on an explicit user step.
  `POST_PROMOTED_NOTIFICATIONS` (Android 16): declared as a non-runtime permission, user-switchable
  per app; check `NotificationManager.canPostPromotedNotifications()` (API 36+) before relying on
  promotion, keep a working non-promoted notification, and route to
  `Settings.ACTION_APP_NOTIFICATION_PROMOTION_SETTINGS` with `Settings.EXTRA_APP_PACKAGE`
  (API 36) only on an explicit user step, and only after `intent.resolveActivity(packageManager)
  != null` confirmed a handler exists — the constant is fixed by spec §F [R32] (the Live-Update
  guide's prose name does not exist in the SDK) and is verified against the
  `android.provider.Settings` reference of the SDK in use.
- **Guard-code ownership, stated at the boundary.** The SDK-version guards around
  `canUseFullScreenIntent()` (`SDK_INT >= 34`) and `canPostPromotedNotifications()`
  (`SDK_INT >= 36`), the degradation branch, and the settings-intent launch are written by the
  `apply` templates of `android-notification-derive` (its gate-4 call block and its Live-Update
  block). This skill records the obligation — the check
  method, the API-level guard, the degradation, and the settings route — in the permission
  ledger row and verifies at step 8 that the guard exists in the code, but does not write it.

### Bluetooth and nearby devices

- Targeting Android 12+: `BLUETOOTH_SCAN`, `BLUETOOTH_ADVERTISE`, `BLUETOOTH_CONNECT` are
  runtime permissions shown as "Nearby devices". Declare only what the actual operations need.
- Apply `neverForLocation` and the legacy bounds from §2.

### Nearby Wi-Fi devices

- Targeting Android 13+ (API 33), the Wi-Fi APIs that discover or connect to nearby devices —
  Wi-Fi Aware, Wi-Fi Direct, local-only hotspot, Wi-Fi RTT ranging, network suggestions and
  specifiers — need the runtime permission `NEARBY_WIFI_DEVICES` (group "Nearby devices")
  instead of a location permission.
- Apply `android:usesPermissionFlags="neverForLocation"` whenever the app never derives location
  from Wi-Fi results; only then can the location permission be dropped for API 33+, bounded at
  `maxSdkVersion="32"` while older devices are supported. Without the flag, both permissions
  are needed on 33+.
- The exceptions stay location-gated on every version: `WifiManager.getScanResults()`,
  `startScan()`, and the connected network's identity (SSID/BSSID via connection info) still
  need `ACCESS_FINE_LOCATION` — establish each API's requirement from its reference (§B), not
  from the family rule.
- The family is governed by `spec/android/permissions/` §F [R38]: it is distinct from local-network
  access — a Wi-Fi-Aware or Wi-Fi-Direct feature does not by itself justify `ACCESS_LOCAL_NETWORK`,
  nor the reverse. Verify individual API requirements against the Wi-Fi permissions reference.

### Exact alarms

- Establish first that the case genuinely needs exactness. Scheduling, syncing, and periodic
  work use `setWindow()`, `setAndAllowWhileIdle()`, or WorkManager and need neither permission.
- `USE_EXACT_ALARM`: granted automatically, not user-revocable, Play-restricted to alarm-clock
  and calendar-style cases.
- `SCHEDULE_EXACT_ALARM`: user-granted, not pre-granted on fresh installs from Android 13, and
  **denied by default on Android 14+ devices for apps targeting API 33 or higher** (only
  calendar and alarm-clock apps keep the pre-grant). Requires a `canScheduleExactAlarms()` check
  before each use and a receiver for `ACTION_SCHEDULE_EXACT_ALARM_PERMISSION_STATE_CHANGED` to
  reschedule when the grant changes; the degradation path is an inexact alarm or WorkManager,
  recorded in the ledger row.

### Health and body sensors

- From Android 16, granular health permissions replace `BODY_SENSORS` /
  `BODY_SENSORS_BACKGROUND`: foreground heart-rate access is
  `android.permission.health.READ_HEART_RATE`, and background access to any health data is the
  single permission `android.permission.health.READ_HEALTH_DATA_IN_BACKGROUND` (there is no
  per-type `*_IN_BACKGROUND` permission). They also govern `Sensor.TYPE_HEART_RATE` and the
  `health` foreground-service type.
- An app whose `minSdk` is below 36 additionally declares the legacy pair `BODY_SENSORS` /
  `BODY_SENSORS_BACKGROUND` bounded at `maxSdkVersion="35"` alongside the new names and requests
  each set on the platform level that knows it (§F [R37]).
- A mobile app using them must expose a privacy-policy activity or the permissions are revoked.
- Play restricts health and fitness data to approved purposes — a ledger declaration obligation.

### Local network access

- **Android 17 (API 37) enforces Local Network Protection** for apps targeting 37 or higher:
  access to local-network addresses — raw sockets, mDNS, SSDP, `NsdManager` resolution — needs
  the new runtime permission `ACCESS_LOCAL_NETWORK` (group `NEARBY_DEVICES`). Android 16
  shipped it as an opt-in preview only (`adb shell am compat enable RESTRICT_LOCAL_NETWORK
  <package>`), which is where the earlier `NEARBY_WIFI_DEVICES`-based wording of the spec came
  from.
- Permission-free alternative first (§C): where the user picks a device or service, the
  `NsdManager` discovery picker (`DiscoveryRequest.FLAG_SHOW_PICKER`) or the Output Switcher for
  media routes serves the feature without the permission.
- **Verify the current enforcement status, the target-SDK threshold, and the permission's
  availability on the target `minSdk` against the primary source at run time** rather than
  trusting this paragraph — the spec's §F is settled (Android 17 enforcement, [R31][R33]) and
  itself requires this run-time re-check for later widening of the restricted operations.

### Restricted by policy rather than by API

`READ_SMS` and the call-log permissions require the app to be the default handler;
`AccessibilityService` use is bounded by Play policy. Both are already forbidden as
conveniences by `spec/android/security/` §E and are admitted only through the declaration path
of `spec/android/permissions/` §G.

---

## 5. Store-side declaration obligations (§G)

Record in the ledger and hand to the operator — filing is the operator's act, discovery is this
skill's:

- SMS and call-log permissions
- `MANAGE_EXTERNAL_STORAGE`
- `QUERY_ALL_PACKAGES`
- `ACCESS_BACKGROUND_LOCATION`
- Broad photo and video access
- Health and fitness data
- `AccessibilityService`
- Every foreground service type, for apps targeting Android 14+
- `USE_FULL_SCREEN_INTENT`, for apps targeting Android 14+ — Play removes the default grant from
  any app it does not judge to be a calling or alarm app, so declaring it is a category claim the
  store reviews (`spec/android/permissions/` §F/§G)

No skill edits store metadata, listings, or the Data Safety questionnaire.
