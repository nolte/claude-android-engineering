# Gefühlte Performance — Start und Jank

Status: draft

## Kontext

Gefühlte Performance ist nicht eine Eigenschaft. Es sind drei, und sie versagen unabhängig voneinander: wie lange die App braucht, bis sie nutzbar ist (**Start**), ob die Frames einer Interaktion vor ihrer Deadline eintreffen (**Jank**), und ob eine unvermeidliche Wartezeit ehrlich kommuniziert wird (**Warteanzeige**). Eine App kann schnell starten und ruckeln, flüssig scrollen und vier Sekunden brauchen, bis überhaupt etwas zu sehen ist, oder beides gut machen und sich trotzdem kaputt anfühlen, weil eine Zwei-Sekunden-Wartezeit gar nichts anzeigt.

Der wiederkehrende Fehler liegt nicht im Beheben, sondern im Messen. Vier Fehlgriffe erzeugen die meisten falschen Schlüsse, und jede Anforderung unten existiert, um einen davon unmöglich zu machen:

- **Den falschen Build messen.** Ein debuggbarer, nicht minifizierter Build hat anderen Code, andere Kompilierung und andere Zeiten. Zahlen daraus sind Fiktion — sie verbergen echte Probleme und erfinden solche, die es im Release nicht geben wird.
- **Das Falsche messen.** Die Zeit bis zum ersten Frame sagt, wann *etwas* erschien, nicht wann die App nutzbar wurde. Eine App, die nach 200 ms ein leeres Skelett zeichnet und nach 3 s fertig geladen ist, hat ein gutes TTID und eine schlechte App.
- **Einen Median berichten.** Jank lebt im Tail. Ein P50 innerhalb der Deadline ist mit einem sichtbar ruckelnden Screen vereinbar.
- **Eine Zahl ohne ihre Bedingungen berichten.** Ein Frame-Budget ohne seine Bildwiederholrate oder eine Startzahl ohne Gerät, Build-Type und Compilation Mode ist mit nichts vergleichbar — auch nicht mit derselben App von letzter Woche.

Diese Spec legt fest, was gemessen wird, unter welchen Bedingungen eine Zahl zählt, welche Budgets aus einer Zahl einen Befund machen und in welcher Reihenfolge Befunde behoben werden.

Provenienz: Schreibtischrecherche (August 2026) über die Android-Vitals-Dokumentation zu Startzeit und Rendering (Quelle der Schwellen für exzessiven Start und eingefrorene Frames), die Macrobenchmark-Dokumentation (Modulaufbau, Metriken, Compilation- und Startup-Modi), die Baseline-Profile-Dokumentation (Erzeugung, Verifikation, Startup Profiles), den Leitfaden zur Startzeitoptimierung sowie die Dokumentation zu JankStats und Perfetto. Wo dieser Korpus eine Zahl festlegt, die keine Herstellerquelle festlegt, sagt die Anforderung das und kennzeichnet sie als Portfolio-Entscheidung.

Grenzen: Die **Scroll**-Messung liegt in `spec/android/long-list-scrolling/` §G — dessen `frameOverrunMs`-Perzentilregeln, die 700-ms-Defektregel und die bewusste Weigerung, ein Scroll-Pass/Fail-Perzentil festzulegen, sind maßgeblich und werden hier referenziert, nie wiederholt oder übersteuert. Die Warteanzeigen-Matrix gehört zu `spec/android/ui-components/` §A und die Reaktionszeit-Wahrnehmungsschwellen zu `spec/android/app-design-navigation/` §F; diese Spec konsumiert beide und definiert keine davon. Der Ausschluss der Benchmark-Bahn aus der Per-Commit-Suite liegt in `spec/android/test-automation/` §F; Geräte-, Trace- und Log-Mechanik in `spec/android/adb-workflows/` §D/§E; die Release-Build-Konfiguration, gegen die gemessen wird, in `spec/android/release-readiness/` §A; Main-Thread- und Dispatcher-Disziplin in `spec/android/app-architecture/` §E; das Stabilitätsbudget für Abstürze und ANRs in `spec/android/release-readiness/` §C.

