# Long Lists and Continuous Scrolling

Status: draft

## Context

A screen that shows many entries — a feed, an inbox, a catalogue, a measurement log — is the place where an app's smoothness is judged. The user's verdict is formed by three properties that are routinely confused with each other: whether frames arrive inside their deadline (*jank*), whether the interaction is quantised into steps the user has to operate (*pagination, snapping, "load more"*), and whether the content jumps under the finger (*layout shift and lost scroll position*). "Continuous scrolling" — the property this spec is named for — requires all three, and each has a different cause and a different fix. Fixing the wrong one is the standard failure mode: a list that stutters because a stale item list is recomposed every frame is not made smooth by a bigger page size, and a list that jumps back to the top after a refresh has no frame-timing problem at all.

This spec fixes how this portfolio's skills build and judge such a surface: which container is the right one, how items keep their identity, how the next entries arrive without a visible step, how the scroll position survives everything that can happen to a process, how a list stays navigable once it is longer than a user can scroll, and how the result is measured rather than felt.

Provenance: desk research (August 2026) over the Compose lazy-layout and performance documentation, the Paging 3 documentation, the Android vitals rendering thresholds, the Macrobenchmark metric reference, the Baseline Profile guidance, the androidx release notes (for the API-availability statements, which are version-bound and dated), and the Nielsen Norman Group's scroll-pattern research. No requirement here rests on a first-party measurement; where a behaviour is documented only by community evidence rather than by vendor documentation, the requirement says so and its source carries the (S) marker.

Boundaries: list-row anatomy, the card rules, and the wait-indication matrix (the 200 ms / 5 s thresholds and which indicator belongs to which wait) are owned by `spec/android/ui-components/` §A; general state preservation and error-message rules by `spec/android/app-design-navigation/` §D/§F; the adaptive feed grid, list-detail panes, and the canonical layouts by `spec/android/screen-formats/` §C, with per-size-class behaviour by its §B; the benchmark lane and its CI exclusion by `spec/android/test-automation/` §F; device and trace mechanics by `spec/android/adb-workflows/`. App-wide startup and jank methodology has no spec yet — see §Open Questions.

Readers: authors of this repo's Android skills who generate or review a list-bearing screen, and reviewers judging whether such a screen scrolls the way this corpus requires.

## Goals

- Make the container decision mechanical, including the three constructions that silently defeat laziness
- Separate the three causes of "not smooth" so a skill fixes the one it actually has
- Make loading the next entries invisible: no step, no spinner where cached data exists, no layout shift
- Make the scroll position unloseable — across recomposition, refresh, navigation, rotation, and process death
- Keep a list navigable past the point where scrolling stops being a usable access path
- Keep the surface usable with a screen reader, a keyboard, and a switch, which is where infinite scrolling fails first
- Make smoothness a measured number on a release build, not an impression from a debug build

## Non-Goals

- App-startup performance (TTID/TTFD), Baseline Profile authoring mechanics beyond the scroll journey, and the general jank methodology — no spec owns these yet (§Open Questions)
- List-row composition and the loading-indicator component choice — `spec/android/ui-components/` §A
- Adaptive column counts, list-detail panes, and window-size behaviour — `spec/android/screen-formats/` §C and §B
- Server-side pagination API design (cursor vs offset, page-token contracts) — a backend concern this spec only consumes
- New development against `RecyclerView`; only the interop rule for an existing View-based screen is in scope
- Deliberately paginated surfaces (onboarding pagers, media viewers) whose stepping is the intended interaction

## Requirements

### A. Container choice

