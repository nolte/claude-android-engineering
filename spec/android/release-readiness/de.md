# Release-Reife des Quellcodes

Status: draft

## Kontext

„Es funktioniert" und „es ist auslieferbar" sind verschiedene Behauptungen, und der Abstand dazwischen ist auf einem Debug-Build nahezu unsichtbar. Der Debug-Build behält jeden Klassennamen, liefert den Leak-Detektor mit, loggt alles, spricht mit dem Staging-Host und führt nie den Optimierer aus, der den Code umschreibt, den Nutzende tatsächlich ausführen. Ein nur dort geprüftes Feature wurde in einer Konfiguration geprüft, die niemand jemals ausführen wird.

Diese Spec legt die Eigenschaften fest, die *Quellcode und Build* haben müssen, bevor die Arbeit als fertig gilt: Der Release-Build ist optimiert und wurde tatsächlich ausgeübt, keine Entwicklungshilfe überlebt in ihm, Stabilität und Plattformaktualität der App liegen innerhalb genannter Budgets, und eine Qualitätsschranke meldet Grün.

Die Umfangsgrenze, einmal genannt und tragend: Die Anforderungen dieses Repositorys stellen den Play-Store-*Release* außerhalb des Umfangs — Signaturschlüssel und ihre Verwahrung, Store-Metadaten, Einträge, Screenshots, Release-Tracks, gestufte Rollouts und der Data-Safety-Fragebogen gehören dem Betreiber, nicht einem Skill. Im Umfang ist alles, was den *Code* produktionsreif macht — genau das, was darüber entscheidet, ob ein Store-Release den Kontakt mit Nutzenden überstehen würde. Ein Skill **DARF NICHT [MUST NOT]** diese Spec als Erlaubnis lesen, den Store-Prozess anzufassen.

Provenienz: Schreibtischrecherche (August 2026) über die Dokumentation zu R8-Shrinking, -Obfuskation und -Optimierung, die Android Core App Quality Guidelines mit ihren prüfbaren Kriterien-IDs, die Android-Vitals-Schwellen (die quantifizierte Stabilitätsobergrenze), die StrictMode-Referenz sowie die Gradle-/AGP-Build-Dokumentation. Versionsgebundene Aussagen nennen ihre AGP-Grenze; diese Spec kodiert Mechanismen, keine exakten Versionen.

Grenzen: Sicherheitspflichten des Release-Builds — `android:debuggable=false`, keine committeten Secrets, Schwachstellen-Scan der Abhängigkeiten, die Regel „R8 ist keine Sicherheitsmaßnahme" — liegen in `spec/android/security/` §F/§G und werden referenziert, nicht wiederholt — mit einer bewussten Ausnahme, der `debuggable`-Regel, die §B wiederholt, damit die Schranke aus §E ohne das Öffnen einer zweiten Spec durchgegangen werden kann. Struktur der Build-Dateien, Version Catalog und Layout der Qualitätswerkzeuge liegen in `spec/android/project-structure/` §B/§G; was eine Testbahn *ist*, in `spec/android/test-automation/` §A/§D–§F und deren CI-Verdrahtung in dessen §G; Messung der Scroll-Performance in `spec/android/long-list-scrolling/` §G; Geräte- und Log-Mechanik in `spec/android/adb-workflows/`.

Leser: Autoren der Android-Skills dieses Repos, die entscheiden müssen, ob eine Änderung fertig ist, sowie Reviewer, die eine „Fertig"-Behauptung beurteilen.

## Ziele

- Den Release-Build, nicht den Debug-Build, zur Konfiguration machen, in der eine Änderung endgültig geprüft wird
- Jede Entwicklungshilfe — Debug-Bibliothek, ausführliches Log, Staging-Endpunkt, Bypass-Schalter — aus dem ausgelieferten Binary heraushalten
- Stabilität eine Zahl geben statt eines Eindrucks
- Die App bewusst statt durch Drift auf dem Stand von Plattform und Abhängigkeiten halten
- Eine Schranke definieren, deren Grün „fertig" bedeutet, und einen roten Zustand unmöglich unbemerkt lassen

## Nicht-Ziele