Leser: Autoren der Android-Skills dieses Repos, die Performance messen oder beheben, sowie Reviewer, die beurteilen, ob eine Performance-Aussage Evidenz oder Eindruck ist.

## Ziele

- Eine Performance-Zahl ohne Bedingungen unmöglich machen
- „Es ist etwas auf dem Bildschirm" von „die App ist nutzbar" trennen und beides verlangen
- Den Tail, nicht den Median, ins Zentrum jeder Jank-Aussage stellen
- Jeder Messung ein Budget geben, damit aus einem Millisekundenwert ein Bestehen oder ein Befund wird
- Die Behebungsreihenfolge festlegen, damit das schlimmste nutzersichtbare Versagen zuerst behoben wird
- Die Behebung zurechenbar machen: eine Änderung, eine Neumessung

## Nicht-Ziele

- Messung von Scroll-Journeys und ihre Budgets — `spec/android/long-list-scrolling/` §G
- Welcher Indikator zu welcher Wartezeit gehört und die Wahrnehmungsschwellen dahinter — `spec/android/ui-components/` §A und `spec/android/app-design-navigation/` §F
- CI-Verdrahtung und Zusammenstellung der Bahnen — `spec/android/test-automation/` §F/§G
- Release-Build-Konfiguration, R8 und das Stabilitätsbudget (Absturz/ANR) — `spec/android/release-readiness/` §A/§C
- Profiling von Speicher, Akku und Netzwerkeffizienz; diese Spec deckt ausschließlich Zeit-bis-nutzbar und Frame-Timing ab
- Serverseitige Latenz; die Antwort des Clients auf ein langsames Backend ist eine Warteanzeige, kein Benchmark

## Anforderungen

### A. Was gemessen wird

- **MUSS [MUST]** die drei Startklassen getrennt berichten und nie aggregieren: **kalt** (Prozess wird neu erzeugt), **warm** (Prozess lebt, Activity wird neu erzeugt), **heiß** (Activity kehrt aus dem Hintergrund zurück) [R1]
- **MUSS [MUST]** beide Anzeigemetriken für den Start berichten, weil sie verschiedene Fragen beantworten [R1]:
  - **TTID** (Time to Initial Display) — der erste Frame ist gezeichnet. Beantwortet „ist überhaupt etwas passiert".
  - **TTFD** (Time to Full Display) — die App ist tatsächlich mit ihren Inhalten nutzbar. Beantwortet „können Nutzende das tun, wofür sie gekommen sind".
- **MUSS [MUST]** TTFD ausdrücklich instrumentieren: `reportFullyDrawn()` oder in Compose `ReportDrawn` / `ReportDrawnWhen { … }` / `ReportDrawnAfter { … }`, platziert dort, wo der Inhalt des Screens wirklich bereit ist, und nicht dort, wo es bequem ist [R1]. Für eine App, die vollständige Darstellung nie signalisiert, **DARF NICHT [MUST NOT]** eine TTFD-Zahl berichtet werden — das Fehlen ist der Befund
- **MUSS [MUST]** das Frame-Vokabular konsistent verwenden [R2]: ein **Janky Frame** überschreitet die Deadline des Displays; ein **Slow Frame** braucht 16 ms–700 ms; ein **Frozen Frame** braucht über 700 ms und wirkt auf Nutzende wie ein Hänger
- **MUSS [MUST]** die Frame-Deadline nennen, gegen die geurteilt wird, denn sie hängt vom Display ab — ~16,7 ms bei 60 Hz, ~11,1 ms bei 90 Hz, ~8,3 ms bei 120 Hz [R2]
- **MUSS [MUST]** jeder berichteten Zahl ihre Bedingungen beifügen: Gerätemodell, Android-Version, Build-Type, Minifizierungszustand, `CompilationMode`, Bildwiederholrate und Iterationszahl. Eine Zahl ohne sie ist mit keiner anderen Zahl vergleichbar und **DARF NICHT [MUST NOT]** eine Regression oder Verbesserung belegen