- **MUST** use a lazy container (`LazyColumn`, `LazyRow`, `LazyVerticalGrid`, `LazyVerticalStaggeredGrid`) for every collection that is data-driven, of unknown length, or longer than the viewport: a `Column`/`Row` with `Modifier.verticalScroll` composes and lays out every child whether or not it is visible [R1]. A plain `Column` is correct only for a short, fixed set the screen is designed around — and **MUST** be the choice there, because a lazy container for six known rows buys nothing and costs the item machinery [R1]
- **MUST NOT** nest a same-direction scroll container whose inner size is unbounded: a `LazyColumn` inside a `Modifier.verticalScroll` throws `IllegalStateException`, because the inner container is offered infinite height [R1]. Headers, footers, banners, and interleaved sections belong **inside** the same lazy container via its `item`/`items` DSL. A cross-direction nest (`LazyRow` inside a `LazyColumn` item) is legal. A same-direction nest with a **fixed inner size** is legal [R1] and **SHOULD** be treated as a smell rather than a violation — it does not throw, but two scroll surfaces then compete for one gesture
- **MUST NOT** emit several logical entries from a single `item {}`: they become one composition unit, can no longer be composed or reused individually, and desynchronise the indices `scrollToItem`/`animateScrollToItem` address [R1]. Only decoration belonging to the row itself (a trailing divider) **MAY** share an item
- **MUST NOT** let an item measure to zero in the scroll direction — an item whose height depends on data that has not arrived yet (a network image without a declared size) makes the whole collection fit the viewport on the first measurement, so the lazy container composes *every* item at once [R1]. Every item **MUST** carry an intrinsic or declared size before its content arrives, and that size **MUST** equal the loaded size so nothing shifts when it does [R1]
- **MUST NOT** attach a snapping fling behaviour, or reach for `HorizontalPager`/`VerticalPager`, to browse many entries: snapping quantises the scroll into steps, which is precisely the property this spec forbids. Pagers are for surfaces whose stepping is the interaction (onboarding, one media item per page)
- **SHOULD** choose the grid variants by content shape — uniform tiles to a grid, mixed-height media to a staggered grid — with the column count owned by the adaptive feed rule in `spec/android/screen-formats/` §C, never a hard-coded number
- **SHOULD NOT** start a new View-based list; where an existing `RecyclerView` screen is extended rather than migrated, its adapter **MUST** diff through `DiffUtil`/`AsyncListDiffer` with stable IDs, which is the same identity requirement as §B in a different API [R23]

### B. Item identity and recomposition

- **MUST** give every item a stable, unique `key` derived from the domain identity (an ID), never the list index: without it Compose falls back to the position, so an insertion or reorder invalidates every item after it, and item state and animations follow the wrong row [R1]
- **MUST** keep that key `Bundle`-compatible (primitive, enum, or `Parcelable`) — the key is what restores `rememberSaveable` state inside an item after activity recreation and after the item is scrolled away and back [R1]
- **MUST** supply `contentType` for any collection with more than one item shape; without it Compose may reuse the composition of type A for an item of type B, which is the expensive case rather than the cheap one [R1]
- **MUST** treat `Modifier.animateItem` as key-dependent: it is only correct with stable keys, and it **MUST NOT** be used to paper over reordering caused by unstable keys [R1]
- **MUST NOT** perform sorting, filtering, grouping, formatting, or any other derivation inside an item body or inside the lazy container's scope: composable bodies run as often as once per frame [R2]. Derivations belong in the ViewModel or the query; where one must stay in the UI layer it **MUST** be wrapped in `remember(inputs)` [R2]
- **MUST** defer scroll-dependent state reads to the latest possible phase: pass a lambda instead of a value, and use the lambda-taking modifiers (`Modifier.offset { … }`) so a scrolling parallax or collapse re-runs layout/draw rather than composition [R2]
- **MUST** wrap any boolean derived from scroll state in `derivedStateOf` (`listState.firstVisibleItemIndex > 0`), and route side effects (analytics, prefetch triggers, scroll-to-top on refresh) through `snapshotFlow` in a `LaunchedEffect` — reading `firstVisibleItemIndex` directly in composition recomposes on every scrolled pixel [R1][R2]
- **MUST NOT** write to state that has already been read in the same composition (a *backwards write*): it can recompose endlessly, every frame, which presents as scroll jank with no expensive item in sight [R2]
- **SHOULD** hand item composables parameters that skip: strong skipping (default since Compose 1.7) makes every restartable composable skippable, but it compares unstable parameters — `List`, `Map`, `Set` and every other collection interface — by *instance*, so a list re-created by `map`/`filter`/`copy` on each emission recomposes the container regardless [R19][R20]. Pass `ImmutableList` (kotlinx-collections-immutable) or an `@Immutable` state type, and hold the collection identity stable across emissions
- **MUST NOT** "fix" that by adding `List` to the compiler's stability configuration: the class then compares by `equals`, which in a lazy list costs a full element-wise comparison at the container **and** again per visible item [R19]

