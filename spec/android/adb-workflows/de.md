# ADB-Workflows

Status: draft

## Kontext

Die Skills dieses Repositories arbeiten CLI-first (REQ-3): Sie deployen Apps auf Geräte und Emulatoren, debuggen sie und lesen ihre Logs ohne Android Studio. ADB (Android Debug Bridge) ist das Werkzeug, das alle drei Aufgaben trägt, und der Debugging-Skill (REQ-16) sowie die Geräte-Zugriffs-Erlaubnis (REQ-4) stehen direkt darauf. Diese Spec ist die autoritative Definition der ADB-Nutzung in diesem Portfolio: Deployment, Debugging, Log-Zugriff und die Skripting-Robustheitsregeln, die ADB in automatisierten, agentengetriebenen Workflows verlässlich machen.

Der Inhalt ist aus einem Recherche-Durchlauf (August 2026) über drei Quellklassen destilliert: die offizielle ADB-/Platform-Tools-Dokumentation (developer.android.com und die AOSP-Quellen — hochaktuell mit Stand Platform-Tools 37.x: `adb server-status`, mDNS-Backend `libadbmdns`, Wireless-Debugging 2.0), die offizielle Logcat-/Debugging-/Bugreport-Dokumentation (inklusive des AOSP-`logcat --help`-Texts, der die maßgebliche Optionsreferenz ist, seit die Webseite die Optionen nicht mehr vollständig listet) sowie Community- und Produktionspraxis (Agent-Runbooks in realen Repos, die kanonische CI-Emulator-Action, Tool-Status von scrcpy/pidcat/adb-enhanced und Googles neue agentenorientierte `android`-CLI).

Grenzen: Die Test-*Ausführungs*-Strategie gehört `spec/android/test-automation/`; Perfetto/Systemweit-Tracing in der Tiefe gehört `spec/android/perceived-performance/` (hier wird nur die Grenze gezogen); die Regeln zu `debuggable` in Release-Builds teilen sich mit der künftigen Security-Spec.

Leser: Autoren der Android-Skills dieses Repos (insbesondere Debugging- und Projekt-Setup-Skill) sowie Reviewer, die beurteilen, ob die Geräteinteraktion eines Skills konform ist.

## Ziele

- Deployment auf Geräte und Emulatoren deterministisch machen: ein dokumentierter Installationspfad, bekannte Fehlerbilder mit bekannten Fixes
- Log-Zugriff präzise machen: auf die untersuchte App eingegrenzt, in Skripten reproduzierbar, sicher (keine PII in Logs)
- Debugging evidenzgetrieben machen: Crashes, ANRs und App-Zustand werden aus definierten Oberflächen gelesen (Logcat-Buffer, Bugreports, dumpsys) statt geraten
- Jede ADB-Interaktion skript- und agentensicher machen: explizites Geräte-Targeting, echte Exit-Code-Behandlung, begrenzte Wartezeiten, sauberer Zustand

## Nicht-Ziele

- Test-Ausführung und -Orchestrierung — gehört `spec/android/test-automation/` (diese Spec liefert nur die Geräte-Verkabelung darunter)
- Performance-Tracing und Profiling in der Tiefe (Perfetto, gfxinfo-Analyse) — `spec/android/perceived-performance/`; hier nur als Grenze benannt
- Play-Store-Deployment — für dieses Repository außerhalb des Scopes; `bundletool` erscheint nur als lokaler Installationspfad für App Bundles
- Rooted-Device- und userdebug-Build-Workflows — Produktions-Builds sind das Ziel; `adb root` ist dort dokumentiert nicht verfügbar und wird nicht vorausgesetzt
- GUI-Tooling (Android Studio, scrcpy als Produkt) — scrcpy wird als Mirroring-Standard referenziert, aber kein Skill hängt von einer GUI ab

## Anforderungen

### A. Umgebung, Targeting und Verbindung

