# App-Design und Navigation

Status: draft

## Kontext

Diese Spec ist das Usability-first-Fundament für den Compose-UI-Skill (REQ-13: Screens mit beim Erstellen angewandter UX-Guidance bauen) und den UX-Audit-Skill (REQ-14): Sie definiert die grundlegende Designsprache und das In-App-Navigationsverhalten, die eine App benutzbar machen — damit generierte Screens und Audit-Befunde eine gemeinsame autoritative Basis teilen.

Der Inhalt ist aus einem Recherche-Durchlauf (August 2026) über drei Quellklassen destilliert: offizielle Design-Guidance (Material 3 inklusive der M3-Expressive-Evolution von 2025, developer.android.com-Design-/Adaptive-/Back-Navigation-Doku, Android-15/16-Behavior-Changes), offizielle Navigationsarchitektur (Navigation 3 — stabil seit November 2025, Navigation 2 offiziell im Maintenance-Mode — plus die Now-in-Android-Referenzimplementierung) und forschungsgestützte Mobile-Usability-Evidenz (Nielsen-Norman-Group-Studien, Hoobers Daumenzonen-Feldforschung, Baymard-Formularforschung, Google-Play-Core-App-Quality-Anforderungen).

Grenzen zu Schwester-Specs: `spec/android/ui-components/` besitzt die Nutzungsregeln auf Komponentenebene; `spec/android/screen-formats/` besitzt Window Size Classes und adaptive Pane-Layouts (diese Spec legt nur fest, welche Navigations-UI in welchen Kontext gehört); `spec/android/test-automation/` besitzt das Navigationstesten; der strukturelle Abdruck (Route/Content-Split, `designsystem`-Modul) bleibt in `spec/android/project-structure/` §E.

Leser: Autoren der Android-Skills dieses Repos sowie Reviewer, die beurteilen, ob Design und Navigation einer generierten oder auditierten App konform sind.

## Ziele

- Das Material-3-Fundament fixieren (Farbrollen, Typografie-Rollen, Shape-Tokens, Surfaces), sodass jeder generierte Screen konstruktiv theme-korrekt, dark-mode-korrekt und accessibility-korrekt ist
- Die Navigationsarchitektur (Navigation 3, Single Activity, Back Stack als State) und die Auswahlregeln für die Navigations-UI fixieren, damit Apps so navigieren, wie Nutzer es erwarten
- Back-Navigation, Deep Links und State-Erhalt gemäß Plattformvertrag verhalten lassen — inklusive Predictive Back und der Android-16-Änderungen
- Forschungsgestützte Usability-Regeln (Daumenzonen, sichtbare Navigation, Fehler-/Empty-/Formular-/Onboarding-Muster) als prüfbare Anforderungen kodieren, nicht als Geschmack

## Nicht-Ziele

- Nutzung und Konsistenz-Governance auf Komponentenebene — gehört `spec/android/ui-components/`
- Window Size Classes, kanonische Layouts und Large-Screen-Qualitätsstufen — gehört `spec/android/screen-formats/` (die Navigations-*Wahl* je Kontext liegt hier, die adaptive Maschinerie dort)
- Konkrete Markenidentität (Palette-Seed-Farben, Fonts, Logo) — Pro-App-Entscheidungen oberhalb des Token-Systems
- Performance-Messung und Latenzbudgets — künftige Perceived-Performance-Spec; diese Spec fixiert nur die Feedback-Semantik (welcher UI-Zustand bei welcher Warteklasse)
- Play-Store-Listing-Assets — Release ist für dieses Repository außerhalb des Scopes

## Anforderungen

### A. Design-Fundament (Material 3)

