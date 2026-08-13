# Screen Formats

Status: draft

## Context

Apps built with this repository's skills must be usable on smartphones **and** tablets (operator requirement). It grounds the Compose-UI skill (REQ-13) and the UX-audit skill's responsiveness scope (REQ-14). This spec is the authoritative definition of the screen formats an app supports and the adaptive machinery behind them: window size classes, canonical layouts, the Google Play adaptive-quality tiers, and the Android 16 reality that orientation and resizability restrictions no longer exist on large screens.

The content is distilled from a research pass (August 2026) over the official adaptive documentation (developer.android.com/develop/adaptive-apps — note Google's 2025 vocabulary shift from "large screen app quality" to **adaptive app quality**), the androidx.window and material3-adaptive release lines, Google Play's tier system, and the Now in Android reference implementation (fully migrated to `NavigationSuiteScaffold` + Navigation-3 `ListDetailSceneStrategy` [R17]).

The load-bearing principle: decisions key on the **window**, never the device. Size classes are window properties that change with rotation, folding, split-screen, and desktop windows — "is tablet" logic is wrong by construction.

Boundaries: navigation-UI choice rules (bar vs rail vs expanded rail) live in `spec/android/app-design-navigation/` §C; density/`dp`/`sp` discipline and font scaling are shared with that spec's §A; testing tools are owned by `spec/android/test-automation/`.

Readers: authors of this repo's Android skills and reviewers judging whether a generated or audited app's adaptivity is conformant.

## Goals

- Fix the supported-format contract: one app, phone and tablet, driven by window size classes with defined behavior per class
- Make the canonical layouts (list-detail, supporting pane, feed) the standard answer to "what changes on a bigger window"
- Meet Google Play's adaptive-quality Tier 3 unconditionally and target Tier 2, so tablet users get a first-class app and Play ranking/warnings work in the app's favor
- Be ready for the Android 16 windowing reality: no orientation locks, resizable everywhere, multi-window as a normal state

## Non-Goals

- Navigation component choice per size class — `spec/android/app-design-navigation/` §C owns it (this spec provides the class definitions it keys on)
- Foldable posture-specific experiences (tabletop/book modes) and desktop Tier-1 differentiation — named as optional extensions, not required scope
- Wear OS, TV, Auto — out of scope for this portfolio's apps
- Performance characteristics of large screens — `spec/android/perceived-performance/`

## Requirements

### A. Window size classes

- **MUST** derive top-level layout decisions from window size classes via `currentWindowAdaptiveInfo().windowSizeClass` (material3-adaptive) on the `androidx.window.core.layout.WindowSizeClass` API; the width breakpoints are compact < 600dp ≤ medium < 840dp ≤ expanded < 1200dp ≤ large < 1600dp ≤ extra-large, heights compact < 480dp ≤ medium < 900dp ≤ expanded [R1][R12]
- **MUST NOT** use deprecated size-class APIs in new code (`WindowWidthSizeClass`/`WindowHeightSizeClass`, `material3-window-size-class`'s `calculateWindowSizeClass`) and **MUST NOT** branch on device type ("isTablet"), physical screen size, or pixel dimensions
- **MUST** treat size classes as dynamic window properties: they change at runtime (rotation, fold, split-screen, freeform windows), and every class transition preserves UI state
- **SHOULD** key primarily on width (officially "usually more important"), design the expanded layout first and optimize downward; the large/extra-large opt-in (`supportLargeAndXLargeWidth`) is a **MAY** until desktop-class windows matter
- **SHOULD** use size classes only for high-level structure (pane count, navigation type); component-local adaptation reads its own constraints (`BoxWithConstraints`) instead of the global class

### B. Behavior per size class

- **MUST** switch content structure at the expanded boundary: compact/medium show one pane; expanded and wider show two panes where the content has a list-detail or main-supporting relationship — a deliberately single-pane responsive layout (feed) is the documented exception
- **MUST** replace or show/hide layout components across classes rather than stretching a phone layout ("adaptive apps replace layout components", the official anti-stretching rule); content, business logic, and navigation destinations stay identical
- **MUST**, on large windows, stop secondary UI from going full-width: dialogs, bottom sheets, buttons, and text fields get maximum widths; context menus attach to their element (component rules in `spec/android/ui-components/`)
- **MUST NOT** declare orientation or resizability restrictions (`screenOrientation`, `resizableActivity`, aspect-ratio limits): ignored on ≥ sw600dp displays from targetSdk 36 (games excepted), with the temporary opt-out removed at targetSdk 37 [R7][R8] — layouts, camera previews, and animations must survive any orientation and any resize
- **MUST** keep the app fully functional in multi-window: no letterboxing/compatibility mode, correct behavior without focus (multi-resume — playback continues, exclusive resources like camera are released and reacquired via `onTopResumedActivityChanged`), and fast repeated resizes without leaks or state loss

### C. Canonical layouts

- **MUST** implement collection-plus-detail content as **list-detail** (`NavigableListDetailPaneScaffold`, or the Navigation-3 `ListDetailSceneStrategy` when the app uses Nav 3 per `spec/android/app-design-navigation/` §B): two panes on expanded, single pane below, selection state preserved across class changes (navigator type parameter is `Parcelable`)
- **MUST** keep two-pane back navigation on the recommended default `PopUntilScaffoldValueChange`; in single-pane mode back closes the detail and returns to the list
- **SHOULD** implement main-content-plus-context as **supporting pane** (~70/30 on expanded, stacked or sheet-based below) and collections of equivalent items as **feed** (`LazyVerticalGrid(GridCells.Adaptive(minSize = …))`, which degrades to a single column on compact)
- **MAY** adopt pane expansion (drag-to-resize) and the reflow/levitate strategies from material3-adaptive 1.1/1.2 where they add value

### D. Play adaptive app quality

- **MUST** meet **Tier 3 ("adaptive ready")** unconditionally — it is the floor below which Play down-ranks the app on tablets and shows a quality warning: full-window rendering without letterboxing, every configuration change and combination (rotate + resize + fold) survives with state intact, full function in split-screen, multi-resume correctness, camera previews correct in every orientation and fold state, and basic keyboard, mouse/trackpad, and stylus input [R5][R6]
- **SHOULD** meet **Tier 2 ("adaptive optimized")** — the target level for this portfolio: size-class-driven adaptive layouts, no full-width secondary UI, 48dp touch targets, focus states for interactive elements, keyboard navigation through main flows plus standard shortcuts (copy/paste/undo, Esc, Enter, Space), right-click context menus, hover states, and content zoom [R6]
- **MAY** pursue **Tier 1 ("adaptive differentiated")** features (foldable postures, multi-instance, drag-and-drop, stylus optimization, desktop windowing polish) per app where they differentiate
- **MUST** verify against the official reference matrix: foldable 841×701dp, 8" tablet 1024×640dp, 10.5" tablet 1280×800dp, 13" 1600×900dp [R15] (execution via `spec/android/test-automation/` §D — `DeviceConfigurationOverride.ForcedSize`, Robolectric qualifiers, resizable emulator, `@PreviewScreenSizes`)

### E. Foldables and desktop windowing (bounded scope)

- **MUST** treat fold/unfold as a configuration change that preserves state (covered by Tier 3); apps that implement only size classes correctly are acceptable on foldables — posture support is officially optional differentiation
- **MUST**, when a `FoldingFeature` reports `isSeparating`, keep critical UI off the hinge (the canonical pane scaffolds do this automatically — one more reason to use them)
- **SHOULD** handle the desktop-windowing chrome where relevant: caption-bar insets (`WindowInsets.captionBar`); freeform windows resize apps regardless of any legacy restriction
- **MAY** implement tabletop/book posture layouts, rear-display experiences, and multi-instance support as Tier-1 work

### F. Density and resources

- **MUST** express all layout dimensions in `dp` and text in `sp` (never pixels); vector drawables are the default asset form, bitmap density buckets only for photographic content (asset rules in `spec/android/iconography/`)
- **SHOULD** remember that tablets often ship lower densities than flagship phones — dp-based size classes, not resolution, are why a WQHD tablet gets the expanded layout

## Acceptance Criteria

The criteria below are a deliberate representative rollup of §A–§F, not a 1:1 mapping; every requirement bullet above is normative on its own.

- [ ] The app renders full-window on every reference-matrix size with no letterboxing and no compatibility mode
- [ ] Top-level layout branches only on `WindowSizeClass` values; no code path inspects device type, physical size, or deprecated size-class APIs
- [ ] List-detail content shows two panes on expanded and one below, with selection preserved across the boundary and correct two-pane back behavior
- [ ] The manifest and code contain no orientation, aspect-ratio, or resizability restrictions
- [ ] Rotation, fold/unfold, split-screen entry/exit, and window resizes preserve visible state (inputs, scroll, selection, media position)
- [ ] The app remains fully usable in split-screen at every supported size, and background/unfocused behavior is correct (playback continues, camera released)
- [ ] On large windows no dialog, sheet, button, or text field spans the full width, and grids widen instead of stretching a single column
- [ ] Keyboard navigation reaches the main flows; Tier-2 shortcuts, hover states, and right-click menus work where the app targets Tier 2
- [ ] Adaptive layouts are verified across the reference matrix via the test-automation §D tooling (previews, forced-size tests, screenshot tests where present)
- [ ] All dimensions are dp/sp-based; no pixel literals in layout code
- [ ] When a separating fold is reported, no critical UI sits on the hinge

## Open Questions

All four questions are parking-lot class: the requirements above state a working default for each (incremental Tier-2 input, L/XL opt-in as MAY, postures optional, `NavigableListDetailPaneScaffold` as the stable path).

- Tier-2 input completeness (full shortcut set, content zoom) for the *first* generated app version: scaffold from day one or staged after the phone experience stabilizes?
- Large/extra-large opt-in: adopt now for future desktop windowing, or defer until a real target exists?
- Foldable postures: worth a standard optional module in the Compose-UI skill, or per-app only?
- material3-adaptive Navigation-3 integration (`ListDetailSceneStrategy`) is still experimental — commit now (NiA does) or gate on stabilization?

## References

All sources retrieved 2026-08-11. Class markers: (P) primary/authoritative vendor documentation, (S) secondary. Platform-behavior facts (breakpoints, targetSdk gates, quality tiers) cite the authoritative primary source per the portfolio triangulation convention; R16–R17 are corroborating context.

- [R1] Window size classes (breakpoints, API, dynamics): <https://developer.android.com/develop/ui/compose/layouts/adaptive/use-window-size-classes>
- [R2] Adaptive layouts overview (replace-don't-stretch): <https://developer.android.com/develop/ui/compose/layouts/adaptive>
- [R3] Canonical layouts: <https://developer.android.com/develop/ui/compose/layouts/adaptive/canonical-layouts>
- [R4] List-detail scaffolds and back behavior: <https://developer.android.com/develop/ui/compose/layouts/adaptive/list-detail>
- [R5] Adaptive app quality (tier system): <https://developer.android.com/docs/quality-guidelines/large-screen-app-quality>
- [R6] Tier 3 / Tier 2 / Tier 1 checklists: <https://developer.android.com/docs/quality-guidelines/adaptive-app-quality/tier-3> (and /tier-2, /tier-1)
- [R7] Android 16 behavior changes (orientation/resizability ignored): <https://developer.android.com/about/versions/16/behavior-changes-16>
- [R8] Orientation/aspect-ratio/resizability guidance: <https://developer.android.com/develop/ui/compose/layouts/adaptive/app-orientation-aspect-ratio-resizability>
- [R9] Multi-window support (multi-resume, resizability defaults): <https://developer.android.com/guide/topics/large-screens/multi-window-support>
- [R10] Fold-aware apps (`FoldingFeature`, postures): <https://developer.android.com/develop/ui/compose/layouts/adaptive/foldables/make-your-app-fold-aware>
- [R11] Desktop windowing support: <https://developer.android.com/develop/ui/compose/layouts/adaptive/support-desktop-windowing>
- [R12] androidx.window releases (L/XL classes, deprecations): <https://developer.android.com/jetpack/androidx/releases/window>
- [R13] material3-adaptive releases: <https://developer.android.com/jetpack/androidx/releases/compose-material3-adaptive>
- [R14] Screen densities (dp/sp, vector-first): <https://developer.android.com/training/multiscreen/screendensities>
- [R15] Testing across screens (reference devices, tools): <https://developer.android.com/training/testing/different-screens/tools>
- [R16] Play large-screen discovery changes (ranking, warnings, per-form-factor ratings; 2022 announcement, policy still in force per R5) (P): <https://android-developers.googleblog.com/2022/03/helping-users-discover-quality-apps-on.html>
- [R17] Now in Android adaptive implementation (NavigationSuiteScaffold, ListDetailSceneStrategy) (S): <https://github.com/android/nowinandroid>
