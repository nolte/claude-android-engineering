# App-Sicherheit

Status: draft

## Kontext

Sicherheit ist ein Satz von Anforderungen, die über Speicherung, Kryptografie, Netzwerk, IPC, WebViews, Permissions und den Build hinweg gelten müssen — kein Feature, das vor dem Release angeschraubt wird. Diese Spec definiert die sicherheitsrelevanten Themengebiete, die eine mit den Skills dieses Repositories gebaute App beachten muss, ehrlich kalibriert für den typischen Nicht-Fintech-Consumer-App-Fall: die wirklich tragende Baseline, die situative Defense-in-Depth und die Resilience-Schicht (Root-Detection, Obfuskierung-als-Sicherheit), die laut Evidenz optional und oft kontraproduktiv ist.

Der Inhalt ist aus einem Recherche-Durchlauf (August 2026) destilliert: die offizielle Android-Security-Guidance (developer.android.com/privacy-and-security — Security Tips, Best Practices, der MASVS-gegliederte Risiko-Katalog, Keystore, Network Security Config) und das OWASP-Mobile-Application-Security-Framework (MASVS-v2.x-Kontrollgruppen, die MAS-Testing-Profile L1/L2/R, die Mobile Top 10 2024, MASTG-Testerwartungen), ergänzt — für §G — um die OAuth-BCPs für native Apps (RFC 8252) und OAuth-Sicherheit (RFC 9700). Wo offizielle Guidance und Community-Konsens auseinandergehen — Certificate Pinning, Root-Detection, Obfuskierung, die deprecatete Jetpack-Security-Library — hält die Spec die ehrliche Position fest, statt zu cargo-culten.

Grenzen: Log-Hygiene-Mechanik (keine PII, R8-Stripping) teilt sich mit `spec/android/adb-workflows/` §C; Dependency-Update-Automatisierung als Security-Praxis überlappt `spec/android/project-structure/`; `debuggable=false` in Release-Builds steht in dieser Spec und in adb-workflows. Session-Handling auf der Leitung — Token-Lebensdauer, Refresh, Logout, Re-Authentifizierung, OAuth-Flows — gehört §G hier; die *Outcome-Zuordnung* eines abgelaufenen Credentials (Fall 4, unauthenticated) und die Single-Flight-Refresh-Mechanik gehören `spec/android/backend-contract/` §B/§C, das Löschen nutzerbezogener Caches beim Sign-out `spec/android/app-architecture/` §C.

Leser: Autoren der Android-Skills dieses Repos sowie Reviewer, die beurteilen, ob eine generierte oder auditierte App die Security-Baseline erfüllt.

## Ziele

- Die MAS-L1-Baseline als bedingungslose Sicherheits-Untergrenze jeder generierten App fixieren: sichere Speicherung, korrekte Krypto, TLS überall, sicheres IPC/WebView, minimale Permissions, sauberer Build
- Die konkreten realen Schwachstellenklassen (Intent Redirection, unsichere Deep Links, Exported-Component-Lecks, WebView-JS-Bridges, Path Traversal) per Anforderung verbieten
- Ehrlich kalibrieren: benennen, was L2 (situativ), was R (optional) ist und wo offizielle Guidance unzureichend oder überkonstruiert ist — damit eine Solo-Entwickler-App weder exponiert noch überfordert ist
- Secrets-Handhabung wahrheitsgemäß machen: kein client-eingebettetes Secret ist geheim; die Backend-Proxy-Grenze und die API-Key-Restriktion sind die realen Kontrollen

## Nicht-Ziele

- Eine MASTG-Penetration-Testing-Prozedur zu sein — diese Spec nennt die defensiven Anforderungen einer gebauten App, nicht, wie man sie angreift
- Backend-/Server-Sicherheit — nur der Client-Beitrag zur Ende-zu-Ende-Sicherheit (korrektes TLS, keine client-vertraute Autorisierung)
- Regulatorische/datenschutzrechtliche Compliance (DSGVO-DPIA) — die Privacy-Anforderungen hier sind die sicherheitsnahe Baseline, kein Rechtsgutachten
- Play-Store-Release-Signing-Key-Management — Release-Scope; hier nur lokale `debuggable`-/Build-Hygiene
- Resilience-Tier-Härtung (RASP, Anti-Tamper) als Anforderung — benannt und als optional eingeordnet gemäß der Evidenz

