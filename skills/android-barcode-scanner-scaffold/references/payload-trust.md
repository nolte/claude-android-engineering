# Payload trust boundary

What must happen to a decoded value before anything acts on it, and how to generate a code that
the app's own scanners can read. Grounded in `spec/android/barcode-scanning/` §F and §I; on any
conflict that spec wins.

The premise: **a scanner is an input channel from a stranger.** Whoever printed the sticker
chooses the bytes, and a printed sticker is a lower bar for an attacker than a crafted link.
Every rule here treats the decoded payload the way `spec/android/security/` §D/§F treats IPC and
network input.

## Table of contents

- [1. The boundary](#1-the-boundary)
- [2. Payload classes](#2-payload-classes)
- [3. URL validation](#3-url-validation)
- [4. Rejection behaviour](#4-rejection-behaviour)
- [5. Generating a readable code](#5-generating-a-readable-code)
- [6. Test fixtures](#6-test-fixtures)
- [Logging a payload](#logging-a-payload)

## 1. The boundary

Three rules, in order. Nothing downstream is safe if any is skipped.

1. **Show, then act.** The decoded destination is displayed and an explicit user action is
   required before anything happens. The value itself, not a summary of it — the user is being
   asked to judge it. Consumer-protection guidance is to inspect the URL before opening it,
   which an app can only make possible by showing it.
2. **Nothing auto-executes.** No placing a call, no sending an SMS, no joining a network, no
   submitting a form, no starting a payment.
3. **Nothing reaches an interpreter.** Not SQL, not a shell, not HTML, not a WebView `loadUrl`,
   not an unencoded URL path or query component, and not `Intent.parseUri`.

Bound the payload before it is stored, rendered, or transmitted. A QR symbol carries up to
2,953 bytes in byte mode at version 40 — enough to break a field that expected an identifier.
No source documents an oversized-payload denial-of-service class for scanners, so this bound is
a defensive default rather than a cited mitigation; say so rather than overclaiming.

## 2. Payload classes

Branch on `valueType`, then apply the class rule. A structure that parsed cleanly is still
untrusted.

> **Spec-extension proposed (REQ-6).** `spec/android/barcode-scanning/` §F fixes the boundary
> (show-then-act, no auto-execute, no interpreter, URL rules) and names `tel:`/`WIFI:`/URL
> explicitly; the per-class rules for `sms:`, contact/calendar, plain text, and product/ISBN
> below are this skill's operationalization and are not yet spec text. Apply them, and record
> in the run report that they rest on a proposed §F extension rather than on a spec bullet.

| Class | Rule |
|---|---|
| URL | §3 below. Never navigate without the confirmation surface. |
| `tel:` | `ACTION_DIAL` only — it shows the dialer and lets the user initiate the call. **Never** `ACTION_CALL`, which dials directly and requires `CALL_PHONE`. |
| `sms:` | Compose only; never send. Show recipient and body. |
| `WIFI:` | Never join without a confirmation showing the SSID. The format is a de-facto ZXing convention, not a standard, and carries the password in plaintext inside the code. Where the project controls provisioning, prefer Wi-Fi Easy Connect (DPP) — Android's own QR provisioning path, cryptographically secured rather than password-bearing. |
| Contact / calendar | Never write to the user's data silently; hand to the platform picker with the parsed values pre-filled and let the user confirm. |
| Plain text | Bound the length, escape at every render site, and never treat it as a command or an identifier without validating against the expected shape. |
| Product / ISBN | Validate the shape before a lookup; a lookup is a network call carrying attacker-chosen input. |

## 3. URL validation

Apply all four; the first three are cheap and the fourth is where most real attacks land.

1. **Scheme allowlist.** `https` for web content. Reject `javascript:`, `file:`, `content:`, and
   `intent:` outright.
2. **Host check by exact match** wherever the app claims the destination as its own.
3. **Render the form the user will actually see.** IDN and punycode handling must not be assumed
   to be done for the app by the platform — a homograph host that renders as a familiar name is
   the whole point of the attack.
4. **Own-domain destinations go through verified App Links** (`android:autoVerify` with
   `assetlinks.json`) so the OS resolves the target instead of the app trusting a string. This is
   deliberately stricter than the general SHOULD in `spec/android/app-design-navigation/` §E:
   there the origin is the platform, here it is whoever printed the code.

**URL shorteners** are not inspectable destinations — the shortened form defeats the user's
inspection step. Either resolve it server-side under the app's control before showing it, or
present it as unverifiable. Do not silently follow it.

## 4. Rejection behaviour

A rejected payload is a designed state, not a crash and not a silent ignore:

- Say what was scanned and why it was not accepted, in the error-wording style of
  `spec/android/app-design-navigation/` §F — no blame, no raw exception text as the primary
  message.
- Offer the next action: scan again, enter manually, or cancel.
- Never log the raw payload where `spec/android/security/` §A forbids it, and never echo it into
  a rendered surface without escaping.

## 5. Generating a readable code

The load-bearing trap first: **encoding UTF-8 correctly requires an ECI designator, and ML Kit
does not recognize ECI-mode QR codes at all.** A code encoded "properly" for non-Latin text is
therefore unreadable by the scanner this skill builds. There is no construction that satisfies
both. Restrict the payload to characters that survive the default interpretation and record the
restriction, or record the conflict — never decide it silently.

- **Set the character set explicitly** (`EncodeHintType.CHARACTER_SET`) rather than inheriting
  the byte-mode default of ISO/IEC 8859-1.
- **Quiet zone:** ZXing's generic `EncodeHintType.MARGIN` documentation says "in pixels", but
  `QRCodeWriter` interprets it in **modules** (its `QUIET_ZONE_SIZE` default is 4), so the
  default already yields the required 4-module quiet zone for QR. Set
  `EncodeHintType.MARGIN` to `4` explicitly anyway and record the unit **at the definition
  site, in the writer's unit** — the unit is per writer (spec §I), not "pixels" and not
  "modules" in general: `QRCodeWriter` reads modules, the 1D writers scale the margin in their
  own narrow-bar (X) units before rendering, and neither is the javadoc's "pixels". A later
  change of writer or of default must not silently shrink the zone, and a value copied from a
  1D writer must never be read as a QR module count.
- **Error correction** (`EncodeHintType.ERROR_CORRECTION`) is a deliberate, recorded trade of
  capacity against damage tolerance. Only the 15 % figure at level M is stated by the
  symbology's originator; the 7 %/25 %/30 % figures for L/Q/H are widely repeated but were not
  traceable to primary text.
- **Render at whole-pixel module boundaries.** Producing a small bitmap and scaling it up with
  interpolation blurs module edges — a decode failure that looks like a rendering nicety. Draw
  per module, or use a vector renderer at display density.
- **Polarity survives theming.** Dark mode must not invert the symbol, and the quiet zone stays
  light even on a dark surface. Inversion is a decoder-side accommodation, not a symbology
  feature.
- **Logos:** never over a finder pattern. No standards body or the symbology's originator
  addresses overlay tolerance at all, so the only defensible construction is the highest error
  correction plus verification by actually scanning it — never a coverage percentage quoted as
  if it were normative.
- **Brightness:** when a code is displayed for another device to scan, raise it via the
  window-level `WindowManager.LayoutParams.screenBrightness` override (`1.0` forces maximum,
  `-1.0` restores system control) and restore it when the surface is left. There is no
  barcode-specific API for this.

## 6. Test fixtures

Generate these as real fixtures — a scanner verified only against a clean code on a bright
screen is not verified.

**Decodability:** a damaged code, a low-contrast one, one at the edge of the pixel budget, one
at an angle, and one at the intended scanning distance.

**Rejection paths:** a `javascript:` URL, a homograph/punycode host, a shortened URL, an
over-long payload, a `WIFI:` payload, and a `tel:` payload — each must reach the rejection or
confirmation state, never an action. (Spec §J names the `javascript:` URL, the over-long
payload, and the `WIFI:` payload; the homograph host, the shortened URL, and the `tel:` fixture
follow from §F's URL rules and are marked **spec-extension proposed (REQ-6)** — apply them and
say so in the report.)

**Permission paths:** granted, denied, and permanently denied (the last is the one that is
usually missed, and it is where the graceful-degradation requirement actually bites).

The emulator's virtual scene accepts an imported image, and the documentation names QR codes as
an intended use — that covers the mechanical layer. It does **not** evidence focus, low light,
distance, motion blur, or torch behaviour; those claims require a physical device and must be
recorded with the device and the capture resolution they were made at.

## Logging a payload

A decoded payload is user-supplied content, so `spec/android/logging/` §C forbids logging it —
not the raw value and not a truncated prefix. A scanned code can carry a credential, a personal
identifier, or a `WIFI:` password in plaintext, and a prefix is enough to leak the format plus the
first characters of a secret.

Log the *outcome* instead, which is what a diagnosis actually needs: the detected format, a length
bucket rather than the length itself, whether the payload was accepted or rejected, and which rule
rejected it. That keeps the rejection paths of this file debuggable without putting the content on
a shared resource other apps may read.