- **MUSS [MUST]** jede Farbe über Material-Farbrollen ausdrücken (`primary`/`onPrimary`, `surface`/`onSurface`, Container-Varianten), aufgelöst aus `MaterialTheme` — nie hartkodierte Werte oder rohe Tonal-Palette-Werte; Hartkodierung bricht Dark Theme, Kontrastgarantien und Dynamic Color
- **MUSS [MUST]** Inhalt mit seiner `on-*`-Rolle paaren (Inhalt auf `primaryContainer` nutzt `onPrimaryContainer`); nur diese Paarungen tragen die Kontrastgarantie (4,5:1 kleiner Text, 3:1 großer Text/Grafik)
- **MUSS [MUST]** die Material-Typografie-Rollen (Display/Headline/Title/Body/Label-Skala) und Shape-Tokens statt Ad-hoc-Größen und -Radien nutzen; Tiefe entsteht über tonale Surface-Container-Rollen, nicht über Schatten-Overlays
- **SOLLTE [SHOULD]** Dynamic Color (Android 12+) mit statischem Marken-Scheme als Fallback unterstützen; **SOLLTE [SHOULD]** ein echtes Dark Theme ausliefern (eigenes dunkles `ColorScheme`, Nutzerwahl Hell/Dunkel/System mit System als Default); **DARF NICHT [MUST NOT]** sich dauerhaft auf Force-Dark verlassen
- **SOLLTE [SHOULD]** auf der stabilen Material-3-Compose-Linie bauen und die Adoption von M3 Expressive einplanen (die erklärte Designrichtung: federbasierte Motion, erweiterte Shapes, emphasized Type); Expressive-only-APIs bleiben **KANN [MAY]**, solange sie in Alpha liegen
- **MUSS [MUST]** Edge-to-Edge korrekt behandeln: erzwungen ab targetSdk 35 (kein Opt-out ab Android 16) — Insets via `Scaffold`/Material-Komponenten oder explizite `WindowInsets`-Behandlung; keine Touch-Targets in System-Gesten-Zonen
- **MUSS [MUST]** die SplashScreen-API für den Start nutzen (System-Splash seit Android 12); **DARF NICHT [MUST NOT]** eigene Splash-Activities ausliefern; von Branding-Images wird abgeraten
- **MUSS [MUST]** die Accessibility-Design-Baseline überall erfüllen: 48dp-Mindest-Touch-Targets, Text- und Zeilenhöhen in `sp` mit Layouts, die 200 % nichtlineare Font-Skalierung überleben, Content Descriptions für Nicht-Text-Elemente (`null` für Dekoratives), und Farbe nie als einziger Bedeutungsträger
- **SOLLTE [SHOULD]** auf dem 8dp-Raster layouten (16dp-Ränder compact, 24dp ab medium) und Material-Motion-Patterns (Container Transform, Shared Axis, Fade-Through) für Navigationsübergänge nutzen

### B. Navigationsarchitektur

- **MUSS [MUST]** neue Apps single-activity bauen (offiziell strongly recommended); zusätzliche Activities sind bewusste Ausnahmen (Interop, separate Entry Points), keine Gleichrangigen
- **MUSS [MUST]** Navigation 3 für neue Multi-Screen-Compose-Apps nutzen — stabil seit November 2025 [R13][R15a] und in den offiziellen Architecture Recommendations benannt [R16]; Navigation 2 ist im Maintenance-Mode [R15], ihre Nutzung in neuem Code braucht ein protokolliertes Rationale
- **MUSS [MUST]** den Back Stack als app-eigenen State behandeln: Keys implementieren `NavKey` und sind `@Serializable`, gehalten in `rememberNavBackStack` (überlebt Konfigurationswechsel *und* Process Death); das Rendern läuft über `NavDisplay` mit einem `entryProvider`
- **MUSS [MUST]** Screen-ViewModels über die offiziellen Decorators an Navigationseinträge scopen (`rememberSaveableStateHolderNavEntryDecorator` + `rememberViewModelStoreNavEntryDecorator`); keine ViewModels in wiederverwendbaren Komponenten (gemäß `spec/android/project-structure/` §E)
- **MUSS [MUST]** minimale Navigationsargumente übergeben — IDs, nie Objekte; die Destination lädt ihre Daten selbst (Single Source of Truth)
- **MUSS [MUST]** in modularisierten Apps Navigations-Keys von Feature-Implementierungen trennbar halten, gemäß dem offiziellen Navigation-3-Modularisierungsmuster: Wo `spec/android/project-structure/` §C den `:feature:x:api`/`:impl`-Split sanktioniert (große Projekte — für Solo-/Kleinprojekte bleibt er dort verboten), liegen Keys in `:api` und Entry-Builder in `:impl`; ohne den Split exponiert das Feature-Modul selbst Keys und Entry-Builder nach demselben Muster
- **MUSS [MUST]** jeder Top-Level-Destination einen eigenen Back Stack geben (Tab-Wechsel erhält den Pro-Tab-Zustand; erneutes Auswählen eines Tabs leert dessen Stack bis zur Wurzel) — Navigation 3 hat keinen eingebauten Mechanismus, das ist expliziter App-State gemäß dem offiziellen Multiple-Back-Stacks-Rezept
- **DARF NICHT [MUST NOT]** während der Komposition navigieren; Navigation läuft in Callbacks/Effects, Screens exponieren Event-Lambdas und erhalten nie einen Navigations-Controller; schnelle Doppel-Taps werden abgefangen (`dropUnlessResumed`-artig)
- **SOLLTE [SHOULD]** bedingte Flows (Auth, einmaliges Onboarding) im Back-Stack-Halter zentralisieren, gemäß dem offiziellen Conditional-Navigation-Muster — nie als Ad-hoc-Checks in Screens