## Anforderungen

### A. Datenspeicherung (MASVS-STORAGE)

- **MUSS [MUST]** alle privaten Daten im Internal Storage speichern (`MODE_PRIVATE`); **DARF NICHT [MUST NOT]** sensible Daten in External Storage, world-readable/writable-Modi oder App-übergreifende SharedPreferences legen und **DARF NICHT [MUST NOT]** sensible Daten loggen (geteilt mit `spec/android/adb-workflows/` §C: R8 strippt Debug-Logs nur mit aktivierter Minification und vorhandener Regel)
- **MUSS [MUST]** gespeicherte Secrets mit Android-Keystore-gestützten Schlüsseln verschlüsseln (oder einem robusten Tool wie Tink über Keystore) — den Mechanismus anpeilen, nicht `EncryptedSharedPreferences`/Jetpack Security: `security-crypto` 1.1.0-beta01 (04.06.2025) hat sämtliche APIs „in favour of existing platform APIs and direct use of Android Keystore" deprecated, und das finale 1.1.0 (30.07.2025) ist mit dieser Deprecation erschienen — es gibt keinen Drop-in-Nachfolger [R10]
- **MUSS [MUST]** Secrets und gerätespezifische Identifier via `dataExtractionRules` (gelesen ab Android 12, API 31) **und**, sobald `minSdk` < 31, über das parallele `fullBackupContent`-Regelset für Android 11 und niedriger aus Backups ausschließen — die Plattform liest nur das zur Geräteversion passende Attribut, ein einzelnes Set lässt den anderen Bereich ungeschützt [R9]; `android:allowBackup` explizit gesetzt, `getNoBackupFilesDir()` für nie gesicherte Daten
- **SOLLTE [SHOULD]** Tastatur-Vorschläge/Clipboard-Exposition auf sensiblen Feldern deaktivieren und jeden sensiblen Text, den die App selbst kopiert, mit `ClipDescription.EXTRA_IS_SENSITIVE` markieren, damit die Clipboard-Vorschau ab API 33 ihn schwärzt [R26]. Das *Laufzeit*-Auth-Token liegt Keystore-verschlüsselt im Internal Storage gemäß dem Punkt oben (§G fixiert die Token-Regeln); Block Store ist ein Device-to-Device-Restore-Mechanismus — Play-Services-gestützt, höchstens 16 Einträge à 4 KB, gedacht zur Re-Authentifizierung auf einem neuen Gerät — und der offizielle Kanal, um ein Token, das Auto Backup ausschließen muss, auf ein anderes Gerät mitzunehmen, nicht der Arbeitsspeicher des Tokens [R9][R27]
- **KANN [MAY]** `android:hasFragileUserData="true"` setzen, damit die Deinstallation anbietet, App-Daten zu behalten; so behaltene Daten überleben die Installation und bleiben daher unter denselben Verschlüsselungs- und Klassifikationsentscheidungen (§H) wie Live-Daten [R28]

### B. Kryptografie (MASVS-CRYPTO)

- **DARF NICHT [MUST NOT]** eigene Kryptografie implementieren, hartkodierte Schlüssel einbetten oder kaputte Primitive nutzen (MD5/SHA-1 für Security, DES/RC4, ECB, `SHA1PRNG`)
- **MUSS [MUST]** aktuelle Primitive nutzen: AES-256-GCM (oder AES-CBC + HMAC-SHA-256), SHA-256-Familie, `SecureRandom`; Schlüssel im Android Keystore erzeugt und gehalten (nie einen Provider außer `AndroidKeyStore` angeben)
- **SOLLTE [SHOULD]** Schlüssel für sensible Daten an Nutzer-Authentifizierung binden (`setUserAuthenticationRequired`, `setInvalidatedByBiometricEnrollment`); **KANN [MAY]** StrongBox nutzen, wo das Risiko es rechtfertigt (für die meisten Apps nicht nötig)

### C. Netzwerk (MASVS-NETWORK)

