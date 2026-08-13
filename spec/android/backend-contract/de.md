# Backend-Contract und Anforderungsübergabe

Status: draft

## Kontext

Ein flacher View Layer (`spec/android/app-architecture/`) erkauft seine Einfachheit mit einer Abhängigkeit: Alles, was die App nicht entscheiden kann, muss das Backend liefern. Damit werden zwei Dinge tragend, bei denen eine clientlastige App nachlässig sein darf — wie die App den Contract konsumiert und was passiert, wenn der Contract nicht enthält, was der Screen braucht.

Die zweite Hälfte geht in der Praxis schief. Ein fehlendes Feld oder ein nicht ausdrückbarer Filter fällt mitten in der Umsetzung auf, zum denkbar schlechtesten Zeitpunkt für ein Designgespräch, und der lokal billigste Zug ist immer derselbe: es auf dem Gerät berechnen. Genau diese eine Entscheidung ist der Punkt, an dem ein flacher Client aufhört, flach zu sein. Diese Spec macht stattdessen die Alternative billig — eine feste Form, die fehlende Fähigkeit als Anforderung festzuhalten, die die Backend-Seite aufgreifen kann, sodass „erheben" weniger kostet als „umgehen".

Die Konsumhälfte ist bewusst eng: Diese Spec legt fest, was der *Client* mit dem Contract tut — wie er generiert wird, wo seine Typen auftauchen dürfen, wie Fehler in eine geschlossene Menge klassifiziert werden und welche Requests wiederholt werden dürfen. Sie sagt nichts darüber, wie das Backend gebaut wird.

Provenienz: Schreibtischrecherche (August 2026) über die Dokumentation des OpenAPI-Generator-Kotlin-Clients, RFC 9457 (Problem Details for HTTP APIs), den IETF-HTTPAPI-Entwurf zum `Idempotency-Key`-Header, die Android-Leitfäden zu Architektur und Offline-First sowie die konsumierende App dieses Portfolios (`nolte/kamerplanter-android`, ein OpenAPI-generierter Retrofit-Client in `core/network`).

Grenzen: TLS und Zertifikatsbehandlung liegen in `spec/android/security/` §C, die Credential-Speicherung in dessen §A und die Pflichten zu Build/Lieferkette sowie Authentifizierungs-Resilienz in dessen §F/§G; die Regel, dass das Backend — nie der Client — entscheidet, ob eine Aktion erlaubt ist, gehört zu `spec/android/app-architecture/` §A; Caching, Veraltung, Schreibstrategien und Sync in `spec/android/app-architecture/` §C/§D; die *Darstellung* von Paging und die Paging-3-Verdrahtung in `spec/android/long-list-scrolling/` §C; die *Formulierung* von Fehlertexten und die Leerzustands-UX in `spec/android/app-design-navigation/` §F; Testmechanik in `spec/android/test-automation/`.

Leser: Autoren der Android-Skills dieses Repos, die ein Feature gegen ein Backend umsetzen, sowie Reviewer, die beurteilen, ob ein Client im Contract geblieben ist, statt daran vorbei zu erfinden.

## Ziele

- Den Contract zur einzigen maschinenlesbaren Quelle für Wire-Typen machen, damit DTOs nie doppelt von Hand gepflegt werden
- Generierte Typen auf eine Schicht beschränken, damit der Client eine Neugenerierung übersteht
- Transport- und Protokollfehler in eine geschlossene, vollständig behandelte Menge überführen statt in ein `catch (e: Exception)`
- Wiederholungen konstruktionsbedingt sicher machen statt hoffnungsbasiert
- „Das Backend kann das noch nicht" einen billigeren Weg geben als einen clientseitigen Workaround
- Eine Backend-Anforderung erzeugen, die ein Backend-Spezialist umsetzen kann, ohne die App-Seite noch etwas fragen zu müssen

## Nicht-Ziele

