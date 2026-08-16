# Authoring-time UX checklist

The rule set every generated screen is checked against, distilled from the eight grounding specs
under `spec/android/`. This is a working digest, not a source of truth: on any conflict the
named spec wins. Apply these while writing the screen, not after.

## Table of contents

- [1. Material 3 foundations](#1-material-3-foundations) — `app-design-navigation` §A
- [2. Navigation architecture and UI](#2-navigation-architecture-and-ui) — `app-design-navigation` §B/§C/§D
- [3. Adaptivity and screen formats](#3-adaptivity-and-screen-formats) — `screen-formats`
- [4. Components](#4-components) — `ui-components`
- [5. Iconography](#5-iconography) — `iconography`
- [6. Localization](#6-localization) — `localization`
- [7. Accessibility baseline](#7-accessibility-baseline) — cross-cutting
- [8. Research-backed usability](#8-research-backed-usability) — `app-design-navigation` §F
- [9. Lists and continuous scrolling](#9-lists-and-continuous-scrolling) — `long-list-scrolling`
- [10. User input and validation](#10-user-input-and-validation) — `user-input-validation`

## 1. Material 3 foundations

- Every color resolves through a Material color role (`primary`/`onPrimary`,
  `surface`/`onSurface`, container variants) from `MaterialTheme` — no hard-coded values.
- Content is paired with its `on-*` role so the contrast guarantee holds (4.5:1 small text,
  3:1 large text/graphics).
- Typography uses the display/headline/title/body/label roles; radii use shape tokens; depth
  comes from tonal surface-container roles, never shadow overlays.
- Dark theme is a real dark `ColorScheme` with light/dark/system choice (system default);
  never rely on force-dark. Dynamic color (Android 12+) with a static brand fallback.
- Edge-to-edge is handled via `Scaffold`/insets; no interactive element inside system-gesture
  zones. Launch uses the SplashScreen API — no custom splash activity.

## 2. Navigation architecture and UI

- Single-activity, Navigation 3. Back stack is app-owned state: keys implement `NavKey`, are
  `@Serializable`, held in `rememberNavBackStack`; rendering via `NavDisplay` +
  `entryProvider`. Navigation 2 is prohibited in new code.
- Screen ViewModels scope to nav entries via the official decorators
  (`rememberSaveableStateHolderNavEntryDecorator` + `rememberViewModelStoreNavEntryDecorator`).
- Navigation arguments are IDs/simple values only — never entity objects.
- Never navigate during composition; screens expose event lambdas and never receive a
  `NavController`. Guard rapid double-taps (`dropUnlessResumed`-style).
- Top-level: 3–5 destinations in a navigation bar on compact (rail from medium); icon *and*
  label on every item; visible selected state (filled-icon convention).
- Primary actions in the thumb-friendly bottom zone; the top app bar carries only
  secondary/rare actions. One FAB maximum per screen.
- Predictive back: `android:enableOnBackInvokedCallback="true"`, no `onBackPressed()`
  interception; Compose uses `BackHandler`/`PredictiveBackHandler` enabled only while their
  condition holds. Up and Back are identical inside the task.
- State preservation: rotation, recents return, and process death land the user exactly where
  they were (serializable keys + `rememberSaveable`/`SavedStateHandle`).

## 3. Adaptivity and screen formats

- Top-level layout branches only on `currentWindowAdaptiveInfo().windowSizeClass` — never on
  device type, physical size, or deprecated size-class APIs.
- Switch content structure at the expanded boundary: one pane on compact/medium, two panes on
  expanded where content is list-detail or main-supporting (feed is the single-pane exception).
- Replace/show/hide layout components across classes — never stretch a phone layout.
- On large windows, cap the width of dialogs, sheets, buttons, and text fields; grids widen
  (`LazyVerticalGrid(GridCells.Adaptive(...))`) instead of stretching one column.
- No orientation, aspect-ratio, or resizability restriction anywhere. Fully functional in
  multi-window (multi-resume; release/reacquire exclusive resources).
- Canonical layouts: list-detail via `NavigableListDetailPaneScaffold` (or the Nav-3
  `ListDetailSceneStrategy`), supporting-pane ~70/30, feed as an adaptive grid. Selection
  state survives class changes; two-pane back uses `PopUntilScaffoldValueChange`.
- Target Play adaptive-quality Tier 3 unconditionally, Tier 2 as the goal.

## 4. Components

- Button emphasis ladder: filled = the one important final action; tonal = emphasized
  secondary; outlined = medium; text = lowest/multi-option. Labels 1–3 words, single-line, at
  most one leading icon, never underlined.
- Exactly one primary action (filled button or FAB, never both competing) per screen; no two
  equally-emphasized actions in a row.
- Message surface by severity: dialog for blocking decisions (≤2 actions, dismissive never
  disabled); snackbar for low/medium process feedback (≤1 action, no icon, never critical);
  modal bottom sheet for long action lists; toast only for background context.
- Selection controls: checkbox = multi-select in lists; radio = single (≤5, one pre-selected,
  vertical); switch = standalone binary that applies immediately (never in a multi-select list
  or behind a save step).
- Wait indication: nothing below ~200 ms; loading indicator 200 ms–5 s; determinate progress
  beyond ~5 s; one variant per process app-wide.
- Text fields: one variant (filled OR outlined) per form; always-visible label (placeholder is
  not a label); error text replaces supporting text.
- Cards never scroll internally or host swipeable content. Chips represent forking paths, not
  task progression; input chips carry a remove icon.
- No superseded baseline components: segmented buttons, baseline bottom app bar, small FAB.

## 5. Iconography

- Material Symbols only, exactly one style family per app (default `outlined`); never mix
  families or weights. No `material-icons-core`/`material-icons-extended`.
- Fill axis is the selected-state signal (filled = active); weight bump is the fallback when
  no filled variant exists — selection is never carried by color alone.
- Icons are checked-in vector drawables under `res/drawable/ic_<name>.xml`, accessed through
  one central registry object in the design system; tinted via `LocalContentColor`/theme roles.
- Directional icons use auto-mirrored forms (`Icons.AutoMirrored.*`); media/clock icons do not
  mirror. Standard icon 24dp on a 48dp touch target.

## 6. Localization

- Every user-visible string in `strings.xml`; `HardcodedText` is error-level. English source
  in `values/`, German in `values-de/`, both complete (`MissingTranslation` error-level).
- Positional placeholders (`%1$s`) everywhere; `<plurals>` with an `other` case and the number
  in the text for counts; never concatenate translated fragments.
- Read strings via `stringResource`/`pluralStringResource` in composables; never concatenate
  in a composable or cache locale-dependent values in `remember` without a config key.
- RTL end-to-end: `supportsRtl="true"`, start/end (never left/right). Dates/numbers via
  `java.time`/`NumberFormat`, not hand-built patterns.
- `localeFilters += listOf("en", "de")` and `generateLocaleConfig = true`; in-app picker via
  `AppCompatDelegate.setApplicationLocales()`. Pseudolocales (`en-XA`, `ar-XB`) in debug.

## 7. Accessibility baseline

- 48dp minimum touch targets; text/line heights in `sp`; layouts survive 200% non-linear font
  scaling without clipping critical UI.
- Every functional icon/control has an action-phrased `contentDescription`; decorative
  elements pass `null`. Stateful icon-only controls describe their state.
- Icon-to-container contrast ≥ 3:1; color is never the only carrier of meaning.

## 8. Research-backed usability

- Error states: visible near the source, specific, constructive (next step), no blame/codes as
  primary text, user input preserved for correction.
- Empty states are onboarding moments with a direct call-to-action — never a dead end.
- Forms: correct keyboard type per field, autofill hints, validation on field exit (not per
  keystroke), input preserved on error, minimize typing — the mechanism behind these four is
  section 10, which is normative wherever it is more specific.
- No function reachable only by a custom gesture; swipe actions have visible alternatives and
  undo for destructive ones. No forced tutorial carousels.
- Permissions requested in context with a prior rationale, never up front cold.
- Prefer undo (snackbar) over confirmation dialogs for frequent reversible actions.

## 9. Lists and continuous scrolling

- Any data-driven, unbounded, or longer-than-viewport collection uses a lazy container; a short
  fixed set uses a plain `Column`. Never nest a same-direction scroll container with an
  unbounded inner size — a `LazyColumn` inside `Modifier.verticalScroll` throws, because the
  inner container is offered infinite height. With a fixed inner size it is legal but is a
  smell (two scroll surfaces competing for one gesture). Headers and footers go *inside* the
  lazy container via its `item`/`items` DSL.
- One logical entry per `item {}`. Several entries in one item break per-item reuse and
  desynchronize the indices `scrollToItem` addresses.
- Every item carries a stable, `Bundle`-compatible domain `key` (never the index), and any
  collection with more than one item shape supplies `contentType`. `Modifier.animateItem` is
  only correct with stable keys.
- No item may measure to zero in the scroll direction: an asynchronously filled item (a network
  image) declares its size *before* its content arrives, and that size equals the loaded size —
  otherwise the container composes every item at once and the content shifts on arrival.
- No sorting, filtering, grouping, or formatting inside an item body or a lazy scope without
  `remember`; scroll-derived booleans go through `derivedStateOf`, scroll side effects through
  `snapshotFlow`, scroll-driven visual offsets through lambda-taking modifiers.
- Item composables receive skippable parameters (`ImmutableList` or an `@Immutable` state type);
  a collection re-created by `map`/`filter` on every emission recomposes regardless of strong
  skipping. Never add `List` to the compiler's stability configuration.
- Paged collections use Paging 3 with a database source of truth behind any network source and
  `cachedIn`; a page arriving never changes the offset of content already on screen, and
  `refresh`/`append`/`prepend` are handled as distinct states with retry.
- The scroll state is hoisted and never composed against an empty item list on the first frame
  when a restored position exists — that is what makes a list jump to the top after process
  death. Never compensate with a `scrollToItem` afterwards.
- A large collection offers search/filter/sort, a recognizable end, and no content stranded
  behind an endless scroll. Collection semantics reach the screen reader, and a non-scroll path
  exists to anything scroll-driven loading would otherwise gate.
- Item images load through a cache-backed loader at a declared target size with a placeholder of
  that size — never a full-resolution decode per row.

## 10. User input and validation

- Every check belongs to one of four stages, and none answers a later stage's question: shaping
  (what the field accepts while typing, no error message), field check (is this one value
  well-formed), form check (are these values consistent with each other), server decision
  (everything the business owns — uniqueness, eligibility, quota, price). A client check is
  assistance; the server's answer wins even when the client thought the input was fine.
- Input lives in a state-based text field (`TextFieldState` / `rememberTextFieldState`) held in
  the screen's state holder, with a per-field **touched** flag, error, and submission state. The
  touched flag is what makes the timing rules below implementable — without it they cannot hold.
- Raw text, normalised value, and transmitted value stay distinguishable; the field the user
  edits never shows the transmitted form. `InputTransformation` enforces limits the user can
  perceive; `OutputTransformation` formats the display without entering the stored value.
- Every field declares `KeyboardType`, `KeyboardCapitalization`, autocorrect (off for
  identifiers and codes), and an `ImeAction` that actually moves focus or submits.
- Numbers, dates, and times parse locale-aware (`NumberFormat`, `java.time`) — never `toInt()` /
  `toDouble()` on user text. A comma decimal separator is a formatting question, not a rejection.
- No error appears before the field is first left; a field of known fixed length may act on
  completion (advance focus, submit an OTP) but still shows no early error. Every shown error
  clears on the keystroke that makes the value valid.
- Submission validates the whole form and moves focus to the first field in error. A disabled
  submit control is never the only statement of what is wrong.
- Every error is text next to its field, carries a correction suggestion where one is known, and
  is exposed via `Modifier.semantics { error(...) }`; form-level status goes through
  `liveRegion`, never through the deprecated `announceForAccessibility()`.
- Server rejections land on the field the contract identifies; the raw server string is never the
  primary message.
- Nothing the user typed is lost by a failed submission, a rejection, a rotation, or process
  death (`rememberSaveable` / `SavedStateHandle`), and nothing oversized goes into saved
  instance state.
- Credentials go through Credential Manager, autofill content types are set on fillable fields,
  secrets use `SecureTextField` without autocorrect or suggestions, and pasting into a credential
  field is never blocked.