- Signaturschlüssel und ihre Verwahrung, Store-Metadaten, Einträge, Screenshots, Release-Tracks, gestufter Rollout und der Data-Safety-Fragebogen — per Anforderung außerhalb des Umfangs dieses Repositorys
- Sicherheitsmaßnahmen des Release-Builds — `spec/android/security/` §F/§G
- Zusammenstellung der Testbahnen — `spec/android/test-automation/` §A/§D–§F; Erstellung von CI-Workflows und Runner-Aufbau — dessen §G
- Methodik zur Messung von Startzeit und Jank sowie das Erstellen von Baseline Profiles — dafür existiert noch keine Spec (§Offene Fragen); die Budgets unten referenzieren sie, ohne die Methode zu definieren
- Versionsschemata und Changelog-Erzeugung — ein Release-Thema auf Portfolioebene, kein Android-Thema
- App-Größenoptimierung über die Vorgaben des Shrinkers hinaus

## Anforderungen

### A. Der Release-Build ist ein echter Build

- **MUSS [MUST]** Code-Shrinking, Optimierung, Obfuskation und Ressourcen-Shrinking für den Release-Build-Type aktivieren: ab AGP 9.3 über den Block `optimization { enable = true }`, davor über `isMinifyEnabled = true` plus `isShrinkResources = true` mit `proguard-android-optimize.txt` als Standarddatei [R1]
- **DARF NICHT [MUST NOT]** den Shrinker für Debug- oder Test-Build-Types aktivieren und **DARF NICHT [MUST NOT]** ihn für Release abschalten, um einen Fehler verschwinden zu lassen — ein Fehler unter R8 ist ein Defekt in der Keep-Konfiguration oder im reflektiven Code und wird dort behoben [R1]
- **MUSS [MUST]** Keep-Regeln spezifisch halten und gemäß der eingesetzten AGP-Generation ablegen (`src/<variant>/keepRules/*.keep` ab AGP 9.3, davor `proguardFiles`); pauschale Regeln (`-keep class ** { *; }`, `-dontobfuscate`, `-dontoptimize`) sind nicht konform, außer als dokumentierte, datierte und ticketgeführte Zwischenlösung [R1]
- **MUSS [MUST]** die `mapping.txt` jedes Release-Builds aufbewahren, der die Maschine verlässt, damit ein Stacktrace dieses Builds retraced werden kann [R1]
- **MUSS [MUST]** die Änderung auf einem echten Release-Build prüfen, bevor die Arbeit als fertig gilt — die Release-Variante auf einem Gerät installieren und den berührten Ablauf ausüben. R8 schreibt Code um, und reflexions- sowie serialisierungsbedingte Fehler zeigen sich nur dort [R1]
- **MUSS [MUST]** sicherstellen, dass die Release-Variante baut (`assembleRelease`, oder `bundleRelease`, wo ein Bundle das Artefakt ist), als Teil der Schranke in §E; das Artefakt zu erzeugen ist im Umfang, es zu veröffentlichen nicht
- **SOLLTE [SHOULD]** ein vorhandenes Startup-Profil und Baseline Profile beibehalten und **DARF NICHT [MUST NOT]** nach R8 arbeitende DEX-verändernde Werkzeuge einsetzen, die es entwerten würden [R1]

### B. Keine Entwicklungshilfe überlebt

- **MUSS [MUST]** Debug-only-Abhängigkeiten (Leak-Detektoren, Netzwerk-Inspektoren, Debug-Overlays, Test-Bibliotheken) auf `debugImplementation`/`testImplementation` beschränken; eine aus der Release-Variante erreichbare Debug-Bibliothek ist nicht konform [R2]
- **MUSS [MUST]** ausführliches und Debug-Logging aus dem Release-Build entfernen — entweder durch Strippen im Shrinker (was nur mit aktivierter Minification und vorhandener Regel funktioniert, gemäß `spec/android/security/` §A) oder durch eine release-sichere Logging-Implementierung, die diese Stufen verwirft
- **DARF NICHT [MUST NOT]** personenbezogene Daten, Credentials, Token oder Request-/Response-Nutzlasten auf irgendeiner Stufe loggen (`spec/android/security/` §A, `spec/android/backend-contract/` §B)
- **DARF NICHT [MUST NOT]** einen Nicht-Produktions-Endpunkt, eine Feature-Umgehung, einen Fake-Daten-Schalter oder einen versteckten Entwickler-Screen in der Release-Variante erreichbar lassen; die Umgebungswahl erfolgt über Build-Types oder Flavors zur Buildzeit, nie über einen an Nutzende ausgelieferten Laufzeitschalter
- **MUSS [MUST]** StrictMode ausschließlich in Debug-Builds aktivieren, mit Disk- und Netzwerkerkennung in der Thread-Policy und Leak-Erkennung in der VM-Policy, und **MUSS [MUST]** einen Verstoß beheben statt unterdrücken — ein StrictMode-Treffer im berührten Ablauf ist ein Defekt, keine Warnung [R3][R2]
- **DARF NICHT [MUST NOT]** `android:debuggable=true` ausliefern und **DARF NICHT [MUST NOT]** das TLS-Vertrauen aus Bequemlichkeit in einer Variante schwächen, die Produktivdaten erreichen kann (`spec/android/security/` §C/§F)

