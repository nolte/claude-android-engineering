# Ikonografie

Status: draft

## Kontext

Icons erscheinen auf mehr Oberflächen als jedes andere visuelle Element: In-App-UI, Navigation, Launcher, Notifications, Shortcuts, Quick-Settings-Tiles. Jede Oberfläche hat eigene harte Regeln, und Inkonsistenz zwischen ihnen ist sofort sichtbar. Diese Spec fixiert das Icon-System für Apps, die mit den Skills dieses Repositories gebaut werden — eine Stilfamilie in der App, korrekte Formate je Oberfläche und die Accessibility-Regeln, die Icons benutzbar machen — das Fundament, gegen das der Compose-UI-Skill (REQ-13) generiert und das der UX-Audit-Skill (REQ-14) auditiert.

Der Inhalt ist aus einem Recherche-Durchlauf (August 2026) destilliert: die offizielle Material-Symbols-Dokumentation (Google Fonts), die Material-3-Icon-Guidelines (Designing/Applying Icons, von den kanonischen Seiten gerendert), die Plattform-Icon-Oberflächen (adaptive Launcher-Icons inklusive der Android-16-QPR2-Auto-Theming-Änderung und der Play-Policy 2025 zum Nutzer-Icon-Theming, Notification-Icons, Shortcut- und Tile-Specs), die Compose-Icon-APIs inklusive der 2025er-Deprecation der `material-icons`-Artefakte sowie das Now-in-Android-Referenzmuster (ein zentrales Icons-Objekt im Design-System-Modul).

Grenzen: Komponentennutzung (Icon-Buttons, Navigationselemente) gehört `spec/android/ui-components/`; Farbrollen und Theming `spec/android/app-design-navigation/` §A; Play-Store-Listing-Assets sind Release-Scope und werden nur berührt, wo das Launcher-Icon überlappt.

Leser: Autoren der Android-Skills dieses Repos sowie Reviewer, die beurteilen, ob generierte oder auditierte Icon-Nutzung konform ist.

## Ziele

- Ein Icon-System in der App: Material Symbols in einer einzigen Stilfamilie, konsistentes Gewicht, Fill als Selected-State-Signal
- Korrekte Formate je Oberfläche: adaptive Launcher-Icons mit Monochrome-Layer, Alpha-only-Notification-Icons, spec-konforme Shortcut- und Tile-Icons
- Icons, die per Default barrierefrei sind: beschriftet wenn funktional, stumm wenn dekorativ, groß genug zum Treffen
- Eine wartbare Pipeline: Vector-first-Assets, ein zentrales Icon-Register, keine deprecateten Icon-Bibliotheken in neuem Code

## Nicht-Ziele

- Icon-Nutzung innerhalb von Komponenten (welche Button-Variante, Badge-Platzierung) — `spec/android/ui-components/`
- Marken-/Produktlogo-Design — kreative Pro-App-Arbeit; diese Spec beschränkt nur, wo Logos erscheinen dürfen (Launcher, nicht in In-App-UI-Slots)
- Play-Store-Listing-Grafiken jenseits der Beziehung des 512px-Icons zum Launcher-Icon — Release-Scope
- Illustrations- und Bildsysteme — nur Icons

## Anforderungen

### A. Das Icon-System (Material Symbols)

- **MUSS [MUST]** Material Symbols als In-App-Icon-System nutzen und sich auf genau eine Stilfamilie pro App festlegen; generierte Projekte defaulten auf `outlined` (der Material-Symbols-Default), sofern die App keine andere deklariert, und eine App mischt nie Familien oder Gewichte innerhalb einer Oberfläche (das dokumentierte Anti-Pattern)
- **MUSS [MUST]** die Fill-Achse als Zustandssignal nutzen: gefüllte Variante für den aktiven/ausgewählten Zustand, outlined für inaktiv — die offizielle Navigationskonvention; existiert keine gefüllte Variante, ist Gewichtserhöhung (Semibold) der Fallback, damit die Auswahl von mehr als Farbe getragen wird
- **MUSS [MUST]** Standard-Icons bei 24dp auf dem Icon-Raster rendern, mit mindestens 48dp Touch-Target (20dp/40dp nur in dichten Desktop-Kontexten); Icons unter 20dp tragen immer ein Textlabel
- **SOLLTE [SHOULD]** das Gewicht bei 400 (regular) als Default halten und bei 24dp nie unter 200 gehen; Grade- und Optical-Size-Achsen sind Feinwerkzeuge, keine freien Pro-Icon-Variablen
- **MUSS [MUST]** eigene Icons auf dem Material-Raster zeichnen, wenn dem Symbolset ein Glyph fehlt: 24dp-Trim-Area, 20dp-Live-Area, 2dp-Strich, 2dp-Eckenradien (eckige Innenecken im Outlined-Stil), kein Inhalt außerhalb der Trim-Area — eigene Icons müssen in den Metriken von der Familie ununterscheidbar sein

