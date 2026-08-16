# App Security

Status: draft

## Context

Security is a set of requirements that must hold across storage, cryptography, networking, IPC, WebViews, permissions, and the build — not a feature bolted on before release. This spec defines the security-relevant subject areas an app built with this repository's skills must address, calibrated honestly for a typical non-fintech consumer app: the baseline that is genuinely load-bearing, the defense-in-depth that is situational, and the resilience layer (root detection, obfuscation-as-security) that the evidence says is optional and often counterproductive.

The content is distilled from a research pass (August 2026) over the official Android security guidance (developer.android.com/privacy-and-security — security tips, best practices, the MASVS-organized risk catalog, Keystore, network security config) and the OWASP Mobile Application Security framework (MASVS v2.x control groups, the MAS testing profiles L1/L2/R, the 2024 Mobile Top 10, MASTG test expectations). Where official guidance and community consensus diverge — certificate pinning, root detection, obfuscation, the deprecated Jetpack Security library — the spec records the honest position instead of cargo-culting.

Boundaries: log-hygiene mechanics (no PII, R8 stripping) are shared with `spec/android/adb-workflows/` §C; dependency-update automation as security practice overlaps `spec/android/project-structure/`; `debuggable=false` in release builds is stated in both this spec and adb-workflows.

Readers: authors of this repo's Android skills and reviewers judging whether a generated or audited app meets the security baseline.

## Goals

- Fix the MAS-L1 baseline as the unconditional security floor for every generated app: safe storage, correct crypto, TLS everywhere, safe IPC/WebView, minimal permissions, clean build
- Ban the concrete real-world vulnerability classes (intent redirection, insecure deep links, exported-component leaks, WebView JS bridges, path traversal) by requirement
- Calibrate honestly: name what is L2 (situational), what is R (optional), and where official guidance is insufficient or over-engineered — so a solo-developer app is neither exposed nor over-prescribed
- Make secrets handling truthful: no client-embedded secret is safe; the backend-proxy boundary and API-key restriction are the real controls

## Non-Goals

- Being a MASTG penetration-testing procedure — this spec states the defensive requirements a built app must satisfy, not how to attack it
- Backend/server security — only the client's contribution to end-to-end security (correct TLS, no client-trusted authorization)
- Regulatory/privacy-law compliance (GDPR DPIA) — the privacy requirements here are the security-adjacent baseline, not a legal assessment
- Play-Store release signing key management — release scope; only local `debuggable`/build hygiene is covered here
- Resilience-tier hardening (RASP, anti-tamper) as a requirement — named and scoped as optional per the evidence

## Requirements

### A. Data storage (MASVS-STORAGE)

- **MUST** store all private data in internal storage (`MODE_PRIVATE`); **MUST NOT** put sensitive data in external storage, world-readable/writable modes, or cross-app SharedPreferences, and **MUST NOT** log sensitive data (shared with `spec/android/adb-workflows/` §C: R8 strips debug logs only with minification on and the rule present)
- **MUST** encrypt stored secrets with Android Keystore-backed keys (or a robust tool such as Tink over Keystore) — target the mechanism, not `EncryptedSharedPreferences`/Jetpack Security, which is deprecated as of 2025 with no drop-in successor
- **MUST** exclude secrets and device-specific identifiers from backups via `dataExtractionRules` (`android:allowBackup` set explicitly, `getNoBackupFilesDir()` for never-backed-up data)
- **SHOULD** disable keyboard suggestions/clipboard exposure on sensitive fields and use Block Store for auth tokens rather than files

### B. Cryptography (MASVS-CRYPTO)

- **MUST NOT** implement custom cryptography, embed hardcoded keys, or use broken primitives (MD5/SHA-1 for security, DES/RC4, ECB, `SHA1PRNG`)
- **MUST** use current primitives: AES-256-GCM (or AES-CBC + HMAC-SHA-256), SHA-256 family, `SecureRandom`; keys generated and held in the Android Keystore (never specify a provider except `AndroidKeyStore`)
- **SHOULD** bind sensitive-data keys to user authentication (`setUserAuthenticationRequired`, `setInvalidatedByBiometricEnrollment`); **MAY** use StrongBox where the risk warrants it (not needed for most apps)

### C. Network (MASVS-NETWORK)

- **MUST** use TLS for all traffic (cleartext is disabled by default since Android 9 and stays off — no `usesCleartextTraffic`); **MUST NOT** weaken TLS with a permissive `TrustManager`, a no-op `HostnameVerifier`, or debug trust anchors in release
- **MAY** pin certificates — but only via the Network Security Config, only for the developer's own endpoints, always with a backup pin, never with a custom `TrustManager`; official guidance actively discourages pinning for most apps (bricking risk on CA rotation), so correct TLS validation is the MUST and pinning is the situational MAY
- **SHOULD** plan for Certificate Transparency (opt-in from Android 16, default from Android 17) as the lower-maintenance alternative to pinning

### D. Platform and IPC (MASVS-PLATFORM)

