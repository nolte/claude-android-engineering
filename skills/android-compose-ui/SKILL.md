---
name: android-compose-ui
description: "Authors new Jetpack Compose screens and components grounded in the UI specs under spec/android/, with mobile-UX patterns applied at authoring time — Material 3 theming through color/typography/shape roles, window-size-class adaptivity (list-detail, supporting-pane, feed), Material Symbols icons, externalized strings, 48dp/200%-font-scale accessibility, input handling with staged validation, error timing, submission rules and IME insets, and perceived-performance hooks (200 ms wait rule, ReportDrawnWhen) — generated as a stateful route plus stateless content composable, with @PreviewScreenSizes, @PreviewFontScale, per-locale previews, and a Robolectric Compose test alongside. Invoke to build, add, or scaffold an Android screen, Compose UI, or component. For reviewing existing UI, use the read-only android-ux-reviewer agent instead. Also handles equivalent German-language requests. Supports resume on re-invocation across per-screen approval gates."
tags: [ui, scaffolding]
phase: build
summary: "Authors Compose screens with M3 theming, adaptivity, localization, and accessibility baked in at authoring time — route/content split, previews, and a Robolectric Compose test."
summary_de: "Erstellt Compose-Screens mit M3-Theming, Adaptivität, Lokalisierung und Barrierefreiheit direkt beim Bauen — Route/Content-Split, Previews und ein Robolectric-Compose-Test."
use_when:
  - "you want to build a new Android screen or Compose component"
  - "you want a screen scaffolded with its preview and Compose test"
  - "you want a new navigation destination wired with UX patterns already applied"
dont_use_when:
  - situation: "You want a feature implemented across UI, ViewModel, repository, and backend boundary"
    alternative: android-feature-implement
  - situation: "You want existing Compose UI reviewed or audited without changing it"
    alternative: android-ux-reviewer
  - situation: "You want the localization of existing screens audited or completed rather than a new screen authored"
    alternative: android-localization-apply
see_also:
  - android-ux-reviewer
  - android-feature-implement
  - android-permissions-derive
  - android-perceived-performance
  - android-localization-apply
  - android-code-reviewer
resumable: true
---

# Android Compose UI

Builds a new Compose screen or component so it is theme-correct, adaptive, localized,
accessible, and testable *by construction* — the UX rules from the grounding specs are
applied while the code is written, never bolted on afterward. Every screen ships as a
stateful route composable plus a stateless content composable, with previews and a
Robolectric-hosted Compose test alongside.

The authoritative rules live in the specs under `spec/android/`; this skill operationalizes
them and never restates or contradicts them. On any conflict the spec wins — report the gap
and propose a spec change rather than deciding silently.

## Grounding specs

Grounded in these `spec/android/` specs (canonical `en.md`), and nothing else decides a UX
question: `app-design-navigation` (§A–§F, incl. deep links), `ui-components`,
`screen-formats` (incl. foldables and input tiers), `iconography`, `localization`,
`long-list-scrolling`, `user-input-validation` (§A–§H, incl. submission), plus
`perceived-performance` §A (TTFD, `ReportDrawnWhen`), `test-automation` §D/§E (Compose tests,
ATF), `project-structure` §D/§E (placement, route/content split), and `logging` §E — a composable
body never logs, because it may re-run every frame, be skipped, discarded, or reordered; a log
belongs in a callback, in a keyed `LaunchedEffect`, or below the UI layer.

## Why this is a skill, not an agent

- **Per-screen user approval is the contract.** Each screen is proposed, confirmed, and
  written with explicit consent (name, destination, layout family, state shape); the flow is
  a sequence of approval gates an agent's fire-and-forget shape can't carry.
- **Persistent code output in the main context.** The generated Kotlin, previews, strings,
  and test land in the working tree and flow back into the conversation for review, not into
  a structured-report boundary.
- **Interactive and resumable.** Multi-screen requests span several gates; the run is
  `resumable: true` so an interrupted authoring session continues without re-asking.
- Counter-dimension considered: a narrow agent would gain context-window isolation on the
  heavy template generation, but the load-bearing part is the per-screen approval dialogue,
  so per `spec/claude/skill-vs-agent/` §Primary decision rule the skill wins.

## Boundary vs the android-ux-reviewer agent

