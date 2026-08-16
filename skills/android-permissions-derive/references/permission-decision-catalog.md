# Permission Decision Catalog

The decision surface for `android-permissions-derive`, distilled from
`spec/android/permissions/` §C (alternatives), §D (declaration), and §F (families). The spec is
authoritative; this file is the working form. Every entry carries the spec section that governs
it so a disagreement is resolved upward rather than locally.

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
| The app must recognise this install | `UUID.randomUUID()` persisted in app storage, or Instance ID | hardware-identifier permissions |
| The user pairs a companion device | Companion Device Pairing | location and Bluetooth-admin permissions |
| A one-time passcode is entered automatically | SMS Retriever API | `READ_SMS` |
| The user's phone number is verified or prefilled | Digital Credentials API, or Phone Number Hint | `READ_PHONE_STATE` |
| Spam calls are filtered | `CallScreeningService` | `READ_PHONE_STATE` |
| Playback pauses on an interruption | `onAudioFocusChange()` handler | `READ_PHONE_STATE` |
| The user places a call | `ACTION_DIAL` (user confirms) | `CALL_PHONE` |
| A payment card is captured | The Google payment-card recognition path (`getPaymentCardRecognitionIntent`), which returns the result without the app opening a camera — **not** card-scan SDKs in general, most of which do require `CAMERA` | `CAMERA`, on that path only |

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
| Legacy Bluetooth on old devices | `BLUETOOTH` and `BLUETOOTH_ADMIN` at `maxSdkVersion="30"` |
| Legacy external storage write | `WRITE_EXTERNAL_STORAGE` at `maxSdkVersion="29"` |
| Hardware the app can live without | `<uses-feature android:name="…" android:required="false" />` plus a `PackageManager.hasSystemFeature()` check at the call site |

Cost to state when applying `neverForLocation`: some BLE beacons are filtered out of scan
results. It is the right default for non-location Bluetooth use and still a behaviour change.

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

Prerequisites per type (spec §D, §F): `camera` → `CAMERA`; `microphone` → `RECORD_AUDIO`;
`location` → a granted location permission; `connectedDevice` → one of the Bluetooth, NFC, USB,
or network-state permissions; `health` → a health or activity-recognition permission;
`phoneCall` → `MANAGE_OWN_CALLS` or the dialer role; `dataSync`, `mediaPlayback`,
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
app that asks. The component-hardening side belongs to `spec/android/security/` §D.

---

## 3. Families whose rules differ (§F)

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

### Bluetooth and nearby devices

- Targeting Android 12+: `BLUETOOTH_SCAN`, `BLUETOOTH_ADVERTISE`, `BLUETOOTH_CONNECT` are
  runtime permissions shown as "Nearby devices". Declare only what the actual operations need.
- Apply `neverForLocation` and the legacy bounds from §2.

### Exact alarms

- Establish first that the case genuinely needs exactness. Scheduling, syncing, and periodic
  work use `setWindow()`, `setAndAllowWhileIdle()`, or WorkManager and need neither permission.
- `USE_EXACT_ALARM`: granted automatically, not user-revocable, Play-restricted to alarm-clock
  and calendar-style cases.
- `SCHEDULE_EXACT_ALARM`: user-granted, not pre-granted on fresh installs from Android 13.
  Requires a `canScheduleExactAlarms()` check before each use and a receiver for
  `ACTION_SCHEDULE_EXACT_ALARM_PERMISSION_STATE_CHANGED` to reschedule when the grant changes.

### Health and body sensors

- From Android 16, granular health permissions (for example `READ_HEART_RATE`,
  `READ_HEART_RATE_IN_BACKGROUND`) replace `BODY_SENSORS` / `BODY_SENSORS_BACKGROUND`; they also
  govern `Sensor.TYPE_HEART_RATE` and the `health` foreground-service type.
- A mobile app using them must expose a privacy-policy activity or the permissions are revoked.
- Play restricts health and fitness data to approved purposes — a ledger declaration obligation.

### Local network access

Android 16 introduces a `NEARBY_WIFI_DEVICES`-gated local-network restriction as an opt-in
preview (`adb shell am compat enable RESTRICT_LOCAL_NETWORK <package>`), with enforcement
announced for a later release. **Verify the current enforcement status against the primary
source at run time** rather than trusting this paragraph; when it applies, raw socket use to
local addresses, mDNS, SSDP, and `NsdManager` fall in scope.

### Restricted by policy rather than by API

`READ_SMS` and the call-log permissions require the app to be the default handler;
`AccessibilityService` use is bounded by Play policy. Both are already forbidden as
conveniences by `spec/android/security/` §E and are admitted only through the declaration path
of `spec/android/permissions/` §G.

---

## 4. Store-side declaration obligations (§G)

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

No skill edits store metadata, listings, or the Data Safety questionnaire.
