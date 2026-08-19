# Android-Testautomatisierung

Status: draft

## Kontext

Die Skills dieses Repositories generieren, erweitern, auditieren und debuggen Android-Apps; jeder Skill-Lauf muss ein Projekt hinterlassen, das grün baut (`project/requirements/android-engineering-skills.md`, REQ-1). Diese Garantie ist nur so stark wie die automatisierte Testsuite des Projekts. Diese Spec ist die autoritative Definition dafür, wie automatisierte Tests in einem Android-App-Projekt strukturiert sind, welche Frameworks sie tragen und wie sie in CI laufen — das Fundament, gegen das die testbezogenen Skills (Projekt-Setup, Compose-UI, Debugging) generieren und auditieren.

Der Inhalt ist aus einem Recherche-Durchlauf (August 2026) über drei Quellklassen destilliert: offizielle Google-Test-Guidance (developer.android.com/training/testing, Compose-Testing, Coroutines-/Hilt-Testing, Gradle Managed Devices), die Dokumentation der Werkzeuge selbst (Roborazzi, Paparazzi, Compose Preview Screenshot Testing, kotlinx-coroutines-test, Turbine, Kover) sowie live inspizierte Referenzprojekte (Now in Android als Flaggschiff, DuckDuckGo Android, Signal Android, Tivi, compose-samples). Wo Googles Guidance und Produktionspraxis auseinandergehen (Mocking, Turbine-Adoption), hält die Spec die Divergenz fest, statt sie zu verstecken.

Abgrenzung zur Schwester-Spec: `spec/android/project-structure/` §F besitzt die Test-*Platzierung* (Tests liegen im getesteten Modul, `src/test/` vs. `src/androidTest/`, geteilte Fixtures in `:core:testing`, konsistentes Naming). Diese Spec besitzt Test-*Strategie, Frameworks und Automatisierung* und referenziert Platzierungsregeln, statt sie zu wiederholen. Performance-Benchmarks (Macrobenchmark/Microbenchmark) sind außer ihrer Grenze zur funktionalen Suite außerhalb des Scopes; sie gehören zu `spec/android/perceived-performance/`.

Leser: Autoren der Android-Skills dieses Repos sowie Reviewer, die beurteilen, ob die Testsuite eines generierten oder auditierten Projekts konform ist.

## Ziele

- Eine Teststrategie definieren, die Defekte auf der billigsten Ebene fängt: viele schnelle JVM-Tests, wenige Instrumented-Tests, bewusste Eskalation nur wenn die Fidelity es verlangt
- Den Framework-Stack je Testart (Unit, Compose-UI, Screenshot, Instrumented, End-to-End) festlegen, damit generierte Projekte konsistent und auditierbar sind
- Suiten konstruktiv deterministisch machen — keine Sleeps, keine unbehandelte Flakiness, stattdessen virtuelle Zeit und Synchronisations-APIs
- Die CI-Verdrahtung definieren (Tasks, Caching, Artefakte, Coverage, Flake-Handling), sodass ein lokaler Pass einen CI-Pass vorhersagt
- Ehrlich skalieren: die minimal tragfähige Suite für eine Solo-Entwickler-App benennen und den additiven Pfad für größere Projekte

## Nicht-Ziele

- Test-Platzierung, Namensschemata und Fixture-Modul-Layout — gehören `spec/android/project-structure/` §F und §C
- Performance-Benchmarking (Macrobenchmark/Microbenchmark, Baseline Profiles) — hier wird nur die Grenze gezogen; die Praxis gehört zu `spec/android/perceived-performance/` §F/§G
- Play-Store-Pre-Launch-Reports und Release-Track-Gerätefarmen — Release ist für dieses Repository außerhalb des Scopes
- CI-Pipeline-Architektur jenseits der Test-Jobs — gehört den Portfolio-CI/CD-Specs
- Festschreiben exakter Tool-Versionen — Mechanismen und Tool-Entscheidungen sind fixiert; Versionen leben im Version Catalog des Projekts

