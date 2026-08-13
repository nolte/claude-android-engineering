# Backend-requirement artifact template

The handoff artifact for a capability the app needs and the backend does not yet provide, per
`spec/android/backend-contract/` §F. It lives in the **app** repository at
`project/backend-requirements/<YYYY-MM-DD>-<slug>.md` and is written in English, because its
reader is a backend specialist in another repository.

## Contents

1. [Rules that are easy to get wrong](#rules-that-are-easy-to-get-wrong)
2. [Template](#template)
3. [Status lifecycle](#status-lifecycle)
4. [Optional issue handoff](#optional-issue-handoff)

## Rules that are easy to get wrong

- The OpenAPI fragment is a **proposal**, never authoritative — the backend owns the final
  design. Say so in the artifact; a fragment presented as a decision invites either silent
  compliance or a rejected requirement.
- Every requested field carries its **rendering purpose**. A bare field list produces a backend
  design that satisfies the letter and misses the screen.
- Acceptance criteria are testable **from the backend side alone** — no criterion may require
  the app to be present.
- Examples are **synthetic**. No production personal data, no credentials, no real user
  identifiers.
- One artifact per capability. A second screen needing the same thing extends the existing
  artifact; it does not file a duplicate.
- The interim client path is written down **with the condition for its removal**, or it becomes
  permanent by accident.

## Template

````markdown
# BR-<n>: <capability in a few words>

Status: draft · Last transition: <YYYY-MM-DD>
App repository: <repo> · Contract version consumed: <version or commit>

## 1. Trigger

<Feature, screen, and the user step that produced the need. One short paragraph.>

## 2. Need

<One sentence, phrased as a capability the backend provides — not as an implementation.>

## 3. Consumer scenario

<What the app renders with the answer. Name the states it must be able to show: loading,
content, empty, and each error case it must distinguish. Say what the user does next.>

## 4. Proposed contract — **proposal, not authoritative**

The backend owns the final design. This fragment states what the client can consume.

```yaml
paths:
  /<resource>:
    get:
      parameters: []
      responses:
        "200":
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/<Model>"
        "422":
          description: <domain rejection the client must distinguish>
          content:
            application/problem+json:
              schema:
                $ref: "#/components/schemas/Problem"
components:
  schemas:
    <Model>:
      type: object
      required: [<field>]
      properties:
        <field>:
          type: <type>
          description: <what the app renders with it — the purpose, not the shape>
```

Error cases the client will distinguish, and how each is rendered:

| Condition | Expected status / problem `type` | Client rendering |
|---|---|---|
| <condition> | <status> / <type URI> | <state and recovery action> |

## 5. Non-functional needs

- Latency budget for the consuming screen: <value, and what the app shows past it>
- Expected page size, ordering, and pagination style: <cursor / offset, page size>
- Authentication scope required: <scope>
- Idempotency: <needed for which writes; `Idempotency-Key` honoured?>
- Cacheability: <validators the client can send: ETag / Last-Modified / sync token>
- Data volume and growth: <rough expectation>
- Urgency: <what is blocked without this capability, and by when the app needs it>

## 6. Acceptance criteria

- [ ] <Testable from the backend side alone>
- [ ] <…>

## 7. Interim client behaviour

<What the app does until this lands, and exactly what must be removed once it does. If the
answer is "the feature ships without this part", say that.>

Removal condition: <what makes the interim path deletable>

## 8. Open questions

- <Every point the app side could not decide.>

## 9. Status log

| Date | Status | Note |
|---|---|---|
| <YYYY-MM-DD> | draft | created during <feature> |
````

## Status lifecycle

`draft` → `proposed` → `accepted` → `implemented` → `consumed`

- **proposed** — handed to the backend side (artifact linked, issue optional)
- **accepted** — the backend agreed; record the contract version that will carry the change
- **implemented** — available in a released contract version
- **consumed** — the app uses it, the interim path is removed, and the artifact says so

An interim path that outlives its artifact's `consumed` transition is a defect; the status is
the tracking mechanism, so it is updated in the same change that consumes the capability.

## Optional issue handoff

Only after explicit operator confirmation (REQ-8):

```bash
gh issue create --repo <owner>/<backend-repo> \
  --title "API: <capability>" \
  --body-file <path to a body derived from the artifact>
```

The issue body is derived from sections 1–6 and links back to the artifact; the artifact stays
the source of truth. Record the issue URL in the artifact's status log.
