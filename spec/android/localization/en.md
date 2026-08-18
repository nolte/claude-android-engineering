# Localization

Status: draft

## Context

Multilingualism is not a translation file bolted on at the end — it is a set of disciplines that must hold from the first string resource: externalized strings, locale-correct formatting, RTL-ready layouts, a per-app language surface, and a translation workflow that keeps languages in sync. This spec is the complete internationalization/localization concept for apps built with this repository's skills, sized for the portfolio's typical case (bilingual English/German) but correct for any language set.

The content is distilled from a research pass (August 2026) over the official Android localization documentation (string resources, multilingual resource resolution, per-app language preferences, RTL, pseudolocales, non-linear font scaling), the current Gradle/AGP surface (`generateLocaleConfig`, `androidResources.localeFilters` as the replacement for `resourceConfigurations`, deprecated since AGP 8.8), the grammatical-inflection and ICU message-formatting APIs, Google's per-app language sample, and translation-workflow practice for small teams (TMS options, the honest 2025/2026 state of LLM-assisted translation).

Boundaries: text-expansion-safe layout mechanics and font scaling are shared with `spec/android/app-design-navigation/` §A (this spec owns the locale-driven causes); icon mirroring rules live in `spec/android/iconography/` §B; per-locale testing execution belongs to `spec/android/test-automation/`.

Readers: authors of this repo's Android skills and reviewers judging whether a generated or audited app is fully localizable.

## Goals

- Every user-visible string externalized, translatable, and grammatically safe (positional placeholders, real plurals) from the first generated screen
- A complete language surface: system-visible supported locales, an in-app language picker, correct persistence down to Android 12
- Locale-correct behavior beyond strings: dates, numbers, sorting, casing, RTL — no concatenation, no hard-coded formats
- A sustainable translation workflow for a solo maintainer: one source of truth, lint-gated completeness, pseudolocale testing before every translation round

## Non-Goals

- Play-Store listing translation — release scope, handled in the Play Console, not in app resources
- Content/CMS localization (server-delivered text) — app-resource localization only
- Choosing the app's concrete language set — per-app decision; this spec fixes the mechanics for any set
- Layout mechanics of text expansion (owned by the design spec) beyond naming the locale-driven causes

## Requirements

### A. String resources

- **MUST** externalize every user-visible string to `strings.xml`; the `HardcodedText` lint check is error-level, and generated code never inlines UI text
- **MUST** use positional placeholders (`%1$s`, `%2$d`) in every parameterized string — translators must be able to reorder arguments, which sequential placeholders forbid
- **MUST** mark non-translatable entries `translatable="false"` (brand names, technical tokens) and keep them only in the default `values/`
- **MUST** use `<plurals>` with the full language-dependent quantity classes for grammatical counts (always including `other`, always carrying the number as a placeholder — the `ImpliedQuantity` lint error exists because "one" covers 101 in some languages); **MUST NOT** abuse plurals for UI states
- **MUST NOT** build sentences by concatenating translated fragments — word order is language-specific; one sentence is one string with placeholders
- **MUST NOT** put translatable content in `<string-array>` items matched by index — order/count drift across locales silently shifts meaning; arrays reference `@string` entries instead
- **SHOULD** name strings by feature/screen prefix (`settings_language_title`, `common_cancel`) and wrap untouchable segments in `<xliff:g id example>` markup; **SHOULD** put a translator-context comment (purpose, placement, length limit) above every non-obvious string

### B. Resource resolution and build configuration

- **MUST** keep the default `values/` complete in the source-of-truth language (English for this portfolio); a string missing from the default set crashes unsupported locales — `MissingTranslation`/`ExtraTranslation` lint stays error-level as the completeness gate
- **MUST** declare the supported locale set in the build: `androidResources { localeFilters += listOf("en", "de") }` — `resourceConfigurations` is deprecated since AGP 8.8 (AGP dropped density filtering and Play requires App Bundles), and `androidResources.localeFilters` is the replacement for the language part of it [R11]; it also strips library locales
- **SHOULD** use BCP-47 qualifiers (`values-b+…`) for new resource directories and rely on the Android-7+ resolution chain (exact → language → child dialects → next user locale → default) instead of duplicating resources per dialect
- **MAY** carry partial translations transiently (fallback covers gaps), but a release round closes them (gate per §E)

### C. Per-app language surface