- **MUSS [MUST]** genau ein `platform-tools`-ADB auf dem `PATH` haben (per `which -a adb` verifizieren); mehrere Installationen verursachen die `adb server version … doesn't match this client`-Kill-Schleife, und Tools mit gebündeltem adb (scrcpy) werden auf das eine gezeigt (`ADB=`-Env)
- **MUSS [MUST]** Platform-Tools aktuell halten — Verhalten ist versionsabhängig (Shell-Exit-Code-Weitergabe ≥ 24 [R2][R27], ssh-artiges Quoting ≥ 23 [R2], `server-status`/Wireless-Debugging 2.0 ≥ 37 [R1][R2])
- **MUSS [MUST]** Geräte explizit targeten, sobald mehr als ein Gerät angeschlossen sein kann: `-s <serial>` pro Aufruf oder `ANDROID_SERIAL` für Sessions exportiert (`-s` überschreibt die Variable); nach jedem Emulator-Retry/-Neustart nutzen alle Folgekommandos explizites `-s`
- **MUSS [MUST]** den Gerätezustand vor dem Handeln prüfen und Zustände auf Abhilfen abbilden: `device` (Achtung: verbunden ≠ fertig gebootet), `offline` (Server neu starten / neu einstecken), `unauthorized` (RSA-Dialog nicht bestätigt — neu verbinden und am Gerät bestätigen)
- **SOLLTE [SHOULD]** Android-11+-Wireless-Debugging über den Pairing-Fluss nutzen (`adb pair ip:port` mit dem Bildschirm-Code, danach Auto-Connect); Skripte verbinden per explizitem `ip:port` und hängen nicht von mDNS-Discovery ab; `adb server-status` und `adb mdns track-services` sind die Diagnosewerkzeuge
- **DARF NICHT [MUST NOT]** den Legacy-Modus `adb tcpip 5555` in geteilten Netzen offen lassen — er hat kein Pairing und akzeptiert jeden Host; er bleibt der pragmatische Fallback für ≤ Android 10 und wird danach mit `adb usb` geschlossen
- **MUSS [MUST]** `adb reverse tcp:<port> tcp:<port>` als kanonischen Weg behandeln, um einen host-lokalen Dev-Server vom Gerät zu erreichen (`localhost` bleibt Secure Context; der Emulator-Alias `10.0.2.2` nicht)
- **DARF NICHT [MUST NOT]** von `adb root`, `run-as` gegen nicht-debuggable Builds oder anderen userdebug-only-Fähigkeiten abhängen — Produktions-Builds sind das Ziel, und `adb root` ist dort dokumentiert nicht verfügbar [R1]

### B. Deployment

