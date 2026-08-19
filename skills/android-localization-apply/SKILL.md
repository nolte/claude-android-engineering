---
name: android-localization-apply
description: "Brings an existing Android app's localization in line with spec/android/localization/: audits strings (HardcodedText, MissingTranslation, ImpliedQuantity, translatable=false, string-array misuse, plurals, ICU MessageFormat), locale-correct code (Locale.ROOT, Collator, BidiFormatter), RTL, build wiring (localeFilters, generateLocaleConfig, pseudolocales), the in-app language picker, and per-locale plus @PreviewFontScale previews; then applies the missing pieces with per-item approval (externalised strings, locale config, AppCompatDelegate picker, debug pseudolocales, localeFilters migration, values-b+<lang> directories), closing on green ./gradlew build and lint. Operations: audit (read-only), apply. Invoke to localize or add a language switcher to an existing app. Don't use for a new project, a new screen's strings, or a read-only UI review. Also handles equivalent German-language requests. Supports resume on re-invocation."
tags: [ui, audit, implementation]
phase: build
summary: "Audits and applies an existing Android app's localization per spec/android/localization/: strings, plurals, locale config, in-app language picker, RTL, pseudolocales, per-locale previews."
summary_de: "Prüft und vervollständigt die Lokalisierung einer bestehenden Android-App gemäß spec/android/localization/: Strings, Plurals, Locale-Konfiguration, Sprachumschalter, RTL, Pseudolocales, Previews."
use_when:
  - "an existing app's strings, plurals, or locale wiring should be audited against the localization spec"
  - "hard-coded UI text should be externalised to strings.xml across an existing app"
  - "an in-app language picker with persistence down to Android 12 should be added"
  - "a new language should be added, or values-<lang> directories are out of sync"
  - "resourceConfigurations should migrate to localeFilters, or generateLocaleConfig is missing"
  - "the app should be verified under en-XA/ar-XB pseudolocales and 200 % font scale"
dont_use_when:
  - situation: "A new Android project should be created with its bilingual baseline"
    alternative: android-project-scaffold
  - situation: "A new screen or component and its strings should be authored"
    alternative: android-compose-ui
  - situation: "Existing UI should be reviewed read-only, localizability being one dimension"
    alternative: android-ux-reviewer
  - situation: "A build or lint failure needs diagnosing rather than a localization decision"
    alternative: android-debugging
  - situation: "A feature needs implementing across layers, its strings being one part"
    alternative: android-feature-implement
see_also:
  - android-project-scaffold
  - android-compose-ui
  - android-ux-reviewer
  - android-debugging
  - android-feature-implement
examples:
  - prompt: "Lokalisiere meine App und baue einen Sprachumschalter ein."
    outcome: "audit then apply: severity report, then externalised strings, locale config, AppCompatDelegate picker, pseudolocales, previews — green ./gradlew build and lint."
  - prompt: "Audit the app's localization; nothing should change yet."
    outcome: "audit: severity-classified report per localization section, nothing written."
resumable: true
---

# Android Localization Apply

Brings the localization of an **existing** Android app in line with `spec/android/localization/`:
audit first, then apply the missing pieces one approved item at a time, closing on a green
`./gradlew build` and lint (REQ-1, REQ-7).

The governing idea is that multilingualism is a **set of disciplines that hold from the first
string**, not a translation file added at the end: externalised, grammatically safe strings;
one source-of-truth language with lint-gated completeness; a complete per-app language
surface; locale-correct formatting and RTL; a pseudolocale pass before every translation
round. The authoritative rules live in `spec/android/localization/`; this skill
operationalizes them, never restates them. On any conflict the spec wins — report the gap and
propose a spec change rather than deciding silently (REQ-6).