- **MUSS [MUST]** TLS für allen Verkehr nutzen (Cleartext ist seit Android 9 für Apps mit targetSdk ≥ 28 default deaktiviert [R29] und bleibt aus — kein `usesCleartextTraffic`); **DARF NICHT [MUST NOT]** TLS mit einem permissiven `TrustManager`, einem No-op-`HostnameVerifier` oder Debug-Trust-Anchors im Release schwächen
- **KANN [MAY]** Zertifikate pinnen — aber nur via Network Security Config, nur für eigene Endpoints des Entwicklers, immer mit Backup-Pin, nie mit Custom-`TrustManager`; offizielle Guidance rät für die meisten Apps aktiv vom Pinning ab (Bricking-Risiko bei CA-Rotation), daher ist korrekte TLS-Validierung das MUSS und Pinning das situative KANN
- **SOLLTE [SHOULD]** Certificate Transparency (Opt-in ab Android 16, Default ab Android 17) als wartungsärmere Alternative zum Pinning einplanen

### D. Plattform und IPC (MASVS-PLATFORM)

- **MUSS [MUST]** `android:exported` an jeder Komponente explizit deklarieren und `false` setzen, sofern kein externer Zugriff beabsichtigt ist; jede exportierte Komponente permission-schützen und input-validieren (ab targetSdk 31 scheitert eine Komponente mit Intent-Filter und ohne explizites `exported` im Build und lässt sich auf Android 12+ nicht installieren [R8]; dieses MUSS ist bewusst breiter — jede Komponente, mit oder ohne Filter)
- **MUSS [MUST]** jeden `PendingIntent` immutable machen (`FLAG_IMMUTABLE`), sofern Mutation nicht wirklich nötig ist, und explizite Intents (Action + Component + Package) für interne Zustellung nutzen — implizite Intents tragen nie sensible Daten
- **MUSS [MUST]** die konkreten Schwachstellenklassen per Anforderung verbieten: Intent Redirection (nie einen angreifer-kontrollierten Intent aus Extras ohne Resolve-Check weiterreichen), unsichere Deep Links (URI-Scheme *und* Host per exaktem Match validieren; verifizierte App Links mit `autoVerify` bevorzugen), Content-Provider-Path-Traversal (`openFile`-Pfade kanonisieren) und Zip-Path-Traversal (`getCanonicalPath`-Prüfung auf jedem entpackten Eintrag)
- **MUSS [MUST]** WebViews härten: JavaScript aus, sofern nicht nötig; `addJavascriptInterface` nur für voll vertrauenswürdigen First-Party-Content (annotiert `@JavascriptInterface` — Pflicht ab targetSdk 17, ab dem nur annotierte öffentliche Methoden aus JavaScript erreichbar sind [R30]; das Reflection-Risiko älterer Plattformen ist eine *Laufzeit*-Frage, im Risiko-Katalog als API < 21 angegeben [R3], und bei jeder aktuellen minSdk gegenstandslos); File-/Content-Access-Settings explizit deaktiviert; Navigation auf eine Allowlist beschränkt, fremde URLs an den Browser übergeben; Safe Browsing aktiviert lassen
- **SOLLTE [SHOULD]** `filterTouchesWhenObscured` / `setHideOverlayWindows` für sensible Controls und `FLAG_SECURE` für sensible Screens anwenden — es hält sie auch aus Screenshots und dem Recents-Thumbnail heraus; `setRecentsScreenshotEnabled(false)` (API 33) deckt Recents allein ab [R31] — mit dem dokumentierten Caveat, dass FLAG_SECURE allein Overlay-Angriffe nicht stoppt; welche Screens als sensibel gelten, folgt der Datenklassifikation in §H

### E. Permissions und Privacy (MASVS-PRIVACY)

- **MUSS [MUST]** nur die minimalen Permissions anfragen, im Kontext, mit Begründung, und Ablehnung graceful behandeln (UX-Regeln gemäß `spec/android/app-design-navigation/` §F); **DARF NICHT [MUST NOT]** eine Permission anfragen, wo ein Intent an eine andere App genügt, und **DARF NICHT [MUST NOT]** persistente Hardware-Identifier (IMEI, Telefonnummer) als IDs nutzen. *Wie* dieses Minimum ermittelt, deklariert, angefordert, verifiziert und festgehalten wird — Ermittlungsmethodik, berechtigungsfreie Alternativen, Manifest-Regeln, Laufzeitablauf und Berechtigungsregister — liegt in `spec/android/permissions/`; dieser Punkt formuliert die Pflicht, jene Spec die Methode
- **MUSS [MUST]** die Play-Data-Safety-Deklaration wahrheitsgemäß zum tatsächlichen Verhalten halten, inklusive Third-Party-SDK-Datenflüssen
- **SOLLTE [SHOULD]** Third-Party-SDK-Datenerfassung an Nutzer-Consent gaten und die Permissions jedes SDK auditieren; **MUSS [MUST]** für jede AccessibilityService-Nutzung die Play-Policy erfüllen (Deklaration + Approval, `isAccessibilityTool` nur für echte Tools) — autonomes Handeln über die Accessibility-API ist verboten

