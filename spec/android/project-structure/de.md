# Android-Projektstruktur

Status: draft

## Kontext

Dieses Repository stellt wiederverwendbare Claude-Skills für die Android-App-Entwicklung bereit (Projekt-Setup, Compose-UI-Erstellung, Mobile-UX, lokales Entwickeln und Debugging). Jeder Skill gründet auf einer gut formulierten Spec; diese Spec ist die autoritative Definition dessen, wie ein gut strukturiertes Android-App-Projekt aussieht. Der Projekt-Setup-Skill generiert konforme Projekte, und Review-/Audit-Skills beurteilen bestehende Projekte dagegen.

Der Inhalt ist aus einem Recherche-Durchlauf (August 2026) über drei Quellklassen destilliert: offizielle Google/Android-Guidance (Architektur-, Modularisierungs- und Build-Dokumentation auf developer.android.com — mit dem expliziten Drei-Stufen-Vokabular *Strongly recommended* / *Recommended* / *Optional*), Gradles offizielle Best-Practices-Dokumentation sowie Referenzprojekte (Now in Android als Flaggschiff, android/compose-samples, Tivi, DuckDuckGo Android, Signal Android). Stabiler Toolchain-Stand zum Recherchezeitpunkt: AGP 9.x (built-in Kotlin), Gradle 9.x (Configuration Cache als bevorzugter Ausführungsmodus), Kotlin 2.x (Compose-Compiler wird mit Kotlin ausgeliefert). Diese Spec kodiert Mechanismen, keine exakten Versionen.

Zwei Kalibrierungs-Befunde prägen die gesamte Spec: (1) Google knüpft Modularisierung explizit an die Codebase-Größe — die eigenen kleinen Samples sind bewusst single-module, `:feature:*`-Modul-Taxonomien sind also kein universeller Default; (2) wo Referenzprojekte divergieren, divergieren sie bei *Namensschemata*, nicht bei den zugrunde liegenden Invarianten (Feature-Isolation, geteilter Design-System-Code, zentralisierte Build-Logik, eingecheckte Formatter-Konfiguration).

Leser: Autoren der Android-Skills dieses Repos sowie Reviewer, die beurteilen, ob ein generiertes oder auditiertes Projekt konform ist.

## Ziele

- Das kanonische Repository-Layout, die Gradle-Build-Konventionen, die Modul-Strategie, die Paketstruktur, das Source-Set-Layout, die Test-Platzierung und das Quality-Tooling-Layout für ein Android-App-Projekt definieren
- Den Skalierungspfad von der Single-Module-App zur modularisierten App als explizite, trigger-basierte Entscheidung kodieren statt als dogmatischen Default
- Generierte Projekte reproduzierbar, schnell baubar und standardmäßig sicher machen (keine Secrets im VCS, keine veralteten Build-Mechanismen)
- Nachgelagerten Skills (Projekt-Setup, Compose-UI, Debugging) einen strukturellen Vertrag geben, gegen den sie generieren und auditieren

## Nicht-Ziele

- Play-Store-Release, App-Signierung für die Distribution und Store-Metadaten — für dieses Repository explizit außerhalb des Scopes
- CI/CD-Pipeline-Design — abgedeckt durch die Portfolio-Specs `project/continuous-integration` und `project/continuous-delivery`
- Laufzeit-Architekturverhalten jenseits seines strukturellen Abdrucks — State-Management-Details, Navigation-Graph-Design und UX-Patterns gehören in eigene künftige Specs unter `spec/android/`
- Kotlin-Multiplatform-Projektlayout — diese Spec zielt auf Android-only-Apps; KMP strukturiert die oberste Ebene um (siehe Tivi) und bräuchte eine eigene Spec
- Festschreiben exakter Tool- oder Library-Versionen — die Spec fixiert Mechanismen (Catalog, Wrapper, BOM); Versionen leben in der `libs.versions.toml` des generierten Projekts

## Anforderungen

### A. Repository-Root-Layout