### B. Wann eine Zahl zählt

- **MUSS [MUST]** auf einem **physischen Gerät** messen — Macrobenchmark rät von Emulatoren ab, weil deren Zahlen nicht repräsentativ für das Nutzererlebnis sind, und wirft auf einem Emulator (oder einem Gerät mit niedrigem Akkustand) einen Fehler, den nur das explizite Instrumentierungsargument `androidx.benchmark.suppressErrors=EMULATOR` unterdrückt [R3][R9]. Ein Lauf, der diese Unterdrückung brauchte, ist ein Rauchtest des Benchmark-Codes, keine Messung: Ein Emulator ist nur für grobe Ladezustands-UI-Prüfungen zulässig, nie für eine berichtete Start- oder Framezahl
- **MUSS [MUST]** einen **nicht debuggbaren, minifizierten, release-förmigen** Build messen, dessen Ziel-App `profileable` deklariert ist [R3], passend zur Release-Konfiguration aus `spec/android/release-readiness/` §A. Eine Zahl aus einem debuggbaren oder nicht minifizierten Build **DARF NICHT [MUST NOT]** als Befund berichtet werden — dieselbe Regel, die `spec/android/long-list-scrolling/` §G für Scroll festlegt
- **MUSS [MUST]** den Kompilierungszustand über verglichene Läufe konstant halten und ihn nennen: `CompilationMode.DEFAULT` bildet ab, was Nutzende bekommen, sobald ein Baseline Profile ausgeliefert ist, `None` den schlechtesten Fall, `Full` keinen von beiden [R3]
- **MUSS [MUST]** genug Iterationen laufen lassen, damit der Tail überhaupt existiert — `measureRepeated` verlangt einen expliziten `iterations`-Wert, und die fünf aus dem Herstellerbeispiel sind die Untergrenze, keine Plattformvorgabe — und **MUSS [MUST]** die Verteilung berichten, nicht einen Einzelwert [R3]
- **MUSS [MUST]** die offensichtlichen Störgrößen vor einem Lauf ausschalten: Animationen deaktiviert gemäß `spec/android/adb-workflows/` §E, Gerät nicht thermisch gedrosselt, Bildschirm an, keine unbeteiligte Vordergrundarbeit
- **MUSS [MUST]** beim Vergleich gegen eine Baseline auf demselben Gerät und derselben Konfiguration neu messen; ein Gerätewechsel ist eine andere Messung, kein Regressionssignal

### C. Budgets

