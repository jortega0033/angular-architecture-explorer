# Angular Architecture Explorer

A read-only, offline, local tool for searching a source snapshot and saving explorations (title, query, selected result). Python 3.12+ standard library, SQLite, and native HTML/CSS/JavaScript. No npm or pip dependencies.

The current baseline searches a small bundled synthetic TypeScript project. See [docs/PRD.md](docs/PRD.md) for scope and planned work.

## Program goal

Build an architecture workbench that understands an Angular codebase as deeply as its compiler: types, templates, dependency injection, signals and lazy routes, across thousands of files and their whole Git history, and that proposes and checks refactorings.

The program is planned ([#41](https://github.com/jortega0033/angular-architecture-explorer/issues/41)). Phase 1 is the current epic [#1](https://github.com/jortega0033/angular-architecture-explorer/issues/1) and the only phase with tickets.

**Score.** Share of facts (injections, template bindings, routes, types) that agree with the official Angular compiler on a pinned set of open-source applications.

| Phase | Content | Hours (rough) | Issue |
|---|---|---|---|
| 1 | The current epic and its tickets | 46 to 84 | [#1](https://github.com/jortega0033/angular-architecture-explorer/issues/1) |
| 2 | Own TypeScript and template analysis | 150 to 260 | [#42](https://github.com/jortega0033/angular-architecture-explorer/issues/42) |
| 3 | Semantic graph | 120 to 200 | [#43](https://github.com/jortega0033/angular-architecture-explorer/issues/43) |
| 4 | Time | 90 to 150 | [#44](https://github.com/jortega0033/angular-architecture-explorer/issues/44) |
| 5 | Change | 140 to 240 | [#45](https://github.com/jortega0033/angular-architecture-explorer/issues/45) |
| 6 | Scale and collaboration | 90 to 150 | [#46](https://github.com/jortega0033/angular-architecture-explorer/issues/46) |

About 640 to 1080 engineer hours in total: rough estimates, not measurements. The numbers in the score and the finish lines are targets until a run shows them. Only phase 1 has tickets to work; the sub-issues of a later phase are written when it starts. No single session is expected to reach the end.

## Run

```
python -m architecture_explorer --data-dir ./demo-data --port 8765
```

Open http://127.0.0.1:8765/. The server binds to 127.0.0.1 only. Data is stored in `<data-dir>/explorer.sqlite3`.

## Test

```
python -m unittest discover -s tests -v
```

Tests start real loopback servers on ephemeral ports with disposable data directories.

## Try it

1. Title `Jobs tour`, query `JobCardComponent`, press Enter: one result, `src/app/jobs.ts:2`.
2. Select it, then Save (or Ctrl+S).
3. Stop and restart the server with the same `--data-dir`, reload the page: the exploration is restored.

Keyboard: `/` focuses the query, Up/Down moves between results, Ctrl/Cmd+S saves.

## Limitations

Search is literal, case-sensitive and per line. Only bundled fixtures are searched. No deletion or authentication. See the baseline verification below for the tested platforms.

## Baseline verification

- The unit suite passed on Windows with Python 3.13 and on Ubuntu 24.04 in WSL2 with Python 3.12 (28 tests on Ubuntu). On Linux, use `python3` in the launch and test commands if `python` is unavailable.
- Windows Chrome 157 ran the workflow with external browser requests blocked. Found a symbol in a bundled TypeScript fixture, selected the result, then saved and reopened the exploration after a server restart. The browser reported no uncaught page errors.