- **MUSS [MUST]** im Repository-Root ablegen: `settings.gradle.kts`, `build.gradle.kts`, `gradle.properties`, `gradle/libs.versions.toml`, `gradle/wrapper/`, `gradlew`, `gradlew.bat`, `.editorconfig` und `.gitignore`
- **MUSS [MUST]** `.gitignore` auf GitHubs kanonischem `Android.gitignore` aufbauen und mindestens abdecken: `.gradle/`, `build/`, `local.properties`, `.idea/` (oder eine selektive Teilmenge), `captures/`, `.cxx/`, `*.apk`, `*.aab`, `*.jks`, `*.keystore`, `google-services.json`, `*.hprof`
- **DARF NICHT [MUST NOT]** eine Secret-tragende Datei versionieren: API-Keys leben in der unversionierten `local.properties` (Google-`secrets-gradle-plugin`-Muster) mit einer eingecheckten Defaults-Datei (zum Beispiel `secrets.defaults.properties`); Release-Keystores gelangen nie ins VCS. Ein bewusst eingecheckter *Debug*-Keystore für reproduzierbare Debug-Signaturen ist ein **KANN [MAY]**
- **MUSS [MUST]** `kotlin.code.style=official` in `gradle.properties` setzen
- **SOLLTE [SHOULD]** Architektur-Dokumentation in einem `docs/`-Ordner halten; Modul-`README.md`-Dateien mit Abhängigkeitsgraphen sind ein **KANN [MAY]**

### B. Gradle-Build-Konventionen

- **MUSS [MUST]** die Kotlin DSL (`.gradle.kts`) für alle Build-Dateien verwenden — Default seit AGP/Studio Giraffe und Gradle 8
- **MUSS [MUST]** Builds ausschließlich über den eingecheckten Wrapper ausführen (`gradlew`, `gradle/wrapper/` inklusive JAR); Upgrades nur via `./gradlew wrapper --gradle-version <v>`; **SOLLTE [SHOULD]** die Wrapper-Integrität über `distributionSha256Sum` und/oder Wrapper-Validierung in CI absichern
- **MUSS [MUST]** alle Dependency- und Plugin-Koordinaten in einem einzigen Version Catalog `gradle/libs.versions.toml` deklarieren: Sektionen `[versions]`/`[libraries]`/`[plugins]` (optional `[bundles]`, sparsam eingesetzt), zentrale Versionen per `version.ref` referenziert, Aliase in kebab-case, Plugins per `alias(libs.plugins.…)` angewendet
- **DARF NICHT [MUST NOT]** dynamische Dependency-Versionen verwenden (zum Beispiel `2.+`)
- **MUSS [MUST]** Repositories zentral in `settings.gradle.kts` via `dependencyResolutionManagement` deklarieren; **SOLLTE [SHOULD]** `RepositoriesMode.FAIL_ON_PROJECT_REPOS` setzen und Repository-Content-Filtering nutzen (zum Beispiel `google()` eingegrenzt auf `com.android.*`, `androidx.*`, `com.google.*`)
- **MUSS [MUST]** `rootProject.name` explizit in `settings.gradle.kts` setzen
- **MUSS [MUST]** die Root-`build.gradle.kts` frei von Code halten bis auf einen `plugins {}`-Block, der alle Submodul-Plugins mit `apply false` deklariert (einheitlicher Build-Script-Classpath); **DARF NICHT [MUST NOT]** `allprojects {}`- / `subprojects {}`-Cross-Project-Konfiguration verwenden
- **MUSS [MUST]** `implementation` gegenüber `api` bevorzugen; `api` nur, wenn der Typ Teil des öffentlichen ABI des Moduls ist
- **MUSS [MUST]** Compose-Versionen über das Compose BOM verwalten (`platform(libs.androidx.compose.bom)`, auch auf Test-Konfigurationen); Compose-Libraries im Catalog tragen keine Einzelversionen; **MUSS [MUST]** den Compose-Compiler über das Kotlin-eigene Plugin `org.jetbrains.kotlin.plugin.compose` mit `version.ref` = Kotlin-Version anwenden
- **MUSS [MUST]** KSP statt kapt verwenden (kapt ist im Maintenance-Modus); kein Modul darf eine kapt-Anwendung behalten
- **MUSS [MUST]** in `gradle.properties` aktivieren: `org.gradle.configuration-cache=true`, `org.gradle.caching=true`, `org.gradle.parallel=true`, `android.useAndroidX=true` sowie ausreichend dimensionierte `org.gradle.jvmargs` (Heap erhöhen, wenn GC ~15 % der Buildzeit übersteigt; `-XX:MaxMetaspaceSize` mitsetzen)
- **DARF NICHT [MUST NOT]** redundante oder veraltete Flags setzen: `android.nonTransitiveRClass` (Default seit AGP 8+), `android.enableJetifier` (nur Legacy-Support-Library), `kotlin.incremental` (Default), Debug-PNG-Crunching-Flags
- **SOLLTE [SHOULD]** typsichere Projekt-Accessors aktivieren (`enableFeaturePreview("TYPESAFE_PROJECT_ACCESSORS")`) und Module als `implementation(projects.core.data)` referenzieren — noch incubating, daher kein MUST
- **KANN [MAY]** Dependency-Hygiene-Tooling ergänzen: Dependency-Guard-Baselines oder das Dependency Analysis Gradle Plugin (Community-Standard, keine offizielle Empfehlung)