- **MUSS [MUST]** die Android-Vitals-Schwellen für exzessiven Start als **Obergrenze** behandeln, nie als Ziel: kalt ≥ 5 s, warm ≥ 2 s, heiß ≥ 1,5 s sind die Punkte, ab denen die Plattform den Start als defekt ansieht [R1][R8]. Eine App irgendwo in deren Nähe hat einen Befund, kein Budget
- **MUSS [MUST]** jeden **Frozen Frame** (über 700 ms) unabhängig von seiner Seltenheit als Defekt behandeln; die Herstellerleitlinie besagt, dass kein Frame jemals so lange brauchen sollte [R2]. Das deckt sich mit `spec/android/long-list-scrolling/` §G und formuliert es nicht abweichend
- **MUSS [MUST]** Frame-Timing bei P50/P90/P95/P99 berichten und am Tail beurteilen; ein P50 innerhalb der Deadline beweist nichts [R2]
- **MUSS [MUST]** eine Regression gegen die eigene frühere Baseline der App auch dann als Befund behandeln, wenn der Absolutwert im Budget liegt — eine 40-%-Startregression unterhalb der Obergrenze ist trotzdem ein ausgelieferter Defekt
- **Portfolio-Entscheidungen**, als solche gekennzeichnet, weil keine Herstellerquelle sie festlegt. Sie sind die Arbeitszahlen dieses Korpus, revidierbar, und ein Skill **MUSS [MUST]** **jede einzelne** von ihnen beim Berichten als Korpus-Entscheidung kennzeichnen, statt sie als Plattformvorgabe darzustellen. Die herstellerbelegten Regeln oben — die Vitals-Obergrenze und die Frozen-Frame-Defektregel — gehören **nicht** dazu und **DÜRFEN NICHT [MUST NOT]** als Korpus-Entscheidungen gekennzeichnet werden:
  - **TTID, Kaltstart: ≤ 500 ms.** Das Gerät, für das das gilt, ist das Gerät, auf dem die Baseline der App entstanden ist, und der Bericht **MUSS [MUST]** es nennen: Derselbe Code kann auf einem Mittelklassegerät bestehen und auf einem anderen durchfallen — die Zahl ist ein Ziel je App, nie eine geräteübergreifende Konstante
  - **TTFD: gegen die eigene Baseline der App beurteilt**, nicht absolut, denn es ist durch die Daten begrenzt, die der Screen braucht — und gegen die Warteanzeige, die seine Ladezustände den Nutzenden schulden (`spec/android/ui-components/` §A)
  - **Nicht-Scroll-Animationspfade: P95-Framedauer innerhalb der Deadline.** (Null Frozen Frames ist die Herstellerregel oben, nicht Teil dieser Entscheidung.)
- **DARF NICHT [MUST NOT]** irgendein Perzentilbudget auf eine **Scroll**-Journey anwenden: `spec/android/long-list-scrolling/` §G weigert sich bewusst, eines festzulegen, weil keine Herstellerquelle das tut, und eines hier zu erfinden würde eine besitzende Spec übersteuern. Die Scroll-Zahl wird mit ihrem Tail berichtet, samt der Aussage, dass kein Pass/Fail-Perzentil festgelegt ist

### D. Start-Methodik

- **MUSS [MUST]** die berichtete Startzahl mit einem Macrobenchmark-`StartupTimingMetric`-Lauf erzeugen [R3]; `am start -W` und die Logcat-Zeile `ActivityManager: Displayed` sind nur eine schnelle lokale Kontrolle, messen allein TTID und **DÜRFEN NICHT [MUST NOT]** Grundlage eines berichteten Befunds sein. Das lokale TTFD-Gegenstück ist die Logcat-Zeile `ActivityManager: Fully drawn <pkg>/.<Activity>: +<Zeit>`, die das System ausgibt, sobald die App die vollständige Anzeige signalisiert hat [R1] — mit demselben Status: eine Kontrolle, dass die §A-Instrumentierung feuert und ungefähr wann, nie eine berichtete Zahl, und ihr Ausbleiben, obwohl der Screen sichtbar bereit ist, ist selbst der §A-Befund
- **MUSS [MUST]** den Kaltstart als Primärfall abdecken, da dessen Optimierung warm und heiß mitverbessert [R1], und warm und heiß daneben berichten statt stattdessen
- **MUSS [MUST]** einen langsamen Start vor dem Beheben lokalisieren, statt bei `Application.onCreate()` zu raten: einen Perfetto-Trace mit dem Aufruf aufzeichnen, den `spec/android/adb-workflows/` §D besitzt, und ihn gegen die dokumentierten Startphasen lesen [R1][R5]. Die Aufzeichnungsmechanik gehört jener Spec, das Lesen und das Urteil dieser
- **MUSS [MUST]** die vier dokumentierten Start-Kostenstellen prüfen, bevor etwas anderes vorgeschlagen wird [R1]: Arbeit in `Application.onCreate()` und in eifrig initialisierten Content Providern, schwere Initialisierung von Activity und erstem Screen, blockierendes I/O oder Bitmap-Dekodierung auf dem Main-Thread sowie eine eigene Splash-Screen-Activity dort, wo die Plattform-`SplashScreen`-API hingehört
- **SOLLTE [SHOULD]** die App-Startup-Bibliothek oder explizite Lazy-Initialisierung einem Content Provider je Abhängigkeit vorziehen und `by lazy` eifrigen Singletons [R1][R7]