### C. Continuity — loading without a step

- **MUST** page the data source for any collection that is unbounded, remote, or too large to hold in memory, and **MUST** use Paging 3 for it rather than a hand-rolled "observe the last visible index and append" loop: request deduplication, the load-state model, retry, and the in-memory cache are the parts a hand-rolled loop gets wrong [R4]
- **MUST** make a local database the single source of truth whenever a network source is paged, with `RemoteMediator` writing into it and the database's `PagingSource` feeding the UI — network-only paging loses its data on configuration change, on process death, and offline [R6]. The UI **MUST** display only what is cached
- **MUST** call `cachedIn(viewModelScope)` on the `PagingData` flow; without it the flow cannot be re-collected, so every recomposition-triggering event restarts loading [R5]
- **MUST** size the page so the next page starts loading before the user reaches the current one — `prefetchDistance` in items ahead, `pageSize` a multiple of the visible item count, and an `initialLoadSize` large enough that the first screen is not itself a step [R4][R5]. The numbers are per-project and **MUST** be recorded where they are set, not scattered as literals
- **MUST** decide placeholders explicitly, and **MUST** make both branches step-free: with `enablePlaceholders = true` the UI **MUST** render a `null` item as a placeholder of the *same height* as the loaded row [R5]; with placeholders off, the pending page **MUST** be represented by a footer element that appears without moving the rows above it. A page arriving must never change the offset of content already on screen
- **MUST** handle `refresh`, `append`, and `prepend` load states separately, surfacing `LoadState.Error` with a `retry()` affordance instead of an empty list — an empty list and a failed load are different states and **MUST NOT** collapse into one [R7]
- **MUST NOT** show a full-screen loading state while cached data exists: distinguish `loadState.mediator` from `loadState.source` so a background sync is an unobtrusive indicator over live content, not a blank screen [R7]
- **SHOULD** widen the prefetch window beyond the default one item when items are expensive to compose: `LazyLayoutCacheWindow` sizes the ahead cache area and the behind area in pixels, and the behind window is what keeps items ready when the user scrolls back [R11][R14][R24]. The gate is the **annotation, never a version number**: while the API carries `@ExperimentalFoundationApi` [R14][R24], adopting it **MUST** be a recorded decision and **MUST NOT** be a default in generated code — and a skill **MUST** re-check that annotation against the project's own dependency set rather than trusting the dated observation in §References
- **SHOULD** schedule nested prefetch (`onNestedPrefetch`, via the prefetch strategy) for a `LazyRow` carousel inside a `LazyColumn`, restricted to the children that will actually be visible — otherwise the row composes its whole first screen in the frame it scrolls into view [R15]
- **MUST** load item images through a cache-backed loader at a declared target size with a placeholder of that size, and **MUST NOT** decode full-resolution bitmaps for a row [R21]; the placeholder is what §A's no-zero-size and this section's no-shift rules depend on

### D. Scroll-position integrity

