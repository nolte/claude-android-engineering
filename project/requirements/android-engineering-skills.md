# Requirements — Reusable Claude Skills for Android App Development

<!--
Produced via the `requirements-elicit` skill, following
spec/project/requirements-elicitation/.
Do not record a requirement before declaring the bounded context below.
`c_d` is an uncertainty proxy (self-consistency-derived), not a calibrated
probability. A requirement is `confirmed` only after an explicit teach-back.
-->

## Bounded context

- **What:** The repository `claude-android-engineering` provides reusable, spec-based Claude skills for Android app development, covering five areas: (1) greenfield project setup, (2) Compose UI building with embedded mobile-UX guidance, (3) UX audit of existing UI (including responsiveness/form factors), (4) perceived performance (measuring and fixing startup time and jank), (5) local development and debugging (build errors, ADB, logcat).
- **For whom:** The operator (nolte) plus deliberate public consumers — documentation, onboarding, and portability are design drivers, not afterthoughts.
- **Targets:** Newly generated projects and the operator's existing apps. Arbitrary foreign, non-conformant Android projects are not a design target.
- **Out of scope:** Play Store release, signing for distribution, store metadata.
- **Scope clarification (2026-08-13):** "production-grade / Play-Store-ready source code" is *in* scope and does not move the boundary above — it means the release build type is optimized and verified (R8, no debug leftovers, stability and platform currency inside stated budgets), not that a skill touches signing keys, store metadata, listings, tracks, or the Data Safety questionnaire. Confirmed by the operator when REQ-19 was elicited.

## Understanding KPI

- Thresholds: `τ_low = 0.4`, `τ_high = 0.8`, self-consistency `k = 2`, question budget = `12` (spec defaults, unchanged)
- `U_gate = min_d c_d` over required dimensions = **0.8**
- Termination: `saturation` — every required dimension reached `c_d ≥ τ_high` with teach-back where §D requires it, and no remaining candidate question had positive net EVPI. 8 of 12 budgeted questions used.
- Audit notes: the clarification on the ambiguous phrase "UX-Optimierungen" was **forced** (`functional` was below `τ_low`; `k = 2` self-consistency check produced divergent readings — audit-skill vs authoring-guidance vs performance). Follow-up questions on tool choices (screenshot-testing framework, detekt adoption) were **withheld** in the discretionary zone: their EVPI did not justify operator fatigue, and they are already tracked as Open Questions in `spec/android/project-structure/`.

### Gap matrix

| Dimension | Applicable | `c_d` | Uncertainty source | Evidence event |
|---|---|---|---|---|
| `functional` | yes | 0.85 | resolved (was: interpretation) | UX-reading multi-select + final teach-back of the five-area picture, confirmed 2026-08-10 |
| `non_functional` | yes | 0.8 | resolved (was: specification) | explicit answers: full nolte-shared baseline, CLI-first, ADB/emulator allowed, runtime research allowed |
| `constraints` | yes | 0.8 | resolved (was: interpretation) | spec-first workflow demonstrated by operator pivot; portfolio-convention baseline explicitly confirmed |
| `domain_objects` | yes | 0.8 | resolved (was: interpretation) | targets answer (new + existing own apps) + toolchain objects (Gradle, ADB, logcat, Compose) enumerated and confirmed in final teach-back |
| `actors` | yes | 0.8 | resolved (was: specification) | explicit answer: operator + deliberate public consumers |
| `acceptance_criteria` | yes | 0.85 | resolved (was: interpretation) | teach-back confirmed: spec conformance + green `./gradlew build`, jointly |
| `edge_cases` | yes | 0.8 | resolved (was: specification) | all four offered hard prohibitions explicitly confirmed |
| `scope_boundaries` | yes | 0.8 | resolved (was: interpretation) | in/out list from opening answer + "Play-Store-Release ist raus" reconfirmed in final teach-back |

## Requirements

- **REQ-1** — WHEN a skill of this repository completes an operation, the skill's output SHALL conform to the acceptance criteria of its underlying spec, AND any generated or modified project SHALL build green with `./gradlew build`.
  - _dimension_: `acceptance_criteria` · _status_: `confirmed` · _source_: "Alle Skills sollen auf gut formulierten Specs basieren" + teach-back "Ja, genau"