### C. Modul-Strategie und Taxonomie

- **MUSS [MUST]** ein neues App-Projekt single-module starten (nur `:app`), sofern zum Erstellungszeitpunkt keine konkrete Wiederverwendungs-, Team-Skalierungs- oder Delivery-Anforderung existiert — Google knüpft Modularisierung an die Codebase-Größe, und die eigenen kleinen Samples sind single-module
- **MUSS [MUST]** die Modularisierungs-Entscheidung (Auslöser und geplanter Schnitt) festhalten, wenn sie getroffen wird; anerkannte Auslöser: anhaltender Buildzeit-Schmerz, Code-Wiederverwendung über Apps/Varianten, erzwungene Sichtbarkeitsgrenzen, parallele Ownership
- **MUSS [MUST]** nach der Modularisierung der Drei-Stufen-Taxonomie `:app` / `:feature:*` / `:core:*` mit diesen Abhängigkeitsregeln folgen: Feature-Module hängen nie von den Implementierungen anderer Feature-Module ab; Core-Module hängen nie von Feature- oder App-Modulen ab; das App-Modul sitzt oben und hängt von Features und benötigten Core-Modulen ab; keine Abhängigkeitszyklen
- **MUSS [MUST]** nach der Modularisierung Build-Konfiguration über Convention Plugins in einem `build-logic/`-Included-Build teilen (`pluginManagement { includeBuild("build-logic") }`) mit komponierbaren Single-Responsibility-Plugins; Plugin-IDs folgen `<projekt>.<plattform>.<modultyp>[.<aspekt>]` (zum Beispiel `myapp.android.library.compose`); `buildSrc` bleibt ein **KANN [MAY]** für sehr kleine Multi-Modul-Builds
- **SOLLTE [SHOULD]** reine Kotlin/JVM-Module gegenüber Android-Library-Modulen bevorzugen, wo keine Android-Ressourcen oder Manifeste nötig sind
- **SOLLTE [SHOULD]** `:core:designsystem` (daten-agnostische Komponenten, Theme, Icons) von `:core:ui` (zusammengesetzte Komponenten, die von Data-Layer-Modellen abhängen dürfen) trennen
- **SOLLTE [SHOULD]** einfache IDs statt Objekte als Navigationsargumente zwischen Features übergeben (Single Source of Truth)
- **KANN [MAY]** Features in `:feature:x:api` (Navigation-Keys) und `:feature:x:impl` (Screens, ViewModels) aufteilen — das aktuelle Now-in-Android-/Navigation-3-Muster für große Projekte; **DARF NICHT [MUST NOT]** diesen Split auf Solo- oder Kleinprojekte anwenden, wo er reiner Overhead ist

### D. Paketstruktur und Source Sets

- **MUSS [MUST]** Layer-Grenzen im Paketbaum sichtbar halten: UI-Code und Data-Code teilen sich nie ein Paket; eine Single-Module-App startet mit Top-Level-Paketen `ui` (oder `feature`) und `data`
- **SOLLTE [SHOULD]** UI-Code nach Feature gruppieren (`feature.<name>`- oder `ui.<feature>`-Pakete, die Screen-Composables, ViewModel und Navigationscode zusammenhalten) statt in einem flachen Layer-Paket — „Feature per Modul oder Paket, Layer darin"
- **MUSS [MUST]** das Standard-Source-Set-Layout `src/main/`, `src/test/`, `src/androidTest/` verwenden (Kotlin-Quellen unter `kotlin/`); Build-Type-/Flavor-Source-Sets folgen der Standard-Prioritätsreihenfolge und werden nur ergänzt, wenn eine Variante sie tatsächlich braucht
- **MUSS [MUST]** `minSdk`, `targetSdk` und `applicationId` in Build-Dateien halten, nicht im Manifest; Manifest-Merge-Konflikte explizit mit `tools:`-Markern auflösen
- **MUSS [MUST]** in modularisierten Projekten die öffentliche Oberfläche jedes Moduls minimal halten (`internal` als Default; nur das Wesentliche exponieren)

### E. Architektur — struktureller Abdruck

