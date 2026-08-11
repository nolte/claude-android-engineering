# Screen composable template

Templates for the stateful-route + stateless-content split, an adaptive list-detail layout,
and the preview set. Fill in the feature name, state shape, and content; keep every rule from
`ux-checklist.md` intact. Package and module placement follow `spec/android/project-structure/`
§E (feature package holds the screen, ViewModel, and nav code together; theme/design-system in
the `designsystem` package).

## Table of contents

- [1. UI state](#1-ui-state)
- [2. Stateful route composable](#2-stateful-route-composable)
- [3. Stateless content composable](#3-stateless-content-composable)
- [4. Adaptive list-detail variant](#4-adaptive-list-detail-variant)
- [5. Navigation key and entry](#5-navigation-key-and-entry)
- [6. Preview set](#6-preview-set)

## 1. UI state

Every state must be constructible without a ViewModel, so the Compose test can drive the
content composable directly.

```kotlin
sealed interface ExampleUiState {
    data object Loading : ExampleUiState
    data class Success(val items: List<ExampleItem>) : ExampleUiState
    data object Empty : ExampleUiState
    data class Error(val message: String) : ExampleUiState
}
```

## 2. Stateful route composable

Thin: obtains the ViewModel, collects state, forwards event lambdas. Passes no `NavController`
down. Navigation runs in the lambdas the caller injects.

```kotlin
@Composable
fun ExampleRoute(
    onItemClick: (String) -> Unit,
    onCreate: () -> Unit,
    viewModel: ExampleViewModel = hiltViewModel(),
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    ExampleContent(
        uiState = uiState,
        onItemClick = onItemClick,
        onCreate = onCreate,
        onRetry = viewModel::retry,
    )
}
```

## 3. Stateless content composable

All styling flows through theme roles and `*Defaults`. Strings via `stringResource`. One
primary action (here the FAB) in the bottom zone. Insets via `Scaffold`.

```kotlin
@Composable
fun ExampleContent(
    uiState: ExampleUiState,
    onItemClick: (String) -> Unit,
    onCreate: () -> Unit,
    onRetry: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            TopAppBar(title = { Text(stringResource(R.string.example_title)) })
        },
        floatingActionButton = {
            // Exactly one primary action per screen.
            FloatingActionButton(onClick = onCreate) {
                Icon(
                    painter = painterResource(AppIcons.Add), // central registry, not a lib
                    contentDescription = stringResource(R.string.example_create_action),
                )
            }
        },
    ) { padding ->
        Box(Modifier.padding(padding).fillMaxSize()) {
            when (uiState) {
                ExampleUiState.Loading ->
                    CircularProgressIndicator(Modifier.align(Alignment.Center))
                is ExampleUiState.Success ->
                    ExampleList(items = uiState.items, onItemClick = onItemClick)
                ExampleUiState.Empty ->
                    EmptyState( // onboarding moment + call-to-action, never a dead end
                        text = stringResource(R.string.example_empty_body),
                        actionLabel = stringResource(R.string.example_create_action),
                        onAction = onCreate,
                    )
                is ExampleUiState.Error ->
                    ErrorState( // names the problem + next step, preserves input elsewhere
                        message = uiState.message,
                        onRetry = onRetry,
                    )
            }
        }
    }
}
```

## 4. Adaptive list-detail variant

Use when the content is a collection-plus-detail relationship. Two panes on expanded, one
below, selection preserved across the boundary (`spec/android/screen-formats/` §C). Branch on
the window size class only for high-level structure, never on device type.

```kotlin
@Composable
fun ExampleListDetailRoute(
    viewModel: ExampleViewModel = hiltViewModel(),
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val navigator = rememberListDetailPaneScaffoldNavigator<String>() // key type is Parcelable
    val scope = rememberCoroutineScope()

    NavigableListDetailPaneScaffold(
        navigator = navigator,
        listPane = {
            AnimatedPane {
                ExampleContent(
                    uiState = uiState,
                    onItemClick = { id ->
                        scope.launch {
                            navigator.navigateTo(ListDetailPaneScaffoldRole.Detail, id)
                        }
                    },
                    onCreate = viewModel::create,
                    onRetry = viewModel::retry,
                )
            }
        },
        detailPane = {
            AnimatedPane {
                navigator.currentDestination?.contentKey?.let { id ->
                    ExampleDetailContent(id = id)
                }
            }
        },
    )
}
```

## 5. Navigation key and entry

Keys are `@Serializable` and implement `NavKey`; the back stack is app state
(`spec/android/app-design-navigation/` §B).

```kotlin
@Serializable
data class ExampleKey(val id: String? = null) : NavKey

fun EntryProviderBuilder<NavKey>.exampleEntry(
    onItemClick: (String) -> Unit,
    onCreate: () -> Unit,
) {
    entry<ExampleKey> {
        ExampleRoute(onItemClick = onItemClick, onCreate = onCreate)
    }
}
```

## 6. Preview set

Previews target the stateless content composable, live next to it, and are named
`<Composable>Preview`. Cover every state plus size/font/locale variants
(`spec/android/localization/` §F, `spec/android/screen-formats/` §D).

```kotlin
@Preview(name = "Populated", showBackground = true)
@Composable
private fun ExampleContentPreview() {
    AppTheme {
        ExampleContent(
            uiState = ExampleUiState.Success(items = fakeItems),
            onItemClick = {}, onCreate = {}, onRetry = {},
        )
    }
}

@Preview(name = "Empty") @Preview(name = "Error")
@Composable
private fun ExampleContentEdgeStatesPreview() { /* Empty and Error states */ }

@PreviewScreenSizes
@Composable
private fun ExampleContentScreenSizesPreview() {
    AppTheme { ExampleContent(ExampleUiState.Success(fakeItems), {}, {}, {}) }
}

@PreviewFontScales
@Composable
private fun ExampleContentFontScalesPreview() {
    AppTheme { ExampleContent(ExampleUiState.Success(fakeItems), {}, {}, {}) }
}

@Preview(name = "German", locale = "de")
@Preview(name = "RTL", locale = "ar")
@Composable
private fun ExampleContentLocalePreview() {
    AppTheme { ExampleContent(ExampleUiState.Success(fakeItems), {}, {}, {}) }
}
```