- **MUST** hoist the scroll state (`rememberLazyListState`, or a state held by the ViewModel where the same list is reached from several routes) so it survives recomposition and configuration change, and **MUST** rely on the same keys from §B for the per-item state inside it [R1]
- **MUST NOT** compose the list with an empty item list on the first frame when a restored scroll position exists: a lazy container cannot distinguish "no items yet" from "no items any more", and a non-zero restored position is overwritten with 0 in that frame — the standard symptom of a paged list that jumps to the top after process death or a return from detail [R22] (S). The screen **MUST** render a loading state until the first page is available, or hold the list state per data identity, rather than compose an empty list and scroll it back afterwards
- **MUST NOT** compensate for such a jump with a `scrollToItem` after the fact: it is visible, it fights the user's fling, and it hides the actual defect
- **MUST** keep keys stable across a refresh — a refresh that re-keys the same entries (index keys, freshly generated UUIDs, keys containing a timestamp) is indistinguishable from a full replacement and discards both position and item state [R1]
- **MUST** ensure a `prepend` or an insertion above the viewport does not move the visible content: the anchor is the visible item's key, and content growing above it **MUST NOT** push it down the screen [R1][R7]
- **MUST** land the user at the same position when they return from a detail screen, from recents, or after a lock/unlock — the Play core app-quality requirement is owned by `spec/android/app-design-navigation/` §D; this spec's contribution is that the list's own state is what makes it achievable
- **SHOULD** scroll to the top only on an event the user caused (a pull-to-refresh, a filter change), and then **SHOULD** do it through `snapshotFlow` on the refresh load state so it happens once the new data is present, not before [R7]

### E. Findability past the scroll limit

- **MUST NOT** make an unbounded scroll the only access path to a large collection: search, filter, and sort **MUST** exist wherever the user's task is to find a specific entry, and sections with sticky headers **SHOULD** carry the ordering the user is expected to reason in [R1][R16]
- **MUST NOT** use infinite scrolling for tasks that are goal-directed: finding a specific item, comparing entries that lie far apart, or inspecting only the top results are the documented failure cases, where a "load more" control or explicit pagination is the correct pattern; infinite scrolling fits homogeneous, exploratory browsing [R16][R17]
- **MUST** make the end of the collection recognisable — `endOfPaginationReached` renders a terminal element, not a silently absent footer; without it the list is indistinguishable from one that failed to load and users infer incompleteness [R7][R16]
- **MUST NOT** strand content behind an endless list: anything the user must be able to reach (legal links, settings, a summary) **MUST** live outside the scroll container or above it, because a list that grows on approach can never be scrolled past [R16]
- **SHOULD** show scroll position for collections long enough to disorient — a project either adopts the platform scroll-indicator API as a recorded decision or builds the indicator from `layoutInfo`. The same gate applies as above: the choice follows the API's stability annotation in the project's own dependency set, and a skill **MUST NOT** treat the dated API observation in §References as current [R11][R12]
- **MUST** treat the empty state, the error state, and the loading state as designed states of the same surface, each with a next action, never as an empty list

### F. Accessibility of a long list

- **MUST** keep collection semantics intact: the lazy containers supply `collectionInfo`/`collectionItemInfo` themselves, so a hand-built scroll container **MUST** supply them explicitly — without them a screen reader cannot announce "item 12 of 340" and the user loses all sense of position [R18]
- **MUST** announce loading and newly appended content rather than changing the list silently; a screen reader user gets no visual cue that more entries arrived [R16][R18]
- **MUST** provide a non-scroll path to content that infinite scrolling would otherwise gate — a "load more" control, pagination, or search — because keyboard, switch, and screen-reader users cannot reliably trigger scroll-driven loading, and this is the pattern's primary accessibility failure [R16]
- **MUST** keep the row's own accessibility contract (touch-target size, merged semantics, meaningful labels) per `spec/android/ui-components/` §A — a list multiplies every per-row defect by its length

### G. Measurement and budgets

