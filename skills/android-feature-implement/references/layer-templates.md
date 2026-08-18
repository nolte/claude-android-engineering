# Layer templates

Kotlin shapes for the data layer, sync, delivery path, state holder, and tests of a flat,
server-authoritative client. Templates, not law: `spec/android/app-architecture/`,
`spec/android/backend-contract/`, `spec/android/notifications-alerting/` §E,
`spec/android/security/` §D, `spec/android/test-automation/` §B, and
`spec/android/project-structure/` remain authoritative, and package names, module layout, and DI
wiring follow the target project. Where a template fixes a value the specs leave open (the
`ExistingWorkPolicy`, the staleness window, the clock type, the HTTP-status mapping) the
surrounding note says so and names it a **recorded default** to be written into the feature
record — or a proposed spec extension (REQ-6).

## Contents

1. [The closed failure type](#1-the-closed-failure-type)
2. [Mapping a call onto it](#2-mapping-a-call-onto-it)
3. [Repository — replica plus revalidation](#3-repository--replica-plus-revalidation)
4. [Queued write and sync worker](#4-queued-write-and-sync-worker)
5. [Delivery path — push reception and scheduled work](#5-delivery-path--push-reception-and-scheduled-work)
6. [ViewModel and screen state](#6-viewmodel-and-screen-state)
7. [Fakes and test rules](#7-fakes-and-test-rules)

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
            /** What the client does about it — set by the status mapping in §2, never by the UI. */
            val kind: RejectionKind = RejectionKind.Rule,
        ) : Failure
        /** `retryAfter` is set when the backend asked for a specific wait (429 / 503). */
        data class ServerFault(val status: Int, val retryAfter: Duration? = null) : Failure
        /** The response did not match the contract — a defect, not a runtime hiccup. */
        data class ContractMismatch(val endpoint: String, val detail: String) : Failure
    }
}

enum class RejectionKind { Rule, ReplicaCleanup, Conflict, UpgradeRequired }
```

## 2. Mapping a call onto it

Every network call goes through one mapper, so no call site invents its own classification.
Nothing here logs a body, a header, or a payload.

```kotlin
suspend fun <T> apiCall(
    endpoint: String,
    notModified: T? = null,                           // set only by conditional requests (§C)
    block: suspend () -> T,
): CallResult<T> = try {
    CallResult.Success(block())
} catch (e: SocketTimeoutException) {                 // before IOException: it is a subclass
    CallResult.Failure.Timeout
} catch (e: SerializationException) {
    CallResult.Failure.ContractMismatch(endpoint, e.messageWithoutPayload())
} catch (e: HttpException) {
    when (val code = e.code()) {
        304 -> notModified?.let { CallResult.Success(it) }        // replica fresh, no body (§B)
            ?: CallResult.Failure.ContractMismatch(endpoint, "304 on an unconditional request")
        401 -> CallResult.Failure.Unauthenticated
        403 -> e.toForbiddenResult()                  // unauthorized vs. domain rejection, below
        408 -> CallResult.Failure.Timeout
        429 -> CallResult.Failure.ServerFault(code, e.retryAfter())
        404, 410 -> e.toDomainRejection(RejectionKind.ReplicaCleanup) // gone: remove/mark the local row
        409, 412 -> e.toDomainRejection(RejectionKind.Conflict)       // the backend's conflict answer
        426 -> e.toDomainRejection(RejectionKind.UpgradeRequired)     // or the contract's problem `type`, below
        in 400..499 -> e.toDomainRejection()                          // `type` + extensions, never `detail`;
                                                                      // an upgrade-required `type` → UpgradeRequired
        in 500..599 -> CallResult.Failure.ServerFault(code, e.retryAfter())
        else -> CallResult.Failure.ContractMismatch(endpoint, "unexpected status $code")
    }
} catch (e: IOException) {                            // UnknownHost, Connect, SocketException,
    CallResult.Failure.Offline                        // SSLHandshake, connection reset, …
}
```

- **The trailing `IOException` branch closes the set.** Without it, a mid-response connection
  reset or a TLS handshake failure escapes the mapper and surfaces as an unhandled exception in
  `viewModelScope` or a worker — the generic-error hole §B exists to prevent. Order matters:
  `SocketTimeoutException` is an `IOException`, so it is caught first.
- **`CancellationException` is deliberately not caught.** It is not an `IOException` and matches
  no branch above, so it propagates as structured concurrency requires. A bare
  `catch (e: Exception)` would swallow it and turn a navigated-away screen into a spurious error.
- `toForbiddenResult()` implements the §B boundary: a `403` whose problem `type` names a business
  rule is a **domain rejection**; a `403` that means "not you" is **unauthorized**. Where the
  contract distinguishes neither, that is a §E trigger — the mapper does not guess.
- `retryAfter()` reads the `Retry-After` header. §B requires honouring it over the client's own
  backoff, which is why it rides on `ServerFault` instead of being dropped here.
- `toDomainRejection()` parses `application/problem+json` per RFC 9457: branch on `type` and on
  defined extension members only. `detail` is display text, never control flow.
- **The status lines apply the §B table of `spec/android/backend-contract/`**, not a skill
  invention: `304` is success without a body (the conditional caller passes a `notModified`
  marker value — e.g. `ObservationPage.NotModified` — the repository branches on to refresh
  the freshness metadata and rewrite nothing), `404`/`410` on
  a resource the replica holds is a rejection whose answer is replica cleanup (a `404` for a
  documented endpoint is a contract mismatch), `412` is a rejection carrying a conflict
  (re-fetch, never retry the stale validator), "app version unsupported" — `426` *or* the
  problem `type` the contract defines for it — blocks on *update the app*, and every unmapped
  `4xx` is a domain rejection. **Skill refinement:** `409` is mapped to the same conflict shape
  as `412`; §B lists it only among the generic domain rejections, so record that choice with the
  feature. The `ReplicaCleanup`/`Conflict`/`UpgradeRequired` markers ride on `DomainRejection`
  as its `kind` so the repository can act without re-reading a status code.
- **`304` is caught before the generic ranges because Retrofit throws `HttpException` for it**
  (and `Response<T>.isSuccessful` is `false` for it): without its own branch a conditional
  refresh reports a fresh replica as a `ContractMismatch`. Retrofit `Response<T>` users add the
  `304 -> Success(notModified)` branch *before* the `isSuccessful` check.
- **A status outside `304`/`4xx`/`5xx` is a contract mismatch**, not "some server fault": any
  other `3xx` that reached the mapper (redirects are followed by the client) or a `1xx` means
  the client stack and the contract disagree.
- `messageWithoutPayload()` keeps the field path and drops the body — a mismatch is reported
  with endpoint and field, never with data.
- Retrofit `Response<T>` users check `isSuccessful` first and map `errorBody()` through the same
  path; Ktor users catch `ClientRequestException`/`ServerResponseException` equivalently.

**Transport configuration.** The mapper sees only what OkHttp lets through: with
`retryOnConnectionFailure` (default `true`) OkHttp silently re-sends a request — body included —
on a stale pooled connection, an unreachable address, a `408`, or a `401`/`407` the
`Authenticator` satisfies. Behind a non-idempotent write without an honoured idempotency key
that is a duplicate write in disguise (`spec/android/backend-contract/` §C), so either the
client disables it or the write's body is one-shot; the choice is recorded with the feature.

```kotlin
val okHttp = OkHttpClient.Builder()
    .connectTimeout(10.seconds.toJavaDuration())   // explicit, never the platform default (§C)
    .readTimeout(20.seconds.toJavaDuration())
    .callTimeout(30.seconds.toJavaDuration())
    .retryOnConnectionFailure(false)               // recorded: no transparent re-send of writes;
    .build()                                        // idempotent GETs retry via the §C policy instead

// Alternative when the shared client must keep the default: mark write bodies one-shot.
class OneShotBody(private val delegate: RequestBody) : RequestBody() {
    override fun contentType() = delegate.contentType()
    override fun contentLength() = delegate.contentLength()
    override fun isOneShot() = true                 // OkHttp will not retransmit it
    override fun writeTo(sink: BufferedSink) = delegate.writeTo(sink)
}
```

## 3. Repository — replica plus revalidation

Reads come from the replica and never wait on the network. Freshness metadata is stored with
the data so staleness is displayable and revalidation decidable.

```kotlin
/** The remote envelope: the page plus the validator that makes the next call conditional. */
data class ObservationPage(
    val items: List<NetworkObservation>,
    val syncToken: String?,
)

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
                val page = result.value                  // ObservationPage, not a bare List
                local.upsert(page.items.map { it.asEntity(fetchedAt = clock.now()) })
                local.setSyncToken(page.syncToken)
                CallResult.Success(Unit)
            }
            is CallResult.Failure -> result               // caller decides what the UI shows
        }
    }

    private companion object {
        // Placeholder, not a policy: the window is a step-3 decision per data type
        // (`spec/android/app-architecture/` §C) and is recorded with the feature.
        val STALENESS_WINDOW = 15.minutes
    }
}
```

`CachedData<T>` carries `value`, `fetchedAt`, and `isStale`; it is what makes the stale state
in §6 expressible at all. Declare `STALENESS_WINDOW` per data type and record it with the
feature — the `15.minutes` above is a template placeholder, not a default the spec sets.

The `Clock` is `kotlinx.datetime.Clock` (or a project-owned interface with the same shape) —
a **recorded default**: `spec/android/app-architecture/` §E requires injected time and
dispatchers but names no clock type; a Kotlin-first project reaches for `kotlinx.datetime`
because it is what `Instant` in Room converters and in tests already uses. `java.time.Clock`
is acceptable where the project standardised on it; note the choice in the feature record.

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

    override suspend fun doWork(): Result {
        val overdue = repository.oldestPendingWriteAge() > DEADLINE
        if (runAttemptCount >= MAX_ATTEMPTS || overdue) { // stated maximum and deadline, not "until WorkManager gives up"
            repository.blockPendingWrites(PendingWriteBlock.RetryExhausted)
            return Result.failure()
        }
        return when (val outcome = repository.drainPendingWrites()) {
            is CallResult.Success -> Result.success()
            CallResult.Failure.Offline, CallResult.Failure.Timeout -> Result.retry()
            is CallResult.Failure.ServerFault -> Result.retry()   // Retry-After already honoured inside the drain
            CallResult.Failure.Unauthenticated -> {
                // The drain already attempted the single-flight refresh and it did not help.
                // Retrying without a fresh credential would loop; failing silently would strand
                // every queued write. Mark them so the UI can raise the sign-in prompt.
                repository.blockPendingWrites(PendingWriteBlock.NeedsSignIn)
                Result.failure()
            }
            is CallResult.Failure.ContractMismatch -> {
                // Not "rejected": the backend deviated from its own contract. Surface it as a
                // defect (endpoint + field, never payload) and raise the §E trigger; the rows
                // stay visible and unsent, they are not the user's fault.
                repository.blockPendingWrites(PendingWriteBlock.ContractDefect(outcome.endpoint))
                Result.failure()
            }
            CallResult.Failure.Unauthorized, is CallResult.Failure.DomainRejection -> {
                repository.blockPendingWrites(PendingWriteBlock.Rejected)   // surface, don't loop
                Result.failure()
            }
        }
    }

    private companion object {
        const val MAX_ATTEMPTS = 6                    // recorded per feature (§C)
        val DEADLINE = 6.hours                        // overall deadline: reported as failed past it (§C)
    }
}

/**
 * Inside the drain: `Result.retry()` cannot carry a per-attempt delay, so a `Retry-After`
 * the backend sent (429 / 503) is honoured *here* — before the next request in the same
 * run — and does not count against `MAX_ATTEMPTS`. Every other transient failure uses the
 * request's own backoff (below).
 */
// In DefaultObservationRepository:
override suspend fun drainPendingWrites(): CallResult<Unit> = withContext(io) {
    for (write in local.pendingWrites()) {
        var attempt = 0
        while (true) {
            when (val result = send(write)) {
                is CallResult.Success -> break
                is CallResult.Failure.ServerFault -> {
                    val wait = result.retryAfter
                    if (wait != null && attempt < 1) { attempt++; delay(wait); continue }
                    return@withContext result           // let the worker back off
                }
                is CallResult.Failure -> return@withContext result
            }
        }
        local.markSent(write.id)
    }
    CallResult.Success(Unit)
}

fun enqueueSync(context: Context) = WorkManager.getInstance(context).enqueueUniqueWork(
    SYNC_WORK_NAME,
    // APPEND_OR_REPLACE, never KEEP: with KEEP, a write made while the worker is already
    // running is a no-op enqueue, and the running drain has already read the queue — that
    // write then waits for an unrelated later enqueue. A silently stranded write violates
    // `spec/android/app-architecture/` §D.
    ExistingWorkPolicy.APPEND_OR_REPLACE,
    OneTimeWorkRequestBuilder<ObservationSyncWorker>()
        .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
        // Capped exponential backoff plus jitter (§C): WorkManager doubles from the initial
        // delay and caps at WorkRequest.MAX_BACKOFF_MILLIS (5 h) but adds no jitter of its
        // own — the random component on the initial delay supplies it, so a fleet of devices
        // does not retry in lockstep. MAX_ATTEMPTS in the worker states the maximum.
        .setBackoffCriteria(
            BackoffPolicy.EXPONENTIAL, 30_000L + Random.nextLong(0, 15_000L), TimeUnit.MILLISECONDS,
        )
        .build(),
)
```

