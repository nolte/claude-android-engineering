#!/usr/bin/env python3
"""Lightweight skill / agent frontmatter validator.

Implements the structural checks named in `spec/claude/skill-management/`
§"Frontmatter validation" and `spec/claude/agent-management/` §Structure.
This is a stop-gap for the upstream `skills-ref` CLI mentioned in
`spec/claude/skill-review/` §"Checks derived from external skill-structure
validation"; once an official binary ships under `anthropics/skills`, this
script can be retired.

Exit codes:
  0  every checked artifact passes
  1  at least one error (`Critical`-grade per `review-plan` §Severity scale)
  2  internal error (file unreadable, YAML unrecoverable, etc.)

Usage:
  python scripts/validate_skills.py              # checks every skill + agent
  python scripts/validate_skills.py skills/foo/  # checks one target

Output is one finding per line, prefixed with severity in Title Case so
downstream tooling can grep deterministically.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - PyYAML is a pinned dev dependency
    yaml = None  # the strict-parse check degrades to a no-op rather than crashing

REPO = Path(__file__).resolve().parent.parent

STARTER_TAGS = {
    "pull-request", "review", "audit", "scaffolding", "prose",
    "audience", "release", "quality-gate", "dependency", "requirements",
    "design", "media", "privacy", "orchestrate", "implementation",
    "planning", "frontend", "ui", "fullstack", "issue",
    "lifecycle", "triage", "validation",
}
RESERVED_TOKENS = {"anthropic", "claude"}
GENERIC_NAMES = {"helper", "utils", "tools", "documents", "data", "files"}
NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")

# --- Name-form convention --------------------------------------------------
# spec/claude/skill-management/ §"Frontmatter validation" and
# spec/claude/skill-agent-naming/ (normative owner) fixes one name form per artefact type:
#   skills  -> <object-noun>-<action>   (trailing token names the action,
#              a finite verb like `apply`/`create` or a deverbal action noun
#              like `audit`/`review`/`handoff`/`management`)
#   agents  -> <subject>-<role-noun>    (trailing token names the actor role,
#              in English almost always carrying -er/-or/-ist morphology)
# Both checks below are Suggestion-grade: a form deviation is a discoverability
# smell, never a platform-validator failure, so it never breaks CI. The
# allowlists are bootstrapped from the current surface; a genuinely new action
# verb or role noun is added here in the same PR that introduces the artefact.
#
# Trailing action tokens established across the skill surface. Extend when a new
# skill legitimately introduces a new action token.
SKILL_ACTION_TOKENS = {
    "apply", "assess", "audit", "author", "capture", "check", "create", "curate",
    "decompose", "define", "derive", "elicit", "execute", "generate", "handoff", "identify",
    "init", "maintain", "manage", "management", "merge", "optimize",
    "orchestrate", "plan", "refactor", "refine", "review", "revise",
    "scope", "start", "sweep", "triage", "trigger",
    "add", "augment", "scaffold", "migrate", "sync", "determine", "release", "map",
    "design",
}
# Closed exception list: established skill names whose trailing token is not an
# action token and that predate or otherwise outweigh a breaking rename. Kept in
# sync with skill-management §Frontmatter validation §"Documented exceptions".
SKILL_NAME_FORM_EXCEPTIONS = {"spec", "yaml-json-schema", "quality-gate"}
# Agent role-noun morphology: an object-role name ends in an actor noun, which
# in English almost always carries one of these derivational suffixes.
AGENT_ROLE_SUFFIXES = ("er", "or", "ist", "ian", "eur")
# Actor nouns that name a role without -er/-or/-ist morphology.
AGENT_ROLE_NOUNS = {"expert"}
# Closed exception list: established agent names that don't fit
# <subject>-<role-noun>. Kept in sync with agent-management §Structure
# §"Documented exceptions".
AGENT_NAME_FORM_EXCEPTIONS = {"png-to-transparent-svg", "audience-review"}
DOUBLE_HYPHEN_RE = re.compile(r"--")
# Match only HTML-shaped tags that the upstream Anthropic platform validator
# rejects: a known HTML-element name (lowercased) optionally followed by
# attributes. Spec-placeholder tokens like `<n>`, `<slug>`, `<topic>`,
# `<canonical_language>` use angle brackets but are documented placeholder
# notation, not XML; the upstream validator accepts them.
HTML_TAG_NAMES = {
    "a", "abbr", "address", "area", "article", "aside", "audio", "b", "base",
    "bdi", "bdo", "blockquote", "body", "br", "button", "canvas", "caption",
    "cite", "code", "col", "colgroup", "data", "datalist", "dd", "del",
    "details", "dfn", "dialog", "div", "dl", "dt", "em", "embed", "fieldset",
    "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5",
    "h6", "head", "header", "hr", "html", "i", "iframe", "img", "input",
    "ins", "kbd", "label", "legend", "li", "link", "main", "map", "mark",
    "menu", "meta", "meter", "nav", "noscript", "object", "ol", "optgroup",
    "option", "output", "p", "param", "picture", "pre", "progress", "q",
    "rp", "rt", "ruby", "s", "samp", "script", "section", "select", "small",
    "source", "span", "strong", "style", "sub", "summary", "sup", "svg",
    "table", "tbody", "td", "template", "textarea", "tfoot", "th", "thead",
    "time", "title", "tr", "track", "u", "ul", "var", "video", "wbr",
}
XML_TAG_RE = re.compile(r"<(/?)([a-z][a-z0-9]*)(\s[^>]*)?/?>")
FORBIDDEN_PRONOUNS_RE = re.compile(r"\b(I|you|your|yours|yourself|we|our|ours|us)\b")

# Strip text inside double-quoted spans (`"..."`) before applying the
# third-person check. Quoted spans are user-trigger phrases or sample
# operator-voice quotes, not author voice; the spec rule bans first /
# second person in *author voice* only (per
# `agentskills.io/skill-creation/best-practices`).
QUOTED_SPAN_RE = re.compile(r'"[^"]*"')


@dataclass
class Finding:
    severity: str  # Critical | Warning | Suggestion | Info
    target: str
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.severity:11s} {self.target}  [{self.rule}] {self.message}"


def parse_frontmatter(text: str) -> dict | None:
    """Return a dict of frontmatter scalars, or None when no `---` block exists.

    Hand-rolled to avoid yaml.safe_load tripping on `: ` inside unquoted
    description values. Only handles the keys this validator needs:
    `name`, `description`, `tags`, `distribution`, `tools`, `model`,
    `when_to_use`, `phase`. Block scalars (`>-`) are folded.
    """
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    fm = parts[1]
    out: dict = {}

    # description / name / distribution / model / when_to_use / phase are scalar
    for key in ("name", "description", "distribution", "model", "when_to_use", "phase", "resumable"):
        m = re.search(
            rf'^{key}:\s*(.+?)(?=\n[a-z_-]+:\s|\n---|\Z)',
            fm, re.M | re.S,
        )
        if not m:
            continue
        raw = m.group(1).strip()
        if raw.startswith('"') and raw.endswith('"'):
            raw = raw[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        elif raw.startswith("'") and raw.endswith("'"):
            raw = raw[1:-1]
        elif raw.startswith(">-"):
            body = raw.split("\n", 1)[1] if "\n" in raw else ""
            raw = re.sub(r"\n\s+", " ", body).strip()
        out[key] = raw

    # tags: [..] inline OR multi-line
    m = re.search(r"^tags:\s*\[([^\]]*)\]", fm, re.M)
    if m:
        out["tags"] = [t.strip().strip('"').strip("'") for t in m.group(1).split(",") if t.strip()]
    else:
        m2 = re.search(r"^tags:\s*\n((?:\s+- .+\n)+)", fm, re.M)
        if m2:
            out["tags"] = [
                line.strip().lstrip("- ").strip()
                for line in m2.group(1).split("\n") if line.strip()
            ]

    # tools: comma list OR multi-line
    m = re.search(r"^tools:\s*(.+)$", fm, re.M)
    if m:
        out["tools"] = [t.strip() for t in m.group(1).split(",") if t.strip()]

    return out


def check_name(name: str | None, target: str, kind: str, expected_basename: str, body: str = "") -> list[Finding]:
    findings: list[Finding] = []
    if not name:
        findings.append(Finding("Critical", target, f"{kind}-management.frontmatter-name-missing",
                                "frontmatter `name` is missing"))
        return findings
    if not (1 <= len(name) <= 64):
        findings.append(Finding("Critical", target, f"{kind}-management.frontmatter-name-length",
                                f"`name` length {len(name)} is outside the 1–64 character range"))
    if not NAME_RE.match(name):
        findings.append(Finding("Critical", target, f"{kind}-management.frontmatter-name-charset",
                                f"`name` `{name}` contains characters outside lowercase ASCII letters, digits, and hyphens, or starts/ends with `-`"))
    if DOUBLE_HYPHEN_RE.search(name):
        findings.append(Finding("Critical", target, f"{kind}-management.frontmatter-name-double-hyphen",
                                f"`name` `{name}` contains consecutive hyphens"))
    if any(t in name.lower() for t in RESERVED_TOKENS):
        # Narrow exception per `skill-management` §Frontmatter validation /
        # `agent-management` §Structure: artefacts whose primary
        # responsibility targets the Claude / Anthropic platform surface
        # MAY waive the ban when the body carries a
        # `## Reserved-token rationale` section.
        if "## Reserved-token rationale" in body:
            findings.append(Finding("Info", target, f"{kind}-management.frontmatter-name-reserved-exception",
                                    f"`name` `{name}` contains a reserved token; exception accepted via `## Reserved-token rationale` section in body"))
        else:
            findings.append(Finding("Critical", target, f"{kind}-management.frontmatter-name-reserved",
                                    f"`name` `{name}` contains a reserved token (`anthropic` / `claude`)"))
    if name.lower() in GENERIC_NAMES:
        findings.append(Finding("Critical", target, f"{kind}-management.frontmatter-name-generic",
                                f"`name` `{name}` is in the generic-names blocklist (defeats discovery)"))
    if name != expected_basename:
        findings.append(Finding("Critical", target, f"{kind}-management.frontmatter-name-filename",
                                f"`name` `{name}` does not match expected basename `{expected_basename}`"))
    return findings


def check_name_form(name: str | None, target: str, kind: str) -> list[Finding]:
    """Suggestion-grade name-form check.

    Skills are `<object-noun>-<action>`; agents are `<subject>-<role-noun>`
    (normative owner: `spec/claude/skill-agent-naming/`; the closed lists here
    mirror that spec and change with it in the same PR).
    Never emits Critical: a form deviation is a discoverability smell, not a
    platform-validator failure. Names in the closed per-kind exception lists are
    silent; the lists themselves are the audit trail.
    """
    if not name:
        return []
    last = name.rsplit("-", 1)[-1]
    if kind == "skill":
        if name in SKILL_NAME_FORM_EXCEPTIONS or last in SKILL_ACTION_TOKENS:
            return []
        return [Finding(
            "Suggestion", target, "skill-management.name-form",
            f"`name` `{name}` does not end in a known action token "
            f"(`<object-noun>-<action>`, e.g. `…-apply`); if `{last}` is a "
            f"legitimate action, add it to SKILL_ACTION_TOKENS, otherwise rename "
            f"or record a closed exception (skill-management §Frontmatter validation)",
        )]
    if name in AGENT_NAME_FORM_EXCEPTIONS or last in AGENT_ROLE_NOUNS \
            or last.endswith(AGENT_ROLE_SUFFIXES):
        return []
    return [Finding(
        "Suggestion", target, "agent-management.name-form",
        f"`name` `{name}` does not end in a role noun "
        f"(`<subject>-<role-noun>`, e.g. `…-reviewer`); if `{last}` names an "
        f"actor role, add it to AGENT_ROLE_NOUNS, otherwise rename or record a "
        f"closed exception (agent-management §Structure)",
    )]


def check_description(desc: str | None, target: str, kind: str) -> list[Finding]:
    findings: list[Finding] = []
    if desc is None:
        findings.append(Finding("Critical", target, f"{kind}-management.frontmatter-description-missing",
                                "frontmatter `description` is missing"))
        return findings
    if len(desc) == 0:
        findings.append(Finding("Critical", target, f"{kind}-management.frontmatter-description-empty",
                                "frontmatter `description` is empty"))
    if len(desc) > 1024:
        findings.append(Finding("Critical", target, f"{kind}-management.frontmatter-description-cap",
                                f"`description` length {len(desc)} exceeds the 1024-character platform cap"))
    for m in XML_TAG_RE.finditer(desc):
        if m.group(2) in HTML_TAG_NAMES:
            findings.append(Finding("Critical", target, f"{kind}-management.frontmatter-description-xml",
                                    f"`description` contains an HTML tag (`{m.group(0)}`)"))
            break  # one finding per description is enough
    # Apply the third-person check on author-voice text only: strip every
    # double-quoted span (operator-voice trigger phrases, sample requests)
    # before the search so quoted `I`/`you`/`our` does not fire.
    author_voice = QUOTED_SPAN_RE.sub(" ", desc)
    pron_match = FORBIDDEN_PRONOUNS_RE.search(author_voice)
    if pron_match:
        findings.append(Finding("Critical", target, f"{kind}-management.frontmatter-description-third-person",
                                f"`description` contains the non-third-person token `{pron_match.group(0)}` in author voice"))
    return findings


def check_tags(tags: list[str] | None, target: str, kind: str) -> list[Finding]:
    findings: list[Finding] = []
    if tags is None:
        if kind == "agent":
            findings.append(Finding("Suggestion", target, f"{kind}-management.frontmatter-tags-missing",
                                    "no `tags` field; consider adding 1–2 starter-vocabulary tags"))
        return findings
    if len(tags) > 5:
        findings.append(Finding("Critical", target, f"{kind}-management.frontmatter-tags-too-many",
                                f"`tags` contains {len(tags)} entries; max 5"))
    for t in tags:
        if len(t) > 30:
            findings.append(Finding("Critical", target, f"{kind}-management.frontmatter-tags-length",
                                    f"tag `{t}` is {len(t)} chars; max 30"))
        if not NAME_RE.match(t):
            findings.append(Finding("Critical", target, f"{kind}-management.frontmatter-tags-charset",
                                    f"tag `{t}` is not lowercase ASCII kebab-case"))
    out_of_starter = [t for t in tags if t not in STARTER_TAGS]
    if out_of_starter:
        findings.append(Finding("Warning", target, f"{kind}-management.tag-vocabulary",
                                f"tags outside the starter vocabulary: {out_of_starter}"))
    return findings


def check_when_to_use(desc: str | None, when_to_use: str | None, target: str, kind: str) -> list[Finding]:
    if not when_to_use or not desc:
        return []
    if len(desc) + len(when_to_use) > 1536:
        return [Finding("Warning", target, f"{kind}-management.frontmatter-when-to-use-cap",
                        f"`description` + `when_to_use` combined length {len(desc) + len(when_to_use)} exceeds 1536-char runtime cap")]
    return []


def check_distribution(distribution: str | None, target: str) -> list[Finding]:
    if distribution is None:
        return [Finding("Critical", target, "agent-management.frontmatter-distribution-missing",
                        "agent has no `distribution` field; must be exactly `plugin` or `project`")]
    if distribution not in ("plugin", "project"):
        return [Finding("Critical", target, "agent-management.frontmatter-distribution-value",
                        f"`distribution` is `{distribution}`; must be exactly `plugin` or `project`")]
    return []


# Closed phase vocabulary per spec/claude/skill-agent-catalog/ §Phase classification.
PHASE_VOCABULARY = frozenset({
    "vision", "plan", "design", "build", "review", "quality", "close-release", "cross-cutting",
})


def check_phase(phase: str | None, target: str, kind: str) -> list[Finding]:
    if phase is None or phase == "":
        return [Finding("Critical", target, f"{kind}-management.frontmatter-phase-missing",
                        f"frontmatter `phase` is missing; expected one of {sorted(PHASE_VOCABULARY)}")]
    if phase not in PHASE_VOCABULARY:
        return [Finding("Critical", target, f"{kind}-management.frontmatter-phase-value",
                        f"`phase` value `{phase}` is not in the closed vocabulary {sorted(PHASE_VOCABULARY)}")]
    return []


def _split_body(text: str) -> str:
    """Return the markdown body (everything after the closing `---` of the frontmatter)."""
    parts = text.split("---", 2)
    return parts[2] if len(parts) >= 3 else text


def check_resumable_wiring(
    resumable: str | None,
    description: str | None,
    name: str | None,
    body: str,
    target: str,
    kind: str,
) -> list[Finding]:
    """Guard the resume contract from spec/claude/resumable-work/.

    A `resumable: true` declaration that the body never backs with a concrete
    `.resume/<name>/` checkpoint instruction is exactly the failure that left the
    convention inert (41 skills declared it, zero ever wrote a file). This is the
    static, regression-catching slice: it cannot prove a checkpoint *fires* at
    runtime (the spec notes that has no post-hoc observable — that is the
    behavioural eval's job), but it refuses a flag with no wiring behind it.
    """
    findings: list[Finding] = []
    if (resumable or "").strip().lower() != "true":
        return findings

    expected_path = f".resume/{name}/" if name else ".resume/"
    if expected_path not in body and ".resume/" not in body:
        findings.append(Finding(
            "Critical", target, f"{kind}-management.resumable-no-persistence",
            f"frontmatter declares `resumable: true` but the body never references "
            f"`{expected_path}` per spec/claude/resumable-work/ §Persistence location",
        ))

    if "resume" not in (description or "").lower():
        findings.append(Finding(
            "Critical", target, f"{kind}-management.resumable-description-silent",
            "`resumable: true` requires a resume clause in `description` "
            "(spec/claude/resumable-work/ §Scope of applicability)",
        ))

    if not re.search(r"start-new|discard|resume detection|on re-invocation", body, re.I):
        findings.append(Finding(
            "Warning", target, f"{kind}-management.resumable-no-detection",
            "`resumable: true` body has no resume-detection step "
            "(expected `resume / start-new / discard` prompt on re-invocation)",
        ))
    return findings


def check_frontmatter_yaml(text: str, target: str, kind: str) -> list[Finding]:
    """Parse the frontmatter block with a standard YAML parser.

    `parse_frontmatter` above is deliberately lenient (regex, tolerant of `: `
    inside unquoted scalars) so the other checks always get their values. But the
    Claude Code runtime loader (js-yaml) and every spec-mandated tool
    (`skill-agent-catalog/en.md:127` — the catalog generator MUST use a standard
    YAML parser) apply *strict* YAML: an unquoted `description:` whose value
    embeds `: ` (a colon-space, e.g. `Read-only: reports…` or `` `status: planned` ``)
    is a mapping-indicator and makes the whole block unparseable. Such a skill may
    silently fail to load in a consumer. This check is the regression guard for
    that class: strict parse failure = Critical.
    """
    if yaml is None or not text.startswith("---"):
        return []
    parts = text.split("---", 2)
    if len(parts) < 3:
        return []
    try:
        yaml.safe_load(parts[1])
    except yaml.YAMLError as exc:  # noqa: BLE001 - any YAML error is a hard fail
        detail = str(getattr(exc, "problem", None) or exc).strip().splitlines()[0]
        return [Finding(
            "Critical", target, f"{kind}-management.frontmatter-yaml-invalid",
            f"frontmatter is not valid YAML ({detail}); a standard parser rejects it "
            f"— quote any scalar value that embeds `: ` (colon-space)",
        )]
    return []


# Body-size hard cap per skill-management/en.md §96,138: SKILL.md body ≤ 5,000
# tokens (AND ≤ 500 lines). Token count is estimated with the spec's 4-char/token
# heuristic. The ≥5,000 band names a MUST violation and is emitted at Critical:
# the T2 backlog of pre-existing over-cap skills (tracked in the 2026-07-01
# skills/agents sweep) has been split into references/, so the cap is now
# enforcing — a SKILL.md body crossing 5,000 est. tokens fails CI. The 4,500–4,999
# band stays a Warning (advisory headroom before the hard cap).
BODY_TOKEN_WARN = 4500
BODY_TOKEN_CAP = 5000
BODY_TOKEN_CAP_SEVERITY = "Critical"


def check_body_token_estimate(body: str, target: str, kind: str) -> list[Finding]:
    """Estimate the SKILL.md body token count and flag the 5,000-token hard cap.

    Content beyond ~5,000 tokens is silently truncated on re-attach after
    compaction — typically the Hard rules / Gotchas at the end. The estimate uses
    the spec's 4-char/token heuristic; it is intentionally approximate, so the
    4,500-token Warning band gives headroom before the enforcing 5,000-token
    Critical cap (BODY_TOKEN_CAP_SEVERITY).
    """
    est = len(body) // 4
    if est >= BODY_TOKEN_CAP:
        return [Finding(
            BODY_TOKEN_CAP_SEVERITY, target, f"{kind}-management.body-token-cap",
            f"body ~{est} tokens (est., 4-char heuristic) exceeds the 5,000-token "
            f"hard cap; split detail into references/ (skill-management §Body size)",
        )]
    if est >= BODY_TOKEN_WARN:
        return [Finding(
            "Warning", target, f"{kind}-management.body-token-approaching",
            f"body ~{est} tokens (est., 4-char heuristic) is approaching the "
            f"5,000-token hard cap; consider moving detail into references/",
        )]
    return []


# Use-case-metadata field limits enforced by the catalog generator
# (scripts/docs/gen_catalog.py). gen_catalog aborts `mkdocs build` (the `docs`
# and `links` CI jobs) when a field crosses these, so mirroring them here catches
# the violation in the fast local validator / pre-commit rather than only in the
# docs build. Kept in sync with gen_catalog's SUMMARY_MAX_LEN / USE_WHEN_* /
# DONT_USE_WHEN_* / SEE_ALSO_MAX_ENTRIES / EXAMPLES_* constants.
SUMMARY_MAX_LEN = 200
USE_WHEN_MAX_LEN = 120
USE_WHEN_MAX_ENTRIES = 6
DONT_USE_WHEN_SITUATION_MAX_LEN = 120
DONT_USE_WHEN_MAX_ENTRIES = 6
SEE_ALSO_MAX_ENTRIES = 8
EXAMPLES_MAX_ENTRIES = 4
EXAMPLES_FIELD_MAX_LEN = 200


def check_use_case_field_lengths(text: str, target: str, kind: str) -> list[Finding]:
    """Mirror the catalog generator's use-case-metadata field caps.

    Because the frontmatter is guaranteed valid YAML by `check_frontmatter_yaml`,
    it can be `safe_load`ed and inspected structurally. Each cap here matches a
    `gen_catalog.py` limit whose violation aborts `mkdocs build` (fatal in CI);
    emitting Critical keeps the local signal aligned with that hard failure.
    """
    if yaml is None or not text.startswith("---"):
        return []
    parts = text.split("---", 2)
    if len(parts) < 3:
        return []
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return []  # already reported by check_frontmatter_yaml
    if not isinstance(data, dict):
        return []
    rule = f"{kind}-management.frontmatter-use-case-field"
    findings: list[Finding] = []

    # gen_catalog measures the *stripped* value (raw.strip()); mirror that so a
    # value that is within the cap after stripping trailing whitespace is not a
    # local-only false positive.
    for key, value in data.items():
        if (key == "summary" or key.startswith("summary_")) and isinstance(value, str) and len(value.strip()) > SUMMARY_MAX_LEN:
            findings.append(Finding("Critical", target, rule,
                f"`{key}` is {len(value.strip())} characters; catalog limit is {SUMMARY_MAX_LEN}"))

    uw = data.get("use_when")
    if isinstance(uw, list):
        if len(uw) > USE_WHEN_MAX_ENTRIES:
            findings.append(Finding("Critical", target, rule,
                f"`use_when` has {len(uw)} entries; catalog limit is {USE_WHEN_MAX_ENTRIES}"))
        for i, entry in enumerate(uw):
            if isinstance(entry, str) and len(entry.strip()) > USE_WHEN_MAX_LEN:
                findings.append(Finding("Critical", target, rule,
                    f"`use_when[{i}]` is {len(entry.strip())} characters; catalog limit is {USE_WHEN_MAX_LEN}"))

    dw = data.get("dont_use_when")
    if isinstance(dw, list):
        if len(dw) > DONT_USE_WHEN_MAX_ENTRIES:
            findings.append(Finding("Critical", target, rule,
                f"`dont_use_when` has {len(dw)} entries; catalog limit is {DONT_USE_WHEN_MAX_ENTRIES}"))
        for i, entry in enumerate(dw):
            situation = entry.get("situation") if isinstance(entry, dict) else None
            if isinstance(situation, str) and len(situation.strip()) > DONT_USE_WHEN_SITUATION_MAX_LEN:
                findings.append(Finding("Critical", target, rule,
                    f"`dont_use_when[{i}].situation` is {len(situation.strip())} characters; catalog limit is {DONT_USE_WHEN_SITUATION_MAX_LEN}"))

    sa = data.get("see_also")
    if isinstance(sa, list) and len(sa) > SEE_ALSO_MAX_ENTRIES:
        findings.append(Finding("Critical", target, rule,
            f"`see_also` has {len(sa)} entries; catalog limit is {SEE_ALSO_MAX_ENTRIES}"))

    ex = data.get("examples")
    if isinstance(ex, list):
        if len(ex) > EXAMPLES_MAX_ENTRIES:
            findings.append(Finding("Critical", target, rule,
                f"`examples` has {len(ex)} entries; catalog limit is {EXAMPLES_MAX_ENTRIES}"))
        for i, entry in enumerate(ex):
            if isinstance(entry, dict):
                for fk, fv in entry.items():
                    if isinstance(fv, str) and len(fv.strip()) > EXAMPLES_FIELD_MAX_LEN:
                        findings.append(Finding("Critical", target, rule,
                            f"`examples[{i}].{fk}` is {len(fv.strip())} characters; catalog limit is {EXAMPLES_FIELD_MAX_LEN}"))

    return findings




# --- 2026-07 audit guards (WP-B6) -----------------------------------------

RATIONALE_HEADINGS = {
    "skill": "## Why this is a skill, not an agent",
    "agent": "## Why this is an agent, not a skill",
}
# Sanctioned nominal description leads that are third-person without a verb.
NOMINAL_LEAD_PREFIXES = (
    "Read-only", "Top-level", "Whole-picture", "Bilingual",
    # role-noun / participle leads that are third-person without an -s verb
    "Senior", "Given",
)
DESCRIPTION_HEADROOM_CHARS = 975  # 95% of the 1024 platform cap


def check_rationale_heading(body: str, target: str, kind: str) -> list[Finding]:
    """Exact-wording rationale heading per `skill-vs-agent` §Rationale section heading.

    The heading is a MUST with fixed wording because grep-based portfolio
    audits key on the exact string; variants defeat them silently.
    """
    heading = RATIONALE_HEADINGS[kind]
    if re.search(rf"^{re.escape(heading)}\s*$", body, re.MULTILINE):
        return []
    return [Finding(
        "Critical", target, f"{kind}-management.rationale-heading-missing",
        f"body lacks the exact rationale heading `{heading}` "
        "(skill-vs-agent §Rationale section heading)")]


def check_description_lead_voice(desc: str | None, target: str, kind: str) -> list[Finding]:
    """Heuristic third-person lead-verb check (imperative-description detector).

    The pronoun gate misses imperative leads ("Audit the..." instead of
    "Audits the..."). Heuristic: the first word of the description should be
    a third-person-singular verb (ends in `s`) or a sanctioned nominal lead.
    Warning severity: a heuristic, not a platform rule.
    """
    if not desc:
        return []
    first = desc.split(" ", 1)[0].strip('"')
    if not first or not first[0].isupper():
        return []
    if first.startswith(NOMINAL_LEAD_PREFIXES):
        return []
    if not first.isalpha() or first.endswith("s"):
        return []
    # Adverb-led third person ("Visually reviews ..."): pass when the second
    # word carries the -s verb instead.
    rest = desc.split(" ", 2)
    if len(rest) > 1 and rest[1].strip('"').endswith("s"):
        return []
    return [Finding(
        "Warning", target, f"{kind}-management.frontmatter-description-lead-voice",
        f"`description` opens with `{first}` — reads as imperative; use the "
        f"third-person form (`{first}s ...`) or a sanctioned nominal lead")]


def check_description_headroom(desc: str | None, target: str, kind: str) -> list[Finding]:
    """Early-warning headroom hint below the hard 1024 cap (R-9 guardrail)."""
    if not desc or len(desc) > 1024 or len(desc) < DESCRIPTION_HEADROOM_CHARS:
        return []
    return [Finding(
        "Info", target, f"{kind}-management.frontmatter-description-headroom",
        f"`description` length {len(desc)} is within 5% of the 1024 cap; "
        "trim on the next edit before an addition breaks the MUST")]


def _tools_list(tools) -> list[str]:
    if tools is None:
        return []
    if isinstance(tools, list):
        return [str(t).strip() for t in tools]
    return [t.strip() for t in str(tools).split(",") if t.strip()]


def check_bash_justification(tools, desc: str | None, body: str, target: str) -> list[Finding]:
    """Agents holding `Bash` carry a greppable justification heading.

    Read-only-shaped agents (description leads with "Read-only" or names a
    read-only responsibility) require `## Read-only Bash justification`
    (agent-management §Tool access narrow exception — a MUST, so Critical).
    Write-capable agents document shell usage under the neutral
    `## Bash justification` (a convention, so Warning when absent).
    """
    if "Bash" not in _tools_list(tools):
        return []
    has_ro = bool(re.search(r"^## Read-only Bash justification\s*$", body, re.MULTILINE))
    has_neutral = bool(re.search(r"^## Bash justification\s*$", body, re.MULTILINE))
    if has_ro or has_neutral:
        return []
    read_only_shaped = bool(re.search(r"\bread-only\b", (desc or ""), re.IGNORECASE))
    if read_only_shaped:
        return [Finding(
            "Critical", target, "agent-management.bash-justification-missing",
            "read-only agent declares `Bash` without a `## Read-only Bash "
            "justification` section (agent-management §Tool access)")]
    return [Finding(
        "Warning", target, "agent-management.bash-justification-missing",
        "write-capable agent declares `Bash` without a `## Bash justification` "
        "section naming its command envelope (agent-management §Tool access)")]


def check_skill(path: Path) -> list[Finding]:
    rel = path.relative_to(REPO).as_posix()
    text = path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    if fm is None:
        return [Finding("Critical", rel, "skill-management.frontmatter-missing", "no YAML frontmatter")]
    expected_name = path.parent.name
    body = _split_body(text)
    findings = []
    findings += check_frontmatter_yaml(text, rel, "skill")
    findings += check_use_case_field_lengths(text, rel, "skill")
    findings += check_body_token_estimate(body, rel, "skill")
    findings += check_name(fm.get("name"), rel, "skill", expected_name, body)
    findings += check_name_form(fm.get("name"), rel, "skill")
    findings += check_description(fm.get("description"), rel, "skill")
    findings += check_tags(fm.get("tags"), rel, "skill")
    findings += check_phase(fm.get("phase"), rel, "skill")
    findings += check_when_to_use(fm.get("description"), fm.get("when_to_use"), rel, "skill")
    findings += check_resumable_wiring(
        fm.get("resumable"), fm.get("description"), fm.get("name"), body, rel, "skill")
    findings += check_rationale_heading(body, rel, "skill")
    findings += check_description_lead_voice(fm.get("description"), rel, "skill")
    findings += check_description_headroom(fm.get("description"), rel, "skill")
    return findings


def check_agent(path: Path) -> list[Finding]:
    rel = path.relative_to(REPO).as_posix()
    text = path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    if fm is None:
        return [Finding("Critical", rel, "agent-management.frontmatter-missing", "no YAML frontmatter")]
    expected_name = path.stem
    body = _split_body(text)
    findings = []
    findings += check_frontmatter_yaml(text, rel, "agent")
    findings += check_use_case_field_lengths(text, rel, "agent")
    findings += check_name(fm.get("name"), rel, "agent", expected_name, body)
    findings += check_name_form(fm.get("name"), rel, "agent")
    findings += check_description(fm.get("description"), rel, "agent")
    findings += check_tags(fm.get("tags"), rel, "agent")
    findings += check_distribution(fm.get("distribution"), rel)
    findings += check_phase(fm.get("phase"), rel, "agent")
    findings += check_resumable_wiring(
        fm.get("resumable"), fm.get("description"), fm.get("name"), body, rel, "agent")
    findings += check_rationale_heading(body, rel, "agent")
    findings += check_description_lead_voice(fm.get("description"), rel, "agent")
    findings += check_description_headroom(fm.get("description"), rel, "agent")
    findings += check_bash_justification(fm.get("tools"), fm.get("description"), body, rel)
    return findings


def check_agent_tree(agents_dir: Path) -> list[Finding]:
    """Flag any markdown nested under `agents/<name>/`.

    Per `spec/claude/agent-management/` §Structure an agent is exactly one
    top-level file `agents/<name>.md`. Claude Code's default agent discovery
    scans `agents/` *recursively*, so a companion markdown file in a sibling
    folder is registered as a phantom, scope-prefixed agent (`<name>:<file>`)
    that — lacking frontmatter — inherits the full tool surface with no `tools`
    restriction. Supporting assets that cannot be inlined live outside the
    `agents/` tree (for example `agent-assets/<name>/`).
    """
    findings: list[Finding] = []
    for md in sorted(agents_dir.rglob("*.md")):
        if md.parent == agents_dir:
            continue  # top-level agent file — the only legitimate shape
        rel = md.relative_to(REPO).as_posix()
        findings.append(Finding(
            "Critical", rel, "agent-management.nested-companion-markdown",
            "markdown nested under agents/ is registered as a phantom all-tools "
            "agent by recursive discovery; inline it into the agent body or move "
            "it outside the agents/ tree (agent-management §Structure)",
        ))
    return findings


# Per-plugin agent-description routing-budget guardrail (R-9 / sprint 0005).
# Claude Code loads every agent `description` into its ~15k-token agent-routing
# budget on every turn, and a consumer installing these plugins inherits that
# weight. This gate freezes the F-7 post-remediation baseline per plugin so the
# aggregate cannot silently creep back toward the ceiling. Metric: the 4-char/
# token estimate (len(concat) // 4) over the concatenated `description` of every
# agent under a plugin's agents/ root — the single method fixed in F-5 and reused
# by check_body_token_estimate. Baseline chars are recorded in
# the F-7 remediation record (git history; re-baselined per PR #438); raising
# one requires re-measuring and updating both places with a recorded rationale.
AGENT_DESC_BUDGET_HEADROOM = 0.15  # +15% slack for legitimately-added agents
# key = agents/ dir relative to REPO ; value = post-remediation baseline chars (F-7)
AGENT_DESC_BASELINE_CHARS = {
    "agents": 11065,                          # nolte-shared (22 agents; claude-plugin-developer carved out to nolte-claude-dev 2026-07-22, F-18 flip)
    "plugins/nolte-claude-dev/agents": 386,    # nolte-claude-dev (1 agent: claude-plugin-developer)
    "plugins/nolte-engineering/agents": 21869,  # nolte-engineering (37 agents; re-baselined 2026-08-01: error-tracking-audit-scanner added, #516 — the 2026-07-24 baseline of 30 agents had 159 chars of headroom left, so a deliberate new capability tripped a gate meant to catch regression, not growth; platform-wide agent-description weight across all four plugins is ~8.6k est. tokens against the ~15k routing budget)
    "plugins/nolte-media/agents": 1108,        # nolte-media (2 agents)
}


def check_agent_description_budget(agents_dir: Path) -> list[Finding]:
    """Fail when a plugin's aggregate agent-`description` weight exceeds its
    frozen R-9 ceiling (baseline + headroom). Reuses the 4-char/token estimate.

    A plugin without a recorded baseline is not gated (returns no findings), so a
    newly-added plugin doesn't fail closed before its baseline is captured.
    """
    key = agents_dir.relative_to(REPO).as_posix()
    baseline = AGENT_DESC_BASELINE_CHARS.get(key)
    if baseline is None:
        return []
    concat = "".join(
        ((parse_frontmatter(md.read_text(encoding="utf-8")) or {}).get("description") or "")
        for md in sorted(agents_dir.glob("*.md"))
    )
    ceiling = int(baseline * (1 + AGENT_DESC_BUDGET_HEADROOM))
    if len(concat) > ceiling:
        return [Finding(
            "Critical", key, "agent-management.description-budget-regression",
            f"aggregate agent `description` weight {len(concat)} chars "
            f"(~{len(concat) // 4} est. tokens) exceeds the frozen R-9 ceiling "
            f"{ceiling} chars (~{ceiling // 4} tokens = baseline {baseline} + "
            f"{int(AGENT_DESC_BUDGET_HEADROOM * 100)}% headroom); trim descriptions "
            f"to agent-management §Description contract, or raise the baseline in "
            f"AGENT_DESC_BASELINE_CHARS and the post-remediation-baseline artefact "
            f"with a recorded rationale",
        )]
    return []


def discover_default_targets() -> list[str]:
    """Default scan scope: the root plugin's skills/ + agents/, plus every
    in-repo plugin under plugins/<name>/ that ships a skills/ or agents/ tree.
    Keeps `task test` and CI (which call this script with no arguments) covering
    every plugin in a multi-plugin repo without per-plugin wiring."""
    targets = ["skills/", "agents/"]
    plugins_dir = REPO / "plugins"
    if plugins_dir.is_dir():
        for plugin in sorted(plugins_dir.iterdir()):
            if not plugin.is_dir():
                continue
            for sub in ("skills", "agents"):
                if (plugin / sub).is_dir():
                    targets.append(f"plugins/{plugin.name}/{sub}/")
    return targets


def main() -> int:
    targets = sys.argv[1:] or discover_default_targets()
    paths: list[Path] = []
    for t in targets:
        p = REPO / t
        if not p.exists():
            print(f"ERROR: path not found: {p}", file=sys.stderr)
            return 2
        if p.is_dir():
            if "skills" in p.parts:
                paths.extend(sorted(p.rglob("SKILL.md")))
            elif "agents" in p.parts:
                paths.extend(sorted(p.glob("*.md")))
            else:
                paths.extend(sorted(p.rglob("SKILL.md")))
                paths.extend(sorted(p.glob("*.md")))
        else:
            paths.append(p)

    all_findings: list[Finding] = []
    for path in paths:
        rel = path.relative_to(REPO).as_posix()
        # Classify by path segment, not a root-anchored prefix, so a skill or
        # agent living under an in-repo plugin root (plugins/<name>/skills/...,
        # plugins/<name>/agents/...) is validated exactly like the root plugin's.
        if path.name == "SKILL.md" and path.parent.parent.name == "skills":
            all_findings.extend(check_skill(path))
        elif path.suffix == ".md" and path.parent.name == "agents":
            all_findings.extend(check_agent(path))

    # Phantom-agent leak scan: the per-file glob above only visits top-level
    # `agents/*.md`, so nested companion markdown would slip through. Run the
    # recursive tree check over every agents/ tree in scope — the root plugin's
    # and each in-repo plugin's (plugins/<name>/agents/).
    for t in targets:
        p = REPO / t
        if p.is_dir() and p.name == "agents":
            all_findings.extend(check_agent_tree(p))
            all_findings.extend(check_agent_description_budget(p))

    if not all_findings:
        print(f"validate_skills: {len(paths)} artifacts checked, no findings")
        return 0

    by_severity = {"Critical": 0, "Warning": 0, "Suggestion": 0, "Info": 0}
    for f in all_findings:
        by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
        print(f)

    print(
        f"\nvalidate_skills: {len(paths)} artifacts; "
        f"{by_severity['Critical']}C / {by_severity['Warning']}W / "
        f"{by_severity['Suggestion']}S / {by_severity['Info']}I",
        file=sys.stderr,
    )
    return 1 if by_severity["Critical"] else 0


if __name__ == "__main__":
    sys.exit(main())