- **MUST** judge scroll smoothness only on a non-debuggable release build with R8 enabled, on a physical device: a debug build imposes a performance cost that both hides and invents problems [R3]. A jank claim from a debug build **MUST NOT** be reported as a finding
- **MUST** measure with `FrameTimingMetric` over a scroll journey rather than by eye, and read `frameOverrunMs` (API 31+) as the primary number: positive values are dropped frames and visible stutter, negative values are headroom, reported at P50/P90/P95/P99 [R9]. The P95/P99 tail is where scroll jank lives — a healthy P50 proves nothing
- **MUST** state the frame deadline the budget is set against, because it is display-dependent: ~16 ms at 60 Hz, ~11 ms at 90 Hz, ~8 ms at 120 Hz [R8]. A budget without its refresh rate is unfalsifiable
- **MUST** treat any frame over 700 ms as a defect regardless of percentile — vendor guidance is that no frame should ever take that long — and frames between 16 ms and 700 ms as the slow-frame class that presents as abrupt scrolling [R8]
- **MUST** include the scroll journey of the app's main list in the Baseline Profile: profiles cover navigation and scrolling, not only startup, and are verified against the minified release build [R10]
- **MUST NOT** propose a framework change as a jank remedy: since Compose 1.9 the measured jank rate for scrolling lists and grids matches the View implementation of the same app [R3]. A slow list is a data, item, or image problem
- **SHOULD** keep these benchmarks in the separate scheduled lane per `spec/android/test-automation/` §F rather than the per-commit suite, and **SHOULD** record the device, build type, and refresh rate alongside every number — a frame budget without them is not comparable across runs
- **MUST** take the general methodology from `spec/android/perceived-performance/` — the measurement-validity gate (§B), the benchmark-module layout and result handling (§G), and the remediation order (§H) — and **MUST** surface the gap and propose a spec extension for anything neither spec states (REQ-6, REQ-17)

## Acceptance Criteria

The criteria below are a deliberate representative rollup of §A–§G, not a 1:1 mapping; every requirement bullet above is normative on its own. Two normative bullets are deliberately left to reviewer judgement rather than a mechanical criterion, because both are judgements about a skill's *reasoning* and not properties of an artifact: the prohibition on proposing a framework change as a jank remedy, and the obligation to take the general methodology from `spec/android/perceived-performance/` rather than inventing a budget number (both §G).

- [ ] Every data-driven or unbounded collection uses a lazy container; no scroll container of the same direction is nested inside another; no `item {}` emits more than one logical entry
- [ ] No item can measure to zero in the scroll direction: every asynchronously filled item declares a size before its content arrives, and that size is unchanged after it arrives
- [ ] Every item has a stable, `Bundle`-compatible domain key; no list keys by index; heterogeneous collections supply `contentType`; `animateItem` appears only with keys
- [ ] No sorting, filtering, or formatting runs in an item body or a lazy scope without `remember`; scroll-derived booleans go through `derivedStateOf`, scroll side effects through `snapshotFlow`, and scroll-driven visual offsets through lambda-taking modifiers; no state is written after being read in the same composition
- [ ] Item composables receive skippable parameters (`ImmutableList` or `@Immutable` state), and `List` is not added to the stability configuration
- [ ] Paged collections use Paging 3 with a database source of truth behind any network source, `cachedIn`, and a recorded `PagingConfig` rather than scattered literals
- [ ] A page arriving never changes the offset of content already on screen: placeholders match loaded-row height, or the pending page is a footer element
- [ ] `refresh`, `append`, and `prepend` states are handled separately, errors offer retry, and no full-screen loading state covers existing cached data
- [ ] A restored scroll position is never composed against an empty item list, no `scrollToItem` compensates for a jump, keys survive a refresh unchanged, and returning from a detail screen, from recents, or after lock/unlock lands on the same position
- [ ] A large collection offers search/filter/sort, a recognisable end, and no content stranded behind the endless scroll; goal-directed tasks are not served by infinite scrolling alone
- [ ] Collection semantics reach the screen reader, loading is announced, and a non-scroll path exists to content that scroll-driven loading would otherwise gate
- [ ] Every reported scroll number comes from `FrameTimingMetric` on a non-debuggable release build on a physical device, cites its refresh-rate deadline, reports the P95/P99 tail, and the main list's scroll journey is in the Baseline Profile
- [ ] No browsing surface snaps or pages through its entries, and any retained `RecyclerView` adapter diffs through `DiffUtil`/`AsyncListDiffer` with stable IDs
- [ ] Item images load through a cache-backed loader at a declared target size with a placeholder of that size, and no row decodes a full-resolution bitmap
- [ ] No frame in a measured scroll journey exceeds 700 ms; every adoption of an experimental scrolling API is a recorded decision rather than a generation default; and a scroll-to-top happens only on a user-caused event and only once the new data is present