- **MUSS [MUST]** eine UI-Schicht und eine Data-Schicht trennen; UI-Schicht-Code greift nie direkt auf Datenquellen zu (Datenbank, DataStore, Netzwerk, Sensoren) — der Zugriff läuft über Repositories, auch bei nur einer Quelle
- **MUSS [MUST]** Repositories `<DataType>Repository` und Datenquellen `<DataType><Remote|Local>DataSource` benennen (nie nach Implementierungsdetails)
- **KANN [MAY]** eine Domain-Schicht einführen (Use Cases benannt `<VerbPräsens><Nomen>UseCase`) — offiziell optional, gerechtfertigt durch Komplexität oder Wiederverwendung; **DARF NICHT [MUST NOT]** triviale Durchreich-Use-Cases erzwingen
- **MUSS [MUST]** Konstruktor-basierte Dependency Injection verwenden; Hilt für modularisierte Apps, manuelle DI akzeptabel für kleine Single-Module-Apps
- **MUSS [MUST]** Screen-Level-Compose-Code als dünnes zustandsbehaftetes Route-Composable strukturieren (holt das ViewModel, sammelt State), das an ein zustandsloses Content-Composable mit `uiState` plus Event-Lambdas delegiert; Previews zielen auf das zustandslose Composable, liegen daneben und heißen `<Composable>Preview`
- **SOLLTE [SHOULD]** Theming-/Design-System-Code an einem dedizierten Ort halten (ein `designsystem`-/`theme`-Paket in Single-Module-Apps; `:core:designsystem` nach der Modularisierung): Theme-Funktion, typisierte Accessors, Kernkomponenten

### F. Test-Struktur

- **MUSS [MUST]** Unit-Tests im selben Modul wie den getesteten Code ablegen (`src/test/`) und Instrumented-Tests in `src/androidTest/`; kein zentrales Test-Modul für Modul-Tests
- **MUSS [MUST]** Fakes gegenüber Mocks bevorzugen (Test-Implementierungen mit Test-only-Hooks); **SOLLTE [SHOULD]** ganz auf eine Mocking-Library verzichten
- **SOLLTE [SHOULD]** nach der Modularisierung geteilte Test-Fixtures (Rules, Fake-Repositories, Testdaten, Test-Runner) in ein `:core:testing`-Modul legen
- **KANN [MAY]** JVM-Screenshot-Tests (Roborazzi oder Paparazzi) in `src/test/` ergänzen, mit pro Modul eingecheckten Goldens unter `src/test/screenshots/`
- **MUSS [MUST]** einem konsistenten Test-Namensschema pro Repository folgen (das Schema selbst ist frei; Schemata zu mischen ist es nicht)
- **SOLLTE [SHOULD]** bei vorhandenen Product Flavors variant-bewusste Test-Tasks ausführen (zum Beispiel `testDemoDebug`) statt des Aggregats `test`

### G. Quality-Tooling-Layout

- **MUSS [MUST]** eine Root-`.editorconfig` einchecken; die ktlint-Regelkonfiguration lebt dort
- **SOLLTE [SHOULD]** Formatierung über Spotless mit ktlint als Kotlin-Formatter orchestrieren; Lizenz-Header-Templates in einem Root-Ordner `spotless/` sind ein **KANN [MAY]**
- **SOLLTE [SHOULD]** die Android-Lint-Konfiguration zentralisieren (ein Convention Plugin, sobald `build-logic/` existiert, sonst eine Root-`lint.xml`); Modul-`lint-baseline.xml`-Dateien sind nur für Legacy-Befunde — neue Projekte starten baseline-frei
- **KANN [MAY]** detekt ergänzen (Konfiguration unter `config/detekt/detekt.yml`) — in der Community verbreitet, in Googles Referenzprojekten abwesend
- **KANN [MAY]** Formatierung über Git-Hooks durchsetzen (zum Beispiel lefthook)

## Akzeptanzkriterien