### F. Code, Build und Supply Chain (MASVS-CODE)

- **MUSS [MUST]** Release-Builds mit `android:debuggable=false` ausliefern (Lint `HardcodedDebugMode` ist fatal), targetSdk aktuell halten und **DARF NICHT [MUST NOT]** Code dynamisch aus unvertrauenswürdigen Quellen laden, unvertrauenswürdige Daten unsicher deserialisieren oder SQL per String-Konkatenation bauen (nur parametrisierte Queries)
- **DARF NICHT [MUST NOT]** Secrets ins Repository committen; **MUSS [MUST]** das `secrets-gradle-plugin` nur als VCS-Hygiene behandeln, nicht als Schutz — ein Schlüssel im APK ist extrahierbar, also werden Client-Secrets restringiert (Google-API-Keys per Package + SHA-256) und echte Secrets leben hinter einem Backend-Proxy
- **MUSS [MUST]** allen unvertrauenswürdigen Input validieren (UI, IPC, Netzwerk, Dateisystem) und Key Attestation server-seitig validieren, falls Attestation genutzt wird
- **SOLLTE [SHOULD]** automatisierte Dependency-Updates (Renovate/Dependabot) und einen Vulnerability-Scan (osv-scanner — die Präferenz dieses Portfolios gegenüber OWASP dependency-check für Gradle-Projekte, eine festgehaltene Entscheidung, kein Vendor-Urteil [R22]) in CI fahren; **SOLLTE [SHOULD]** die Android-Lint-Security-Checks (`TrustAllX509TrustManager`, `ExportedContentProvider`, `HardcodedDebugMode`, `MissingPermission`, …) als Fehler erzwingen — `MissingPermission` wird von diesem SOLLTE durch `spec/android/permissions/` §H auf MUSS angehoben — und `mobsfscan` in CI fahren (bester Effort/Value für einen Solo-Dev); **SOLLTE [SHOULD]** Gradle Dependency Verification (Checksums) gemäß `spec/android/project-structure/` §B aktivieren, das die Mechanik besitzt — real, aber wartungsintensiv, daher SOLLTE, nicht MUSS

### G. Authentifizierung, Session-Handling und Resilience (kalibriert)