Grounding specs, in the order they bind this skill: `spec/android/localization/` §A (string
resources), §B (resolution and build configuration), §C (per-app language surface), §D
(locale-correct behaviour and RTL), §E (testing and translation workflow), §F (Compose
specifics); `spec/android/iconography/` §B (mirrored vectors); `spec/android/app-design-navigation/`
§A (text-expansion and font-scale layout mechanics); `spec/android/test-automation/` §D/§E
(per-locale previews and screenshot lanes); `spec/android/project-structure/` §G (lint
configuration placement); `spec/android/release-readiness/` (what "done" means for the touched
build).

## Why this is a skill, not an agent

- **Per-item approval is the contract.** Externalising a string, adding a language, rewriting
  a picker, and migrating a build script are operator decisions that outlive the run (REQ-8);
  an agent's fire-and-forget shape cannot carry them.
- **The persistent artifacts are the deliverable.** `strings.xml` files, the locale config,
  the picker, and build-script changes land in the working tree, reviewed in context.
- **It composes with sibling capabilities.** New screens → `android-compose-ui`, red build →
  `android-debugging`, greenfield → `android-project-scaffold`; per `spec/claude/skill-vs-agent/`
  §Primary decision rule the orchestrator is always a skill.
- Counter-dimension considered: `audit` alone — scanning every resource file and Kotlin
  source — would suit an agent's context isolation, and `android-ux-reviewer` already covers
  localizability read-only. It stays here because its findings are phrased as the `apply`
  items the operator approves next, so one finding vocabulary serves both.

## Boundary vs the sibling capabilities

- `android-project-scaffold` (REQ-12) lays the bilingual baseline into a **new** project
  (`values-b+de/`, `generateLocaleConfig` with `resources.properties`, `@PreviewFontScale`,
  the picker). This skill never scaffolds; it starts where a project already exists.
- `android-compose-ui` (REQ-13) externalises strings **at authoring time** for the screen it
  builds and ships the per-locale previews of that screen. This skill retrofits the same
  discipline onto screens that already exist and hands any *new* screen there.
- `android-ux-reviewer` (REQ-14) audits UI read-only, localizability included; its report is a
  valid input to `apply`. This skill's `audit` is broader — resources, build wiring, Kotlin
  call sites — and is written to feed `apply`.
- `android-feature-implement` (REQ-19) owns feature work across layers and externalises the
  strings it introduces; it may call this skill when a feature exposes a localization gap.
- `android-debugging` (REQ-16) diagnoses a red build or lint run; this skill routes red states
  there and never guesses at a failure.
- Server-delivered text stays content-localization scope (spec Non-Goals); this skill only
  ensures the app formats it through ICU `MessageFormat` (§D).

## German trigger phrases

Respond to these (and equivalents) exactly as to their English counterparts; the frontmatter
`description` stays English-only per `skill-management` §Structure.

- "App lokalisieren", "Mach die App mehrsprachig", "Lokalisierung prüfen / auditieren"
- "Strings externalisieren", "Hart codierte Texte in strings.xml auslagern"
- "Sprachumschalter einbauen", "Sprache in der App wechseln", "Sprache pro App merken"
- "Neue Sprache hinzufügen", "Übersetzungen abgleichen", "Pseudolocale-Test", "RTL prüfen"

## User-language policy

Detect the operator's language and respond in it (German for this operator). Generated
artifacts stay canonical: Kotlin, Gradle, XML, and identifiers in English; the audit report is
written in English so it stays reviewable alongside the spec corpus. The default `values/`
holds the English source of truth (§B); translated files carry the target language only.

## Operations

Pick one at the start and say which is running. The split is deliberate: `audit` **only
reports**, `apply` **writes**. Nothing is written into the project before the operator has
approved the item.

- **`audit`** — the app exists and its localization conformance is unknown. Runs the audit
  procedure below and **writes nothing at all**: it produces a findings report on the
  canonical `Critical` / `Warning` / `Suggestion` / `Info` scale of `spec/claude/review-plan/`.
  When the operator wants the report on disk, it goes to
  `.audits/android-localization/<YYYY-MM-DD>.md`, nowhere else — the location is fixed by
  `spec/android/localization/` §Acceptance Criteria.
