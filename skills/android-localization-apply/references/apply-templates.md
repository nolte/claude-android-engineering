# Apply templates

Templates for the `apply` operation. Every block traces to a `spec/android/localization/`
(L10N), `spec/android/iconography/` (ICON), or `spec/android/project-structure/` (PS)
requirement; the spec, not this file, is normative. This is a **structural contract**, not a
version manifest — resolve concrete AGP/AndroidX versions at apply time (REQ-5) and never
pin one here. Every write into an existing file is confirmed per hunk (REQ-8).

## Table of contents

- [1. Lint severities](#1-lint-severities)
- [2. Build script](#2-build-script)
- [3. Manifest](#3-manifest)
- [4. String externalisation and repair](#4-string-externalisation-and-repair)
- [5. Adding a language](#5-adding-a-language)
- [6. In-app language picker](#6-in-app-language-picker)
- [7. Locale-correct code](#7-locale-correct-code)
- [8. Previews](#8-previews)
- [9. Verification: pseudolocale and font-scale pass](#9-verification-pseudolocale-and-font-scale-pass)

## 1. Lint severities

Root `lint.xml` (PS §G places it centrally; the severities are MUSTs of L10N §A/§B). Merge
these `<issue>` rows into an existing file — never replace it, never add a baseline entry
that suppresses them:

```xml
<lint>
  <issue id="HardcodedText" severity="error" />
  <issue id="MissingTranslation" severity="error" />
  <issue id="ExtraTranslation" severity="error" />
  <issue id="ImpliedQuantity" severity="error" />
  <issue id="RtlHardcoded" severity="error" />
</lint>
```

`RtlHardcoded` is not named by the spec; it is the lint surface of §D's "start/end everywhere"
MUST and is added under that section. The module's `lint { lintConfig = rootProject.file("lint.xml"); abortOnError = true }`
block must point at the file — check it exists before relying on the severities.

## 2. Build script

App module `build.gradle.kts` (L10N §B/§C/§E), Kotlin DSL only (REQ-9):

```kotlin
android {
    androidResources {
        localeFilters += listOf("en", "de")   // the agreed set, BCP-47 tags
        generateLocaleConfig = true           // pairs with res/resources.properties
    }
    buildTypes {
        debug { isPseudoLocalesEnabled = true }
    }
}
```

`app/src/main/res/resources.properties`:

```properties
unqualifiedResLocale=en
```

**Migration from `resourceConfigurations`.** `resourceConfigurations` (and the older
`resConfigs`) is deprecated since AGP 8.8; `androidResources.localeFilters` replaces its
language part (L10N §B [R11]). Replace it in the same hunk — the two must never coexist. On an
AGP older than the cut-over, report the version gap and route to `android-toolchain-upgrade`;
do not write the deprecated form. Density entries in the old list have no successor (Play
requires App Bundles): drop them and say so in the report.

**Manual alternative** when `generateLocaleConfig` cannot be used (multi-module resource
ownership the operator does not want to move): `res/xml/locales_config.xml` with one
`<locale android:name="…"/>` per supported tag, wired via `android:localeConfig` (§3). Keep
exactly one of the two mechanisms; the manual file's set must equal `localeFilters`.

## 3. Manifest

`app/src/main/AndroidManifest.xml` (L10N §C/§D):

```xml
<application
    android:supportsRtl="true"
    ...>                       <!-- add android:localeConfig="@xml/locales_config" only for the manual variant -->

    <!-- Persists AppCompatDelegate.setApplicationLocales() below Android 13 (L10N §C).
         Redundant but harmless when minSdk >= 33. -->
    <service
        android:name="androidx.appcompat.app.AppLocalesMetadataHolderService"
        android:enabled="false"
        android:exported="false">
        <meta-data
            android:name="autoStoreLocales"
            android:value="true" />
    </service>
</application>
```

`android:exported` is set explicitly per `spec/android/security/` §D; the service is
`enabled="false"` by design — AppCompat reads only its meta-data.

## 4. String externalisation and repair

Naming: `<feature>_<what>` (`settings_language_title`, `common_cancel`); shared strings under
`common_`. One sentence is one string; the number and every untouchable segment are
placeholders. Read in composables via `stringResource` / `pluralStringResource`, elsewhere via
`context.getString` / `resources.getQuantityString`.

```xml
<resources xmlns:xliff="urn:oasis:names:tc:xliff:document:1.2">
    <!-- Brand token: stays in values/ only, never translated (L10N §A/§E) -->
    <string name="app_name" translatable="false">Example</string>

    <!-- Settings > Language: title of the picker screen. Max ~24 chars. -->
    <string name="settings_language_title">Language</string>
    <string name="settings_language_system_default">System default</string>

    <!-- Home: greeting with the user's display name (positional placeholder) -->
    <string name="home_greeting">Hello, %1$s!</string>

    <!-- Order list: count of items; the number stays in the text (ImpliedQuantity) -->
    <plurals name="orders_item_count">
        <item quantity="one">%1$d item</item>
        <item quantity="other">%1$d items</item>
    </plurals>

    <!-- Untouchable segment wrapped for translators (L10N §A SHOULD) -->
    <string name="account_signed_in_as">Signed in as <xliff:g id="email" example="a@b.de">%1$s</xliff:g></string>

    <!-- User-visible options reference strings, never index-matched prose (L10N §A MUST NOT) -->
    <string name="theme_option_light">Light</string>
    <string name="theme_option_dark">Dark</string>
    <string-array name="theme_options" translatable="false">
        <item>@string/theme_option_light</item>
        <item>@string/theme_option_dark</item>
    </string-array>
</resources>
```

Repair patterns (each confirmed per file, REQ-8):

| Finding | Before | After |
|---|---|---|
| Inlined text | `Text("Hello, $name!")` | `Text(stringResource(R.string.home_greeting, name))` |
| Sequential placeholders | `Hello %s, you have %d items` | `Hello %1$s, you have %2$d items` |
| Concatenation | `stringResource(R.string.a) + " " + stringResource(R.string.b)` | one string `%1$s … %2$s` or a full-sentence key |
| Count via `if` | `if (n == 1) "1 item" else "$n items"` | `pluralStringResource(R.plurals.orders_item_count, n, n)` |
| `translatable="false"` in a translated file | entry in `values-b+de/` | delete from the translated file; keep in `values/` |
| Index-matched user text | `<string-array>` of prose | per-item `@string` entries as above |

## 5. Adding a language

Directory form: `res/values-b+<lang>/` (`values-b+de/`, `values-b+pt+BR/`) — BCP-47 per
L10N §B SHOULD. Never create it beside an existing legacy `values-<lang>/` for the same
language (same qualifier, split key set); migrate the directory with confirmation or keep the
legacy form and record it.

Seed the new `strings.xml` with the **same key set** as `values/`, minus every
`translatable="false"` entry. Values are the English source (or a drafted translation when
the operator asks); mark the file so the draft state is visible in review and in the report:

```xml
<?xml version="1.0" encoding="utf-8"?>
<!-- DRAFT: seeded from values/strings.xml on <date>; every string below needs
     human review before a release round (spec/android/localization/ §E). -->
<resources>
    <string name="settings_language_title">Sprache</string>
    ...
</resources>
```

Key-set check (read-only; also the §E completeness heuristic when lint is relaxed):

```sh
diff <(grep -o 'name="[^"]*"' app/src/main/res/values/strings.xml | sort) \
     <(grep -o 'name="[^"]*"' app/src/main/res/values-b+de/strings.xml | sort)
```

Lines only in `values/` are missing translations (acceptable transiently, listed in the
report); lines only in the translated file are `ExtraTranslation` errors and are removed.
Extend `localeFilters` (§2) in the same plan item; the generated locale config follows.

## 6. In-app language picker

L10N §C: `AppCompatDelegate` (host activity is an `AppCompatActivity`, also in Compose apps),
argument via `LocaleListCompat.forLanguageTags`, reset via `getEmptyLocaleList()`, call on the
main thread (it may recreate the activity), options derived from the declared locale config —
never a second hard-coded list.

```kotlin
// ui/language/SupportedLocales.kt
object SupportedLocales {
    /** Language tags from the declared locale config (L10N §C). */
    fun load(context: Context): List<String> =
        if (Build.VERSION.SDK_INT >= 33) {
            val list = LocaleConfig(context).supportedLocales ?: LocaleList.getEmptyLocaleList()
            (0 until list.size()).map { list[it].toLanguageTag() }
        } else {
            parseLocaleConfig(context.resources.getXml(LOCALE_CONFIG_RES))
        }

    private fun parseLocaleConfig(parser: XmlResourceParser): List<String> = buildList {
        while (parser.eventType != XmlPullParser.END_DOCUMENT) {
            if (parser.eventType == XmlPullParser.START_TAG && parser.name == "locale") {
                parser.getAttributeValue(ANDROID_NS, "name")?.let(::add)
            }
            parser.next()
        }
    }

    // The resource generated by generateLocaleConfig; for a manual file use R.xml.locales_config.
    // Verify the generated resource name against the AGP release in use at apply time (REQ-5);
    // where it cannot be resolved below API 33, report the gap (REQ-6) rather than hard-coding a list.
    private val LOCALE_CONFIG_RES = R.xml._generated_res_locale_config
    private const val ANDROID_NS = "http://schemas.android.com/apk/res/android"
}
```

```kotlin
// ui/language/LanguagePicker.kt — content composable; the route/screen it lives in belongs to
// android-compose-ui when it is new. Runs on the main thread (called from a click handler).
@Composable
fun LanguagePicker(
    supportedTags: List<String>,
    modifier: Modifier = Modifier,
) {
    val current = AppCompatDelegate.getApplicationLocales()
    val selectedTag = current.toLanguageTags().takeIf { it.isNotEmpty() }
    Column(modifier) {
        LanguageOption(
            label = stringResource(R.string.settings_language_system_default),
            selected = selectedTag == null,
            onSelect = { AppCompatDelegate.setApplicationLocales(LocaleListCompat.getEmptyLocaleList()) },
        )
        supportedTags.forEach { tag ->
            val locale = Locale.forLanguageTag(tag)
            LanguageOption(
                label = locale.getDisplayName(locale).replaceFirstChar { it.titlecase(locale) },
                selected = selectedTag == tag,
                onSelect = { AppCompatDelegate.setApplicationLocales(LocaleListCompat.forLanguageTags(tag)) },
            )
        }
    }
}
```

`LanguageOption` is a selectable row (`Modifier.selectable(role = Role.RadioButton)`) from the
app's design system; the label uses each locale's own display name so every option is
readable regardless of the current language. Persistence: the `autoStoreLocales` service (§3)
below Android 13; the framework stores it from 13 on. `LocaleManager` directly only when
`minSdk >= 33` (§C MAY).

**Dropped language reset** (§C SHOULD) — in `Application.onCreate()` after AppCompat is
initialised, or in the picker host:

```kotlin
val stored = AppCompatDelegate.getApplicationLocales()
if (!stored.isEmpty && stored[0]?.toLanguageTag() !in supportedTags) {
    AppCompatDelegate.setApplicationLocales(LocaleListCompat.getEmptyLocaleList())
}
```

**Grammatical inflection** (§C SHOULD, API 34+, optional plan item): expose the addressee's
grammatical gender through `GrammaticalInflectionManager.setRequestedApplicationGrammaticalGender()`
guarded by `Build.VERSION.SDK_INT >= 34`, ship `values-b+de-feminine/`, `-masculine/`,
`-neuter/` sets for the inflected strings only, keep the ungendered form in `values-b+de/`;
declare `grammaticalGender` in `configChanges` only when the activity handles the change itself.

## 7. Locale-correct code

L10N §D — patch each Kotlin file only for the finding named in the plan:

| Finding | Replace with |
|---|---|
| `SimpleDateFormat("dd.MM.yyyy")` / `ofPattern("…")` for display | `DateTimeFormatter.ofLocalizedDate(FormatStyle.MEDIUM)`; custom shape via `DateFormat.getBestDateTimePattern(locale, "yMMMd")` (`android.text.format`); relative time via `DateUtils.getRelativeTimeSpanString` |
| `"$amount €"` / `"%.2f".format(x)` for display | `NumberFormat.getCurrencyInstance(locale).format(amount)` / `NumberFormat.getInstance(locale)` — `android.icu.text.NumberFormat` where `minSdk >= 24` |
| `key.lowercase()` on identifiers / `equalsIgnoreCase` on enum names | `key.lowercase(Locale.ROOT)` / compare after `Locale.ROOT` normalisation |
| `sortedBy { it.title }` on user-visible text | `sortedWith(compareBy(Collator.getInstance(locale)) { it.title })` |
| Phone / address / username inside a translated sentence | `BidiFormatter.getInstance().unicodeWrap(value)` before it enters the placeholder |
| Programmatic or server-delivered template with a count or gender | `android.icu.text.MessageFormat("{count, plural, one {# file} other {# files}}", locale).format(mapOf("count" to n))` — `select` for gender, `selectordinal` for ordinals |
| `paddingLeft` / `Alignment.CenterLeft` / `Arrangement.Start` misuse | `paddingStart` / `Alignment.CenterStart`; `CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Ltr)` only around direction-fixed content (phone numbers, code) |
| Directional vector without mirroring | `android:autoMirrored="true"` on the `<vector>` root (ICON §B) — arrows, back/forward, undo/redo, list indent; not media, clock, or check glyphs |
| `remember { NumberFormat.getInstance() }` | `val config = LocalConfiguration.current; remember(config) { … }` |

Where the current locale is needed in a composable, read `LocalConfiguration.current.locales[0]`
(or `Locale.getDefault()` in non-UI code) rather than caching a locale at construction time.

## 8. Previews

L10N §F — on every screen-level (stateless content) composable, beside the existing preview:

```kotlin
@Preview(name = "en", showBackground = true)
@Preview(name = "de", locale = "de", showBackground = true)
@Preview(name = "ar (RTL)", locale = "ar", showBackground = true)
@PreviewFontScale            // androidx.compose.ui.tooling.preview.PreviewFontScale — singular
@Composable
private fun OrdersScreenPreview() = AppTheme { OrdersScreen(uiState = OrdersUiState.preview()) }
```

Use the app's second supported locale where it is not `de`. The `locale` parameter sets
`LocalConfiguration` only — the preview proves resource resolution and layout, not
`Locale.getDefault()` reads. Where a Roborazzi lane exists (`android-test-suite-apply`), add
the locale and font-scale variants through `DeviceConfigurationOverride` there as well.

## 9. Verification: pseudolocale and font-scale pass

Order: `./gradlew build` → the module lint task (`./gradlew :app:lintDebug`, or the variant
the project uses) → the pass below. Both Gradle steps must be green before the pass runs; a
red step routes to `android-debugging` (REQ-7).

Device or emulator commands (REQ-4; the emulator must be a debug build with
`isPseudoLocalesEnabled`):

```sh
# Install the debug variant
./gradlew :app:installDebug

# Per-app locale (API 33+): switch the app alone, leaving the device locale untouched
adb shell cmd locale set-app-locales <applicationId> --locales en-XA   # expansion + leaks
adb shell cmd locale set-app-locales <applicationId> --locales ar-XB   # RTL mirroring
adb shell cmd locale set-app-locales <applicationId> --locales de      # the real translation
adb shell cmd locale set-app-locales <applicationId> --locales ""      # back to system default

# Device-wide pseudolocale (any API): Settings > System > Languages, or on a rooted emulator
adb root && adb shell "setprop persist.sys.locale en-XA; stop; start"

# 200 % font scale (Android 14+ non-linear scaling), then reset
adb shell settings put system font_scale 2.0
adb shell settings put system font_scale 1.0

# Screenshot evidence for the report
adb exec-out screencap -p > .audits/android-localization/<date>-en-XA-<screen>.png
```

What to look for, per screen: under `en-XA` any text that is **not** accented is a leaked
hard-coded string or a concatenation; clipped or ellipsised primary controls at 200 % and
under expansion are §E findings; under `ar-XB` any left-anchored element, unmirrored arrow,
or number rendered in the wrong direction is a §D finding. `setApplicationLocales` from the
picker must survive `adb shell am force-stop <applicationId>` and a relaunch (persistence).
Where no device is available, state that the pass is pending and which previews (§8) stood in.