- **MUSS [MUST]** das Backend als Authentifizierungs- und Autorisierungsautorität behandeln (MASVS-AUTH-1 [R18]): Der Client präsentiert Credentials und Token und folgt den Best Practices des Protokolls; er gewährt sich nie selbst Zugriff aus einem lokal gecachten „angemeldet"-Flag, und ein abgelaufenes oder abgelehntes Credential ist `spec/android/backend-contract/` §B Fall 4 (unauthenticated), nie ein generischer Fehler
- **MUSS [MUST]** das Access-Token nur im flüchtigen Speicher halten und das Refresh-Token — ein Langzeit-Credential — Keystore-verschlüsselt im Internal Storage gemäß §A ablegen, nie in SharedPreferences, External Storage, Logs oder einer backup-eingeschlossenen Datei [R32]; **MUSS [MUST]** Token-Lebensdauer und Rotation akzeptieren, die das Backend vorgibt (kurzlebige Access-Token, Refresh single-flight gemäß `spec/android/backend-contract/` §C), und **DARF NICHT [MUST NOT]** eine Session lokal über das hinaus verlängern, was das Backend bestätigt hat
- **MUSS [MUST]** beim Logout in dieser Reihenfolge invalidieren: den Revocation- bzw. Logout-Endpoint des Backends aufrufen, dann beide Token und alle nutzerbezogenen gecachten Daten lokal löschen (`spec/android/app-architecture/` §C) — ein Logout, der nur die UI leert, lässt ein lebendes Credential zurück, der häufigste Logout-Defekt, den MASTG benennt [R32]
- **MUSS [MUST]** Session-Ablauf als gestalteten Flow behandeln: stiller Refresh, wo ein Refresh-Token existiert; sonst eine Re-Authentifizierungs-Aufforderung, die den Nutzer auf den Screen und die ungesendete Eingabe zurückbringt, auf der er war — nie ein Kaltstart und nie ein Stacktrace
- **MUSS [MUST]**, wo die App sich per OAuth 2.0/OIDC anmeldet, den Authorization-Code-Grant mit PKCE in einem *externen* User-Agent nutzen — Custom Tabs, etwa via AppAuth-Android — und **DARF NICHT [MUST NOT]** den Authorization-Request in einem eingebetteten WebView ausführen: RFC 8252 §8.12 legt fest, dass native Apps keine eingebetteten User-Agents nutzen dürfen (MUST NOT), weil die hostende App das vollständige Credential des Nutzers lesen kann, und Identity Provider lehnen solche Requests ab [R33][R34][R35]. Refresh-Token-Rotation oder Sender-Constraining ist eine Backend-Eigenschaft (RFC 9700 §4.14.2), die der Client tolerieren muss: Ein rotiertes Refresh-Token wird sofort persistiert, und ein abgelehntes Refresh-Token bedeutet Re-Authentifizierung, keine Retry-Schleife [R36]
- **MUSS [MUST]**, wo die App biometrisch authentifiziert, um lokale Daten zu schützen (MASVS-AUTH-2 [R18]; MASTG-TEST-0017/-0018 [R37]), `BiometricPrompt` mit einem `CryptoObject` (`BIOMETRIC_STRONG`) nutzen — ein reiner Erfolgs-Callback ist ein spoofbarer Client-Check und nur als UX-Convenience vor unkritischen Aktionen als **KANN [MAY]** akzeptabel
- **SOLLTE [SHOULD]** Step-up-Authentifizierung (biometrisch, PIN oder erneut eingegebenes Passwort) vor einer sensiblen In-App-Operation verlangen, wo die App solche hat (MASVS-AUTH-3 [R18]); eine Consumer-App ohne solche Operationen hält das in der MAS-Profil-Entscheidung unten als nicht anwendbar fest
- **DARF NICHT [MUST NOT]** R8/Obfuskierung als Sicherheitskontrolle behandeln — es ist eine Größenoptimierung mit einem geringen Reverse-Engineering-Bremseffekt als Nebenwirkung; **SOLLTE [SHOULD]** R8-Minification fürs Release aktivieren (Größe plus dieser Nebeneffekt), nie als Sicherheitsversprechen
- **KANN [MAY]** Resilience-Tier-Kontrollen (Root-/Tamper-Detection, Play-Integrity-Attestation) nur dann ergänzen, wenn ein konkretes Business-Asset sie rechtfertigt; laut OWASP „does not in itself constitute a vulnerability", sie sind bypassbar und tragen False-Positive- und Platform-Lock-in-Kosten — für eine normale Consumer-App sind sie optional und oft nicht lohnend
- Welche L2/R-Kontrollen übernommen werden oder nicht, wird protokolliert (welches MAS-Profil die App anpeilt und warum)

### H. Datenklassifikation und Threat Model — welche Daten welche Kontrolle auslösen

