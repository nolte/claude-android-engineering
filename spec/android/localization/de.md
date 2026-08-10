# Lokalisierung

Status: draft

## Kontext

Mehrsprachigkeit ist keine am Ende angeschraubte Übersetzungsdatei — sie ist ein Satz von Disziplinen, die ab der ersten String-Ressource gelten müssen: externalisierte Strings, locale-korrekte Formatierung, RTL-fähige Layouts, eine Per-App-Sprachoberfläche und ein Übersetzungs-Workflow, der Sprachen synchron hält. Diese Spec ist das vollständige Internationalisierungs-/Lokalisierungskonzept für Apps, die mit den Skills dieses Repositories gebaut werden — dimensioniert für den typischen Portfolio-Fall (zweisprachig Englisch/Deutsch), aber korrekt für jedes Sprachset.

Der Inhalt ist aus einem Recherche-Durchlauf (August 2026) destilliert: die offizielle Android-Lokalisierungsdokumentation (String-Ressourcen, mehrsprachige Ressourcenauflösung, Per-App-Sprachen, RTL, Pseudolocales, nichtlineare Font-Skalierung), die aktuelle Gradle-/AGP-Oberfläche (`generateLocaleConfig`, `localeFilters` als Ersatz des seit AGP 8.8 deprecateten `resourceConfigurations`), Googles Per-App-Language-Sample sowie Übersetzungs-Workflow-Praxis für kleine Teams (TMS-Optionen, der ehrliche Stand 2025/2026 LLM-gestützter Übersetzung).

Grenzen: Textexpansions-sichere Layout-Mechanik und Font-Skalierung teilen sich mit `spec/android/app-design-navigation/` §A (diese Spec besitzt die locale-getriebenen Ursachen); Icon-Spiegelungsregeln liegen in `spec/android/iconography/` §B; die Ausführung der Per-Locale-Tests gehört `spec/android/test-automation/`.

Leser: Autoren der Android-Skills dieses Repos sowie Reviewer, die beurteilen, ob eine generierte oder auditierte App vollständig lokalisierbar ist.

## Ziele

- Jeder nutzersichtbare String ab dem ersten generierten Screen externalisiert, übersetzbar und grammatisch sicher (positionale Platzhalter, echte Plurale)
- Eine vollständige Sprachoberfläche: systemsichtbare unterstützte Locales, ein In-App-Sprachwähler, korrekte Persistenz bis Android 12 hinunter
- Locale-korrektes Verhalten jenseits von Strings: Daten, Zahlen, Sortierung, Groß-/Kleinschreibung, RTL — keine Konkatenation, keine hartkodierten Formate
- Ein tragfähiger Übersetzungs-Workflow für einen Solo-Maintainer: eine Source of Truth, lint-geprüfte Vollständigkeit, Pseudolocale-Tests vor jeder Übersetzungsrunde

## Nicht-Ziele

- Play-Store-Listing-Übersetzung — Release-Scope, läuft über die Play Console, nicht über App-Ressourcen
- Content-/CMS-Lokalisierung (servergelieferter Text) — nur App-Ressourcen-Lokalisierung
- Die Wahl des konkreten Sprachsets einer App — Pro-App-Entscheidung; diese Spec fixiert die Mechanik für jedes Set
- Layout-Mechanik der Textexpansion (gehört der Design-Spec) jenseits der Benennung der locale-getriebenen Ursachen

## Anforderungen

### A. String-Ressourcen

