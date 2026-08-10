# UI Components

Status: draft

## Context

A consistent app is built from components that are each used for the purpose they were designed for. This spec fixes the usage rules for the individual Material 3 UI elements — when each component is the right choice, when it is the wrong one, and how a project *enforces* uniform usage — so that every screen the Compose-UI skill (REQ-13) generates and every finding the UX-audit skill (REQ-14) raises follows one component vocabulary.

The content is distilled from a research pass (August 2026) over the official Material 3 component guidelines (m3.material.io, fully rendered per component), the Compose component documentation and API mapping (developer.android.com), the 2025 M3 Expressive component updates, and the consistency-governance machinery of the Now in Android reference project (design-system wrapping plus a custom Android Lint check at ERROR severity that forbids raw Material components where a wrapper exists).

Boundaries: design foundations (color/typography/shape roles) and navigation-UI choice live in `spec/android/app-design-navigation/`; the icon system lives in `spec/android/iconography/`; large-window sizing constraints on dialogs/sheets live in `spec/android/screen-formats/` §B.

Readers: authors of this repo's Android skills and reviewers judging whether generated or audited UI uses components consistently and correctly.

## Goals

- One semantic vocabulary: for every UI need there is a defined component, and for every component a defined purpose — including the explicit misuses
- A visible prominence hierarchy: exactly one primary action per screen, expressed through the emphasis ladder, never through competing highlights
- Enforced consistency: the design-system wrapping pattern plus lint enforcement makes uniform usage a build-time property, not a review hope
- Currency: the 2025 Expressive component supersessions (segmented buttons, baseline bottom app bar, small FAB) don't leak into newly generated code

## Non-Goals

- Color, typography, shape, and motion foundations — `spec/android/app-design-navigation/` §A
- Navigation components' choice rules (bar/rail/drawer) — `spec/android/app-design-navigation/` §C
- Icon style, sizes, and accessibility rules — `spec/android/iconography/`
- Adaptive sizing of components on large windows — `spec/android/screen-formats/` §B
- Building a general-purpose design-system library — the governance pattern here serves per-app consistency

## Requirements

### A. Component selection — the semantic matrix

- **MUST** follow the button emphasis ladder: filled button for the one important, final action of a flow ("Save", "Confirm" — ideally one per screen); tonal for lower-priority-but-emphasized ("Next"); outlined for medium-emphasis secondary actions; text button for the lowest priority and multi-option rows; elevated only when separation from a prominent background demands it
- **MUST** keep button labels short (1–3 words), single-line (no truncation or wrapping), one leading icon at most, and never underlined (links are hyperlinked body text)
- **MUST** use at most one FAB per screen, only for the most important constructive action (create, compose, start); **MUST NOT** use FABs for minor or destructive actions, per-card actions, or as a toolbar substitute; the FAB stays in place on scroll; the small FAB is no longer recommended
- **MUST** respect the chips-vs-buttons distinction: chips represent forking paths and dynamic context (assist/filter/input/suggestion), buttons represent linear steps — **MUST NOT** use chips to progress or finish a task, show a single chip alone, or build a filter chip set with only one option; input chips carry a required trailing remove icon
- **MUST** pick the message surface by severity: dialog only for blocking decisions/critical information (max two actions, confirming action right, dismissive never disabled, confirming disabled until a choice exists); snackbar for low/medium-priority process feedback (one optional action, never critical content, never stacked, never the only path to a feature, no icons); modal bottom sheet as the mobile alternative for long action lists; toast only for background-context notes — in the foreground a snackbar wins
- **MUST** use full-screen dialogs only on compact windows for multi-step subtasks; on medium+ windows a basic dialog replaces them
- **MUST** apply the selection-control matrix: checkboxes for multiple selection in lists, radio buttons for single selection (≤ 5 options, always one pre-selected, vertical, never nested), switches for standalone binary settings that take effect immediately — **MUST NOT** use switches for multi-select lists, opposing options (button group instead), or anything requiring a save step
- **MUST** apply the wait-indication matrix consistently: nothing below ~200 ms; the loading indicator for short indeterminate waits (200 ms–5 s, also the pull-to-refresh surface); a progress indicator (determinate as soon as progress is known) beyond ~5 s; one indicator per group, the same variant for the same process across the app, and never a loading→determinate hand-off in place
- **MUST** keep text fields uniform: one variant (filled or outlined) per form — never mixed side by side; every field has an always-visible label (placeholder is not a label), error text replaces supporting text (never both), required fields are marked and explained
- **MUST** honor container rules: cards never scroll internally, never host swipeable content or more than one swipe action, and don't force content that spacing/headers would structure better; list rows keep element positions consistent, supporting text 1–3 lines; menus show conditionally unavailable items as disabled instead of removing them, and never embed direct controls (switches/buttons) in menu items
- **SHOULD** use search surfaces per role (persistent bar when search is central, icon button when secondary), date pickers per input mode (text input for distant dates like birthdays — never a calendar-scroll), and badges only on navigation items (small = unread, large = count, "999+" cap)

