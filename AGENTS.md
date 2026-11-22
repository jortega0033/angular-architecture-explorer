# AGENTS.md

Instructions for coding agents. The full version is [CLAUDE.md](CLAUDE.md); this file repeats only what an agent must know before running anything.

This is a Python standard-library project (Python 3.12+). There is no Node toolchain, no `package.json`, no pip dependency, no linter. CI runs the test command on Linux and Windows.

## Test commands

```
python -m unittest discover -s tests -v
```

Use `python3` on Linux when `python` is absent. Expected today: 28 tests, OK.

## Run command

```
python -m architecture_explorer --data-dir ./demo-data --port 8765
```

## Rules

- Standard library only; read-only towards analysed sources; loopback only; no outbound network.
- Never commit to `main`; one ticket per branch; draft pull request opened only after local checks and both review gates, marked ready only on green CI; the owner merges. See "Delivery workflow" in [CLAUDE.md](CLAUDE.md#delivery-workflow).
- Report only commands you ran and results you saw. Evidence list: [CLAUDE.md](CLAUDE.md#evidence-before-claiming-a-ticket-done).

## Ticket workflow

- Implementing an issue follows one playbook: [.claude/skills/implement-ticket/SKILL.md](.claude/skills/implement-ticket/SKILL.md). Summary and gates: [CLAUDE.md](CLAUDE.md#agents-and-the-triage-loop).
- The roles it names are in `.claude/agents/`. Each starts with an "In this repository" section; read that section before the generic text below it.
- Code review and the acceptance check run on every ticket, and the pull request lists the roles that ran with their verdicts.

## Loop conventions

- The triage loop is L1, report-only and manual. See [LOOP.md](LOOP.md) and [loop-constraints.md](loop-constraints.md).
- No scheduler, no automated source fixes, no GitHub writes, no auto-merge.
