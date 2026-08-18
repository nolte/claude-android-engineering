# Authoring-time UX checklist

The rule set every generated screen is checked against, distilled from the grounding specs
under `spec/android/`: `app-design-navigation`, `ui-components`, `screen-formats`,
`iconography`, `localization`, `long-list-scrolling`, `user-input-validation`, plus
`perceived-performance` §A and `test-automation` §D/§E. This is a working digest, not a source
of truth: on any conflict the named spec wins. Apply these while writing the screen, not after.

## Table of contents

- [1. Material 3 foundations](#1-material-3-foundations) — `app-design-navigation` §A
- [2. Navigation architecture and UI](#2-navigation-architecture-and-ui) — `app-design-navigation` §B/§C/§D/§E
- [3. Adaptivity and screen formats](#3-adaptivity-and-screen-formats) — `screen-formats`
- [4. Components](#4-components) — `ui-components`
- [5. Iconography](#5-iconography) — `iconography`
- [6. Localization](#6-localization) — `localization`
- [7. Accessibility baseline](#7-accessibility-baseline) — cross-cutting
- [8. Research-backed usability](#8-research-backed-usability) — `app-design-navigation` §F
- [9. Lists and continuous scrolling](#9-lists-and-continuous-scrolling) — `long-list-scrolling`
- [10. User input and validation](#10-user-input-and-validation) — `user-input-validation`
- [11. Waits and time to full display](#11-waits-and-time-to-full-display) — `ui-components` §A, `perceived-performance` §A

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
- Top-level: 3–5 destinations in a navigation bar on compact (rail from medium, never a bottom
  bar on large windows; no new modal drawer); icon *and* label on every item; visible selected
  state (filled-icon convention). Each top-level destination owns its own back stack — tab
  switch preserves per-tab state, reselecting a tab pops it to root — as explicit app state
  (Navigation 3 has no built-in mechanism).
- Primary actions in the thumb-friendly bottom zone; the top app bar carries only
  secondary/rare actions. One FAB maximum per screen.
- Predictive back: `android:enableOnBackInvokedCallback="true"` (never set to `false` as an
  opt-out), no `onBackPressed()` interception; Compose uses `BackHandler`/
  `PredictiveBackHandler` enabled only while their condition holds. Up and Back are identical
  inside the task (Up never exits the app); confirm-exit only for genuinely unsaved data.
- State preservation: rotation, recents return, and process death land the user exactly where
  they were (serializable keys + `rememberSaveable`/`SavedStateHandle`).
- Deep links (§E): verified App Links (`android:autoVerify` + `assetlinks.json`) for own-domain
  content, custom schemes only for internal flows; the link lands directly on the content (no
  interstitial, auth deferred to the first protected interaction); a mid-hierarchy landing
  builds a synthetic back stack mirroring organic navigation — intent parsing to a typed
  `NavKey` per the official recipe until Nav 3 deep-link APIs stabilize.
- Conditional flows (auth, one-time onboarding) live in the back-stack holder, never as ad-hoc
  checks inside screens.

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
- Target Play adaptive-quality Tier 3 unconditionally, Tier 2 as the goal: keyboard navigation
  through the main flows (Tab/arrow focus order, Enter/Space activation, Esc dismisses), focus
  states visible on every interactive element, hover states, right-click context menus
  (a `DropdownMenu` anchored at the pointer position, attached to its element), standard shortcuts (copy/paste/undo).
- Foldables: fold/unfold is a configuration change that preserves state. When
  `WindowInfoTracker.windowLayoutInfo` reports a `FoldingFeature` with `isSeparating`, keep
  critical UI off the hinge — the canonical pane scaffolds do this automatically, a bespoke
  layout must read the feature. Desktop windowing: `WindowInsets.captionBar` where relevant.
- Verify against the reference matrix (841×701, 1024×640, 1280×800, 1600×900 dp) via
  `@PreviewScreenSizes` and `DeviceConfigurationOverride.ForcedSize` in the Compose test.

## 4. Components

- Button emphasis ladder: filled = the one important final action; tonal = emphasized
  secondary; outlined = medium; text = lowest/multi-option. Labels 1–3 words, single-line (no
  truncation or wrapping), at most one leading icon, never underlined (links are hyperlinked
  body text).
- Exactly one primary action (filled button or FAB, never both competing) per screen; no two
  equally-emphasized actions in a row.
- Message surface by severity: dialog for blocking decisions (≤2 actions, confirming action
  right, dismissive never disabled); snackbar for low/medium process feedback (≤1 action, no
  icon, never critical, never stacked); modal bottom sheet for long action lists; toast only
  for background context.
- Full-screen dialogs only on compact windows for multi-step subtasks; on medium+ windows a
  basic (width-capped) dialog replaces them.
- Selection controls: checkbox = multi-select in lists; radio = single (≤5, one pre-selected,
  vertical, never nested); switch = standalone binary that applies immediately (never in a
  multi-select list, for opposing options, or behind a save step).
- Wait indication: nothing below ~200 ms; loading indicator 200 ms–5 s; determinate progress
  beyond ~5 s; one variant per process app-wide (mechanics in section 11).
- Text fields: one variant (filled OR outlined) per form; always-visible label (placeholder is
  not a label); error text replaces supporting text; required fields marked and explained.
- Cards never scroll internally or host swipeable content (at most one swipe action); list rows
  keep element positions consistent, supporting text 1–3 lines. Menus show conditionally
  unavailable items disabled instead of removing them and never embed direct controls
  (switches/buttons). Chips represent forking paths, not task progression; never a single chip
  alone; input chips carry a remove icon.
- Design-system wrappers (`NiaButton` pattern) for every component whose defaults the app
  changes; configure through theme roles and `*Defaults` only.
- No superseded baseline components: segmented buttons, baseline bottom app bar, small FAB.

## 5. Iconography

- Material Symbols only, exactly one style family per app (default `outlined`); never mix
  families or weights. No `material-icons-core`/`material-icons-extended`.
- Fill axis is the selected-state signal (filled = active); weight bump is the fallback when
  no filled variant exists — selection is never carried by color alone.
- Icons are checked-in vector drawables under `res/drawable/ic_<name>.xml`, accessed through
  one central registry object in the design system; tinted via `LocalContentColor`/theme roles.
- Directional icons mirror in RTL via `android:autoMirrored="true"` on the checked-in vector
  drawable (`Icons.AutoMirrored.*` lives in the forbidden `material-icons-core` and is not an
  option); media-playback and clock icons do not mirror. Standard icon 24dp on a 48dp touch
  target; icons below 20dp always carry a text label.
- Scope note: the launcher icon (adaptive, `mipmap-anydpi-v26`, monochrome layer), notification
  small icons, shortcut, and tile icons follow `iconography` §C/§D and are **not** authored by
  this skill's screen pass; never place launcher/product-logo artwork in an in-app icon slot.

## 6. Localization

- Every user-visible string in `strings.xml`; `HardcodedText` is error-level. English source
  in `values/`, German in `values-b+de/`, both complete (`MissingTranslation` error-level).
- Positional placeholders (`%1$s`) everywhere; `<plurals>` with an `other` case and the number
  in the text for counts; never concatenate translated fragments. Non-translatable entries
  (brand names, technical tokens) carry `translatable="false"` and live only in `values/`.
  No translatable text in index-matched `<string-array>` items — arrays reference `@string`.
- Read strings via `stringResource`/`pluralStringResource` in composables; never concatenate
  in a composable or cache locale-dependent values in `remember` without a config key.
- RTL end-to-end: `supportsRtl="true"`, start/end (never left/right); `CompositionLocalProvider`
  overrides of `LayoutDirection` only for direction-fixed content. Free-direction inline data
  (addresses, phone numbers in translated sentences) wrapped with `BidiFormatter.unicodeWrap`.
- Dates/numbers via `java.time`/`NumberFormat` (prefer `android.icu.*`), not hand-built
  patterns. `Locale.ROOT` for internal keys (Turkish-i), the user locale for display casing,
  `Collator` for user-visible sorting.
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
- Prefer undo (snackbar) over confirmation dialogs for frequent reversible actions;
  confirmations only for serious irreversible consequences.
- Progressive disclosure: core options first, advanced behind an explicit step; limit
  simultaneous choices; front-load key information for scanning.

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
  `liveRegion`, never through the deprecated `announceForAccessibility()`. A form whose errors
  do not fit one screen adds an error summary *in addition to* the per-field messages.
- Server rejections land on the field the contract identifies; the raw server string is never the
  primary message — the UI state carries a closed `ErrorKind`, the composable resolves the
  localized text.
- Nothing the user typed is lost by a failed submission, a rejection, a rotation, or process
  death (`rememberSaveable` / `SavedStateHandle`), and nothing oversized goes into saved
  instance state.
- Credentials go through Credential Manager, autofill content types are set on fillable fields
  (`ContentType.NewUsername`/`ContentType.NewPassword` on registration and change-credential
  forms, `AutofillManager.commit()` where the save moment is a button), secrets use
  `SecureTextField` without autocorrect or suggestions, and pasting into a credential field is
  never blocked. Sensitive values the app copies to the clipboard carry
  `ClipDescription.EXTRA_IS_SENSITIVE`; input content is never logged (field name and reason
  only).
- Submission (§G): exactly one in-flight submission per form — the control is disabled or the
  intent ignored while pending, and the pending state is visible; values stay readable while
  pending and fully editable again on failure. A domain rejection names the field or rule and
  asks for a change; a transport failure names retry and never implies user error — the two are
  never the same message. No navigation away before the backend confirms the write (queued or
  local-first writes excepted; their pending state travels with the data). Persisted drafts are
  cleared only after confirmation; success is stated as legibly as failure and lands the user
  where the result is visible.
- Keyboard and insets: the form (or its scroll container) uses `Modifier.imePadding()` — or an
  insets-aware `Scaffold` — under edge-to-edge so the keyboard never covers a field or its
  error; the focused field scrolls into view via `BringIntoViewRequester` (or a
  `Modifier.bringIntoViewRequester` + `onFocusChanged` pair) when the IME opens.

## 11. Waits and time to full display

- Nothing is shown for the first ~200 ms of a wait; an indeterminate loading indicator appears
  after that (`LaunchedEffect` + `delay(200)` gating visibility, or `AnimatedVisibility` fed by
  the same delayed flag); a determinate indicator takes over once progress is known beyond
  ~5 s; the same variant is used for the same process app-wide; no in-place loading→determinate
  hand-off.
- Every screen signals full display: `ReportDrawnWhen { uiState is Success }` (or `ReportDrawn`
  / `ReportDrawnAfter`) placed where the content is genuinely present — never at first frame.
  A screen without the signal has no TTFD, and that absence is a finding.
- Instant feedback on every tap (state layers, pressed state) even when the result takes time.