This skill **authors** new UI with UX patterns applied up front (REQ-13). Reviewing
*existing* screens against the same UX criteria is the job of the read-only
`android-ux-reviewer` agent (REQ-14): that agent inspects and reports, it never writes. Do not
audit here and do not author there. When the user asks to review or critique existing UI, hand
off to `android-ux-reviewer`; when that agent's findings come back, this skill applies them.

## German trigger phrases

Respond to these (and equivalents) exactly as to their English counterparts; the frontmatter
`description` stays English-only per `skill-management` §Structure:

- "Baue einen neuen Screen", "Erstelle eine Compose-UI für …", "Lege ein neues Composable an"
- "Scaffolde den Einstellungs-Screen mit Preview und Test"
- "Füge ein neues Navigationsziel mit Liste und Detail hinzu"
- "Baue ein Formular für … (mit Validierung)"

## User-language policy

Detect the user's language and respond in it (German for this operator). All generated
artifacts stay in their canonical form: Kotlin, resource keys, and code comments in English;
user-visible copy is externalized to `strings.xml` (English source in `values/`, German in
`values-b+de/` for a new directory — but continue in an existing legacy `values-de/` rather
than creating both: they map to the same `de` qualifier and split the key set) per
`spec/android/localization/` §A/§B — never inlined in composables.

## Operations

This skill has one dispatchable operation, `author`, run as the per-screen procedure below.
Multi-screen requests run it once per screen, with a checkpoint after every gate.

## Preconditions

Before writing anything:

- Confirm the working directory is a git repository and locate the target module. This skill
  authors *into* an app the `android-project-scaffold` skill (or an equivalent existing
  project) laid out per `spec/android/project-structure/`. If no Gradle application module
  exists at all, stop and route the user to `android-project-scaffold`.
- If the app has no `designsystem` package or module (project-structure §E makes it a SHOULD;
  REQ-11 admits existing apps that lack it), **do not stop**: report the gap explicitly,
  propose creating the package (theme + icon registry) as the first written item of this run,
  and — if the user declines — continue by resolving every color, type, and shape through the
  Material 3 roles of the app's existing `MaterialTheme` and referencing icons through a
  registry object created next to the screen. Record the missing package as a spec-conformance
  finding in the final report (REQ-6).
- Read `references/ux-checklist.md` in full before proposing any screen — it is the
  authoring-time rule set distilled from the grounding specs listed above, and every generated
  screen is checked against it.
- Check for uncommitted changes in the paths to be touched (feature package, `strings.xml`,
  `src/test/`). If dirty, report and ask whether to stash, commit, or abort — never overwrite
  unconfirmed work (REQ-8).

## Authoring procedure

Run these steps once per screen or component; confirm with the user at each gate before
writing files.

### 1. Define the screen contract

Agree on the feature package, the screen name, the navigation destination (a `@Serializable`
`NavKey`), and the `uiState` shape (a sealed/`data class` UI state covering loading,
populated, empty, and error — every state must be constructible without a ViewModel per
`spec/android/test-automation/` §D; the populated case carries an `ImmutableList` or an
`@Immutable` type, the error case carries a closed `ErrorKind`, never a raw server string).
Pick the layout family from `spec/android/screen-formats/` §C: list-detail, supporting-pane,
or feed. If the destination is a top-level tab, note that it owns its own back stack
(app-design-navigation §B); if it is deep-linkable, note the synthetic back stack it needs
(§E). Gate: confirm the contract before generating code.

### 2. Generate the route + content split

Read `references/screen-template.md` when authoring the composable. Produce a thin stateful
route composable (obtains the ViewModel, collects state, wires event lambdas) delegating to a
stateless content composable that takes `uiState` plus event lambdas and passes no
`NavController` (per `spec/android/app-design-navigation/` §B and project-structure §E).
Apply, at authoring time: Material 3 roles/tokens only (no literals), window-size-class
adaptivity, Material Symbols via the central icon registry, `stringResource` for every string,
and the 48dp/`sp`/edge-to-edge accessibility baseline. The loading state shows nothing for the
first ~200 ms and an indeterminate indicator afterwards (ui-components §A), and the screen
signals full display with `ReportDrawnWhen { uiState is Success }` placed where the content is
genuinely present (perceived-performance §A). Gate: confirm before writing.

