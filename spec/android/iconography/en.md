# Iconography

Status: draft

## Context

Icons appear on more surfaces than any other visual element: in-app UI, navigation, the launcher, notifications, shortcuts, quick-settings tiles. Each surface has its own hard rules, and inconsistency between them is immediately visible. This spec fixes the icon system for apps built with this repository's skills — one style family in-app, correct per-surface formats, and the accessibility rules that make icons usable — the foundation the Compose-UI skill (REQ-13) generates against and the UX-audit skill (REQ-14) audits.

The content is distilled from a research pass (August 2026) over the official Material Symbols documentation (Google Fonts), the Material 3 icon guidelines (designing/applying icons, rendered from the canonical pages), the platform icon surfaces (adaptive launcher icons including the Android 16 QPR2 auto-theming change and the 2025 Play policy on user icon theming, notification icons, shortcut and tile specs), the Compose icon APIs including the 2025 deprecation of the `material-icons` artifacts, and the Now in Android reference pattern (a central icons object in the design-system module).

Boundaries: component usage (icon buttons, navigation items) is owned by `spec/android/ui-components/`; color roles and theming by `spec/android/app-design-navigation/` §A; Play-Store listing assets are release scope and only touched where the launcher icon overlaps.

Readers: authors of this repo's Android skills and reviewers judging whether generated or audited icon usage is conformant.

## Goals

- One icon system in-app: Material Symbols in a single style family, consistent weight, fill used as the selected-state signal
- Correct per-surface formats: adaptive launcher icons with a monochrome layer, alpha-only notification icons, spec-conformant shortcut and tile icons
- Icons that are accessible by default: labeled when functional, silent when decorative, big enough to hit
- A maintainable pipeline: vector-first assets, a central icon registry, no deprecated icon libraries in new code

## Non-Goals

- Icon usage inside components (which button variant, badge placement) — `spec/android/ui-components/`
- Brand/product logo design — per-app creative work; this spec only constrains where logos may appear (launcher, not in-app UI slots)
- Play-Store listing graphics beyond the 512px icon's relationship to the launcher icon — release scope
- Illustration and imagery systems — icons only

## Requirements

### A. The icon system (Material Symbols)

- **MUST** use Material Symbols as the in-app icon system and commit to exactly one style family per app; generated projects default to `outlined` (the Material Symbols default) unless the app declares another, and an app never mixes families or weights within one interface (the documented anti-pattern)
- **MUST** use the fill axis as the state signal: filled variant for the active/selected state, outlined for inactive — the official navigation convention; when no filled variant exists, weight increase (semibold) is the fallback so selection is carried by more than color
- **MUST** render standard icons at 24dp on the icon grid with a minimum 48dp touch target (20dp/40dp only in dense desktop-class contexts); icons below 20dp always carry a text label
- **SHOULD** keep weight at 400 (regular) as the default and never below 200 at 24dp; grade and optical-size axes are tuning tools, not per-icon free variables
- **MUST** draw custom icons on the Material grid when the symbol set lacks a glyph: 24dp trim area, 20dp live area, 2dp stroke, 2dp corner radii (square interior corners in outlined style), no content outside the trim area — custom icons must be indistinguishable from the family in metrics

### B. Compose usage and asset pipeline

- **MUST NOT** add the `androidx.compose.material:material-icons-core/-extended` artifacts to new code — officially "no longer maintained or recommended", with significant build-time cost; existing usage is migration debt, not precedent
- **MUST** source icons as individual vector-drawable XMLs, downloaded from the Material Symbols catalog (fonts.google.com/icons, Android tab) in the app's chosen style/weight and checked into the design-system module/package under `res/drawable/ic_<name>.xml`; `Icon` with `ImageVector`/`painterResource` renders them, tinted via `LocalContentColor`/theme roles — never hard-coded colors
- **MUST** mark directional icons for RTL mirroring on the checked-in vector itself: `android:autoMirrored="true"` on the `<vector>` root (API 19+, system-handled mirroring for drawables whose RTL form is a plain graphical mirror) [R21] — navigation arrows, back/forward, undo/redo, and list-indent glyphs mirror; media-playback, clock, and check-mark icons do not (this list is authoritative; `spec/android/localization/` §D refers back here for RTL icon behaviour). `Icons.AutoMirrored.*` is the same idea inside the deprecated `material-icons-core`/`-extended` artifacts [R6] and is therefore mentioned here only for legacy code that still carries them: it is a migration note, never a reason to add those artifacts to a module in conflict with the first bullet
- **MUST** centralize icon access in one registry object in the design system (the `NiaIcons` pattern): features reference the registry, never an icon library directly — the registry is the single point where the style-family decision is enforced
- **MUST** keep UI icons vector (`VectorDrawable`); raster is reserved for photographic content; animated icon states **MAY** use `AnimatedImageVector` (experimental) or Compose animation APIs
- **SHOULD** follow the `ic_<name>` resource naming convention (established tooling convention)

