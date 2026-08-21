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
- Methodik zur Messung von Startzeit und Jank sowie das Erstellen von Baseline Profiles — liegen in `spec/android/perceived-performance/` §D–§F; §E dieser Spec konsumiert deren Regressions-*Bericht* und definiert die Methode nicht (siehe §Offene Fragen zur Frage einer harten Schranke)
- Versionsschemata und Changelog-Erzeugung — ein Release-Thema auf Portfolioebene, kein Android-Thema
- App-Größenoptimierung über die Vorgaben des Shrinkers hinaus

## Anforderungen

### A. Der Release-Build ist ein echter Build

- **MUSS [MUST]** Code-Shrinking, Optimierung, Obfuskation und Ressourcen-Shrinking für den Release-Build-Type aktivieren: ab AGP 9.3 über den Block `optimization { enable = true }`, davor über `isMinifyEnabled = true` plus `isShrinkResources = true` mit `proguard-android-optimize.txt` als Standarddatei [R1]
- **DARF NICHT [MUST NOT]** den Shrinker für Debug- oder Test-Build-Types aktivieren und **DARF NICHT [MUST NOT]** ihn für Release abschalten, um einen Fehler verschwinden zu lassen — ein Fehler unter R8 ist ein Defekt in der Keep-Konfiguration oder im reflektiven Code und wird dort behoben [R1]
- **MUSS [MUST]** Keep-Regeln spezifisch halten und gemäß der eingesetzten AGP-Generation ablegen (`src/<variant>/keepRules/*.keep` ab AGP 9.3, davor `proguardFiles`); pauschale Regeln (`-keep class ** { *; }`, `-dontobfuscate`, `-dontoptimize`) sind nicht konform, außer als dokumentierte, datierte und ticketgeführte Zwischenlösung [R1]. `getDefaultProguardFile("proguard-android.txt")` wird ab AGP 9 nicht mehr unterstützt, weil es `-dontoptimize` enthält; der Standardsatz ist `proguard-android-optimize.txt`, in der DSL ab AGP 9.3 implizit enthalten und nur bewusst über `optimization { keepRules { includeDefault = false } }` weglassbar [R1][R7]. R8 läuft auf AGP 9 per Default im Strict-Full-Mode (eine gehaltene Klasse hält ihren Default-Konstruktor nicht mehr implizit), eine Keep-Regel benennt also den Konstruktor, den sie braucht (`spec/android/project-structure/` §B)
- **MUSS [MUST]** die `mapping.txt` jedes Release-Builds aufbewahren, der die Maschine verlässt, damit ein Stacktrace dieses Builds retraced werden kann [R1]
- **MUSS [MUST]** die Änderung auf einem echten Release-Build prüfen, bevor die Arbeit als fertig gilt — die Release-Variante auf einem Gerät installieren und den berührten Ablauf ausüben. R8 schreibt Code um, und reflexions- sowie serialisierungsbedingte Fehler zeigen sich nur dort [R1]
- **MUSS [MUST]** sicherstellen, dass die Release-Variante baut (`assembleRelease`, oder `bundleRelease`, wo ein Bundle das Artefakt ist), als Teil der Schranke in §E; das Artefakt zu erzeugen ist im Umfang, es zu veröffentlichen nicht
- **SOLLTE [SHOULD]** ein vorhandenes Startup-Profil und Baseline Profile beibehalten und **DARF NICHT [MUST NOT]** nach R8 arbeitende DEX-verändernde Werkzeuge einsetzen, die es entwerten würden [R1]

### B. Keine Entwicklungshilfe überlebt

- **MUSS [MUST]** Debug-only-Abhängigkeiten (Leak-Detektoren, Netzwerk-Inspektoren, Debug-Overlays, Test-Bibliotheken) auf `debugImplementation`/`testImplementation` beschränken; eine aus der Release-Variante erreichbare Debug-Bibliothek ist nicht konform [R2]
- **MUSS [MUST]** ausführliches und Debug-Logging aus dem Release-Build entfernen — entweder durch Strippen im Shrinker (was nur mit gemäß §A aktiviertem Shrinker und vorhandener Regel funktioniert — `spec/android/logging/` §G besitzt, welche Regel und wohin sie gehört) oder durch eine release-sichere Logging-Implementierung, die diese Stufen verwirft
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

