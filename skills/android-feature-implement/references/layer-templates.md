# Layer templates

Kotlin shapes for the data layer, sync, and state holder of a flat, server-authoritative
client. Templates, not law: `spec/android/app-architecture/`, `spec/android/backend-contract/`,
and `spec/android/project-structure/` remain authoritative, and package names, module layout,
and DI wiring follow the target project.

## Contents

1. [The closed failure type](#1-the-closed-failure-type)
2. [Mapping a call onto it](#2-mapping-a-call-onto-it)
3. [Repository — replica plus revalidation](#3-repository--replica-plus-revalidation)
4. [Queued write and sync worker](#4-queued-write-and-sync-worker)
5. [ViewModel and screen state](#5-viewmodel-and-screen-state)
6. [Fakes for the failure set](#6-fakes-for-the-failure-set)

## 1. The closed failure type

Eight cases, exhaustive `when`, no generic branch. Lives in the network component and is mapped
to UI states by the ViewModel.

```kotlin
sealed interface CallResult<out T> {
    data class Success<T>(val value: T) : CallResult<T>
    sealed interface Failure : CallResult<Nothing> {
        data object Offline : Failure
        data object Timeout : Failure
        data object Unauthenticated : Failure
        data object Unauthorized : Failure
        /** The request was understood and refused on a business rule. */
        data class DomainRejection(
            val problemType: String?,
            val fieldErrors: Map<String, String> = emptyMap(),
        ) : Failure
        data class ServerFault(val status: Int) : Failure
        /** The response did not match the contract — a defect, not a runtime hiccup. */
        data class ContractMismatch(val endpoint: String, val detail: String) : Failure
    }
}
```

## 2. Mapping a call onto it

Every network call goes through one mapper, so no call site invents its own classification.
Nothing here logs a body, a header, or a payload.

```kotlin
suspend fun <T> apiCall(endpoint: String, block: suspend () -> T): CallResult<T> = try {
    CallResult.Success(block())
} catch (e: UnknownHostException) {
    CallResult.Failure.Offline
} catch (e: ConnectException) {
    CallResult.Failure.Offline
} catch (e: SocketTimeoutException) {
    CallResult.Failure.Timeout
} catch (e: SerializationException) {
    CallResult.Failure.ContractMismatch(endpoint, e.messageWithoutPayload())
} catch (e: HttpException) {
    when (e.code()) {
        401 -> CallResult.Failure.Unauthenticated
        403 -> CallResult.Failure.Unauthorized
        in 400..499 -> e.toDomainRejection()          // reads `type` + extensions, never `detail`
        else -> CallResult.Failure.ServerFault(e.code())
    }
}
```

- `toDomainRejection()` parses `application/problem+json` per RFC 9457: branch on `type` and on
  defined extension members only. `detail` is display text, never control flow.
- `messageWithoutPayload()` keeps the field path and drops the body — a mismatch is reported
  with endpoint and field, never with data.
- Retrofit `Response<T>` users check `isSuccessful` first and map `errorBody()` through the same
  path; Ktor users catch `ClientRequestException`/`ServerResponseException` equivalently.

## 3. Repository — replica plus revalidation

Reads come from the replica and never wait on the network. Freshness metadata is stored with
the data so staleness is displayable and revalidation decidable.

```kotlin
class DefaultObservationRepository @Inject constructor(
    private val local: ObservationLocalDataSource,
    private val remote: ObservationRemoteDataSource,
    private val clock: Clock,
    @Dispatcher(IO) private val io: CoroutineDispatcher,
) : ObservationRepository {

    override fun observationsStream(): Flow<CachedData<List<Observation>>> =
        local.observationsStream()
            .map { entities ->
                CachedData(
                    value = entities.map(ObservationEntity::asExternalModel),
                    fetchedAt = entities.minOfOrNull { it.fetchedAt },
                    isStale = entities.isStaleAt(clock.now(), STALENESS_WINDOW),
                )
            }
            .catch { emit(CachedData.empty()) }          // a local failure never cancels the UI
            .flowOn(io)

    /** Revalidate against the backend; the replica stays readable throughout. */
    override suspend fun refresh(): CallResult<Unit> = withContext(io) {
        when (val result = remote.fetchObservations(since = local.syncToken())) {
            is CallResult.Success -> {
                local.upsert(result.value.map { it.asEntity(fetchedAt = clock.now()) })
                local.setSyncToken(result.value.syncToken)
                CallResult.Success(Unit)
            }
            is CallResult.Failure -> result               // caller decides what the UI shows
        }
    }

    private companion object { val STALENESS_WINDOW = 15.minutes }
}
```

`CachedData<T>` carries `value`, `fetchedAt`, and `isStale`; it is what makes the stale state
in §5 expressible at all. Declare `STALENESS_WINDOW` per data type and record it with the
feature.

## 4. Queued write and sync worker

Only for **queued** or **local-first** writes. An online-only write is a plain `suspend`
function returning `CallResult`, with the affordance disabled while offline.

```kotlin
@Entity
data class PendingWrite(
    @PrimaryKey val id: String,                  // also the Idempotency-Key: stable across retries
    val payload: String,
    val createdAt: Instant,
    val lastError: String? = null,
)

@HiltWorker
class ObservationSyncWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted params: WorkerParameters,
    private val repository: ObservationRepository,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result = when (val outcome = repository.drainPendingWrites()) {
        is CallResult.Success -> Result.success()
        CallResult.Failure.Offline, CallResult.Failure.Timeout -> Result.retry()
        is CallResult.Failure.ServerFault -> Result.retry()
        else -> Result.failure()                  // rejected or unauthorized: surface, don't loop
    }
}

fun enqueueSync(context: Context) = WorkManager.getInstance(context).enqueueUniqueWork(
    SYNC_WORK_NAME,
    ExistingWorkPolicy.KEEP,
    OneTimeWorkRequestBuilder<ObservationSyncWorker>()
        .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
        .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
        .build(),
)
```

- The row id doubles as the idempotency key so a retry after process death is still the *same*
  logical write. Without backend support for `Idempotency-Key`, automatic retry of a
  non-idempotent write is forbidden — raise the requirement instead.
- A `Result.failure()` path must leave the pending row visible and actionable in the UI, with
  `lastError` mapped to a user-facing state. Deleting the row silently is a lost write.

## 5. ViewModel and screen state

```kotlin
sealed interface ObservationsUiState {
    data object Loading : ObservationsUiState
    data class Content(
        val items: ImmutableList<ObservationUi>,
        val lastUpdated: Instant?,
        val isStale: Boolean,
        val pendingCount: Int,
        val banner: Banner? = null,        // recoverable failure over existing content
    ) : ObservationsUiState
    data object Empty : ObservationsUiState
    data class Error(val kind: ErrorKind, val onRetry: Boolean = true) : ObservationsUiState
}

@HiltViewModel
class ObservationsViewModel @Inject constructor(
    private val repository: ObservationRepository,
    private val savedState: SavedStateHandle,
) : ViewModel() {

    val uiState: StateFlow<ObservationsUiState> =
        combine(repository.observationsStream(), repository.pendingWritesStream(), ::toUiState)
            .stateIn(
                scope = viewModelScope,
                started = SharingStarted.WhileSubscribed(5_000),
                initialValue = ObservationsUiState.Loading,
            )

    fun onRefresh() {
        viewModelScope.launch {
            when (val result = repository.refresh()) {
                is CallResult.Success -> Unit                  // the replica emits the new state
                is CallResult.Failure -> _banner.value = result.toBanner()
            }
        }
    }
}
```

- One `uiState`, no event channel: `onRefresh()`'s outcome becomes state.
- `Content` carries `isStale`, `lastUpdated`, and `pendingCount` — the three signals a flat
  client owes the user. A screen that can be served from cache and cannot say so is
  non-conformant.
- A failure over *existing* content is a banner inside `Content`, not a full-screen `Error`;
  replacing readable cached data with an error screen throws away the point of the replica.
- The UI composable itself is authored by the `android-compose-ui` skill against this state.

## 6. Fakes for the failure set

One fake per remote data source, able to produce every case from §1 — this is what makes the
§7 coverage floor of `references/flat-layer-checklist.md` reachable.

```kotlin
class FakeObservationRemoteDataSource : ObservationRemoteDataSource {
    var nextResult: CallResult<List<NetworkObservation>> = CallResult.Success(emptyList())
    override suspend fun fetchObservations(since: String?) = nextResult
}
```

Drive time with an injected `Clock` (`kotlinx.datetime` or a project-owned interface) and
coroutines with `kotlinx-coroutines-test`; a test that sleeps to observe staleness is a design
defect, not a slow test.