### C. Launcher icon

- **MUST** ship an adaptive icon (`mipmap-anydpi-v26`): 108dp canvas, foreground + background layers (vectors preferred), all critical content inside the 66dp safe zone, clean edges — no self-drawn masks, outlines, or shadows (OEM masks vary and the system composes effects)
- **MUST** provide a designed `<monochrome>` layer for themed icons (authored as a single-color version of the foreground silhouette, not an automatic tint of the full-color foreground): user icon theming is Play-accepted policy, and recent Android applies *automatic* theming to apps without a monochrome layer [R7][R10] — a missing layer means an algorithmically generated result instead of a designed one
- **SHOULD** keep the launcher glyph a simple, text-free silhouette that survives masking and monochrome rendering; the Play-Store 512px asset mirrors the same artwork (full square, no self-rounded corners or shadows — Play masks dynamically)
- **MUST NOT** use launcher/product-logo artwork in in-app UI icon slots — in-app slots follow §A

### D. Notification, shortcut, and tile icons

- **MUST** design the notification small icon alpha-only: white artwork on transparency at 24dp base — the system renders only the alpha channel and derives color from `setColor`/theme; colored or solid artwork degrades to a blob
- **SHOULD** use the large notification icon only when imagery carries meaning (sender avatar — circular for persons, square otherwise; content source; meaningful symbol), and a per-type symbol instead of the app logo when the app sends many notification kinds
- **MUST** follow the shortcut spec where app shortcuts exist: 48dp circular container (44dp live area, 2dp padding, `#F5F5F5` fill, no shadows) with a centered 24dp vector system icon; avatars as density PNGs; at most four distinct shortcuts
- **MUST** provide quick-settings tile icons as solid-white 24dp `VectorDrawable`s (system tints by tile state)

### E. Icon accessibility

- **MUST** give every functional icon a meaningful `contentDescription` (the action, not the picture: "Take photo", not "camera"); stateful icon-only controls describe their state; decorative icons set `contentDescription = null` so screen readers skip them
- **MUST** keep icon-to-container contrast at 3:1 minimum, and never encode meaning in icon color alone
- Navigation-item label and selected-state placement rules live in `spec/android/app-design-navigation/` §C; this spec supplies the fill/weight mechanics (filled = active) they build on

## Acceptance Criteria

The criteria below are a deliberate representative rollup of §A–§E, not a 1:1 mapping; every requirement bullet above is normative on its own. Verification of the rendering and accessibility criteria runs through `spec/android/test-automation/` (screenshot tests for icon rendering, ATF checks for content descriptions and touch targets).

- [ ] The app uses exactly one Material Symbols style family; no screen mixes families or weights
- [ ] Active/selected navigation states render the filled variant (or semibold fallback); inactive states render outlined
- [ ] No module depends on `material-icons-core` or `material-icons-extended`; all icons are checked-in vector drawables behind the central registry
- [ ] Every directional icon carries `android:autoMirrored="true"` on its checked-in vector; media/clock icons do not; no `Icons.AutoMirrored.*` reference exists outside recorded legacy code
- [ ] The launcher icon is adaptive with foreground, background, and monochrome layers, content inside the 66dp safe zone, and no baked-in mask or shadow
- [ ] The notification small icon is white-on-transparent and renders correctly (no blob) on API 31+ with a set accent color
- [ ] Every functional icon has an action-phrased content description; every decorative icon passes `null`; icon touch targets measure ≥ 48dp
- [ ] Icon tints resolve through `LocalContentColor`/theme roles; no icon call site hard-codes a color
- [ ] Where shortcuts or quick-settings tiles exist, their icons match the per-surface specs in §D
- [ ] Icon-to-container contrast is at least 3:1, and no icon encodes meaning through color alone
- [ ] No launcher/product-logo artwork appears in an in-app UI icon slot
- [ ] Custom icons match the Material grid metrics (trim/live area, stroke, corners) of the chosen family
- [ ] Icon drawables follow the `ic_<name>` naming convention, or the deviation from §B's SHOULD is recorded