## Anforderungen

### A. Teststrategie

- **MUSS [MUST]** Tests als Pyramide verteilen: zahlreiche kleine JVM-Tests an der Basis, wenige große End-to-End-Tests an der Spitze; für jeden neuen Test die niedrigste Ebene nutzen, die adäquates Feedback liefert
- **MUSS [MUST]** *Scope* (Unit → Component → Feature → Application) und *Ausführungsort* (lokale JVM vs. Instrumented auf Gerät) als unabhängige Dimensionen behandeln — ein Feature-UI-Test kann weiterhin auf der JVM laufen (Robolectric), und Scope-Eskalation bedeutet nie automatisch Geräte-Eskalation
- **MUSS [MUST]** mindestens unit-testen: ViewModels (State-Erzeugung für Normal- *und* Edge-Cases — Fehler, leere Daten, korrupte Eingaben), Repositories und Data-Layer-Logik, Use Cases sowie nicht-trivialen Utility-Code
- **DARF NICHT [MUST NOT]** Framework-Einstiegspunkte (Activities, Services) oder Framework-/Library-Verhalten selbst unit-testen; Logik, die das erfordern würde, wird stattdessen aus dem Einstiegspunkt herausgezogen
- **MUSS [MUST]** die kritischen Nutzerinteraktionen jedes Screens mit einem UI-Test gegen das zustandslose Content-Composable abdecken und die häufigsten Navigationspfade mit einer kleinen Zahl von Journey-Tests
- **SOLLTE [SHOULD]** die konkrete Teststrategie des Projekts (welche Ebenen existieren, was einen Merge gatet) in einem kurzen Dokument — `project/test-strategy.md` — oder der CLAUDE.md des Projekts festhalten, gemäß Googles Strategie-Guidance
- **SOLLTE [SHOULD]** die Architektur konstruktiv testbar halten: keine Business-Logik in Framework-Einstiegspunkten, kein `Context` in ViewModels, alle Abhängigkeiten hinter Interfaces injiziert — die Architekturregeln in `spec/android/project-structure/` §E sind der Enabler und werden hier nicht wiederholt

### B. Lokale Unit-Tests (JVM)

- **MUSS [MUST]** Tests als JUnit-4-Testklassen schreiben — der Runner-Pfad, den Googles Guidance und AndroidX Test dokumentieren [R5]. JUnit 5 ist ein **KANN [MAY]**, und die Mechanik unterscheidet sich je Host: *lokale JVM*-Unit-Tests brauchen kein Drittanbieter-Plugin — AGPs lokale Unit-Test-Tasks sind Gradle-`Test`-Tasks (`testOptions.unitTests.all { it.useJUnitPlatform() }`) [R27][R28]; *Instrumented*-Tests auf JUnit 5 brauchen das Community-Plugin `android-junit5` samt Runner-Support und die dort dokumentierte Geräte-Untergrenze (Android 8.0/API 26 für JUnit 5, API 35 für JUnit 6) [R29]. Generierter Code **DARF NICHT [MUST NOT]** JUnit 5 in einem der beiden Hosts voraussetzen
- **MUSS [MUST]** `kotlinx-coroutines-test` verwenden: jeder Coroutine-Testkörper läuft in `runTest`, mit genau einem `TestScheduler`, den alle `TestDispatcher` eines Tests teilen
- **MUSS [MUST]** den Main-Dispatcher in ViewModel-Tests über eine `MainDispatcherRule` ersetzen (TestWatcher um `Dispatchers.setMain`/`resetMain`); **MUSS [MUST]** Dispatcher in Produktionsklassen injizieren statt `Dispatchers.IO`/`Default` hartzukodieren
- **DARF NICHT [MUST NOT]** `Thread.sleep` aufrufen oder in irgendeinem Test Wanduhrzeit abwarten; virtuelle Zeit (`advanceUntilIdle`, `advanceTimeBy`) und Synchronisations-APIs sind die einzigen Wartemechanismen
- **SOLLTE [SHOULD]** in State-Holder-Tests auf `StateFlow.value` assertieren (StateFlow als Datenhalter behandeln); steht ein `stateIn(WhileSubscribed)`-Flow unter Test, muss vor dem Assertieren ein Collector aktiv sein
- **KANN [MAY]** Turbine für Emissionsreihenfolge- und Hot-Flow-Tests nutzen; es ist Bequemlichkeit, nicht Baseline — Referenzprojekte assertieren überwiegend via `first()`/`value`
- **DARF NICHT [MUST NOT]** Robolectric für einfache Unit-Tests verwenden — es ist letzter Ausweg für Legacy-Code oder Android-Klassen-Abhängigkeiten; seine sanktionierten Rollen sind UI-Verhaltenstests und Screenshots (§D, §E)
- **SOLLTE [SHOULD]** genau eine Assertion-Library wählen und repo-weit konsistent nutzen; `kotlin.test` ist der Default für Kotlin-first-Projekte (aktuelle Flaggschiff-Sample-Praxis), `assertk` oder Truth sind akzeptable Alternativen

