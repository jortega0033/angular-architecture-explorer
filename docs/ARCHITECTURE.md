# Architecture notes and PRD reconciliation

Written 2026-11-22 against commit `f1e7db2` (the only commit on `main`). Product scope and the API summary are in [PRD.md](PRD.md); this document records how the code works today, with source lines, and where the PRD and the code differ.

Status words used below:

- **Implemented**: the code exists and was observed working in this review (command and result are in the [verification record](#verification-record)).
- **Planned**: described in the PRD or the backlog; no code exists.
- **Needs verification**: the code exists, or a claim is made elsewhere, but it was not observed in this review.

## What runs

A single Python process (standard library only, Python 3.12+) that serves a JSON API and three static files on `127.0.0.1`, stores saved explorations in one SQLite file, and searches an in-memory index of four bundled TypeScript fixtures. It is not an Angular application and has no Node toolchain.

```
browser (static/index.html, app.js, app.css)
        |  fetch /api/v1/*  (same origin)
        v
server.py   HTTP, guards, validation, routing      ExplorerServer, Handler
   |                         |
   v                         v
store.py                 fixtures.py
SQLite, table projects   in-memory index of fixtures/**/*.ts (read-only)
```

| Module | Responsibility | Owns |
|---|---|---|
| `architecture_explorer/__main__.py` | CLI: arguments, startup line, signals, exit codes | process lifecycle |
| `architecture_explorer/server.py` | HTTP server, request guards, routing, input validation, JSON errors | the HTTP contract |
| `architecture_explorer/store.py` | SQLite persistence for explorations | table `projects`, schema version |
| `architecture_explorer/fixtures.py` | Loads bundled `.ts` files once, lists, reads and searches them | the source index |
| `architecture_explorer/static/` | Browser UI in plain HTML, CSS and JavaScript | UI state only; no storage |
| `tests/` | `unittest` suite that starts real loopback servers | checks `AE-C01`..`AE-C18` |

Dependency direction: `__main__` imports `server` and `store`; `server` imports `store` and `fixtures`; `store` and `fixtures` import only the standard library. The UI reaches the application only through `/api/v1`.

## Traced workflow: search, select, save, restart, reopen

This is the PRD's single end-to-end outcome (§1.2). Status: **Implemented**, observed through the unit suite, the HTTP API and a browser.

1. **Start.** `main()` parses `--data-dir` and `--port` (`__main__.py:23-27`), calls `create_server` (`:30`), maps a newer database schema to exit code 2 (`:31-33`) and other start failures to exit code 1 (`:34-36`), prints `Serving on http://127.0.0.1:<port>` (`:50`) and serves until interrupted. `SIGTERM` and `SIGBREAK` are turned into a clean stop (`:38-47`).
2. **Wiring.** `create_server` (`server.py:387-395`) validates the port, creates the data directory, builds `FixtureIndex()` (`:393`), opens `Store(<data-dir>/explorer.sqlite3)` (`:394`) and binds `127.0.0.1` (`:395`).
3. **Index load.** `FixtureIndex.__init__` (`fixtures.py:27-42`) walks `architecture_explorer/fixtures/` without following links, keeps regular `.ts` files that are not symlinks (`:34-38`), decodes UTF-8 with replacement and splits on `\n` so that a trailing newline adds no line (`:15-21`, `:40-41`). After that the index never touches the disk.
4. **Page.** `GET /` is served from an allowlist of three files (`server.py:18-22`, `:198-200`, `:246-253`); the HTML response carries the CSP (`:23-26`, `:252`).
5. **Search.** The UI calls `GET /api/v1/fixtures/search?q=` (`app.js:221-228`). `Handler._search` (`server.py:276-284`) rejects queries over 200 characters and calls `FixtureIndex.search` (`fixtures.py:67-79`): literal, case-sensitive substring match per line, in code-point path order then line order, at most 200 results, with `truncated` set when more exist. The database is not involved.
6. **Select.** Clicking a result (`app.js:266`) fetches `GET /api/v1/fixtures/file?path=` (`app.js:284-287`, `server.py:269-274`); `FixtureIndex.lines` refuses backslashes, NUL, absolute paths and `.`/`..` segments (`fixtures.py:56-65`).
7. **Save.** `save()` sends `POST /api/v1/projects`, or `PUT /api/v1/projects/{id}` with the last seen `version` once an id exists (`app.js:452-463`). On the server: Host and Origin guards (`server.py:186-194`), body reading with content-type and size checks (`:302-330`), field validation (`validate_project`, `:52-128`; the selection must be an indexed path with an in-range line, `:105-110`), then `Store.create` (`store.py:169-193`) or `Store.update` (`:195-232`), each one `BEGIN IMMEDIATE` transaction.
8. **Reopen after restart.** All state is in SQLite. On load the UI lists explorations (`app.js:349-351`) and, when the URL carries `#project=<id>` (`app.js:137`, `:573-574`), opens it (`:399-400`), restores title, query and selection, re-runs the search and reports a saved selection that no longer matches (`:368-396`).

## Invariants

Storage (`store.py`):

- One shared connection guarded by a lock; every write is one explicit transaction that rolls back on any error (`:75-82`, `:176-189`, `:204-228`).
- Optimistic concurrency: an update whose `version` differs from the stored one raises `Conflict` carrying the current record (`:210-212`); the server answers 409 with `current` (`server.py:349-354`, `:362-371`).
- `CHECK ((selected_path IS NULL) = (selected_line IS NULL))` (`:23`). Only a path and a line number are stored, never source text.
- `PRAGMA user_version = 1` (`:10`, `:112`). A database with a newer version raises `SchemaVersionError` (`:95-99`) and the CLI exits with code 2.
- `updated_at` is strictly increasing within a process and across restarts (`_stamp`, `:119-126`; seeded from the table at `:86-87`).
- The list endpoint returns at most 200 explorations, newest first (`:11`, `:150-160`).

Server (`server.py`):

- `Host` must be `127.0.0.1:<port>` or `localhost:<port>` with the bound port, else 403 `forbidden_host` (`:187-190`).
- `POST` and `PUT` need an `Origin` of the same two forms, else 403 `forbidden_origin` (`:191-194`).
- Writes need `Content-Type: application/json`, a numeric `Content-Length`, no `Transfer-Encoding`, at most 16384 bytes, and a JSON object body (`:302-330`).
- Only three static paths exist (`:18-22`); everything else is the API or 404.
- Every response sets `X-Content-Type-Options: nosniff`, `Cache-Control: no-store` and `Connection: close` (`:373-384`); HTTP/1.0, one request per connection (`:156`).
- Unknown fields, wrong types, control characters and out-of-range values produce 400 `validation_error` with a `fields` map and store nothing (`:52-128`).
- Unhandled exceptions become 500 `internal_error` with a generic message (`:178-184`).
- On Windows `SO_REUSEADDR` is off, so a busy port fails to bind instead of being shared (`:134`).

Source index (`fixtures.py`):

- Paths are relative, `/`-separated and sorted by code point (`:39`, `:42`).
- Results are ordered by `(path, line)`, one per matching line, lines are 1-based, excerpts are trimmed and cut to 200 characters (`:67-79`).

UI (`static/app.js`): all dynamic text is inserted with `textContent` or DOM nodes; `innerHTML` does not occur in the file. Stale responses are ignored through a search sequence number (`:223`, `:229`) and an epoch counter (`:369`, `:387`, `:456`, `:469`).

## PRD capability status

| PRD item | Status | Evidence |
|---|---|---|
| AE-S0 fixture search, path/line/excerpt, ordering, 200 cap | Implemented | `fixtures.py:67-79`; tests AE-C07..AE-C11 pass |
| AE-S0 saved explorations: create, read, list, update, 409 conflict | Implemented | `store.py:169-232`; tests AE-C12..AE-C15 pass |
| AE-S0 restart and reopen | Implemented | tests AE-C16 (in-process and subprocess); browser run below |
| Guards, CSP, error codes, limits (§4, §5) | Implemented | tests AE-C01..AE-C06 pass |
| Newer schema refused, CLI entry (AE-C17, AE-C18) | Implemented | tests pass |
| AE-C19 browser demo (§9) | Implemented, observed manually | Chromium 156 run below. External network was not blocked in this run. |
| Accessibility and design (§1.5): labels, focus outline, `/`, arrows, Ctrl/Cmd+S, `aria-live`, `role="alert"` | Needs verification | Key handlers at `app.js:514-561`, `role="status"` and `role="alert"` in `index.html:47-50`. Contrast ratio, 800x600 layout, reduced motion and a screen-reader pass were not checked. |
| Ubuntu 24.04 / Python 3.12 run, Windows Chrome 157 run with network blocked | Needs verification | Claimed in the README "Baseline verification"; not repeated here |
| AE-S1 bounded snapshot import, canonical paths, limits | Planned | No import code or endpoint; the index only reads the bundled directory |
| AE-S2 snapshot versions, hash-based reparse, stale notice | Planned | Schema version is 1 with one table |
| AE-S3 route and import graph | Planned | No tokenizer, no `edges` table |
| AE-S4 trace and unresolved-import diagnostics | Planned | None |
| AE-S5 scripted headless-Chrome flow | Planned | No browser test files or tool |
| AE-REL release gate | Planned | None |

Check IDs: `AE-C01`..`AE-C17` are tagged in comments in `tests/test_api.py`; `tests/test_cli.py` covers `AE-C16` and `AE-C18`. `AE-C19` is a manual demo. `AE-C20`..`AE-C37` have no code or tests.

## PRD drift and gaps

Material:

1. **Verification status was stale.** The PRD said the tests were "not yet observed passing" and the baseline "unverified" (header, §2, §8 legend, §10, §11). The suite passes (28 tests) and the browser demo works. The PRD status lines were updated in the same change as this document.
2. **"Tracked in the backlog" had no target.** PRD §11 refers to a backlog. The live backlog is the GitHub issues (epic #1 and children). `.prep/backlog.json` and `.prep/contract.md` are untracked local scaffolding (ignored by `.gitignore`) and are not a source of truth.
3. **No API is defined for the planned work.** PRD §5 lists future tables but no endpoints for import, snapshots, the graph, traces or diagnostics, and it does not say how an import is started (API call, CLI flag or both). Each ticket has to fix its own contract and add it to §5.
4. **No storage is defined for snapshot content.** The future tables hold `files(snapshot, path, sha256, size)` but nothing holds file content. An immutable, readable snapshot (AE-C24) cannot depend on re-reading a directory that may have changed, so content has to be stored (for example content-addressed by `sha256`). This is a decision for the import ticket.
5. **AE-C25 is scheduled before the thing it compares exists.** It sits in milestone M3 (AE-S2) and expects "identical edges", but edges arrive with AE-S3 in M4. In M3 the comparison can only cover the per-file index; the edge comparison belongs to M4.
6. **The `eager` versus `dependency` rule is not a tokenizer rule.** §6.3 limits the tokenizer to import and export forms, while §6.2 classifies an edge as `eager` because the imported name is used as a route `component`. Telling the two apart needs an extra, stated rule about `component:` usage in the importing file.
7. **The index and validation are fixture-specific.** `/api/v1/fixtures/*`, the health field `fixture_files` and the validation message "path is not an indexed fixture file" (`server.py:106`) assume the bundled files. A saved selection has no snapshot identity. The import and index tickets must add that without breaking `AE-C01`..`AE-C18`.
8. **Schema migration does not exist yet.** `_init_schema` creates the tables only when the stored version is lower than 1 (`store.py:106-117`). The first schema change needs a version bump, an upgrade path from version 1, and a test for it.
9. **The browser-test tool is undecided.** PRD §4 forbids pip and npm dependencies in the app; a scripted headless-Chrome flow needs either a dev-only tool or a hand-written DevTools client. `.gitignore` already lists `playwright-report/`, `test-results/` and `.venv/`, but nothing in the repository uses them.

Minor:

- A write without `Content-Length` returns HTTP 411 with code `bad_request` (`server.py:308-310`); PRD §5 lists `bad_request` only as 400.
- The 200-exploration list cap (`store.py:11`) and the `Location` header on create (`server.py:336`) are not in PRD §5.
- PRD §4 does not say that the UI talks only to `/api/v1`.
- There is no CI, linter or type checker; the README's two-platform claim rests on manual runs.

## Risks for the planned work

- A large import on the single locked connection blocks every other request for its duration; the import ticket should bound the work (the limits do) and keep the write transaction short.
- Symlink and case-collision behaviour differs between Windows and Linux; creating symlinks on Windows may need elevation, so those tests need a documented skip condition rather than a silent pass.
- A hand-written TypeScript tokenizer has known traps: template literals with `${}` nesting, regular-expression literals versus division, and unterminated strings. Correctness is judged only against hand-written expectations (PRD §6.2, §6.3).
- The data directory holds `explorer.sqlite3` plus `-wal` and `-shm` files while the server runs; copy or inspect it only after a clean stop.

## Verification record

Observed on 2026-11-22, Windows 11, Python 3.13.14, in a worktree at `f1e7db2`.

| Command or action | Result |
|---|---|
| `python -m unittest discover -s tests -v` | `Ran 28 tests in 15.683s`, `OK` |
| `python -m architecture_explorer --data-dir <temp> --port 18771` | printed `Serving on http://127.0.0.1:18771`; `GET /` returned 200 |
| `curl http://127.0.0.1:18771/api/v1/health` | `{"status": "ok", "version": "0.1.0", "fixture_files": 4, "projects": 0}` |
| `curl "http://127.0.0.1:18771/api/v1/fixtures/search?q=JobCardComponent"` | one result: `src/app/jobs.ts`, line 2, `export class JobCardComponent {` |
| Browser, PRD §9 steps 1 to 3 (Chromium 156, port 18772): title `Jobs tour`, query `JobCardComponent`, Enter, select the result, Save | one result `src/app/jobs.ts:2`; preview shows the file with line 2; status `Saved (version 1)`; URL gained `#project=<id>`; list shows `Jobs tour`; no console errors |
| Browser, PRD §9 step 4: stop the server, start it on the same data directory, reload | health reported `"projects": 1`; title, query, selected result, preview and status restored; no console errors; every request went to `127.0.0.1` |

Not run: Linux, Python 3.12, a browser run with external network blocked, any accessibility tooling.
