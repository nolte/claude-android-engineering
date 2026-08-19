# UI-Komponenten

Status: draft

## Kontext

Eine konsistente App besteht aus Komponenten, die jeweils für den Zweck eingesetzt werden, für den sie entworfen wurden. Diese Spec fixiert die Nutzungsregeln der einzelnen Material-3-UI-Elemente — wann welche Komponente die richtige Wahl ist, wann die falsche, und wie ein Projekt einheitliche Nutzung *durchsetzt* — damit jeder vom Compose-UI-Skill (REQ-13) generierte Screen und jeder Befund des UX-Audit-Skills (REQ-14) einem gemeinsamen Komponentenvokabular folgt.

Der Inhalt ist aus einem Recherche-Durchlauf (August 2026) destilliert: die offiziellen Material-3-Komponenten-Guidelines (m3.material.io, je Komponente vollständig gerendert), die Compose-Komponentendokumentation samt API-Mapping (developer.android.com), die M3-Expressive-Komponenten-Updates von 2025 sowie die Konsistenz-Governance-Maschinerie des Referenzprojekts Now in Android (Design-System-Wrapping plus ein eigener Android-Lint-Check auf ERROR-Stufe, der rohe Material-Komponenten verbietet, wo ein Wrapper existiert).

Grenzen: Design-Fundament (Farb-/Typografie-/Shape-Rollen) und die Wahl der Navigations-UI liegen in `spec/android/app-design-navigation/`; das Icon-System liegt in `spec/android/iconography/`; die Größenbeschränkungen von Dialogen/Sheets auf großen Fenstern liegen in `spec/android/screen-formats/` §B.

Leser: Autoren der Android-Skills dieses Repos sowie Reviewer, die beurteilen, ob generierte oder auditierte UI Komponenten konsistent und korrekt nutzt.

## Ziele

- Ein semantisches Vokabular: für jeden UI-Bedarf eine definierte Komponente, für jede Komponente ein definierter Zweck — inklusive der expliziten Fehlnutzungen
- Eine sichtbare Prominenz-Hierarchie: genau eine Primäraktion pro Screen, ausgedrückt über die Emphasis-Leiter, nie über konkurrierende Hervorhebungen
- Durchgesetzte Konsistenz: das Design-System-Wrapping-Muster plus Lint-Enforcement macht einheitliche Nutzung zu einer Build-Zeit-Eigenschaft, nicht zu einer Review-Hoffnung
- Aktualität: die Expressive-Ablösungen von 2025 (Segmented Buttons, Baseline-Bottom-App-Bar, Small FAB) gelangen nicht in neu generierten Code

## Nicht-Ziele

- Farb-, Typografie-, Shape- und Motion-Fundament — `spec/android/app-design-navigation/` §A
- Auswahlregeln der Navigationskomponenten (Bar/Rail/Drawer) — `spec/android/app-design-navigation/` §C
- Icon-Stil, -Größen und -Accessibility-Regeln — `spec/android/iconography/`
- Adaptive Größenanpassung der Komponenten auf großen Fenstern — `spec/android/screen-formats/` §B
- Der Bau einer allgemeinen Design-System-Bibliothek — das Governance-Muster hier dient der Pro-App-Konsistenz

## Anforderungen

### A. Komponentenwahl — die semantische Matrix

