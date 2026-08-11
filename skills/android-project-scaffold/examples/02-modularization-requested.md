# Example 02 — Modularization requested with a concrete trigger

**Prompt:** "Scaffold a new Android app, and set it up modularized — we already share a design system with a second app."

**Expected behavior:**

1. Parameter gate: the operator names a recognized trigger (code reuse across apps). The skill records the trigger and intended split, then confirms a modularized layout instead of the single-module default.
2. File-plan gate: blueprint shows `:app` / `:feature:*` / `:core:*` with a `build-logic/` included build of single-responsibility convention plugins (`<project>.<platform>.<module-type>`), `:core:designsystem` split from `:core:ui`, Hilt DI, and `:core:testing` for shared fixtures.
3. Write + verify as in Example 01, with the dependency rules enforced (features never depend on other features' implementations; core never depends on feature/app; no cycles).

**Pass criteria:** modularization only because a concrete trigger was stated; `build-logic/` included build (not a monolithic `buildSrc`); the `:feature:x:api`/`:impl` split is NOT applied (project is not large); module graph honors every §C dependency rule.
