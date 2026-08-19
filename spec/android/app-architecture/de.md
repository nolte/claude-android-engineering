# App-Architektur — Der flache View Layer

Status: draft

## Kontext

Eine Android-App, die zu einem Backend gehört, hat eine architektonische Frage, die alle anderen überragt: *wer entscheidet*. Die Antwort, die dieser Korpus festlegt, ist das Backend — die App ist ein **flacher View Layer**. Sie stellt dar, was das Backend feststellt, sie nimmt entgegen, was Nutzende eingeben, und sie hält eine lokale Kopie, damit sie nutzbar bleibt, wenn das Netz es nicht ist. Sie leitet die Regeln des Backends nicht erneut her und wird keine zweite, still auseinanderlaufende Implementierung der Fachlichkeit.

Drei Dinge werden routinemäßig verwechselt und bleiben in dieser Spec durchgängig getrennt:

- **Autorität** — wer entscheidet, ob etwas wahr, erlaubt oder angenommen ist. Immer das Backend.
- **Wahrheitsquelle für die Darstellung** — was die UI beobachtet. Immer der lokale Speicher, denn ein Screen, der direkt aus dem Netz liest, hört in dem Moment auf zu funktionieren, in dem das Netz es tut.
- **Darstellung** — Compose, das überhaupt keine Entscheidung besitzt.