### C. Wahl der Navigations-UI

- **MUSS [MUST]** 3–5 Top-Level-Destinationen in einer Navigation Bar auf kompakten Fenstern exponieren; mehr als fünf ist verboten (Touch-Target-Gedränge); größere Fenster wechseln gemäß `spec/android/screen-formats/` (Rail ab medium; Expanded Rail darüber)
- **DARF NICHT [MUST NOT]** eine Bottom Navigation Bar auf großen Fenstern verwenden, und **SOLLTE NICHT [SHOULD NOT]** neue Navigation um den modalen Drawer entwerfen — mit M3 Expressive ist der Drawer zugunsten der Expanded Navigation Rail deprecated
- **MUSS [MUST]** Icon *und* Label auf Navigationselementen zeigen und die aktuelle Destination sichtbar markieren (Selected State, Filled-Icon-Konvention gemäß `spec/android/iconography/`): Die Forschung zeigt, sichtbare Navigation schlägt versteckte — in der quantitativen NN/g-Studie senkte versteckte Navigation die Content-Discoverability um über 20 % und verlangsamte mobile Aufgaben um ~15 % [R24]
- **MUSS [MUST]** Primäraktionen in die daumenfreundliche untere Zone legen (Bottom Bar, FAB-Bereich, Bottom Sheets); die Ecken der Top App Bar sind die am schwersten erreichbare Zone und tragen nur sekundäre/seltene Aktionen — Hoober: 75 % der Interaktionen sind daumengetrieben, und die Touch-Genauigkeit nimmt zu den Ecken hin ab
- **SOLLTE [SHOULD]** Suche als Ergänzung zum Browsen behandeln, nicht als Ersatz; maximal ein FAB pro Screen für die eine wichtigste Aktion (Detailregeln in `spec/android/ui-components/`)

### D. Back-Navigation und State

- **MUSS [MUST]** Predictive Back unterstützen: `android:enableOnBackInvokedCallback="true"`, kein Abfangen von `onBackPressed()`/`KEYCODE_BACK` — ab targetSdk 36 werden diese gar nicht mehr aufgerufen; Compose-Abfangen läuft über `BackHandler`/`PredictiveBackHandler`, und Callbacks sind nur aktiviert, solange ihre Bedingung gilt (ein dauerhaft aktivierter Interceptor tötet die Back-to-Home-Animation)
- **MUSS [MUST]** Up und Back innerhalb des App-Tasks identisch halten (Up verlässt die App nie); Exit-Bestätigungen existieren nur für echt ungespeicherte Daten
- **MUSS [MUST]** State gemäß Play Core App Quality erhalten: Rückkehr aus Recents, Sperren/Entsperren und Rotation landen exakt dort, wo der Nutzer war (Eingaben, Scroll-Positionen, Medienpositionen); Process-Death-Restauration läuft über serialisierbare Navigations-Keys plus `rememberSaveable`/`SavedStateHandle`
- **DARF NICHT [MUST NOT]** Orientierung oder Resizability einschränken — ab targetSdk 36 auf großen Screens ignoriert (exakter Breakpoint und Ausnahmen gemäß `spec/android/screen-formats/` §B; das Opt-out stirbt mit targetSdk 37)

### E. Deep Links