- Backend-Umsetzung, Hoheit über das API-Design oder die Qualitätsschranken des Backends — diese Spec legt nur fest, was der Client braucht und wie er fragt
- Transportsicherheit, Entwurf des Authentifizierungsverfahrens und Credential-Speicherung — `spec/android/security/` §A/§C/§G
- Cache, Veraltung, Schreibstrategie, Konfliktbehandlung — `spec/android/app-architecture/` §C/§D
- Paging-UI-Verhalten und Paging-3-Mechanik — `spec/android/long-list-scrolling/` §C
- GraphQL, gRPC und Echtzeit-Transporte; die Anforderungen unten setzen einen HTTP/JSON-Contract voraus und bräuchten für die anderen eine Erweiterung (§Offene Fragen)
- Die Wahl von Backend-Produkt oder Hosting; die App konsumiert, was das Backend-Repository des Betreibers bereitstellt

## Anforderungen

### A. Contract-first konsumieren

- **MUSS [MUST]** ein dokumentiertes Backend über einen typisierten Client konsumieren, der aus dessen veröffentlichtem Contract (OpenAPI) generiert wird, sofern ein Contract existiert; handgeschriebene DTOs, die ein veröffentlichtes Schema doppeln, sind nicht konform [R1]
- **MUSS [MUST]** das Contract-Dokument (oder eine gepinnte Referenz auf ein versioniertes Artefakt) ins App-Repository committen, damit ein Build ohne laufendes Backend reproduzierbar ist, und **MUSS [MUST]** bewusst neu generieren — generierte Quellen werden nie von Hand bearbeitet
- **MUSS [MUST]** in eine dedizierte Netzwerkkomponente generieren (`core/network` oder das Einzelmodul-Äquivalent nach `spec/android/project-structure/` §C) und **MUSS [MUST]** generierte Typen, HTTP-Statuscodes und Serialisierungsannotationen hinter der Repository-Grenze halten (`spec/android/app-architecture/` §F)
- **MUSS [MUST]** generierte DTOs in der Datenquelle oder im Repository auf App-Modelle abbilden, nie darüber
- **SOLLTE [SHOULD]** den Kotlin-Generator so konfigurieren: `library` = `jvm-retrofit2` mit `useCoroutines` oder `jvm-ktor`, wo bereits ein Ktor-Stack existiert; `serializationLibrary` = `kotlinx_serialization`; `dateLibrary` = `java8` (reine JVM-Apps). Das ist eine **Portfolio-Vorgabe**, keine Herstellerempfehlung — der Generator unterstützt mehrere Kombinationen, und [R1] wird nur für die Optionsnamen und ihre zulässigen Werte zitiert. Eine andere Kombination ist erlaubt, **MUSS [MUST]** aber mit Begründung festgehalten werden
- **KANN [MAY]** den Client von Hand schreiben, wenn überhaupt kein Contract-Dokument existiert; dann greift §E sofort — das Fehlen eines Contracts ist selbst eine Backend-Anforderung, und die handgeschriebenen Typen sind eine Zwischenlösung mit festgehaltenem Zielzustand
- **DARF NICHT [MUST NOT]** das Backend von mehr als einer Stelle je Ressource aufrufen: eine Datenquelle je API-Bereich, ein Repository je Datentyp (Benennung nach `spec/android/project-structure/` §E)

### B. Die geschlossene Ergebnismenge

- **MUSS [MUST]** jedes Ergebnis eines Aufrufs auf genau einen von acht Fällen abbilden — ein Erfolg plus sieben Fehler — und **MUSS [MUST]** alle acht je Feature behandeln (die Fakes aus `spec/android/app-architecture/` §G existieren, um das nachzuweisen):
  1. **Erfolg**
  2. **Offline / nicht erreichbar** — keine nutzbare Verbindung, DNS-Fehler, abgelehnte Verbindung
  3. **Timeout** — Connect-, Read- oder Gesamtfrist überschritten
  4. **Nicht authentifiziert** — das Credential fehlt oder ist abgelaufen; die Antwort des Clients ist ein Refresh oder eine Anmeldeaufforderung, nie ein generischer Fehler
  5. **Nicht autorisiert** — das Credential ist gültig und die Aktion nicht erlaubt; eine *Serverentscheidung*, die als solche dargestellt wird
  6. **Fachliche Ablehnung** — der Request wurde verstanden und wegen einer Fachregel abgelehnt (Validierung, Konflikt, Zustand); trägt Feld- oder Regeldetails, sofern der Contract sie liefert
  7. **Serverfehler** — das Backend ist gescheitert; wiederholbar nach §C, nie den Nutzenden angelastet
  8. **Contract-Abweichung** — die Antwort ließ sich nicht in die generierten Typen parsen, oder ein Pflichtfeld fehlte
