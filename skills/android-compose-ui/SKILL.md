---
name: android-compose-ui
description: "Authors new Jetpack Compose screens and components with mobile-UX patterns applied at authoring time — Material 3 theming through color/typography/shape roles, window-size-class adaptivity (list-detail, supporting-pane, feed), Material Symbols icons, externalized strings with per-locale previews, and 48dp/200%-font-scale accessibility — generated as a stateful route plus stateless content composable split, with @PreviewScreenSizes, @PreviewFontScales, per-locale previews, and a Robolectric Compose test alongside. Invoke when the user asks to build, add, or scaffold an Android screen, a Compose UI, or a component. For reviewing existing UI, use the read-only ux-audit agent instead. Also handles equivalent German-language requests. Supports resume on re-invocation across per-screen approval gates."
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
see_also:
  - android-feature-implement
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

## Boundary vs the ux-audit agent

This skill **authors** new UI with UX patterns applied up front (REQ-13). Reviewing
*existing* screens against the same UX criteria is the job of the read-only `ux-audit` agent
(REQ-14): that agent inspects and reports, it never writes. Do not audit here and do not
author there. When the user asks to review or critique existing UI, hand off to that agent.

## User-language policy

Detect the user's language and respond in it (German for this operator). All generated
artifacts stay in their canonical form: Kotlin, resource keys, and code comments in English;
user-visible copy is externalized to `strings.xml` (English source in `values/`, German in
`values-de/`) per `spec/android/localization/` §A — never inlined in composables.

## Preconditions

Before writing anything:

- Confirm the working directory is a git repository and locate the target module. This skill
  authors *into* an app the `project-setup` skill already scaffolded per
  `spec/android/project-structure/`; if no `:app` module or `designsystem` package exists,
  stop and route the user to project setup first.
- Read `references/ux-checklist.md` in full before proposing any screen — it is the
  authoring-time rule set distilled from all seven grounding specs, and every generated screen
  is checked against it.
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
`spec/android/test-automation/` §D). Pick the layout family from
`spec/android/screen-formats/` §C: list-detail, supporting-pane, or feed. Gate: confirm the
contract before generating code.

### 2. Generate the route + content split

Read `references/screen-template.md` when authoring the composable. Produce a thin stateful
route composable (obtains the ViewModel, collects state, wires event lambdas) delegating to a
stateless content composable that takes `uiState` plus event lambdas and passes no
`NavController` (per `spec/android/app-design-navigation/` §B and project-structure §E).
Apply, at authoring time: Material 3 roles/tokens only (no literals), window-size-class
adaptivity, Material Symbols via the central icon registry, `stringResource` for every string,
and the 48dp/`sp`/edge-to-edge accessibility baseline. Gate: confirm before writing.

Where the screen shows a collection, apply `spec/android/long-list-scrolling/` in the same
pass — the container choice (§A), a stable domain `key` plus `contentType` on every item and
no derivation inside an item body (§B), and a declared item size so nothing measures to zero
before its content arrives (§A). These are authoring-time properties: retrofitting them later
means rewriting the list.

### 3. Externalize strings and icons

Add every user-visible string to `values/strings.xml` (positional placeholders, `<plurals>`
for counts) and its `values-de/` translation; register any new icon as a checked-in vector
drawable behind the design-system registry (`spec/android/iconography/` §A/§B). Never add
`material-icons-extended`. Gate: confirm the string keys and translations.

### 4. Generate previews

Emit `<Composable>Preview` functions next to the stateless content composable covering every
`uiState`, plus `@PreviewScreenSizes`, `@PreviewFontScales`, and per-locale
`@Preview(locale = "de")` / `@Preview(locale = "ar")` (RTL) previews per
`spec/android/localization/` §F and screen-formats §D.

### 5. Generate the Compose test

Read `references/compose-test-template.md` when writing the test. Generate a Robolectric-hosted
Compose test in `src/test/` that drives the stateless content composable with fake `uiState`
and no-op lambdas, matches nodes via semantics (resource-looked-up text, content descriptions,
roles) not `testTag`, and asserts each state renders. Add a `StateRestorationTester` check
where the screen holds `rememberSaveable` state (`spec/android/test-automation/` §D).

### 6. Build green and report

Run `./gradlew build` (compile + lint + the new test). Success requires spec conformance AND
a green build (REQ-1). If it is red, report the failure explicitly — never leave a silent red
state (REQ-7). Summarize the files written, the UX-checklist items satisfied, and any
spec-gap findings.

## Reference files

- Read `references/ux-checklist.md` before step 1 for the authoring-time UX rule set (M3,
  navigation, adaptivity, iconography, localization, accessibility) distilled from the specs.
- Read `references/screen-template.md` in step 2 for the route/content composable split,
  adaptive list-detail layout, theming, and preview templates.
- Read `references/compose-test-template.md` in step 5 for the Robolectric Compose-test and
  state-restoration templates.

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
- **Never** key a lazy list by index, emit several logical entries from one `item {}`, nest a
  same-direction scroll container with an unbounded inner size, or let an asynchronously filled
  item measure to zero in the scroll direction (`spec/android/long-list-scrolling/` §A/§B).
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
- **Robolectric is only sanctioned for UI-behavior and screenshot tests.** Plain
  ViewModel/logic unit tests stay pure-JVM (JUnit 4 + `kotlinx-coroutines-test`); do not reach
  for Robolectric there (`spec/android/test-automation/` §B).
- **Window size classes are window properties, not device properties.** They change at runtime
  on rotation, fold, and split-screen; every class transition must preserve UI state. Never
  cache "is tablet".
- **The fill axis is the selected-state signal for Material Symbols**, filled = active. When no
  filled variant exists, use a weight increase as the fallback so selection is not carried by
  color alone (`spec/android/iconography/` §A).