- **SOLLTE [SHOULD]** verifizierte App Links (`android:autoVerify` + `assetlinks.json`) für eigene Domain-Inhalte nutzen; Custom Schemes nur für interne/Partner-Flows
- **MUSS [MUST]** Deep-Link-Nutzer direkt zum Inhalt bringen — keine Interstitials, kein erzwungenes Login bevor der Inhalt sichtbar ist (Auth auf die erste geschützte Interaktion verschieben)
- **MUSS [MUST]** bei einem Deep Link mitten in die Hierarchie einen synthetischen Back Stack bauen, der organischer Navigation entspricht; die Deep-Link-APIs von Navigation 3 liegen zum Abrufdatum in der 1.2-Alpha-Linie [R15a] — bis zur Stabilisierung folgt das Intent-Parsing zu einem typisierten `NavKey` dem offiziellen Rezeptmuster
- Deep-Link-Testkommandos gehören `spec/android/adb-workflows/` §D

### F. Usability-Regeln (forschungsgestützt)

- **MUSS [MUST]** Fehlerzustände gemäß den Error-Message-Regeln schreiben: sichtbar nahe der Quelle, spezifisch, konstruktiv (was als Nächstes tun), keine Schuldzuweisung oder Codes als Primärtext, und Nutzereingaben bleiben zur Korrektur immer erhalten
- **SOLLTE [SHOULD]** Undo (Snackbar-Aktion) gegenüber Bestätigungsdialogen für häufige reversible Aktionen bevorzugen; Bestätigungen sind ernsten irreversiblen Konsequenzen vorbehalten
- **MUSS [MUST]** Empty States als Onboarding-Momente gestalten: benennen, was hierher gehört, plus direkte Call-to-Action — nie eine Sackgasse
- **MUSS [MUST]** in Formularen: korrekte Keyboard-Typen je Feld, Autofill-Hints, Validierung beim Verlassen des Feldes (nie beim Tippen), Fehlerzusammenfassung mit erhaltener Eingabe; Tippen minimieren (Forschung: die wahrgenommene Feldanzahl treibt Abbrüche)
- **DARF NICHT [MUST NOT]** irgendeine Funktion nur über eine Custom-Geste erreichbar machen; Swipe-Aktionen sind Beschleuniger mit sichtbaren Alternativen und Undo bei Destruktivem; keine App-Gesten in System-Edge-Gesten-Zonen (`systemGestureExclusionRects` nur wo unvermeidbar, ≤ 200dp pro Kante)
- **DARF NICHT [MUST NOT]** erzwungene Tutorial-Karussells ausliefern — die Forschung zeigt keinen Task-Erfolgs-Nutzen und schlechtere wahrgenommene Schwierigkeit; Onboarding ist kontextuell (Erstkontakt mit einem Feature), und der einzige gerechtfertigte Vorab-Schritt ist funktionale Anpassung
- **MUSS [MUST]** Permissions im Kontext mit vorheriger Begründung anfragen — die NN/g-Forschung berichtet bis zu 28 % höhere Grant-Raten für In-Context-Anfragen, wobei die Messaging-Qualität das Opt-in massiv verschiebt [R28]
- **SOLLTE [SHOULD]** die Antwortzeit-Feedback-Semantik anwenden: sofortiges Feedback auf jeden Tap; kein Indikator unter ~200 ms; Ladeanzeige für kurze unbestimmte Wartezeiten; Fortschrittsanzeige mit Abbruch ab ~10 s (Messung und Budgets gehören der künftigen Performance-Spec)
- **SOLLTE [SHOULD]** Progressive Disclosure anwenden: Kernoptionen zuerst, Fortgeschrittenes hinter einem expliziten Schritt; gleichzeitige Auswahloptionen begrenzen (Choice Overload); Schlüsselinformation zum Scannen vorn platzieren

## Akzeptanzkriterien

Die folgenden Kriterien sind ein bewusst repräsentatives Rollup von §A–§F, keine 1:1-Abbildung; jeder Anforderungspunkt oben ist für sich normativ.