Eine App kann offlinefähig und trotzdem flach sein: Die lokale Datenbank ist ein *Replikat*, keine zweite Meinung. Der Fehlermodus, dessentwegen diese Spec existiert, ist die Drift, die mit einer harmlosen clientseitigen Regel beginnt („wir können schon jetzt sehen, dass diese Bestellung nicht zulässig ist") und mit einem Client endet, der dem Server vor den Augen der Nutzenden widerspricht.

Provenienz: Schreibtischrecherche (August 2026) über den offiziellen Android-Architekturleitfaden und seine gestuften Architekturempfehlungen (*Strongly recommended* / *Recommended* / *Optional*), den Offline-First-Leitfaden für den Data Layer, die Dokumentation zu ViewModel und lebenszyklusbewusstem Sammeln, die WorkManager-Leitlinien sowie die Referenzimplementierung Now in Android. Wo diese Spec von der offiziellen Leitlinie abweicht, sagt sie es und begründet es — siehe §A. Zitiertiefe: Jede Anforderung unten stützt sich auf Erstanbieter-Plattformdokumentation, die für die eigene API eines Herstellers die maßgebliche Quelle ist und nicht eine Stimme unter dreien; dieser Korpus wendet diese Konvention einheitlich an, und eine Anforderung, die auf weniger Gesichertem als ausgeliefertem, dokumentiertem Verhalten beruht, muss das an der Anforderung selbst sagen.

Grenzen: Der *strukturelle* Abdruck der Architektur — Modul- und Paketlayout, Benennung von Repositories und Datenquellen, Konstruktorinjektion und Hilt, der Route/Content-Split, die Testplatzierung — liegt in `spec/android/project-structure/` §C–§F und wird hier nicht wiederholt; jene Spec verweist das Laufzeitverhalten der Architektur ausdrücklich an eine eigene Spec, und das ist diese. Navigationsarchitektur und Zurück-Verhalten liegen in `spec/android/app-design-navigation/` §B/§D, Listen- und Paging-Verhalten in `spec/android/long-list-scrolling/`, alles zum Wire-Contract und zum Erheben einer Anforderung an das Backend in `spec/android/backend-contract/`, Speicher- und Datenschutzpflichten des Caches in `spec/android/security/` §A/§E, Testmechanik in `spec/android/test-automation/` und die Härtung des Release-Builds in `spec/android/release-readiness/`.

Leser: Autoren der Android-Skills dieses Repos, die ein Feature über die Schichten hinweg umsetzen, sowie Reviewer, die beurteilen, ob ein Feature den Client flach gehalten hat.

## Ziele

- Eine mechanische Regel dafür festlegen, was auf dem Gerät entschieden werden darf und was nicht
- Die App offline nutzbar machen, ohne die lokale Kopie zu einer zweiten Autorität werden zu lassen
- Jedem Screen ein Zustandsmodell geben, das *veraltet*, *ausstehend* und *abgelehnt* ausdrücken kann — die drei Zustände, denen ein flacher Client nicht ausweichen kann
- Den Fehlerpfad jedes Schreibvorgangs zu einem entworfenen Teil des Features machen statt zu einem Nachgedanken
- Die generierten Wire-Typen und die Speicher-Engine aus dem UI Layer heraushalten, damit beide austauschbar bleiben
- Jede Schicht auf der JVM testbar machen — ohne Gerät und ohne Backend
- Eine fehlende Backend-Fähigkeit in eine festgehaltene Anforderung überführen statt in einen clientseitigen Workaround

## Nicht-Ziele

- Modulgrenzen, Paketlayout, Benennungskonventionen, DI-Verdrahtung und der Route/Content-Split — `spec/android/project-structure/` §C–§F
- Navigationsgraphen, Zurück-Behandlung, Deep Links — `spec/android/app-design-navigation/` §B/§D/§E
- Paging-Mechanik, Item-Identität und Scroll-Kontinuität — `spec/android/long-list-scrolling/`
- Der HTTP-Contract, der generierte Client, Fehler-Nutzlastformate und das Backend-Anforderungsartefakt — `spec/android/backend-contract/`
- Verschlüsselung zwischengespeicherter Daten, Berechtigungspolitik und Log-Hygiene als Sicherheitspflichten — `spec/android/security/`
- Die Backend-Architektur selbst; diese Spec legt nur fest, was der Client von ihr verlangt
- Apps ganz ohne Backend — eine rein lokale App erbt §B, §C, §E und §G, §A/§D entfallen

## Anforderungen

### A. Die Flachheitsregel — was das Gerät entscheiden darf

- **MUSS [MUST]** das Backend als Autorität für jede fachliche Entscheidung behandeln: ob eine Eingabe annehmbar ist, ob eine Aktion erlaubt ist, welchen Wert ein Status, Preis, eine Berechtigung, ein Kontingent oder ein abgeleitetes Label hat und wann ein Ablauf weitergehen darf. Der Client stellt diese Antworten dar; er berechnet sie nicht
- **MUSS [MUST]** clienteigene Logik auf genau vier Klassen beschränken und **MUSS [MUST]** alles, was in keine davon passt, als Lücke gemäß `spec/android/backend-contract/` §E melden, statt still zu entscheiden:
  1. **Darstellung** — Abbildung von Backend-Daten auf das Gezeichnete, Formatierung, Sortieren und Filtern bereits gelieferter Daten für die Anzeige — *innerhalb* einer vollständig gelieferten Menge (eine vollständige Seite, eine vollständige Liste, die der Client hält); ein Sortieren oder Filtern, das den Client zum Over-Fetch zwänge oder Seiten umfassen müsste, die er nicht hält, ist `spec/android/backend-contract/` §E, keine Darstellung
  2. **Cache- und Sync-Politik** — was gespeichert wird, wann revalidiert wird, wie ein Schreibvorgang wiederholt wird
  3. **Gerätefähigkeit** — Kamera, Sensoren, Berechtigungen, Konnektivität, Dateizugriff, Hintergrundausführung
  4. **Navigation und UI-Zustand** — welcher Screen sichtbar ist, was ausgewählt, was aufgeklappt ist
- **MUSS [MUST]** die wiederkehrenden „Wo lebt das?"-Fälle in diesen Heimaten verorten, damit ein Skill die Zuordnung anwendet, statt sie still zu entscheiden:
  - **lokale Entwurfs- und Formularpersistenz** (ein ungesendetes Formular, ein halb getippter Eintrag) — Klasse 4, solange der Screen lebt, Klasse 2, sobald sie den Prozesstod überleben muss; lokal als *ungesendete Eingabe* gespeichert, nie als Fachdaten im Replikat, und gemäß der Prozesstod-Regel aus §B wiederhergestellt
  - **Feature-Flags und Remote-Config** — vom Backend gelieferte Werte, die der Client wie alle anderen Daten cacht (Klasse 2) und auf denen er für das Gezeichnete verzweigt (Klasse 1); ein Flag, dessen Wert über Berechtigung, Anspruch oder Preis entscheidet, ist eine fachliche Entscheidung, die das Backend auswertet und als *Ergebnis* liefert, keine Regel, die der Client auswertet
  - **Analytics und Telemetrie** — Erfassung, Bündelung und Versand sind Gerätefähigkeits-Arbeit (Klasse 3); der Client zeichnet Ereignisse auf, leitet nie eine Geschäftskennzahl auf dem Gerät ab, und die Datenschutzpflichten des Aufgezeichneten folgen `spec/android/security/` §E
  - **Client-Versions-Gating** („diese App ist zu alt") — eine Backend-Entscheidung, die auf der Leitung geliefert wird (`spec/android/backend-contract/` §B ordnet die Antwort „Version nicht unterstützt" zu); der Client stellt die Sperre und die Aktualisierungsaktion dar und vergleicht nie seine eigene Version gegen eine lokal gehaltene Regel
  - **Darstellungs- vs. Fach-Aggregate** — eine Fußzeilensumme, eine Anzahl oder ein „n von m" über die Elemente, die dem Screen *geliefert* wurden, ist Darstellung (Klasse 1); eine Gesamtsumme, ein Saldo oder eine Anzahl, die Daten umfasst, die der Client nicht hält, oder die eine Regel anpassen könnte (Rabatte, Kontingente), ist ein Fach-Aggregat, das der Client beim Backend erfragt
- **MUSS [MUST]** clientseitige Eingabeprüfungen als *reine Hilfestellung* behandeln — Pflichtfeldmarkierungen, Formathinweise, Tastaturtypen, Längengrenzen aus dem Contract. Hilfestellung **DARF NICHT [MUST NOT]** als Annahmeentscheidung dargestellt werden, und die Antwort des Servers **MUSS [MUST]** auch dann gewinnen, wenn der Client die Eingabe für gültig hielt
- **DARF NICHT [MUST NOT]** eine Backend-Regel „für eine schnellere UI" nachbauen, spiegeln oder vorberechnen; wird ein abgeleiteter Wert zur Darstellung gebraucht, fordert der Client das Feld an (`spec/android/backend-contract/` §E), statt es herzuleiten
- **DARF NICHT [MUST NOT]** eine lokal hergeleitete fachliche Entscheidung so persistieren, als wäre sie Backend-Wahrheit — ein vom Client berechneter Wert wird niemals unmarkiert neben servergelieferten Daten ins Replikat geschrieben
- **MUSS [MUST]** eine Server-Ablehnung als erstklassigen UI-Zustand modellieren, der benennt, was als Nächstes zu tun ist, niemals als rohe Exception in einem Dialog (Textregeln nach `spec/android/app-design-navigation/` §F)
- **Kalibrierte Abweichung:** Die offiziellen Architektur-*Empfehlungen* sagen — auf der Stufe *Strongly recommended* —, der Data Layer „contains the vast majority of your app's business logic" [R2], und der Architekturleitfaden rahmt die Schicht genauso [R1]. Diese Aussage adressiert Apps, denen die Fachlichkeit gehört. In diesem Korpus liegt die Fachlichkeit im Backend, also hält der Client-Data-Layer ausschließlich **Client**-Logik — Caching, Sync, Retry und Mapping. Die Schichtung des Leitfadens, seine SSOT- und UDF-Prinzipien sowie seine Empfehlungen werden unverändert übernommen; verengt wird allein die *Platzierung fachlicher Regeln*, und ein Skill **MUSS [MUST]** diese engere Regel anwenden

### B. UI Layer und Zustand

- **MUSS [MUST]** unidirektionalem Datenfluss folgen: Das ViewModel stellt Zustand über das Observer-Muster bereit und nimmt Nutzerabsicht als Methodenaufrufe entgegen [R2]
- **MUSS [MUST]** den Screen-Zustand als eine einzige `uiState`-Eigenschaft vom Typ `StateFlow` bereitstellen (mehrere Eigenschaften nur bei wirklich unzusammenhängenden Daten), erzeugt mit `stateIn(scope, SharingStarted.WhileSubscribed(5_000), initial)`, wenn er aus einem Data-Layer-Strom stammt, und ihn mit `collectAsStateWithLifecycle()` sammeln [R2]
- **DARF NICHT [MUST NOT]** Einmal-Ereignisse vom ViewModel an die UI senden; das Ereignis wird im ViewModel behandelt und sein Ergebnis wird Zustand [R2]
- **MUSS [MUST]** den Screen-Zustand so modellieren, dass er je Screen alles ausdrücken kann: **Laden**, **Inhalt**, **Fehler mit Wiederherstellungsaktion**, **Leer** und — weil der Client flach und offlinefähig ist — **Veraltung** (dieser Inhalt ist eine Kopie vom Alter *t*) sowie **ausstehender Schreibvorgang** (dieser Inhalt enthält eine vom Backend unbestätigte Änderung). Eine **Server-Ablehnung** ist eine Ausprägung des Fehlerzustands, kein eigener: Sie benennt die ablehnende Regel und den nächsten Schritt. Ein Screen, der aus dem Cache gezeigt werden kann, das aber nicht sagen kann, ist nicht konform
- **MUSS [MUST]** das ViewModel frei von `Activity`, `Context`, `Resources` und jedem lebenszyklusgebundenen Typ halten und **DARF NICHT [MUST NOT]** `AndroidViewModel` verwenden — eine kalibrierte Verschärfung: Die Empfehlungsseite führt „Do not use `AndroidViewModel`" auf der Stufe *Recommended*, und dieser Korpus hebt es auf MUSS, weil der flache Client jeden `Context`-abhängigen Wert im Composable auflöst [R2]; nutzersichtbarer Text wird im Composable aus String-Ressourcen aufgelöst, gemäß `spec/android/localization/` §A
- **MUSS [MUST]** ViewModels nur auf Screen-Ebene platzieren; wiederverwendbare Komponenten erhalten gehobenen Zustand und einfache State-Holder-Klassen [R2]
- **DARF NICHT [MUST NOT]** eine Entscheidung in ein Composable legen, die über die Auswahl des zu Zeichnenden aus dem übergebenen Zustand hinausgeht — kein Datenzugriff, keine Regelauswertung, kein Auslösen von Anfragen außerhalb eines Effects
- **MUSS [MUST]** lebenszyklusabhängige Arbeit mit lebenszyklusbewussten Effects (`LifecycleStartEffect`, `LifecycleResumeEffect`, `repeatOnLifecycle`) steuern statt mit überschriebenen `Activity`-Callbacks [R2]
- **MUSS [MUST]** Prozesstod überleben: Jeder Zustand, dessen Verlust Nutzende ärgern würde, wird aus `SavedStateHandle` (ViewModel) oder `rememberSaveable` (UI) wiederhergestellt, und der wiederhergestellte Screen **DARF NICHT [MUST NOT]** einen ungesendeten Schreibvorgang still verwerfen

### C. Data Layer — das Replikat, das die UI beobachtet

- **MUSS [MUST]** den UI Layer ausschließlich über Repositories lesen lassen; Composables und ViewModels berühren nie direkt eine Datenbank, DataStore, einen Netzwerkclient oder eine System-Datenquelle [R2]
- **MUSS [MUST]** den lokalen Speicher zur einzigen Wahrheitsquelle machen, die die UI beobachtet, und das Backend zur Autorität, gegen die abgeglichen wird; ein Repository-Lesevorgang **DARF NICHT [MUST NOT]** davon abhängen, dass ein Netzwerk-Roundtrip gelingt
- **MUSS [MUST]** drei Modellmengen trennen — Netzwerk-DTO, lokale Entity und das an den UI Layer gereichte Modell — mit Mapping-Funktionen an jeder Grenze [R3]; die generierten Wire-Typen **DÜRFEN NICHT [MUST NOT]** in der öffentlichen Signatur eines Repositories auftauchen
- **MUSS [MUST]** Lesevorgänge als `Flow` und Schreibvorgänge als `suspend`-Funktionen bereitstellen [R3]
- **MUSS [MUST]** zu jedem zwischengespeicherten Datentyp Frischemetadaten speichern (Abrufzeitpunkt sowie den Validator des Contracts — ETag, Version oder Sync-Token —, sofern vorhanden), denn ohne sie lässt sich Veraltung weder anzeigen noch revalidieren
- **MUSS [MUST]** je zwischengespeichertem Datentyp eine Veraltungspolitik festlegen, die drei Dinge benennt: das Revalidierungsfenster, ob veralteter Inhalt während der Revalidierung gezeigt wird, und was die UI nach hartem Ablauf zeigt. „Ewig cachen, nie sagen" ist nicht konform
- **MUSS [MUST]** alle nutzerbezogenen Cache-Daten bei Abmeldung und Kontowechsel löschen oder neu schlüsseln; die Speicherpflichten dieser Daten folgen `spec/android/security/` §A
- **SOLLTE [SHOULD]** den lokalen Speicher nach Form wählen: ein relationales oder abfragbares Replikat in Room, kleine skalare Einstellungen in DataStore, große Binärdaten als Dateien mit referenzierender Zeile — und **DARF NICHT [MUST NOT]** `SharedPreferences` für neuen Code verwenden
- **MUSS [MUST]** einen Lesefehler des lokalen Speichers durch Ausgeben eines sicheren Zustands behandeln (`catch` in einen Fehler- oder Leerzustand), niemals dadurch, dass die Exception das Sammeln in der UI abbricht [R3]

### D. Schreibvorgänge und Synchronisation

- **MUSS [MUST]** je Schreibvorgang genau eine von drei Strategien wählen und die Wahl beim Feature festhalten [R3]:
  - **Nur online** — der Schreibvorgang geht ans Backend und wird erst danach lokal abgebildet; offline ist die Bedienmöglichkeit mit begründetem Hinweis deaktiviert
  - **Eingereiht** — der Schreibvorgang wird lokal vermerkt und später abgearbeitet; Nutzende werden nicht blockiert, ein Fehlschlag ist tolerierbar
  - **Local-first (verzögert)** — der Schreibvorgang wird sofort auf das Replikat angewandt, eingereiht und beim Sync abgeglichen
- **MUSS [MUST]** **nur online** als Vorgabe für jeden Schreibvorgang setzen, dessen Annahme von einer Backend-Regel abhängt — was unter §A auf die meisten zutrifft. Local-first wird nur gewählt, wenn das Feature dessen Preis ausdrücklich zahlt: ein sichtbarer Ausstehend-Zustand, ein entworfener Rückbau bei Ablehnung durch das Backend und eine Konfliktantwort nach §D unten
- **MUSS [MUST]** eingereihte und local-first-Abarbeitungen mit WorkManager als Unique Work unter Konnektivitätsbedingung mit exponentiellem Backoff ausführen [R3] — die Untergrenze von WorkManager ist `WorkRequest.MIN_BACKOFF_MILLIS` (10 s; Default ist 30 s exponentiell), eine Abarbeitung wiederholt also nie schneller, und ein Schreibvorgang, der Wiederholung unter 10 Sekunden braucht, ist keine WorkManager-Arbeit, sondern eine In-Process-Wiederholung innerhalb von `spec/android/backend-contract/` §C [R9]; eine an `viewModelScope` gebundene Retry-Schleife ist für Arbeit, die den Screen überleben muss, nicht konform
- **MUSS [MUST]** jeden unbestätigten Schreibvorgang in der UI sichtbar machen (ausstehend) und jeden endgültig fehlgeschlagenen handlungsfähig machen (erneut versuchen, bearbeiten, verwerfen) — ein Schreibvorgang **DARF NICHT [MUST NOT]** still verworfen werden, und sein Fehlschlag **DARF NICHT [MUST NOT]** nur im Log gemeldet werden
- **MUSS [MUST]** die Konfliktauflösung vom Backend beziehen: Der Client sendet den Validator, den er hält (Version, ETag oder Zeitstempel), und stellt das Urteil des Backends dar. Der Client **DARF NICHT [MUST NOT]** ein Merge erfinden und **DARF NICHT [MUST NOT]** einen neueren Serverzustand still mit einem älteren lokalen überschreiben [R3]
- **MUSS [MUST]** jeden automatisch wiederholten Schreibvorgang auf der Leitung idempotenzsicher machen, gemäß `spec/android/backend-contract/` §C; bietet das Backend keinen solchen Mechanismus, ist automatisches Wiederholen dieses Schreibvorgangs verboten, bis die Anforderung erhoben und beantwortet ist
- **MUSS [MUST]** je synchronisiertem Datenbereich festlegen, was eine serverseitige Löschung und eine gebrochene Sync-Position mit dem Replikat tun, und beides in der Veraltungspolitik aus §C benennen: Ein `404`/`410` beim Refresh eines Elements, das das Replikat hält (`spec/android/backend-contract/` §B), entfernt oder tombstoned diese Zeile, und ihr Screen zeigt „nicht mehr verfügbar" statt eines Fehlers; ein Sync-Token oder Validator, den das Backend als unbekannt oder ungültig ablehnt, löst einen **vollständigen Resync** dieses Datenbereichs aus — das Replikat wird ersetzt, nicht gemergt — wobei die UI die veraltete Kopie währenddessen nur zeigt, wenn die Politik es erlaubt
- **SOLLTE [SHOULD]** einen einzigen geplanten Abgleichseinstieg (einen Sync-Worker je Datenbereich) gegenüber Ad-hoc-Refreshes je Screen bevorzugen, damit Frische eine Eigenschaft des Replikats ist und nicht davon abhängt, welcher Screen zuletzt geöffnet wurde

### E. Nebenläufigkeit und Ausführung

- **MUSS [MUST]** zwischen den Schichten mit Coroutines und Flows kommunizieren [R2]
- **MUSS [MUST]** Dispatcher injizieren, statt `Dispatchers.*` in einer getesteten Klasse zu referenzieren, und **MUSS [MUST]** IO auf einem IO-Dispatcher ausführen — nie auf dem Main-Thread (im Debug-Build geprüft gemäß `spec/android/release-readiness/` §B)
- **MUSS [MUST]** Arbeit auf ihre Lebensdauer begrenzen: `viewModelScope` für screengebundene Arbeit, ein anwendungsweiter Coroutine-Scope für Fire-and-forget-Arbeit, die den Screen überdauern muss, und WorkManager für Arbeit, die den Prozesstod überleben muss
- **DARF NICHT [MUST NOT]** Netzwerk- oder Datenbankarbeit direkt aus der Komposition starten; Anfragen werden aus der Zustandssammlung, einem Effect oder einem Nutzerabsichts-Callback ausgelöst

### F. Die Schichten austauschbar halten

- **MUSS [MUST]** den generierten oder handgeschriebenen HTTP-Client hinter der Repository-Grenze halten; nichts oberhalb importiert einen generierten Typ, einen HTTP-Status oder eine Serialisierungsannotation
- **MUSS [MUST]** Speichertypen (Room-Entities, DAOs, DataStore-Schlüssel) unterhalb derselben Grenze halten
- **DARF NICHT [MUST NOT]** einen Domain Layer einführen, um Regeln zu beherbergen, die zum Backend gehören; Use Cases existieren nur, um *Client*-Orchestrierung über ViewModels hinweg wiederzuverwenden, und triviale Durchreich-Use-Cases bleiben nach `spec/android/project-structure/` §E verboten
- **SOLLTE [SHOULD]** Feature-Pakete frei von Abhängigkeiten auf andere Feature-Pakete halten; über Features geteilte Daten wandern in eine Core-/Data-Komponente

### G. Testbarkeit

- **MUSS [MUST]** jede Schicht auf der JVM ohne Gerät und ohne laufendes Backend ausführbar machen: ViewModel-Zustandstests über ein Fake-Repository, Repository-Tests über Fake-Datenquellen, Mapper-Tests über Fixtures. Mechanik, Platzierung und die Fakes-statt-Mocks-Regel liegen in `spec/android/test-automation/` §B/§C
- **MUSS [MUST]** für jede Remote-Datenquelle ein Fake bereitstellen, das **jeden** Fall der in `spec/android/backend-contract/` §B definierten geschlossenen Menge erzeugen kann — Erfolg, offline, Timeout, nicht authentifiziert, nicht autorisiert, fachliche Ablehnung (ein Konflikt ist eine ihrer Ausprägungen), Serverfehler und Contract-Abweichung. Diese Liste zu verkürzen ist nicht konform: Die beiden Authentifizierungsfälle sind die, die eine handgeschriebene Fake-Menge aus Gewohnheit auslässt — und die, deren UI-Antwort sich am stärksten unterscheidet
- **MUSS [MUST]** die Zeit überall injizierbar halten, wo Veraltung, Ablauf oder Backoff berechnet wird — ein Test, der schlafen muss, ist ein Entwurfsfehler
- **MUSS [MUST]** für jeden Screen, der aus dem Cache gezeigt werden kann, mindestens den Veraltungs- und den Ausstehend-Zustand abdecken; das sind die Zustände, die es nur gibt, weil der Client flach ist, und deshalb genau die, die niemand aus Gewohnheit schreibt

### H. Entscheidungen festhalten

- **MUSS [MUST]** je umgesetztem Feature festhalten: die Schreibstrategie je Schreibvorgang (§D), die Veraltungspolitik je gecachtem Typ (§C) und jede erhobene Backend-Lücke (`spec/android/backend-contract/` §E–§F). Der Vermerk liegt beim Feature — in dessen Requirement- oder Feature-Datei —, nicht nur in einer Commit-Message
- **MUSS [MUST]**, wenn ein Fall von dieser Spec nicht abgedeckt ist, die Lücke melden und eine Spec-Erweiterung vorschlagen, statt still zu entscheiden (Repository-REQ-6)

## Akzeptanzkriterien

Die Kriterien sind eine repräsentative Zusammenfassung von §A–§H, keine 1:1-Abbildung; jede Anforderung oben ist für sich normativ.

- [ ] Keine fachliche Entscheidung (Annahme, Erlaubnis, Status, Berechtigung, abgeleitetes Label) wird auf dem Gerät berechnet; clientseitige Eingabeprüfungen existieren nur als Hilfestellung und übersteuern nie die Antwort des Servers
- [ ] Jede clienteigene Logik fällt in eine der vier Klassen aus §A, und was in keine passt, wurde als Lücke gemeldet statt umgesetzt; Entwürfe, Feature-Flags, Telemetrie, Versions-Gating und Aggregate sitzen in den Heimaten, die §A zuweist, und kein clientseitiges Sortieren oder Filtern erzwingt einen Over-Fetch
- [ ] Kein Composable greift auf Daten zu, wertet eine Regel aus oder löst eine Anfrage außerhalb eines Effects aus; lebenszyklusabhängige Arbeit nutzt lebenszyklusbewusste Effects statt überschriebener `Activity`-Callbacks, und keine Netzwerk- oder Datenbankarbeit startet aus der Komposition
- [ ] Jedes ViewModel stellt einen einzigen `uiState`-`StateFlow` bereit, gesammelt mit `collectAsStateWithLifecycle`, ohne ViewModel→UI-Ereigniskanal und ohne gehaltenen lebenszyklusgebundenen Typ
- [ ] Jeder Screen-Zustand kann Laden, Inhalt, Leer, Fehler-mit-Aktion, Veraltung und ausstehenden Schreibvorgang ausdrücken; ein cachegestützter Screen zeigt seine Veraltung
- [ ] Die UI berührt nie eine Datenquelle; jeder Lesevorgang läuft über ein Repository, Lesevorgänge sind `Flow`, Schreibvorgänge `suspend`
- [ ] Netzwerk-DTOs, lokale Entities und UI-Modelle sind getrennte Typen mit expliziten Mappern; kein generierter Wire-Typ und kein Speichertyp erscheint oberhalb der Repository-Grenze
- [ ] Jeder zwischengespeicherte Datentyp trägt Frischemetadaten und eine festgelegte Veraltungspolitik, die auch das Verhalten bei serverseitiger Löschung und vollständigem Resync benennt; nutzerbezogene Cache-Daten werden bei Abmeldung und Kontowechsel gelöscht
- [ ] Jeder Schreibvorgang benennt eine der drei Strategien; nicht-nur-online-Schreibvorgänge laufen über WorkManager mit Konnektivitätsbedingung und Backoff, sind während des Wartens sichtbar und bei endgültigem Fehlschlag handlungsfähig
- [ ] Es existiert kein clientseitiges Merge; Konflikte löst das Backend gegen einen vom Client gesendeten Validator, und automatisches Wiederholen gibt es nur dort, wo der Wire-Contract den Schreibvorgang idempotenzsicher macht
- [ ] Dispatcher und Zeit sind injiziert; kein IO läuft auf dem Main-Thread; Arbeit, die den Prozesstod überleben muss, läuft in WorkManager
- [ ] Ein wiederhergestellter Screen (Prozesstod, Konfigurationswechsel) verliert weder Nutzereingaben noch einen ungesendeten Schreibvorgang
- [ ] Jede Schicht hat JVM-Tests mit Fakes über die vollständige geschlossene Fehlermenge, inklusive der Veraltungs- und Ausstehend-Zustände
- [ ] Schreibstrategie, Veraltungspolitik und erhobene Backend-Lücken sind beim Feature festgehalten

## Offene Fragen

Jede Frage nennt die Vorgabe, die die Anforderungen oben bereits kodieren.

- Sollen die Anzeigen für „unbestätigter Schreibvorgang" und „veralteter Inhalt" als geteilte Komponenten im Designsystem standardisiert werden (eine Erweiterung von `spec/android/ui-components/`) oder je Screen bleiben? Vorgabe: je Screen, wobei §A nur festlegt, dass der Zustand existiert
- Soll ein Repository einen einzigen `Result`-förmigen Lesevorgang bereitstellen, der die geschlossene Fehlermenge faltet, oder Inhalts- und Fehlerströme getrennt halten? Vorgabe: offen — §B legt das *Zustandsmodell* fest, nicht den Transport von Fehlern zwischen den Schichten
- Ist Room für ein Replikat aus nur wenigen Datensätzen gerechtfertigt, oder genügt ein serialisierter DataStore-Schnappschuss? Vorgabe: Die Formregel aus §C entscheidet; es wird keine Größenschwelle festgelegt
- Soll eine offlinefähige App zu periodischem Hintergrund-Sync verpflichtet sein oder nur beim Wechsel in den Vordergrund synchronisieren? Vorgabe: nicht festgelegt; §D verlangt nur einen einzigen Abgleichseinstieg je Datenbereich

## Referenzen

- [R1] Guide to app architecture — Trennung der Belange, UI aus Datenmodellen treiben, SSOT, UDF, Schichtverantwortungen: <https://developer.android.com/topic/architecture>
- [R2] Architecture recommendations (Stufen Strongly recommended / Recommended / Optional) — Data Layer hält „the vast majority of your app's business logic" (Strongly recommended), „Do not use `AndroidViewModel`" (Recommended), UDF, `uiState`/`StateFlow`/`WhileSubscribed(5000)`, `collectAsStateWithLifecycle`, keine VM→UI-Ereignisse, ViewModels auf Screen-Ebene, lebenszyklusbewusste Effects, DI, Testen: <https://developer.android.com/topic/architecture/recommendations>
- [R3] Build an offline-first app — lokale Wahrheitsquelle, Modelltrennung, Lese-/Schreibstrategien (nur online, eingereiht, verzögert), Konfliktauflösung, WorkManager-Sync: <https://developer.android.com/topic/architecture/data-layer/offline-first>
- [R4] Data layer — Repositories, Datenquellen und ihre Verantwortungen: <https://developer.android.com/topic/architecture/data-layer>
- [R5] UI layer und UI State — State Holder, Zustandsmodellierung, unidirektionaler Datenfluss: <https://developer.android.com/topic/architecture/ui-layer>
- [R6] ViewModel-Überblick und `SavedStateHandle`: <https://developer.android.com/topic/libraries/architecture/viewmodel>
- [R7] WorkManager — persistente Arbeit, Unique Work, Constraints, Backoff: <https://developer.android.com/topic/libraries/architecture/workmanager>
- [R8] Now in Android — Referenzimplementierung des Offline-First-Replikats und des Sync-Workers: <https://github.com/android/nowinandroid>
- [R9] WorkManager — Work-Requests definieren: Retry- und Backoff-Politik (`MIN_BACKOFF_MILLIS` = 10 s Minimum, Default `EXPONENTIAL` mit 30 s): <https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work>