### B. Prominence hierarchy

- **MUST** express exactly one primary action per screen with the highest-emphasis component (filled button or FAB — never both competing); all other actions step down the ladder
- **MUST NOT** emphasize more than one action at a time in a toolbar or action row; too many buttons on a screen is itself the documented anti-pattern — prefer alternative surfaces (chips, text links, icon buttons)
- **SHOULD** distinguish mixed button variants through their color/emphasis roles so the primary action stays unambiguous

### C. Consistency governance

- **MUST** channel every component whose defaults the app changes, or whose freedom the app restricts, through a design-system wrapper (the `NiaButton` pattern): the wrapper bakes in theme defaults and exposes a deliberately reduced API (no `colors`/`shape`/`elevation` passthrough); components used stock stay direct Material 3 usage — wrapping everything is not the goal
- **MUST** configure components exclusively through theme roles and the `*Defaults` APIs (slot parameters, `ButtonDefaults`, `CardDefaults`, …) — never color/size literals at call sites; without a `MaterialTheme` ancestor Material components render wrong by design
- **MUST**, once wrappers exist, enforce them with a lint check at ERROR severity that maps each wrapped Material component to its wrapper (the Now-in-Android `DesignSystemDetector` pattern, wired through the build so it applies project-wide)
- **SHOULD** place wrappers in the design-system module (`:core:designsystem` per `spec/android/project-structure/` §C once modularized; the `designsystem` package per its §E in single-module apps); **MAY** maintain a catalog app/screen that renders every wrapper for visual review
- **SHOULD** use the standard disabled-state alphas (38 % content, 12 % container per the M3 state specification, mirrored by the reference project's constants [R21][R25]) via the components' own state layers rather than custom opacity

### D. Expressive currency

- **MUST NOT** generate the superseded baseline components into new code: segmented buttons (→ connected button group), the baseline bottom app bar (→ docked toolbar), the small FAB
- **MAY** adopt the new Expressive components (button groups, split button, FAB menu, floating/docked toolbars, loading indicator, wavy progress) as their Compose APIs reach stability; while `@ExperimentalMaterial3ExpressiveApi`, each adoption is a recorded decision
- **SHOULD** track component-guidance changes at authoring time — the component set moved substantially in 2025, and stale component choices are audit findings, not style preferences

## Acceptance Criteria

The criteria below are a deliberate representative rollup of §A–§D, not a 1:1 mapping; every requirement bullet above is normative on its own.

- [ ] Every generated screen has at most one filled button or FAB as its primary action, and no second equally-emphasized action competes with it
- [ ] No dialog in generated code carries more than two actions or a disabled dismissive action; no snackbar carries critical information, an icon, or more than one action
- [ ] Selection controls match their semantics everywhere: no switch in a multi-select list, no radio group without a pre-selection, no selection control whose effect waits for a save button
- [ ] Wait indication follows the matrix: no spinner below 200 ms, no indeterminate indicator for waits with known progress beyond 5 s, and one process uses one indicator variant app-wide
- [ ] No form mixes filled and outlined text fields; every text field has a visible label; error text replaces supporting text
- [ ] No card scrolls internally or hosts swipeable content; no menu item embeds a switch or button; conditionally unavailable menu items render disabled
- [ ] No chip advances a task; no single-chip set exists; every input chip has a remove affordance
- [ ] Generated code contains no segmented buttons, baseline bottom app bars, or small FABs
- [ ] All component styling flows through theme roles and `*Defaults`/wrapper APIs; no color or dimension literal appears at a component call site
- [ ] Where design-system wrappers exist, a lint check at ERROR severity forbids the wrapped raw Material components, and CI runs it
- [ ] Experimental Expressive APIs appear only with a recorded adoption decision

## Open Questions

All four questions are parking-lot class: the requirements above state a working default for each (wrap-on-customization, baseline components already banned, catalog optional, component defaults acceptable).

- Wrapper scaffold timing: should the Compose-UI skill generate the design-system wrapper layer (plus lint check) from the first screen, or only once the app customizes a component's defaults?
- Expressive component adoption: switch generated code to connected button groups and docked toolbars now (guidance already deprecates the baselines) even where the Compose API is still experimental, or wait for stable?
- Catalog surface: standard `app-catalog` module for every generated app, or only for apps with a grown design system?
- Disabled-state alpha constants: read from a shared token file or accept the component defaults silently?

## References

All sources retrieved 2026-08-11. Class markers: (P) primary/authoritative vendor documentation, (S) secondary (reference-project code). m3.material.io pages are client-rendered; contents were captured via rendered fetches of the canonical URLs. Component usage rules are Material 3's own authoritative design specification — the single primary source for each component — corroborated by the Compose API docs (R22–R24) and the reference project (R25) where implementation behavior is asserted.

- [R1] Buttons guidelines (P): <https://m3.material.io/components/buttons/guidelines>
- [R2] FAB guidelines (P): <https://m3.material.io/components/floating-action-button/guidelines>
- [R3] Icon buttons guidelines (P): <https://m3.material.io/components/icon-buttons/guidelines>
- [R4] Chips guidelines (P): <https://m3.material.io/components/chips/guidelines>
- [R5] Cards guidelines (P): <https://m3.material.io/components/cards/guidelines>
- [R6] Lists guidelines (P): <https://m3.material.io/components/lists/guidelines>
- [R7] Dialogs guidelines (P): <https://m3.material.io/components/dialogs/guidelines>
- [R8] Bottom sheets guidelines (P): <https://m3.material.io/components/bottom-sheets/guidelines>
- [R9] Snackbar guidelines (P): <https://m3.material.io/components/snackbar/guidelines>
- [R10] Toasts (foreground → snackbar) (P): <https://developer.android.com/guide/topics/ui/notifiers/toasts>
- [R11] Text fields guidelines (P): <https://m3.material.io/components/text-fields/guidelines>
- [R12] Menus guidelines (P): <https://m3.material.io/components/menus/guidelines>
- [R13] Checkbox / radio / switch guidelines (P): <https://m3.material.io/components/checkbox/guidelines> (and /radio-button, /switch)
- [R14] Progress indicators guidelines (P): <https://m3.material.io/components/progress-indicators/guidelines>
- [R15] Loading indicator guidelines (Expressive, wait matrix) (P): <https://m3.material.io/components/loading-indicator/guidelines>
- [R16] Badges guidelines (P): <https://m3.material.io/components/badges/guidelines>
- [R17] Search guidelines (P): <https://m3.material.io/components/search/guidelines>
- [R18] Date/time picker guidelines (P): <https://m3.material.io/components/date-pickers/guidelines> (and /time-pickers)
- [R19] Segmented buttons → button groups supersession (P): <https://m3.material.io/components/button-groups/guidelines>
- [R20] Toolbars guidelines (bottom-app-bar supersession, single-emphasis rule) (P): <https://m3.material.io/components/toolbars/guidelines>
- [R21] Building with M3 Expressive (P): <https://m3.material.io/blog/building-with-m3-expressive>
- [R22] Compose components API mapping (P): <https://developer.android.com/develop/ui/compose/components>
- [R23] Material 3 theming in Compose (roles, Defaults, no-theme caveat) (P): <https://developer.android.com/develop/ui/compose/designsystems/material3>
- [R24] Custom design systems in Compose (wrap-then-extend rule) (P): <https://developer.android.com/develop/ui/compose/designsystems/custom>
- [R25] Now in Android design-system wrappers and lint enforcement (S): <https://github.com/android/nowinandroid> (core/designsystem/component/*, lint/DesignSystemDetector.kt)
- [R26] Compose Material 3 releases (Expressive API graduation) (P): <https://developer.android.com/jetpack/androidx/releases/compose-material3>
