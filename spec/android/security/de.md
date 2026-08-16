# App-Sicherheit

Status: draft

## Kontext

Sicherheit ist ein Satz von Anforderungen, die über Speicherung, Kryptografie, Netzwerk, IPC, WebViews, Permissions und den Build hinweg gelten müssen — kein Feature, das vor dem Release angeschraubt wird. Diese Spec definiert die sicherheitsrelevanten Themengebiete, die eine mit den Skills dieses Repositories gebaute App beachten muss, ehrlich kalibriert für den typischen Nicht-Fintech-Consumer-App-Fall: die wirklich tragende Baseline, die situative Defense-in-Depth und die Resilience-Schicht (Root-Detection, Obfuskierung-als-Sicherheit), die laut Evidenz optional und oft kontraproduktiv ist.

Der Inhalt ist aus einem Recherche-Durchlauf (August 2026) destilliert: die offizielle Android-Security-Guidance (developer.android.com/privacy-and-security — Security Tips, Best Practices, der MASVS-gegliederte Risiko-Katalog, Keystore, Network Security Config) und das OWASP-Mobile-Application-Security-Framework (MASVS-v2.x-Kontrollgruppen, die MAS-Testing-Profile L1/L2/R, die Mobile Top 10 2024, MASTG-Testerwartungen). Wo offizielle Guidance und Community-Konsens auseinandergehen — Certificate Pinning, Root-Detection, Obfuskierung, die deprecatete Jetpack-Security-Library — hält die Spec die ehrliche Position fest, statt zu cargo-culten.

Grenzen: Log-Hygiene-Mechanik (keine PII, R8-Stripping) teilt sich mit `spec/android/adb-workflows/` §C; Dependency-Update-Automatisierung als Security-Praxis überlappt `spec/android/project-structure/`; `debuggable=false` in Release-Builds steht in dieser Spec und in adb-workflows.

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
- **MUSS [MUST]** gespeicherte Secrets mit Android-Keystore-gestützten Schlüsseln verschlüsseln (oder einem robusten Tool wie Tink über Keystore) — den Mechanismus anpeilen, nicht `EncryptedSharedPreferences`/Jetpack Security, das seit 2025 deprecated ist, ohne Drop-in-Nachfolger
- **MUSS [MUST]** Secrets und gerätespezifische Identifier via `dataExtractionRules` aus Backups ausschließen (`android:allowBackup` explizit gesetzt, `getNoBackupFilesDir()` für nie gesicherte Daten)
- **SOLLTE [SHOULD]** Tastatur-Vorschläge/Clipboard-Exposition auf sensiblen Feldern deaktivieren und Block Store für Auth-Token statt Dateien nutzen

### B. Kryptografie (MASVS-CRYPTO)

- **DARF NICHT [MUST NOT]** eigene Kryptografie implementieren, hartkodierte Schlüssel einbetten oder kaputte Primitive nutzen (MD5/SHA-1 für Security, DES/RC4, ECB, `SHA1PRNG`)
- **MUSS [MUST]** aktuelle Primitive nutzen: AES-256-GCM (oder AES-CBC + HMAC-SHA-256), SHA-256-Familie, `SecureRandom`; Schlüssel im Android Keystore erzeugt und gehalten (nie einen Provider außer `AndroidKeyStore` angeben)
- **SOLLTE [SHOULD]** Schlüssel für sensible Daten an Nutzer-Authentifizierung binden (`setUserAuthenticationRequired`, `setInvalidatedByBiometricEnrollment`); **KANN [MAY]** StrongBox nutzen, wo das Risiko es rechtfertigt (für die meisten Apps nicht nötig)

### C. Netzwerk (MASVS-NETWORK)