## Open Questions

- Frame budget as a number: this spec fixes the *deadline* per refresh rate and the vendor thresholds (16 ms slow, 700 ms frozen), but not the pass/fail percentile for a scroll benchmark (`frameOverrunMs` P95 ≤ 0? P99?). No vendor source states one, so inventing it would violate the corpus rule against silent decisions; `spec/android/perceived-performance/` §C inherits this refusal explicitly rather than resolving it.
- General jank and startup methodology now has an owner: `spec/android/perceived-performance/` §B/§G/§H covers the validity gate, benchmark-module layout, result handling, and the remediation order. This spec continues to own list-scroll measurement alone.
- Experimental prefetch and scroll indicators: adopt `LazyLayoutCacheWindow` and `Modifier.scrollIndicator` now (both available, both experimental in the current stable line) or wait for the stable APIs? Working default: recorded decision per project, never a generation default.
- Default `PagingConfig` shape: should the skills carry a default `pageSize`/`prefetchDistance`/`initialLoadSize` triple derived from the visible item count, or require a per-project choice? Working default: per-project, recorded at the definition site.
- Placeholders as the house default: `enablePlaceholders = true` gives a step-free scrollbar and stable extent but demands equal-height rows; off is safer for variable-height content. Working default: explicit per list, both branches constrained by §C.

## References

Sources retrieved 2026-08-11; every version and API-availability statement re-verified 2026-08-12. Class markers: (P) primary/authoritative vendor documentation and vendor release notes, (S) secondary — vendor-authored engineering articles, maintained tool documentation, third-party API indexes, community-reported behaviour, and published UX research.

**Version statements are dated observations, not pins.** No requirement in this spec is gated on a version number; the two that concern experimental APIs are gated on the stability annotation a reader is required to re-check in the project's own dependency set (§C, §E). Observed 2026-08-12: the latest stable `compose-foundation` is `1.12.0` and the latest stable `compose-material3` is `1.4.0`, while the current Compose BOM `2026.06.01` still maps to `compose-foundation 1.11.4` — a BOM lags its libraries, so the API surface a project actually has follows its BOM, not the newest release [R11][R12][R13]. `LazyLayoutCacheWindow` carried `@ExperimentalFoundationApi` on that date [R14][R24], with a stabilisation entry appearing in the `1.13.0-alpha01` notes [R11]; the Material 3 scrollbar sat in the `1.5.0-alpha` line [R12]. These figures will age faster than the requirements they illustrate.

