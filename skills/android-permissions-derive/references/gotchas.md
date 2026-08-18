# Gotchas

Concrete corrections to non-obvious facts an executing agent would otherwise get wrong. Read
before step 2 alongside the decision catalog (see `SKILL.md` §Reference files); the three load-bearing ones are also
restated in `SKILL.md`.

- **Declaring a permission can break the permission-free path.** With `CAMERA` declared but not
  granted, `ACTION_IMAGE_CAPTURE` raises a `SecurityException` instead of handing off to the
  system camera. The defensive declaration is the defect.
- **`shouldShowRequestPermissionRationale()` returning `false` is ambiguous by position, not by
  value.** Before the first request it means "no rationale needed — ask"; on a not-granted
  permission *after* a completed request it means "permanently denied". Only the grant state
  plus the recorded request history separate the two, and collapsing them produces an app that
  explains a refusal the user never made and never shows the system dialog
  (`spec/android/permissions/` §E).
- **A granted permission is not a stable property.** One-time grants expire, users revoke in
  settings, and app hibernation resets the set after months of non-use — which also clears the
  cache and stops jobs and notifications from Android 12. Re-check before each access.
- **Permission groups bundle dialogs, not semantics.** Group membership changes without notice,
  so a second permission in the same group must still be checked and requested by name.
- **A foreground service needs three declarations, not one.** Type on the `<service>`, the base
  permission, and the type-specific permission — and the runtime permission the type
  presupposes. Targeting Android 14+, a missing type raises
  `MissingForegroundServiceTypeException` and a missing type permission raises a
  `SecurityException`, both at `startForeground()`.
- **`neverForLocation` has a functional cost.** It filters some BLE beacons out of scan results.
  It is the right default for non-location Bluetooth use, but it is a behaviour change, not a
  free annotation. And its companion `ACCESS_FINE_LOCATION` at `maxSdkVersion="30"` belongs in
  the manifest only while the app still supports API ≤ 30 — at `minSdk` 31+ it can never apply.
- **The granular media permissions do not exist below API 33.** An app with a lower `minSdk`
  that declares only `READ_MEDIA_IMAGES` and friends fails with a `SecurityException` on every
  older device; `READ_EXTERNAL_STORAGE` at `maxSdkVersion="32"` is the other half of the pair.
- **`USE_EXACT_ALARM` is granted automatically — which is exactly why it is restricted.** It is
  not the easy way around `SCHEDULE_EXACT_ALARM`; Play limits it to alarm-clock and
  calendar-style cases, and most scheduling needs neither permission.
- **`SCHEDULE_EXACT_ALARM` starts denied on Android 14+.** For apps targeting API 33 or higher
  the grant is off by default on Android 14+ devices (calendar and alarm-clock apps excepted),
  so `canScheduleExactAlarms()` returning `false` on a fresh install is the normal case, not an
  edge case — the inexact or WorkManager fallback must be a working path.
- **There is no `READ_HEART_RATE_IN_BACKGROUND`.** The Android 16 health permissions pair
  `android.permission.health.READ_HEART_RATE` with the single background permission
  `android.permission.health.READ_HEALTH_DATA_IN_BACKGROUND`; a per-type background name is a
  declaration the platform never grants.
- **Local network access is a runtime permission on Android 17.** `ACCESS_LOCAL_NETWORK`
  (group `NEARBY_DEVICES`) gates local-address sockets, mDNS, SSDP, and `NsdManager` for apps
  targeting API 37+; the Android 16 opt-in preview never enforced it. Verify enforcement status
  at run time and prefer the `NsdManager` discovery picker where the user chooses the device.
- **The two non-runtime notification permissions still need a runtime check.** `canUseFullScreenIntent()`
  (API 34+) and `canPostPromotedNotifications()` (API 36+) are guarded by SDK-version checks;
  the guard code lives in `android-notification-derive`'s `apply` templates, and this skill's
  ledger row records the obligation and step 8 verifies its presence.
- **The merged manifest is where permissions actually come from.** A dependency bump can add a
  permission with no source-manifest edit, which is why the check is re-run after every
  dependency change.
- **`GrantPermissionRule` cannot revoke.** A permission granted through it applies to every test
  in the instrumentation run and attempting to revoke crashes the process — denial coverage is
  established through ADB, not through the rule.
- **A release APK is usually unsigned in these projects.** Without a release signing config the
  artifact is `app-release-unsigned.apk`, so locate the file rather than assuming its name
  before running `apkanalyzer`.