- **MUSS [MUST]** TLS für allen Verkehr nutzen (Cleartext ist seit Android 9 default deaktiviert und bleibt aus — kein `usesCleartextTraffic`); **DARF NICHT [MUST NOT]** TLS mit einem permissiven `TrustManager`, einem No-op-`HostnameVerifier` oder Debug-Trust-Anchors im Release schwächen
- **KANN [MAY]** Zertifikate pinnen — aber nur via Network Security Config, nur für eigene Endpoints des Entwicklers, immer mit Backup-Pin, nie mit Custom-`TrustManager`; offizielle Guidance rät für die meisten Apps aktiv vom Pinning ab (Bricking-Risiko bei CA-Rotation), daher ist korrekte TLS-Validierung das MUSS und Pinning das situative KANN
- **SOLLTE [SHOULD]** Certificate Transparency (Opt-in ab Android 16, Default ab Android 17) als wartungsärmere Alternative zum Pinning einplanen

### D. Plattform und IPC (MASVS-PLATFORM)

- **MUSS [MUST]** `android:exported` an jeder Komponente explizit deklarieren und `false` setzen, sofern kein externer Zugriff beabsichtigt ist; jede exportierte Komponente permission-schützen und input-validieren (Android 12+ scheitert im Build bei fehlendem `exported`)
- **MUSS [MUST]** jeden `PendingIntent` immutable machen (`FLAG_IMMUTABLE`), sofern Mutation nicht wirklich nötig ist, und explizite Intents (Action + Component + Package) für interne Zustellung nutzen — implizite Intents tragen nie sensible Daten
- **MUSS [MUST]** die konkreten Schwachstellenklassen per Anforderung verbieten: Intent Redirection (nie einen angreifer-kontrollierten Intent aus Extras ohne Resolve-Check weiterreichen), unsichere Deep Links (URI-Scheme *und* Host per exaktem Match validieren; verifizierte App Links mit `autoVerify` bevorzugen), Content-Provider-Path-Traversal (`openFile`-Pfade kanonisieren) und Zip-Path-Traversal (`getCanonicalPath`-Prüfung auf jedem entpackten Eintrag)
- **MUSS [MUST]** WebViews härten: JavaScript aus, sofern nicht nötig; `addJavascriptInterface` nur für voll vertrauenswürdigen First-Party-Content (annotiert `@JavascriptInterface`, targetSdk ≥ 21); File-/Content-Access-Settings explizit deaktiviert; Navigation auf eine Allowlist beschränkt, fremde URLs an den Browser übergeben; Safe Browsing aktiviert lassen
- **SOLLTE [SHOULD]** `filterTouchesWhenObscured` / `setHideOverlayWindows` für sensible Controls und `FLAG_SECURE` für sensible Screens anwenden (mit dem dokumentierten Caveat, dass FLAG_SECURE allein Overlay-Angriffe nicht stoppt)

### E. Permissions und Privacy (MASVS-PRIVACY)

- **MUSS [MUST]** nur die minimalen Permissions anfragen, im Kontext, mit Begründung, und Ablehnung graceful behandeln (UX-Regeln gemäß `spec/android/app-design-navigation/` §F); **DARF NICHT [MUST NOT]** eine Permission anfragen, wo ein Intent an eine andere App genügt, und **DARF NICHT [MUST NOT]** persistente Hardware-Identifier (IMEI, Telefonnummer) als IDs nutzen. *Wie* dieses Minimum ermittelt, deklariert, angefordert, verifiziert und festgehalten wird — Ermittlungsmethodik, berechtigungsfreie Alternativen, Manifest-Regeln, Laufzeitablauf und Berechtigungsregister — liegt in `spec/android/permissions/`; dieser Punkt formuliert die Pflicht, jene Spec die Methode
- **MUSS [MUST]** die Play-Data-Safety-Deklaration wahrheitsgemäß zum tatsächlichen Verhalten halten, inklusive Third-Party-SDK-Datenflüssen
- **SOLLTE [SHOULD]** Third-Party-SDK-Datenerfassung an Nutzer-Consent gaten und die Permissions jedes SDK auditieren; **MUSS [MUST]** für jede AccessibilityService-Nutzung die Play-Policy erfüllen (Deklaration + Approval, `isAccessibilityTool` nur für echte Tools) — autonomes Handeln über die Accessibility-API ist verboten

### F. Code, Build und Supply Chain (MASVS-CODE)