Where the screen takes a value from the user, apply `spec/android/user-input-validation/` in the
same pass — state-based text field with a per-field touched flag (§B); keyboard type,
capitalization, autocorrect, IME action per field (§C); no error before the field is first
left, every error cleared on the fixing keystroke (§D); error text next to the field with
`Modifier.semantics { error(...) }`, a live region for form-level status, an error summary on
long forms (§E); `ContentType.NewUsername`/`NewPassword` on registration and change-credential
forms (§F); and the §G submission contract — exactly one in-flight submission with a visible
pending state, values readable while pending and editable again on failure, rejection and
transport failure never the same message, no navigation away before backend confirmation
(queued/local-first writes excepted). The form sits under `Modifier.imePadding()` and brings
the focused field into view (`BringIntoViewRequester`). Client-side checks are shaping and
well-formedness only; the acceptance decision stays with the backend (§A). These are
authoring-time properties — retrofitting them later means rewriting the form; the template
carries the form snippet.

Where the screen shows a collection, apply `spec/android/long-list-scrolling/` in the same
pass — the container choice (§A), a stable domain `key` plus `contentType` on every item and
no derivation inside an item body (§B), and a declared item size so nothing measures to zero
before its content arrives (§A); the template carries the lazy-list snippet. These are
authoring-time properties: retrofitting them later means rewriting the list.

### 3. Externalize strings and icons

Add every user-visible string to `values/strings.xml` (positional placeholders, `<plurals>`
for counts, `translatable="false"` for brand/technical tokens, no translatable text in
`<string-array>`) and its German translation (`values-b+de/` for a new directory; an existing
legacy `values-de/` is continued, never doubled); register any new icon as a checked-in
vector drawable behind the design-system registry, with `android:autoMirrored="true"` on
directional glyphs (`spec/android/iconography/` §A/§B). Never add `material-icons-core` or
`material-icons-extended`. Gate: confirm the string keys and translations.

### 4. Generate previews

Emit `<Composable>Preview` functions next to the stateless content composable covering every
`uiState`, plus `@PreviewScreenSizes`, `@PreviewFontScale`, and per-locale
`@Preview(locale = "de")` / `@Preview(locale = "ar")` (RTL) previews per
`spec/android/localization/` §F and screen-formats §D.

### 5. Generate the Compose test

Read `references/compose-test-template.md` when writing the test. Generate a Robolectric-hosted
Compose test in `src/test/` that drives the stateless content composable with fake `uiState`
and no-op lambdas, matches nodes via semantics (resource-looked-up text, content descriptions,
roles) not `testTag`, asserts each state renders, synchronizes via `mainClock`/`waitUntil`
(never sleeps), and enables ATF checks (`spec/android/test-automation/` §D/§E). Add a
`StateRestorationTester` check where the screen holds `rememberSaveable` state, a
`DeviceConfigurationOverride.ForcedSize` case for the reference matrix, and — for a
Navigation 3 destination — a test `NavDisplay` asserting on back-stack contents. Where the
screen takes input, add the `spec/android/user-input-validation/` §H set the template carries:
timing contract, error semantics and live region, the adversarial value set as pure-function
tests, a `SavedStateHandle` round-trip for holder-owned input, and a server-rejection fake
asserting the error lands on the field with the input preserved — without them a generated
form can violate §D–§G and still build green.

### 6. Build green and report

Run `./gradlew build` (compile + lint + the new test). Success requires spec conformance AND
a green build (REQ-1). If it is red, report the failure explicitly — never leave a silent red
state (REQ-7). Summarize the files written, the UX-checklist items satisfied, and any
spec-gap findings.

## Reference files

- Read `references/ux-checklist.md` before step 1 for the authoring-time UX rule set (M3,
  navigation, adaptivity, iconography, localization, accessibility, lists, input, perceived
  performance) distilled from the specs.
- Read `references/screen-template.md` in step 2 for the route/content composable split,
  delayed loading state and `ReportDrawnWhen`, adaptive list-detail layout, lazy list, form
  and submission, theming, and preview templates.
- Read `references/compose-test-template.md` in step 5 for the Robolectric Compose-test,
  state-restoration, configuration-variant, input, and Navigation 3 templates.

## Resumability

