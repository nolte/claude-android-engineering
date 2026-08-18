# Example 03 — Existing files and a red build

**Prompt:** "Bootstrap an Android app here" — run inside a directory that already contains a `settings.gradle.kts` and a partial `app/` module.

**Expected behavior:**

1. Preconditions detect the existing `settings.gradle.kts` and `app/`. The skill reports every collision and treats each as a per-file confirmation gate — it does **not** overwrite silently (REQ-8). It merges into existing config where possible rather than replacing wholesale.
2. Operator approves overwriting some files and declines others; the skill honors each choice and checkpoints the decisions.
3. Verify phase: `./gradlew build` comes back **red** (a leftover kapt application and an `org.jetbrains.kotlin.android` apply in the pre-existing `app/build.gradle.kts` — both incompatible with the AGP 9 built-in-Kotlin scaffold).
4. The skill reports the full failing task output, diagnoses the kapt residue against the blueprint, and proposes migrating it to KSP and dropping the Kotlin Android plugin (REQ-7 / REQ-9). It applies the fix only at the approval gate, then re-runs the verify sequence from `./gradlew build`.

**Pass criteria:** no file overwritten without confirmation; the red build is surfaced with its output, never swallowed; the proposed fix removes the outdated mechanism (kapt → KSP) rather than papering over it; the run is set `completed` only once the build is green.