- **DARF NICHT [MUST NOT]** Coroutine-Cancellation in die Menge abbilden: Cancellation ist kein Ergebnis des Aufrufs, sondern das Verschwinden seines Aufrufers. Eine `CancellationException` **MUSS [MUST]** erneut geworfen und nie in einen Fehlerfall gefangen werden — sie zu verschlucken macht aus einem verlassenen Screen einen scheinbaren Fehlerzustand und bricht die strukturierte Nebenläufigkeit
- **MUSS [MUST]** die drei Grenzfälle auflösen, die die acht Fälle nebeneinander lassen, damit ein Client-Implementierer nie raten muss:
  - **offline vs. Timeout** — entschieden durch den tatsächlich eingetretenen Fehler (Namensauflösung oder abgelehnte Verbindung gegenüber überschrittener Frist), nicht durch die Wartezeit der Nutzenden
  - **nicht autorisiert vs. fachliche Ablehnung** — eine Ablehnung, die davon abhängt, *wer* fragt, ist „nicht autorisiert"; eine Ablehnung, die davon abhängt, *was* gefragt wird oder in welchem Zustand die Ressource ist, ist eine fachliche Ablehnung. Liefert ein Backend für beides denselben Status, entscheidet der Problem-`type` des Contracts; unterscheidet es beides gar nicht, greift §E — der Client **DARF NICHT [MUST NOT]** raten, denn die beiden Fälle führen zu unterschiedlichen UI-Antworten
  - **Rate-Limiting** — ein `429` gilt für die Klassifikation als **Serverfehler** (der Request war wohlgeformt, und die Nutzenden trifft keine Schuld), aber der Client **MUSS [MUST]** ein vorhandenes `Retry-After` anstelle des eigenen Backoffs beachten und **DARF NICHT [MUST NOT]** einen ratenbegrenzten Versuch auf ein Retry-Budget anrechnen, als hätte das Backend versagt
- **MUSS [MUST]** Contract-Abweichung als Defekt gegen den Contract behandeln, nicht als verschluckbaren Laufzeitfehler: Sie wird dem Betreiber sichtbar gemacht (Log mit betroffenem Endpunkt und Feld, nie mit der Nutzlast) und wird zur Backend-Anforderung nach §E, wenn das Backend von seinem eigenen Dokument abweicht
- **MUSS [MUST]** einen RFC-9457-Body `application/problem+json` konsumieren, sofern das Backend einen sendet, und dabei `type` sowie definierte Extension-Member für den Kontrollfluss lesen; **DARF NICHT [MUST NOT]** `detail` für Logik parsen und **DARF NICHT [MUST NOT]** Verhalten an `title` festmachen [R2]
- **DARF NICHT [MUST NOT]** eine rohe Server-Zeichenkette als primären Fehlertext eines Screens darstellen; der Client bildet den Fall auf eine eigene Meldung mit Wiederherstellungsaktion ab (Formulierung nach `spec/android/app-design-navigation/` §F). Servergelieferter Text **KANN [MAY]** als sekundäres Detail gezeigt werden, wenn der Contract ihn als nutzersichtbar und lokalisiert ausweist
- **MUSS [MUST]** feldbezogene Ablehnungen an die entsprechenden Eingabefelder zurückführen statt in ein einzelnes Banner, sofern der Contract die Feldzuordnung trägt
- **DARF NICHT [MUST NOT]** Request- oder Response-Bodies, Header mit Credentials oder personenbezogene Daten loggen (`spec/android/security/` §A); ein Fehlerlog nennt nur Endpunkt, Status und Fehlerklasse

### C. Requests: Timeouts, Wiederholungen, Idempotenz

