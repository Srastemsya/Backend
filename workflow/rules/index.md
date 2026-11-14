# Rule routing
Read this index; load only rules relevant to the assigned role and task. Files here are explicit instructions, not Cursor glob/alwaysApply automation. New rules need a row with scope and roles; existing rules must be preserved and conflicts raised.

| File | Roles | Scope |
|---|---|---|
| testing.md | Developer, Tester | Test ownership and immutable evidence |
| [design.md](design.md) | Design, Developer | Figma sections, reusable components, color and gradient tokens, and frontend handoff documentation |
| [matchwear/backend-architecture.md](matchwear/backend-architecture.md) | Developer | Backend implementation |
| [matchwear/runtime-heal.md](matchwear/runtime-heal.md) | Developer | FastAPI readiness and Compose recovery |
| [matchwear/docs-with-code.md](matchwear/docs-with-code.md) | Developer | Backend API and event contracts |

PM receives a short checklist of applicable obligations and evidence, not all implementation rules. Tester may read behavioral requirements from architecture rules, but must not inspect implementation to verify them. Developer runs source-level compliance checks.