### C. Test-Doubles

- **MUSS [MUST]** Fakes gegenüber Mocks bevorzugen: handgeschriebene Test-Implementierungen hinter demselben Interface, mit Test-only-Hooks (zum Beispiel ein Fake-Repository auf Basis eines `MutableSharedFlow(replay = 1)` plus einer imperativen `send…`-Methode)
- **DARF NICHT [MUST NOT]** eigene Business-Logik, Datenklassen oder Repositories des Projekts mocken; **KANN [MAY]** eine Mocking-Library (MockK/Mockito) an echten Systemgrenzen einsetzen, wo Interaktionsverifikation der Zweck ist — Produktions-Apps tun das nachweislich, und die Spec erlaubt es nur dort
- **DARF NICHT [MUST NOT]** tiefe Mock-Graphen („complex mocks") oder Spies aufbauen; eine schwer zu fakende Abhängigkeit zeigt ein Seam-Problem im Design an, das zu beheben ist
- **MUSS [MUST]** ViewModels in Unit-Tests direkt mit Fakes konstruieren (manuelle Konstruktor-Injektion); Hilt wird in Unit-Tests nicht verwendet
- **MUSS [MUST]** in Hilt-basierten Integrations-/UI-Tests `@HiltAndroidTest` + `HiltAndroidRule(order = 0)` mit einem Hilt-Test-Runner verwenden und Bindings je Ersetzungs-Scope via `@TestInstallIn` (Default), `@UninstallModules` oder `@BindValue` ersetzen
- Die Platzierung geteilter Fakes, Rules und Testdaten in einem `:core:testing`-artigen Modul regelt `spec/android/project-structure/` §F

### D. Compose-UI-Tests

- **MUSS [MUST]** Screen-UI gegen das zustandslose Content-Composable mit Fake-`uiState`-Werten und No-op-Event-Lambdas testen — jeder UI-Zustand (Loading, Populated, Error) ist ohne ViewModel konstruierbar; der Route-/Content-Split aus `spec/android/project-structure/` §E ist der Enabler
- **MUSS [MUST]** Knoten primär über Semantics matchen (Text via Ressourcen-Lookup, Content Descriptions, Rollen/Zustände); `testTag` ist letzter Ausweg für Container ohne eigene Semantik — semantisches Matching hält die App accessible und den Test locale-sicher
- **MUSS [MUST]** auf die Test-Synchronisation von Compose bauen: Auto-Sync als Default, `mainClock`-Steuerung für Animationen, `waitUntil`/`waitUntilExactlyOneExists` für externe Arbeit — niemals Sleeps, und Idling Resources nur in kleinen Interop-Tests
- **SOLLTE [SHOULD]** Feature-Level-Compose-Tests auf Robolectric hosten (`src/test/`, `isIncludeAndroidResources = true`) — offiziell für Compose unterstützt, schnell und CI-billig; die bekannten Grenzen (kein echter Screen, kein WebView, keine System-UI, reduzierte Rendering-Fidelity) eskalieren genau diese Fälle zu Instrumented-Tests
- **SOLLTE [SHOULD]** eine kleine Zahl von Ganz-App-Integrationstests (echte Activity, Hilt, echte Navigation) im `:app`-Modul halten; Feature-Module bleiben auf der `ComponentActivity`-/Fake-State-Ebene
- **SOLLTE [SHOULD]** in Hilt-Projekten eine `@AndroidEntryPoint ComponentActivity` in einem kleinen dedizierten Test-Manifest-Modul bereitstellen (das `ui-test-hilt-manifest`-Muster), damit Compose-Tests Hilt-injizierten Content hosten können
- **SOLLTE [SHOULD]** `rememberSaveable`-Restauration mit `StateRestorationTester` verifizieren; **KANN [MAY]** Activity-Recreation via `ActivityScenario.recreate()` und echten Process-Death via UI Automator abdecken, wo das Risiko es rechtfertigt
- **SOLLTE [SHOULD]** `DeviceConfigurationOverride` (erzwungene Größe, Dark Mode, Font Scale, Locales) nutzen, um Konfigurationsvarianten ohne Geräte zu testen
- **MUSS [MUST]** beim Testen von Navigation-3-Screens den Back-Stack als einfachen State behandeln: einen Test-`NavDisplay` mit dem `entryProvider` des Features aufbauen und auf den Back-Stack-Inhalt assertieren; Navigations-Callbacks bleiben injizierte Lambdas, nie ein durchgereichter Controller

### E. Screenshot- und Accessibility-Tests

- **SOLLTE [SHOULD]** Screenshot-Tests auf der JVM ausführen (ohne Geräte): das Default-Werkzeug für einen Robolectric-Stack ist Roborazzi (`@GraphicsMode(NATIVE)`, Record-/Verify-/Compare-Gradle-Tasks); Paparazzi ist ein **KANN [MAY]** für reine Design-System-Module ohne Runtime-Bedarf; Googles Compose Preview Screenshot Testing ist ein **KANN [MAY]**, solange es alpha bleibt (`com.android.compose.screenshot` 0.0.1-alpha15 zum Recherchezeitpunkt — die volle IDE-Integration braucht AGP ≥ 9.0 und Kotlin ≥ 2.2.10, die Gradle-Tasks allein AGP ≥ 8.5.0; die APIs können sich noch erheblich ändern) [R21]
- **MUSS [MUST]** Goldens auf genau einer Plattform aufnehmen (CI/Linux) — Text-Rendering unterscheidet sich zwischen Betriebssystemen; ein am Arbeitsplatz aufgenommenes Golden-Set ist Drift per Konstruktion. Goldens werden pro Modul eingecheckt (Platzierung per `spec/android/project-structure/` §F)
- **MUSS [MUST]** Screenshots in CI auf jedem PR verifizieren, sobald Screenshot-Tests existieren; Vergleichsbilder werden als Build-Artefakte hochgeladen; ein Auto-Record-Commit-Bot für Same-Repo-PRs ist ein **KANN [MAY]**
- **SOLLTE [SHOULD]** Accessibility-Test-Framework-Checks in die Suite integrieren: `enableAccessibilityChecks()`/`tryPerformAccessibilityChecks()` in Compose-Tests (Compose ≥ 1.8) oder ATF-Hooks im Screenshot-Helper, mit ausschließlich benannten, begründeten Suppressions
- **DARF NICHT [MUST NOT]** automatisierte Accessibility-Checks als Ersatz für manuelle TalkBack-/Accessibility-Scanner-Durchgänge behandeln; die Automatisierung ist ein Regressionsnetz, kein Audit

### F. Instrumented- und End-to-End-Tests

- **MUSS [MUST]** Instrumented-Tests für Verhalten reservieren, das echt ein Gerät oder einen Emulator erfordert (System-UI, WebView, Hardware-Rendering, echter Process-Death, Release-Build-Verifikation); alles andere läuft zuerst auf der JVM
- **MUSS [MUST]** Instrumented-Suiten über AndroidX Test mit `AndroidJUnitRunner` (oder dem Hilt-Runner des Projekts) ausführen; **SOLLTE [SHOULD]** den Android Test Orchestrator mit `clearPackageData` aktivieren, damit jeder Test in seiner eigenen Invocation mit sauberem State läuft
- **SOLLTE [SHOULD]** UI Automator (2.4+-API) für Cross-App- und System-Oberflächen-Interaktionen sowie für Release-Build-Verifikation (minifiziert) nutzen; er ist kein Ersatz für In-Process-Compose-Tests
- **KANN [MAY]** eine Handvoll Maestro-Smoke-Journeys für geräteechte Flows ergänzen — additive Bequemlichkeit außerhalb des Gradle-/JUnit-Ökosystems (keine Test-Doubles, kein Hilt), nie die primäre UI-Test-Ebene
- **MUSS [MUST]** flaky Tests fixen, statt Retries zu institutionalisieren: Retries sind ein **SOLLTE [SHOULD]** für große/Instrumented-Tests als Produktivitätsbrücke und ein **DARF NICHT [MUST NOT]** als dauerhafter Ersatz für einen Fix; Flake-Tracking folgt den Portfolio-Workflow-Health-Konventionen
- **MUSS [MUST]** die Performance-Grenze ziehen: Macrobenchmark-/Microbenchmark-Läufe sind eine separate, geplante (nächtliche) Spur auf physischen Geräten — nie Teil der funktionalen Per-Commit-Suite

### G. CI-Automatisierung

- **MUSS [MUST]** auf jedem PR ausführen: die Unit-Tests genau einer Debug-Variante (variantenbewusster Task, zum Beispiel `testDebug` — nie das All-Varianten-Aggregat `test`) plus Lint; die Invocation läuft über dieselben Taskfile-/Gradle-Einstiege wie lokal
- **MUSS [MUST]** JUnit-XML-Ergebnisse als Build-Artefakte hochladen (`if: !cancelled()`); **SOLLTE [SHOULD]** sie über eine Report-Action als PR-Annotationen anzeigen
- **MUSS [MUST]** für Emulator-Jobs auf GitHub-gehosteten Linux-Runnern KVM aktivieren (die dokumentierte udev-Regel) — Hardware-Beschleunigung ist seit 2024 verfügbar, und unbeschleunigte Emulatoren sind eine Flake-Quelle
- **SOLLTE [SHOULD]** PR-blockierende Instrumented-Tests (sofern vorhanden) über die Emulator-Runner-Action mit kleiner API-Level-Matrix, deaktivierten Animationen und AVD-Snapshot-Caching ausführen; Gradle Managed Devices sind ein **KANN [MAY]** — bevorzugt für reproduzierbare API-Matrizen und geplante Spuren, zweite Wahl für PR-blockierende Jobs angesichts der CI-Stabilitätsberichte; ATD-Images beschleunigen Suiten, können aber keine Hardware-Rendering-Screenshot-Tests hosten
- **SOLLTE [SHOULD]** große Instrumented-Suiten sharden (Runner-Sharding, GMD-Shards oder Smart Sharding einer Gerätefarm), statt die Wanduhrzeit eines Jobs unbegrenzt wachsen zu lassen
- **SOLLTE [SHOULD]** Coverage mit Kover für Kotlin-Multi-Modul-JVM-Suiten messen (Aggregation eingebaut); Jacoco bleibt der Fallback, sobald Instrumented-Coverage zusammengeführt werden muss; Coverage-*Gates* sind ein **KANN [MAY]**, und wo vorhanden, wird die Gate-Verdrahtung selbst reviewt — ein Referenzprojekt shippt aktuell ein totes Gate hinter einer veralteten Matrix-Bedingung, was beweist: Gates verrotten wie Code
- **MUSS [MUST]** jeden Test-Task im generierten Projekt standardmäßig grün halten: das `task check` eines frisch gescaffoldeten Projekts besteht lokal und in CI beim ersten Lauf (REQ-1, REQ-7)

### H. Skalierung: Solo-Default und Team-Ergänzungen

- **MUSS [MUST]** als minimal tragfähige Suite für eine neue Solo-Entwickler-App ausliefern: JVM-Unit-Tests für ViewModels/Use Cases/Data-Logik (runTest + MainDispatcherRule + Fakes) und einen CI-Workflow, der die Einzel-Varianten-Unit-Tests plus Lint mit Gradle-Caching und XML-Artefakten ausführt
- **SOLLTE [SHOULD]** JVM-Screenshot-Tests (Roborazzi) als zweite Ebene ergänzen — sie liefern UI-Regressionsschutz ohne jeden Emulator-Job
- **KANN [MAY]** Instrumented-Suiten, Emulator-Matrizen, Coverage-Gates und E2E-Spuren aufschieben, bis Teamgröße, Codebase-Größe oder beobachtete Defekte sie rechtfertigen; jede Ergänzung wird als bewusste Strategieänderung festgehalten, nicht stillschweigend angehäuft
- **DARF NICHT [MUST NOT]** Geräte-Matrix-CI-Jobs, Retry-Maschinerie oder Benchmark-Spuren standardmäßig in ein frisches Solo-Projekt generieren — das ist Großteam-Maschinerie mit realen Wartungskosten

## Akzeptanzkriterien

Die Kriterien sind eine repräsentative Zusammenfassung von §A–§H, keine 1:1-Abbildung; jede Anforderung oben ist für sich normativ.

- [ ] Die Testquellen eines generierten Projekts enthalten JVM-Unit-Tests für jedes ViewModel und Repository, das der Generator erzeugt hat, mit je mindestens einem Fehler-/Edge-Case
- [ ] Jeder Coroutine-Test nutzt `runTest`; eine `MainDispatcherRule` (oder Äquivalent) ist vorhanden und in jedem ViewModel-Test angewendet; keine Produktionsklasse hartkodiert einen Dispatcher
- [ ] Kein Test im Repository ruft `Thread.sleep` oder ein äquivalentes Wanduhr-Warten auf
- [ ] Keine Mocking-Library-Nutzung zielt auf ein projekteigenes Interface mit verfügbarem Fake; Fakes liegen gemäß `spec/android/project-structure/` §F
- [ ] Compose-Screen-Tests zielen auf zustandslose Content-Composables mit Fake-State; kein Test instanziiert ein ViewModel über Hilt in einem Unit-Test
- [ ] Compose-Knoten-Matching nutzt zuerst Semantics; jede `testTag`-Nutzung liegt auf einem Container ohne eigene Text-Semantik
- [ ] Feature-Level-Compose-Tests laufen in `src/test/` unter Robolectric; Instrumented-Tests existieren nur für dokumentiertes gerätespezifisches Verhalten
- [ ] Wo Screenshot-Tests existieren: Goldens sind pro Modul eingecheckt, ausschließlich auf CI/Linux aufgenommen, und `verifyRoborazzi…` (bzw. der Verify-Task des gewählten Tools) läuft auf jedem PR
- [ ] Accessibility-Checks (ATF) laufen innerhalb der Compose- oder Screenshot-Test-Ebene, mit einzeln im Code begründeten Suppressions
- [ ] CI führt pro PR genau die Unit-Tests einer Debug-Variante plus Lint über dieselben Einstiege wie lokal aus, lädt JUnit-XML-Artefakte hoch, und jeder Emulator-Job auf einem GitHub-gehosteten Linux-Runner aktiviert KVM
- [ ] Retry-Mechanismen gelten, wo vorhanden, nur für Instrumented-/große Tests, und jeder bekannte flaky Test wird gemäß den Workflow-Health-Konventionen getrackt statt stillschweigend wiederholt
- [ ] Kein Benchmark-Task (Macro-/Microbenchmark) läuft in der Per-Commit-CI-Spur
- [ ] Das vollständige `task check` eines frisch generierten Projekts (inklusive seiner Test-Tasks) besteht lokal und in CI ohne manuellen Eingriff
- [ ] Die gewählte Assertion-Library des Projekts wird konsistent genutzt (eine einzige Library über alle Testquellen)
- [ ] Ein frisch generiertes Solo-Projekt liefert die §H-Minimalsuite und nicht mehr: kein Geräte-Matrix-CI-Job, keine Retry-Maschinerie und keine Benchmark-Spur existiert, sofern das Projekt die Strategieänderung, die sie hinzufügte, nicht festgehalten hat

## Offene Fragen

Jede Frage nennt die Vorgabe, die die Anforderungen oben bereits kodieren.

- Assertion-Library-Default: `kotlin.test` (Flaggschiff-Sample-Praxis) vs. `assertk` (Produktions-App-Favorit) — entscheiden, wenn der erste Skill Testcode generiert
- Screenshot-Tool-Festlegung: Roborazzi ist hier der Default; neu bewerten, wenn Googles Compose Preview Screenshot Testing alpha verlässt (geteilte offene Frage mit `spec/android/project-structure/`)
- Turbine: als Standard für Flow-Emissions-Tests übernehmen oder Opt-in-Bequemlichkeit lassen?
- Coverage-Schwellen: ob generierte Projekte überhaupt ein Kover-Gate bekommen, und mit welchen Zahlen — verschoben, bis der Quality-Gate-Skill Gestalt annimmt
- JUnit 5/6 auf Android: neu bewerten, falls Google je JUnit 5+ als AndroidX-Test-Runner-Pfad dokumentiert; bis dahin steht das JUnit-4-MUSS, und JUnit 5 bleibt das §B-KANN (JVM ohne Plugin, Instrumented mit dem Community-Plugin)
- Maestro-Smoke-Journeys: als optionales Template für geräteechte Flows scaffolden oder komplett den Einzelprojekten überlassen?

## Referenzen

- [R1] Testing Fundamentals — Scope-/Host-Dimensionen, testbare Architektur: <https://developer.android.com/training/testing/fundamentals>
- [R2] What to test — Unit-/UI-Prioritäten, zu vermeidende Low-Value-Tests: <https://developer.android.com/training/testing/fundamentals/what-to-test>
- [R3] Testing Strategies — Pyramide, fünf Ebenen, Lowest-Layer-Regel, Strategie-Dokument: <https://developer.android.com/training/testing/fundamentals/strategies>
- [R4] Test Doubles — Fakes bevorzugt, Spies abgeraten: <https://developer.android.com/training/testing/fundamentals/test-doubles>
- [R5] Local Tests — JUnit 4, Mocking-Warnungen: <https://developer.android.com/training/testing/local-tests>
- [R6] Robolectric-Positionierung — letzter Ausweg für Unit-Tests, sanktionierte UI-/Screenshot-Rollen, Grenzen: <https://developer.android.com/training/testing/local-tests/robolectric>
- [R7] Coroutines-Testing — runTest, TestDispatchers, ein Scheduler, injizierte Dispatcher: <https://developer.android.com/kotlin/coroutines/test>
- [R8] Flow-Testing — first()/value, WhileSubscribed-Collector-Regel, Turbine als Drittanbieter-Bequemlichkeit: <https://developer.android.com/kotlin/flow/test>
- [R9] Hilt-Testing — kein Hilt in Unit-Tests, @HiltAndroidTest, @TestInstallIn: <https://developer.android.com/training/dependency-injection/hilt-testing>
- [R10] Compose-Testing — Semantics-first-Matching, Rules, Synchronisation: <https://developer.android.com/develop/ui/compose/testing>
- [R11] Compose-Testing Common Patterns — zustandsloses Testen, StateRestorationTester, DeviceConfigurationOverride: <https://developer.android.com/develop/ui/compose/testing/common-patterns>
- [R12] Compose-Accessibility-Testing — ATF-Integration in Compose ≥ 1.8: <https://developer.android.com/develop/ui/compose/accessibility/testing>
- [R13] Instrumented Tests — Einsatzkriterien, AndroidX-Test-Stack: <https://developer.android.com/training/testing/instrumented-tests>
- [R14] AndroidJUnitRunner und Test Orchestrator — Isolation, clearPackageData, Sharding: <https://developer.android.com/training/testing/instrumented-tests/androidx-test-libraries/runner>
- [R15] Instrumented-Test-Stabilität — keine Sleeps, Retry-aber-Fix, wait-until statt Idling Resources: <https://developer.android.com/training/testing/instrumented-tests/stability>
- [R16] UI Automator — Cross-App-Scope, 2.4-API, Benchmark-Interaktionen: <https://developer.android.com/training/testing/other-components/ui-automator>
- [R17] Gradle Managed Devices — ATD-Images, Headless-CI-GPU-Flag, FTL-Integration: <https://developer.android.com/studio/test/gradle-managed-devices>
- [R18] CI-Automatisierung und -Features — Geräteoptionen, Retry-Matrix, Sharding, Benchmark-Kadenz: <https://developer.android.com/training/testing/continuous-integration/automation>
- [R19] Roborazzi — Record-/Verify-Tasks, ATF-Checks, Threshold-Optionen: <https://github.com/takahirom/roborazzi>
- [R20] Paparazzi — layoutlib-Rendering, AGP-Kopplung, Status: <https://cashapp.github.io/paparazzi/>
- [R21] Compose Preview Screenshot Testing (alpha) — src/screenshotTest-Source-Set, Plugin 0.0.1-alpha15, AGP-/Kotlin-Anforderungen für Gradle-only vs. IDE-Integration: <https://developer.android.com/studio/preview/compose-screenshot-testing>
- [R22] KVM auf GitHub-gehosteten Runnern (GA 2024): <https://github.blog/changelog/2024-04-02-github-actions-hardware-accelerated-android-virtualization-now-available/>
- [R23] android-emulator-runner-Action — AVD-Caching-Muster: <https://github.com/ReactiveCircus/android-emulator-runner>
- [R24] Kover — Kotlin-first-Coverage, Multi-Modul-Aggregation, keine Instrumented-Coverage: <https://kotlin.github.io/kotlinx-kover/gradle-plugin/>
- [R25] Now-in-Android-Testflächen — MainDispatcherRule, Test\*Repository-Fakes, Screenshot-Helper, Build-Workflow: <https://github.com/android/nowinandroid>
- [R26] Navigation 3 — Back-Stack als State (Testgrundlage): <https://developer.android.com/guide/navigation/navigation-3>
- [R27] Advanced test setup — `testOptions.unitTests.all {}` stellt lokale Unit-Test-Tasks als Gradle-`Test`-Tasks bereit (P): <https://developer.android.com/studio/test/advanced-test-setup>
- [R28] Gradle Java Testing — `useJUnitPlatform()` auf einem `Test`-Task (P): <https://docs.gradle.org/current/userguide/java_testing.html>
- [R29] Community-Plugin android-junit5 — JUnit 5 für Android-Unit- und Instrumented-Tests, Geräte-API-Untergrenze je JUnit-Generation (S): <https://github.com/mannodermaus/android-junit5>
