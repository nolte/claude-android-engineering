# Permission Ledger and Verification

The persistent artifact and the commands that prove it, per `spec/android/permissions/` §B
(ledger), §H (verification), and §I (testing). ADB mechanics themselves are owned by
`spec/android/adb-workflows/`; the commands below are the permission-specific uses of them.

---

## 1. The ledger

One row per permission in the final set. A permission with an incomplete row is not admitted —
that rule is what makes the set derived rather than accumulated.

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
apkanalyzer manifest permissions app/build/outputs/apk/release/app-release.apk
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