- **MUSS [MUST]** Release-Builds mit `android:debuggable=false` ausliefern (Lint `HardcodedDebugMode` ist fatal), targetSdk aktuell halten und **DARF NICHT [MUST NOT]** Code dynamisch aus unvertrauenswürdigen Quellen laden, unvertrauenswürdige Daten unsicher deserialisieren oder SQL per String-Konkatenation bauen (nur parametrisierte Queries)
- **DARF NICHT [MUST NOT]** Secrets ins Repository committen; **MUSS [MUST]** das `secrets-gradle-plugin` nur als VCS-Hygiene behandeln, nicht als Schutz — ein Schlüssel im APK ist extrahierbar, also werden Client-Secrets restringiert (Google-API-Keys per Package + SHA-256) und echte Secrets leben hinter einem Backend-Proxy
- **MUSS [MUST]** allen unvertrauenswürdigen Input validieren (UI, IPC, Netzwerk, Dateisystem) und Key Attestation server-seitig validieren, falls Attestation genutzt wird
- **SOLLTE [SHOULD]** automatisierte Dependency-Updates (Renovate/Dependabot) und einen Vulnerability-Scan (osv-scanner, der OWASP dependency-check für Gradle praktisch abgelöst hat) in CI fahren; **SOLLTE [SHOULD]** die Android-Lint-Security-Checks (`TrustAllX509TrustManager`, `ExportedContentProvider`, `HardcodedDebugMode`, …) als Fehler erzwingen und `mobsfscan` in CI fahren (bester Effort/Value für einen Solo-Dev); **KANN [MAY]** Gradle Dependency Verification (Checksums) ergänzen — real, aber wartungsintensiv, daher SOLLTE/KANN, nicht MUSS

### G. Authentifizierung und Resilience (kalibriert)

- **MUSS [MUST]**, wo die App biometrisch authentifiziert, um lokale Daten zu schützen, `BiometricPrompt` mit einem `CryptoObject` (`BIOMETRIC_STRONG`) nutzen — ein reiner Erfolgs-Callback ist ein spoofbarer Client-Check und nur als UX-Convenience vor unkritischen Aktionen als **KANN [MAY]** akzeptabel
- **DARF NICHT [MUST NOT]** R8/Obfuskierung als Sicherheitskontrolle behandeln — es ist eine Größenoptimierung mit einem geringen Reverse-Engineering-Bremseffekt als Nebenwirkung; **SOLLTE [SHOULD]** R8-Minification fürs Release aktivieren (Größe plus dieser Nebeneffekt), nie als Sicherheitsversprechen
- **KANN [MAY]** Resilience-Tier-Kontrollen (Root-/Tamper-Detection, Play-Integrity-Attestation) nur dann ergänzen, wenn ein konkretes Business-Asset sie rechtfertigt; laut OWASP „does not in itself constitute a vulnerability", sie sind bypassbar und tragen False-Positive- und Platform-Lock-in-Kosten — für eine normale Consumer-App sind sie optional und oft nicht lohnend
- Welche L2/R-Kontrollen übernommen werden oder nicht, wird protokolliert (welches MAS-Profil die App anpeilt und warum)

## Akzeptanzkriterien

Die folgenden Kriterien sind ein bewusst repräsentatives Rollup von §A–§G, keine 1:1-Abbildung; jeder Anforderungspunkt oben ist für sich normativ.