Per `spec/claude/resumable-work/`, this skill is `resumable: true`. State is persisted to
`.resume/android-compose-ui/<run-id>.yml` after every successful per-screen approval gate and
after each named step boundary. On re-invocation, scan `.resume/android-compose-ui/*.yml` for
files with `status: in_progress` whose `inputs:` snapshot (target module + screen name) matches
the current request; when one matches, prompt
`Resume run <run_id> from phase <phase> (last checkpoint <last_checkpoint_at>)? [resume / start-new / discard]`.
`resume` re-hydrates and re-asks no answered gate; `start-new` leaves the old file intact;
`discard` deletes it. Fail closed on unparseable or higher-`schema_version` files. The envelope
keys and lifecycle are load-bearing in the spec and are not duplicated here.

## Hard rules

- **Never** hard-code a color, text size, or corner radius; all styling resolves through
  `MaterialTheme` roles and tokens (`spec/android/app-design-navigation/` §A).
- **Never** pass a `NavController` into a screen composable or navigate during composition;
  screens expose event lambdas only (app-design-navigation §B).
- **Never** inline a user-visible string in a composable; externalize to `strings.xml` with
  positional placeholders and ship the German translation (localization §A/§F).
- **Never** add `material-icons-core`/`material-icons-extended`, use Navigation 2, lock
  orientation/resizability, branch on "isTablet", or generate superseded baseline components
  (segmented buttons, baseline bottom app bar, small FAB) — all outdated per the specs (REQ-9).
- **Never** emit more than one primary action (filled button or FAB) per screen
  (`spec/android/ui-components/` §B).
- **Never** show a loading indicator inside the first ~200 ms of a wait, and never ship a
  screen without a `ReportDrawn*` signal placed where its content is genuinely ready
  (ui-components §A, perceived-performance §A).
- **Never** key a lazy list by index, emit several logical entries from one `item {}`, nest a
  same-direction scroll container with an unbounded inner size, or let an asynchronously filled
  item measure to zero in the scroll direction (`spec/android/long-list-scrolling/` §A/§B).
- **Never** raise a field error while the user is typing into a field for the first time, leave a
  shown error standing after the value became valid, or signal an error by colour or icon without
  text (`spec/android/user-input-validation/` §D/§E).
- **Never** let a screen lose what the user typed — through a failed submission, a rejection, a
  rotation, or process death — and never block pasting into a credential field
  (`spec/android/user-input-validation/` §B/§F).
- **Never** allow a second in-flight submission of the same form, present a transport failure as
  the user's mistake (or a rejection as a transport error), or navigate away before the backend
  has confirmed a non-queued write (`spec/android/user-input-validation/` §G).
- **Never** overwrite an existing file without explicit per-item confirmation (REQ-8).
- **Always** generate the stateless content composable, its previews, and the Compose test in
  the same pass — a screen is not "done" without them.
- **Always** end with a `./gradlew build`; report a red state rather than leaving it silent.
- When a spec under `spec/android/` disagrees with this skill, the spec wins — report the gap
  and propose a spec change (REQ-6).

## Gotchas

Concrete corrections to non-obvious facts the executing agent would otherwise get wrong:

- **The `@Preview(locale = …)` parameter only sets `LocalConfiguration`.** Code that reads
  `Locale.getDefault()` directly won't see it — and such code shouldn't exist in UI. Verify
  German/RTL previews by reading through `stringResource`, not device-locale APIs.
- **The multi-preview annotation is `@PreviewFontScale` (singular).** There is no
  `@PreviewFontScales`; the sibling annotations are `@PreviewScreenSizes`, `@PreviewLightDark`,
  and `@PreviewDynamicColors`.
- **`Icons.AutoMirrored.*` lives in `material-icons-core`, which is forbidden.** Auto-mirroring
  for checked-in vectors is `android:autoMirrored="true"` in the drawable XML; the registry
  exposes the drawable, not an `Icons.*` reference.
- **Robolectric is only sanctioned for UI-behavior and screenshot tests.** Plain
  ViewModel/logic unit tests stay pure-JVM (JUnit 4 + `kotlinx-coroutines-test`); do not reach
  for Robolectric there (`spec/android/test-automation/` §B).
- **`StateRestorationTester` recreates only the composition.** A ViewModel stays alive, so it
  proves nothing about `SavedStateHandle` keys — those need a direct round-trip test
  (user-input-validation §H).
- **Window size classes are window properties, not device properties.** They change at runtime
  on rotation, fold, and split-screen; every class transition must preserve UI state. Never
  cache "is tablet".
- **The fill axis is the selected-state signal for Material Symbols**, filled = active. When no
  filled variant exists, use a weight increase as the fallback so selection is not carried by
  color alone (`spec/android/iconography/` §A).