- **`APPEND_OR_REPLACE` is a recorded default**, not a spec rule: `spec/android/app-architecture/`
  §D requires that no write is stranded and names WorkManager unique work, but does not pick
  the `ExistingWorkPolicy`. Record the choice with the feature; if the project already runs a
  chained sync graph, `APPEND` may be right, and that is a documented deviation.
- **Backoff, jitter, maximum, and deadline are four settings, not one.** `BackoffPolicy.EXPONENTIAL`
  supplies growth and the cap, the randomised initial delay supplies jitter, `MAX_ATTEMPTS`
  supplies the stated maximum, and `DEADLINE` the overall deadline after which the write is
  reported as failed — all four §C requires and all recorded with the feature. Leaving the
  maximum or the deadline to WorkManager's implicit behaviour is not a stated policy.

- The row id doubles as the idempotency key so a retry after process death is still the *same*
  logical write. Without backend support for `Idempotency-Key`, automatic retry of a
  non-idempotent write is forbidden — raise the requirement instead.
- A `Result.failure()` path must leave the pending row visible and actionable in the UI, with
  `lastError` mapped to a user-facing state. Deleting the row silently is a lost write.
- **`ContractMismatch` has its own branch**, never the `else`. Folding it into "rejected" tells
  the user their write was refused when in fact the backend broke its contract; the branch
  surfaces a contract defect and is the §E trigger of `spec/android/backend-contract/`.