- **REQ-2** — The skills of this repository SHALL follow the nolte-shared plugin conventions (bilingual en/de specs, resumable runs per `.resume/`, German trigger phrases, skill-vs-agent split per `spec/claude/`).
  - _dimension_: `non_functional`, `constraints` · _status_: `confirmed` · _source_: baseline question, "Ja, komplett"
- **REQ-3** — The skills SHALL be operable without Android Studio; WHEN a skill runs, terminal, Gradle, and CLI tools SHALL suffice.
  - _dimension_: `non_functional` · _status_: `confirmed` · _source_: NFR multi-select, "CLI-first"
- **REQ-4** — WHERE debugging or verification requires a device, a skill MAY drive ADB, emulators, and attached devices.
  - _dimension_: `non_functional` · _status_: `confirmed` · _source_: NFR multi-select, "ADB/Emulator erlaubt"
- **REQ-5** — WHERE currency matters (for example tool versions), a skill MAY perform web research at runtime instead of relying on static knowledge.
  - _dimension_: `non_functional` · _status_: `confirmed` · _source_: NFR multi-select, "Recherche zur Laufzeit"
- **REQ-6** — IF a skill encounters a structural or convention decision not covered by any spec, THEN the skill SHALL report the gap (proposing a spec extension) and SHALL NOT decide silently.
  - _dimension_: `edge_cases` · _status_: `confirmed` · _source_: edge-case multi-select, "Spec-lose Strukturentscheidung"
- **REQ-7** — WHEN a skill run ends, the skill SHALL NOT leave the project in a non-building or red-test state without explicitly reporting it.
  - _dimension_: `edge_cases` · _status_: `confirmed` · _source_: edge-case multi-select, "Roter Zustand hinterlassen"
- **REQ-8** — The skills SHALL NOT overwrite or delete existing code or configuration without prior operator confirmation.
  - _dimension_: `edge_cases` · _status_: `confirmed` · _source_: edge-case multi-select, "Ungefragt destruktiv"
- **REQ-9** — The skills SHALL NOT scaffold with mechanisms the underlying spec marks as outdated (for example kapt, monolithic buildSrc, Groovy DSL).
  - _dimension_: `edge_cases` · _status_: `confirmed` · _source_: edge-case multi-select, "Veraltetes Wissen anwenden"
- **REQ-10** — The repository SHALL be designed for the operator plus public consumers: documentation, onboarding, and portability are design drivers for every shipped skill.
  - _dimension_: `actors` · _status_: `confirmed` · _source_: actors question, "Ich + öffentliche Konsumenten"
- **REQ-11** — The skills SHALL operate on newly generated projects AND on the operator's existing apps; arbitrary foreign, non-conformant projects are not a design target.
  - _dimension_: `domain_objects`, `scope_boundaries` · _status_: `confirmed` · _source_: targets question, "Neu + Bestand"
- **REQ-12** — The repository SHALL provide a project-setup skill: WHEN the operator requests a new Android app project, the skill SHALL scaffold it conforming to `spec/android/project-structure/`.
  - _dimension_: `functional` · _status_: `confirmed` · _source_: opening answer "Neue App-Projekte aufsetzen" + final teach-back
- **REQ-13** — The repository SHALL provide a Compose-UI skill: WHEN the operator requests a new screen or component, the skill SHALL build it with mobile-UX patterns applied at authoring time.
  - _dimension_: `functional` · _status_: `confirmed` · _source_: opening answer "Compose-UI bauen" + UX-reading "UX-Wissen beim Bauen" + final teach-back
- **REQ-14** — The repository SHALL provide a UX-audit skill: WHEN invoked on existing UI, the skill SHALL review screens/composables against mobile-UX criteria including responsiveness and form-factor adaptation, and SHALL deliver findings.
  - _dimension_: `functional` · _status_: `confirmed` · _source_: UX-reading "Audit bestehender UI" + "Responsiveness/Formfaktoren" + final teach-back