- **MUSS [MUST]** `compileSdk` auf dem neuesten stabilen SDK und `targetSdk` auf dem neuesten stabilen SDK halten, gegen das die App geprüft wurde; ein zurückhängendes `targetSdk` wird mit Grund und Datum festgehalten, nie stillschweigend gelassen [R2]. Der Rückstand ist durch die Target-API-Regel des Stores begrenzt, die diese Spec als äußere Grenze übernimmt, obwohl das Store-*Release* außerhalb des Umfangs liegt: seit 2026-08-31 müssen neue Apps und App-Updates API 36 anvisieren (eine Verlängerung bis 2026-11-01 kann in der Console beantragt werden), und eine bestehende App unter API 35 wird neuen Nutzern auf neueren OS-Versionen nicht mehr angeboten [R8]. Ein festgehaltener Rückstand, der diese Linie überschreitet, ist ein Defekt, keine Abweichung. Auf AGP 9 fällt ein ungesetztes `targetSdk` auf `compileSdk` zurück (`spec/android/project-structure/` §B), beurteilt wird also der *effektive* Wert
- **MUSS [MUST]** `minSdk` mit Begründung festhalten und **MUSS [MUST]** den berührten Ablauf auf der neuesten Plattformversion erneut prüfen, die die App zu unterstützen behauptet [R2]
- **DARF NICHT [MUST NOT]** Non-SDK-(versteckte) Schnittstellen verwenden; der Lint-Check ist der mechanische Detektor [R2]
- **MUSS [MUST]** Abhängigkeiten über den Version Catalog deklarieren (`spec/android/project-structure/` §B) und **MUSS [MUST]** sie aktuell halten. Die Automatisierung und der Schwachstellen-Scan, die Aktualität praktikabel machen — Renovate/Dependabot plus ein Scanner in der CI —, liegen in `spec/android/security/` §F und sind dort ein **SOLLTE**; diese Spec verschärft bewusst das *Ergebnis* (Abhängigkeiten sind aktuell) zu einem MUSS und belässt die *Mechanismuswahl* jener Spec bei einer Empfehlung. Ein verhaltensändernder Abhängigkeits-Bump wird wie jede andere Änderung auf dem Release-Build geprüft
- **MUSS [MUST]** Plattform-Verhaltensänderungen, die das neue `targetSdk` aktiviert, vor dem Anheben behandeln — die Pflichten zu Adaptivität und Edge-to-Edge liegen in `spec/android/screen-formats/` §B/§D und `spec/android/app-design-navigation/` §A und sind Voraussetzung des Bumps, keine Nacharbeit
- **MUSS [MUST]** die dokumentierte Verhaltensänderungsliste des zu übernehmenden `targetSdk` durchgehen und das Urteil je Punkt festhalten, mindestens für API 36 [R9]: Predictive Back ist per Default aktiv (`onBackPressed` wird nicht aufgerufen und `KEYCODE_BACK` nicht mehr zugestellt; `android:enableOnBackInvokedCallback="false"` ist ein befristeter Opt-out, den das Predictive-Back-MUSS aus `spec/android/app-design-navigation/` §D nicht als Dauerzustand erlaubt), Orientierungs-, Resizability- und Seitenverhältnis-Einschränkungen werden auf Displays ab 600 dp kleinster Breite ignoriert, und der Edge-to-Edge-Opt-out (`windowOptOutEdgeToEdgeEnforcement`) ist auf Android-16-Geräten deprecated und deaktiviert
- **MUSS [MUST]** 16-KB-Page-Size-kompatiblen nativen Code ausliefern: jede App mit `.so`-Dateien — direkt oder über ein SDK wie ML Kit oder eine Datenbank-Engine — wird mit AGP ≥ 8.5.1 gebaut, das unkomprimierte Shared Libraries auf 16-KB-Grenzen zip-aligned, solange `packaging { jniLibs { useLegacyPackaging } }` auf seinem `false`-Default bleibt (auf AGP ≤ 8.5 ist der dokumentierte Workaround `useLegacyPackaging = true` — komprimierte Bibliotheken werden bei der Installation entpackt und brauchen kein Alignment, auf Kosten der Installationsgröße) und mit NDK ≥ r28 oder den expliziten Linker-Flags `-Wl,-z,max-page-size=16384`, und das Alignment wird am Release-Artefakt geprüft — die *Alignment*-Spalte des APK Analyzers, `check_elf_alignment.sh <apk>` oder `zipalign -c -P 16 -v 4 <apk>` [R10]. Play verlangt es seit 2025-11-01 für neue Apps und Updates mit targetSdk ≥ 35 und ab 2027-02-01 für alle App-Updates [R10][R11]; eine App ohne nativen Code erfüllt diesen Punkt, indem sie das festhält

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

- **MUSS [MUST]** mit der Änderung jede von dieser Spec erlaubte Zwischenabweichung festhalten (eine pauschale Keep-Regel, ein zurückhängendes `targetSdk`, ein übersprungenes Schrankenelement), samt Grund und Bedingung für ihre Entfernung; Toolchain- und Dependency-Upgrades werden in `project/toolchain-log.md` festgehalten, neben den übrigen Entscheidungsartefakten des Repositories
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
- [ ] Jede von dieser Spec erlaubte Zwischenabweichung (pauschale Keep-Regel, zurückhängendes `targetSdk`, übersprungenes Schrankenelement) ist mit der Änderung samt Grund und Ablösebedingung festgehalten; ein zurückhängendes `targetSdk` bleibt innerhalb des Target-API-Fensters des Stores
- [ ] Native Bibliotheken sind, wo vorhanden, am Release-Artefakt 16-KB-aligned und die Prüfmethode ist benannt; die Verhaltensänderungsliste des übernommenen `targetSdk` wurde Punkt für Punkt durchgegangen