- [ ] Keine sensiblen Daten werden in External Storage, world-readable-Modi, App-übergreifende SharedPreferences oder Logs geschrieben; gespeicherte Secrets sind Keystore-gestützt (nicht Jetpack Security)
- [ ] Kein hartkodierter Schlüssel, keine eigene Krypto und kein kaputtes Primitiv erscheint im Code; Krypto nutzt AES-GCM/SHA-256/`SecureRandom` mit Keystore-Schlüsseln
- [ ] Aller Verkehr ist TLS; kein permissiver `TrustManager`/`HostnameVerifier` existiert; jedes Pinning ist NSC-basiert mit Backup-Pin auf einem eigenen Endpoint
- [ ] Jede Komponente deklariert `android:exported` explizit (Default false); jeder `PendingIntent` ist `FLAG_IMMUTABLE`, sofern nicht begründet; interne Zustellung nutzt explizite Intents
- [ ] Deep Links validieren Scheme und Host; entpackte Archiveinträge sind kanonisch-pfad-geprüft; kein Intent wird aus unvertrauenswürdigen Extras ohne Resolve-Check weitergereicht
- [ ] WebViews laufen mit JavaScript aus, sofern nicht nötig, ohne unvertrauenswürdige JS-Bridge, mit deaktiviertem File-/Content-Access und einer Allowlist für Navigation
- [ ] Permissions sind minimal und im Kontext angefragt; kein persistenter Hardware-Identifier wird genutzt; die Data-Safety-Deklaration entspricht dem Verhalten
- [ ] Release-Builds sind nicht-debuggable; kein Secret ist committet; API-Keys sind restringiert und echte Secrets backend-proxied
- [ ] CI fährt einen Dependency-Vulnerability-Scan und die Android-Lint-Security-Checks auf Fehler-Stufe
- [ ] Biometrischer Schutz lokaler Daten nutzt ein `CryptoObject`, keinen reinen Erfolgs-Callback
- [ ] Das anvisierte MAS-Profil (L1-Baseline plus etwaige L2/R-Kontrollen) ist mit Begründung protokolliert; R-Tier-Kontrollen fehlen, sofern kein benanntes Asset sie rechtfertigt

## Offene Fragen

Alle Fragen sind Parking-Lot-Klasse: Die Anforderungen oben nennen für jede einen funktionierenden Default.

- Certificate Pinning: für generierte Apps auf kein Pinning + Certificate Transparency defaulten (der wartungsarme Pfad) oder Pinning als Opt-in-Template für Eigen-Endpoint-Apps anbieten?
- Verschlüsselte lokale Speicherung: jetzt auf Tink-über-Keystore als generiertes Muster standardisieren, da Jetpack Security deprecated ist, oder auf einen offiziellen Nachfolger warten?
- Self-Audit-Tooling-Tiefe: `mobsfscan` (und optional einen Pre-Release-MobSF-Scan) standardmäßig in die CI des Projekt-Scaffolds verdrahten oder opt-in lassen?
- MAS-Profil-Default: Ist L1 der richtige protokollierte Default für generierte Apps, mit L2-Opt-in je Datensensitivität?

## Referenzen

Alle Quellen abgerufen am 11.08.2026. Klassenmarker: (P) primäre/maßgebliche Vendor-Dokumentation, (O) OWASP/Standardisierungsgremium, (S) sekundär. Plattform-erzwungene Fakten zitieren die Primärquelle; umstrittene Positionen (Pinning, Root-Detection, Obfuskierung) tragen die divergierenden Quellen inline in der Prosa oben.

- [R1] Android Security Tips (Checkliste) (P): <https://developer.android.com/privacy-and-security/security-tips>
- [R2] App Security Best Practices (P): <https://developer.android.com/privacy-and-security/security-best-practices>
- [R3] App-Security-Risiko-Katalog (MASVS-gegliedert) (P): <https://developer.android.com/privacy-and-security/risks>
- [R4] Cryptography-Guidance (Primitive, Provider-Regeln, Tink) (P): <https://developer.android.com/privacy-and-security/cryptography>
- [R5] Android-Keystore-System (P): <https://developer.android.com/privacy-and-security/keystore>
- [R6] Network Security Configuration (Pinning, Trust Anchors, CT) (P): <https://developer.android.com/privacy-and-security/security-config>
- [R7] Security mit HTTPS/SSL (Pinning abgeraten, TrustManager-Regeln) (P): <https://developer.android.com/privacy-and-security/security-ssl>
- [R8] Android-12-Behavior-Changes (exported, PendingIntent-Mutabilität) (P): <https://developer.android.com/about/versions/12/behavior-changes-12>
- [R9] Auto Backup und Data Extraction Rules (P): <https://developer.android.com/identity/data/autobackup>
- [R10] Jetpack-Security-Deprecation (Releases) (P): <https://developer.android.com/jetpack/androidx/releases/security>
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