- **MUSS [MUST]** jeden Datentyp, den der Client speichert oder rendert, in eine von vier Klassen einordnen und die Klassifikation mit der MAS-Profil-Entscheidung (§G) protokollieren: **(1) Credentials und Token**; **(2) personenbezogene Daten** (Namen, Kontaktdaten, Account-Identifier, personenbezogene nutzergenerierte Inhalte); **(3) besondere Kategorien** (Gesundheit, präzise Standorthistorie, Finanz- oder Zahlungsdaten, biometrische Templates); **(4) einfacher App-Inhalt** (öffentliche Katalogdaten, UI-Präferenzen, Feature-Flags)
- **MUSS [MUST]** Kontrollen nach Klasse anwenden, damit keine Kontrolle ad hoc gewählt wird: Klasse 1 — Keystore-verschlüsselter Internal Storage, Backup-Ausschluss, nie geloggt, beim Logout gelöscht (§A/§G); Klasse 2 — die App-Sandbox (privater Internal Storage), Backup-Ausschluss für Identifier, gelöscht bei Sign-out und Account-Wechsel (`spec/android/app-architecture/` §C), von der Data-Safety-Deklaration abgedeckt (§E); Klasse 3 — alles, was Klasse 2 verlangt, plus `FLAG_SECURE` auf den Screens, die sie rendern (§D), Keystore-gestützte Verschlüsselung der Replica oder der sensiblen Spalten und eine protokollierte L2-Profil-Entscheidung; Klasse 4 — nur die L1-Baseline [R1][R18][R19]
- **Eine Room-Replica mit personenbezogenen Daten der Klasse 2 braucht auf L1 kein SQLCipher und keine Volldatenbank-Verschlüsselung**: Die App-Sandbox — privater Internal Storage unter einer App-eigenen UID auf einem Gerät mit File-based Encryption — ist die Kontrolle, die MASVS-STORAGE-1 verlangt, und das L1-Profil sieht sie als ausreichend an [R1][R18][R19]. Datenbankverschlüsselung ist eine Klasse-3- bzw. L2-Maßnahme, gegen eine benannte Bedrohung übernommen (gerootetes Gerät, Backup-Extraktion), nie als Reflex
- **MUSS [MUST]** das Threat Model benennen, gegen das die App verteidigt; der L1-Default ist: ein verlorenes oder gestohlenes *gesperrtes* Gerät, eine bösartige mitinstallierte App, ein Netzwerkangreifer und Backup-Extraktion. Ein gerootetes Gerät und der Gerätebesitzer selbst sind R-Tier-Bedrohungen und außerhalb des Scopes, sofern die Resilience-Entscheidung aus §G nichts anderes sagt
- **DARF NICHT [MUST NOT]** eine Kontrolle stillschweigend hochstufen: Die Wahl von SQLCipher, StrongBox, Root-Detection oder eines L2-Profils wird zusammen mit der Datenklasse und der Bedrohung protokolliert, die sie gerechtfertigt hat

## Akzeptanzkriterien

Die folgenden Kriterien sind ein bewusst repräsentatives Rollup von §A–§H, keine 1:1-Abbildung; jeder Anforderungspunkt oben ist für sich normativ.

- [ ] Keine sensiblen Daten werden in External Storage, world-readable-Modi, App-übergreifende SharedPreferences oder Logs geschrieben; gespeicherte Secrets sind Keystore-gestützt (nicht Jetpack Security); Backup-Regeln existieren als `dataExtractionRules` und, für minSdk < 31, als `fullBackupContent`
- [ ] Kein hartkodierter Schlüssel, keine eigene Krypto und kein kaputtes Primitiv erscheint im Code; Krypto nutzt AES-GCM/SHA-256/`SecureRandom` mit Keystore-Schlüsseln
- [ ] Aller Verkehr ist TLS; kein permissiver `TrustManager`/`HostnameVerifier` existiert; jedes Pinning ist NSC-basiert mit Backup-Pin auf einem eigenen Endpoint
- [ ] Jede Komponente deklariert `android:exported` explizit (Default false); jeder `PendingIntent` ist `FLAG_IMMUTABLE`, sofern nicht begründet; interne Zustellung nutzt explizite Intents
- [ ] Deep Links validieren Scheme und Host; entpackte Archiveinträge sind kanonisch-pfad-geprüft; kein Intent wird aus unvertrauenswürdigen Extras ohne Resolve-Check weitergereicht
- [ ] WebViews laufen mit JavaScript aus, sofern nicht nötig, ohne unvertrauenswürdige JS-Bridge, mit deaktiviertem File-/Content-Access und einer Allowlist für Navigation
- [ ] Permissions sind minimal und im Kontext angefragt; kein persistenter Hardware-Identifier wird genutzt; die Data-Safety-Deklaration entspricht dem Verhalten
- [ ] Release-Builds sind nicht-debuggable; kein Secret ist committet; API-Keys sind restringiert und echte Secrets backend-proxied
- [ ] CI fährt einen Dependency-Vulnerability-Scan und die Android-Lint-Security-Checks auf Fehler-Stufe
- [ ] Biometrischer Schutz lokaler Daten nutzt ein `CryptoObject`, keinen reinen Erfolgs-Callback
- [ ] Access-Token leben nur im Speicher und Refresh-Token Keystore-verschlüsselt im Internal Storage; Logout widerruft server-seitig und löscht Token und nutzerbezogenen Cache; Session-Ablauf führt zu stillem Refresh oder einer Re-Authentifizierungs-Aufforderung, nie zu einem generischen Fehler
- [ ] Jeder OAuth-2.0/OIDC-Sign-in läuft als Authorization-Code + PKCE in Custom Tabs/AppAuth, nie in einem eingebetteten WebView
- [ ] R8/Obfuskierung wird weder als Sicherheitskontrolle genutzt noch als solche dokumentiert; Release-Minification ist wegen der Größe aktiviert, ohne Sicherheitsversprechen
- [ ] Jeder gespeicherte Datentyp trägt eine Klasse gemäß §H mit den Kontrollen, die diese Klasse verlangt; eine Room-Replica mit Klasse-2-Daten ist auf L1 nicht datenbankverschlüsselt, sofern kein Klasse-3-Datum oder keine benannte Bedrohung es rechtfertigt
- [ ] Das anvisierte MAS-Profil (L1-Baseline plus etwaige L2/R-Kontrollen) ist mit Begründung protokolliert; R-Tier-Kontrollen fehlen, sofern kein benanntes Asset sie rechtfertigt