### C. Stabilitätsbudget

- **MUSS [MUST]** die Android-Vitals-Schwellen für schlechtes Verhalten als Obergrenze behandeln, nicht als Ziel: nutzerwahrgenommene Absturzrate 1,09 % und nutzerwahrgenommene ANR-Rate 0,47 % insgesamt, 8 % je Gerätemodell [R4]. Eine App, deren absturzfreie Rate unbekannt ist, erfüllt diese Anforderung nicht — der Messweg (In-App-Telemetrie oder Konsole) ist Voraussetzung, kein optionales Extra
- **DARF NICHT [MUST NOT]** Stabilität durch Verschlucken von Exceptions vortäuschen: Jede gefangene Exception wird entweder in einen nutzersichtbaren Zustand mit Wiederherstellungsaktion überführt oder erneut geworfen; ein leerer Catch-Block ist nicht konform
- **MUSS [MUST]** den Main-Thread frei von blockierender Arbeit halten, denn dort wird das ANR-Budget verbraucht — IO-, Datenbank- und Netzwerkarbeit laufen auf injizierten Dispatchern (`spec/android/app-architecture/` §E)
- **MUSS [MUST]** Prozesstod und Konfigurationswechsel überstehen, ohne Nutzereingaben oder ungesendete Schreibvorgänge zu verlieren (`spec/android/app-architecture/` §B), und **MUSS [MUST]** das für den berührten Ablauf ausdrücklich prüfen — die Entwickleroption „Activities nicht behalten" oder ein Hintergrund-Kill ist die mechanische Kontrolle
- **SOLLTE [SHOULD]** einen Crash-Reporting-Pfad für ausgelieferte Builds verdrahten; wo einer existiert, **MUSS [MUST]** er die Datenschutzregeln beachten (keine personenbezogenen Daten in Breadcrumbs), und das Hochladen von Symbolen/Mapping **MUSS [MUST]** Teil des Release-Builds sein, sonst sind die Reports unlesbar

### D. Aktualität von Plattform und Abhängigkeiten

- **MUSS [MUST]** `compileSdk` auf dem neuesten stabilen SDK und `targetSdk` auf dem neuesten stabilen SDK halten, gegen das die App geprüft wurde; ein zurückhängendes `targetSdk` wird mit Grund und Datum festgehalten, nie stillschweigend gelassen [R2]
- **MUSS [MUST]** `minSdk` mit Begründung festhalten und **MUSS [MUST]** den berührten Ablauf auf der neuesten Plattformversion erneut prüfen, die die App zu unterstützen behauptet [R2]
- **DARF NICHT [MUST NOT]** Non-SDK-(versteckte) Schnittstellen verwenden; der Lint-Check ist der mechanische Detektor [R2]
- **MUSS [MUST]** Abhängigkeiten über den Version Catalog deklarieren (`spec/android/project-structure/` §B) und **MUSS [MUST]** sie aktuell halten. Die Automatisierung und der Schwachstellen-Scan, die Aktualität praktikabel machen — Renovate/Dependabot plus ein Scanner in der CI —, liegen in `spec/android/security/` §F und sind dort ein **SOLLTE**; diese Spec verschärft bewusst das *Ergebnis* (Abhängigkeiten sind aktuell) zu einem MUSS und belässt die *Mechanismuswahl* jener Spec bei einer Empfehlung. Ein verhaltensändernder Abhängigkeits-Bump wird wie jede andere Änderung auf dem Release-Build geprüft
- **MUSS [MUST]** Plattform-Verhaltensänderungen, die das neue `targetSdk` aktiviert, vor dem Anheben behandeln — die Pflichten zu Adaptivität und Edge-to-Edge liegen in `spec/android/screen-formats/` §B/§D und `spec/android/app-design-navigation/` §A und sind Voraussetzung des Bumps, keine Nacharbeit