- **MUSS [MUST]** Connect-, Read- und Call-Timeouts explizit setzen; die Plattformvorgaben sind keine Entscheidung
- **MUSS [MUST]** automatisch nur wiederholen, wo der Request idempotent ist — `GET`, `HEAD`, `PUT`, `DELETE` gemäß Contract — mit gedeckeltem exponentiellem Backoff plus Jitter und einer festgelegten Höchstzahl an Versuchen [R4]
- **DARF NICHT [MUST NOT]** `POST` oder `PATCH` automatisch wiederholen, es sei denn, der Request trägt einen Idempotenzschlüssel, den das Backend beachtet; bietet das Backend keinen solchen Mechanismus, ist die Wiederholung manuell (nutzerausgelöst), bis die Anforderung nach §E erhoben ist [R3]
- **SOLLTE [SHOULD]**, sofern das Backend es unterstützt, `Idempotency-Key` als clientseitig erzeugte UUID senden, die über Wiederholungen *desselben* logischen Schreibvorgangs stabil bleibt und für einen neuen wechselt; der Schlüssel wird mit einem eingereihten Schreibvorgang persistiert, damit er den Prozesstod überlebt [R3][R8]. Der Header ist nur durch einen nicht finalen IETF-Entwurf spezifiziert, deshalb bleibt dies ein **SOLLTE**, das daran gebunden ist, dass das Backend ihn tatsächlich beachtet; der Mechanismus ist gleichwohl etablierte, ausgelieferte Praxis bei mehreren Zahlungsanbietern [R8], und wo ein Backend keinen anbietet, greift stattdessen das Verbot aus §C, einen nicht idempotenten Schreibvorgang automatisch zu wiederholen
- **MUSS [MUST]** die Credential-Erneuerung im Single-Flight ausführen: gleichzeitige 401er lösen einen Refresh aus, und die wartenden Aufrufe werden einmal wiederholt — ein Refresh-Sturm ist zugleich Defekt und Rate-Limit-Risiko
- **MUSS [MUST]** den Paginierungsmechanismus des Contracts verwenden (cursorbasiert bevorzugt gegenüber Offset) und **DARF NICHT [MUST NOT]** Paging durch eine unbegrenzte Seite nachbilden; die clientseitige Verdrahtung folgt `spec/android/long-list-scrolling/` §C
- **MUSS [MUST]** Validatoren für Conditional Requests (`ETag`/`If-None-Match`, `If-Modified-Since`) senden, wo der Contract sie bereitstellt — die Frischemetadaten des Replikats (`spec/android/app-architecture/` §C) existieren genau dafür
- **SOLLTE [SHOULD]** nach Möglichkeit einen Request je Screen-Zustand halten; ein Screen, der drei oder mehr Aufrufe für seinen ersten Frame braucht, ist ein §E-Auslöser und keine clientseitige Orchestrierungsübung. Zwei Aufrufe sind zulässig, wenn sie unabhängig und parallel laufen; zwei Aufrufe, bei denen der zweite die Antwort des ersten braucht, sind bereits eine abhängige Kette — und eine abhängige Kette ist unabhängig von ihrer Länge ein §E-Gespräch

### D. Mit Contract-Änderungen leben

- **MUSS [MUST]** die Deserialisierung so konfigurieren, dass unbekannte Felder ignoriert werden, damit eine additive Backend-Änderung eine ausgelieferte App nicht zum Absturz bringt
- **MUSS [MUST]** jedem Enum ein Rückfallmitglied geben und **DARF NICHT [MUST NOT]** einen unbekannten Enum-Wert als fatalen Fehler behandeln; die UI zeigt eine neutrale Darstellung, und der Fall wird als Contract-Beobachtung geloggt
- **DARF NICHT [MUST NOT]** von Feldreihenfolge, vom Vorhandensein eines optionalen Felds oder von einem undokumentierten Feld abhängen, das das Backend zufällig sendet
- **MUSS [MUST]** den Client in der CI aus dem committeten Contract neu generieren und den Build bei einem Kompilierbruch scheitern lassen, damit eine Contract-Aktualisierung nicht still halbfertig landet
- **MUSS [MUST]** die Contract-Version (oder den Commit) festhalten, gegen die die App gebaut wird, und **MUSS [MUST]** die minimale Backend-Version nennen, wenn die App eine voraussetzt
- **SOLLTE [SHOULD]** ein Feld, das die App braucht und der Contract als optional ausweist, als Klärungspunkt nach §E behandeln, statt anzunehmen, dass es immer da ist