## Offene Fragen

Alle Fragen sind Parking-Lot-Klasse: Die Anforderungen oben nennen für jede einen funktionierenden Default.

- Certificate Pinning: für generierte Apps auf kein Pinning + Certificate Transparency defaulten (der wartungsarme Pfad) oder Pinning als Opt-in-Template für Eigen-Endpoint-Apps anbieten?
- Verschlüsselte lokale Speicherung: jetzt auf Tink-über-Keystore als generiertes Muster standardisieren, da Jetpack Security deprecated ist, oder auf einen offiziellen Nachfolger warten?
- Self-Audit-Tooling-Tiefe: `mobsfscan` (und optional einen Pre-Release-MobSF-Scan) standardmäßig in die CI des Projekt-Scaffolds verdrahten oder opt-in lassen?
- MAS-Profil-Default: Ist L1 der richtige protokollierte Default für generierte Apps, mit L2-Opt-in je Datensensitivität?

## Referenzen

Alle Quellen abgerufen am 11.08.2026; [R26]–[R37] ergänzt und erneut verifiziert am 19.08.2026. Klassenmarker: (P) primäre/maßgebliche Vendor-Dokumentation, (O) OWASP/Standardisierungsgremium, (S) sekundär. Plattform-erzwungene Fakten zitieren die Primärquelle; umstrittene Positionen (Pinning, Root-Detection, Obfuskierung) tragen die divergierenden Quellen inline in der Prosa oben.

