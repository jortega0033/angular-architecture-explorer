# CLAUDE.md

Instructions for Claude Code (and any other agent or engineer) working in this repository.

## What this repository is

Angular Architecture Explorer is a **Python standard-library web app** that analyses Angular-style TypeScript sources offline. It is **not an Angular project**: there is no `package.json`, no Node toolchain and no pip dependency. The runtime is Python 3.12+ (`http.server`, `sqlite3`) serving native HTML, CSS and JavaScript from the package.

Today it searches four bundled synthetic `.ts` fixtures and saves explorations. Importing a user-supplied snapshot, the versioned index, the route and import graph, traces and diagnostics are planned work (epic #1).

## Sources of truth

| Topic | Where |
|---|---|
| Product scope, API summary (§5), invariants (§6), check IDs `AE-C01`..`AE-C37` (§8) | [docs/PRD.md](docs/PRD.md) |
| Traced workflow, module boundaries, invariants with source lines, implemented / planned / needs-verification status, PRD drift | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Run, test and demo steps for users | [README.md](README.md) |
| Backlog | GitHub issues: epic #1 and its child issues #2 to #10 (linked as sub-issues; order and dependencies in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#backlog-map)). The PRD's "backlog" means these issues. |
| Agent roles and the triage loop | [docs/agents-and-loop.md](docs/agents-and-loop.md), [LOOP.md](LOOP.md) |

If code and a document disagree, the code and its tests describe current behaviour; fix the document in the same pull request or record the drift in `docs/ARCHITECTURE.md`.

## Setup and commands

There is no install step. Use `python` (Windows) or `python3` (Linux, when `python` is absent).

| Purpose | Command | Last observed |
|---|---|---|
| Unit and API suite | `python -m unittest discover -s tests -v` | 2026-11-22, Windows 11, Python 3.13.14: 28 tests, OK, about 16 s |
| Run the app | `python -m architecture_explorer --data-dir ./demo-data --port 8765` | Prints `Serving on http://127.0.0.1:8765`; `GET /` returns 200 |
| Health probe | `curl http://127.0.0.1:8765/api/v1/health` | `{"status": "ok", "version": "0.1.0", "fixture_files": 4, "projects": 0}` |
| Manual browser demo (AE-C19) | Steps in [docs/PRD.md §9](docs/PRD.md#9-baseline-quickstart-and-demo) | 2026-11-22, Chromium 156: search, select, save, restart, reopen all worked; no console errors |

Notes that save time:

- The suite starts real loopback servers on ephemeral ports with temporary data directories. It needs no network and leaves nothing behind. `tests/test_cli.py` spawns `python -m architecture_explorer` as a subprocess.
- There is no linter, formatter, type checker or CI configured. Do not claim any of them ran.
- Stop a foreground server with Ctrl+C. If you start it in the background from Git Bash on Windows, `kill` on the shell job does not stop `python.exe`; find the listener with `netstat -ano | grep :<port>` and stop it with `taskkill //PID <pid> //F`. Always confirm the port is free afterwards.
- Use a data directory that is ignored by Git: `./demo-data` (its `*.sqlite*` files are ignored), `./data`, or a temporary directory. Never commit a database.
- One check at a time: do not run the suite and a server on the same port in parallel.

## Architecture boundaries

Details and line references are in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). The rules that matter when changing code:

- **Standard library only.** No pip or npm dependency in the app (`PRD §4`, a recorded decision). A dev-only tool for browser tests needs an explicit, recorded decision in its ticket.
- **Read-only and offline.** The tool never writes to analysed sources and makes no outbound network call. It binds `127.0.0.1` only.
- **Layering.** `server.py` (HTTP, guards, validation, routing) calls `store.py` (SQLite) and `fixtures.py` (in-memory source index). `store.py` and `fixtures.py` do not import `server.py` or each other. The browser UI in `architecture_explorer/static/` talks only to `/api/v1`.
- **Request guards stay on every route.** Loopback `Host` with the bound port; same-origin `Origin` on writes; JSON content type; 16 KiB body cap; strict CSP on the HTML page; user and source text rendered with `textContent`, never `innerHTML`.
- **Storage.** One SQLite connection behind a lock, one explicit transaction per write, optimistic `version` on explorations, `PRAGMA user_version` gate. A schema change needs a version bump and a real migration: today `_init_schema` only handles "empty database to version 1".
- **Stable contracts.** The endpoints, error codes and limits in `PRD §5`, the startup line `Serving on http://127.0.0.1:<port>`, exit code 2 for a newer schema, and the element ids used by the UI (`#title`, `#query`, `#search-btn`, `#results`, `#result-count`, `#save-btn`, `#new-btn`, `#project-list`, `#status`, `#error`, `#selection-note`, `#preview`). Each result row is a button whose `.loc` span reads `<path>:<line>`, followed by the excerpt.
- **Regression rule.** Checks `AE-C01`..`AE-C18` stay in the suite and keep passing for every later milestone (`PRD §8`).

## Git workflow

- Default branch `main`. It has no branch protection and no CI, so discipline is manual.
- Never commit to `main` directly. Branch from the tip of `origin/main`, one ticket per branch, named `<type>/<issue-number>-<slug>` (for example `feat/2-snapshot-import`).
- Small commits with a conventional prefix (`feat:`, `fix:`, `docs:`, `test:`, `chore:`), matching the existing history.
- Open a draft pull request that references its issue (`Part of epic #1`, `Closes #<n>`). The owner reviews and merges; agents never merge, force-push shared branches, publish or deploy.
- Do not commit: databases, data directories, `.env*`, `__pycache__/`, `.venv/`, `.prep/` (local planning scaffolding, ignored on purpose), browser test output.
- Keep documentation changes in the same pull request as the behaviour they describe (PRD §5 for API changes, PRD §8 for new or changed checks, README for user-facing steps).

## Evidence before claiming a ticket done

Report only what you ran and saw. For every ticket, the pull request description carries:

1. The exact command and the tail of its output for `python -m unittest discover -s tests -v`, with the test count. `AE-C01`..`AE-C18` must still pass.
2. The names of the new tests and the `AE-C` IDs they cover, each test carrying its ID in a comment as the existing tests do. Expected values are written by hand in the test, never computed by the code under test (`PRD §6.2`).
3. For API changes: one request and response per new endpoint and per new error code, captured from a running server.
4. For UI changes: the manual steps performed in a browser, the browser and version, and the result, including keyboard operation and the `aria-live` status text. State plainly if a browser run was not done.
5. For storage changes: proof of restart survival (stop the server, start it on the same `--data-dir`, read the data back) and of the upgrade path from a version-1 database.
6. Platform: operating system and Python version. Say which of Windows and Linux was not run.
7. `git status --short` is clean and the diff touches only files in the ticket's scope.

If something could not be verified, say so in the pull request instead of marking the criterion done.

## Agents and the triage loop

**Roles.** Project agent roles live in `.claude/agents/`: nine pinned copies from Agency Agents (MIT) and `loop-verifier`. Each of the nine starts with an "In this repository" section tailored to this project (stack and constraints, files it owns or reviews, commands, invariants, what to hand back). That section and this file override the generic upstream text below it. The five review and audit roles and `loop-verifier` are read-only (`tools: Read, Grep, Glob`): give them the diff, the acceptance criteria and the recorded command output. Selection, provenance, local changes and the name-collision note are in [docs/agents-and-loop.md](docs/agents-and-loop.md) and [.claude/agency-agents/README.md](.claude/agency-agents/README.md).

**Ticket work.** When asked to implement, continue or finish a GitHub issue, follow the playbook [`.claude/skills/implement-ticket/SKILL.md`](.claude/skills/implement-ticket/SKILL.md). Claude Code loads it on its own for ticket work; `/implement-ticket <issue number>` starts it by hand. Delegate to the roles without waiting to be asked; the "Use proactively ..." sentence that ends each role's `description` is what triggers the delegation.

| When | Roles |
|---|---|
| Before coding | Codebase Onboarding Engineer (unfamiliar area), Software Architect (boundary, schema, API or dependency change) |
| While coding | The implementing role that matches the files being changed: Backend Architect, Frontend Developer, Test Automation Engineer |
| After coding, when the change matches | Accessibility Auditor (UI), API Tester (HTTP contract) |
| Gates on every ticket, whatever its size | Code Reviewer on the full diff, then Reality Checker against the acceptance criteria |

- The session or role that wrote a change does not count as its reviewer.
- The pull request description lists the roles that ran and their verdicts under "Agent roles run".

**Triage loop.** The Loop Engineering setup is **L1, report-only, manual**: `/issue-triage` may update `issue-triage-state.md` and `loop-run-log.md` and nothing else. No scheduler, no automated fixes, no GitHub writes, no auto-merge. Binding rules are in [loop-constraints.md](loop-constraints.md).