### E. Wann eine Backend-Anforderung erhoben wird

- **MUSS [MUST]** eine Backend-Anforderung erheben — und **DARF NICHT [MUST NOT]** einen stillen clientseitigen Workaround umsetzen —, sobald die Umsetzung des Features eines der Folgenden verlangen würde:
  - eine fachliche Entscheidung auf dem Gerät herleiten (die §A-Regel aus `spec/android/app-architecture/`)
  - ein Feld anzeigen, das der Contract nicht führt
  - Filtern, Sortieren, Suchen oder Paginieren, das die API nicht ausdrücken kann, sodass der Client übermäßig lädt und nachverarbeitet
  - drei oder mehr Aufrufe für den ersten Frame eines Screens oder ein N+1-Aufrufmuster über eine Liste
  - ein mehrschrittiger Schreibvorgang, der als Einheit gelingen oder scheitern muss, aber nur als getrennte Aufrufe verfügbar ist
  - ein nicht idempotenter Schreibvorgang, den der Client wiederholen soll (§C)
  - Polling, wo ein Conditional Request, ein Push oder ein Sync-Token genügen würde
  - ein Fehlerfall, den der Client unterscheiden muss, den der Contract aber nicht unterscheidbar macht (etwa: alles ist ein 400 mit Fließtext)
- **MUSS [MUST]** nach dem Erheben das Übergangsverhalten des Clients mit dem Betreiber abstimmen, statt es allein zu wählen: warten, das Feature ohne den betroffenen Teil ausliefern oder einen zeitlich befristeten Zwischenweg umsetzen, der im Artefakt festgehalten und beim Landen des Backends entfernt wird (Repository-REQ-6, REQ-8)
- **DARF NICHT [MUST NOT]** einen Zwischenweg still dauerhaft werden lassen — der Status des Artefakts (§F) ist der Nachverfolgungsmechanismus

### F. Das Übergabeartefakt

- **MUSS [MUST]** die Anforderung nach `project/backend-requirements/<YYYY-MM-DD>-<slug>.md` im *App*-Repository schreiben, mit einer stabilen Kennung `BR-<n>`, auf die Codekommentare, Commits und Issues verweisen können
- **MUSS [MUST]** diese Abschnitte in dieser Reihenfolge enthalten, damit die Backend-Seite ohne Rückfrage umsetzen kann:
  1. **Auslöser** — Feature, Screen und Nutzerschritt, aus dem der Bedarf entstand
  2. **Bedarf** — ein Satz, formuliert als Fähigkeit, nicht als Umsetzung
  3. **Konsumentenszenario** — was die App mit der Antwort darstellt, inklusive der Lade-, Leer- und Fehlerzustände, die sie zeigen können muss
  4. **Vorgeschlagener Contract** — Endpunkt(e), Methode, Request-Form, Response-Form und die Fehlerfälle, die der Client unterscheiden wird, als OpenAPI-Fragment (Paths + Schemas + Responses), ausdrücklich markiert als **Vorschlag, nicht maßgeblich** — das finale Design gehört dem Backend
  5. **Nicht-funktionale Bedarfe** — Latenzbudget des konsumierenden Screens, erwartete Seitengröße und Sortierung, Auth-Scope, Idempotenzbedarf, Cachebarkeit und Validatoren, Datenvolumen sowie die Dringlichkeit auf App-Seite: was ohne diese Fähigkeit blockiert ist und bis wann die App sie braucht, damit das Backend sie gegen die eigene Warteschlange einplanen kann
  6. **Akzeptanzkriterien** — allein von der Backend-Seite prüfbar, ein Punkt je Kriterium
  7. **Übergangsverhalten des Clients** — was die App tut, bis das hier landet, und was danach entfernt werden muss
  8. **Offene Fragen** — jeder Punkt, den die App-Seite nicht entscheiden konnte
  9. **Status** — einer von `draft` → `proposed` → `accepted` → `implemented` → `consumed`, mit dem Datum des letzten Übergangs