### E. Jank-Methodik

- **MUSS [MUST]** eine berichtete Jank-Zahl mit Macrobenchmark-`FrameTimingMetric` erzeugen [R3] und dabei `frameOverrunMs` lesen, wo verfügbar — wie `spec/android/long-list-scrolling/` §G es für Scroll bereits verlangt
- **DARF NICHT [MUST NOT]** einen Jank-Befund allein auf `dumpsys gfxinfo framestats` stützen, Compose-Oberfläche oder nicht: Die Herstellerdokumentation begrenzt dieses Instrument auf Apps, die über das `View`-basierte Toolkit zeichnen (`Canvas`/View-Hierarchie — was Compose einschließt, dessen `AndroidComposeView` durch dieselbe HWUI-Pipeline rendert), und stellt fest, dass Render-Statistiken für Vulkan-, Unity-, Unreal- und OpenGL-Oberflächen nicht verfügbar sind [R2]. Das Instrument *sieht* einen Compose-Screen also; der Grund, warum es ein grobes lokales Signal bleibt, ist, was es ist, nicht, was es abdeckt — ein Histogramm pro Prozess ohne den Frame-Overrun je Frame, ohne Iterationskontrolle, Kompilierungszustand und Bedingungsprotokoll, die §A/§B verlangen. Die berichtete Zahl kommt aus `FrameTimingMetric` [R3]; eine Vulkan-/GL-Oberfläche hat gar kein `gfxinfo`-Signal
- **MUSS [MUST]** die Ursache vor dem Beheben mit einem Trace lokalisieren — Perfettos Frame-Timeline zeigt, welche Frames verfehlt wurden und was der Main-Thread tat [R2][R5]. Eine ohne Trace vorgeschlagene Jank-Behebung ist geraten
- **MUSS [MUST]** die Ursache in die dokumentierten Familien einordnen statt „es ist langsam" zu berichten [R2]: Main-Thread-Arbeit (I/O, Binder-Aufrufe, Lock-Konkurrenz, Allokations- und GC-Druck), Render-Thread-Arbeit (übergroße Bitmap-Uploads, teure Pfade), Layout- und Rekompositionskosten sowie Bild- oder Datenarbeit, die nicht auf den Main-Thread gehört
- **MUSS [MUST]** Messung und Deutung einer Scroll-Oberfläche an `spec/android/long-list-scrolling/` §G verweisen, einschließlich dessen Regel, dass ein Framework-Wechsel nie die Behebung für eine langsame Liste ist

### F. Baseline und Startup Profiles

- **MUSS [MUST]** für jede App, deren Start oder Scrollen gemessen wird, ein Baseline Profile ausliefern; es ist die wirksamste Einzeländerung überhaupt, mit herstellerseitig berichteten Verbesserungen um 30 % bei der Codeausführung ab dem ersten Start [R4]
- **MUSS [MUST]** es mit dem Baseline-Profile-Gradle-Plugin und einer `BaselineProfileRule`-Journey erzeugen — nie durch Handbearbeitung von `baseline-prof.txt` — und **MUSS [MUST]** Start, die Hauptnavigationspfade und das Scrollen der Hauptliste abdecken (die Scroll-Journey verlangt `spec/android/long-list-scrolling/` §G bereits) [R4]
- **MUSS [MUST]** das Profil gegen den **minifizierten Release**-Build verifizieren und **DARF NICHT [MUST NOT]** gegen den nicht minifizierten Erzeugungs-Build verifizieren [R4]
- **MUSS [MUST]** `androidx.profileinstaller` vorhalten und aktuell halten und **DARF NICHT [MUST NOT]** nach R8 arbeitende DEX-verändernde Werkzeuge einführen, die das Profil oder das DEX-Layout entwerten würden (`spec/android/release-readiness/` §A) [R4]
- **SOLLTE [SHOULD]** daneben ein Startup Profile für die DEX-Layout-Optimierung ergänzen, wo die AGP-Version es unterstützt [R4]
- **MUSS [MUST]** das Profil neu erzeugen, wenn sich die abgedeckten Journeys wesentlich ändern; ein Profil, das die Navigation vom letzten Jahr beschreibt, optimiert Code, den die App nicht mehr ausführt