- **MUST** make supported languages visible to the system: `generateLocaleConfig = true` with `resources.properties` (`unqualifiedResLocale=…`) — or a manual `locales_config.xml` wired via `android:localeConfig`
- **MUST** implement the in-app language picker through `AppCompatDelegate.setApplicationLocales()`/`getApplicationLocales()` (activities are `AppCompatActivity`, also in Compose apps), with the `autoStoreLocales` manifest service enabling persistence below Android 13
- **SHOULD** offer "system default" as a choice (`setApplicationLocales(emptyLocaleList)`), and reset stored locales when a language is dropped from the config so users don't strand
- **MUST** build the picker's argument with `LocaleListCompat.forLanguageTags("<bcp47>")` and reset with `LocaleListCompat.getEmptyLocaleList()`; the call runs on the main thread because it may recreate the activity, and the picker's option list is derived from the declared locale config (§C above) rather than a second hard-coded list [R4]
- **MAY** use the framework `LocaleManager` directly only when minSdk ≥ 33
- **SHOULD**, where a supported language inflects by the addressee's grammatical gender (German does), offer the choice through `GrammaticalInflectionManager.setRequestedApplicationGrammaticalGender()` on API 34+ and ship the inflected variants as `values-<locale>-feminine|masculine|neuter` resource sets, keeping the ungendered form as the default; the change is a configuration change unless `grammaticalGender` is declared in `configChanges` [R19]. Below API 34 the ungendered default renders unchanged

### D. Locale-correct behavior

- **MUST** format dates/times via `java.time` localized formatters (`DateTimeFormatter.ofLocalized…`, ICU skeletons via `getBestDateTimePattern` for custom shapes; `DateUtils` for relative times) and numbers/currency via `NumberFormat`/ICU — never hand-built patterns or string interpolation of numbers into RTL contexts
- **MUST** make locale-sensitive string operations explicit: `Locale.ROOT` for internal keys (the Turkish-i problem breaks even `equalsIgnoreCase`), user locale for display casing, `Collator` for user-visible sorting
- **MUST** support RTL end-to-end: `android:supportsRtl="true"`, start/end everywhere (never left/right), Compose's automatic `LayoutDirection` mirroring with deliberate `CompositionLocalProvider` overrides only for direction-fixed content (phone numbers, code); directional icons auto-mirror per `spec/android/iconography/` §B
- **SHOULD** wrap free-direction inline data (addresses, phone numbers inside translated sentences) with `BidiFormatter.unicodeWrap`
- **SHOULD** prefer `android.icu.*` classes (API 24+) over their `java.text` counterparts
- **MUST**, for text the app formats from server-delivered or programmatic templates instead of `strings.xml` (the one case §A's `<plurals>` cannot cover), use `android.icu.text.MessageFormat` (API 24+) with `plural`, `select`, and `selectordinal` arguments rather than string interpolation, so counts and gendered forms stay grammatical there too [R20]; the templates themselves remain content-localization scope per Non-Goals

### E. Testing and translation workflow

- **MUST** enable pseudolocales in debug builds (`isPseudoLocalesEnabled = true`) and run an `en-XA` (expansion, hardcoded-string, concatenation detection) and `ar-XB` (RTL) pass before every translation round
- **MUST** treat one language as the source of truth and derive all others; translations never diverge structurally (per-locale files carry the same keys, enforced by the lint gate)
- **MUST** verify layouts at 200 % font scale and with expanded pseudolocale text (German runs ~30–40 % longer; no fixed-width text containers) — execution via `spec/android/test-automation/` previews (`@Preview(locale = …)`, `@PreviewFontScale`) and per-locale screenshot tests where present
- **SHOULD** run a lightweight translation workflow: string freeze before a release round, LLM-assisted draft translation with human review for visible strings (the honest 2025/2026 state: LLM output rates "good" in 55–80 % of blind evaluations — a draft quality, not a ship quality), a TMS (Weblate/Crowdin) only when contributor translation begins
- **SHOULD** treat the app name as `translatable="false"` brand unless localized branding is a deliberate choice

### F. Compose specifics

- **MUST** read strings via `stringResource`/`pluralStringResource` in composables (recomposition-safe on locale change); **MUST NOT** concatenate strings in composables or cache locale-dependent values in `remember` without a locale/configuration key
- **SHOULD** include per-locale previews (`@Preview(locale = "de")`, `@Preview(locale = "ar")` for RTL) and the font-scale multipreview (`@PreviewFontScale` from `androidx.compose.ui.tooling.preview` — the annotation class is singular even where prose spells it plural; a plural spelling does not compile) in the standard preview set [R9]; note the preview `locale` parameter sets `LocalConfiguration` only — code reading `Locale.getDefault()` directly won't see it (and generally shouldn't exist in UI code)

## Acceptance Criteria

The criteria below are a deliberate representative rollup of §A–§F, not a 1:1 mapping; every requirement bullet above is normative on its own.