- **MUSS [MUST]** ausschließlich synthetische Beispiele verwenden; keine personenbezogenen Produktivdaten, keine Credentials, keine echten Nutzerkennungen. Das ist eine eigene Regel dieser Spec, und sie existiert, weil das Artefakt ein repository-übergreifendes Dokument ist: Hineinkopierte Daten verlassen die Speichergrenze der App vollständig — eine andere Exposition als die geräteseitigen Pflichten, die `spec/android/security/` §A/§E regelt
- **MUSS [MUST]** zu jedem angefragten Feld das *Warum* nennen — eine Feldliste ohne Darstellungszweck lädt zu einem Backend-Design ein, das den Buchstaben erfüllt und den Screen verfehlt
- **MUSS [MUST]** beim Status `accepted` die Contract-Version festhalten, die die Änderung tragen wird, und beim Status `consumed` den Zwischenweg entfernen und das im Artefakt vermerken
- **KANN [MAY]** nach ausdrücklicher Bestätigung des Betreibers ein Issue im Backend-Repository eröffnen, dessen Rumpf aus dem Artefakt abgeleitet ist und darauf zurückverweist; das Artefakt bleibt die Wahrheitsquelle, und der Issue-Link wird darin vermerkt. Das Eröffnen ohne Bestätigung ist verboten (Repository-REQ-8)
- **SOLLTE [SHOULD]** ein Artefakt je Fähigkeit halten; ein zweiter Screen mit demselben Bedarf erweitert das bestehende Artefakt, statt ein Duplikat anzulegen

### G. Verifikation

- **MUSS [MUST]** alle acht Fehlerfälle aus §B mit Fakes in JVM-Tests abdecken, bevor ein Feature als fertig gilt (`spec/android/test-automation/` §B/§C)
- **MUSS [MUST]** prüfen, dass kein generierter Typ die Repository-Grenze überschreitet — ein Grep nach dem generierten Paket außerhalb der Netzwerkkomponente ist die mechanische Kontrolle
- **MUSS [MUST]** prüfen, dass wiederholte Schreibvorgänge idempotenzsicher sind (§C) — per Test, wo ein Schlüssel verwendet wird, sonst per Inspektion
- **MUSS [MUST]** eine erhobene, aber unbeantwortete Backend-Anforderung im Abschlussbericht des Laufs melden, statt die Arbeit still abzuschließen (Repository-REQ-6, REQ-7)

## Akzeptanzkriterien

Die Kriterien sind eine repräsentative Zusammenfassung von §A–§G, keine 1:1-Abbildung; jede Anforderung oben ist für sich normativ.