### E. Die Schranke

- **MUSS [MUST]** diese Schranke als Definition von „fertig" für jede Änderung an einem Android-Projekt behandeln und **MUSS [MUST]** jedes rote Element melden statt still hinnehmen (Repository-REQ-1, REQ-7):
  1. `./gradlew build` ist grün
  2. Android Lint meldet keinen Fund der Schwere Error in geändertem Code, und **es wurde kein neuer Baseline-Eintrag** dafür hinzugefügt; die in `spec/android/security/` §F genannten Sicherheitschecks werden auf Error-Schwere durchgesetzt — jene Spec formuliert die Durchsetzung als SOLLTE, diese Schranke verlangt sie, sodass ein Projekt, das sie nie angehoben hat, das vor dem Beanspruchen der Schranke nachholt
  3. Unit-Tests bestehen, einschließlich der Fehlerfallabdeckung, die `spec/android/app-architecture/` §G und `spec/android/backend-contract/` §G verlangen
  4. Die Release-Variante baut mit aktivem Shrinker (§A)
  5. Der berührte Ablauf wurde manuell auf einem Gerät mit der **Release**-Variante ausgeübt (§A)
  6. Jeder Punkt aus §B trifft auf diese Variante zu
- **DARF NICHT [MUST NOT]** eine Lint-Baseline anlegen oder erneuern, einen Check abschalten oder eine Unterdrückung annotieren, um die Schranke für neuen Code zu bestehen; ein Baseline-Eintrag ist nur für vorbestehende Altfunde da (`spec/android/project-structure/` §G)
- **MUSS [MUST]**, wenn ein Element der Schranke nicht ausführbar ist (kein Gerät angeschlossen, kein Backend erreichbar), im Abschlussbericht des Laufs nennen, welches übersprungen wurde und warum — ein nicht ausführbares Element gilt nie still als grün
- **SOLLTE [SHOULD]** die instrumentierten und Screenshot-Bahnen nach `spec/android/test-automation/` §G ausführen, wo die Änderung UI berührt
- **SOLLTE [SHOULD]** die Artefakt-Größendifferenz und jede wahrscheinlich verursachte Startzeit- oder Scroll-Regression melden, über die Messwege aus `spec/android/long-list-scrolling/` §G

### F. Festhalten

- **MUSS [MUST]** mit der Änderung jede von dieser Spec erlaubte Zwischenabweichung festhalten (eine pauschale Keep-Regel, ein zurückhängendes `targetSdk`, ein übersprungenes Schrankenelement), samt Grund und Bedingung für ihre Entfernung
- **MUSS [MUST]** einen nicht abgedeckten Fall melden, statt still zu entscheiden (Repository-REQ-6)

## Akzeptanzkriterien

Die Kriterien sind eine repräsentative Zusammenfassung von §A–§F, keine 1:1-Abbildung; jede Anforderung oben ist für sich normativ.

