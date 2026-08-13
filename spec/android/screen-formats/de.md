# Bildschirmformate

Status: draft

## Kontext

Apps, die mit den Skills dieses Repositories gebaut werden, müssen auf Smartphones **und** Tablets nutzbar sein (Operator-Anforderung). Sie fundiert den Compose-UI-Skill (REQ-13) und den Responsiveness-Scope des UX-Audit-Skills (REQ-14). Diese Spec ist die autoritative Definition der unterstützten Bildschirmformate und der adaptiven Maschinerie dahinter: Window Size Classes, kanonische Layouts, die Google-Play-Adaptive-Quality-Stufen und die Android-16-Realität, dass Orientierungs- und Resizability-Einschränkungen auf großen Screens nicht mehr existieren.

Der Inhalt ist aus einem Recherche-Durchlauf (August 2026) destilliert: offizielle Adaptive-Dokumentation (developer.android.com/develop/adaptive-apps — samt Googles Vokabelwechsel 2025 von „Large screen app quality" zu **Adaptive app quality**), die Release-Linien von androidx.window und material3-adaptive, das Play-Tier-System und die Now-in-Android-Referenzimplementierung (vollständig auf `NavigationSuiteScaffold` + Navigation-3-`ListDetailSceneStrategy` migriert [R17]).

Das tragende Prinzip: Entscheidungen hängen am **Fenster**, nie am Gerät. Size Classes sind Fenstereigenschaften, die sich mit Rotation, Falten, Split-Screen und Desktop-Fenstern ändern — „is tablet"-Logik ist per Konstruktion falsch.

Grenzen: Die Auswahlregeln der Navigations-UI (Bar vs. Rail vs. Expanded Rail) liegen in `spec/android/app-design-navigation/` §C; Density-/`dp`-/`sp`-Disziplin und Font-Skalierung teilen sich mit deren §A; Testwerkzeuge gehören `spec/android/test-automation/`.

Leser: Autoren der Android-Skills dieses Repos sowie Reviewer, die beurteilen, ob die Adaptivität einer generierten oder auditierten App konform ist.

## Ziele

- Den Format-Vertrag fixieren: eine App, Phone und Tablet, getrieben von Window Size Classes mit definiertem Verhalten je Klasse
- Die kanonischen Layouts (List-Detail, Supporting Pane, Feed) zur Standardantwort auf „was ändert sich im größeren Fenster" machen
- Google Plays Adaptive-Quality-Tier 3 bedingungslos erfüllen und Tier 2 anpeilen, damit Tablet-Nutzer eine erstklassige App bekommen und Play-Ranking/Warnungen für die App arbeiten
- Bereit sein für die Android-16-Windowing-Realität: keine Orientierungs-Locks, überall resizable, Multi-Window als Normalzustand

## Nicht-Ziele

- Die Wahl der Navigationskomponente je Size Class — gehört `spec/android/app-design-navigation/` §C (diese Spec liefert die Klassendefinitionen, auf die dort verwiesen wird)
- Foldable-Posture-spezifische Erlebnisse (Tabletop-/Book-Modi) und Desktop-Tier-1-Differenzierung — als optionale Erweiterungen benannt, kein Pflicht-Scope
- Wear OS, TV, Auto — außerhalb des Scopes der Apps dieses Portfolios
- Performance-Eigenschaften großer Screens — `spec/android/perceived-performance/`

## Anforderungen

### A. Window Size Classes

- **MUSS [MUST]** Top-Level-Layoutentscheidungen aus Window Size Classes ableiten, via `currentWindowAdaptiveInfo().windowSizeClass` (material3-adaptive) auf der `androidx.window.core.layout.WindowSizeClass`-API; die Breiten-Breakpoints sind compact < 600dp ≤ medium < 840dp ≤ expanded < 1200dp ≤ large < 1600dp ≤ extra-large, Höhen compact < 480dp ≤ medium < 900dp ≤ expanded [R1][R12]
- **DARF NICHT [MUST NOT]** deprecatete Size-Class-APIs in neuem Code nutzen (`WindowWidthSizeClass`/`WindowHeightSizeClass`, `calculateWindowSizeClass` aus `material3-window-size-class`) und **DARF NICHT [MUST NOT]** auf Gerätetyp („isTablet"), physische Bildschirmgröße oder Pixelmaße verzweigen
- **MUSS [MUST]** Size Classes als dynamische Fenstereigenschaften behandeln: Sie ändern sich zur Laufzeit (Rotation, Falten, Split-Screen, Freiform-Fenster), und jeder Klassenübergang erhält den UI-Zustand
- **SOLLTE [SHOULD]** primär auf die Breite keyen (offiziell „usually more important"), das Expanded-Layout zuerst entwerfen und nach unten optimieren; das Large/Extra-large-Opt-in (`supportLargeAndXLargeWidth`) ist ein **KANN [MAY]**, bis Desktop-Fenster relevant werden
- **SOLLTE [SHOULD]** Size Classes nur für die Grobstruktur nutzen (Pane-Anzahl, Navigationstyp); komponentenlokale Anpassung liest eigene Constraints (`BoxWithConstraints`) statt der globalen Klasse

### B. Verhalten je Size Class

- **MUSS [MUST]** die Inhaltsstruktur an der Expanded-Grenze wechseln: compact/medium zeigen eine Pane; expanded und breiter zeigen zwei Panes, wo der Inhalt eine List-Detail- oder Haupt-plus-Kontext-Beziehung hat — ein bewusst einspaltiges responsives Layout (Feed) ist die dokumentierte Ausnahme
- **MUSS [MUST]** Layoutbausteine über Klassen hinweg ersetzen bzw. ein-/ausblenden, statt ein Phone-Layout zu strecken („adaptive apps replace layout components", die offizielle Anti-Stretching-Regel); Inhalte, Business-Logik und Navigationsziele bleiben identisch
- **MUSS [MUST]** auf großen Fenstern Sekundär-UI von voller Breite abhalten: Dialoge, Bottom Sheets, Buttons und Textfelder bekommen Maximalbreiten; Kontextmenüs hängen am Element (Komponentenregeln in `spec/android/ui-components/`)
- **DARF NICHT [MUST NOT]** Orientierungs- oder Resizability-Einschränkungen deklarieren (`screenOrientation`, `resizableActivity`, Aspect-Ratio-Grenzen): ab targetSdk 36 auf Displays ≥ sw600dp ignoriert (Spiele ausgenommen), das temporäre Opt-out entfällt mit targetSdk 37 [R7][R8] — Layouts, Kamera-Previews und Animationen müssen jede Orientierung und jeden Resize überleben
- **MUSS [MUST]** die App in Multi-Window voll funktionsfähig halten: kein Letterboxing/Kompatibilitätsmodus, korrektes Verhalten ohne Fokus (Multi-Resume — Wiedergabe läuft weiter, exklusive Ressourcen wie die Kamera werden über `onTopResumedActivityChanged` abgegeben und zurückgeholt) und schnelle wiederholte Resizes ohne Leaks oder Zustandsverlust

### C. Kanonische Layouts

- **MUSS [MUST]** Sammlung-plus-Detail-Inhalte als **List-Detail** umsetzen (`NavigableListDetailPaneScaffold`, oder die Navigation-3-`ListDetailSceneStrategy`, wenn die App Nav 3 gemäß `spec/android/app-design-navigation/` §B nutzt): zwei Panes auf expanded, eine darunter, Auswahlzustand über Klassenwechsel erhalten (der Typparameter des Navigators ist `Parcelable`)
- **MUSS [MUST]** die Zwei-Pane-Back-Navigation auf dem empfohlenen Default `PopUntilScaffoldValueChange` halten; im Ein-Pane-Modus schließt Back das Detail und kehrt zur Liste zurück
- **SOLLTE [SHOULD]** Hauptinhalt-plus-Kontext als **Supporting Pane** umsetzen (~70/30 auf expanded, gestapelt oder als Sheet darunter) und Sammlungen gleichwertiger Elemente als **Feed** (`LazyVerticalGrid(GridCells.Adaptive(minSize = …))`, degradiert auf compact zu einer Spalte)
- **KANN [MAY]** Pane-Expansion (Drag-to-Resize) und die Reflow-/Levitate-Strategien aus material3-adaptive 1.1/1.2 übernehmen, wo sie Mehrwert bringen

### D. Play Adaptive App Quality

- **MUSS [MUST]** **Tier 3 („adaptive ready")** bedingungslos erfüllen — die Untergrenze, unter der Play die App auf Tablets abwertet und eine Qualitätswarnung zeigt: Full-Window-Rendering ohne Letterboxing, jeder Konfigurationswechsel und jede Kombination (Rotieren + Resize + Falten) übersteht mit intaktem Zustand, volle Funktion im Split-Screen, Multi-Resume-Korrektheit, Kamera-Previews korrekt in jeder Orientierung und jedem Faltzustand sowie Basis-Support für Tastatur, Maus/Trackpad und Stylus [R5][R6]
- **SOLLTE [SHOULD]** **Tier 2 („adaptive optimized")** erfüllen — das Zielniveau dieses Portfolios: size-class-getriebene adaptive Layouts, keine Full-Width-Sekundär-UI, 48dp-Touch-Targets, Fokuszustände für interaktive Elemente, Tastaturnavigation durch die Hauptflüsse plus Standard-Shortcuts (Copy/Paste/Undo, Esc, Enter, Leertaste), Rechtsklick-Kontextmenüs, Hover-Zustände und Content-Zoom [R6]
- **KANN [MAY]** **Tier-1**-Features („adaptive differentiated": Foldable-Postures, Multi-Instance, Drag-and-drop, Stylus-Optimierung, Desktop-Windowing-Politur) pro App verfolgen, wo sie differenzieren
- **MUSS [MUST]** gegen die offizielle Referenzmatrix verifizieren: Foldable 841×701dp, 8"-Tablet 1024×640dp, 10,5"-Tablet 1280×800dp, 13" 1600×900dp [R15] (Ausführung über `spec/android/test-automation/` §D — `DeviceConfigurationOverride.ForcedSize`, Robolectric-Qualifier, Resizable Emulator, `@PreviewScreenSizes`)

### E. Foldables und Desktop-Windowing (begrenzter Scope)

- **MUSS [MUST]** Falten/Entfalten als zustandserhaltenden Konfigurationswechsel behandeln (durch Tier 3 abgedeckt); Apps, die nur Size Classes korrekt umsetzen, sind auf Foldables akzeptabel — Posture-Support ist offiziell optionale Differenzierung
- **MUSS [MUST]** bei einem `FoldingFeature` mit `isSeparating` kritische UI vom Scharnier fernhalten (die kanonischen Pane-Scaffolds tun das automatisch — ein Grund mehr, sie zu nutzen)
- **SOLLTE [SHOULD]** die Desktop-Windowing-Chrome behandeln, wo relevant: Caption-Bar-Insets (`WindowInsets.captionBar`); Freiform-Fenster resizen Apps unabhängig von Legacy-Einschränkungen
- **KANN [MAY]** Tabletop-/Book-Posture-Layouts, Rear-Display-Erlebnisse und Multi-Instance-Support als Tier-1-Arbeit umsetzen

### F. Density und Ressourcen

- **MUSS [MUST]** alle Layoutmaße in `dp` und Text in `sp` ausdrücken (nie Pixel); Vector Drawables sind die Default-Asset-Form, Bitmap-Density-Buckets nur für fotografischen Inhalt (Asset-Regeln in `spec/android/iconography/`)
- **SOLLTE [SHOULD]** im Blick behalten, dass Tablets oft niedrigere Dichten haben als Flagship-Phones — dp-basierte Size Classes, nicht die Auflösung, sind der Grund, warum ein WQHD-Tablet das Expanded-Layout bekommt

## Akzeptanzkriterien

Die folgenden Kriterien sind ein bewusst repräsentatives Rollup von §A–§F, keine 1:1-Abbildung; jeder Anforderungspunkt oben ist für sich normativ.

- [ ] Die App rendert auf jeder Größe der Referenzmatrix full-window, ohne Letterboxing und ohne Kompatibilitätsmodus
- [ ] Das Top-Level-Layout verzweigt nur auf `WindowSizeClass`-Werten; kein Codepfad inspiziert Gerätetyp, physische Größe oder deprecatete Size-Class-APIs
- [ ] List-Detail-Inhalte zeigen auf expanded zwei Panes und darunter eine, mit über die Grenze erhaltener Auswahl und korrektem Zwei-Pane-Back-Verhalten
- [ ] Manifest und Code enthalten keine Orientierungs-, Aspect-Ratio- oder Resizability-Einschränkungen
- [ ] Rotation, Falten/Entfalten, Split-Screen-Eintritt/-Austritt und Fenster-Resizes erhalten den sichtbaren Zustand (Eingaben, Scroll, Auswahl, Medienposition)
- [ ] Die App bleibt im Split-Screen in jeder unterstützten Größe voll nutzbar, und das Verhalten ohne Fokus ist korrekt (Wiedergabe läuft weiter, Kamera freigegeben)
- [ ] Auf großen Fenstern spannt kein Dialog, Sheet, Button oder Textfeld die volle Breite, und Grids werden breiter, statt eine Einzelspalte zu strecken
- [ ] Tastaturnavigation erreicht die Hauptflüsse; Tier-2-Shortcuts, Hover-Zustände und Rechtsklick-Menüs funktionieren, wo die App Tier 2 anpeilt
- [ ] Adaptive Layouts sind über die Referenzmatrix mit dem §D-Tooling der Test-Spec verifiziert (Previews, Forced-Size-Tests, Screenshot-Tests wo vorhanden)
- [ ] Alle Maße sind dp/sp-basiert; keine Pixel-Literale im Layoutcode
- [ ] Wenn ein trennender Falz gemeldet wird, sitzt keine kritische UI auf dem Scharnier

## Offene Fragen

Alle vier Fragen sind Parking-Lot-Klasse: Die Anforderungen oben nennen für jede einen funktionierenden Default (inkrementelle Tier-2-Eingabe, L/XL-Opt-in als KANN, Postures optional, `NavigableListDetailPaneScaffold` als stabiler Pfad).

- Tier-2-Eingabe-Vollständigkeit (volles Shortcut-Set, Content-Zoom) für die *erste* generierte App-Version: von Anfang an scaffolden oder gestuft, nachdem das Phone-Erlebnis stabil ist?
- Large/Extra-large-Opt-in: jetzt übernehmen für künftiges Desktop-Windowing oder aufschieben, bis ein reales Ziel existiert?
- Foldable-Postures: als optionales Standardmodul im Compose-UI-Skill oder nur pro App?
- Die material3-adaptive-Navigation-3-Integration (`ListDetailSceneStrategy`) ist noch experimentell — jetzt festlegen (NiA tut es) oder auf Stabilisierung warten?

## Referenzen

Alle Quellen abgerufen am 11.08.2026. Klassenmarker: (P) primäre/maßgebliche Vendor-Dokumentation, (S) sekundär. Plattformverhaltens-Fakten (Breakpoints, targetSdk-Gates, Qualitätsstufen) zitieren die maßgebliche Primärquelle gemäß Portfolio-Triangulationskonvention; R16–R17 sind korroborierender Kontext.

- [R1] Window Size Classes (Breakpoints, API, Dynamik): <https://developer.android.com/develop/ui/compose/layouts/adaptive/use-window-size-classes>
- [R2] Adaptive-Layouts-Überblick (Ersetzen statt Strecken): <https://developer.android.com/develop/ui/compose/layouts/adaptive>
- [R3] Kanonische Layouts: <https://developer.android.com/develop/ui/compose/layouts/adaptive/canonical-layouts>
- [R4] List-Detail-Scaffolds und Back-Verhalten: <https://developer.android.com/develop/ui/compose/layouts/adaptive/list-detail>
- [R5] Adaptive App Quality (Tier-System): <https://developer.android.com/docs/quality-guidelines/large-screen-app-quality>
- [R6] Tier-3-/Tier-2-/Tier-1-Checklisten: <https://developer.android.com/docs/quality-guidelines/adaptive-app-quality/tier-3> (und /tier-2, /tier-1)
- [R7] Android-16-Behavior-Changes (Orientierung/Resizability ignoriert): <https://developer.android.com/about/versions/16/behavior-changes-16>
- [R8] Orientierungs-/Aspect-Ratio-/Resizability-Guidance: <https://developer.android.com/develop/ui/compose/layouts/adaptive/app-orientation-aspect-ratio-resizability>
- [R9] Multi-Window-Support (Multi-Resume, Resizability-Defaults): <https://developer.android.com/guide/topics/large-screens/multi-window-support>
- [R10] Fold-aware Apps (`FoldingFeature`, Postures): <https://developer.android.com/develop/ui/compose/layouts/adaptive/foldables/make-your-app-fold-aware>
- [R11] Desktop-Windowing-Support: <https://developer.android.com/develop/ui/compose/layouts/adaptive/support-desktop-windowing>
- [R12] androidx.window-Releases (L/XL-Klassen, Deprecations): <https://developer.android.com/jetpack/androidx/releases/window>
- [R13] material3-adaptive-Releases: <https://developer.android.com/jetpack/androidx/releases/compose-material3-adaptive>
- [R14] Screen Densities (dp/sp, Vector-first): <https://developer.android.com/training/multiscreen/screendensities>
- [R15] Testen über Bildschirmgrößen (Referenzgeräte, Werkzeuge): <https://developer.android.com/training/testing/different-screens/tools>
- [R16] Play-Large-Screen-Discovery-Änderungen (Ranking, Warnungen, Formfaktor-Ratings; Ankündigung 2022, Policy weiterhin in Kraft gemäß R5) (P): <https://android-developers.googleblog.com/2022/03/helping-users-discover-quality-apps-on.html>
- [R17] Now-in-Android-Adaptive-Implementierung (NavigationSuiteScaffold, ListDetailSceneStrategy) (S): <https://github.com/android/nowinandroid>