- **REQ-15** — The repository SHALL provide a perceived-performance skill: WHEN invoked, the skill SHALL measure UX-relevant performance (startup time, jank, loading states) and SHALL support fixing the findings.
  - _dimension_: `functional` · _status_: `confirmed` · _source_: UX-reading "Gefühlte Performance" + final teach-back
- **REQ-16** — The repository SHALL provide a local-development-and-debugging skill: WHEN the operator faces build errors or runtime defects, the skill SHALL support diagnosis via Gradle output, ADB, and logcat.
  - _dimension_: `functional` · _status_: `confirmed` · _source_: opening answer "Lokales entwickeln und debugging" + final teach-back
- **REQ-17** — Every skill SHALL be grounded in a well-formulated spec under `spec/`, authored before or with the skill; the spec is written first when missing.
  - _dimension_: `constraints` · _status_: `confirmed` · _source_: "Alle Skills sollen auf gut Fomulierten Specs basieren" + operator pivot "Erzeuge erst eine ausführliche spec" + baseline confirmation
- **REQ-18** — The repository SHALL provide a barcode-scanning skill: WHEN the operator adds code-scanning capability to an existing app, the skill SHALL decide the access path on evidence (preferring the path that needs no camera permission where it suffices), SHALL configure the capture pipeline against the decodability budget, and SHALL require every decoded payload to pass a trust boundary before the app acts on it. The skill SHALL also cover generating codes that the same scanners can read.
  - _dimension_: `functional` · _status_: `confirmed` · _source_: operator request 2026-08-12 "erzeuge den fehlenden skill für eine möglichst gute barcode scanner entwicklung innerhalb der app", grounded in `spec/android/barcode-scanning/` authored first per REQ-17

- **REQ-19** — The repository SHALL provide a feature-implementation skill: WHEN the operator asks for a feature in a native Kotlin Android app, the skill SHALL implement it across every layer it touches as a **flat, server-authoritative view layer** — the backend decides every domain question, the local replica is what the UI observes, and no domain rule is computed on the device. WHERE the feature would require a capability the backend contract does not provide, the skill SHALL capture it as a numbered backend-requirement artifact under `project/backend-requirements/` (including an OpenAPI proposal and backend-testable acceptance criteria) that a backend specialist can implement, and SHALL NOT implement a silent client-side workaround. WHEN the implementation ends, the skill SHALL close on the release-readiness gate (optimized release build verified on a device, lint, tests) per REQ-1 and REQ-7.
  - _dimension_: `functional`, `constraints` · _status_: `confirmed` · _source_: operator request 2026-08-13 "Erzeuge einen dedizierten Spezialisten für das Entwickeln von Android anwendungungen auf kotlin basis … Es soll darauf geachtet werden das es sich bei der Android um einen Flachen View Layer handelt. Bei Bedarf werden Anforderungen an die Backend Komponente Gesammelt …", plus three confirmed decisions in the same turn: server-authoritative with an offline cache as UI SSOT; code production-readiness only (no store process); handoff as repo artifact + OpenAPI draft + optional backend-repo issue. Grounded in `spec/android/app-architecture/`, `spec/android/backend-contract/`, and `spec/android/release-readiness/`, authored first per REQ-17

## Surviving assumptions / open risks

- **A2 (assumed):** The skills serve the operator's *personal* Android projects; no team-workflow requirements (shared conventions negotiation, CODEOWNERS flows) were elicited. Risk: if a team context emerges, `actors` needs a `revisit`.
- **Risk — skill granularity:** The five areas were confirmed as the functional picture, but the mapping to *individual* skills (five skills vs merged/split cuts, skill-vs-agent decisions per area) is deliberately left to per-skill decomposition under `spec/claude/skill-vs-agent/`. The final cut may differ from the five-area list without violating these requirements.
- **Risk — public-consumer depth:** REQ-10 confirms public consumers as a design driver, but no concrete consumer persona was elicited (which docs language, which onboarding path). Feed this into `audience-identify` before authoring README/docs.
- **Deferred tool decisions** (tracked as Open Questions in `spec/android/project-structure/`): detekt adoption, screenshot-testing framework, `build-logic/` scaffold timing, feature `api`/`impl` threshold.
