# Screen composable template

Templates for the stateful-route + stateless-content split, the delayed loading state with
`ReportDrawnWhen`, an adaptive list-detail layout, the lazy list, a form with the submission
contract, and the preview set. Fill in the feature name, state shape, and content; keep every
rule of the authoring-time checklist `SKILL.md` step 1 points to intact. Package and module
placement follow `spec/android/project-structure/` §D/§E (feature package holds the screen,
ViewModel, and nav code together; theme/design-system in the `designsystem` package).

## Table of contents

- [1. UI state](#1-ui-state)
- [2. Stateful route composable](#2-stateful-route-composable)
- [3. Stateless content composable](#3-stateless-content-composable)
- [4. Delayed loading indicator](#4-delayed-loading-indicator)
- [5. Lazy list](#5-lazy-list)
- [6. Adaptive list-detail variant](#6-adaptive-list-detail-variant)
- [7. Form and submission variant](#7-form-and-submission-variant)
- [8. Navigation key and entry](#8-navigation-key-and-entry)
- [9. Preview set](#9-preview-set)

## 1. UI state

Every state must be constructible without a ViewModel, so the Compose test can drive the
content composable directly. The populated case carries an `ImmutableList` (kotlinx
collections-immutable) or an `@Immutable` type so item composables stay skippable
(`spec/android/long-list-scrolling/` §B); the error case carries a closed `ErrorKind`, never
a raw server string — the composable resolves the localized text
(`spec/android/user-input-validation/` §E, `spec/android/backend-contract/` §B).

```kotlin
sealed interface ExampleUiState {
    data object Loading : ExampleUiState
    data class Success(val items: ImmutableList<ExampleItem>) : ExampleUiState
    data object Empty : ExampleUiState
    data class Error(val kind: ErrorKind, val canRetry: Boolean = true) : ExampleUiState
}

@Immutable
data class ExampleItem(
    val id: String,
    val title: String,
    val subtitle: String?,
    val thumbnailUrl: String?,
)

/** Closed set mirroring the failure classification of `spec/android/backend-contract/` §B. */
sealed interface ErrorKind {
    data object Offline : ErrorKind
    data object ServerUnavailable : ErrorKind
    data object Unauthorized : ErrorKind
    data class Rejected(val field: String?, val ruleRes: Int) : ErrorKind // domain rejection
}

@Composable
fun ErrorKind.message(): String = when (this) {
    ErrorKind.Offline -> stringResource(R.string.error_offline_retry)
    ErrorKind.ServerUnavailable -> stringResource(R.string.error_server_retry)
    ErrorKind.Unauthorized -> stringResource(R.string.error_sign_in_again)
    is ErrorKind.Rejected -> stringResource(ruleRes)
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
primary action (here the FAB) in the bottom zone. Insets via `Scaffold`. Full display is
signalled with `ReportDrawnWhen` where content is genuinely present
(`spec/android/perceived-performance/` §A); the loading state honours the 200 ms rule
(`spec/android/ui-components/` §A) through the indicator in section 4.

```kotlin
@Composable
fun ExampleContent(
    uiState: ExampleUiState,
    onItemClick: (String) -> Unit,
    onCreate: () -> Unit,
    onRetry: () -> Unit,
    modifier: Modifier = Modifier,
) {
    // TTFD: content is "fully drawn" only when real data (or a terminal state) is on screen.
    ReportDrawnWhen { uiState !is ExampleUiState.Loading }

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
                    DelayedLoadingIndicator(Modifier.align(Alignment.Center)) // ≥ 200 ms
                is ExampleUiState.Success ->
                    ExampleList(items = uiState.items, onItemClick = onItemClick)
                ExampleUiState.Empty ->
                    EmptyState( // onboarding moment + call-to-action, never a dead end
                        text = stringResource(R.string.example_empty_body),
                        actionLabel = stringResource(R.string.example_create_action),
                        onAction = onCreate,
                    )
                is ExampleUiState.Error ->
                    ErrorState( // names the problem + next step; localized, never the raw string
                        message = uiState.kind.message(),
                        onRetry = onRetry.takeIf { uiState.canRetry },
                    )
            }
        }
    }
}
```

## 4. Delayed loading indicator

Nothing below ~200 ms; one variant per process app-wide. Put this in the design-system package
so every screen shares it.

```kotlin
@Composable
fun DelayedLoadingIndicator(
    modifier: Modifier = Modifier,
    delayMillis: Long = 200,
) {
    var visible by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) {
        delay(delayMillis)
        visible = true
    }
    AnimatedVisibility(visible = visible, modifier = modifier) {
        CircularProgressIndicator() // indeterminate 200 ms–5 s; determinate beyond, if known
    }
}
```

## 5. Lazy list

Stable domain `key`, `contentType` where item shapes differ, a declared size on anything that
arrives asynchronously, no derivation inside the item body (`spec/android/long-list-scrolling/`
§A/§B). Hoist the `LazyListState` when a restored position matters.

```kotlin
@Composable
fun ExampleList(
    items: ImmutableList<ExampleItem>,
    onItemClick: (String) -> Unit,
    modifier: Modifier = Modifier,
    listState: LazyListState = rememberLazyListState(),
) {
    LazyColumn(state = listState, modifier = modifier.fillMaxSize()) {
        item(key = "header", contentType = "header") { ExampleHeader() }
        items(
            items = items,
            key = { it.id },                 // domain identity, never the index
            contentType = { "row" },         // required once a second shape exists
        ) { item ->
            ExampleRow(item = item, onClick = { onItemClick(item.id) })
        }
    }
}

@Composable
private fun ExampleRow(item: ExampleItem, onClick: () -> Unit) {
    ListItem(
        headlineContent = { Text(item.title) },
        supportingContent = item.subtitle?.let { { Text(it) } },
        leadingContent = {
            AsyncImage( // size declared before load; equals the loaded size
                model = item.thumbnailUrl,
                contentDescription = null,
                modifier = Modifier.size(56.dp),
            )
        },
        modifier = Modifier.clickable(onClick = onClick),
    )
}
```

Paging 3 note: with `LazyPagingItems`, key via `itemKey { it.id }`, type via
`itemContentType { "row" }`, render `refresh`/`append`/`prepend` load states as distinct rows
with retry, and give the placeholder row exactly the loaded row's height so a page arriving
never shifts content already on screen.

## 6. Adaptive list-detail variant

Use when the content is a collection-plus-detail relationship. Two panes on expanded, one
below, selection preserved across the boundary (`spec/android/screen-formats/` §C). Branch on
the window size class only for high-level structure, never on device type. The scaffold keeps
critical UI off a separating hinge on its own.

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

## 7. Form and submission variant

State-based fields with a touched flag, errors in text with semantics, a live region for
form-level status, IME insets, and the §G submission contract of
`spec/android/user-input-validation/`: one in-flight submission, values readable while pending,
rejection ≠ transport failure, no navigation before confirmation.

```kotlin
data class ExampleFormUiState(
    val name: FieldState = FieldState(),          // TextFieldState lives in the holder
    val email: FieldState = FieldState(),
    val submission: Submission = Submission.Idle,  // Idle | InFlight | Rejected(kind) | Failed(kind) | Confirmed
    val formErrors: ImmutableList<Int> = persistentListOf(), // error summary (res ids)
)

@Composable
fun ExampleFormContent(
    uiState: ExampleFormUiState,
    onFieldLeft: (Field) -> Unit,
    onSubmit: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val scrollState = rememberScrollState()
    val focusManager = LocalFocusManager.current
    val statusText = uiState.submission.statusText() // null while Idle

    Column(
        modifier
            .fillMaxSize()
            .verticalScroll(scrollState)
            .imePadding()                             // keyboard never covers field or error
            .padding(horizontal = 16.dp),
    ) {
        if (uiState.formErrors.isNotEmpty()) {         // summary in addition to per-field text
            ErrorSummary(uiState.formErrors)
        }
        FormTextField(
            state = uiState.name.text,
            label = stringResource(R.string.form_name_label),
            error = uiState.name.error?.let { stringResource(it) }, // only after first blur
            keyboardOptions = KeyboardOptions(
                keyboardType = KeyboardType.Text,
                capitalization = KeyboardCapitalization.Words,
                imeAction = ImeAction.Next,
            ),
            onKeyboardAction = { focusManager.moveFocus(FocusDirection.Down) },
            onFocusLost = { onFieldLeft(Field.Name) },
            contentType = ContentType.PersonFullName,
        )
        FormTextField(
            state = uiState.email.text,
            label = stringResource(R.string.form_email_label),
            error = uiState.email.error?.let { stringResource(it) },
            keyboardOptions = KeyboardOptions(
                keyboardType = KeyboardType.Email,
                autoCorrectEnabled = false,
                imeAction = ImeAction.Done,
            ),
            onKeyboardAction = { onSubmit() },
            onFocusLost = { onFieldLeft(Field.Email) },
            contentType = ContentType.EmailAddress,   // NewUsername/NewPassword on sign-up forms
        )
        Button(
            onClick = onSubmit,
            enabled = uiState.submission !is Submission.InFlight, // exactly one in flight
            // testTag is the recorded exception (test-automation §D): while in flight the button
            // carries no text semantics, so the in-flight test has nothing else to match on.
            modifier = Modifier
                .align(Alignment.End)
                .testTag("form_submit"),
        ) {
            if (uiState.submission is Submission.InFlight) {
                DelayedLoadingIndicator()             // pending state is visible
            } else {
                Text(stringResource(R.string.form_submit))
            }
        }
        if (statusText != null) {
            Text(                                     // rejection: "change X"; transport: "retry"
                text = statusText,
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
            )
        }
    }
}

@Composable
private fun FormTextField(
    state: TextFieldState,
    label: String,
    error: String?,
    keyboardOptions: KeyboardOptions,
    onKeyboardAction: () -> Unit,
    onFocusLost: () -> Unit,
    contentType: ContentType,
) {
    val bringIntoView = remember { BringIntoViewRequester() }
    val scope = rememberCoroutineScope()
    OutlinedTextField(                                // one variant per form
        state = state,
        label = { Text(label) },
        isError = error != null,
        supportingText = error?.let { { Text(it) } },   // error text replaces supporting text
        keyboardOptions = keyboardOptions,
        onKeyboardAction = { onKeyboardAction() },
        modifier = Modifier
            .fillMaxWidth()
            .bringIntoViewRequester(bringIntoView)
            .onFocusChanged { focus ->
                if (focus.isFocused) scope.launch { bringIntoView.bringIntoView() }
                else onFocusLost()
            }
            .semantics {
                this.contentType = contentType
                if (error != null) this.error(error)
            },
    )
}
```

The route composable navigates only on `Submission.Confirmed` (in a `LaunchedEffect` keyed on
the state, never during composition); the ViewModel ignores `submit()` while `InFlight`, keeps
every `TextFieldState` untouched on `Rejected`/`Failed`, and maps a field-identified rejection
onto that field's `error`.

## 8. Navigation key and entry

Keys are `@Serializable` and implement `NavKey`; the back stack is app state
(`spec/android/app-design-navigation/` §B). A top-level destination owns its own back stack;
a deep-linkable key is parsed from the intent into this typed key and pushed on top of a
synthetic parent stack (§E).

One key class per destination — `EntryProviderBuilder` rejects a second `entry<T>` for a class
it already holds, so list and detail never share a key type.

```kotlin
@Serializable
data object ExampleKey : NavKey                      // the list destination

@Serializable
data class ExampleDetailKey(val id: String) : NavKey // one detail destination per item

fun EntryProviderBuilder<NavKey>.exampleEntries(
    onItemClick: (String) -> Unit,
    onCreate: () -> Unit,
) {
    entry<ExampleKey> {
        ExampleRoute(onItemClick = onItemClick, onCreate = onCreate)
    }
    entry<ExampleDetailKey> { key ->
        ExampleDetailContent(id = key.id)
    }
}
```

## 9. Preview set

Previews target the stateless content composable, live next to it, and are named
`<Composable>Preview`. Cover every state plus size/font/locale variants
(`spec/android/localization/` §F, `spec/android/screen-formats/` §D). The multi-preview
annotations are `@PreviewScreenSizes` and `@PreviewFontScale` (singular).

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

@PreviewFontScale
@Composable
private fun ExampleContentFontScalePreview() {
    AppTheme { ExampleContent(ExampleUiState.Success(fakeItems), {}, {}, {}) }
}

@Preview(name = "German", locale = "de")
@Preview(name = "RTL", locale = "ar")
@Composable
private fun ExampleContentLocalePreview() {
    AppTheme { ExampleContent(ExampleUiState.Success(fakeItems), {}, {}, {}) }
}
```