- **MUSS [MUST]** jeden nutzersichtbaren String nach `strings.xml` externalisieren; der `HardcodedText`-Lint-Check ist auf Fehler-Stufe, und generierter Code inlined nie UI-Text
- **MUSS [MUST]** positionale Platzhalter (`%1$s`, `%2$d`) in jedem parametrisierten String nutzen — Übersetzer müssen Argumente umordnen können, was sequentielle Platzhalter verbieten
- **MUSS [MUST]** nicht zu übersetzende Einträge `translatable="false"` markieren (Markennamen, technische Tokens) und nur im Default-`values/` halten
- **MUSS [MUST]** `<plurals>` mit den vollen sprachabhängigen Quantity-Klassen für grammatische Mengen nutzen (immer inklusive `other`, immer mit der Zahl als Platzhalter — der `ImpliedQuantity`-Lint-Fehler existiert, weil „one" in manchen Sprachen auch 101 abdeckt); **DARF NICHT [MUST NOT]** Plurale für UI-Zustände missbrauchen
- **DARF NICHT [MUST NOT]** Sätze durch Konkatenation übersetzter Fragmente bauen — Wortstellung ist sprachspezifisch; ein Satz ist ein String mit Platzhaltern
- **DARF NICHT [MUST NOT]** übersetzbaren Inhalt in indexbasierte `<string-array>`-Einträge legen — Reihenfolge-/Anzahl-Drift über Locales verschiebt still die Bedeutung; Arrays referenzieren `@string`-Einträge
- **SOLLTE [SHOULD]** Strings mit Feature-/Screen-Präfix benennen (`settings_language_title`, `common_cancel`) und unantastbare Segmente in `<xliff:g id example>`-Markup wrappen; **SOLLTE [SHOULD]** über jedem nicht offensichtlichen String einen Übersetzer-Kontextkommentar (Zweck, Platzierung, Längenlimit) führen

### B. Ressourcenauflösung und Build-Konfiguration

- **MUSS [MUST]** das Default-`values/` in der Source-of-Truth-Sprache vollständig halten (Englisch für dieses Portfolio); ein im Default-Set fehlender String crasht nicht unterstützte Locales — `MissingTranslation`/`ExtraTranslation`-Lint bleibt als Vollständigkeits-Gate auf Fehler-Stufe
- **MUSS [MUST]** das unterstützte Locale-Set im Build deklarieren: `androidResources { localeFilters += listOf("en", "de") }` (der AGP-8.8+-Ersatz für das deprecatete `resourceConfigurations`), was zugleich Library-Locales strippt
- **SOLLTE [SHOULD]** BCP-47-Qualifier (`values-b+…`) für neue Ressourcenverzeichnisse nutzen und sich auf die Android-7+-Auflösungskette (exakt → Sprache → Kind-Dialekte → nächste Nutzer-Locale → Default) verlassen, statt Ressourcen je Dialekt zu duplizieren
- **KANN [MAY]** partielle Übersetzungen transient führen (der Fallback deckt Lücken), aber eine Release-Runde schließt sie (Gate gemäß §E)

### C. Per-App-Sprachoberfläche

- **MUSS [MUST]** unterstützte Sprachen für das System sichtbar machen: `generateLocaleConfig = true` mit `resources.properties` (`unqualifiedResLocale=…`) — oder ein manuelles `locales_config.xml`, verdrahtet via `android:localeConfig`
- **MUSS [MUST]** den In-App-Sprachwähler über `AppCompatDelegate.setApplicationLocales()`/`getApplicationLocales()` implementieren (Activities sind `AppCompatActivity`, auch in Compose-Apps), mit dem `autoStoreLocales`-Manifest-Service für Persistenz unterhalb Android 13
- **SOLLTE [SHOULD]** „Systemstandard" als Wahl anbieten (`setApplicationLocales(emptyLocaleList)`) und gespeicherte Locales zurücksetzen, wenn eine Sprache aus der Konfiguration fällt, damit Nutzer nicht stranden
- **KANN [MAY]** den Framework-`LocaleManager` direkt nutzen, aber nur bei minSdk ≥ 33

### D. Locale-korrektes Verhalten

- **MUSS [MUST]** Daten/Zeiten über lokalisierte `java.time`-Formatter formatieren (`DateTimeFormatter.ofLocalized…`, ICU-Skeletons via `getBestDateTimePattern` für eigene Formen; `DateUtils` für relative Zeiten) und Zahlen/Währungen über `NumberFormat`/ICU — nie handgebaute Muster oder String-Interpolation von Zahlen in RTL-Kontexte
- **MUSS [MUST]** locale-sensitive String-Operationen explizit machen: `Locale.ROOT` für interne Keys (das Turkish-i-Problem bricht sogar `equalsIgnoreCase`), Nutzer-Locale für Anzeige-Casing, `Collator` für nutzersichtbare Sortierung
- **MUSS [MUST]** RTL durchgängig unterstützen: `android:supportsRtl="true"`, überall start/end (nie left/right), Composes automatische `LayoutDirection`-Spiegelung mit bewussten `CompositionLocalProvider`-Overrides nur für richtungsfixierten Inhalt (Telefonnummern, Code); direktionale Icons spiegeln automatisch gemäß `spec/android/iconography/` §B
- **SOLLTE [SHOULD]** frei gerichtete Inline-Daten (Adressen, Telefonnummern in übersetzten Sätzen) mit `BidiFormatter.unicodeWrap` wrappen
- **SOLLTE [SHOULD]** `android.icu.*`-Klassen (API 24+) gegenüber ihren `java.text`-Pendants bevorzugen

### E. Testen und Übersetzungs-Workflow

- **MUSS [MUST]** Pseudolocales in Debug-Builds aktivieren (`isPseudoLocalesEnabled = true`) und vor jeder Übersetzungsrunde einen `en-XA`- (Expansion, Hardcoded-String- und Konkatenations-Erkennung) und `ar-XB`-Durchlauf (RTL) fahren
- **MUSS [MUST]** eine Sprache als Source of Truth behandeln und alle anderen ableiten; Übersetzungen divergieren nie strukturell (Per-Locale-Dateien tragen dieselben Keys, durch das Lint-Gate erzwungen)
- **MUSS [MUST]** Layouts bei 200 % Font-Skalierung und mit expandiertem Pseudolocale-Text verifizieren (Deutsch läuft ~30–40 % länger; keine Textcontainer fester Breite) — Ausführung über die Previews von `spec/android/test-automation/` (`@Preview(locale = …)`, `@PreviewFontScales`) und Per-Locale-Screenshot-Tests, wo vorhanden
- **SOLLTE [SHOULD]** einen leichtgewichtigen Übersetzungs-Workflow fahren: String-Freeze vor einer Release-Runde, LLM-gestützte Entwurfsübersetzung mit menschlichem Review für sichtbare Strings (der ehrliche Stand 2025/2026: LLM-Output wird in 55–80 % der Blind-Bewertungen als „gut" eingestuft — Entwurfsqualität, keine Ship-Qualität), ein TMS (Weblate/Crowdin) erst, wenn Contributor-Übersetzung beginnt
- **SOLLTE [SHOULD]** den App-Namen als `translatable="false"`-Marke behandeln, sofern lokalisiertes Branding keine bewusste Entscheidung ist

### F. Compose-Spezifika

- **MUSS [MUST]** Strings in Composables über `stringResource`/`pluralStringResource` lesen (rekompositionssicher bei Sprachwechsel); **DARF NICHT [MUST NOT]** Strings in Composables konkatenieren oder locale-abhängige Werte ohne Locale-/Configuration-Key in `remember` cachen
- **SOLLTE [SHOULD]** Per-Locale-Previews (`@Preview(locale = "de")`, `@Preview(locale = "ar")` für RTL) ins Standard-Preview-Set aufnehmen; Hinweis: der Preview-`locale`-Parameter setzt nur `LocalConfiguration` — Code, der `Locale.getDefault()` direkt liest, sieht ihn nicht (und sollte in UI-Code ohnehin nicht existieren)

## Akzeptanzkriterien

Die folgenden Kriterien sind ein bewusst repräsentatives Rollup von §A–§F, keine 1:1-Abbildung; jeder Anforderungspunkt oben ist für sich normativ.

- [ ] `lint` besteht mit `HardcodedText`, `MissingTranslation`, `ExtraTranslation` und `ImpliedQuantity` auf Fehler-Stufe; kein nutzersichtbarer String ist im Code inlined
- [ ] Jeder parametrisierte String nutzt positionale Platzhalter; keine Laufzeit-Konkatenation baut einen Satz
- [ ] Mengen rendern über `<plurals>` mit `other`-Fall und der Zahl im Text
- [ ] Der Build deklariert `localeFilters` passend zum unterstützten Set, und der System-Sprachwähler listet die App mit genau diesen Sprachen
- [ ] Der In-App-Sprachwähler wechselt die Sprache zur Laufzeit, persistiert über Neustarts auf Android 12 und 13+ und bietet „Systemstandard" an
- [ ] Daten, Zahlen und Währungen rendern in jeder unterstützten Sprache locale-korrekt; interne Keys nutzen `Locale.ROOT`-Operationen
- [ ] Die App rendert korrekt unter `ar-XB` (vollständig gespiegelt, kein left/right-Leck) und unter `en-XA` bei 200 % Font-Skalierung ohne abgeschnittene kritische UI
- [ ] `values/` (Quellsprache) ist vollständig; jede andere Locale-Datei trägt dasselbe Key-Set
- [ ] Composables lesen allen Text über `stringResource`-Familien-APIs; Per-Locale-Previews existieren für jedes Screen-Level-Composable
- [ ] Das generierte Projekt liefert zweisprachig aus (en Quelle, de Übersetzung), mit allem Obigen grün beim ersten Build

## Offene Fragen

Alle Fragen sind Parking-Lot-Klasse: Die Anforderungen oben nennen für jede einen funktionierenden Default.

- Translation Memory: von Anfang an ein TMS für den zweisprachigen Solo-Fall einführen oder git-only bleiben, bis externe Übersetzer auftauchen (aktueller Default: git-only)?
- LLM-Übersetzungsautomatisierung: einen Entwurfsübersetzungs-Schritt in einen künftigen Skill verdrahten (mit verpflichtendem menschlichem Review) oder Übersetzung komplett manuell halten?
- String-Naming: die `<screen>_<what>`-Konvention per Custom-Lint-Check erzwingen oder dem Review überlassen?
- Regionale Varianten (de-AT/de-CH, en-GB): explizit außen vor, bis ein realer Bedarf entsteht — bestätigen, wenn die erste App shippt?

## Referenzen

Alle Quellen abgerufen am 11.08.2026. Klassenmarker: (P) primäre/maßgebliche Vendor-Dokumentation, (S) sekundär. Plattform-Fakten zitieren die maßgebliche Primärquelle gemäß Portfolio-Triangulationskonvention; Workflow-Befunde sind inline attribuiert, wo einzelstudienbasiert.

- [R1] Lokalisierungs-Überblick (P): <https://developer.android.com/guide/topics/resources/localization>
- [R2] String-Ressourcen (Platzhalter, Plurale, Arrays, Styling) (P): <https://developer.android.com/guide/topics/resources/string-resource>
- [R3] Mehrsprachige Ressourcenauflösung (Fallback-Kette, BCP-47) (P): <https://developer.android.com/guide/topics/resources/multilingual-support>
- [R4] Per-App-Sprachen (localeConfig, AppCompatDelegate, autoStoreLocales) (P): <https://developer.android.com/guide/topics/resources/app-languages>
- [R5] Sprachunterstützungs-Grundlagen (RTL, Formatierung, BidiFormatter) (P): <https://developer.android.com/training/basics/supporting-devices/languages>
- [R6] Pseudolocales (en-XA/ar-XB) (P): <https://developer.android.com/guide/topics/resources/pseudolocales>
- [R7] Nichtlineare Font-Skalierung bis 200 % (Android 14) (P): <https://developer.android.com/about/versions/14/features>
- [R8] Compose-Ressourcen (stringResource, Rekomposition) (P): <https://developer.android.com/develop/ui/compose/resources>
- [R9] Compose-Previews (locale-/fontScale-Parameter) (P): <https://developer.android.com/develop/ui/compose/tooling/previews>
- [R10] Internationalisierung (ICU, MessageFormat, Casing/Kollation) (P): <https://developer.android.com/guide/topics/resources/internationalization>
- [R11] AGP-API-Updates (`localeFilters` ersetzt `resourceConfigurations`) (P): <https://developer.android.com/build/releases/gradle-plugin-api-updates>
- [R12] Lint-Checks — ImpliedQuantity u. a. (P): <https://googlesamples.github.io/android-custom-lint-rules/checks/ImpliedQuantity.md.html>
- [R13] Per-App-Languages-Sample (locales_config, Picker) (P): <https://github.com/android/user-interface-samples/tree/main/PerAppLanguages>
- [R14] M3-Bidirektionalität (Icon-Spiegelungsregeln) (P): <https://m3.material.io/foundations/layout/bidirectionality-rtl>
- [R15] Textgrößen-/Expansionsforschung (W3C) (S): <https://www.w3.org/International/articles/article-text-size.en.html>
- [R16] LLM-Übersetzungsqualitäts-Evaluation 2025 (Einzelstudie, attribuiert) (S): <https://lokalise.com/blog/what-is-the-best-llm-for-translation/>
- [R17] TMS-Landschaft für kleine Teams (S): <https://www.saashub.com/compare-crowdin-vs-weblate>
- [R18] Turkish-i-Casing-Problem (S): <https://garygregory.wordpress.com/2015/11/03/java-lowercase-conversion-turkey/>