- **MUST** declare `android:exported` explicitly on every component and set it `false` unless external access is intended; permission-protect and input-validate any exported component (Android 12+ fails the build on missing `exported`)
- **MUST** make every `PendingIntent` immutable (`FLAG_IMMUTABLE`) unless mutation is genuinely required, and use explicit intents (action + component + package) for internal delivery — implicit intents never carry sensitive data
- **MUST** ban the concrete vulnerability classes by requirement: intent redirection (never forward an attacker-controlled intent from extras without a resolve check), insecure deep links (validate URI scheme *and* host by exact match; prefer verified App Links with `autoVerify`), content-provider path traversal (canonicalize `openFile` paths), and zip path traversal (`getCanonicalPath` check on every extracted entry)
- **MUST** harden WebViews: JavaScript off unless required; `addJavascriptInterface` only for fully trusted first-party content (annotated `@JavascriptInterface`, targetSdk ≥ 21); file/content access settings explicitly disabled; navigation restricted to an allowlist with foreign URLs handed to the browser; Safe Browsing left enabled
- **SHOULD** apply `filterTouchesWhenObscured` / `setHideOverlayWindows` for sensitive controls and `FLAG_SECURE` for sensitive screens (with the documented caveat that FLAG_SECURE alone doesn't stop overlay attacks)

### E. Permissions and privacy (MASVS-PRIVACY)

- **MUST** request only the minimum permissions, in context, with a rationale, and handle denial gracefully (UX rules per `spec/android/app-design-navigation/` §F); **MUST NOT** request a permission where an intent to another app suffices, and **MUST NOT** use persistent hardware identifiers (IMEI, phone number) as IDs. *How* that minimum is derived, declared, requested, verified, and recorded — the derivation method, the permission-free alternatives, the manifest rules, the runtime flow, and the permission ledger — is owned by `spec/android/permissions/`; this bullet states the obligation, that spec states the method
- **MUST** keep the Play Data Safety declaration accurate to actual behavior, including third-party SDK data flows
- **SHOULD** gate third-party SDK data collection on user consent and audit each SDK's permissions; **MUST**, for any AccessibilityService use, meet the Play policy (declaration + approval, `isAccessibilityTool` only for genuine tools) — autonomous action via the Accessibility API is prohibited

### F. Code, build, and supply chain (MASVS-CODE)

- **MUST** ship release builds with `android:debuggable=false` (lint `HardcodedDebugMode` is fatal), keep targetSdk current, and **MUST NOT** load code dynamically from untrusted sources, deserialize untrusted data unsafely, or build SQL by string concatenation (parameterized queries only)
- **MUST NOT** commit secrets to the repository; **MUST** treat the `secrets-gradle-plugin` as VCS hygiene only, not protection — a key in the APK is extractable, so client secrets are restricted (Google API keys by package + SHA-256) and real secrets live behind a backend proxy
- **MUST** validate all untrusted input (UI, IPC, network, filesystem) and validate key attestation server-side if attestation is used
- **SHOULD** run automated dependency updates (Renovate/Dependabot) and a vulnerability scan (osv-scanner, which has effectively displaced OWASP dependency-check for Gradle) in CI; **SHOULD** enforce the Android Lint security checks (`TrustAllX509TrustManager`, `ExportedContentProvider`, `HardcodedDebugMode`, …) as errors and run `mobsfscan` in CI (best effort/value for a solo dev); **MAY** add Gradle dependency verification (checksums) — real but high-maintenance, so SHOULD/MAY not MUST

### G. Authentication and resilience (calibrated)

- **MUST**, where the app authenticates biometrically to protect local data, use `BiometricPrompt` with a `CryptoObject` (`BIOMETRIC_STRONG`) — a result-only success callback is a spoofable client check and is acceptable **MAY** only as UX convenience before non-critical actions
- **MUST NOT** treat R8/obfuscation as a security control — it is a size optimization with a minor reverse-engineering speed-bump as a side effect; **SHOULD** enable R8 minification for release (size plus that side effect), never as a security promise
- **MAY** add resilience-tier controls (root/tamper detection, Play Integrity attestation) only when a concrete business asset justifies them; per OWASP their absence "does not in itself constitute a vulnerability", they are bypassable, and they carry false-positive and platform-lock-in costs — for a normal consumer app they are optional and often not worth it
- Whatever L2/R controls are or are not adopted, the decision is recorded (which MAS profile the app targets and why)

## Acceptance Criteria

The criteria below are a deliberate representative rollup of §A–§G, not a 1:1 mapping; every requirement bullet above is normative on its own.

- [ ] No sensitive data is written to external storage, world-readable modes, cross-app SharedPreferences, or logs; stored secrets are Keystore-backed (not Jetpack Security)
- [ ] No hardcoded key, custom crypto, or broken primitive appears in the code; crypto uses AES-GCM/SHA-256/`SecureRandom` with Keystore keys
- [ ] All traffic is TLS; no permissive `TrustManager`/`HostnameVerifier` exists; any pinning is NSC-based with a backup pin on an own endpoint
- [ ] Every component declares `android:exported` explicitly (default false); every `PendingIntent` is `FLAG_IMMUTABLE` unless justified; internal delivery uses explicit intents
- [ ] Deep links validate scheme and host; extracted archive entries are canonical-path-checked; no intent is redirected from untrusted extras without a resolve check
- [ ] WebViews run with JavaScript off unless required, no untrusted JS bridge, file/content access disabled, and an allowlist for navigation
- [ ] Permissions are minimal and requested in context; no persistent hardware identifier is used; the Data Safety declaration matches behavior
- [ ] Release builds are non-debuggable; no secret is committed; API keys are restricted and real secrets are backend-proxied
- [ ] CI runs a dependency vulnerability scan and the Android Lint security checks at error severity
- [ ] Biometric protection of local data uses a `CryptoObject`, not a result-only callback
- [ ] The targeted MAS profile (L1 baseline, plus any L2/R controls) is recorded with rationale; R-tier controls are absent unless a stated asset justifies them

## Open Questions

All questions are parking-lot class: the requirements above state a working default for each.

- Certificate pinning: default to no pinning + Certificate Transparency for generated apps (the low-maintenance path), or offer pinning as an opt-in template for own-endpoint apps?
- Encrypted local storage: standardize on Tink-over-Keystore as the generated pattern now that Jetpack Security is deprecated, or wait for an official successor?
- Self-audit tooling depth: wire `mobsfscan` (and optionally a pre-release MobSF scan) into the project scaffold's CI by default, or leave it opt-in?
- MAS profile default: is L1 the right recorded default for generated apps, with L2 opt-in per data sensitivity?

## References

All sources retrieved 2026-08-11. Class markers: (P) primary/authoritative vendor documentation, (O) OWASP/standards body, (S) secondary. Platform-enforced facts cite the primary source; contested positions (pinning, root detection, obfuscation) carry the divergent sources inline in the prose above.

- [R1] Android security tips (checklist) (P): <https://developer.android.com/privacy-and-security/security-tips>
- [R2] App security best practices (P): <https://developer.android.com/privacy-and-security/security-best-practices>
- [R3] App security risks catalog (MASVS-organized) (P): <https://developer.android.com/privacy-and-security/risks>
- [R4] Cryptography guidance (primitives, provider rules, Tink) (P): <https://developer.android.com/privacy-and-security/cryptography>
- [R5] Android Keystore system (P): <https://developer.android.com/privacy-and-security/keystore>
- [R6] Network security configuration (pinning, trust anchors, CT) (P): <https://developer.android.com/privacy-and-security/security-config>
- [R7] Security with HTTPS/SSL (pinning discouraged, TrustManager rules) (P): <https://developer.android.com/privacy-and-security/security-ssl>
- [R8] Android 12 behavior changes (exported, PendingIntent mutability) (P): <https://developer.android.com/about/versions/12/behavior-changes-12>
- [R9] Auto backup and data extraction rules (P): <https://developer.android.com/identity/data/autobackup>
- [R10] Jetpack Security deprecation (releases) (P): <https://developer.android.com/jetpack/androidx/releases/security>
- [R11] Biometric authentication (CryptoObject) (P): <https://developer.android.com/identity/sign-in/biometric-auth>
- [R12] Permissions best practices (usage notes) (P): <https://developer.android.com/training/permissions/usage-notes>
- [R13] AccessibilityService Play policy (S): <https://support.google.com/googleplay/android-developer/answer/10964491>
- [R14] Data safety section (Play) (S): <https://support.google.com/googleplay/android-developer/answer/10787469>
- [R15] Shrink/obfuscate code (R8 = size, not security) (P): <https://developer.android.com/build/shrink-code>
- [R16] secrets-gradle-plugin (VCS hygiene, not APK protection) (S): <https://github.com/google/secrets-gradle-plugin>
- [R17] Google API key security best practices (restriction) (P): <https://developers.google.com/maps/api-security-best-practices>
- [R18] OWASP MASVS v2 (control groups, testing profiles) (O): <https://mas.owasp.org/MASVS/>
- [R19] OWASP MAS testing profiles (L1/L2/R) (O): <https://mas.owasp.org/MASTG/0x03b-Testing-Profiles/>
- [R20] OWASP Mobile Top 10 (2024) (O): <https://owasp.org/www-project-mobile-top-10/>
- [R21] OWASP MASVS-RESILIENCE (absence is not a vulnerability) (O): <https://github.com/OWASP/masvs/blob/master/Document/11-MASVS-RESILIENCE.md>
- [R22] osv-scanner (Gradle vulnerability scanning) (S): <https://github.com/google/osv-scanner>
- [R23] mobsfscan (CI self-audit) (S): <https://github.com/MobSF/mobsfscan>
- [R24] Intent redirection guidance (P): <https://support.google.com/faqs/answer/9267555>
- [R25] Content-provider path traversal guidance (P): <https://support.google.com/faqs/answer/7496913>