### B. Compose-Nutzung und Asset-Pipeline

- **DARF NICHT [MUST NOT]** die Artefakte `androidx.compose.material:material-icons-core/-extended` in neuen Code aufnehmen — offiziell „no longer maintained or recommended", mit erheblichen Build-Zeit-Kosten; Bestandsnutzung ist Migrationsschuld, kein Präzedenzfall
- **MUSS [MUST]** Icons als einzelne Vector-Drawable-XMLs beziehen, aus dem Material-Symbols-Katalog (fonts.google.com/icons, Android-Tab) in der gewählten Stil-/Gewichtsvariante der App heruntergeladen und im Design-System-Modul/-Paket unter `res/drawable/ic_<name>.xml` eingecheckt; `Icon` mit `ImageVector`/`painterResource` rendert sie, getönt über `LocalContentColor`/Theme-Rollen — nie hartkodierte Farben
- **MUSS [MUST]** auto-gespiegelte Formen für direktionale Icons nutzen (`Icons.AutoMirrored.*` / `android:autoMirrored="true"`): Navigationspfeile spiegeln in RTL, Medien-Playback- und Uhr-Icons nicht (Regeln gemäß `spec/android/localization/` §D)
- **MUSS [MUST]** den Icon-Zugriff in einem Registry-Objekt im Design-System zentralisieren (das `NiaIcons`-Muster): Features referenzieren das Register, nie direkt eine Icon-Bibliothek — das Register ist der eine Ort, an dem die Stilfamilien-Entscheidung durchgesetzt wird
- **MUSS [MUST]** UI-Icons als Vektor halten (`VectorDrawable`); Raster ist fotografischem Inhalt vorbehalten; animierte Icon-Zustände **KÖNNEN [MAY]** `AnimatedImageVector` (experimentell) oder Compose-Animations-APIs nutzen
- **SOLLTE [SHOULD]** der `ic_<name>`-Ressourcen-Namenskonvention folgen (etablierte Tooling-Konvention)

### C. Launcher-Icon

- **MUSS [MUST]** ein adaptives Icon ausliefern (`mipmap-anydpi-v26`): 108dp-Canvas, Foreground- + Background-Layer (Vektoren bevorzugt), alle kritischen Inhalte innerhalb der 66dp-Safe-Zone, saubere Kanten — keine selbst gezeichneten Masken, Umrisse oder Schatten (OEM-Masken variieren, und das System komponiert Effekte)
- **MUSS [MUST]** einen gestalteten `<monochrome>`-Layer für Themed Icons bereitstellen (als einfarbige Version der Foreground-Silhouette autoriert, nicht als automatische Tönung des Vollfarb-Foregrounds): Nutzer-Icon-Theming ist Play-akzeptierte Policy, und aktuelles Android wendet auf Apps ohne Monochrome-Layer *automatisches* Theming an [R7][R10] — ein fehlender Layer bedeutet ein algorithmisch erzeugtes statt ein gestaltetes Ergebnis
- **SOLLTE [SHOULD]** den Launcher-Glyph als einfache, textfreie Silhouette halten, die Maskierung und Monochrome-Rendering übersteht; das Play-Store-512px-Asset spiegelt dasselbe Artwork (volles Quadrat, keine selbst gerundeten Ecken oder Schatten — Play maskiert dynamisch)
- **DARF NICHT [MUST NOT]** Launcher-/Produktlogo-Artwork in In-App-UI-Icon-Slots verwenden — In-App-Slots folgen §A

### D. Notification-, Shortcut- und Tile-Icons