- **`apply`** — findings exist (from this run, a previous `audit`, or an `android-ux-reviewer`
  report) and the missing pieces are to be written. Runs steps 1–7. Without a finding list it
  runs `audit` first and says so.

An end-to-end request ("localize the app") is `audit` then `apply` back-to-back; announce the
handover so the operator sees the report before anything is written.

## Preconditions

Before deciding anything:

- Confirm the working directory is a git repository holding an Android project with a Gradle
  application module. Without one, stop and route to `android-project-scaffold`.
- Read `references/localization-audit-rules.md` in full — it is the rule set of §A–§F
  distilled into detectable findings with severities, and every audit finding cites it.
- Establish the AGP version (decides `localeFilters` versus `resourceConfigurations` and
  `generateLocaleConfig` availability), `minSdk` (decides `LocaleManager` versus
  `AppCompatDelegate`, and whether the `autoStoreLocales` service is needed), the module graph
  (which modules own resources), the existing locale set (`values-*` directories), and whether
  a `lint.xml` exists.
- Check for uncommitted changes in `res/`, build scripts, the manifest, and `lint.xml`. If
  dirty, report and ask whether to stash, commit, or abort — never overwrite unconfirmed work
  (REQ-8).

## Audit procedure (operation `audit`)

Read-only throughout. Nothing is written — no string, build script, or manifest.

1. **Enumerate the surface.** Every `res/values*/` directory per module with its qualifier
   form (BCP-47 `values-b+…` versus legacy `values-de`), its strings, plurals, and arrays; the
   `lint.xml` severities; the `androidResources` and `buildTypes.debug` blocks; the manifest
   (`supportsRtl`, `localeConfig`, `autoStoreLocales`); every `setApplicationLocales`/
   `LocaleManager` call site; the screen-level composables with their preview annotations.
