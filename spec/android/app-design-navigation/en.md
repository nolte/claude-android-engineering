# App Design and Navigation

Status: draft

## Context

This spec is the usability-first foundation for the Compose-UI skill (REQ-13: build screens with UX guidance applied at authoring time) and the UX-audit skill (REQ-14): it defines the foundational design language and the in-app navigation behavior that make an app usable, so generated screens and audit findings share one authoritative baseline.

The content is distilled from a research pass (August 2026) over three source classes: official design guidance (Material 3 including the 2025 M3 Expressive evolution, developer.android.com design/adaptive/back-navigation/insets/animation docs, Android 15/16 behavior changes), official navigation architecture (Navigation 3 — stable since November 2025, with Navigation 2 officially in maintenance mode — plus the Now in Android reference implementation), and research-backed mobile usability evidence (Nielsen Norman Group studies, Hoober's thumb-zone field research, Baymard form research, Google Play core app quality requirements).

Boundaries against sibling specs: `spec/android/ui-components/` owns component-level usage rules; `spec/android/screen-formats/` owns window size classes and adaptive pane layouts (this spec only fixes which navigation UI belongs to which context); `spec/android/test-automation/` owns navigation testing; the structural imprint (route/content split, `designsystem` module) stays in `spec/android/project-structure/` §E.

Readers: authors of this repo's Android skills and reviewers judging whether a generated or audited app's design and navigation are conformant.

## Goals

- Fix the Material 3 foundation (color roles, typography roles, shape tokens, surfaces) so every generated screen is theme-correct, dark-mode-correct, and accessibility-correct by construction
- Fix the navigation architecture (Navigation 3, single activity, back stack as state) and the navigation UI choice rules so apps navigate the way users expect
- Make back navigation, deep links, and state preservation behave per platform contract — including predictive back and the Android 16 changes
- Encode research-backed usability rules (thumb zones, visible navigation, error/empty/forms/onboarding patterns) as testable requirements, not taste

## Non-Goals

- Component-level usage and consistency governance — owned by `spec/android/ui-components/`
- Window size classes, canonical layouts, and large-screen quality tiers — owned by `spec/android/screen-formats/` (navigation *choice* per context lives here; the adaptive machinery there)
- Concrete brand identity (palette seed colors, fonts, logo) — per-app decisions on top of the token system
- Performance measurement and latency budgets — `spec/android/perceived-performance/`; this spec only fixes feedback semantics (which UI state at which wait class)
- Play-Store listing assets — release is out of scope for this repository

## Requirements

### A. Design foundations (Material 3)

- **MUST** express every color through Material color roles (`primary`/`onPrimary`, `surface`/`onSurface`, container variants) resolved from `MaterialTheme` — never hard-coded values or raw tonal-palette values; hard-coding breaks dark theme, contrast guarantees, and dynamic color
- **MUST** pair content with its `on-*` role (content on `primaryContainer` uses `onPrimaryContainer`); only these pairings carry the contrast guarantee (4.5:1 small text, 3:1 large text/graphics)
- **MUST** use the Material typography roles (display/headline/title/body/label scale) and shape tokens instead of ad-hoc sizes and radii; depth comes from tonal surface-container roles, not shadow overlays
- **SHOULD** support dynamic color (Android 12+) with a static brand scheme as fallback: the theme composable selects `dynamicLightColorScheme(context)`/`dynamicDarkColorScheme(context)` behind a `Build.VERSION_CODES.S` gate and otherwise the static light/dark `ColorScheme`, with `isSystemInDarkTheme()` as the default input to the light/dark decision [R6][R33]; **SHOULD** ship a proper dark theme (own dark `ColorScheme`, user choice light/dark/system with system as default); **MUST NOT** rely on force-dark as a permanent solution
- **SHOULD** honor the user's system contrast setting (Android 14+): dynamic schemes reflect it without app code, so a static brand scheme **SHOULD** ship medium- and high-contrast variants (Material Theme Builder exports them) selected from `UiModeManager.getContrast()` (API 34) — an app that renders only its own colors is what that API exists for [R34][R35]
- **SHOULD** build on the stable Material 3 Compose line and plan adoption of M3 Expressive (the declared design direction: spring-based motion, expanded shapes, emphasized type); Expressive-only APIs remain **MAY** while they sit in alpha
- **MUST** handle edge-to-edge correctly: enforced from targetSdk 35 (no opt-out from Android 16) — insets via `Scaffold`/Material components or explicit `WindowInsets` handling; no touch targets inside system-gesture zones
- **MUST** treat the on-screen keyboard as an inset, not an afterthought: any screen with text input applies `WindowInsets.ime` — `Modifier.imePadding()` on the form container, or the scaffold's `contentWindowInsets` extended with the IME (its default covers system bars only) — so the focused field and the submit control stay above the keyboard; scrolling forms add `Modifier.imeNestedScroll()` and draw the last field above the system bars with a `Spacer(Modifier.windowInsetsBottomHeight(WindowInsets.systemBars))` rather than content padding; a field that a layout cannot bring on screen by itself is scrolled into view with `BringIntoViewRequester` on focus; and the activity keeps `android:windowSoftInputMode="adjustResize"` under edge-to-edge for backward-compatible IME insets — `adjustPan` and a permanently open keyboard hiding the primary action are defects [R39][R40][R41][R42]. The validation-side rules (focus movement to the first error, IME actions) live in `spec/android/user-input-validation/` §C/§D
- **MUST** use the SplashScreen API for launch (system splash since Android 12); **MUST NOT** ship custom splash activities; branding images are advised against
- **MUST** meet the accessibility design baseline everywhere: 48dp minimum touch targets, text and line heights in `sp` with layouts that survive 200 % non-linear font scaling, content descriptions for non-text elements (`null` for decorative), and never color as the only carrier of meaning
- **SHOULD** lay out on the 8dp grid (16dp margins compact, 24dp medium+), and use Material motion patterns (container transform, shared axis, fade-through) for navigation transitions — in Navigation 3 through `NavDisplay`'s `transitionSpec`/`popTransitionSpec`/`predictivePopTransitionSpec` (app-wide) and the per-entry `NavDisplay.TransitionKey`/`PopTransitionKey`/`PredictivePopTransitionKey` metadata (per destination), and for hero/container transforms through `SharedTransitionLayout` with `Modifier.sharedElement`/`sharedBounds` (stable since compose-animation 1.10) with the `SharedTransitionScope` handed to `NavDisplay` [R36][R37]; the M3 Expressive `MotionScheme` (`MaterialTheme.motionScheme`, `MotionScheme.standard()`/`expressive()`) is the theme-level source of animation specs once the app adopts the Expressive theme and remains **MAY** while it sits in the 1.5 alphas [R4]
- **SHOULD** give confirmations and thresholds a haptic signal through `LocalHapticFeedback.current.performHapticFeedback(HapticFeedbackType.…)` — `Confirm`/`Reject` for the outcome of an interaction, `SegmentTick`/`SegmentFrequentTick` for discrete steps, `GestureThresholdActivate` for pull-to-refresh-class thresholds, `LongPress` on long-press actions — and **MUST NOT** vibrate on every tap or as decoration: haptics mark meaning, and the platform constants they map to carry their own fallback where a device lacks the effect [R38]

### B. Navigation architecture

- **MUST** build new apps single-activity (strongly recommended officially); additional activities are deliberate exceptions (interop, separate entry points), not peers
- **MUST** use Navigation 3 for new multi-screen Compose apps — stable since November 2025 [R13][R15a] and named in the official architecture recommendations [R16]; Navigation 2 is in maintenance mode [R15] and its use in new code needs a recorded rationale
- **MUST** treat the back stack as app-owned state: keys implement `NavKey` and are `@Serializable`, held in `rememberNavBackStack` (survives configuration change *and* process death); rendering goes through `NavDisplay` with an `entryProvider`
- **MUST** scope screen ViewModels to navigation entries via the official decorators (`rememberSaveableStateHolderNavEntryDecorator` + `rememberViewModelStoreNavEntryDecorator`); no ViewModels in reusable components (per `spec/android/project-structure/` §E)
- **MUST** pass minimal navigation arguments — IDs, never objects; the destination loads its own data (single source of truth)
- **MUST**, in modularized apps, keep navigation keys separable from feature implementations per the official Navigation 3 modularization pattern: where `spec/android/project-structure/` §C sanctions the `:feature:x:api`/`:impl` split (large projects — it stays prohibited for solo/small projects there), keys live in `:api` and entry builders in `:impl`; without the split, the feature module itself exposes keys and entry builders following the same pattern
- **MUST** give each top-level destination its own back stack (tab switch preserves per-tab state; reselecting a tab clears its stack to root) — Navigation 3 has no built-in mechanism, so this is explicit app state per the official multiple-back-stacks recipe
- **MUST NOT** navigate during composition; navigation runs in callbacks/effects, screens expose event lambdas and never receive a navigation controller; rapid double-taps are guarded (`dropUnlessResumed`-style)
- **SHOULD** centralize conditional flows (auth, one-time onboarding) in the back-stack holder per the official conditional-navigation pattern — never as ad-hoc checks inside screens
- **MUST** express "how many entries render at once" through Navigation 3 `SceneStrategy`s rather than through parallel UI state: dialogs and bottom-sheet destinations are back-stack entries rendered by `DialogSceneStrategy` (metadata `DialogSceneStrategy.dialog()`, listed before every non-overlay strategy), and two-pane content uses the list-detail/supporting-pane scene strategies whose window-size behavior `spec/android/screen-formats/` §C owns; a custom `SceneStrategy` implements `calculateScene` and its `Scene` implements `equals`/`hashCode` [R43][R44]. `adaptive-navigation3` is still an alpha artifact, so its adoption is the recorded decision `spec/android/screen-formats/` §Open Questions tracks

### C. Navigation UI choice

- **MUST** expose 3–5 top-level destinations in a navigation bar on compact windows; more than five is prohibited (touch-target crowding); larger windows switch per `spec/android/screen-formats/` (rail from medium; expanded rail beyond)
- **MUST NOT** use a bottom navigation bar on large windows, and **SHOULD NOT** design new navigation around the modal drawer — with M3 Expressive the drawer is deprecated in favor of the expanded navigation rail
- **MUST** show icon *and* label on navigation items, and mark the current destination visibly (selected state, filled-icon convention per `spec/android/iconography/`): research shows visible navigation beats hidden — in NN/g's quantitative study, hidden navigation dropped content discoverability by more than 20 % and slowed mobile tasks by ~15 % [R24]
- **MUST** place primary actions in the thumb-friendly bottom zone (bottom bar, FAB area, bottom sheets); top-app-bar corners are the hardest reach zone and carry only secondary/rare actions — Hoober: 75 % of interactions are thumb-driven, and touch accuracy degrades toward corners
- **SHOULD** treat search as a complement to browsing, not a replacement; one FAB maximum per screen for the single most important action (detail rules in `spec/android/ui-components/`)

### D. Back navigation and state

- **MUST** support predictive back: `android:enableOnBackInvokedCallback="true"`, no `onBackPressed()`/`KEYCODE_BACK` interception — from targetSdk 36 on Android 16+ the predictive system animations are on by default and `onBackPressed()` is not called nor `KEYCODE_BACK` dispatched [R8]; the platform still allows a *temporary* opt-out via `android:enableOnBackInvokedCallback="false"`, and generated apps **MUST NOT** use it (a migration crutch, not a design choice); Compose interception uses `BackHandler`/`PredictiveBackHandler`, and callbacks are enabled only while their condition holds (a permanently enabled interceptor kills the back-to-home animation)
- **MUST** keep Up and Back identical inside the app's task (Up never exits the app); confirm-exit prompts exist only for genuinely unsaved data
- **MUST** preserve state per Play core app quality: return from recents, lock/unlock, and rotation land the user exactly where they were (inputs, scroll positions, media positions); process-death restoration goes through serializable navigation keys plus `rememberSaveable`/`SavedStateHandle`
- **MUST NOT** restrict orientation or resizability — ignored from targetSdk 36 on large screens (exact breakpoint and exceptions per `spec/android/screen-formats/` §B; the opt-out dies with targetSdk 37)

### E. Deep links

- **SHOULD** use verified App Links (`android:autoVerify` + `assetlinks.json`) for own-domain content; custom schemes only for internal/partner flows
- **MUST** take deep-link users directly to content — no interstitials, no forced login before the content is visible (defer auth to the first protected interaction)
- **MUST**, when a deep link lands mid-hierarchy, build a synthetic back stack that mirrors organic navigation; Navigation 3's deep-link APIs sit in the 1.2 alpha line as of retrieval date [R15a] — until they stabilize, intent parsing to a typed `NavKey` follows the official recipe pattern
- Deep-link testing commands are owned by `spec/android/adb-workflows/` §D

### F. Usability rules (research-backed)

- **MUST** write error states per the error-message rules: visible near the source, specific, constructive (what to do next), no blame or codes as the primary text, and user input is always preserved for correction
- **SHOULD** prefer undo (snackbar action) over confirmation dialogs for frequent reversible actions; confirmations are reserved for serious irreversible consequences
- **MUST** design empty states as onboarding moments: state what belongs here plus a direct call-to-action — never a dead end
- **MUST**, in forms: correct keyboard types per field, autofill hints, validation on field exit (never while typing), error summary preserved with input; minimize typing (research: perceived field count drives abandonment)
- **MUST NOT** make any function reachable only through a custom gesture; swipe actions are accelerators with visible alternatives and undo for destructive ones; no app gestures in system edge-gesture zones (`systemGestureExclusionRects` only where unavoidable, ≤ 200dp per edge)
- **MUST NOT** ship forced tutorial carousels — research shows no task-success benefit and worse perceived difficulty; onboarding is contextual (first contact with a feature), and the only justified upfront step is functional customization
- **MUST** request permissions in context with a prior rationale — the NN/g article cites Tan et al. (2014): users were 12 % more likely to grant a permission when given a reason, and the best-worded rationale produced an 81 % lift in grants over the worst-worded one — a single-study result, attributed as such [R28]
- **SHOULD** apply the response-time feedback semantics: instant feedback on every tap; no indicator below ~200 ms; loading indication for short indeterminate waits; progress indication with cancel beyond ~10 s (measurement and budgets belong to `spec/android/perceived-performance/`)
- **SHOULD** apply progressive disclosure: core options first, advanced behind an explicit step; limit simultaneous choices (choice overload); front-load key information for scanning

## Acceptance Criteria

The criteria below are a deliberate representative rollup of §A–§F, not a 1:1 mapping; every requirement bullet above is normative on its own.

- [ ] No generated screen contains a hard-coded color, text size, or corner radius; all styling resolves through `MaterialTheme` roles and tokens
- [ ] The app builds and renders correctly in dark theme and at 200 % font scale without clipped or truncated critical UI
- [ ] Edge-to-edge is handled: no content under system bars without insets handling, no interactive element in gesture zones; every screen with text input keeps the focused field and its submit control visible above the open keyboard, and the activity declares `adjustResize`
- [ ] A new multi-screen app uses Navigation 3 with serializable `NavKey`s and `rememberNavBackStack`; no `NavController` is passed into screen composables
- [ ] Navigation arguments are IDs or simple values only; no `@Serializable` payload object carries entity data
- [ ] Dialog and sheet destinations are back-stack entries rendered through a `SceneStrategy`; no dialog visibility lives in ad-hoc boolean state beside the back stack
- [ ] Top-level navigation has 3–5 destinations with icons and labels, a visible selected state, and per-destination back stacks that survive tab switches
- [ ] Predictive back works end-to-end: no `onBackPressed` overrides, no `enableOnBackInvokedCallback="false"` in the manifest, back callbacks are condition-enabled, and the system back-preview animation plays
- [ ] State preservation passes the Play-quality checks: rotation, recents return, and process death restore the visible state (verified per `spec/android/test-automation/` §D patterns)
- [ ] Deep links open content directly and produce a realistic synthetic back stack
- [ ] Every error state names the problem and the next step and preserves user input; every empty state carries a call-to-action
- [ ] Form fields declare keyboard types and autofill hints; validation fires on exit, not per keystroke
- [ ] No function is gesture-only; no forced tutorial carousel exists; permission requests appear in context with a rationale
- [ ] Primary actions sit in the bottom interaction zone on compact windows; the top app bar carries only secondary actions
- [ ] No orientation or resizability restriction exists in the manifest or code

## Open Questions

All five questions are parking-lot class: the requirements above state a working default for each, so implementation proceeds without an answer.

- M3 Expressive adoption timing: flip generated apps to `MaterialExpressiveTheme` once the Compose APIs graduate from the 1.5 alphas, or stay on baseline M3 until the system rollout broadens?
- Navigation 3 deep links: adopt the 1.2 `DeepLinkMatcher` APIs as soon as they stabilize, or keep the recipe-based parsing pattern?
- Drawer deprecation: any legitimate remaining drawer use case for this portfolio's apps, or ban it outright in generated code?
- Should the Compose-UI skill scaffold a standard conditional-navigation (auth/onboarding) template, or leave that per app?
- Fixed-length-field error timing: §F forbids raising a validation error while the user is still typing, without exception; `spec/android/user-input-validation/` §D defers here the question whether a field of known fixed length (one-time code, postal code) may show an error on *completion* of that length, since the research it cites treats that as the one case where "still typing" has a defined end. Working default until decided: no carve-out — completion may advance focus or submit, but the error waits for field exit (the stricter reading both specs already apply)

## References

All sources retrieved 2026-08-11; R8, R28, and R33–R44 retrieved or re-verified 2026-08-19. Class markers by group: R1–R23, R31–R32, and R33–R44 are primary/authoritative vendor documentation (P; R35 is the Material Components for Android theming guide); R24–R30 are research/secondary sources (S) whose quantitative findings are attributed inline as single-study results where no independent corroboration exists.

- [R1] Material 3 — apply colors / color roles: <https://m3.material.io/styles/color/advanced/apply-colors>
- [R2] Material 3 — elevation via tonal surfaces: <https://m3.material.io/styles/elevation/applying-elevation>
- [R3] M3 Expressive announcement (motion physics, shapes, component updates): <https://blog.google/products-and-platforms/platforms/android/material-3-expressive-android-wearos-launch/>
- [R4] Compose Material 3 releases (stable line vs Expressive alphas): <https://developer.android.com/jetpack/androidx/releases/compose-material3>
- [R5] Dark theme guidance: <https://developer.android.com/develop/ui/views/theming/darktheme>
- [R6] Dynamic color: <https://developer.android.com/develop/ui/views/theming/dynamic-colors>
- [R7] Android 15 behavior changes (edge-to-edge enforcement): <https://developer.android.com/about/versions/15/behavior-changes-15>
- [R8] Android 16 behavior changes (orientation/resizability ignored, edge-to-edge final): <https://developer.android.com/about/versions/16/behavior-changes-16>
- [R9] Splash screen API and design rules: <https://developer.android.com/develop/ui/views/launch/splash-screen>
- [R10] Accessibility principles and apps guide (targets, contrast, labels): <https://developer.android.com/guide/topics/ui/accessibility/apps>
- [R11] Non-linear font scaling (Android 14): <https://developer.android.com/about/versions/14/features>
- [R12] Navigation 3 — basics (back stack as state): <https://developer.android.com/guide/navigation/navigation-3/basics>
- [R13] Navigation 3 stable announcement: <https://developer.android.com/blog/posts/jetpack-navigation-3-is-stable>
- [R14] Navigation 3 — save state (serializable keys, ViewModel decorators): <https://developer.android.com/guide/navigation/navigation-3/save-state>
- [R15] Navigation releases (Nav2 maintenance mode): <https://developer.android.com/jetpack/androidx/releases/navigation>
- [R15a] Navigation 3 releases (stable line, 1.2 alpha deep links): <https://developer.android.com/jetpack/androidx/releases/navigation3>
- [R16] Architecture recommendations (single activity, Navigation 3, ViewModel scoping): <https://developer.android.com/topic/architecture/recommendations>
- [R17] Navigation principles (Up/Back, synthetic stacks): <https://developer.android.com/guide/navigation/principles>
- [R18] Pass data between destinations (minimal arguments): <https://developer.android.com/guide/navigation/use-graph/pass-data>
- [R19] Predictive back: <https://developer.android.com/guide/navigation/custom-back/predictive-back-gesture>
- [R20] App Links (verification): <https://developer.android.com/training/app-links>
- [R21] nav3-recipes (deep links, conditional navigation, multiple back stacks): <https://github.com/android/nav3-recipes>
- [R22] Material navigation-bar guidelines (3–5 destinations): <https://m3.material.io/components/navigation-bar/guidelines>
- [R23] Layout and navigation patterns (bottom-first ergonomics, no bottom bar on large screens): <https://developer.android.com/design/ui/mobile/guides/layout-and-content/layout-and-nav-patterns>
- [R24] NN/g — hamburger menus / hidden navigation study: <https://www.nngroup.com/articles/hamburger-menus/>
- [R25] Hoober — how people hold and touch phones: <https://alistapart.com/article/how-we-hold-our-gadgets/> and <https://www.uxmatters.com/mt/archives/2017/07/design-for-fingers-touch-and-people-part-3.php>
- [R26] NN/g — error message guidelines: <https://www.nngroup.com/articles/error-message-guidelines/>
- [R27] NN/g — mobile tutorials and onboarding studies: <https://www.nngroup.com/articles/mobile-tutorials/> and <https://www.nngroup.com/articles/mobile-app-onboarding/>
- [R28] NN/g — permission requests (in-context timing): <https://www.nngroup.com/articles/permission-requests/>
- [R29] NN/g — response-time limits: <https://www.nngroup.com/articles/response-times-3-important-limits/>
- [R30] Baymard — mobile form/keyboard/validation research: <https://baymard.com/blog/mobile-touch-keyboards> and <https://baymard.com/blog/inline-form-validation>
- [R31] Google Play core app quality (back, state preservation, targets, contrast): <https://developer.android.com/docs/quality-guidelines/core-app-quality>
- [R32] Gesture navigation conflicts (exclusion rects): <https://developer.android.com/develop/ui/views/touch-and-input/gestures/gesturenav>
- [R33] Material 3 in Compose — `dynamicLightColorScheme`/`dynamicDarkColorScheme`, `Build.VERSION_CODES.S` gate, `isSystemInDarkTheme()`, color-role pairing (P): <https://developer.android.com/develop/ui/compose/designsystems/material3>
- [R34] `UiModeManager.getContrast()` / `addContrastChangeListener` — user color contrast, API 34, only needed outside the Material rendering pipeline (P): <https://developer.android.com/reference/android/app/UiModeManager>
- [R35] Material Components for Android — color contrast control: automatic with dynamic color on Android 14+, medium/high-contrast overlays for static themes (P): <https://github.com/material-components/material-components-android/blob/master/docs/theming/Color.md>
- [R36] Navigation 3 — animate between destinations: `transitionSpec`/`popTransitionSpec`/`predictivePopTransitionSpec`, per-entry transition metadata keys, `SharedTransitionLayout` with `NavDisplay` (P): <https://developer.android.com/guide/navigation/navigation-3/animate-destinations>
- [R37] Compose shared element transitions (`SharedTransitionLayout`, `sharedElement`, `sharedBounds`; stable per compose-animation 1.10.0-alpha05 notes) (P): <https://developer.android.com/develop/ui/compose/animation/shared-elements> and <https://developer.android.com/jetpack/androidx/releases/compose-animation>
- [R38] `HapticFeedbackType` constants (`Confirm`, `Reject`, `SegmentTick`, `GestureThresholdActivate`, `LongPress`, …) and `LocalHapticFeedback` (P): <https://developer.android.com/reference/kotlin/androidx/compose/ui/hapticfeedback/HapticFeedbackType>; haptic-feedback semantics and constant fallback behavior: <https://developer.android.com/develop/ui/views/haptics/haptic-feedback>
- [R39] Compose window insets — `WindowInsets.ime`, `imePadding()`, safe-drawing/gesture insets, edge-to-edge enforcement from targetSdk 35 (P): <https://developer.android.com/develop/ui/compose/layouts/insets>
- [R40] Compose insets in UI — `imePadding()` consumption, `Spacer` with `windowInsetsBottomHeight` for the last text field (P): <https://developer.android.com/develop/ui/compose/system/insets-ui>
- [R41] Keyboard IME animations in Compose — `imeNestedScroll()`, `imePadding()` on scrolling containers and bottom-anchored controls (P): <https://developer.android.com/develop/ui/compose/system/keyboard-animations>
- [R42] Software keyboard control — `windowSoftInputMode="adjustResize"` for backward-compatible IME insets, edge-to-edge prerequisite, `WindowInsetsAnimationCompat` (API 30+) (P): <https://developer.android.com/develop/ui/views/layout/sw-keyboard>; `BringIntoViewRequester` reference (foundation, stable since 1.1.0): <https://developer.android.com/reference/kotlin/androidx/compose/foundation/relocation/BringIntoViewRequester>
- [R43] Navigation 3 — custom layouts with `Scene`/`SceneStrategy`, list-detail scenes, `adaptive-navigation3` (P): <https://developer.android.com/guide/navigation/navigation-3/scenes>
- [R44] `DialogSceneStrategy` reference (`navigation3-ui`, dialog metadata, ordering before non-overlay strategies) (P): <https://developer.android.com/reference/androidx/navigation3/ui/DialogSceneStrategy>