- [R1] Android Security Tips (Checkliste) (P): <https://developer.android.com/privacy-and-security/security-tips>
- [R2] App Security Best Practices (P): <https://developer.android.com/privacy-and-security/security-best-practices>
- [R3] App-Security-Risiko-Katalog (MASVS-gegliedert) (P): <https://developer.android.com/privacy-and-security/risks>
- [R4] Cryptography-Guidance (Primitive, Provider-Regeln, Tink) (P): <https://developer.android.com/privacy-and-security/cryptography>
- [R5] Android-Keystore-System (P): <https://developer.android.com/privacy-and-security/keystore>
- [R6] Network Security Configuration (Pinning, Trust Anchors, CT) (P): <https://developer.android.com/privacy-and-security/security-config>
- [R7] Security mit HTTPS/SSL (Pinning abgeraten, TrustManager-Regeln) (P): <https://developer.android.com/privacy-and-security/security-ssl>
- [R8] Android-12-Behavior-Changes (exported, PendingIntent-Mutabilität) (P): <https://developer.android.com/about/versions/12/behavior-changes-12>
- [R9] Auto Backup — `dataExtractionRules` (API 31+) plus `fullBackupContent` für Android 11 und niedriger, `getNoBackupFilesDir()`, Block Store für Token-Restore (P): <https://developer.android.com/identity/data/autobackup>
- [R10] Jetpack-Security-Releases (`security-crypto` 1.1.0-beta01, 04.06.2025, deprecated alle APIs; 1.1.0, 30.07.2025) (P): <https://developer.android.com/jetpack/androidx/releases/security>
- [R11] Biometrische Authentifizierung (CryptoObject) (P): <https://developer.android.com/identity/sign-in/biometric-auth>
- [R12] Permissions-Best-Practices (Usage Notes) (P): <https://developer.android.com/training/permissions/usage-notes>
- [R13] AccessibilityService-Play-Policy (S): <https://support.google.com/googleplay/android-developer/answer/10964491>
- [R14] Data-Safety-Section (Play) (S): <https://support.google.com/googleplay/android-developer/answer/10787469>
- [R15] Code shrinken/obfuskieren (R8 = Größe, nicht Sicherheit) (P): <https://developer.android.com/build/shrink-code>
- [R16] secrets-gradle-plugin (VCS-Hygiene, kein APK-Schutz) (S): <https://github.com/google/secrets-gradle-plugin>
- [R17] Google-API-Key-Security-Best-Practices (Restriktion) (P): <https://developers.google.com/maps/api-security-best-practices>
- [R18] OWASP MASVS v2 (Kontrollgruppen, Testing-Profile) (O): <https://mas.owasp.org/MASVS/>
- [R19] OWASP MAS Testing Profiles (L1/L2/R) (O): <https://mas.owasp.org/MASTG/0x03b-Testing-Profiles/>
- [R20] OWASP Mobile Top 10 (2024) (O): <https://owasp.org/www-project-mobile-top-10/>
- [R21] OWASP MASVS-RESILIENCE (Abwesenheit ist keine Schwachstelle) (O): <https://github.com/OWASP/masvs/blob/master/Document/11-MASVS-RESILIENCE.md>
- [R22] osv-scanner (Gradle-Vulnerability-Scanning) (S): <https://github.com/google/osv-scanner>
- [R23] mobsfscan (CI-Self-Audit) (S): <https://github.com/MobSF/mobsfscan>
- [R24] Intent-Redirection-Guidance (P): <https://support.google.com/faqs/answer/9267555>
- [R25] Content-Provider-Path-Traversal-Guidance (P): <https://support.google.com/faqs/answer/7496913>
- [R26] Copy and Paste — `ClipDescription.EXTRA_IS_SENSITIVE` für sensible Clipboard-Inhalte (P): <https://developer.android.com/develop/ui/views/touch-and-input/copy-paste>
- [R27] Block Store — Device-to-Device-Credential-Restore, bis zu 16 Einträge à 4 KB (P): <https://developer.android.com/identity/block-store>
- [R28] `<application>`-Manifest-Element — `android:hasFragileUserData` (P): <https://developer.android.com/guide/topics/manifest/application-element>
- [R29] Android-9-Behavior-Changes — Cleartext default deaktiviert für Apps mit targetSdk ≥ 28 (P): <https://developer.android.com/about/versions/pie/android-9.0-changes-28>
- [R30] `WebView.addJavascriptInterface` — Annotation Pflicht ab targetSdk 17 (`JELLY_BEAN_MR1`), Reflection-Risiko auf älteren Runtimes (P): <https://developer.android.com/reference/android/webkit/WebView#addJavascriptInterface(java.lang.Object,%20java.lang.String)>
- [R31] `Activity.setRecentsScreenshotEnabled` (API 33) und `FLAG_SECURE` (P): <https://developer.android.com/reference/android/app/Activity#setRecentsScreenshotEnabled(boolean)>
- [R32] OWASP MASTG — Mobile-App-Authentifizierungsarchitekturen (Access-Token im flüchtigen Speicher, Refresh-Token in sicherem Storage, Logout muss die Server-Session zerstören, OAuth-Best-Practices) (O): <https://mas.owasp.org/MASTG/0x04e-Testing-Authentication-and-Session-Management/>
- [R33] RFC 8252 — OAuth 2.0 for Native Apps (§8.12: native Apps dürfen keine eingebetteten User-Agents nutzen) (O): <https://www.rfc-editor.org/rfc/rfc8252>
- [R34] Android-Custom-Tabs-Überblick (externer User-Agent für Sign-in) (P): <https://developer.chrome.com/docs/android/custom-tabs>
- [R35] AppAuth for Android — Referenz-Client der OpenID Foundation für RFC-8252-Flows (S): <https://github.com/openid/AppAuth-Android>
- [R36] RFC 9700 — OAuth 2.0 Security Best Current Practice (§4.14.2 Refresh-Token-Rotation / sender-constrained Refresh-Token) (O): <https://www.rfc-editor.org/rfc/rfc9700>
- [R37] OWASP MASTG-TEST-0017 (Confirm Credentials) und MASTG-TEST-0018 (Biometric Authentication) (O): <https://mas.owasp.org/MASTG/tests/android/MASVS-AUTH/MASTG-TEST-0018/>