2. **Run lint once, read-only.** `./gradlew :app:lintDebug` (or the project's debug variant)
   and read the report for `HardcodedText`, `MissingTranslation`, `ExtraTranslation`,
   `ImpliedQuantity`, `RtlHardcoded`, `MissingQuantity`, `StringFormatInvalid`; note their
   configured severities — a MUST-level check below error severity is itself a finding (§A/§B).
3. **Walk the rules.** Apply every heuristic in `references/localization-audit-rules.md`
   §1–§6: string hygiene (§A), completeness and build wiring (§B), the language surface (§C),
   locale-correct code and RTL (§D), pseudolocales and workflow (§E), Compose reads and
   previews (§F).
4. **Report** on the canonical scale: `Critical` for a breached MUST or MUST NOT, `Warning`
   for a breached SHOULD, `Suggestion` for a MAY worth adopting or a SHOULD deliberately
   deferred, `Info` for a surface scanned clean. Each finding carries the file and line, the
   spec section, and the `apply` item that would fix it. A choice no spec settles is reported
   as a gap with a proposed extension (REQ-6).

## Procedure (operation `apply`)

Run the steps in order. Confirm with the operator at each gate before writing.

### 1. State the target in one sentence

Restate what the operator wants — "the app ships English and German, switchable in-app, and
passes the pseudolocale pass" is answerable; "better i18n" is not. Fix the supported locale
set with the operator: the spec fixes the mechanics, never the set (Non-Goals). Gate: confirm
the restatement and the locale set.

### 2. Build the apply plan

Derive the item list from the findings, in this order (each item assumes the earlier ones):
lint severities (§A/§B); `resourceConfigurations` → `androidResources.localeFilters`
migration and `generateLocaleConfig` with `resources.properties` (or repair of a manual
`locales_config.xml`) (§B/§C); `supportsRtl` and the `autoStoreLocales` service in the
manifest (§C/§D); externalisation of hard-coded strings and repair of placeholders, plurals,
`translatable="false"` misuse, and index-matched `<string-array>` user text (§A); missing
`values-b+<lang>/` directories and key-set drift (§B/§E); the in-app language picker (§C);
locale-correct code fixes — `Locale.ROOT`, `Collator`, `BidiFormatter`, `java.time`/ICU
formatters, ICU `MessageFormat` for programmatic templates (§D); `isPseudoLocalesEnabled` on
debug (§E); per-locale previews and `@PreviewFontScale` (§F); optionally the grammatical
inflection surface (§C SHOULD). Present the list with the files each item touches. Gate:
confirm the list; the operator may drop items.

### 3. Fix build wiring, lint, and manifest

From `references/apply-templates.md` §1–§3: `lint.xml` severities (merged into an existing
file, never replacing it), the `androidResources { localeFilters += …; generateLocaleConfig
= true }` block plus `res/resources.properties`, `isPseudoLocalesEnabled = true` on the debug
build type, `android:supportsRtl="true"`, and the `autoStoreLocales` metadata service. When
`resourceConfigurations` is present, replace it in the same hunk — never leave both (REQ-9).
On AGP below the `localeFilters` cut-over, report the version gap and route to
`android-toolchain-upgrade` rather than writing the deprecated form. Confirm before every
write to an existing file (REQ-8). Checkpoint after each item.

### 4. Externalise and repair strings

Per finding, from `references/apply-templates.md` §4: move the literal into `values/strings.xml`
under a feature-prefixed name and read it via `stringResource`/`pluralStringResource` (or
`getString` outside composables); make placeholders positional; merge concatenated sentences
into one string with placeholders; convert count text to `<plurals>` with `other` and the
number as a placeholder; move `translatable="false"` entries out of translated files; replace
index-matched user-text arrays with `@string` references. Existing keys are never renamed
wholesale — a rename touches every locale file and is confirmed per key. Checkpoint after
each file.

### 5. Add languages and the picker

From `references/apply-templates.md` §5–§6: create each missing `values-b+<lang>/strings.xml`
with the **same key set** as `values/`, seeded from the English source and clearly marked as
draft — a draft translation is transient per §B/§E, and the report names every visible string
that still needs human review. A drafted translation is draft quality only (§E), and says so. Then add the picker: an `AppCompatActivity` host,
`AppCompatDelegate.setApplicationLocales(LocaleListCompat.forLanguageTags(tag))` on the main
thread, "system default" via `getEmptyLocaleList()`, options derived from the declared locale
config, and — only when `minSdk >= 33` — the framework `LocaleManager` (§C). A dropped
language resets stored locales that point at it. Confirm before writing the picker into an
existing settings screen; a wholly new screen is routed to `android-compose-ui` with what it
must express. Checkpoint after each item.

### 6. Fix locale-correct code and previews

From `references/apply-templates.md` §7–§8: `Locale.ROOT` on internal keys, `Collator` on
user-visible sorting, `BidiFormatter.unicodeWrap` on free-direction inline data,
`java.time`/ICU formatters in place of hand-built patterns, ICU `MessageFormat` for programmatic
templates, `remember` keyed on the configuration where it caches locale-dependent values,
start/end in place of left/right, `android:autoMirrored="true"` on directional vectors (§D,
iconography §B). Add `@Preview(locale = "de")`, an RTL `@Preview(locale = "ar")`, and
`@PreviewFontScale` (singular) to every screen-level composable that lacks them (§F). Each
existing Kotlin file is patched only for the finding named in the plan, never rewritten.
Checkpoint after each file.

### 7. Verify, run the pseudolocale pass, and hand off

- Run `./gradlew build` once (it already runs lint via `check`). It must be green; report
  every failure with its output and route a red build to `android-debugging` (REQ-7).
- Run the pseudolocale pass of `references/apply-templates.md` §9 where a device or emulator
  is available (REQ-4): the debug build under `en-XA` (expansion, leaked hard-coded strings,
  concatenation) and `ar-XB` (mirroring, left/right leakage), and 200 % font scale; where none
  is available, state that the pass is pending and which previews stood in for it.
- Re-run the audit heuristics over the touched surface and confirm no `Critical` remains.
- Report, in the operator's language: the locale set, every item applied or dropped, every
  key added, the drafts needing human review, the verification and pseudolocale-pass results,
  and any spec gap. Never leave a red, skipped, or unrunnable element unreported (REQ-1, REQ-7).

## Reference files

- Read `references/localization-audit-rules.md` before the audit and before step 2 — the
  detectable findings of §A–§F with heuristic, severity, and fix, plus the gotchas.
- Read `references/apply-templates.md` in steps 3–7 — lint, build-script, manifest, and
  string templates; the picker; locale-correct code; previews; the pseudolocale pass.

## Resumability

Per `spec/claude/resumable-work/`, this skill is `resumable: true`. State is persisted to
`.resume/android-localization-apply/<run-id>.yml` after every gate and at each named step
boundary. On re-invocation, scan `.resume/android-localization-apply/*.yml` for files with
`status: in_progress` whose `inputs:` snapshot (repository + operation + locale set) matches
the current request; when one matches, prompt
`Resume run <run_id> from phase <phase> (last checkpoint <last_checkpoint_at>)? [resume / start-new / discard]`.
`resume` re-hydrates and re-asks no answered gate; `start-new` leaves the old file intact;
`discard` deletes it. Fail closed on unparseable or higher-`schema_version` files. The envelope
keys and lifecycle are load-bearing in the spec and are not duplicated here.

## Hard rules

- **Never** write a string, build script, manifest, or Kotlin change in `audit`, and never
  write an `apply` item the operator has not approved in the plan (REQ-8).
- **Never** inline a user-visible string in code, build a sentence from translated fragments,
  use sequential placeholders, or put translatable user text in an index-matched
  `<string-array>` (§A).
- **Never** put a `translatable="false"` entry into a translated file, and never leave a key
  in a translated file that the default `values/` lacks (§A/§B).
- **Never** write `resourceConfigurations` into a build script, and never leave it beside
  `localeFilters` (§B, REQ-9); never write a second hard-coded language list for the picker
  when the declared locale config can be read (§C).
- **Never** call `setApplicationLocales` off the main thread, and never build its argument
  from anything but `LocaleListCompat.forLanguageTags` / `getEmptyLocaleList` (§C).
- **Never** hand-build a date or number pattern, lower-case an internal key with the user
  locale, or sort user-visible text without a `Collator` (§D).
- **Never** rename existing keys wholesale, rewrite a `strings.xml` file, or replace an
  existing `lint.xml` without per-file confirmation (REQ-8).
- **Never** present a drafted translation as ship quality; every visible drafted string is
  named for human review (§E).
- **Never** scaffold a new project or author a new screen; route to `android-project-scaffold`
  and `android-compose-ui`.
- **Always** report a localization choice no spec settles — regional variants, TMS adoption,
  a lint check for naming, the picker's option-derivation mechanism below API 33 — as a gap
  with a proposed extension instead of deciding silently (REQ-6).
- **Always** close `apply` on green `./gradlew build` and lint, and route a red build to
  `android-debugging` (REQ-7).
- When `spec/android/localization/` disagrees with this skill, the spec wins.

## Gotchas

Read `references/localization-audit-rules.md` §7 for the full set. The three that most often
produce a wrong result:

- **The preview `locale` parameter sets `LocalConfiguration` only.** Code that reads
  `Locale.getDefault()` in UI renders the host locale in a `de` preview and passes for the
  wrong reason; read through `stringResource` and the composition-local configuration.
- **`ImpliedQuantity` fires on a plural whose text omits the number.** "one" covers 101 in
  some languages, so `<item quantity="one">One item</item>` is a lint error, not a style nit;
  every quantity string carries the number.
- **`@PreviewFontScale` is singular.** A plural spelling does not compile.
