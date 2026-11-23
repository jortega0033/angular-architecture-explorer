# Owner decisions

Decisions the owner made for this repository on 2026-11-22. Changing any entry needs the owner; an agent that finds a decision blocking a ticket stops and says so.

| # | Decision | Date | Implemented in |
|---|---|---|---|
| 1 | The instructions, tooling and playbook live on the default branch (`main`). | 2026-11-22 | `CLAUDE.md`, `.claude/` |
| 2 | Persona agents run automatically during ticket work and carry instructions tailored to this project. | 2026-11-22 | `.claude/agents/`, `.claude/skills/implement-ticket/SKILL.md` |
| 3 | Every open ticket is about app implementation; tooling is installed, not ticketed. | 2026-11-22 | `CLAUDE.md` ("Delivery workflow"), this file |
| 4 | Agents may take a ticket up to a ready pull request: local checks, both gates, draft pull request, CI, ready only on green CI. Only the owner merges and releases. | 2026-11-22 | `.claude/skills/next-ticket/SKILL.md`, `.claude/settings.json`, `docs/RELEASING.md` |
| 5 | No scheduler. Ticket work starts only on the owner's go signal (`/next-ticket`), because the repository is used to train AI models. | 2026-11-22 | `.claude/skills/next-ticket/SKILL.md` (`disable-model-invocation: true`), `LOOP.md` |
| 6 | A review gate hook blocks opening or readying a pull request until the gate roles have run after the last code edit. | 2026-11-22 | `.claude/hooks/role_gate.py`, `.claude/settings.json` |
| 7 | Loop Engineering stays at L1, report-only and unscheduled. | 2026-11-22 | `LOOP.md`, `loop-constraints.md`, `loop-budget.md` |
| 8 | Continuous integration runs on Linux and Windows; the default branch requires a pull request and green checks. | 2026-11-22 | `.github/workflows/ci.yml`; branch protection is set on GitHub by the owner |
| 9 | Permission rules: documented commands are allowed; force pushes, pushes to the default branch, merges, releases and reads of secrets are denied; edits to CI, agent configuration and Loop files ask first. | 2026-11-22 | `.claude/settings.json` |
| 10 | Open decisions on tickets are settled with the ticket's stated default (list below). | 2026-11-22 | The tickets, `.claude/skills/next-ticket/SKILL.md` |
| 12 | The ten UI rules in `docs/ui-quality.md` are binding, and the `ui-ux-pro-max` and `unslop` skills are installed and used for UI work and for copy. | 2026-11-22 | `docs/ui-quality.md`, `.claude/skills/ui-ux-pro-max/`, `.claude/skills/unslop/`, `.claude/skills/implement-ticket/SKILL.md` |
| 13 | Visual system: Pipenzo Flow look tokens (docs/design-tokens.md). SDLC kit version: jortega0033/sdlc-kit v1.0.0. | 2026-11-23 | `architecture_explorer/static/tokens.css`, `docs/design-tokens.md` |

Entry 11 of the kit (Rust verified in CI only) does not apply: this repository has no Rust.

## Entry 10: open decisions settled by the ticket default

Each ticket marks its proposals **[Default]**; the implementer may change one with a stated reason in the pull request.

| Issue | Decision | Default taken |
|---|---|---|
| #2 | Snapshot content storage | Content-addressed `blobs(sha256, content)` plus `snapshots` and `files` tables |
| #2 | How an import starts | `POST /api/v1/snapshots` with `{"root": "<absolute directory>"}`, read by the server from local disk |
| #2 | Directories not traversed | `node_modules` and dot-directories, counted in `skipped_dirs` |
| #2 | Symbolic links inside the root | Not followed, counted as skipped; links pointing outside the root reject the import |
| #2 | Import limits | 2,000 `.ts` files, 1 MiB per file, 20 MiB total, depth 20, injectable for tests |
| #2 | Case collisions and leading BOM | Compared with `str.casefold()`; a leading UTF-8 BOM is dropped when decoding |
| #3 | Analysis cache and snapshot identity | `analyses(sha256, analyzer_version, data)` table; `projects.snapshot_version INTEGER NULL`; tests in `tests/test_index.py` |
| #4 | `path_alias` versus `bare_package` | `@/`, `~`, `#` prefix or first segment is a top-level snapshot directory, else `bare_package` |
| #4 | Edge classification | Dynamic literal import is `lazy`; static import used as a `component:` value is `eager`; the rest `dependency` |
| #4 | Storage, endpoint and module | Schema 3 to 4 with `edges` and `diagnostics`; `GET /api/v1/snapshots/{version}/graph`, 10,000 edge cap; `architecture_explorer/graph.py`; tests in `tests/test_graph.py` |
| #5 | Trace limits and API | At most 20 traces with `truncated`; trace search in `graph.py`; tests in `tests/test_trace.py` |
| #6 | Full-flow test and CI job | `e2e/test_full_flow.py`; run with `python -m unittest discover -s e2e -v`; CI browser job on `ubuntu-24.04` once CI exists |
| #7 | Version bump | `__version__` from `0.1.0` to `0.2.0` |
| #8 | Tokenizer module and line endings | `architecture_explorer/tsimports.py` with `extract_imports(text) -> ImportScan`; a `//` comment ends at `\n` or `\r`; tests in `tests/test_tsimports.py` |
| #9 | Browser tool decision | Option (a): dev-only driver pinned in `requirements-dev.txt` in `.venv/`, harness in `e2e/` |
| #10 | CI workflow file name | Superseded: CI is installed by this setup as `.github/workflows/ci.yml` (job `test`, Linux and Windows, Python 3.12 and 3.13) |

No ticket was found that states no default. For any later ticket that does, take the conservative option and flag it in the issue.