- [ ] Der Release-Build-Type aktiviert Code- und Ressourcen-Shrinking mit Optimierung; Debug- und Test-Build-Types nicht
- [ ] Keep-Regeln sind spezifisch und korrekt abgelegt; es existiert kein pauschales Keep, `-dontobfuscate` oder `-dontoptimize` ohne datierte, ticketgeführte Begründung
- [ ] `mapping.txt` wird für jeden Release-Build aufbewahrt, der die Maschine verlässt
- [ ] Der berührte Ablauf wurde aus der Release-Variante installiert und auf einem Gerät ausgeübt, und das Release-Artefakt baut
- [ ] Keine Debug-only-Abhängigkeit, kein ausführliches Log, kein Nicht-Produktions-Endpunkt, kein Bypass-Schalter und kein versteckter Entwickler-Screen ist in der Release-Variante erreichbar
- [ ] Die Release-Variante ist nicht debuggbar, keine Variante mit Zugriff auf Produktivdaten schwächt das TLS-Vertrauen, und auf keiner Stufe werden personenbezogene Daten, Credentials, Token oder Request-/Response-Nutzlasten geloggt
- [ ] Im berührten Ablauf läuft keine blockierende Arbeit auf dem Main-Thread
- [ ] StrictMode ist im Debug-Build mit Disk-, Netzwerk- und Leak-Erkennung aktiv, und der berührte Ablauf erzeugt keinen Verstoß
- [ ] Absturzfreie und ANR-Raten sind messbar und liegen innerhalb der Vitals-Schwellen; in geändertem Code existiert kein leerer Catch-Block
- [ ] Der berührte Ablauf übersteht Prozesstod und Konfigurationswechsel ohne Verlust von Nutzereingaben oder ungesendeten Schreibvorgängen, geprüft mit „Activities nicht behalten" oder einem Hintergrund-Kill statt per Inspektion
- [ ] Abhängigkeiten sind im Version Catalog deklariert und aktuell, und jede Plattform-Verhaltensänderung, die das eingesetzte `targetSdk` aktiviert, wurde vor dessen Übernahme behandelt
- [ ] `compileSdk` ist das neueste stabile, `targetSdk` das neueste geprüfte (jeder Rückstand mit Grund und Datum festgehalten), `minSdk` trägt eine Begründung, und keine Non-SDK-Schnittstelle wird verwendet
- [ ] Die sechs Elemente der Schranke aus §E sind grün, oder jedes rote oder übersprungene Element ist im Abschlussbericht mit Grund benannt
- [ ] Es wurde kein Lint-Baseline-Eintrag, keine Check-Abschaltung und keine Unterdrückung hinzugefügt, um die Schranke für neuen Code zu bestehen

## Offene Fragen

Jede Frage nennt die Vorgabe, die die Anforderungen oben bereits kodieren.

- Für die app-weite Methodik zu Startzeit (TTID/TTFD) und Jank existiert in diesem Korpus keine Spec; die Fähigkeit zur gefühlten Performance arbeitet ohne eine. Soll sie eine eigene Spec bekommen, oder soll §E quantifizierte Startzeitbudgets erhalten? Vorgabe: §E verlangt einen Regressions-*Bericht*, keine feste Zahl
- Soll Crash-Reporting für die eigenen Apps des Betreibers ein MUSS statt eines SOLLTE sein, da das Vitals-Budget ohne es nicht prüfbar ist? Vorgabe: SOLLTE, weil der Messweg auch die Play Console sein kann
- Soll die Schranke zusätzlich zu einer Upgrade-Installation eine Neuinstallation verlangen (Migrationspfade brechen nur bei Ersterer)? Vorgabe: nicht verlangt; der manuelle Schritt aus §E legt den Installationsmodus nicht fest
- Lohnt sich eine feste Schwelle für die Größendifferenz (etwa: jede Änderung markieren, die mehr als *n* KB hinzufügt), oder genügt der Bericht? Vorgabe: nur der Bericht

## Referenzen

- [R1] Shrink, obfuscate, and optimize your app (R8) — Aktivierung des Shrinkers, Keep-Regeln, Ressourcen-Shrinking, `mapping.txt`, „always test the release build", Vorbehalt zu DEX-verändernden Werkzeugen: <https://developer.android.com/build/shrink-code>
- [R2] Core app quality guidelines — prüfbare Kriterien, u. a. `Production_Build_Quality`, `StrictMode_Compliance`, `Target_SDK_Version`, `Compile_SDK_Version`, `Non_SDK_Interfaces`, `SDK_Maintenance`, `Sensitive_Data_Logging`: <https://developer.android.com/docs/quality-guidelines/core-app-quality>
- [R3] StrictMode — Thread- und VM-Policies, Penalties, Debug-only-Leitlinie: <https://developer.android.com/reference/android/os/StrictMode>
- [R4] Android vitals — Core Vitals und Schwellen für schlechtes Verhalten (nutzerwahrgenommene Absturzrate 1,09 %, ANR-Rate 0,47 %, 8 % je Gerät; 28-Tage-Rollfenster): <https://developer.android.com/topic/performance/vitals>
- [R5] Android Lint — Ausführung, Schweregrade und Baselines: <https://developer.android.com/studio/write/lint>
- [R6] Configure build variants — Build-Types, Flavors und variantenbezogene Abhängigkeiten: <https://developer.android.com/build/build-variants>
