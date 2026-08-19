# Permission Ledger and Verification

The persistent artifact and the commands that prove it, per `spec/android/permissions/` §B
(ledger), §H (verification), and §I (testing), plus the read-only audit procedure. ADB mechanics themselves are owned by
`spec/android/adb-workflows/`; the commands below are the permission-specific uses of them.

## Table of contents

- [1. The ledger](#1-the-ledger) — who writes it, the row template, removal rows, the
  non-runtime notification rows
- [2. Verifying the actual set](#2-verifying-the-actual-set) — merged manifest, artifact,
  device, lint
- [3. Establishing the test states](#3-establishing-the-test-states) — ADB state setup,
  `GrantPermissionRule`, what each state asserts
- [4. Audit procedure (operation `audit`)](#4-audit-procedure-operation-audit) — read-only,
  severity-classified report

---

## 1. The ledger

One row per permission in the final set. A permission with an incomplete row is not admitted —
that rule is what makes the set derived rather than accumulated.

Who writes it: `derive` writes the row at `SKILL.md` step 5, after trigger point, denial
behaviour, and store obligation are decided; `apply` fills the **Declared as** and **Tests**
lines at steps 6 and 8 as it writes them. `audit` writes nothing — its report names the rows
the app owes and the `derive` run that would write them.

Location: `project/permissions-ledger.md`, fixed by `spec/android/permissions/` §B — alongside
the requirement and backend-requirement artifacts under `project/`. Not a per-project choice.

### Row template

```markdown
### `android.permission.CAMERA`

- **Type:** runtime (`dangerous`)
- **Feature:** the user photographs a damaged part while filing a report
- **API:** `CameraX ProcessCameraProvider.bindToLifecycle(...)` — live preview with an in-app
  overlay is required, so the capture intent does not serve the feature
- **Alternative considered:** `ACTION_IMAGE_CAPTURE` — rejected: the report flow needs the
  measurement overlay drawn on the live preview, which the system camera app cannot render
- **Declared as:** `<uses-permission android:name="android.permission.CAMERA" />` plus
  `<uses-feature android:name="android.hardware.camera" android:required="false" />`
- **Requested at:** the "Add photo" action in the report screen, after the rationale sheet
- **On denial:** the report is filed without a photo; the photo row shows "Camera unavailable —
  enable in settings" with a settings route. Nothing else in the flow is blocked
- **Store obligation:** none
- **Tests:** `ReportPhotoPermissionTest` covers granted, denied, permanently denied
```

Optional lines, used where they apply: **Runtime check:** for a special permission or one of the
two non-runtime notification permissions (the check method, its API-level guard, and the
settings intent — see below); **Model surface:** where the Privacy Dashboard, the camera or
microphone indicator, or a device-wide sensor toggle changes what "granted" means for this
permission (`spec/android/permissions/` §A).

### Rows that record a removal

```markdown
### `android.permission.ACCESS_FINE_LOCATION` — removed

- **Source:** injected by `com.example.analyticssdk:core:4.2.0`
- **Reason for removal:** no feature of this app derives or uses location; the SDK's regional
  reporting works without it
- **Removed with:** `tools:node="remove" tools:selector="com.example.analyticssdk"`
- **Re-check:** on every bump of that dependency (§H requires re-verification after dependency
  changes)
```

### Rows for the non-runtime notification permissions

`USE_FULL_SCREEN_INTENT` and `POST_PROMOTED_NOTIFICATIONS` are declared at install time but
behave like special permissions at runtime. Their row's **Feature** line names the notification
ledger row (`project/notification-ledger.md`) the permission follows from, and the **Runtime
check** line records the obligation that this skill verifies but does not implement:

```markdown
### `android.permission.POST_PROMOTED_NOTIFICATIONS`

- **Type:** install-time (non-runtime), user-switchable per app — handled like special
- **Feature:** the user tracks their active delivery on the lock screen and status bar
  (notification ledger row "Delivery en route", gate 2, Live Update)
- **API:** `NotificationCompat.Builder.setRequestPromotedOngoing(true)`
- **Alternative considered:** a non-promoted ongoing notification — kept as the fallback,
  rejected as the primary surface because the ETA must be glanceable without opening the drawer
- **Declared as:** `<uses-permission android:name="android.permission.POST_PROMOTED_NOTIFICATIONS" />`
- **Requested at:** never (no dialog); the settings route is offered from the delivery screen on
  an explicit user step
- **Runtime check:** `canPostPromotedNotifications()` guarded by `SDK_INT >= 36`; on `false`
  the non-promoted notification is posted; settings route
  `Settings.ACTION_APP_NOTIFICATION_PROMOTION_SETTINGS` + `EXTRA_APP_PACKAGE`. Guard code owned
  by `android-notification-derive` (`apply`, Live-Update template); presence verified at step 8
- **On denial:** the same event stays visible as an ordinary ongoing notification and on the
  delivery screen
- **Store obligation:** none (`USE_FULL_SCREEN_INTENT` rows carry the Android 14+ category
  claim instead)
- **Tests:** `DeliveryLiveUpdateTest` covers promoted, promotion-off, notifications-off
```

---

## 2. Verifying the actual set

### The merged manifest — the only evidence that counts

```bash
# Build the variant so the merge actually runs.
./gradlew :app:assembleRelease

# The merger's decision log: which element came from which manifest, and why.
cat app/build/outputs/logs/manifest-merger-release-report.txt

# The merged manifest itself (path is AGP-version dependent — locate it rather than assume it).
find app/build/intermediates -name AndroidManifest.xml -path '*merged*'
```

Read the permission set out of the merged result, never out of `app/src/main/AndroidManifest.xml`.

### The built artifact — the strongest check

```bash
# Locate the artifact rather than assuming its name — without a release signing config the
# file is app-release-unsigned.apk, which is the normal case for a scaffolded project.
APK=$(find app/build/outputs/apk/release -name '*.apk' | head -1)
apkanalyzer manifest permissions "$APK"
```

This prints exactly what the package declares, after every merge. Diff it against the ledger:
each side must account for the other completely.

### The installed app on a device

```bash
# Grant state plus the denial flags: USER_SET = denied once, USER_FIXED = permanently denied.
adb shell dumpsys package <package> | sed -n '/runtime permissions/,/^$/p'

# Enumerate the platform's runtime permissions by group.
adb shell pm list permissions -d -g
```

### Lint

`MissingPermission` runs as an error, so a protected call without a check fails the build rather
than the user's device. The lint-severity wiring is owned by `spec/android/security/` §F.

---

## 3. Establishing the test states

Every permission in the ledger is covered in three states. Set them deterministically rather
than by tapping dialogs.

```bash
PKG=com.example.app
PERM=android.permission.CAMERA

# Granted
adb shell pm grant $PKG $PERM

# Never asked (the true initial state — clearing the flags is what resets it)
adb shell pm revoke $PKG $PERM
adb shell pm clear-permission-flags $PKG $PERM user-set user-fixed

# Denied once  (shouldShowRequestPermissionRationale() -> true)
adb shell pm revoke $PKG $PERM
adb shell pm set-permission-flags $PKG $PERM user-set
adb shell pm clear-permission-flags $PKG $PERM user-fixed

# Permanently denied  (shouldShowRequestPermissionRationale() -> false)
adb shell pm revoke $PKG $PERM
adb shell pm set-permission-flags $PKG $PERM user-set user-fixed
```

Full state reset, when a test needs a clean install rather than a permission reset:

```bash
adb shell pm clear $PKG    # wipes data and revokes runtime permissions
```

Special permissions have no runtime dialog and are toggled as app-ops:

```bash
adb shell appops set $PKG SCHEDULE_EXACT_ALARM allow
adb shell appops set $PKG MANAGE_EXTERNAL_STORAGE deny
```

### `GrantPermissionRule` — what it can and cannot do

```kotlin
@get:Rule
val permissionRule: GrantPermissionRule =
    GrantPermissionRule.grant(Manifest.permission.CAMERA)
```

It **only grants**. It is ignored below API 23, the grant applies to every test in the
instrumentation run, and there is no way to revoke — attempting to do so crashes the
instrumentation process. Use it to get an unrelated test past a dialog; never as the mechanism
for denial coverage, which is established with the ADB commands above.

`adb install -g` pre-grants everything and is acceptable for hermetic runs that are not about
permissions — such a run does not count as coverage of the granted state.

### What each state must assert

| State | Assertion |
| --- | --- |
| Granted | The protected work runs, and the permission was re-checked immediately before it |
| Denied once | The rationale is shown before the re-request; the degraded path is reachable |
| Permanently denied | No system dialog is attempted; the explanation plus the settings route appears |
| Special permission returning from settings | The `onResume()` re-check picks up the new state |

---

## 4. Audit procedure (operation `audit`)

Read-only throughout. Nothing is written — not the ledger, not the manifest, not tests. (This
replaces the earlier behaviour in which `audit` wrote ledger rows and tests; it now mirrors the
read-only `audit` of `android-notification-derive`.)

1. **Enumerate the surface.** The merged permission set (§2 commands), every `<uses-feature>`,
   `<queries>`, foreground-service type, and `tools:node="remove"` marker, and every
   `checkSelfPermission` / request / special-permission check call site.
2. **Reconcile against the ledger.** Read `project/permissions-ledger.md` where it exists. A
   declared permission with no row, and a row with no declaration, are both findings.
3. **Re-derive each declared permission** as a candidate that must earn its row: `SKILL.md`
   steps 1–3 against the feature it implies, then compare with what the manifest and code do.
   A permission a permission-free alternative serves, and a library-injected one no feature
   needs, are the findings this operation exists for. A notification permission with no
   notification-ledger row behind it is a finding that routes to `android-notification-derive`
   first (see the Notifications family of the decision catalog named in `SKILL.md` §Reference files).
4. **Check the declaration and runtime rules** of the catalog per permission: `maxSdkVersion`
   bounds, `neverForLocation`, the foreground-service triple, `<queries>`, the SDK guards the
   ledger records, permanent-denial handling, no startup bundle, `MissingPermission` at error.
5. **Report** on the canonical severity scale of `spec/claude/review-plan/`: `Critical` for a
   declared permission with no traceable feature, a permission-free alternative ignored, a
   missing notification-ledger row behind a notification permission, or a `MissingPermission`
   lint finding; `Warning` for a declaration or runtime rule broken; `Suggestion` for a
   narrower permission or bound the app would now qualify for; `Info` for a surface scanned
   clean. Each finding carries the file and line, the spec section, and the operation
   (`derive`, `apply`) that would fix it — turning a finding into a row is a `derive` run the
   operator starts afterwards.