## Offene Fragen

Jede Frage nennt die Vorgabe, die die Anforderungen oben bereits kodieren.

- Die app-weite Methodik zu Startzeit (TTID/TTFD) und Jank liegt in `spec/android/perceived-performance/`. Soll §E zusätzlich hart gegen dessen Startbudget schranken oder ein Regressions-*Bericht* bleiben? Vorgabe: ein Bericht, damit ein langsamer, aber nicht regressierter Screen keine Änderung blockiert, die ihn nicht verursacht hat
- Soll Crash-Reporting für die eigenen Apps des Betreibers ein MUSS statt eines SOLLTE sein, da das Vitals-Budget ohne es nicht prüfbar ist? Vorgabe: SOLLTE, weil der Messweg auch die Play Console sein kann
- Soll die Schranke zusätzlich zu einer Upgrade-Installation eine Neuinstallation verlangen (Migrationspfade brechen nur bei Ersterer)? Vorgabe: nicht verlangt; der manuelle Schritt aus §E legt den Installationsmodus nicht fest
- Lohnt sich eine feste Schwelle für die Größendifferenz (etwa: jede Änderung markieren, die mehr als *n* KB hinzufügt), oder genügt der Bericht? Vorgabe: nur der Bericht

## Referenzen

- [R1] Enable app optimization with R8 — die `optimization {}`-DSL ab AGP 9.3 und der frühere `isMinifyEnabled`/`isShrinkResources`-Pfad, `keepRules`-Source-Set, `proguard-android.txt` entfallen, „always test the release build", Vorbehalt zu DEX-verändernden Werkzeugen (die frühere URL `/build/shrink-code` leitet hierher weiter): <https://developer.android.com/topic/performance/app-optimization/enable-app-optimization>
- [R2] Core app quality guidelines — prüfbare Kriterien, u. a. `Production_Build_Quality`, `StrictMode_Compliance`, `Target_SDK_Version`, `Compile_SDK_Version`, `Non_SDK_Interfaces`, `SDK_Maintenance`, `Sensitive_Data_Logging`: <https://developer.android.com/docs/quality-guidelines/core-app-quality>
- [R3] StrictMode — Thread- und VM-Policies, Penalties, Debug-only-Leitlinie: <https://developer.android.com/reference/android/os/StrictMode>
- [R4] Android vitals — Core Vitals und Schwellen für schlechtes Verhalten (nutzerwahrgenommene Absturzrate 1,09 %, ANR-Rate 0,47 %, 8 % je Gerät; 28-Tage-Rollfenster): <https://developer.android.com/topic/performance/vitals>
- [R5] Android Lint — Ausführung, Schweregrade und Baselines: <https://developer.android.com/studio/write/lint>
- [R6] Configure build variants — Build-Types, Flavors und variantenbezogene Abhängigkeiten: <https://developer.android.com/build/build-variants>
- [R7] Keep rules overview — Standard-Keep-Regeln, `optimization { keepRules { includeDefault = false } }`, Migration weg von `proguard-android.txt`: <https://developer.android.com/topic/performance/app-optimization/keep-rules-overview>
- [R8] Google-Play-Target-API-Level-Anforderungen — API 36 für neue Apps und Updates ab 2026-08-31, Verlängerung bis 2026-11-01, bestehende Apps unter API 35 für neue Nutzer ausgeblendet: <https://developer.android.com/google/play/requirements/target-sdk>
- [R9] Android-16-Verhaltensänderungen für Apps mit targetSdk 36 — Predictive Back per Default und `enableOnBackInvokedCallback`-Opt-out, Large-Screen-Orientierungs-/Resizability-Einschränkungen ignoriert, `windowOptOutEdgeToEdgeEnforcement` deaktiviert: <https://developer.android.com/about/versions/16/behavior-changes-16>
- [R10] Support 16 KB page sizes — AGP-8.5.1-Alignment, `useLegacyPackaging`, NDK-r28-Default, Linker-Flags, Prüfung per APK Analyzer / `check_elf_alignment.sh` / `zipalign -c -P 16`, Update-Stichtag 2027-02-01: <https://developer.android.com/guide/practices/page-sizes>
- [R11] Android Developers Blog — Plays 16-KB-Anforderung für neue Apps und Updates mit Android 15+ ab 2025-11-01: <https://android-developers.googleblog.com/2025/05/prepare-play-apps-for-devices-with-16kb-page-size.html>