## 5. Delivery path — push reception and scheduled work

The delivery path is data-layer work owned by this skill (`spec/android/notifications-alerting/`
§E); the channel and the notification's construction come from `android-notification-derive`
and its ledger row. Nothing below is written without that row.

**Pushed** — the service only enqueues. It reads the data payload, hands the work to
WorkManager, and returns inside its execution window; it never fetches, writes the replica, or
posts a notification. It is a framework entry point and is not unit-tested; the worker's
repository call is.

```kotlin
class AppMessagingService : FirebaseMessagingService() {

    override fun onMessageReceived(message: RemoteMessage) {
        // Data message: the app controls channel, grouping, localisation, styling (§E).
        // A notification message would have been rendered by the SDK without this code.
        val eventKey = message.data["event"] ?: return          // unknown shape: ignore, don't crash
        val request = OneTimeWorkRequestBuilder<PushSyncWorker>()
            .setInputData(workDataOf(KEY_EVENT to eventKey, KEY_REF to message.data["ref"]))
            .apply {
                // Expedited only for what the server sent as priority: high — i.e. what will
                // produce a user-visible notification. Sync-only pushes stay ordinary.
                if (message.priority == RemoteMessage.PRIORITY_HIGH) {
                    setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
                }
            }
            .build()
        WorkManager.getInstance(this).enqueueUniqueWork(
            "push-$eventKey-${message.data["ref"]}", ExistingWorkPolicy.KEEP, request,
        )
    }

    override fun onNewToken(token: String) {
        // Token rotation = a window in which pushes may have been lost. Register the new
        // token and run the missed-message sync; the replica, not the push, is the truth.
        WorkManager.getInstance(this).enqueueUniqueWork(
            SYNC_WORK_NAME, ExistingWorkPolicy.APPEND_OR_REPLACE,
            OneTimeWorkRequestBuilder<TokenRefreshAndSyncWorker>()
                .setInputData(workDataOf(KEY_TOKEN to token)).build(),
        )
    }
}
```