- **MUSS [MUST]** das Notification-Small-Icon alpha-only gestalten: weißes Artwork auf Transparenz bei 24dp Basis — das System rendert nur den Alpha-Kanal und leitet die Farbe aus `setColor`/Theme ab; farbiges oder flächiges Artwork degradiert zum Klumpen
- **SOLLTE [SHOULD]** das Large-Icon nur nutzen, wenn Bildmaterial Bedeutung trägt (Absender-Avatar — rund für Personen, sonst eckig; Inhaltsquelle; bedeutungsvolles Symbol), und bei vielen Notification-Arten ein Symbol je Art statt des App-Logos
- **MUSS [MUST]** der Shortcut-Spec folgen, wo App-Shortcuts existieren: 48dp-Kreiscontainer (44dp-Live-Area, 2dp-Padding, `#F5F5F5`-Füllung, keine Schatten) mit zentriertem 24dp-Vektor-System-Icon; Avatare als Density-PNGs; höchstens vier verschiedene Shortcuts
- **MUSS [MUST]** Quick-Settings-Tile-Icons als rein weiße 24dp-`VectorDrawable`s liefern (das System tönt nach Tile-Zustand)

### E. Icon-Accessibility

- **MUSS [MUST]** jedem funktionalen Icon eine aussagekräftige `contentDescription` geben (die Aktion, nicht das Bild: „Foto aufnehmen", nicht „Kamera"); zustandsbehaftete Icon-only-Controls beschreiben ihren Zustand; dekorative Icons setzen `contentDescription = null`, damit Screenreader sie überspringen
- **MUSS [MUST]** den Icon-zu-Container-Kontrast bei mindestens 3:1 halten und Bedeutung nie allein in Icon-Farbe kodieren
- Navigations-Item-Label- und Selected-State-Platzierungsregeln liegen in `spec/android/app-design-navigation/` §C; diese Spec liefert die Fill-/Gewichts-Mechanik (filled = aktiv), auf der sie aufbauen

## Akzeptanzkriterien

Die folgenden Kriterien sind ein bewusst repräsentatives Rollup von §A–§E, keine 1:1-Abbildung; jeder Anforderungspunkt oben ist für sich normativ. Die Verifikation der Rendering- und Accessibility-Kriterien läuft über `spec/android/test-automation/` (Screenshot-Tests für Icon-Rendering, ATF-Checks für Content Descriptions und Touch-Targets).

- [ ] Die App nutzt genau eine Material-Symbols-Stilfamilie; kein Screen mischt Familien oder Gewichte
- [ ] Aktive/ausgewählte Navigationszustände rendern die gefüllte Variante (oder den Semibold-Fallback); inaktive rendern outlined
- [ ] Kein Modul hängt von `material-icons-core` oder `material-icons-extended` ab; alle Icons sind eingecheckte Vector Drawables hinter dem zentralen Register
- [ ] Jedes direktionale Icon ist auto-gespiegelt; Medien-/Uhr-Icons nicht
- [ ] Das Launcher-Icon ist adaptiv mit Foreground-, Background- und Monochrome-Layer, Inhalt innerhalb der 66dp-Safe-Zone und ohne eingebackene Maske oder Schatten
- [ ] Das Notification-Small-Icon ist weiß-auf-transparent und rendert auf API 31+ mit gesetzter Akzentfarbe korrekt (kein Klumpen)
- [ ] Jedes funktionale Icon hat eine aktionsformulierte Content Description; jedes dekorative übergibt `null`; Icon-Touch-Targets messen ≥ 48dp
- [ ] Icon-Töne lösen über `LocalContentColor`/Theme-Rollen auf; keine Icon-Aufrufstelle hartkodiert eine Farbe
- [ ] Wo Shortcuts oder Quick-Settings-Tiles existieren, entsprechen ihre Icons den Oberflächen-Specs aus §D
- [ ] Der Icon-zu-Container-Kontrast beträgt mindestens 3:1, und kein Icon kodiert Bedeutung allein über Farbe
- [ ] Kein Launcher-/Produktlogo-Artwork erscheint in einem In-App-UI-Icon-Slot
- [ ] Eigene Icons entsprechen den Material-Raster-Metriken (Trim-/Live-Area, Strich, Ecken) der gewählten Familie

## Offene Fragen

Alle Fragen sind Parking-Lot-Klasse: Die Anforderungen oben nennen für jede einen funktionierenden Default (outlined-Familie per §A, eingecheckte `ic_<name>.xml` per §B, gestalteter Monochrome-Layer per §C).