- [ ] Kein generierter Screen enthält eine hartkodierte Farbe, Textgröße oder einen Eckenradius; alles Styling löst über `MaterialTheme`-Rollen und -Tokens auf
- [ ] Die App baut und rendert korrekt im Dark Theme und bei 200 % Font-Skalierung ohne abgeschnittene oder gestutzte kritische UI
- [ ] Edge-to-Edge ist behandelt: kein Inhalt unter Systemleisten ohne Insets-Behandlung, kein interaktives Element in Gesten-Zonen
- [ ] Eine neue Multi-Screen-App nutzt Navigation 3 mit serialisierbaren `NavKey`s und `rememberNavBackStack`; kein `NavController` wird in Screen-Composables gereicht
- [ ] Navigationsargumente sind nur IDs oder einfache Werte; kein `@Serializable`-Payload-Objekt trägt Entitätsdaten
- [ ] Die Top-Level-Navigation hat 3–5 Destinationen mit Icons und Labels, einen sichtbaren Selected State und Pro-Destination-Back-Stacks, die Tab-Wechsel überleben
- [ ] Predictive Back funktioniert Ende-zu-Ende: keine `onBackPressed`-Overrides, Back-Callbacks sind bedingungsaktiviert, und die System-Back-Preview-Animation spielt
- [ ] State-Erhalt besteht die Play-Quality-Prüfungen: Rotation, Recents-Rückkehr und Process Death stellen den sichtbaren Zustand wieder her (verifiziert gemäß `spec/android/test-automation/` §D-Mustern)
- [ ] Deep Links öffnen Inhalte direkt und erzeugen einen realistischen synthetischen Back Stack
- [ ] Jeder Fehlerzustand benennt Problem und nächsten Schritt und erhält Nutzereingaben; jeder Empty State trägt eine Call-to-Action
- [ ] Formularfelder deklarieren Keyboard-Typen und Autofill-Hints; Validierung feuert beim Verlassen, nicht je Tastendruck
- [ ] Keine Funktion ist nur per Geste erreichbar; kein erzwungenes Tutorial-Karussell existiert; Permission-Anfragen erscheinen im Kontext mit Begründung
- [ ] Primäraktionen sitzen auf kompakten Fenstern in der unteren Interaktionszone; die Top App Bar trägt nur Sekundäraktionen
- [ ] Keine Orientierungs- oder Resizability-Einschränkung existiert in Manifest oder Code

## Offene Fragen

Alle vier Fragen sind Parking-Lot-Klasse: Die Anforderungen oben nennen für jede einen funktionierenden Default, die Umsetzung kann also ohne Antwort fortfahren.

- M3-Expressive-Adoptionszeitpunkt: generierte Apps auf `MaterialExpressiveTheme` umstellen, sobald die Compose-APIs aus den 1.5-Alphas graduieren, oder auf Baseline-M3 bleiben, bis der System-Rollout breiter ist?
- Navigation-3-Deep-Links: die 1.2-`DeepLinkMatcher`-APIs übernehmen, sobald sie stabilisieren, oder beim rezeptbasierten Parsing-Muster bleiben?
- Drawer-Deprecation: Gibt es für die Apps dieses Portfolios noch einen legitimen Drawer-Anwendungsfall, oder wird er in generiertem Code komplett verboten?
- Soll der Compose-UI-Skill ein Standard-Template für bedingte Navigation (Auth/Onboarding) scaffolden oder bleibt das pro App?

## Referenzen

Alle Quellen abgerufen am 11.08.2026. Klassenmarker nach Gruppe: R1–R23 und R31–R32 sind primäre/maßgebliche Vendor-Dokumentation (P); R24–R30 sind Forschungs-/Sekundärquellen (S), deren quantitative Befunde inline als Einzelstudien-Ergebnisse attribuiert sind, wo keine unabhängige Korroboration existiert.