- [R1] Lists and grids in Compose — laziness, keys, `contentType`, sticky headers, `animateItem`, scroll state, nesting rules, zero-size items, one-entry-per-item rule (P): <https://developer.android.com/develop/ui/compose/lists>
- [R2] Compose performance best practices — `remember`, `derivedStateOf`, deferred reads, backwards writes (P): <https://developer.android.com/develop/ui/compose/performance/bestpractices>
- [R3] Compose performance overview — release build and R8 as preconditions, jank parity with Views since Compose 1.9 (P): <https://developer.android.com/develop/ui/compose/performance>
- [R4] Paging 3 overview — layering, `PagingSource`, `RemoteMediator`, `LazyPagingItems` (P): <https://developer.android.com/topic/libraries/architecture/paging/v3-overview>
- [R5] Paging 3 — displaying paged data, `PagingConfig`, placeholders and their `null` contract, `cachedIn`, invalidation (P): <https://developer.android.com/topic/libraries/architecture/paging/v3-paged-data>
- [R6] Paging 3 — network plus database, database as source of truth, `RemoteMediator`, `initialize()`, remote keys, `endOfPaginationReached` (P): <https://developer.android.com/topic/libraries/architecture/paging/v3-network-db>
- [R7] Paging 3 — `LoadState`, refresh/append/prepend, retry, mediator-vs-source distinction (P): <https://developer.android.com/topic/libraries/architecture/paging/load-state>
- [R8] Slow rendering / Android vitals — 16 ms at 60 fps, 11 ms at 90, 8 ms at 120, slow-frame and 700 ms frozen-frame thresholds (P): <https://developer.android.com/topic/performance/vitals/render>
- [R9] Macrobenchmark metrics — `FrameTimingMetric`, `frameDurationCpuMs`, `frameOverrunMs` (API 31+), P50/P90/P95/P99 (P): <https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics>
- [R10] Baseline Profiles overview — scroll journeys as profile content, release-build verification (P): <https://developer.android.com/topic/performance/baselineprofiles/overview>
- [R11] Compose Foundation release notes — `LazyLayoutCacheWindow` availability and stabilisation, `ScrollIndicatorState`, `Modifier.scrollIndicator`, prefetch-scheduler fixes (P): <https://developer.android.com/jetpack/androidx/releases/compose-foundation>
- [R12] Compose Material 3 release notes — scrollbar and `PullToRefreshBox` API state, current stable version (P): <https://developer.android.com/jetpack/androidx/releases/compose-material3>
- [R13] Compose BOM to library mapping (P): <https://developer.android.com/develop/ui/compose/bom/bom-mapping>
- [R14] `LazyLayoutCacheWindow` API reference — ahead/behind cache window semantics (P): <https://developer.android.com/reference/kotlin/androidx/compose/foundation/lazy/layout/LazyLayoutCacheWindow>
- [R15] `LazyListPrefetchStrategy` API reference — `onNestedPrefetch`, `NestedPrefetchScope.schedulePrefetch` (P): <https://developer.android.com/reference/kotlin/androidx/compose/foundation/lazy/LazyListPrefetchStrategy>
- [R16] Infinite scrolling: when to use it, when to avoid it — task fit, footer stranding, refinding, back-navigation position loss, accessibility (S): <https://www.nngroup.com/articles/infinite-scrolling-tips/>
- [R17] Alternatives to infinite scrolling — load-more, integrated pagination, traditional pages (S): <https://www.nngroup.com/videos/alternatives-to-infinite-scrolling/>
- [R18] Compose accessibility semantics — `collectionInfo`/`collectionItemInfo` for collections (P): <https://developer.android.com/develop/ui/compose/accessibility/semantics>
- [R19] Jetpack Compose stability explained — collection interfaces are unstable, cost of the stability configuration in lazy lists (S): <https://medium.com/androiddevelopers/jetpack-compose-stability-explained-79c10db270c8>
- [R20] Strong skipping mode explained — default since Compose 1.7, instance comparison for unstable parameters (S): <https://medium.com/androiddevelopers/jetpack-compose-strong-skipping-mode-explained-cbdb2aa4b900>
- [R21] Coil for Compose — memory cache, target size, placeholders in scrolling lists (S): <https://coil-kt.github.io/coil/compose/>
- [R22] Lazy list scroll position reset when the first frame has no items, and the Paging workaround pattern (S): <https://issuetracker.google.com/issues/177245496> (sign-in required) and <https://effbada.hashnode.dev/how-to-remember-the-scroll-position-of-lazycolumn-built-with-paging-3-cl8d0x2st01odwpnv2g2o0q57>
- [R23] `RecyclerView` list-diffing reference — `DiffUtil`/`AsyncListDiffer` and stable IDs (P): <https://developer.android.com/reference/androidx/recyclerview/widget/AsyncListDiffer>
- [R24] Third-party Compose API index — independent corroboration of the `@ExperimentalFoundationApi` annotation on `LazyLayoutCacheWindow` and of its two window functions (S): <https://composables.com/jetpack-compose/androidx.compose.foundation/foundation/interfaces/LazyLayoutCacheWindow/api>