### G. Benchmark-Modul und Umgang mit Ergebnissen

- **MUSS [MUST]** Benchmarks in einem eigenen `com.android.test`-Modul mit eigenem, von `release` abgeleitetem `benchmark`-Build-Type halten (nicht debuggbar, minifiziert, `matchingFallbacks` bei Mehrmodulprojekten gesetzt), mit als `profileable` deklarierter Ziel-App [R3]
- **DARF NICHT [MUST NOT]** die Benchmark-Bahn in die Per-Commit-CI-Suite aufnehmen — sie ist eine eigene geplante Bahn gemäß `spec/android/test-automation/` §F
- **DARF NICHT [MUST NOT]** Trace-Dateien oder rohe Benchmark-Ausgaben ins Repository committen; sie sind Build-Ausgaben [R3]. Committet wird, wenn eine Regressionsschranke gewünscht ist, ein kleiner Baseline-Vermerk mit den Zahlen **und** den Bedingungen aus §A, unter denen sie gemessen wurden; das Format der Datei ist frei, ihre Bedingungsfelder sind es nicht
- **MUSS [MUST]** im Laufbericht nennen, welche Zahlen neu sind, welche gegen eine Baseline verglichen wurden und welche keine Vergleichsbasis hatten

### H. Behebungsreihenfolge und Zurechenbarkeit

- **MUSS [MUST]** in der Reihenfolge der Nutzerwirkung beheben, nicht in der Fundreihenfolge [R2]: zuerst ANRs und Frozen Frames, dann der Start gegen §C, dann Slow Frames, dann alles Übrige
- **MUSS [MUST]** **eine** Behebung nach der anderen anwenden und die von ihr adressierte Metrik neu messen, bevor die nächste folgt; Bündeln zerstört die Zurechenbarkeit und ist der Weg, auf dem eine Regression zusammen mit einer Verbesserung ausgeliefert wird
- **MUSS [MUST]** die Vorher/Nachher-Differenz mit den Bedingungen beider Läufe festhalten und **MUSS [MUST]** eine Behebung, die ihre Zahl nicht bewegt hat, als solche berichten, statt sie zu behalten, weil sie vernünftig wirkte
- **MUSS [MUST]** einen roten Build oder eine fehlgeschlagene Messung melden, statt weitere Änderungen darauf zu stapeln (Repository-REQ-1, REQ-7)
- **MUSS [MUST]** eine Lücke melden und eine Spec-Erweiterung vorschlagen, wenn eine von dieser Spec nicht abgedeckte Entscheidung nötig wird, statt still zu entscheiden (Repository-REQ-6)

### I. Feldmessung

- **SOLLTE [SHOULD]** JankStats für Frame-Timing im Feld verdrahten, denn Labormessung deckt die Geräte und Journeys ab, an die jemand gedacht hat, und Felddaten den Rest [R2][R6]
- **MUSS [MUST]**, wo Feldtelemetrie existiert, personenbezogene Daten vollständig aus Performance-Ereignissen heraushalten. Das ist eine eigene Regel dieser Spec: `spec/android/security/` §A verbietet das Loggen sensibler Daten und dessen §E regelt die Offenlegungspflicht für Datenflüsse von Dritt-SDKs, aber keiner der beiden Abschnitte legt eine Regel für Telemetrie-Nutzlasten fest — sie wird hier fixiert
- Die absturzfreien und ANR-Budgets, gegen die Felddaten beurteilt werden, liegen in `spec/android/release-readiness/` §C und werden hier nicht wiederholt