- [R1] Material 3 — Farben anwenden / Farbrollen: <https://m3.material.io/styles/color/advanced/apply-colors>
- [R2] Material 3 — Elevation über tonale Surfaces: <https://m3.material.io/styles/elevation/applying-elevation>
- [R3] M3-Expressive-Ankündigung (Motion-Physik, Shapes, Komponenten-Updates): <https://blog.google/products-and-platforms/platforms/android/material-3-expressive-android-wearos-launch/>
- [R4] Compose-Material-3-Releases (stabile Linie vs. Expressive-Alphas): <https://developer.android.com/jetpack/androidx/releases/compose-material3>
- [R5] Dark-Theme-Guidance: <https://developer.android.com/develop/ui/views/theming/darktheme>
- [R6] Dynamic Color: <https://developer.android.com/develop/ui/views/theming/dynamic-colors>
- [R7] Android-15-Behavior-Changes (Edge-to-Edge-Erzwingung): <https://developer.android.com/about/versions/15/behavior-changes-15>
- [R8] Android-16-Behavior-Changes (Orientierung/Resizability ignoriert, Edge-to-Edge final): <https://developer.android.com/about/versions/16/behavior-changes-16>
- [R9] SplashScreen-API und Designregeln: <https://developer.android.com/develop/ui/views/launch/splash-screen>
- [R10] Accessibility-Prinzipien und Apps-Guide (Targets, Kontrast, Labels): <https://developer.android.com/guide/topics/ui/accessibility/apps>
- [R11] Nichtlineare Font-Skalierung (Android 14): <https://developer.android.com/about/versions/14/features>
- [R12] Navigation 3 — Basics (Back Stack als State): <https://developer.android.com/guide/navigation/navigation-3/basics>
- [R13] Navigation-3-Stable-Ankündigung: <https://developer.android.com/blog/posts/jetpack-navigation-3-is-stable>
- [R14] Navigation 3 — Save State (serialisierbare Keys, ViewModel-Decorators): <https://developer.android.com/guide/navigation/navigation-3/save-state>
- [R15] Navigation-Releases (Nav2 Maintenance-Mode): <https://developer.android.com/jetpack/androidx/releases/navigation>
- [R15a] Navigation-3-Releases (stabile Linie, 1.2-Alpha-Deep-Links): <https://developer.android.com/jetpack/androidx/releases/navigation3>
- [R16] Architecture Recommendations (Single Activity, Navigation 3, ViewModel-Scoping): <https://developer.android.com/topic/architecture/recommendations>
- [R17] Navigationsprinzipien (Up/Back, synthetische Stacks): <https://developer.android.com/guide/navigation/principles>
- [R18] Daten zwischen Destinations übergeben (minimale Argumente): <https://developer.android.com/guide/navigation/use-graph/pass-data>
- [R19] Predictive Back: <https://developer.android.com/guide/navigation/custom-back/predictive-back-gesture>
- [R20] App Links (Verifikation): <https://developer.android.com/training/app-links>
- [R21] nav3-recipes (Deep Links, Conditional Navigation, Multiple Back Stacks): <https://github.com/android/nav3-recipes>
- [R22] Material-Navigation-Bar-Guidelines (3–5 Destinationen): <https://m3.material.io/components/navigation-bar/guidelines>
- [R23] Layout- und Navigationsmuster (Bottom-first-Ergonomie, keine Bottom Bar auf großen Screens): <https://developer.android.com/design/ui/mobile/guides/layout-and-content/layout-and-nav-patterns>
- [R24] NN/g — Hamburger-Menüs / Hidden-Navigation-Studie: <https://www.nngroup.com/articles/hamburger-menus/>
- [R25] Hoober — Wie Menschen Telefone halten und berühren: <https://alistapart.com/article/how-we-hold-our-gadgets/> und <https://www.uxmatters.com/mt/archives/2017/07/design-for-fingers-touch-and-people-part-3.php>
- [R26] NN/g — Error-Message-Guidelines: <https://www.nngroup.com/articles/error-message-guidelines/>
- [R27] NN/g — Mobile-Tutorial- und Onboarding-Studien: <https://www.nngroup.com/articles/mobile-tutorials/> und <https://www.nngroup.com/articles/mobile-app-onboarding/>
- [R28] NN/g — Permission Requests (In-Context-Timing): <https://www.nngroup.com/articles/permission-requests/>
- [R29] NN/g — Antwortzeit-Grenzen: <https://www.nngroup.com/articles/response-times-3-important-limits/>
- [R30] Baymard — Mobile-Formular-/Keyboard-/Validierungsforschung: <https://baymard.com/blog/mobile-touch-keyboards> und <https://baymard.com/blog/inline-form-validation>
- [R31] Google Play Core App Quality (Back, State-Erhalt, Targets, Kontrast): <https://developer.android.com/docs/quality-guidelines/core-app-quality>
- [R32] Gesten-Navigations-Konflikte (Exclusion Rects): <https://developer.android.com/develop/ui/views/touch-and-input/gestures/gesturenav>