## Open Questions

All questions are parking-lot class: the requirements above state a working default for each (outlined family default per §A, checked-in `ic_<name>.xml` per §B, designed monochrome layer per §C).

- Migration guidance for existing apps still on `material-icons-extended`: dedicated skill operation, or does the UX-audit skill only flag it without auto-remediating (current default)?
- Icon downloads: keep the manual catalog-download-and-check-in workflow of §B, or wire a small fetch script for the Symbols catalog into the project scaffold?
- Style-family override: should the Compose-UI skill prompt for family at scaffold time, or always start `outlined` and let the app change it later?

## References

All sources retrieved 2026-08-11; R6 and R21 re-verified 2026-08-19. Class markers: (P) primary/authoritative vendor documentation, (S) secondary (reference-project code, ecosystem documentation). m3.material.io pages are client-rendered; contents were captured via rendered fetches of the canonical URLs.

- [R1] Material Symbols guide (styles, variable axes) (P): <https://developers.google.com/fonts/docs/material_symbols>
- [R2] M3 — applying icons (fill/weight/grade, target sizes, labels) (P): <https://m3.material.io/styles/icons/applying-icons>
- [R3] M3 — designing icons (grid, keylines, stroke, custom icons) (P): <https://m3.material.io/styles/icons/designing-icons>
- [R4] M3 — navigation bar guidelines (filled = active convention, contrast) (P): <https://m3.material.io/components/navigation-bar/guidelines>
- [R5] Compose material icons deprecation and Symbols workflow (P): <https://developer.android.com/develop/ui/compose/graphics/images/material>
- [R6] Compose Material releases (`Icons.AutoMirrored` introduced in `material-icons-core`/`-extended` 1.6.0-alpha05, plain directional icons deprecated there) (P): <https://developer.android.com/jetpack/androidx/releases/compose-material>
- [R7] Adaptive launcher icons (layers, safe zone, monochrome; Android 16 QPR2 auto-theming) (P): <https://developer.android.com/develop/ui/views/launch/icon_design_adaptive>
- [R8] Create app icons (Image Asset Studio, densities, notification generation) (P): <https://developer.android.com/studio/write/create-app-icons>
- [R9] Play icon design specification (512px, dynamic masking) (P): <https://developer.android.com/google-play/resources/icon-design-specifications>
- [R10] Play policy change: user icon theming (2025) (S): <https://www.androidauthority.com/google-play-icon-theming-agreement-3597899/>
- [R11] Notifications design guidance (small/large icon rules) (P): <https://developer.android.com/design/ui/mobile/guides/home-screen/notifications>
- [R12] Build a notification (small icon requirement) (P): <https://developer.android.com/develop/ui/views/notifications/build-notification>
- [R13] Notification icon rendering (alpha channel) (S): <https://documentation.onesignal.com/docs/en/notification-icons>
- [R14] App Shortcuts icon design guidelines (PDF) (P): <https://developer.android.com/static/shareables/design/app-shortcuts-design-guidelines.pdf>
- [R15] Quick-settings tiles (white vector requirement) (P): <https://developer.android.com/develop/ui/views/quicksettings-tiles>
- [R16] Vector drawable resources (vector-first rationale) (P): <https://developer.android.com/develop/ui/views/graphics/vector-drawable-resources>
- [R17] Animated vector drawables in Compose (experimental) (P): <https://developer.android.com/develop/ui/compose/animation/vectors>
- [R18] Compose accessibility semantics (contentDescription rules) (P): <https://developer.android.com/develop/ui/compose/accessibility/semantics>
- [R19] Icon-button accessibility (stateful descriptions) (P): <https://developer.android.com/develop/ui/compose/components/icon-button>
- [R20] Now in Android central icon registry (S): <https://github.com/android/nowinandroid> (core/designsystem/icon/NiaIcons.kt)
- [R21] Language support basics — `android:autoMirrored="true"` for RTL drawable mirroring (API 19+), limits for multi-element drawables (P): <https://developer.android.com/training/basics/supporting-devices/languages>