- Migrationsleitfaden für Bestands-Apps auf `material-icons-extended`: eigene Skill-Operation, oder flaggt der UX-Audit-Skill es nur, ohne automatisch zu remedieren (aktueller Default)?
- Icon-Downloads: beim manuellen Katalog-Download-und-Einchecken-Workflow aus §B bleiben oder ein kleines Fetch-Skript für den Symbols-Katalog ins Projekt-Scaffold verdrahten?
- Stilfamilien-Override: soll der Compose-UI-Skill die Familie beim Scaffolding abfragen oder immer `outlined` starten und die App sie später ändern lassen?

## Referenzen

Alle Quellen abgerufen am 11.08.2026. Klassenmarker: (P) primäre/maßgebliche Vendor-Dokumentation, (S) sekundär (Referenzprojekt-Code, Ökosystem-Dokumentation). m3.material.io-Seiten sind clientseitig gerendert; die Inhalte wurden über gerenderte Abrufe der kanonischen URLs erfasst.

- [R1] Material-Symbols-Guide (Stile, variable Achsen) (P): <https://developers.google.com/fonts/docs/material_symbols>
- [R2] M3 — Applying Icons (Fill/Weight/Grade, Zielgrößen, Labels) (P): <https://m3.material.io/styles/icons/applying-icons>
- [R3] M3 — Designing Icons (Raster, Keylines, Strich, eigene Icons) (P): <https://m3.material.io/styles/icons/designing-icons>
- [R4] M3 — Navigation-Bar-Guidelines (Filled-=-aktiv-Konvention, Kontrast) (P): <https://m3.material.io/components/navigation-bar/guidelines>
- [R5] Compose-Material-Icons-Deprecation und Symbols-Workflow (P): <https://developer.android.com/develop/ui/compose/graphics/images/material>
- [R6] Compose-Material-Releases (AutoMirrored-Deprecations) (P): <https://developer.android.com/jetpack/androidx/releases/compose-material>
- [R7] Adaptive Launcher-Icons (Layer, Safe Zone, Monochrome; Android-16-QPR2-Auto-Theming) (P): <https://developer.android.com/develop/ui/views/launch/icon_design_adaptive>
- [R8] App-Icons erstellen (Image Asset Studio, Dichten, Notification-Generierung) (P): <https://developer.android.com/studio/write/create-app-icons>
- [R9] Play-Icon-Design-Spezifikation (512px, dynamische Maskierung) (P): <https://developer.android.com/google-play/resources/icon-design-specifications>
- [R10] Play-Policy-Änderung: Nutzer-Icon-Theming (2025) (S): <https://www.androidauthority.com/google-play-icon-theming-agreement-3597899/>
- [R11] Notifications-Design-Guidance (Small-/Large-Icon-Regeln) (P): <https://developer.android.com/design/ui/mobile/guides/home-screen/notifications>
- [R12] Notification bauen (Small-Icon-Pflicht) (P): <https://developer.android.com/develop/ui/views/notifications/build-notification>
- [R13] Notification-Icon-Rendering (Alpha-Kanal) (S): <https://documentation.onesignal.com/docs/en/notification-icons>
- [R14] App-Shortcuts-Icon-Design-Guidelines (PDF) (P): <https://developer.android.com/static/shareables/design/app-shortcuts-design-guidelines.pdf>
- [R15] Quick-Settings-Tiles (Weiß-Vektor-Pflicht) (P): <https://developer.android.com/develop/ui/views/quicksettings-tiles>
- [R16] Vector-Drawable-Ressourcen (Vector-first-Begründung) (P): <https://developer.android.com/develop/ui/views/graphics/vector-drawable-resources>
- [R17] Animierte Vector Drawables in Compose (experimentell) (P): <https://developer.android.com/develop/ui/compose/animation/vectors>
- [R18] Compose-Accessibility-Semantics (contentDescription-Regeln) (P): <https://developer.android.com/develop/ui/compose/accessibility/semantics>
- [R19] Icon-Button-Accessibility (zustandsbehaftete Beschreibungen) (P): <https://developer.android.com/develop/ui/compose/components/icon-button>
- [R20] Now-in-Android-Zentral-Icon-Register (S): <https://github.com/android/nowinandroid> (core/designsystem/icon/NiaIcons.kt)
