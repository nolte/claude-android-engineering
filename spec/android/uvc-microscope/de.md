# USB-C-(UVC-)Mikroskopkameras

Status: draft

## Kontext

Ein externes USB-Mikroskop ist der günstigste Weg, einer Android-App den vergrößerten Blick auf ein physisches Objekt zu geben — ein Blatt mit Verdacht auf Schädlingsbefall, eine Lötstelle, eine Materialprobe. Es ist zugleich der Punkt, an dem gewöhnliches Android-Kamerawissen aufhört zu stimmen: Das Kamera-Framework der Plattform macht diese Geräte nicht verlässlich sichtbar, die gepflegte Community-Engine hat Artefakte veröffentlicht, die nicht auflösen, und ihr USB-Berechtigungscode stürzt unter einem modernen `targetSdk` schlicht ab. Ein Skill, der die Sache angeht wie CameraX, produziert eine App, die nicht baut, nicht startet oder einen schwarzen Bildschirm zeigt.

Diese Spec ist die autoritative Definition, wie die Skills dieses Portfolios eine UVC-Kamera (USB Video Class) integrieren: welcher Zugriffsweg tragfähig ist, wie die Engine-Abhängigkeit bereitgestellt wird, welche Defekte umgangen werden müssen, wie Standbilder entstehen, welche physischen Bedienelemente am Mikroskopkörper erreichbar sind und — entscheidend für die Iterationsgeschwindigkeit — wie eine solche App überhaupt getestet wird, wenn die Peripherie den einzigen USB-Port des Geräts belegt.