- [ ] Der Wire-Client wird aus einem committeten Contract-Dokument generiert; kein handgepflegtes DTO doppelt ein veröffentlichtes Schema, und keine generierte Quelle ist von Hand bearbeitet
- [ ] Generierte Typen, HTTP-Status und Serialisierungsannotationen erscheinen nur innerhalb der Netzwerkkomponente; das Repository liefert App-Modelle
- [ ] Jedes Aufrufergebnis bildet auf einen der acht Fälle aus §B ab, und jedes Feature behandelt alle acht, nachgewiesen durch Fakes in JVM-Tests
- [ ] Contract-Abweichung wird als Contract-Defekt gemeldet, nicht verschluckt; keine Nutzlast, kein Credential und keine personenbezogenen Daten werden geloggt
- [ ] Problem-Details-Bodies werden über `type` und Extension-Member gelesen; `detail` wird nie für Logik geparst; keine rohe Server-Zeichenkette ist der primäre Fehlertext eines Screens
- [ ] Timeouts sind explizit; automatische Wiederholungen gibt es nur für idempotente Requests oder geschlüsselte Schreibvorgänge; die Credential-Erneuerung läuft im Single-Flight
- [ ] Die Paginierung nutzt den Mechanismus des Contracts; Conditional-Request-Validatoren werden gesendet, wo verfügbar
- [ ] Unbekannte Felder und unbekannte Enum-Werte werden toleriert; die CI generiert den Client aus dem committeten Contract neu und scheitert bei einem Kompilierbruch
- [ ] Die konsumierte Contract-Version ist beim Build festgehalten, und eine erforderliche Mindest-Backend-Version ist genannt, wo es eine gibt
- [ ] Coroutine-Cancellation wird erneut geworfen statt in die Ergebnismenge abgebildet, und die Grenzfälle offline/Timeout, nicht-autorisiert/fachliche-Ablehnung sowie Rate-Limiting sind so aufgelöst, wie §B es festlegt
- [ ] Jeder §E-Auslöser hat ein `BR-<n>`-Artefakt unter `project/backend-requirements/` erzeugt, mit allen neun Abschnitten, ausschließlich synthetischen Beispielen und aktuellem Status
- [ ] Jedes im Artefakt angefragte Feld nennt den Darstellungszweck, dem es dient, und das Artefakt benennt, was ohne die Fähigkeit blockiert ist
- [ ] Eine erhobene, aber unbeantwortete Backend-Anforderung wird im Abschlussbericht des Laufs benannt statt implizit gelassen
- [ ] Jeder Übergangsweg im Client ist in seinem Artefakt festgehalten und wird entfernt, wenn das Artefakt `consumed` erreicht
- [ ] Ein Issue im Backend-Repository existiert nur dort, wo der Betreiber es bestätigt hat, und verweist auf das Artefakt zurück

## Offene Fragen

Jede Frage nennt die Vorgabe, die die Anforderungen oben bereits kodieren.

- Soll das App-Repository zusätzlich einen generierten, menschenlesbaren Diff der Contract-Änderungen zwischen Versionen halten, oder genügen committeter Contract plus Git-Historie? Vorgabe: Die Git-Historie genügt
- Soll die `BR-<n>`-Nummerierung je Repository oder portfolioweit laufen? Vorgabe: je Repository, da das Artefakt im App-Repo liegt
- GraphQL- und gRPC-Backends: diese Spec um ein transportneutrales §A/§B erweitern oder eine Schwester-Spec schreiben? Vorgabe: außerhalb des Umfangs, bis ein Portfolio-Projekt es braucht
- Darf der Client je einen Kompatibilitäts-Shim für einen bekannten Backend-Defekt ausliefern (statt eine Anforderung zu erheben)? Vorgabe: nur als Zwischenweg nach §E, immer festgehalten, nie dauerhaft

## Referenzen

- [R1] OpenAPI Generator — Optionen des Kotlin-Client-Generators (`library`, `serializationLibrary`, `dateLibrary`, `useCoroutines`): <https://openapi-generator.tech/docs/generators/kotlin/>
- [R2] RFC 9457 — Problem Details for HTTP APIs (`application/problem+json`, `type`/`title`/`status`/`detail`/`instance`, Extension-Member, „consumers SHOULD NOT parse `detail`"): <https://www.rfc-editor.org/rfc/rfc9457.html>
- [R3] IETF HTTPAPI WG — The Idempotency-Key HTTP Header Field (Entwurf; clientseitige Schlüsselerzeugung, serverseitige Behandlung von Duplikaten/Nebenläufigkeit, 409/422-Semantik): <https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/>
- [R4] Build an offline-first app — Netzwerkfehlerbehandlung, exponentielles Backoff, Sync über WorkManager: <https://developer.android.com/topic/architecture/data-layer/offline-first>
- [R5] Guide to app architecture — Data Layer, Repositories, Datenquellen: <https://developer.android.com/topic/architecture/data-layer>
- [R6] kotlinx.serialization — JSON-Konfiguration (`ignoreUnknownKeys`, Defaultwerte, Umgang mit unbekannten Enums): <https://github.com/Kotlin/kotlinx.serialization/blob/master/docs/json.md>
- [R7] OpenAPI Specification 3.1: <https://spec.openapis.org/oas/latest.html>
- [R8] Stripe API — Idempotente Requests (ausgelieferte Herstellerpraxis, die den Entwurf aus [R3] stützt): <https://docs.stripe.com/api/idempotent_requests>