## Akzeptanzkriterien

Die Kriterien sind eine repräsentative Zusammenfassung von §A–§I, keine 1:1-Abbildung; jede Anforderung oben ist für sich normativ.

- [ ] Jede berichtete Zahl trägt Gerät, Android-Version, Build-Type, Minifizierungszustand, `CompilationMode`, Bildwiederholrate und Iterationszahl
- [ ] Der Start wird getrennt nach kalt, warm und heiß berichtet, mit TTID und TTFD; eine App ohne Instrumentierung für vollständige Darstellung wird als solche berichtet, statt eine TTFD-Zahl zu bekommen
- [ ] Jede berichtete Zahl stammt von einem physischen Gerät mit einem nicht debuggbaren, minifizierten, profileable Build; keine Emulator- oder Debug-Build-Zahl wird als Befund dargestellt
- [ ] Startzahlen stammen aus `StartupTimingMetric` und Framezahlen aus `FrameTimingMetric`; `am start -W`, die Logcat-Zeilen `Displayed`/`Fully drawn` und `gfxinfo` erscheinen nur als lokale Kontrollen, und kein Jank-Befund ruht allein auf `gfxinfo`
- [ ] Frame-Timing wird bei P50/P90/P95/P99 mit genannter Deadline berichtet; keine Scroll-Journey wird gegen ein erfundenes Perzentilbudget beurteilt
- [ ] Jeder Frozen Frame wird als Defekt berichtet; der Start wird gegen die Vitals-Obergrenze und das Korpusziel beurteilt, und **jede** Portfolio-Entscheidung aus §C ist im Bericht als Korpus-Entscheidung gekennzeichnet, die herstellerbelegten Regeln dagegen nicht
- [ ] Verglichene Läufe halten `CompilationMode` konstant und nennen ihn, laufen auf demselben Gerät und derselben Konfiguration und entstanden mit deaktivierten Animationen auf einem thermisch ungedrosselten Gerät
- [ ] Jeder Jank-Befund benennt seine Ursachenfamilie (Main-Thread, Render-Thread, Layout/Rekomposition oder Arbeit, die nicht auf den Main-Thread gehört), statt zu berichten, dass ein Screen langsam ist
- [ ] Eine Regression gegen die eigene Baseline der App wird auch dann als Befund berichtet, wenn der Absolutwert im Budget liegt
- [ ] Ein Baseline Profile existiert, ist plugin-erzeugt aus einer Journey über Start, Navigation und das Scrollen der Hauptliste und ist gegen den minifizierten Release-Build verifiziert
- [ ] Benchmarks liegen in einem eigenen `com.android.test`-Modul auf einem von Release abgeleiteten `benchmark`-Build-Type und fehlen in der Per-Commit-CI-Suite
- [ ] Keine Trace-Datei und keine rohe Benchmark-Ausgabe ist committet; ein committeter Baseline-Vermerk trägt die Bedingungen aus §A
- [ ] Behebungen werden einzeln angewandt, jede gegen die von ihr adressierte Metrik neu gemessen, mit Differenz und den Bedingungen beider Läufe — einschließlich der Behebungen, die nichts gebracht haben
- [ ] Wo Feld-Performance-Telemetrie (JankStats oder Äquivalent) existiert, tragen ihre Ereignis-Nutzlasten keine personenbezogenen Daten — keine Identifikatoren, Freitexte oder Bildschirminhalte jenseits der Metrik, des Screen- oder Journey-Namens und der §A-Bedingungen

