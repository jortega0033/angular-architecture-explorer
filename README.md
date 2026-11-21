# Angular Architecture Explorer

A read-only, offline, local tool for searching a source snapshot and saving explorations (title, query, selected result). Python 3.12+ standard library, SQLite, and native HTML/CSS/JavaScript. No npm or pip dependencies.

The current baseline searches a small bundled synthetic TypeScript project. See [docs/PRD.md](docs/PRD.md) for scope and planned work.

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
