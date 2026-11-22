# Angular Architecture Explorer — PRD and Technical Specification

Package: `architecture_explorer`. Status: baseline implemented and verified on 2026-11-22 (28 automated tests pass; the browser demo AE-C19 was run manually). Commands, results and what remains unverified are in [ARCHITECTURE.md](ARCHITECTURE.md#verification-record). The epic below is future work, tracked as GitHub issue #1 and its children.

Labels used throughout: **[Decision]** fixed, **[Default]** a documented proposal that can change, **[Open]** unresolved.

## 1. Product definition

### 1.1 User and problem
A developer joining an Angular codebase needs to answer "where is this component used, how is it reached from a route, and what does it depend on?" Editors answer pieces of this, but the answer is not saved, shared, or kept next to the question. The explorer is a read-only local tool: you search a source snapshot, select a result, and keep the exploration (title, query, selection) so you can reopen it later.

### 1.2 One end-to-end outcome
Open the tool, search the sample project for `JobCardComponent`, see `src/app/jobs.ts:2`, select it, save the exploration under a title, restart the server, and reopen the exploration with the same query and selection intact.

### 1.3 Scope boundaries
- Read-only: the tool never modifies analyzed sources. **[Decision]**
- Offline, loopback only (`127.0.0.1`), no accounts, no external services. **[Decision]**
- Baseline analyzes only bundled synthetic TypeScript fixtures. **[Decision]**
- Out of scope for now: editing source, running the Angular compiler, type resolution, multi-user sync, authentication, deletion of saved explorations **[Default]**.

### 1.4 Workflow states
`empty` → (type query, Search) → `results` → (select row) → `selected` → (Save) → `saved`. Editing title/query/selection after save → `dirty`. Save conflicting with a newer version → `conflict` (Load latest → `saved`). Server error → `error` (state preserved, retry by saving again).

### 1.5 Accessibility and design
Technical-documentation style: off-white page, slate text, high-contrast violet accents (text contrast ≥ 4.5:1). Every control has a visible label. Visible focus outline on all interactive elements. Keyboard: Tab order follows the workflow; `/` focuses the query; Enter searches; Up/Down moves between results; Enter/Space selects; Ctrl/Cmd+S saves. Status updates in an `aria-live` region; errors in `role="alert"`. Responsive down to 800×600 with no horizontal page scroll. Respect `prefers-reduced-motion`. Result rows show `path:line` in monospace with the excerpt beneath, so paths and lines scan quickly.

### 1.6 Why it matters
**[Open]** Motivation beyond the problem in §1.1 is not documented yet.

### 1.7 Smallest durable milestone
M1 (baseline, below): search → select → save → restart → reopen on bundled fixtures.

## 2. Epic and stories

**Epic AE-E1: Explore an Angular project's structure offline.** Turn a bounded, user-supplied source snapshot into a versioned, incrementally updated route and import graph with traceable diagnostics, preserving explorations across restarts.

| ID | Story | Depends on | Status |
|----|-------|-----------|--------|
| AE-S0 | Baseline: fixture search, results with path/line/excerpt, saved explorations, restart reopen | — | **Implemented (M1); verified 2026-11-22** |
| AE-S1 | Bounded snapshot import with canonical paths | AE-S0 | Open |
| AE-S2 | Incremental versioned index | AE-S1 | Open |
| AE-S3 | Angular route and static import graph | AE-S2 | Open |
| AE-S4 | Trace and unresolved-import diagnostics | AE-S3 | Open |
| AE-S5 | Offline end-to-end browser flow | AE-S1–S4 | Open |
| AE-REL | Release integration gate (full suite, clean checkout, README accuracy) | AE-S1–S5 | Open |

Observable outcomes per open story:
- **AE-S1** Importing a directory enforces limits (**[Default]** ≤ 2,000 files, ≤ 1 MiB per file, ≤ 20 MiB total, depth ≤ 20), stores paths in canonical form (`/`-separated, relative, no `.`/`..`, no symlink escapes, case-collisions reported), skips non-`.ts` files, and rejects the whole import atomically on violation with a message naming the first offender.
- **AE-S2** Each import creates a snapshot version; re-import reparses only files whose content hash changed; search results state which snapshot version they came from; saved explorations remember their snapshot and say when it is stale.
- **AE-S3** For the graph fixture (§6.2) the explorer reports exactly the three expected edges with kinds `eager`, `lazy`, `dependency`. Changing one import changes only that edge, and the result is still present after restart.
- **AE-S4** Selecting a symbol shows a trace (route → file → dependency chain). Imports that cannot be resolved are listed with file, line, specifier and reason, never silently dropped.
- **AE-S5** A scripted headless-Chrome flow covers import → search → trace → save → restart → reopen with external network blocked.

## 3. Milestones

| Milestone | Content | Gate |
|-----------|---------|------|
| **M1 Baseline** (implemented) | AE-S0 | AE-C01–AE-C18 pass; demo AE-C19 (§9) |
| M2 Import | AE-S1 | AE-C20–AE-C23 |
| M3 Index | AE-S2 | AE-C24–AE-C27 |
| M4 Graph | AE-S3, AE-S4 | AE-C28–AE-C34 |
| M5 Release | AE-S5 | AE-C35–AE-C37 plus all earlier checks |

Dependencies are strictly linear M1 → M2 → M3 → M4 → M5.

## 4. Architecture

- Python 3.12+ standard library (`http.server`, `sqlite3`, `json`, `hashlib`); native HTML/CSS/JS served from the package; no npm or pip dependencies in the app. **[Decision]**
- Entry point: `python -m architecture_explorer --data-dir <dir> --port <port>`. Binds `127.0.0.1` only; port `0` picks an ephemeral port; startup prints `Serving on http://127.0.0.1:<port>`.
- Layers: `server.py` (HTTP, guards, routing) → `store.py` (SQLite, explorations) → `fixtures.py` (read-only bundled sources and search). Static UI in `static/`.
- Guards: `Host` must be loopback with the bound port; writes (`POST`/`PUT`) require a same-origin `Origin`, JSON content type, and a 16 KiB body cap; strict CSP (no inline script/style); all user text rendered with `textContent`.
- Offline: no network calls in app code; no external fonts, scripts or images.
- Platform: The [baseline verification](../README.md#baseline-verification) records Ubuntu unit tests and the Windows Chrome workflow.

## 5. Data schema and API

This section is the authoritative API summary.

Table `projects(id, title, query, selected_path, selected_line, version, created_at, updated_at)`, `PRAGMA user_version = 1`, `CHECK` that path and line are both null or both set. A newer `user_version` refuses to start.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/health` | status, version, fixture and project counts |
| GET | `/api/v1/fixtures/files` | indexed fixture files with line counts |
| GET | `/api/v1/fixtures/file?path=` | lines of one fixture file |
| GET | `/api/v1/fixtures/search?q=` | literal case-sensitive search, ≤ 200 results |
| GET/POST | `/api/v1/projects` | list / create saved explorations |
| GET/PUT | `/api/v1/projects/{id}` | read / update with optimistic `version` |

Errors: `{"error":{"code","message"[,"fields"]}}` with codes `bad_request` 400, `validation_error` 400, `forbidden_host`/`forbidden_origin` 403, `not_found` 404, `method_not_allowed` 405, `conflict` 409 (adds `current`), `payload_too_large` 413, `unsupported_media_type` 415, `internal_error` 500.

Limits: title 1–120 chars, query ≤ 200 chars, no control characters, body ≤ 16 KiB, ≤ 200 results, excerpt ≤ 200 chars.

Future tables **[Default]**: `snapshots(id, version, created_at, file_count)`, `files(snapshot, path, sha256, size)`, `edges(snapshot, from_path, to_path, kind, line)`, `diagnostics(snapshot, path, line, specifier, reason)`; `projects` gains `snapshot_version`.

## 6. Algorithms and invariants

### 6.1 Baseline search
For each indexed file in code-point path order, for each line in order, emit a result if `query` is a substring (case-sensitive, literal, never a regex or pattern). Stop at 200 results and set `truncated`. Invariants: results are sorted by `(path, line)`; at most one result per line; lines are 1-based; a trailing newline adds no line; the query is stored byte-for-byte (including spaces).

### 6.2 Future graph fixture and expected graph (independent of the parser)
Fixture files: `routes.ts`, `home.ts`, `jobs.ts`, `shared/widget.ts` under `src/app/`.

Expected edges (written by hand, never computed by the code under test):
1. `src/app/routes.ts` → `src/app/home.ts`, kind `eager` (static `import` used as a route `component`).
2. `src/app/routes.ts` → `src/app/jobs.ts`, kind `lazy` (dynamic `import()` in `loadChildren`).
3. `src/app/jobs.ts` → `src/app/shared/widget.ts`, kind `dependency` (static import).

### 6.3 Future parsing strategy **[Default]**
A local, bounded tokenizer in the standard library that recognizes only `import … from '…'`, side-effect `import '…'`, `export … from '…'` and `import('…')`, skipping comments and string/template contents, and resolves relative specifiers against canonical paths (trying `.ts`, `/index.ts`). Anything else (path aliases, bare package names, computed specifiers) is reported as a diagnostic, not guessed. Correctness is judged only against the hand-written expected graph and a negative fixture set (imports in comments/strings, unterminated strings). **[Open]** An external TypeScript parser may later be adopted as an explicit, separately staged dependency; it would need a host check for Node availability and does not change the offline requirement.

### 6.4 Future incremental index invariants
- A snapshot version never changes after creation.
- Re-import yields the same edges as a full rebuild (verified by comparing both).
- Changing one file's imports changes only edges whose `from_path` is that file.
- Import limits are checked before any write; failure leaves the previous snapshot active.

## 7. Errors, retry, cancel, restart, multi-tab
- Save failure (network/500): UI keeps all fields, shows an alert, Save stays enabled; retrying sends the same version, so a retry after an unseen success yields a 409 that the user resolves with Load latest.
- Two tabs: the second save of the same version gets 409 `conflict` with the server's current copy; no silent overwrite.
- Stale search responses (user typed again before a reply) are ignored.
- Search cancel: starting a new search supersedes the old one.
- Restart: all state is in SQLite; explorations reopen by id (`#project=<id>`) or from the project list. A saved selection missing from new results is reported, not dropped silently.
- Storage: each write is one transaction; failure leaves no partial row. Schema from a newer version aborts startup with exit code 2.
- Future import: atomic; a cancelled or failed import leaves the previous snapshot intact.

## 8. Deterministic fixtures and checks

Baseline fixture (4 files): `home.ts` 3 lines, `jobs.ts` 5, `routes.ts` 5, `shared/widget.ts` 3. `jobs.ts` line 2 is `export class JobCardComponent {`, the only occurrence.

Status legend: **Calc** = calculated expectation, no test yet; **Test** = automated test in `tests/` (AE-C01–AE-C18 observed passing on 2026-11-22); **Demo** = manual demonstration (AE-C19 observed on 2026-11-22, without network blocking). See [ARCHITECTURE.md](ARCHITECTURE.md#verification-record).

| ID | Story | Milestone | Check | Expected | Kind |
|----|-------|-----------|-------|----------|------|
| AE-C01 | S0 | M1 | GET health | `status ok`, `fixture_files` 4 | Test |
| AE-C02 | S0 | M1 | GET `/`, assets | 200, CSP, nosniff, labelled controls, traversal 404 | Test |
| AE-C03 | S0 | M1 | bind address | `127.0.0.1` | Test |
| AE-C04 | S0 | M1 | Host validation | foreign host 403; `localhost:<port>` 200 | Test |
| AE-C05 | S0 | M1 | Origin on writes | missing/foreign 403; same-origin 201 | Test |
| AE-C06 | S0 | M1 | Content type, body cap, malformed JSON, 405 | 415 / 413 / 400 / 405 | Test |
| AE-C07 | S0 | M1 | file list | four files with lines 3,5,5,3 | Test |
| AE-C08 | S0 | M1 | search `JobCardComponent` | exactly `src/app/jobs.ts` line 2 | Test |
| AE-C09 | S0 | M1 | search ordering | `Component` → home:1, jobs:2, routes:1, routes:3 | Test |
| AE-C10 | S0 | M1 | literal, case-sensitive, 200-char limit | metacharacters match only literal text | Test |
| AE-C11 | S0 | M1 | file read and traversal | `..`, absolute, backslash → 404 | Test |
| AE-C12 | S0 | M1 | create/get/list | 201 v1; list newest-first | Test |
| AE-C13 | S0 | M1 | validation matrix | 400 `validation_error` with `fields`; nothing stored | Test |
| AE-C14 | S0 | M1 | update and conflict | v2; stale version 409 with `current`; missing 404 | Test |
| AE-C15 | S0 | M1 | hostile text and SQL metacharacters | stored verbatim | Test |
| AE-C16 | S0 | M1 | restart reopen | same record, query bytes, selection; next PUT v3 | Test |
| AE-C17 | S0 | M1 | newer schema | startup refused | Test |
| AE-C18 | S0 | M1 | CLI entry | startup line; invalid port non-zero exit | Test |
| AE-C19 | S0 | M1 | browser flow §9 | UI shows `src/app/jobs.ts:2`, saves, reopens after restart | Demo |
| AE-C20 | S1 | M2 | import limits | each limit violation rejected atomically | Calc |
| AE-C21 | S1 | M2 | canonical paths | `./a/../b.ts` → `b.ts`; symlink escape and case collision rejected | Calc |
| AE-C22 | S1 | M2 | non-TS skipped | counted, not indexed | Calc |
| AE-C23 | S1 | M2 | failed import keeps old snapshot | prior search results unchanged | Calc |
| AE-C24 | S2 | M3 | snapshot versioning | v1→v2 on re-import; v1 immutable | Calc |
| AE-C25 | S2 | M3 | incremental equals full rebuild | identical edges | Calc |
| AE-C26 | S2 | M3 | only changed file reparsed | parse count 1 | Calc |
| AE-C27 | S2 | M3 | stale exploration notice | shown after re-import | Calc |
| AE-C28 | S3 | M4 | expected graph | exactly the three edges in §6.2 | Calc |
| AE-C29 | S3 | M4 | import change | only the changed edge differs | Calc |
| AE-C30 | S3 | M4 | edge change survives restart | same edges after restart | Calc |
| AE-C31 | S3 | M4 | tokenizer negatives | imports in comments/strings ignored | Calc |
| AE-C32 | S4 | M4 | trace | `routes.ts` → `jobs.ts` → `widget.ts` chain shown | Calc |
| AE-C33 | S4 | M4 | unresolved import | listed with file, line, specifier, reason | Calc |
| AE-C34 | S4 | M4 | path alias / bare package | diagnostic, not an edge | Calc |
| AE-C35 | S5 | M5 | E2E in headless Chrome | full flow passes | Calc |
| AE-C36 | S5 | M5 | external network blocked | flow passes, zero external requests | Calc |
| AE-C37 | S5 | M5 | Linux run | quickstart passes on Linux | Calc |

Regression rule: AE-C01–AE-C18 stay in the suite for every later milestone.

## 9. Baseline quickstart and demo

```
python -m unittest discover -s tests -v
python -m architecture_explorer --data-dir ./demo-data --port 8765
```
Open `http://127.0.0.1:8765/`, then:
1. Enter title `Jobs tour`, query `JobCardComponent`, press Enter. Expect one result `src/app/jobs.ts:2`.
2. Select it (click, or Down then Enter); the preview highlights line 2.
3. Press Save (or Ctrl+S). Expect "Saved (version 1)" and the URL gaining `#project=<id>`.
4. Stop the server (Ctrl+C), start it again with the same command, reload the page. Expect the title, the exact query and the selected result restored; the project list shows "Jobs tour".

Exact commands for the loopback API check: `curl http://127.0.0.1:8765/api/v1/health`.

## 10. Assumptions and limitations
- The baseline was verified by execution on Windows with Python 3.13 (test suite and manual browser flow). Not re-verified in that run: Linux, Python 3.12, a browser run with external network blocked, and the accessibility targets in §1.5.
- Search is case-sensitive and per-line only; no regex, no multi-line matches.
- Explorations store a query and one selected line; no notes or graph state yet.
- No deletion, authentication or sharing; single user on one machine.
- Python `http.server` is adequate for a loopback tool, not for exposure beyond it.
- Chrome on Linux compatibility is a design target, not evidence.

## 11. Baseline versus work ahead
Baseline (implemented and verified, see the status line at the top): AE-S0 and checks AE-C01–AE-C19. Ahead: AE-S1–AE-S5, a release integration gate, and AE-C20–AE-C37, tracked in GitHub issue #1 (epic) and its child issues #2 to #10 (map in [ARCHITECTURE.md](ARCHITECTURE.md#backlog-map)). Known gaps between this document and the code, including decisions the planned work still needs, are listed in [ARCHITECTURE.md](ARCHITECTURE.md#prd-drift-and-gaps).