- [ ] Ein frisch generiertes Projekt baut unmittelbar nach der Generierung grün mit `./gradlew build`
- [ ] Die Root-`build.gradle.kts` enthält nur einen `plugins {}`-Block mit `apply false`-Deklarationen; nirgendwo existieren `allprojects`-/`subprojects`-Blöcke
- [ ] Jede Dependency und jedes Plugin in Modul-Build-Dateien löst über `libs.versions.toml`-Accessors auf; keine hartkodierten Koordinaten oder dynamischen Versionen
- [ ] `gradle.properties` aktiviert Configuration Cache, Build Cache, parallele Ausführung und AndroidX und enthält keines der in §B als veraltet gelisteten Flags
- [ ] Kein Modul wendet kapt an; Annotation Processing läuft über KSP
- [ ] Compose-Libraries tragen keine Einzelversionen (BOM-verwaltet), und das Compose-Compiler-Plugin referenziert die Kotlin-Version
- [ ] Ein neu generiertes Projekt enthält genau ein `:app`-Modul, sofern Modularisierung nicht explizit angefordert wurde; bei Modularisierung erfüllt der Modul-Graph jede Abhängigkeitsregel aus §C
- [ ] Unit- und Instrumented-Tests liegen in `src/test/` / `src/androidTest/` des getesteten Moduls
- [ ] Ein Formatierungs-Check (Spotless/ktlint) besteht auf frisch generiertem Code
- [ ] `git ls-files` zeigt keine `local.properties`, keinen Release-Keystore und keine `google-services.json`
- [ ] Der Paketbaum trennt UI- und Data-Schicht, und Screen-Code ist nach Feature gruppiert
- [ ] Screen-Composables sind in zustandsbehaftete Route- und zustandslose, preview-fähige Content-Composables aufgeteilt

## Offene Fragen

- detekt-Adoption: Googles Referenzprojekte verzichten darauf, die Community setzt es breit ein — entscheiden, wenn der Quality-Gate-/Audit-Skill dieses Repos Gestalt annimmt
- Schwelle für den `:feature:x:api`/`:impl`-Split: ab welcher Projektgröße lohnt sich der Navigation-3-artige Schnitt?
- Soll der Projekt-Setup-Skill `build-logic/` von Anfang an scaffolden (billig solange leer) oder erst bei der ersten Modularisierung (Single-Module-Reinheit)?
- Screenshot-Testing-Tool-Wahl: Roborazzi vs. Paparazzi vs. Googles neueres Compose Preview Screenshot Testing (`src/screenshotTest`-Source-Set)
- Kotlin Multiplatform: Falls KMP je in den Scope kommt, ändert sich das Top-Level-Layout grundlegend (siehe Tivi) und braucht eine eigene Spec

## Referenzen

- [R1] Android-App-Architektur-Guide — Schichten, Separation of Concerns, SSOT, UDF: <https://developer.android.com/topic/architecture>
- [R2] Architektur-Empfehlungen (Stufen Strongly recommended / Recommended / Optional): <https://developer.android.com/topic/architecture/recommendations>
- [R3] Modularisierungs-Überblick — wann (nicht) modularisieren: <https://developer.android.com/topic/modularization>
- [R4] Gängige Modularisierungs-Patterns — Modultypen, Abhängigkeitsregeln, api vs. implementation: <https://developer.android.com/topic/modularization/patterns>
- [R5] Now in Android — Modularization Learning Journey (Feature-api/impl-Split, Core-Taxonomie): <https://github.com/android/nowinandroid/blob/main/docs/ModularizationLearningJourney.md>
- [R6] Now in Android — build-logic Convention Plugins: <https://github.com/android/nowinandroid/blob/main/build-logic/README.md>
- [R7] Gradle Best Practices — Structuring Builds: <https://docs.gradle.org/current/userguide/best_practices_structuring_builds.html>
- [R8] Gradle Best Practices — Dependencies: <https://docs.gradle.org/current/userguide/best_practices_dependencies.html>
- [R9] Gradle Version Catalogs: <https://docs.gradle.org/current/userguide/version_catalogs.html>
- [R10] Migration zu Version Catalogs (Android): <https://developer.android.com/build/migrate-to-catalogs>
- [R11] Migration von kapt zu KSP: <https://developer.android.com/build/migrate-to-ksp>
- [R12] Compose-Compiler-Gradle-Plugin (wird mit Kotlin 2.x ausgeliefert): <https://developer.android.com/develop/ui/compose/compiler>
- [R13] Compose Bill of Materials: <https://developer.android.com/develop/ui/compose/bom>
- [R14] Build-Varianten und Source Sets: <https://developer.android.com/build/build-variants>
- [R15] Manifest-Merging: <https://developer.android.com/build/manage-manifests>
- [R16] Compose-Previews und Stateless-Composable-Guidance: <https://developer.android.com/develop/ui/compose/tooling/previews>
- [R17] Optimize your build (gradle.properties-Flags, veraltete Flags): <https://developer.android.com/build/optimize-your-build>
- [R18] Navigation-3-Modularisierung (Feature api/impl): <https://developer.android.com/guide/navigation/navigation-3/modularize>
- [R19] GitHubs kanonisches Android.gitignore: <https://github.com/github/gitignore/blob/main/Android.gitignore>
- [R20] Secrets Gradle Plugin (local.properties-Muster): <https://github.com/google/secrets-gradle-plugin>