- **MUSS [MUST]** der Button-Emphasis-Leiter folgen: Filled Button für die eine wichtige, abschließende Aktion eines Flows („Speichern", „Bestätigen" — idealerweise einer pro Screen); Tonal für Nachrangiges-mit-Betonung („Weiter"); Outlined für Sekundäraktionen mittlerer Betonung; Text Button für die niedrigste Priorität und Mehrfach-Optionen; Elevated nur, wenn die Abhebung von einem prominenten Hintergrund es verlangt
- **MUSS [MUST]** Button-Labels kurz halten (1–3 Wörter), einzeilig (kein Abschneiden oder Umbrechen), höchstens ein führendes Icon, und nie unterstrichen (Links sind verlinkter Fließtext)
- **MUSS [MUST]** höchstens einen FAB pro Screen einsetzen, nur für die wichtigste konstruktive Aktion (Erstellen, Verfassen, Starten); **DARF NICHT [MUST NOT]** FABs für Neben- oder destruktive Aktionen, Pro-Card-Aktionen oder als Toolbar-Ersatz nutzen; der FAB bleibt beim Scrollen stehen; der Small FAB wird nicht mehr empfohlen
- **MUSS [MUST]** die Chips-vs.-Buttons-Unterscheidung respektieren: Chips repräsentieren Verzweigungen und dynamischen Kontext (Assist/Filter/Input/Suggestion), Buttons lineare Schritte — **DARF NICHT [MUST NOT]** Chips zum Fortschreiten oder Abschließen einer Aufgabe nutzen, einen einzelnen Chip allein zeigen oder ein Filter-Chip-Set mit nur einer Option bauen; Input-Chips tragen ein verpflichtendes Entfernen-Icon
- **MUSS [MUST]** die Meldungsfläche nach Schwere wählen: Dialog nur für blockierende Entscheidungen/kritische Information (max. zwei Aktionen, bestätigende rechts, ablehnende nie disabled, bestätigende disabled bis eine Wahl existiert); Snackbar für Prozess-Feedback niedriger/mittlerer Priorität (eine optionale Aktion, nie kritischer Inhalt, nie gestapelt, nie der einzige Weg zu einem Feature, keine Icons); modales Bottom Sheet als mobile Alternative für lange Aktionslisten; Toast nur für Hintergrund-Hinweise — im Vordergrund gewinnt die Snackbar
- **MUSS [MUST]** Full-Screen-Dialoge nur auf kompakten Fenstern für mehrschrittige Teilaufgaben nutzen; auf medium+ ersetzt sie ein Basic Dialog
- **MUSS [MUST]** die Selection-Control-Matrix anwenden: Checkboxen für Mehrfachauswahl in Listen, Radio Buttons für Einzelauswahl (≤ 5 Optionen, immer eine vorausgewählt, vertikal, nie verschachtelt), Switches für eigenständige binäre Einstellungen mit Sofortwirkung — **DARF NICHT [MUST NOT]** Switches für Mehrfachauswahl-Listen, gegensätzliche Optionen (stattdessen Button Group) oder etwas mit Speicherschritt nutzen
- **MUSS [MUST]** die Warteanzeige-Matrix konsistent anwenden: nichts unter ~200 ms; der Loading Indicator für kurze unbestimmte Wartezeiten (200 ms–5 s, auch die Pull-to-Refresh-Fläche); ein Progress Indicator (determinate, sobald Fortschritt bekannt) über ~5 s; ein Indikator pro Gruppe, dieselbe Variante für denselben Prozess app-weit, und nie eine Loading→Determinate-Übergabe an Ort und Stelle
- **MUSS [MUST]** Textfelder einheitlich halten: eine Variante (filled oder outlined) pro Formular — nie nebeneinander gemischt; jedes Feld hat ein stets sichtbares Label (Placeholder ist kein Label), Fehlertext ersetzt Supporting-Text (nie beides), Pflichtfelder sind markiert und erklärt
- **MUSS [MUST]** Container-Regeln einhalten: Cards scrollen nie intern, hosten nie swipebaren Inhalt oder mehr als eine Swipe-Aktion und erzwingen keinen Inhalt, den Abstände/Überschriften besser strukturieren würden; Listenzeilen halten Elementpositionen konsistent, Supporting-Text 1–3 Zeilen; Menüs zeigen bedingt nicht verfügbare Einträge disabled statt sie zu entfernen und betten nie direkte Controls (Switches/Buttons) in Menüeinträge ein
- **SOLLTE [SHOULD]** Suchflächen je Rolle nutzen (persistente Bar, wenn Suche zentral ist, Icon-Button, wenn sekundär), Date Picker je Eingabemodus (Texteingabe für ferne Daten wie Geburtstage — nie Kalender-Scrollen) und Badges nur an Navigationselementen (klein = ungelesen, groß = Anzahl, „999+"-Deckel)

### B. Prominenz-Hierarchie

- **MUSS [MUST]** genau eine Primäraktion pro Screen mit der höchsten Emphasis-Komponente ausdrücken (Filled Button oder FAB — nie beide konkurrierend); alle anderen Aktionen steigen die Leiter hinab
- **DARF NICHT [MUST NOT]** in einer Toolbar oder Aktionszeile mehr als eine Aktion gleichzeitig hervorheben; zu viele Buttons auf einem Screen sind selbst das dokumentierte Anti-Pattern — alternative Flächen bevorzugen (Chips, Textlinks, Icon-Buttons)
- **SOLLTE [SHOULD]** gemischte Button-Varianten über ihre Farb-/Emphasis-Rollen unterscheiden, damit die Primäraktion eindeutig bleibt

### C. Konsistenz-Governance

- **MUSS [MUST]** jede Komponente, deren Defaults die App ändert oder deren Freiheitsgrade sie einschränkt, durch einen Design-System-Wrapper führen (das `NiaButton`-Muster): Der Wrapper backt Theme-Defaults ein und exponiert eine bewusst reduzierte API (kein `colors`-/`shape`-/`elevation`-Durchreichen); stock genutzte Komponenten bleiben direkte Material-3-Nutzung — alles zu wrappen ist nicht das Ziel
- **MUSS [MUST]** Komponenten ausschließlich über Theme-Rollen und die `*Defaults`-APIs konfigurieren (Slot-Parameter, `ButtonDefaults`, `CardDefaults`, …) — nie Farb-/Größen-Literale an Aufrufstellen; ohne `MaterialTheme`-Vorfahren rendern Material-Komponenten by design falsch
- **MUSS [MUST]**, sobald Wrapper existieren, sie mit einem Lint-Check auf ERROR-Stufe durchsetzen, der jede gewrappte Material-Komponente auf ihren Wrapper abbildet (das Now-in-Android-`DesignSystemDetector`-Muster, über den Build projektweit verdrahtet)
- **SOLLTE [SHOULD]** Wrapper im Design-System-Modul platzieren (`:core:designsystem` gemäß `spec/android/project-structure/` §C nach der Modularisierung; das `designsystem`-Paket gemäß deren §E in Single-Module-Apps); **KANN [MAY]** eine Katalog-App/-Screen pflegen, die jeden Wrapper zur visuellen Prüfung rendert
- **SOLLTE [SHOULD]** die Standard-Disabled-Alphas (38 % Inhalt, 12 % Container gemäß der M3-State-Spezifikation, gespiegelt von den Konstanten des Referenzprojekts [R21][R25]) über die State-Layer der Komponenten nutzen statt eigener Opazität

### D. Expressive-Aktualität

- **DARF NICHT [MUST NOT]** die abgelösten Baseline-Komponenten in neuen Code generieren: Segmented Buttons (→ Connected Button Group), die Baseline-Bottom-App-Bar (→ Docked Toolbar), den Small FAB
- **MUSS [MUST]**, solange das `compose-material3` des Projekts die stabile 1.4-Linie ist (die Nachfolger liegen nur in den 1.5.0-alpha-Artefakten — `ButtonGroup`, `SplitButton` und die Floating Toolbar sind innerhalb dieser Alpha-Linie aus dem Experimental-Status graduiert, aber kein stabiles Release trägt sie [R26]), diese baseline-konformen Defaults statt der verbotenen Komponenten verwenden: eine Single-Select-`FilterChip`-Reihe für eine segmentierte Wahl zwischen Filtern oder Modi und `PrimaryTabRow`, wo die Wahl Ansichten wechselt; die Primäraktion als der eine FAB mit Sekundäraktionen in der Top App Bar anstelle einer Bottom App Bar; den FAB in Standardgröße anstelle des Small FAB. Die 1.5.0-alpha-Nachfolger stattdessen zu übernehmen ist nur als protokollierte Entscheidung gemäß dem folgenden Punkt zulässig
- **KANN [MAY]** die neuen Expressive-Komponenten (Button Groups, Split Button, FAB Menu, Floating/Docked Toolbars, Loading Indicator, Wavy Progress) übernehmen, sobald ihre Compose-APIs ein stabiles Release erreichen; solange sie in der Alpha-Linie liegen oder `@ExperimentalMaterial3ExpressiveApi` tragen, ist jede Übernahme eine protokollierte Entscheidung
- **SOLLTE [SHOULD]** Änderungen der Komponenten-Guidance zur Authoring-Zeit verfolgen — das Komponentenset hat sich 2025 substanziell bewegt, und veraltete Komponentenwahl ist ein Audit-Befund, keine Stilfrage

## Akzeptanzkriterien

Die folgenden Kriterien sind ein bewusst repräsentatives Rollup von §A–§D, keine 1:1-Abbildung; jeder Anforderungspunkt oben ist für sich normativ.

- [ ] Jeder generierte Screen hat höchstens einen Filled Button oder FAB als Primäraktion, und keine zweite gleich stark betonte Aktion konkurriert damit
- [ ] Kein Dialog in generiertem Code trägt mehr als zwei Aktionen oder eine deaktivierte ablehnende Aktion; keine Snackbar trägt kritische Information, ein Icon oder mehr als eine Aktion
- [ ] Selection Controls entsprechen überall ihrer Semantik: kein Switch in einer Mehrfachauswahl-Liste, keine Radio-Gruppe ohne Vorauswahl, kein Selection Control, dessen Wirkung auf einen Speichern-Button wartet
- [ ] Die Warteanzeige folgt der Matrix: kein Spinner unter 200 ms, kein unbestimmter Indikator für Wartezeiten mit bekanntem Fortschritt über 5 s, und ein Prozess nutzt app-weit eine Indikator-Variante
- [ ] Kein Formular mischt filled und outlined Textfelder; jedes Textfeld hat ein sichtbares Label; Fehlertext ersetzt Supporting-Text
- [ ] Keine Card scrollt intern oder hostet swipebaren Inhalt; kein Menüeintrag bettet einen Switch oder Button ein; bedingt nicht verfügbare Menüeinträge rendern disabled
- [ ] Kein Chip treibt eine Aufgabe voran; kein Einzel-Chip-Set existiert; jeder Input-Chip hat eine Entfernen-Affordanz
- [ ] Generierter Code enthält keine Segmented Buttons, Baseline-Bottom-App-Bars oder Small FABs; auf der stabilen material3-Linie treten an ihre Stelle die benannten Defaults (Single-Select-Filter-Chips / Tab Row, FAB plus Top-App-Bar-Aktionen, Standard-FAB) oder eine protokollierte Expressive-Übernahme
- [ ] Alles Komponenten-Styling fließt über Theme-Rollen und `*Defaults`-/Wrapper-APIs; kein Farb- oder Maß-Literal erscheint an einer Komponenten-Aufrufstelle
- [ ] Wo Design-System-Wrapper existieren, verbietet ein Lint-Check auf ERROR-Stufe die gewrappten rohen Material-Komponenten, und CI führt ihn aus
- [ ] Experimentelle Expressive-APIs erscheinen nur mit protokollierter Übernahme-Entscheidung

## Offene Fragen

Alle vier Fragen sind Parking-Lot-Klasse: Die Anforderungen oben nennen für jede einen funktionierenden Default (Wrap-bei-Anpassung, Baseline-Komponenten bereits verboten, Katalog optional, Komponenten-Defaults akzeptabel).

- Wrapper-Scaffold-Zeitpunkt: Soll der Compose-UI-Skill die Design-System-Wrapper-Schicht (plus Lint-Check) ab dem ersten Screen generieren oder erst, wenn die App die Defaults einer Komponente anpasst?
- Expressive-Komponenten-Übernahme: generierten Code jetzt auf Connected Button Groups und Docked Toolbars umstellen (die Guidance deprecatet die Baselines bereits), obwohl ihre Compose-APIs nur in den 1.5.0-alpha-Artefakten liegen, oder die Stable-Line-Defaults aus §D behalten, bis ein stabiles Release sie trägt?
- Katalog-Fläche: Standard-`app-catalog`-Modul für jede generierte App oder nur für Apps mit gewachsenem Design-System?
- Disabled-State-Alpha-Konstanten: aus einer geteilten Token-Datei lesen oder die Komponenten-Defaults stillschweigend akzeptieren?

## Referenzen

Alle Quellen abgerufen am 11.08.2026; R26 erneut verifiziert am 19.08.2026. Klassenmarker: (P) primäre/maßgebliche Vendor-Dokumentation, (S) sekundär (Referenzprojekt-Code). m3.material.io-Seiten sind clientseitig gerendert; die Inhalte wurden über gerenderte Abrufe der kanonischen URLs erfasst. Komponenten-Nutzungsregeln sind Material 3s eigene maßgebliche Design-Spezifikation — die einzige Primärquelle je Komponente — korroboriert durch die Compose-API-Docs (R22–R24) und das Referenzprojekt (R25), wo Implementierungsverhalten behauptet wird.

- [R1] Buttons-Guidelines (P): <https://m3.material.io/components/buttons/guidelines>
- [R2] FAB-Guidelines (P): <https://m3.material.io/components/floating-action-button/guidelines>
- [R3] Icon-Buttons-Guidelines (P): <https://m3.material.io/components/icon-buttons/guidelines>
- [R4] Chips-Guidelines (P): <https://m3.material.io/components/chips/guidelines>
- [R5] Cards-Guidelines (P): <https://m3.material.io/components/cards/guidelines>
- [R6] Lists-Guidelines (P): <https://m3.material.io/components/lists/guidelines>
- [R7] Dialogs-Guidelines (P): <https://m3.material.io/components/dialogs/guidelines>
- [R8] Bottom-Sheets-Guidelines (P): <https://m3.material.io/components/bottom-sheets/guidelines>
- [R9] Snackbar-Guidelines (P): <https://m3.material.io/components/snackbar/guidelines>
- [R10] Toasts (Vordergrund → Snackbar) (P): <https://developer.android.com/guide/topics/ui/notifiers/toasts>
- [R11] Text-Fields-Guidelines (P): <https://m3.material.io/components/text-fields/guidelines>
- [R12] Menus-Guidelines (P): <https://m3.material.io/components/menus/guidelines>
- [R13] Checkbox-/Radio-/Switch-Guidelines (P): <https://m3.material.io/components/checkbox/guidelines> (und /radio-button, /switch)
- [R14] Progress-Indicators-Guidelines (P): <https://m3.material.io/components/progress-indicators/guidelines>
- [R15] Loading-Indicator-Guidelines (Expressive, Warte-Matrix) (P): <https://m3.material.io/components/loading-indicator/guidelines>
- [R16] Badges-Guidelines (P): <https://m3.material.io/components/badges/guidelines>
- [R17] Search-Guidelines (P): <https://m3.material.io/components/search/guidelines>
- [R18] Date-/Time-Picker-Guidelines (P): <https://m3.material.io/components/date-pickers/guidelines> (und /time-pickers)
- [R19] Segmented-Buttons-→-Button-Groups-Ablösung (P): <https://m3.material.io/components/button-groups/guidelines>
- [R20] Toolbars-Guidelines (Bottom-App-Bar-Ablösung, Ein-Emphasis-Regel) (P): <https://m3.material.io/components/toolbars/guidelines>
- [R21] Building with M3 Expressive (P): <https://m3.material.io/blog/building-with-m3-expressive>
- [R22] Compose-Komponenten-API-Mapping (P): <https://developer.android.com/develop/ui/compose/components>
- [R23] Material-3-Theming in Compose (Rollen, Defaults, No-Theme-Caveat) (P): <https://developer.android.com/develop/ui/compose/designsystems/material3>
- [R24] Custom Design Systems in Compose (Wrap-then-Extend-Regel) (P): <https://developer.android.com/develop/ui/compose/designsystems/custom>
- [R25] Now-in-Android-Design-System-Wrapper und Lint-Enforcement (S): <https://github.com/android/nowinandroid> (core/designsystem/component/*, lint/DesignSystemDetector.kt)
- [R26] Compose-Material-3-Releases (stabil 1.4.0 vs. 1.5.0-alpha-Linie; Graduierung von `ButtonGroup`/`SplitButton`/Floating Toolbar innerhalb der Alphas) (P): <https://developer.android.com/jetpack/androidx/releases/compose-material3>
