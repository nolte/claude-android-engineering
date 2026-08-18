# Localization audit rules

The rules of `spec/android/localization/` §A–§F, distilled into findings the `audit` operation
can detect and the `apply` operation can fix. Every row names its spec section; the spec, not
this table, is normative. Severity follows the canonical scale of `spec/claude/review-plan/`:
`Critical` for a breached MUST or MUST NOT, `Warning` for a breached SHOULD, `Suggestion` for
a MAY worth adopting or a SHOULD deliberately deferred, `Info` for a surface scanned clean.

The heuristics are grep-grade starting points over `src/main/res/**`, `src/main/**/*.kt`,
`src/main/AndroidManifest.xml`, the module build scripts, and `lint.xml`; every hit is read in
context before it becomes a finding. Lint output (`./gradlew :app:lintDebug`, report under
`build/reports/lint-results-debug.xml`) is the primary evidence for §A/§B; the greps catch what
lint's configured severity hides.

## Table of contents

- [1. String resources (§A)](#1-string-resources-a)
- [2. Completeness and build configuration (§B)](#2-completeness-and-build-configuration-b)
- [3. Per-app language surface (§C)](#3-per-app-language-surface-c)
- [4. Locale-correct behaviour and RTL (§D)](#4-locale-correct-behaviour-and-rtl-d)
- [5. Pseudolocales and translation workflow (§E)](#5-pseudolocales-and-translation-workflow-e)
- [6. Compose specifics (§F)](#6-compose-specifics-f)
- [7. Gotchas](#7-gotchas)

## 1. String resources (§A)

| Rule | Detection heuristic | Severity | Fix (apply step) |
|---|---|---|---|
| Every user-visible string is externalised; `HardcodedText` is error-level (MUST) | Lint `HardcodedText` hits; `Text("` / `Text(text = "` / `contentDescription = "` / `label = { Text("` / `placeholder = "` with a literal in `*.kt`; `android:text="` with a literal in layout XML; `lint.xml` sets `HardcodedText` below `error` or omits it while the project's lint defaults are relaxed | Critical per inlined string; Critical for the severity | step 3 (severity), step 4 (externalise) |
| Positional placeholders in every parameterised string (MUST) | `%s`, `%d`, `%f` without `N$` in any `strings.xml`; two or more placeholders in one entry without positions | Critical | step 4 |
| `translatable="false"` only in the default `values/` (MUST) | `translatable="false"` inside `values-*/strings.xml`; brand names / URLs / technical tokens in `values/` without the attribute (lint `MissingTranslation` on them is the symptom) | Critical (wrong file); Warning (missing attribute) | step 4 |
| Counts through `<plurals>` with `other` and the number in the text; no plurals for UI states (MUST / MUST NOT) | `<plurals>` without `quantity="other"`; a quantity item whose text has no placeholder (lint `ImpliedQuantity`); `<plurals>` whose items differ by state words rather than count; `if (count == 1)` around two strings in Kotlin | Critical | step 4 |
| No sentence built by concatenation (MUST NOT) | `stringResource(…) + `, `getString(…) + "`, `"$"`-templates that splice two resources, `buildString` over resources, `String.format` with a resource and a literal separator | Critical | step 4 |
| No translatable user text in index-matched `<string-array>` (MUST NOT) | `<string-array>` in `values/` without `translatable="false"` whose items are prose; `resources.getStringArray(` feeding UI | Critical | step 4 |
| Feature-prefixed names, `<xliff:g>` on untouchable segments, translator comments (SHOULD) | `name="` values with no `_` prefix or with generic names (`text1`, `label`); URLs / placeholders inside translatable text without `<xliff:g>`; parameterised strings without a preceding `<!-- -->` comment | Warning (naming, xliff); Suggestion (comments) | step 4 |

## 2. Completeness and build configuration (§B)

| Rule | Detection heuristic | Severity | Fix (apply step) |
|---|---|---|---|
| Default `values/` complete in the source language; `MissingTranslation` / `ExtraTranslation` at error (MUST) | Lint hits of either id; a key present in a `values-*` file but not in `values/`; `lint.xml` sets either below `error`; a `lint-baseline.xml` suppressing them | Critical | step 3 (severity), step 5 (key sets) |
| Supported set declared via `androidResources.localeFilters` (MUST); `resourceConfigurations` is deprecated since AGP 8.8 | Neither `localeFilters` nor `resourceConfigurations` in the app module build script; `resourceConfigurations` / `resConfigs` present; the filter set differs from the `values-*` directories that exist | Critical (absent or deprecated form); Warning (mismatch) | step 3 |
| BCP-47 qualifiers for new directories (SHOULD) | `values-<lang>` / `values-<lang>-r<REGION>` directories instead of `values-b+<lang>` (`values-b+<lang>+<REGION>`); duplicated resources across dialect directories the resolution chain would cover | Suggestion — record legacy directories, do not rename them without a per-directory confirmation | step 5 |
| Partial translations only transiently (MAY) | A `values-*` file with fewer keys than `values/` while lint is silent (severity relaxed) | Warning | step 5 |

## 3. Per-app language surface (§C)

| Rule | Detection heuristic | Severity | Fix (apply step) |
|---|---|---|---|
| Supported languages visible to the system (MUST) | Neither `generateLocaleConfig = true` (with `res/resources.properties` carrying `unqualifiedResLocale=`) nor `android:localeConfig="@xml/…"` on `<application>`; both present at once; a manual `locales_config.xml` whose `<locale>` set differs from `localeFilters` | Critical (absent); Warning (drift, both forms) | step 3 |
| Picker through `AppCompatDelegate.setApplicationLocales` / `getApplicationLocales`; activities are `AppCompatActivity`; `autoStoreLocales` service for persistence below 13 (MUST) | No `setApplicationLocales` call anywhere while a locale set is declared (no picker); the host activity extends `ComponentActivity` instead of `AppCompatActivity`; the `androidx.appcompat.app.AppLocalesMetadataHolderService` entry with `autoStoreLocales` meta-data missing from the manifest while `minSdk < 33`; a custom `Configuration`/`Locale.setDefault` hack | Critical | step 3 (manifest), step 5 (picker) |
| "System default" offered; stored locales reset when a language is dropped (SHOULD) | No `getEmptyLocaleList()` branch in the picker; a language removed from `localeFilters` without a reset path | Warning | step 5 |
| Argument via `LocaleListCompat.forLanguageTags`; main-thread call; options derived from the declared locale config (MUST) | `LocaleListCompat.create(Locale(` / `Locale.forLanguageTag` fed manually; the call inside `Dispatchers.IO` / `withContext(IO)`; a hard-coded `listOf("en", "de")` in the picker beside the build declaration | Critical | step 5 |
| Framework `LocaleManager` only with `minSdk >= 33` (MAY) | `getSystemService(LocaleManager::class.java)` while `minSdk < 33` | Critical | step 5 |
| Grammatical inflection surface where a supported language inflects (SHOULD, API 34+) | German (or another inflecting language) supported, addressee-facing strings present, no `GrammaticalInflectionManager` usage and no `values-*-feminine|masculine|neuter` sets | Suggestion — record as deferred unless the app addresses the user in inflected forms | step 6 (optional) |

## 4. Locale-correct behaviour and RTL (§D)

| Rule | Detection heuristic | Severity | Fix (apply step) |
|---|---|---|---|
| Dates and numbers via localized formatters (MUST) | `SimpleDateFormat("` with a literal pattern; `DateTimeFormatter.ofPattern("` for display; `"$amount €"`, `"%.2f"`, `toString()` of a number into a `Text`; `String.format(` without a `Locale` on display text | Critical | step 6 |
| Explicit locale operations: `Locale.ROOT` for keys, user locale for display, `Collator` for sorting (MUST) | `.lowercase()` / `.uppercase()` / `equalsIgnoreCase` on identifiers, enum names, or map keys without `Locale.ROOT`; `sortedBy { it.name }` / `compareTo` on user-visible strings without `Collator` | Critical | step 6 |
| RTL end-to-end: `supportsRtl`, start/end, deliberate direction overrides only (MUST) | `android:supportsRtl` missing or `false`; `paddingLeft` / `marginRight` / `Alignment.CenterLeft` / `Arrangement.Start` misuse in code and XML (lint `RtlHardcoded`); `CompositionLocalProvider(LocalLayoutDirection provides Ltr)` around content that is not direction-fixed | Critical | step 3 (manifest), step 6 |
| Directional vectors mirror (`spec/android/iconography/` §B) | Arrow / back / undo vectors under `res/drawable*/` without `android:autoMirrored="true"`; media and clock glyphs that carry it | Critical (missing on directional); Warning (present on non-directional) | step 6 |
| `BidiFormatter.unicodeWrap` on free-direction inline data (SHOULD) | Phone numbers, addresses, or usernames interpolated into translated sentences without wrapping | Warning | step 6 |
| Prefer `android.icu.*` over `java.text` (SHOULD, API 24+) | `java.text.NumberFormat` / `java.text.DateFormat` imports where `minSdk >= 24` | Suggestion | step 6 |
| ICU `MessageFormat` for server-delivered or programmatic templates (MUST, API 24+) | `String.format` / template interpolation on text that arrives from the network or a non-resource template; a hand-rolled plural switch on it | Critical | step 6 |

## 5. Pseudolocales and translation workflow (§E)

| Rule | Detection heuristic | Severity | Fix (apply step) |
|---|---|---|---|
| Pseudolocales enabled in debug (MUST) | `isPseudoLocalesEnabled = true` missing from `buildTypes.debug` | Critical | step 3 |
| One source-of-truth language; per-locale files carry the same key set (MUST) | Key-set diff between `values/strings.xml` and each `values-*/strings.xml` (compare `name="…"` sets); a translated file with a key `values/` lacks | Critical | step 5 |
| Layouts verified at 200 % font scale and under expanded text (MUST) | No `@PreviewFontScale` on screen-level composables; no forced-font-scale screenshot test where a screenshot lane exists; fixed-width text containers (`Modifier.width(` around a `Text`) | Critical (no verification path); Warning (fixed widths) | step 6 (previews), step 7 (pass) |
| Lightweight translation workflow (SHOULD) | Untranslated drafts shipped without a review note; no string-freeze note in the release checklist | Suggestion | report only |
| App name `translatable="false"` unless localized branding is deliberate (SHOULD) | `app_name` translated in a `values-*` file without a recorded decision | Warning | step 4 |

## 6. Compose specifics (§F)

| Rule | Detection heuristic | Severity | Fix (apply step) |
|---|---|---|---|
| Strings read via `stringResource` / `pluralStringResource` (MUST) | `context.getString(` / `resources.getString(` inside a `@Composable`; `LocalContext.current.resources.getQuantityString(` | Critical | step 4 |
| No concatenation in composables; no locale-dependent `remember` without a configuration key (MUST NOT) | `stringResource(a) + stringResource(b)`; `remember { NumberFormat.getInstance() }` / `remember { DateTimeFormatter… }` without `LocalConfiguration.current` as a key | Critical | step 6 |
| Per-locale previews and `@PreviewFontScale` on screen-level composables (SHOULD; the AC requires them for every screen-level composable) | `*Screen.kt` / `*Content.kt` with a `@Preview` but no `@Preview(locale = "de")` (or the app's second locale), no RTL locale preview, or no `@PreviewFontScale`; a plural `@PreviewFontScales` spelling (compile error) | Warning | step 6 |
| Preview code reads through resources, not `Locale.getDefault()` | `Locale.getDefault()` in a `ui/` package | Warning | step 6 |

## 7. Gotchas

- **The preview `locale` parameter sets `LocalConfiguration` only.** `Locale.getDefault()`
  in UI code renders the host locale in a `de` preview and passes for the wrong reason.
- **`ImpliedQuantity` fires on a plural whose text omits the number.** "one" covers 101 in
  some languages; every quantity item carries `%1$d`.
- **`@PreviewFontScale` is singular** (`androidx.compose.ui.tooling.preview.PreviewFontScale`);
  a plural spelling does not compile.
- **`resourceConfigurations` and `localeFilters` side by side** is a build-script smell, not
  a migration; the deprecated form still filters and masks a wrong `localeFilters` set.
- **`generateLocaleConfig` and a manual `android:localeConfig`** both present make the manual
  file win in the manifest and the generated one dead; keep exactly one.
- **`setApplicationLocales` below Android 13 without the `autoStoreLocales` service** works
  until the process dies — the choice is not persisted and the audit sees a working picker
  that forgets. `minSdk >= 33` makes the service unnecessary, not harmful.
- **`values-de` and `values-b+de` are the same qualifier** to the resource system; two
  directories for one language split the key set and produce phantom `MissingTranslation`
  hits. Never create the BCP-47 form beside a legacy one — migrate the directory or leave it.
- **`localeFilters` strips library locales too**: a library string the app shows in a locale
  outside the filter falls back to the library's default; the filter set is the app's real
  language set, not a size optimisation.
- **Turkish-i:** `"ID".lowercase()` under `tr` yields a dotless ı; every key comparison goes
  through `Locale.ROOT`.
- **`ar-XB` mirrors, but only for `supportsRtl="true"`.** A pass that shows no mirroring at
  all is a manifest finding, not a layout finding.
- **A drafted translation seeded from English passes lint** and ships English text under a
  German locale; the report, not lint, is the gate for human review.