- [ ] `lint` passes with `HardcodedText`, `MissingTranslation`, `ExtraTranslation`, and `ImpliedQuantity` at error severity; no user-visible string is inlined in code
- [ ] Every parameterized string uses positional placeholders; no runtime string concatenation builds a sentence
- [ ] Counts render through `<plurals>` with an `other` case and the number in the text
- [ ] The build declares `localeFilters` matching the supported set, and the system language picker lists the app with exactly those languages
- [ ] The in-app language picker changes the language at runtime, persists across restarts on Android 12 and 13+, offers "system default", and derives its options from the declared locale config
- [ ] Dates, numbers, and currencies render locale-correctly in every supported language; internal keys use `Locale.ROOT` operations
- [ ] The app renders correctly under `ar-XB` (fully mirrored, no left/right leakage) and under `en-XA` at 200 % font scale without clipped critical UI
- [ ] `values/` (source language) is complete; every other locale file carries the same key set
- [ ] Composables read all text through `stringResource`-family APIs; per-locale previews exist for every screen-level composable
- [ ] The generated project ships bilingual (en source, de translation) with all of the above green on first build
- [ ] String keys follow the `<screen>_<what>` prefix convention, or the deviation from §A's SHOULD is recorded

## Open Questions

All questions are parking-lot class: the requirements above state a working default for each.

- Translation memory: introduce a TMS from the start for the solo bilingual case, or stay git-only until external translators appear (current default: git-only)?
- LLM translation automation: wire a draft-translation step into a future skill (with mandatory human review), or keep translation fully manual?
- String naming: enforce the `<screen>_<what>` convention via a custom lint check, or leave it to review?
- Regional variants (de-AT/de-CH, en-GB): explicitly out until a real need appears — confirm when the first app ships?

## References

All sources retrieved 2026-08-11; R19–R20 and the AGP wording re-verified 2026-08-19. Class markers: (P) primary/authoritative vendor documentation, (S) secondary. Platform facts cite the authoritative primary source per the portfolio triangulation convention; workflow findings are attributed inline where single-study.

- [R1] Localization overview (P): <https://developer.android.com/guide/topics/resources/localization>
- [R2] String resources (placeholders, plurals, arrays, styling) (P): <https://developer.android.com/guide/topics/resources/string-resource>
- [R3] Multilingual resource resolution (fallback chain, BCP-47) (P): <https://developer.android.com/guide/topics/resources/multilingual-support>
- [R4] Per-app language preferences (localeConfig, AppCompatDelegate, autoStoreLocales) (P): <https://developer.android.com/guide/topics/resources/app-languages>
- [R5] Language support basics (RTL, formatting, BidiFormatter) (P): <https://developer.android.com/training/basics/supporting-devices/languages>
- [R6] Pseudolocales (en-XA/ar-XB) (P): <https://developer.android.com/guide/topics/resources/pseudolocales>
- [R7] Non-linear font scaling to 200 % (Android 14) (P): <https://developer.android.com/about/versions/14/features>
- [R8] Compose resources (stringResource, recomposition) (P): <https://developer.android.com/develop/ui/compose/resources>
- [R9] Compose previews (locale/fontScale parameters) (P): <https://developer.android.com/develop/ui/compose/tooling/previews>
- [R10] Internationalization (ICU, MessageFormat, casing/collation) (P): <https://developer.android.com/guide/topics/resources/internationalization>
- [R11] AGP API updates (`localeFilters` replacing `resourceConfigurations`) (P): <https://developer.android.com/build/releases/gradle-plugin-api-updates>
- [R12] Lint checks — ImpliedQuantity et al. (P): <https://googlesamples.github.io/android-custom-lint-rules/checks/ImpliedQuantity.md.html>
- [R13] Per-app languages sample (locales_config, picker) (P): <https://github.com/android/user-interface-samples/tree/main/PerAppLanguages>
- [R14] M3 bidirectionality (icon mirroring rules) (P): <https://m3.material.io/foundations/layout/bidirectionality-rtl>
- [R15] Text-size/expansion research (W3C) (S): <https://www.w3.org/International/articles/article-text-size.en.html>
- [R16] LLM translation quality evaluation 2025 (single-study, attributed) (S): <https://lokalise.com/blog/what-is-the-best-llm-for-translation/>
- [R17] TMS landscape for small teams (S): <https://www.saashub.com/compare-crowdin-vs-weblate>
- [R18] Turkish-i casing problem (S): <https://garygregory.wordpress.com/2015/11/03/java-lowercase-conversion-turkey/>
- [R19] Grammatical Inflection API (Android 14, `GrammaticalInflectionManager`, gender resource qualifiers) (P): <https://developer.android.com/about/versions/14/features/grammatical-inflection>
- [R20] `android.icu.text.MessageFormat` reference (plural/select/selectordinal arguments, API 24+) (P): <https://developer.android.com/reference/android/icu/text/MessageFormat>