Herkunft: Anders als die schreibtischrecherchierten Specs dieses Korpus sind die folgenden Anforderungen überwiegend **gemessen**. Sie stammen aus einer vollständigen Integration, die am 11.08.2026 gebaut und hardwareverifiziert wurde — gegen ein Generalplus-Mikroskop `1b3f:2002` (verkauft als „4K-WiFi-Mikroskop") auf einem Pixel 7a mit Android 16 und AUSBC 3.3.3. Jede mit [M] markierte Aussage wurde auf dieser Hardware beobachtet; Plattformverhalten ist auf Herstellerdokumentation belegt. Wo ein Befund für einen konkreten Gerätekörper und nicht für UVC allgemein gilt, sagt die Anforderung das ausdrücklich.

Grenzen: ADB-Transport, Installationsfehler und Log-Zugriffsmechanik gehören `spec/android/adb-workflows/` — diese Spec ergänzt nur, was sich ändert, wenn eine Peripherie den USB-Port belegt. Die UX von Laufzeitberechtigungen gehört `spec/android/app-design-navigation/` §F, die Sparsamkeit bei Berechtigungen `spec/android/security/` §E. Die Teststrategie bleibt bei `spec/android/test-automation/`; hier wird nur begründet, warum diese Tests nicht auf einem Emulator laufen können. Upload-, Speicher- und Bilderkennungspipelines, die ein aufgenommenes Bild weiterverarbeiten, sind außerhalb des Geltungsbereichs.

Leserschaft: Autorinnen und Autoren der Android-Skills dieses Repositories, die Mikroskop- oder Externkamera-Fähigkeit ergänzen, sowie Reviewer, die die Konformität einer solchen Integration beurteilen.

## Ziele

- Die Entscheidung über den Zugriffsweg einmal und belegt treffen, damit kein Skill CameraX-gegen-nativ für externe Kameras neu aufrollt
- Die Bereitstellung der Abhängigkeit reproduzierbar machen, obwohl die Upstream-Veröffentlichung auf eine Weise kaputt ist, die nur teilweise auflöst
- Die Integrationsebene einmal festlegen, damit die Defekte des Wrappers wegkonstruiert statt wiederholt umgangen werden
- Jeden bekannten Engine-Defekt in eine benannte Umgehung mit erkennbarem Symptom überführen, damit ein Skill denselben Absturz nicht zweimal debuggt
- Aufnahmen ein Bild im Speicher liefern lassen, das eine Upload-Pipeline verarbeiten kann — in einer bewusst gewählten und nicht von der Vorschau geerbten Auflösung
- Die physischen Bedienelemente am Mikroskopkörper dort erreichbar machen, wo sie verdrahtet sind, und dort ehrlich als nicht verfügbar ausweisen, wo sie es nicht sind
- Die geräteabhängige Entwicklungsschleife beschleunigen: Portkonflikt, Wachzustandsfalle und die diagnostischen Wahrheitsquellen sind vorab bekannt

## Nicht-Ziele

- Arbeit mit eingebauten Kameras (CameraX, Camera2 auf internen Objektiven) — dort gilt gewöhnliche Kameraführung, unberührt von dieser Spec
- Videoaufzeichnung, Streaming oder Encoding vom UVC-Gerät — diese Spec deckt Live-Vorschau und Einzelbildaufnahme ab
- Der geräteeigene WLAN-/Access-Point-Modus des Mikroskops — eine eigene Produktfläche, die den USB-Weg des Telefons umgeht und dessen WLAN belegt
- Upload, Persistenz und nachgelagerte Bildverarbeitung einer Aufnahme
- Play-Store-Distributionsfragen für Apps, die USB-Host-Features deklarieren
- Audio von zusammengesetzten UVC-/UAC-Geräten

## Anforderungen

### A. Zugriffsweg

- **DARF NICHT [MUST NOT]** versuchen, eine externe UVC-Kamera über die Web-Plattform zu erreichen: `getUserMedia` in WebView oder PWA macht externe Kameras unter Android nicht sichtbar [R7], und WebUSB kann sie gar nicht ansteuern, weil UVC über **isochrone** Endpunkte streamt, die WebUSB nicht unterstützt [R6]
- **DARF NICHT [MUST NOT]** annehmen, ein React-Native- oder plattformübergreifender Kamera-Wrapper decke das ab — `react-native-vision-camera` baut auf Camera2 auf, und externe UVC-Geräte liefern dort regelmäßig `undefined` [R8][R9]; der USB-Bildabgriff erfordert nativen Android-Code, unabhängig vom UI-Framework der App
- **SOLLTE [SHOULD]** Camera2s `LENS_FACING_EXTERNAL` als unzuverlässig statt als nicht vorhanden behandeln: Die Konstante existiert [R5], doch die Abdeckung für USB-Kameras hängt vom OEM ab und darf auf einem Zielgerät nicht vorausgesetzt werden — ein Skill **DARF NICHT [MUST NOT]** eine erforderliche Fähigkeit darauf bauen, ohne sie auf dieser Hardware zu verifizieren
- **MUSS [MUST]** deshalb für jede erforderliche Externkamera-Fähigkeit eine native `libuvc`-basierte Engine einbinden [R4]; in diesem Portfolio ist das AUSBC (AndroidUSBCamera) [R1]
- **SOLLTE [SHOULD]** die Deskriptoren des konkreten Zielgeräts erfassen, bevor darum herum entworfen wird — Vendor-/Produkt-ID, Pixelformat und Moduliste —, weil Aushandlung und Standbildstrategie davon abhängen; das Referenzgerät ist `1b3f:2002`, `iProduct = "GENERAL - UVC"`, UVC 1.00, buspowered, MJPEG, Modi 3840×2160 / 2048×1024 / 1920×1080 / 1280×720 [R7]
- **DARF NICHT [MUST NOT]** der angegebenen Bildrate trauen: Der Deskriptor des Referenzgeräts nennt 30 fps, liefert aber rund 4,7 fps bei 4K und 17 fps bei 1080p [R7]; vor der Wahl eines Vorschaumodus messen
- **MUSS [MUST]** ein neu vermessenes Gerät in §Verifizierte Geräte eintragen — Vendor-/Produkt-ID, Modi, gemessene Raten, welche Körpertasten USB erreichen und ob die UVC-Zoomsteuerung unterstützt wird —, damit das nächste Projekt die Messung erbt statt eine Hardwaresitzung zu wiederholen

### B. Engine-Integrationsebene und Artefaktbereitstellung

- **MUSS [MUST]** auf der `libuvc`-Ebene integrieren — `USBMonitor` plus `UVCCamera` — statt über AUSBCs Komfort-Wrapper `CameraUVC`. Dessen Kosten sind konkret und kumulativ: Er verbirgt den Button-Callback hinter einem privaten Feld (§F), besitzt eine Öffnungssequenz mit Wettlauf (§D) und setzt einen Moduswechsel als vollständigen Neustart mit fest kodierter Sekundenpause um (§G). Eine Ebene tiefer zu integrieren beseitigt alle drei, und was es kostet — ein eigener Kamera-Thread, Flächenverwaltung und Modusaushandlung — sind rund 150 Zeilen gegen die 200, die der Wrapper verdrängt [M]
- **MUSS [MUST]** die USB-Berechtigung über den Plattform-`UsbManager` erwerben und `USBMonitor.register()` niemals aufrufen: `register()` ist der einzige Träger des `targetSdk`-34-Defekts aus §C, während `hasPermission()`, `openDevice()` und der `UsbControlBlock`-Konstruktor nur von der erteilten Berechtigung und dem `UsbManager`-Handle abhängen. Die Methode nicht aufzurufen beseitigt den Defekt, statt ihn zu umgehen [M]
- **MUSS [MUST]** prüfen, dass jedes Artefakt der gewählten Version auflöst, bevor sie gepinnt wird, und **MUSS [MUST]** eine auflösende POM als unzureichenden Beleg behandeln — AUSBC 3.3.3 ist unvollständig veröffentlicht (JitPacks Build dieses Tags scheitert mangels NDK in `:libuvc:ndkClean`), sodass `libausbc` existiert, `libuvc` und `libnative` aber nie veröffentlicht wurden, und `libnative:3.3.3` liefert eine POM, deren AAR mit 404 antwortet, wodurch die Auflösung spät und mit irreführender Meldung scheitert [R2][M]
- **SOLLTE [SHOULD]** `libuvc:3.2.7` pinnen, dessen Graph (`libuvccommon`, `appcompat`, `xlog`) vollständig auflöst und das die gesamte von dieser Spec benötigte API trägt — `openDevice`, `setButtonCallback`, `setStatusCallback`, `setPreviewSize`, `setFrameCallback`, `setPreviewTexture`, `checkSupportFlag` [M]; es statt `libausbc` zu nehmen entfernt `libnative` vollständig aus dem Graphen und macht Vendoring überflüssig
- **MUSS [MUST]** beachten, dass die 3.2.x-Linie den ursprünglichen Namensraum `com.serenegiant.usb` verwendet, während 3.3.x auf `com.jiangdg.*` umbenannt hat — die beiden Generationen sind nicht mischbar, und genau deshalb kann ein Projekt auf `libausbc:3.3.3` kein veröffentlichtes `libuvc` einsetzen und wird ins Vendoring gezwungen [M]
- **SOLLTE [SHOULD]** nur dort, wo eine Wrapper-Abhängigkeit unvermeidbar ist, eine Veröffentlichungslücke mit einem versionierten, mitgelieferten Maven-Repository unter `third_party/` schließen, das die fehlenden Artefakte unter ihren Originalkoordinaten hält, samt README, das je Artefakt festhält, woher die Bytes stammen, warum diese Quelle akzeptabel ist und was sie überflüssig machen würde; das Repository **MUSS [MUST]** vor dem entfernten deklariert und beide mit `content { includeModule(...) }` eingeschränkt werden. Die Engine in CI aus Quellen zu bauen ist **nicht** gerechtfertigt: Es holte dieselbe NDK-Toolchain zurück, an der die Upstream-Veröffentlichung scheiterte, für eine Abhängigkeit, die die obige Ebenenentscheidung ohnehin entfernt
- **SOLLTE [SHOULD]** im selben Rückfallszenario `libuvc` als ausdrückliche Compile-Abhängigkeit neben `libausbc` aufnehmen — die veröffentlichte POM stuft es als `runtime` ein, doch seine Typen (`IDeviceConnectCallBack`, `USBMonitor.UsbControlBlock`) tauchen in der API auf, die ein Aufrufer implementieren muss, sodass die Kompilierung ohne sie scheitert [M]

### C. Manifest, Berechtigungen und Geräteanschluss

- **MUSS [MUST]** `<uses-feature android:name="android.hardware.usb.host" android:required="false" />` deklarieren — `required="true"` schlösse jedes Gerät ohne OTG von der Installation aus, obwohl die App dort mit einer klaren Meldung „kein USB-Host" weiterhin laufen sollte [R3]
- **MUSS [MUST]** die Laufzeitberechtigung `CAMERA` deklarieren und vor dem Öffnen des Streams halten: AUSBC verweigert ab `targetSdk >= 28` jedes UVC-Gerät ohne sie, obwohl keine Plattformkamera beteiligt ist [M]; die Begründung gegenüber der Nutzerin **MUSS [MUST]** das Mikroskop erklären, nicht eine Selfie-Kamera
- **MUSS [MUST]** die USB-Freigabe als eigene, zweite Zustimmung behandeln: Sie wird pro Gerät vom System-USB-Dialog erteilt, nicht vom Android-Laufzeitberechtigungsfluss, und eine Ablehnung ist ein anderer Zustand als eine verweigerte `CAMERA`-Berechtigung [R3]
- **MUSS [MUST]** die Berechtigungsanfrage beim Schreiben `targetSdk`-korrekt bauen: Der Intent hinter dem `PendingIntent` muss **explizit** sein (`setPackage`) und dabei **veränderlich bleiben** — `UsbManager` hängt die Freigabe-Extras an, `FLAG_IMMUTABLE` zerstört den Ablauf —, und ein Receiver für die eigene Berechtigungs-Action muss ab API 33 mit `RECEIVER_NOT_EXPORTED` registriert werden [R12][R13]
- **MUSS [MUST]** das Symptom für den Fall kennen, dass eine Engine das falsch macht, denn es ist fatal und sofort statt bloß eingeschränkt: `USBMonitor.register()` in AUSBC 3.3.3 verpackt einen impliziten Intent in einen veränderlichen `PendingIntent` und wirft bei der ersten Registrierung unter `targetSdk >= 34` `IllegalArgumentException: … disallows creating or retrieving a PendingIntent with FLAG_MUTABLE, an implicit Intent …` [R12][M]. Die Ebenenentscheidung aus §B vermeidet diese Methode vollständig; ein Projekt, das das nicht kann, **MUSS [MUST]** das mitgelieferte Artefakt entlang der beiden obigen Linien patchen
- **SOLLTE [SHOULD]** einen anschlussgetriebenen Start über einen Intent-Filter `android.hardware.usb.action.USB_DEVICE_ATTACHED` mit einer `device_filter.xml` für die Ziel-Vendor-/Produkt-ID anbieten [R3] und **DARF NICHT [MUST NOT]** den einzigen Einstiegspunkt der App davon abhängig machen — Filter gelten pro Gerät und scheitern bei nicht gelisteter Hardware lautlos
- **MUSS [MUST]** ein Zustandsmodell anbieten, das die für Nutzende handlungsrelevanten Fehlerfälle unterscheidet: kein Gerät angeschlossen, Gerät angeschlossen aber USB-Freigabe ausstehend, USB-Freigabe verweigert, Host-Modus vom Telefon nicht unterstützt und Engine-Fehler — diese zu einem „Kamera nicht verfügbar" zusammenzufassen macht die App im Feld undiagnostizierbar

### D. Lebenszyklus des Streams

- **MUSS [MUST]** die Öffnungssequenz mit einem Nebenläufigkeits-Flag absichern, wem auch immer es gehört. Die Gefahr ist generisch — ein freigegebenes Gerät und eine lebende Fläche treffen aus unabhängigen Callbacks ein —, doch AUSBC verschärft sie, indem es `isCameraOpened()` erst am Ende seiner Öffnungssequenz setzt, sodass beide Callbacks die Prüfung passieren; der unterlegene Aufruf kann das belegte Gerät nicht übernehmen und meldet einen **irreführenden** `ERROR "unsupported preview size"`, während der siegreiche Stream normal rendert [M]
- **MUSS [MUST]** dieses Symptom richtig lesen: `unsupported preview size` bei sichtbar rendernden Bildern bedeutet doppeltes Öffnen, keinen nicht unterstützten Modus — die angeforderte Auflösung daraufhin zu ändern ist die falsche Reparatur [M]
- **MUSS [MUST]** erst öffnen, wenn beide Vorbedingungen erfüllt sind — ein freigegebenes Gerät **und** eine lebende Vorschaufläche — und beim jeweils zweiten Eintreffen erneut auswerten, da ihre Reihenfolge nicht garantiert ist
- **SOLLTE [SHOULD]** `RenderMode.NORMAL` wählen, wenn die App Rohbilder braucht: Dieser Modus rendert in die `TextureView` und hält den NV21-Frame-Callback aktiv, während der OpenGL-Pfad Bilder nur mit gesetztem `isRawPreviewData`/`isCaptureRawImage` liefert [M]
- **MUSS [MUST]** den Stream abbauen, wenn der Screen die Komposition verlässt, und bei Rückkehr neu registrieren, und **DARF NICHT [MUST NOT]** ein vorübergehendes Schließen während einer absichtlichen Umkonfiguration als Geräteverlust behandeln
- **MUSS [MUST]** Engine-Callbacks nach jedem Wiederöffnen neu anhängen und sich dabei an die Kamerainstanz binden, die der Zustands-Callback übergibt, statt an ein veränderliches Feld — ein gleichzeitiges Abziehen kann das Feld leeren und die Hardwaretaste für den Rest der Sitzung stumm zurücklassen [M]

### E. Standbildaufnahme

- **SOLLTE NICHT [SHOULD NOT]** AUSBCs eigenes `captureImage()` für eine Upload-Pipeline verwenden: Es verlangt `WRITE_EXTERNAL_STORAGE` und schreibt nach DCIM, was der Berechtigungssparsamkeit (`spec/android/security/` §E) widerspricht und eine Datei zwischen Kamera und Verbraucher schiebt [M]
- **MUSS [MUST]** stattdessen ein einzelnes Bild über einen einmaligen Preview-Daten-Callback abgreifen und im Prozess mit `YuvImage.compressToJpeg` kodieren [R10], was zugleich das Zuschnittrechteck entgegennimmt, das ein digitaler Zoom braucht
- **MUSS [MUST]** jede Zuschnittkante auf einen geraden Pixel runden: NV21 tastet Chroma 2×2 unter, eine ungerade Grenze verschiebt die Farbebenen gegen die Helligkeitsebene
- **MUSS [MUST]** das Warten auf ein Bild mit einem Zeitlimit begrenzen und einen typisierten Fehlschlag melden — bei 4,7 fps ist ein naives Warten von einem Hänger nicht zu unterscheiden
- **SOLLTE [SHOULD]** sich darauf stützen, dass die Engine Bilder verwirft, deren Größe nicht zur aktiven Anforderung passt, wodurch veraltete Bilder nach einem Moduswechsel von selbst ausscheiden statt zur Fehlerquelle zu werden [M]
- **MUSS [MUST]** die aufgenommenen Abmessungen und die Bytegröße an den Aufrufer oder ins Log zurückmelden; ohne sie bleibt eine stillschweigend herabgestufte Aufnahme unsichtbar [M]

### F. Physische Bedienelemente am Mikroskopkörper

- **DARF NICHT [MUST NOT]** erwarten, dass die Tasten am Körper als Android-Key-Events ankommen: Das Referenzgerät registriert überhaupt kein HID-Eingabegerät, es erreicht also nichts `onKeyDown` [M]
- **MUSS [MUST]** den Auslöser stattdessen über den **UVC-Status-Endpoint** lesen, per Button-Callback der Engine — auf dem Referenzgerät gemessen als `button=1, state=1` beim Drücken und `state=0` beim Loslassen, passend zum Standard-Standbildknopf von UVC [M][R11]
- **DARF NICHT [MUST NOT]** dafür unter der Ebenenentscheidung aus §B Reflexion brauchen: `setButtonCallback` und `setStatusCallback` sind auf `UVCCamera` öffentlich [M]. Nur ein Projekt, das an AUSBCs `CameraUVC` gebunden ist — welches sie hinter einem privaten Feld verbirgt —, **KANN [MAY]** sie reflektiv erreichen und **MUSS [MUST]** die Reflexion dann auf das Modul beschränken, dem die Engine gehört, sie gegen eine Null-Instanz absichern und eine passende `-keepclassmembers`-Regel ergänzen, da R8 das Feld in Release-Builds sonst umbenennt
- **DARF NICHT [MUST NOT]** annehmen, die übrigen Tasten seien mit USB verdrahtet. Die Zoomwippe des Referenzgeräts sendet über USB nichts — weder Button- noch Control-Change-Ereignis über ein 30-minütiges Messfenster —, und das Gerät meldet zusätzlich keine Unterstützung für die UVC-Zoomsteuerung; diese Tasten bedienen nur seine eigenständige WLAN-Firmware [M]
- **MUSS [MUST]** je Gerät verifizieren statt Tastennummern spekulativ zu belegen, und **SOLLTE [SHOULD]** jedes nicht zugeordnete Button- und Status-Ereignis roh protokollieren, damit ein unbekannter Körper in einer einzigen Hardwaresitzung belegbasiert abgebildet werden kann
- **SOLLTE [SHOULD]** dort, wo der Hardwarepfad fehlt, Zoom auf dem Bildschirm als Ersatz anbieten, umgesetzt als mittiger Zuschnitt auf Vorschau-Transformation und aufgenommenes Bild gleichermaßen, damit das Foto dem gezeigten Ausschnitt entspricht; ein Skill **MUSS [MUST]** solchen Zoom als digital ausweisen und **DARF NICHT [MUST NOT]** ihn als Vergrößerung darstellen

### G. Auflösungsstrategie

- **SOLLTE [SHOULD]** die Vorschau in einem Modus halten, der zum Ausrichten schnell genug ist, und die Auflösung nur für das Standbild anheben — bei 4,7 fps ist eine 4K-Vorschau zum Ausrichten eines Mikroskops unbrauchbar, während die Bildrate für eine Einzelaufnahme bedeutungslos ist [R7]
- **MUSS [MUST]** einkalkulieren, was ein Moduswechsel kostet, und ihn **MUSS [MUST]** messen statt annehmen: AUSBCs `updateResolution` ist ein vollständiges Schließen und Wiederöffnen mit fest kodierter Sekundenpause, wodurch Hin- und Rückschalten die Vorschau rund vier bis fünf Sekunden einfriert [M]. `UVCCamera` direkt zu steuern (§B) erlaubt die günstigere Folge `stopPreview` → `setPreviewSize` → `startPreview`, ohne das Gerät freizugeben; in beiden Fällen **MUSS [MUST]** ein Skill die Wartezeit in der UI sichtbar machen und Aufnahmen serialisieren, damit zwei sich nicht überlappen
- **MUSS [MUST]** degradieren statt zu scheitern: Greift der Wechsel nicht innerhalb eines begrenzten Zeitlimits, wird in der laufenden Auflösung aufgenommen statt einen Fehler zurückzugeben, und der Vorschaumodus wird auch nach einer abgebrochenen Aufnahme wiederhergestellt
- **SOLLTE [SHOULD]** den größten unterstützten Modus beim Gerät erfragen statt einen fest zu kodieren, damit derselbe Code sich über Gerätekörper hinweg anpasst; auf dem Referenzgerät ergibt das 3840×2160 mit rund 673 kB JPEG gegenüber 130 kB bei 1080p [M]
- **MUSS [MUST]** vor dem Bezahlen der Latenz verifizieren, dass der Spitzenmodus eines Geräts echte Details trägt, und das **MUSS [MUST]** messend statt nach Augenschein geschehen: ein fein strukturiertes Motiv aufnehmen, dann (a) die Aufnahme halbieren, wieder hochskalieren und das Residuum gegen das Original bilden sowie (b) das radial gemittelte Leistungsspektrum oberhalb der halben Nyquist-Frequenz gegen das mittlere Band vergleichen. Firmware-Hochrechnung lässt beides zusammenbrechen — kleines Residuum und steiler Abfall mit Knick bei exakt der halben Nyquist-Frequenz. Die Schwellen werden kalibriert, indem dieselben zwei Tests auf die absichtlich herunter- und wieder hochgerechnete Aufnahme laufen; diese Kontrolle trennt Hochrechnung von JPEG-Rauschen [M]
- **SOLLTE [SHOULD]** „günstiges Mikroskop, also interpoliert" als zu prüfende Hypothese behandeln statt als Tatsache: Das Referenzgerät besteht den Test. Am 11.08.2026 gemessen verliert seine 4K-Aufnahme beim Halbieren und Wiederherstellen 17,5 % des Bildkontrasts gegenüber 3,5 % bei einer absichtlich hochgerechneten Kontrolle, und das Leistungsspektrum fällt ins hohe Band nur um 1,25 Dekaden ohne Knick bei der halben Nyquist-Frequenz gegenüber 3,07 Dekaden bei der Kontrolle — sein Spitzenmodus löst also Detail auf, das 1080p nicht kann, und Standbilder auf den größten Modus zu legen ist hier gerechtfertigt [M]
- **SOLLTE [SHOULD]** wissen, dass AUSBC mit einem fest kodierten Minimum von 10 fps aushandelt, was bei Geräten mit übertriebenen Deskriptorangaben gelingt, einen ehrlich niedrigratigen Modus aber abweisen kann [M]

### H. Architektur und Isolation

- **MUSS [MUST]** die Engine hinter eine app-eigene Schnittstelle stellen und jeden Engine-Typ, einschließlich des reflektiven Zugriffs aus §F, auf ein einziges Modul beschränken — die Engine ist ein austauschbares Implementierungsdetail, und ihre API ist weder stabil noch gut dokumentiert
- **SOLLTE [SHOULD]** den Kamerazustand als versiegelten Typ mit den unterscheidbaren Fehlerfällen aus §C ausdrücken statt über nullbare Felder und Wahrheitswerte
- **MUSS [MUST]** Geometrie- und Kodierlogik (Zuschnittrundung, JPEG-Kodierung) frei von Engine- und Android-View-Typen halten, damit sie ohne Gerät unit-testbar ist — die hardwaregebundenen Teile sind es nicht, was die testbaren Teile umso wertvoller macht
- **SOLLTE [SHOULD]** jede nicht offensichtliche Umgehung aus §B–§G als Kommentar festhalten, der die Randbedingung an der Stelle nennt, an der sie auferlegt wird; wer später eine Absicherung entfernt, weil sie „überflüssig aussieht", holt einen Defekt zurück, dessen Wiederentdeckung eine Hardwaresitzung kostet

### I. Entwicklungs- und Test-Workflow

- **MUSS [MUST]** den Portkonflikt als wichtigste Randbedingung des Workflows einplanen: Das Mikroskop belegt den einzigen USB-C-Port des Telefons, ADB **MUSS [MUST]** deshalb während der gesamten Entwicklungsschleife über das Netzwerk laufen [M] — zuerst per Kabel installieren und Netzwerk-ADB aktivieren, dann abziehen und die Peripherie anschließen
- **MUSS [MUST]** für diesen Transport `spec/android/adb-workflows/` §A folgen: Pairing ab Android 11 ist der Standard, das alte `tcpip 5555` ist ein gekennzeichneter Rückfallweg, der danach mit `adb usb` geschlossen wird
- **MUSS [MUST]** das Gerät während einer Sitzung wach halten: Auf einem dösenden oder gesperrten Telefon stoppt die Vorschau und Netzwerk-ADB wird unerreichbar, was sich exakt wie ein Peripheriefehler liest [M]
- **SOLLTE [SHOULD]** `adb shell dumpsys usb` und dessen Feld `host_connected` als Wahrheitsquelle dafür nutzen, ob die Peripherie überhaupt angeschlossen ist, bevor irgendein App-Symptom gedeutet wird [M]
- **SOLLTE [SHOULD]** den nativen Tag der Engine neben dem eigenen beobachten: Frame-Allokationszeilen des Tags `libUVCCamera` belegen einen lebenden Stream selbst bei schwarz bleibender Fläche und trennen so einen Stream- von einem Renderfehler [M]
- **MUSS [MUST]** OEM-Installationssperren einplanen, wenn das Testgerät kein Stock-Build ist — MIUIs `INSTALL_FAILED_USER_RESTRICTED` blockiert `adb install` und `pm install` in der Shell gleichermaßen, sodass nur die Installation am Gerät aus einer gepushten Datei bleibt [M]; die Entschlüsselungstabelle steht in `spec/android/adb-workflows/` §B
- **DARF NICHT [MUST NOT]** Emulator-Abdeckung für diese Fähigkeit einplanen: Emulatoren bieten keinen USB-Host, es ist also ein physisches OTG-fähiges Gerät erforderlich, und diese Pfade können CI nicht absichern (`spec/android/test-automation/`). Ein Skill **MUSS [MUST]** diese Einschränkung benennen, statt einen grünen CI-Lauf suggerieren zu lassen, die Fähigkeit sei getestet
- **SOLLTE [SHOULD]** Belege mit `screencap` und der Logzeile über die aufgenommenen Abmessungen sichern, damit eine Hardwaresitzung ein prüfbares Artefakt statt eines mündlichen Berichts hinterlässt [M]

## Verifizierte Geräte

Jede Zeile ist eine Hardwaresitzung. Ein Gerät wird erst gelistet, wenn die genannten Spalten direkt beobachtet wurden; eine ungemessene Spalte ist `unbekannt` und wird nie aus einem Datenblatt abgeleitet.

| USB-ID | Deskriptor | Modi | Gemessene Rate | Körpertasten über USB | UVC-Zoomsteuerung | Verifiziert |
| --- | --- | --- | --- | --- | --- | --- |
| `1b3f:2002` | `GENERAL - UVC`, UVC 1.00, buspowered, MJPEG | 3840×2160 (gemessen echt, nicht hochgerechnet) / 2048×1024 / 1920×1080 / 1280×720 | ~4,7 fps bei 4K, ~17 fps bei 1080p (Deskriptor nennt 30) | Nur Auslöser, als UVC-Button-Index 1; Zoomwippe sendet nichts | Nicht unterstützt (`CTRL_ZOOM_ABS` fehlt) | 11.08.2026, Pixel 7a / Android 16 |

## Abnahmekriterien

Die folgenden Kriterien sind eine bewusst repräsentative Zusammenfassung von §A–§I, keine 1:1-Abbildung; jeder Anforderungspunkt oben ist für sich normativ.

- [ ] Kein Skill schlägt für eine externe UVC-Kamera einen WebView-, WebUSB- oder Cross-Platform-Wrapper-Weg vor, und keiner macht eine erforderliche Fähigkeit ohne Geräteverifikation von Camera2s `LENS_FACING_EXTERNAL` abhängig
- [ ] Die Integration sitzt auf der `libuvc`-Ebene, und die USB-Berechtigung wird über den Plattform-`UsbManager` erworben; `USBMonitor.register()` wird nie aufgerufen
- [ ] Jedes transitive Artefakt der gepinnten Version löst auf, geprüft am AAR und nicht nur an der POM; ein mitgeliefertes Repository existiert nur dort, wo eine Wrapper-Abhängigkeit es erzwungen hat — vor dem entfernten, mit Inhaltsfilter und Herkunftsnachweis je Artefakt
- [ ] Das Manifest deklariert USB-Host als `required="false"`, die App hält `CAMERA` vor dem Öffnen, und die USB-Freigabe ist als eigene Zustimmung modelliert
- [ ] Die USB-Berechtigungsanfrage ist `targetSdk`-aktuell: ein expliziter, weiterhin veränderlicher `PendingIntent` und ein Receiver mit Export-Flag — verifiziert dadurch, dass die App eine lebende Vorschau erreicht statt bei der Registrierung abzustürzen
- [ ] Die App unterscheidet in ihrer UI die Zustände kein Gerät, Freigabe ausstehend, Freigabe verweigert, kein Host-Support und Engine-Fehler
- [ ] Der Öffnungspfad ist gegen gleichzeitiges Öffnen abgesichert, und die Codebasis enthält keine Auflösungsänderung als Reaktion auf ein unechtes „unsupported preview size"
- [ ] Die Aufnahme liefert ein JPEG im Speicher ohne Speicherberechtigung, mit geraden Zuschnittkanten, begrenztem Warten und gemeldeten Abmessungen
- [ ] Engine-Callbacks werden nach jedem Wiederöffnen über die vom Zustands-Callback gelieferte Instanz neu angehängt
- [ ] Die Codebasis erreicht Button- und Status-Callbacks direkt; verbliebener reflektiver Engine-Zugriff ist durch eine Wrapper-Abhängigkeit begründet, auf das besitzende Modul beschränkt, gegen Null abgesichert und von einer ProGuard-Keep-Regel gedeckt
- [ ] Die Tastenzuordnung ist belegbasiert: Nur gemessene Indizes werden abgebildet, nicht zugeordnete Ereignisse roh protokolliert, und keine UI bietet ein Hardware-Bedienelement an, das das Gerät nicht meldet
- [ ] Zoom wird als digital ausgewiesen, wo er ein Zuschnitt ist, und wirkt auf Vorschau und Aufnahme identisch
- [ ] Ein Auflösungswechsel für Standbilder ist serialisiert, in der UI sichtbar, zeitlich begrenzt, degradiert bei Fehlschlag auf den laufenden Modus und stellt den Vorschaumodus stets wieder her
- [ ] Die Testanleitung des Skills richtet Netzwerk-ADB ein, bevor die Peripherie angeschlossen wird, benennt die Wachzustandsanforderung und stellt fest, dass Emulatoren diese Fähigkeit nicht abdecken können

## Offene Fragen

- Die Ebenenentscheidung aus §B ist belegt entschieden — das veröffentlichte `libuvc:3.2.7` trägt die nötige API, und `openDevice`/`hasPermission`/`UsbControlBlock` hängen nachweislich nicht von `register()` ab —, sie ist jedoch durch Quell- und Binärinspektion belegt, noch nicht durch einen laufenden Stream. Offen bleibt der Laufzeitnachweis auf dem Referenzgerät; bis dahin bleibt der in §C–§G dokumentierte Wrapper-Weg der bekannt funktionierende Rückfall.

## Referenzen

Quellen abgerufen am 11.08.2026. Klassenmarker: (P) primäre/autoritative Hersteller- oder Standarddokumentation, (S) sekundär (gepflegte Tool-Repositories), (M) gemessen — eigene Beobachtung aus der in §Kontext beschriebenen hardwareverifizierten Integration, im Text als [M] zitiert.

- [R1] AndroidUSBCamera (AUSBC) — die in diesem Portfolio genutzte `libuvc`-basierte Engine (S): <https://github.com/jiangdongguo/AndroidUSBCamera>
- [R2] JitPack-Build-Log für AUSBC 3.3.3, zeigt den `:libuvc:ndkClean`-Fehlschlag hinter der unvollständigen Veröffentlichung (S): <https://jitpack.io/com/github/jiangdongguo/AndroidUSBCamera/3.3.3/build.log>
- [R3] USB-Host-Überblick — Manifest-Deklaration des Host-Modus, Gerätefilter und der Berechtigungsdialog je Gerät (P): <https://developer.android.com/develop/connectivity/usb/host>
- [R4] libuvc — die plattformübergreifende UVC-Implementierung, die die Android-Engines kapseln (S): <https://github.com/libuvc/libuvc>
- [R5] Referenz zu `CameraMetadata.LENS_FACING_EXTERNAL` (P): <https://developer.android.com/reference/android/hardware/camera2/CameraMetadata#LENS_FACING_EXTERNAL>
- [R6] WebUSB-API-Spezifikation — unterstützte Transfertypen, isochron ausgenommen (P): <https://wicg.github.io/webusb/>
- [R7] Ursprüngliche Geräteanalyse — Deskriptoren, Moduliste, gemessene Bildraten und die ausgeschlossenen Zugriffswege des Referenzmikroskops (S): <https://github.com/nolte/kamerplanter-android/issues/1>
- [R8] react-native-vision-camera, Issue 1407 — externe USB-Kameras undefined (S): <https://github.com/mrousavy/react-native-vision-camera/issues/1407>
- [R9] react-native-vision-camera, Issue 2131 — externe USB-Kameras undefined (S): <https://github.com/mrousavy/react-native-vision-camera/issues/2131>
- [R10] Referenz zu `YuvImage` — NV21 nach JPEG mit Zuschnittrechteck (P): <https://developer.android.com/reference/android/graphics/YuvImage>
- [R11] USB Device Class Definition for Video Devices — Status-Endpoint und Semantik des Standbildknopfs (P): <https://www.usb.org/document-library/video-class-v15-document-set>
- [R12] Android-14-Verhaltensänderungen — veränderlicher `PendingIntent` mit implizitem Intent wird ab `targetSdk >= 34` abgewiesen (P): <https://developer.android.com/about/versions/14/behavior-changes-14#security>
- [R13] Android-14-Verhaltensänderungen — zur Laufzeit registrierte Receiver müssen ihren Exportzustand deklarieren (P): <https://developer.android.com/about/versions/14/behavior-changes-14#runtime-receivers-exported>