- **SOLLTE [SHOULD]** `./gradlew installDebug` als Default-Build-und-Install-Schritt des Dev-Loops nutzen; rohes `adb install` ist das richtige Werkzeug, wenn das APK bereits gebaut ist oder ein bestimmtes Gerät gemeint ist
- **MUSS [MUST]** bei jedem wiederholten `adb install` `-r` übergeben; `-t` für Gradle-Test-APKs (`testOnly`), `-g` zum Vorab-Erteilen aller Runtime-Permissions in hermetischen Läufen, `-d` nur für bewusste Debug-Downgrades
- **MUSS [MUST]** die `INSTALL_FAILED_*`-Decode-Tabelle kennen und den dokumentierten Fix anwenden statt Retry-Schleifen: `UPDATE_INCOMPATIBLE` (Signatur-Mismatch → erst deinstallieren), `VERSION_DOWNGRADE` (→ `-d` oder deinstallieren), `ALREADY_EXISTS` (→ `-r`), `TEST_ONLY` (→ `-t`), `INSUFFICIENT_STORAGE` (→ `df /data`, aufräumen), `USER_RESTRICTED` (OEM-Installationssperre — Xiaomi/MIUI „Install via USB"); Split-APK-Sets laufen über `adb install-multiple`
- **MUSS [MUST]** App Bundles lokal via `bundletool build-apks` + `bundletool install-apks` installieren — ein Bundle lässt sich nicht direkt per `adb install` installieren
- **SOLLTE [SHOULD]** nach der Installation deterministisch starten: `adb shell am start -n <pkg>/<activity>`, bei unbekannter Activity per `cmd package resolve-activity --brief <pkg>` auflösen; das `monkey -p <pkg> 1`-Idiom ist der geräuschvolle Fallback
- **DARF NICHT [MUST NOT]** annehmen, dass es eine „Apply Changes"-CLI gibt — das ist IDE-only; die CLI-Beschleunigungen sind `--fastdeploy` und (mit v4-Signatur) `--incremental`
- **MUSS [MUST]** App-Zustand bewusst zurücksetzen und den Unterschied kennen: `pm clear <pkg>` löscht Daten und widerruft Runtime-Permissions (hermetischer Reset); `am force-stop <pkg>` beendet ohne zu löschen

### C. Log-Zugriff

- **MUSS [MUST]** Log-Lesen auf die untersuchte App eingrenzen: `adb logcat --pid=$(adb shell pidof -s <pkg>)` (nach Prozess-Neustart neu auflösen) oder Tag-Allowlists `adb logcat MyTag:D *:S`; geräteseitiges Filtern (`-s`, tag:priority-Specs, `--regex`) hat Vorrang vor Host-seitigen `grep`-Pipes
- **MUSS [MUST]** in Skripten das Snapshot-Muster nutzen: `adb logcat -c` (je Ziel-Buffer) vor dem Szenario, `adb logcat -d [-e <regex>]` danach — nicht-blockierend, pipefähig, reproduzierbar; ein begrenztes blockierendes Warten ist `adb logcat -e <regex> -m 1`
- **MUSS [MUST]** die Buffer kennen: `main`, `system`, `crash` (Teil des `default`-Sets), `events` (binär, `-v descriptive`), `radio`; Crash-Diagnose liest `-b crash`
- **SOLLTE [SHOULD]** `-v threadtime` (Default) plus Modifier nach Bedarf nutzen (`color` für Menschen, `epoch`/`UTC` zur Korrelation); Datei-Logging via `-f` mit `-r`/`-n`-Rotation
- **MUSS [MUST]** `adb logcat --help` auf dem Zielgerät als maßgebliche Optionsreferenz behandeln — die aktuelle Webseite listet die Optionen nicht mehr vollständig
- **DARF NICHT [MUST NOT]** PII, Credentials oder Tokens im App-Code loggen (offizielle Security-Guidance); Release-Builds strippen Debug-Logs via R8 `-assumenosideeffects` auf `android.util.Log` — was nur mit aktivierter Minification und vorhandener Regel geschieht, nie per Default
- **SOLLTE [SHOULD]** verbose Logging über zur Laufzeit schaltbare Tags führen (`adb shell setprop log.tag.<TAG> VERBOSE`); Timber bleibt der De-facto-Standard fürs App-seitige Logging in Android-only-Apps (stabil, aber eingefroren; Trees nur in Debug-Builds pflanzen)

### D. Debugging-Oberflächen

- **MUSS [MUST]** Java/Kotlin-Crashes aus dem Crash-Buffer von Logcat lesen: Marker `FATAL EXCEPTION` unter Tag `AndroidRuntime`, zuerst Exception-Typ plus oberster eigener Stack-Frame; minifizierte Traces werden mit `retrace` gegen die `mapping.txt` des Builds aufgelöst
- **MUSS [MUST]** Native-Crash-Tombstones und ANR-Traces auf Produktionsgeräten via `adb bugreport` beziehen — die `FS/data/tombstones/`- und `FS/data/anr/`-Spiegel des Zips erreichen Pfade, die direktes `adb pull` ohne Root nicht erreicht
- **MUSS [MUST]** die ANR-Schwellen kennen (5 s Input-Dispatch, 5 s Foreground-Broadcast, `startForegroundService` → `startForeground` binnen 5 s — Plattform-Fakten gemäß der maßgeblichen Vitals-Dokumentation [R8]) und die Suchanker (`am_anr`, `"ANR in"`, `"VM TRACES AT LAST ANR"`); `adb shell am monitor` beobachtet Crashes/ANRs live
- **SOLLTE [SHOULD]** `StrictMode` (`detectAll` + `penaltyLog`, nur Debug-Builds) als ANR-Prävention nutzen und Verstöße aus Logcat-Tag `StrictMode` lesen
- **SOLLTE [SHOULD]** App-Zustand über gezielte `dumpsys`-Services inspizieren (nie nacktes `dumpsys`): `dumpsys activity` (+ Paketfilter), `dumpsys meminfo <pkg>` (Private Dirty, geleakte Activities/Views unter Objects), `dumpsys package <pkg>` (Permissions/Komponenten/userId), `dumpsys battery`/`deviceidle` für Power-State-Simulation
- **MUSS [MUST]** Deep Links mit dem dokumentierten Kommando testen: `adb shell am start -W -a android.intent.action.VIEW -d "<uri>" <pkg>` (`&` in URIs escapen)
- **MUSS [MUST]** Process-Death-Simulationen unterscheiden: `am kill <pkg>` = systeminitiierter Tod eines Hintergrundprozesses (State-Restauration beim Relaunch erwartet); `am force-stop` = nutzerinitiierter Kill (Restauration nicht erwartet) — `force-stop` für Restaurationstests ist ein falsch-negatives Ergebnis
- **KANN [MAY]** einen CLI-Debugger über die JDWP-Kette anhängen (`adb jdwp` → `adb forward tcp:<port> jdwp:<pid>` → `jdb -attach`) — dokumentierter Notausgang, nicht der Default-Workflow
- **MUSS [MUST]** Systemtraces mit Perfettos Helfer `record_android_trace` aufzeichnen statt eine Konfiguration von Hand zusammenzubauen: Er zeichnet auf, holt den Trace und öffnet ihn. Das Skript aus dem Perfetto-Repository beziehen, dann mit Ausgabepfad, Dauer, Puffergröße, App-Filter und den für die Fragestellung nötigen Kategorien aufrufen — `sched` und `freq` für die CPU-Tätigkeit, `view` und `input` für UI-Arbeit, `am`/`wm`/`gfx` für Lebenszyklus und Rendering (`record_android_trace -o <datei>.perfetto-trace -t 20s -b 32mb -a <pkg> sched freq view input am wm gfx`); `--no-open` unterdrückt den UI-Start auf einer Maschine ohne Oberfläche [R29]. Diese Spec besitzt die Aufzeichnung; das Lesen des Traces für ein Performance-Urteil gehört zu `spec/android/perceived-performance/` §D/§E

### E. Skripting- und Agenten-Robustheit

- **MUSS [MUST]** auf echten Boot gaten, nicht auf Transportzustand: `adb wait-for-device` gefolgt von Polling auf `sys.boot_completed` bis `1` (beim Vergleich `\r` strippen) — `wait-for-device` allein kehrt mitten im Boot zurück
- **MUSS [MUST]** Exit-Codes wahrheitsgemäß behandeln: `adb shell` propagiert Geräte-Exit-Codes nur ab API ≥ 24 [R2][R27] (und nie mit `-x`); `am instrument` endet immer mit 0 — `INSTRUMENTATION_STATUS_CODE` aus der `-w -r`-Ausgabe parsen; `adb install`-Ausgabe wird zusätzlich auf `Success`/`INSTALL_FAILED` gegrept
- **MUSS [MUST]** hänganfällige Aufrufe (`screencap`, `dumpsys`, `uiautomator`) in `timeout` wrappen; es gibt kein host-seitiges adb-Timeout-Flag (`-t` ist eine Transport-ID)
- **SOLLTE [SHOULD]** transiente `device not found`/`closed`-Fehler einmal via `adb kill-server && adb start-server` neu versuchen — nie in einer Schleife
- **SOLLTE [SHOULD]** geleakten Zustand mit `trap`-Handlern aufräumen: `adb forward --remove-all`, veränderte `settings` zurücksetzen, gestartete Emulatoren beenden
- **MUSS [MUST]** Screenshots agentensicher über Gerätedatei plus Pull erfassen (`screencap -p /sdcard/x.png && adb pull …`), nicht via `exec-out` (dokumentiertes Häng-Risiko in Produktions-Agent-Runbooks); `screenrecord` ist hart auf 180 s begrenzt, ohne Audio [R1]
- **MUSS [MUST]** Animationen für deterministische UI-Automatisierung deaktivieren: `settings put global window_animation_scale 0.0`, `transition_animation_scale 0.0`, `animator_duration_scale 0.0`
- **DARF NICHT [MUST NOT]** sich für Nicht-ASCII-Eingaben auf `input text` verlassen (ASCII-only); Unicode läuft bei Bedarf über eine IME-Brücke wie ADBKeyBoard
- **MUSS [MUST]** die Argumentreihenfolge-Asymmetrie erinnern: `adb forward LOCAL REMOTE` vs. `adb reverse REMOTE LOCAL` — der häufigste Skripting-Bug
- **SOLLTE [SHOULD]** Runtime- und Spezial-Permissions in der Automatisierung via `pm grant`/`pm revoke` bzw. `appops set` erteilen (oder vorab `install -g`)

### F. Emulator-Verwaltung (CLI)

- **MUSS [MUST]** AVDs nicht-interaktiv erzeugen mit `echo "no" | avdmanager create avd --force -n <name> -k "system-images;…"` nach `sdkmanager --install` des Images
- **MUSS [MUST]** das etablierte Headless-Flag-Set in CI/Agenten nutzen: `-no-window -gpu swiftshader_indirect -noaudio -no-boot-anim` plus ein bewusstes Snapshot-Flag (nächster Punkt; GPU-Fallback `lavapipe` bei Crash); KVM ist auf Linux-Runnern Pflicht (udev-Regel) [R21][R28], gemäß `spec/android/test-automation/` §G
- **MUSS [MUST]** das Snapshot-Flag nach Laufzweck wählen: `-no-snapshot` (voller Cold Boot) für deterministische Debugging- und Reproduktionsläufe; Snapshot-gecachte AVDs mit `-no-snapshot-save` sind die sanktionierte Ausnahme für CI-Wanduhrzeit (gemäß `spec/android/test-automation/` §G)
- **MUSS [MUST]** das Port-Modell respektieren: Konsolen-/adb-Portpaare ab 5554/5555 (+2 je Instanz, Serial `emulator-<console-port>`); headless Instanzen mit `adb -s emulator-<port> emu kill` stoppen
- **KANN [MAY]** QoL-Aufgaben über `adb-enhanced` (`adbe`) als gepflegten Wrapper erledigen

### G. Konventionen der Agenten-Ära

- **SOLLTE [SHOULD]** Googles offizielle agentenorientierte `android`-CLI (`android run --apks`, `android emulator create/start/stop`, `android screen capture`, `android layout`) als Ergänzung zu adb verfolgen — sie standardisiert Deploy/Launch/Inspektion für Agenten, ersetzt aber weder adb noch Gradle
- **SOLLTE [SHOULD]** Geräte-Runbooks als agentenkonsumierbare Skill-Dokumente kodieren (Produktionspräzedenz: Repos mit `.claude/skills/`-adb-Runbooks samt der Robustheitsregeln aus §E)
- **KANN [MAY]** Accessibility-Tree-first-Gerätesteuerung (uiautomator dump; MCP-artige Brücken) mit Screenshot-Verifikation als Fallback nutzen; zielgetriebene Agenten-Loops sind für Regressionstests ungeeignet (das bleibt bei `spec/android/test-automation/`)
- Strukturiertes JSON-Logcat existiert in Stock-adb nicht — Agenten parsen `-v epoch`/threadtime-Text oder Instrumentation-Status-Zeilen; anderslautende Behauptungen betreffen Wrapper-Tooling, nicht adb

## Akzeptanzkriterien

Die folgenden Kriterien sind ein bewusst repräsentatives Rollup von §A–§G, keine 1:1-Abbildung; jeder Anforderungspunkt oben ist für sich normativ.

- [ ] Jedes skill-ausgegebene adb-Kommando im Multi-Device-Kontext trägt `-s` (oder einen dokumentierten `ANDROID_SERIAL`-Export); nach einem Emulator-Neustart folgt kein nacktes adb-Kommando
- [ ] Ein wiederholt installierender Skill übergibt immer `-r` und wendet bei `INSTALL_FAILED_*`-Ausgaben den dokumentierten Fix aus §B an, statt blind zu wiederholen
- [ ] Log-Sammlung in Skills nutzt das Clear-then-Dump-Muster (`-c` … `-d`) oder `--pid`-/Tag-Eingrenzung; kein unbegrenzt blockierendes `logcat` ohne `-m`/Timeout in Skripten
- [ ] Kein generierter oder skill-verfasster App-Code loggt PII; Release-Build-Konfigurationen tragen die R8-Log-Stripping-Regel, wenn über Warnungen hinaus geloggt wird
- [ ] Crash-Triage-Anweisungen referenzieren Crash-Buffer und `retrace`; ANR-Triage referenziert Bugreport-`FS/`-Pfade, nie ein nacktes `adb pull /data/anr`
- [ ] Deep-Link-Tests nutzen `am start -W -a android.intent.action.VIEW`; State-Restaurationstests nutzen `am kill`, nicht `am force-stop`
- [ ] Boot-Wartezeiten pollen `sys.boot_completed`; kein Skript behandelt `wait-for-device` als „gebootet", und kein Test-Gate liest den Exit-Code von `am instrument`
- [ ] Hänganfällige adb-Aufrufe sind timeout-gewrappt, und Screenshots laufen über `/sdcard` + `pull`
- [ ] UI-Automatisierung läuft mit den drei Animations-Skalen auf 0
- [ ] Emulator-Scaffolds nutzen das §F-Headless-Flag-Set und nicht-interaktive AVD-Erzeugung und stoppen Instanzen via `adb emu kill`
- [ ] Die Wireless-Guidance der Spec wird befolgt: pairing-basiertes Wireless Debugging als dokumentierter Default, `tcpip 5555` nur als markierter Legacy-Fallback, der geschlossen wird
- [ ] Kein Skill hängt von `adb root`, `run-as` gegen nicht-debuggable Builds oder anderen userdebug-only-Fähigkeiten ab

## Offene Fragen

- Googles `android`-Agent-CLI: als First-Class-Abhängigkeit des Debugging-Skills übernehmen, sobald sie stabilisiert, oder adb-only bleiben mit der CLI als optionaler Beschleunigung?
- Unicode-Eingabe: Ist ADBKeyBoard (Drittanbieter-IME) als Skill-Abhängigkeit akzeptabel, oder sollen Skills Texteingabe-Automatisierung jenseits von ASCII meiden?
- Wireless-Pairing-Automatisierung: Erst-Pairing ist bewusst interaktiv; sollen Skills nur einen USB-first-Setup-Pfad dokumentieren?

## Referenzen

Alle Quellen abgerufen am 11.08.2026. Klassenmarker: (P) primäre/maßgebliche Vendor- oder AOSP-Dokumentation, (S) sekundär (gepflegte Tool-Repos, Engineering-Runbooks). Plattformverhaltens-Fakten zitieren die eine maßgebliche Primärquelle; Aussagen, die nachgelagertes Tooling steuern, tragen korroborierende Zitate inline.

- [R1] Offizielle ADB-Dokumentation (Architektur, Targeting, Wireless, Install, Shell-Tools): <https://developer.android.com/tools/adb>
- [R2] Platform-Tools-Release-Notes (versionsabhängiges Verhalten, mDNS-Backends): <https://developer.android.com/tools/releases/platform-tools>
- [R3] Offizielle logcat-Seite (+ Verweis auf `adb logcat --help`): <https://developer.android.com/tools/logcat>
- [R4] AOSP-logcat-Quelle/Hilfetext (maßgebliche Optionsreferenz): <https://android.googlesource.com/platform/system/logging/+/refs/heads/main/logcat/logcat.cpp>
- [R5] dumpsys-Dokumentation: <https://developer.android.com/tools/dumpsys>
- [R6] Bug Reports (Zip-Struktur, FS/-Spiegel): <https://developer.android.com/studio/debug/bug-report>
- [R7] Bug Reports lesen (Suchanker): <https://source.android.com/docs/core/tests/debug/read-bug-reports>
- [R8] ANR-Dokumentation (Schwellen, Traces): <https://developer.android.com/topic/performance/vitals/anr>
- [R9] Crash-Dokumentation (FATAL-EXCEPTION-Anatomie): <https://developer.android.com/topic/performance/vitals/crash>
- [R10] Native Crashes / Tombstones: <https://source.android.com/docs/core/tests/debug/native-crash>
- [R11] retrace-Tool: <https://developer.android.com/tools/retrace>
- [R12] Log-Info-Disclosure-Risiko (keine PII, R8-Stripping): <https://developer.android.com/privacy-and-security/risks/log-info-disclosure>
- [R13] StrictMode-Referenz: <https://developer.android.com/reference/android/os/StrictMode>
- [R14] Deep-Link-Test-Kommando: <https://developer.android.com/training/app-links/deep-linking>
- [R15] Doze-/App-Standby-Testsequenzen: <https://developer.android.com/training/monitoring-device-state/doze-standby>
- [R16] Emulator-Kommandozeile (Headless-Flags, Ports): <https://developer.android.com/studio/run/emulator-commandline>
- [R17] avdmanager: <https://developer.android.com/tools/avdmanager>
- [R18] bundletool: <https://developer.android.com/tools/bundletool>
- [R19] Builds von der Kommandozeile (installDebug): <https://developer.android.com/build/building-cmdline>
- [R20] Googles agentenorientierte Android-CLI: <https://developer.android.com/tools/agents/android-cli>
- [R21] android-emulator-runner (Boot-Gate, Animations-Settings, AVD-Cache): <https://github.com/ReactiveCircus/android-emulator-runner>
- [R22] scrcpy (Mirroring-Standard): <https://github.com/Genymobile/scrcpy>
- [R23] adb-enhanced: <https://github.com/ashishb/adb-enhanced>
- [R24] MASTG-JDWP/jdb-Technik (CLI-Debugger-Kette): <https://mas.owasp.org/MASTG/techniques/android/MASTG-TECH-0031/>
- [R25] Process-Death-Simulations-Unterschied: <https://vtsen.hashnode.dev/how-to-simulate-process-death-in-android>
- [R26] Host-lokalen Server vom Gerät erreichen (`adb reverse`, Secure Context) (P): <https://developer.android.com/develop/ui/views/layout/webapps/access-local-server>
- [R27] AOSP-Issue: `adb shell`-Exit-Codes vor API 24 nicht propagiert (S): <https://issuetracker.google.com/issues/36908392>
- [R28] KVM-Hardwarebeschleunigung GA auf GitHub-gehosteten Runnern (S): <https://github.blog/changelog/2024-04-02-github-actions-hardware-accelerated-android-virtualization-now-available/>
- [R29] Perfetto System-Tracing — der Helfer `record_android_trace`, seine Flags und die aufgezeichneten Kategorien: <https://perfetto.dev/docs/getting-started/system-tracing>