## Offene Fragen

Jede Frage nennt die Vorgabe, die die Anforderungen oben bereits kodieren.

- Das Scroll-Pass/Fail-Perzentil bleibt offen, geerbt aus `spec/android/long-list-scrolling/` §Offene Fragen: Keine Herstellerquelle legt eines fest. Vorgabe: den Tail berichten, kein Urteil behaupten. Es festzulegen bräuchte eigene Messungen dieses Korpus über mehrere Geräte
- Soll der Korpus ein Referenzgerät benennen, damit kalte TTID-Zahlen über Apps hinweg vergleichbar werden? Parkplatz: §C löst die Mehrdeutigkeit auf, indem es das Ziel auf das Gerät bezieht, auf dem die Baseline der App entstanden ist, und verlangt, dass der Bericht es nennt — kein Lauf wird dadurch blockiert. Ein portfolioweites Referenzgerät zu benennen bräuchte Hardware, die dieser Korpus nicht hat; bis dahin wird die geräteübergreifende Vergleichbarkeit der Absolutzahl ausdrücklich nicht behauptet
- Soll ein committeter Baseline-Vermerk verpflichtend sein statt abhängig vom Wunsch nach einer Regressionsschranke? Vorgabe: abhängig — §G legt seinen Inhalt fest, nicht seine Existenz
- Soll JankStats im Feld für die eigenen Apps des Betreibers ein MUSS sein? Vorgabe: SOLLTE, da eine Solo-App legitim keine Telemetrie-Pipeline haben kann

## Referenzen

- [R1] App startup time — kalt/warm/heiß, TTID und TTFD, `reportFullyDrawn` und die Compose-`ReportDrawn*`-APIs, die Vitals-Schwellen für exzessiven Start und die dokumentierten Start-Kostenstellen: <https://developer.android.com/topic/performance/vitals/launch-time>
- [R2] Slow rendering — Definitionen und Schwellen für Janky, Slow und Frozen Frames, die Deadline je Bildwiederholrate, die Messinstrumente und ihr Geltungsbereich sowie die dokumentierten Jank-Ursachenfamilien: <https://developer.android.com/topic/performance/vitals/render>
- [R3] Macrobenchmark overview — eigenes `com.android.test`-Modul, von Release abgeleiteter Benchmark-Build-Type, profileable Ziel-App, `StartupTimingMetric`/`FrameTimingMetric`, `CompilationMode`, `StartupMode`, Iterationen, Emulatoren abgeraten (Fehler, sofern nicht unterdrückt) und Ablageort der Traces: <https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview>
- [R4] Baseline Profiles overview — Erzeugung über Gradle-Plugin und `BaselineProfileRule`, Journey-Abdeckung, Verifikation gegen den minifizierten Release, Startup Profiles und `ProfileInstaller`-Voraussetzungen: <https://developer.android.com/topic/performance/baselineprofiles/overview>
- [R5] Perfetto — Trace-Aufzeichnung und die Frame-Timeline zum Lokalisieren verfehlter Frames und der Startphasen: <https://perfetto.dev/docs/>
- [R6] JankStats — Erhebung von Frame-Timing im Feld: <https://developer.android.com/topic/performance/jankstats>
- [R7] App-Startup-Bibliothek — Ersatz von Content Providern je Abhängigkeit durch explizite Initialisierungsreihenfolge: <https://developer.android.com/topic/libraries/app-startup>
- [R8] Android vitals — die Metriken und Schwellen, an denen die Plattform eine App misst: <https://developer.android.com/topic/performance/vitals>
- [R9] Macrobenchmark-Instrumentierungsargumente — `androidx.benchmark.suppressErrors` und die Fehlerklassen `EMULATOR`/`LOW-BATTERY`, die es unterdrückt: <https://developer.android.com/topic/performance/benchmarking/macrobenchmark-instrumentation-args>