```xml
<!-- Manifest: the messaging service must be exported=false and carry the FCM intent filter;
     it is the only component that receives, everything else runs in WorkManager. -->
<service
    android:name=".push.AppMessagingService"
    android:exported="false">
    <intent-filter>
        <action android:name="com.google.firebase.MESSAGING_EVENT" />
    </intent-filter>
</service>
```

```kotlin
@HiltWorker
class PushSyncWorker @AssistedInject constructor(
    @Assisted context: Context, @Assisted params: WorkerParameters,
    private val repository: ObservationRepository,
    private val notifier: ObservationNotifier,      // built by android-notification-derive
) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = when (val r = repository.refresh()) {
        is CallResult.Success -> {
            notifier.notifyIfRowSaysSo(inputData.getString(KEY_EVENT))   // ledger row decides
            Result.success()
        }
        CallResult.Failure.Offline, CallResult.Failure.Timeout,
        is CallResult.Failure.ServerFault -> Result.retry()
        is CallResult.Failure -> Result.failure()    // surfaced by the repository's own mapping
    }
}
```

**Missed-message sync on foreground** — FCM stores a bounded backlog and may discard it; the
push is a hint. Trigger the same reconciliation entry point (§4's `enqueueSync`, or the
repository's `refresh()`) from a process-lifecycle observer, so a message lost while the app was
killed is caught the next time the user comes back:

```kotlin
class ForegroundSyncObserver @Inject constructor(private val enqueue: () -> Unit) :
    DefaultLifecycleObserver {
    override fun onStart(owner: LifecycleOwner) = enqueue()   // ProcessLifecycleOwner
}
```

**Scheduled** — WorkManager for anything deferrable; `AlarmManager` only where the time itself
is what the user cares about (their reminder), and only after `android-permissions-derive`
handled the exact-alarm permission:

```kotlin
// Deferrable: the platform picks the moment within the window (Doze-aware).
WorkManager.getInstance(context).enqueueUniquePeriodicWork(
    "digest", ExistingPeriodicWorkPolicy.UPDATE,
    PeriodicWorkRequestBuilder<DigestWorker>(24, TimeUnit.HOURS).build(),
)

// The time IS the point (user-set reminder) — exact alarm, permission derived elsewhere.
alarmManager.setExactAndAllowWhileIdle(
    AlarmManager.RTC_WAKEUP, triggerAtMillis,
    PendingIntent.getBroadcast(
        context, requestCode,
        Intent(context, ReminderReceiver::class.java).setPackage(context.packageName), // explicit
        PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
    ),
)
```

**Tap path** — the `PendingIntent` targets the destination activity directly, immutable and
explicit; no service or receiver trampoline (blocked from Android 12), a deep link with a
synthetic back stack (`spec/android/security/` §D, `spec/android/notifications-alerting/` §E):

```kotlin
val tap = TaskStackBuilder.create(context).run {
    addNextIntentWithParentStack(
        Intent(context, MainActivity::class.java)              // explicit
            .setAction(Intent.ACTION_VIEW)
            .setData("app://observations/$id".toUri()),         // validated in the activity by exact scheme+host
    )
    getPendingIntent(requestCode, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
}
```

- `ReminderReceiver` and any other component added here declares `android:exported="false"`;
  a receiver that must be exported is permission-protected and validates every extra.
- `priority: high` on the server side is paired with a visible notification on the device;
  a high-priority push that only syncs is deprioritised by FCM over time — that is a backend
  requirement conversation (`spec/android/backend-contract/` §E), not a client workaround.
- The service, the receiver, and `doWork()` shells are framework entry points: no unit test
  targets them (`spec/android/test-automation/` §B); the repository and notifier behind them are
  tested through §7's fakes.

## 6. ViewModel and screen state

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

    /** The refresh outcome is state, so it has to be one of the flows uiState is built from. */
    private val banner = MutableStateFlow<Banner?>(null)

    val uiState: StateFlow<ObservationsUiState> =
        combine(
            repository.observationsStream(),
            repository.pendingWritesStream(),
            banner,
            ::toUiState,
        )
            .stateIn(
                scope = viewModelScope,
                started = SharingStarted.WhileSubscribed(5_000),
                initialValue = ObservationsUiState.Loading,
            )

    fun onRefresh() {
        viewModelScope.launch {
            when (val result = repository.refresh()) {
                is CallResult.Success -> banner.value = null   // the replica emits the new state
                is CallResult.Failure -> banner.value = result.toBanner()
            }
        }
    }

    fun onBannerDismissed() { banner.value = null }
}
```

- One `uiState`, no event channel: `onRefresh()`'s outcome becomes state. The banner flow is
  part of the `combine` for exactly that reason — a `MutableStateFlow` the state is *not* built
  from is an event channel with extra steps, and its updates never reach the screen.
- `Content` carries `isStale`, `lastUpdated`, and `pendingCount` — the three signals a flat
  client owes the user. A screen that can be served from cache and cannot say so is
  non-conformant.
- A failure over *existing* content is a banner inside `Content`, not a full-screen `Error`;
  replacing readable cached data with an error screen throws away the point of the replica.
- The UI composable itself is authored by the `android-compose-ui` skill against this state.

## 7. Fakes and test rules

One fake per remote data source, able to produce every case from §1 — this is what makes the
coverage floor of SKILL.md step 6 reachable.

```kotlin
class FakeObservationRemoteDataSource : ObservationRemoteDataSource {
    var nextResult: CallResult<ObservationPage> =
        CallResult.Success(ObservationPage(items = emptyList(), syncToken = null))

    override suspend fun fetchObservations(since: String?) = nextResult
}
```

Drive time with an injected `Clock` (`kotlinx.datetime` or a project-owned interface) and
coroutines with `kotlinx-coroutines-test`; a test that sleeps to observe staleness is a design
defect, not a slow test.

The mechanics `spec/android/test-automation/` §B fixes — JUnit 4, `runTest`, a
`MainDispatcherRule`, and a live collector before asserting on a `WhileSubscribed` state:

```kotlin
class MainDispatcherRule(
    private val dispatcher: TestDispatcher = UnconfinedTestDispatcher(),
) : TestWatcher() {
    override fun starting(description: Description) = Dispatchers.setMain(dispatcher)
    override fun finished(description: Description) = Dispatchers.resetMain()
}

class ObservationsViewModelTest {                       // JUnit 4; JUnit 5 is never assumed
    @get:Rule val mainDispatcherRule = MainDispatcherRule()

    private val remote = FakeObservationRemoteDataSource()
    private val repository = FakeObservationRepository(remote)

    @Test
    fun `offline refresh keeps content and shows a stale banner`() = runTest {
        val viewModel = ObservationsViewModel(repository, SavedStateHandle())
        // WhileSubscribed: without a collector, uiState.value stays Loading forever.
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.uiState.collect() }
        repository.seed(listOf(observation("1")))
        remote.nextResult = CallResult.Failure.Offline

        viewModel.onRefresh()
        advanceUntilIdle()                                // virtual time, never Thread.sleep

        val state = viewModel.uiState.value
        assertIs<ObservationsUiState.Content>(state)      // kotlin.test
        assertEquals(Banner.Offline, state.banner)
        assertTrue(state.isStale)
    }
}
```

- The rule and the collector are not optional ceremony: `stateIn(WhileSubscribed)` produces
  nothing until subscribed, and `viewModelScope` needs a Main dispatcher to exist.
- No Robolectric here — nothing above touches an Android class. If a test seems to need one,
  the logic is in the wrong layer.
- `AppMessagingService`, `ReminderReceiver`, and the worker shells (§4, §5) have no unit tests;
  the repository call they delegate to is what the fakes exercise.
