# Loop Budget — angular-architecture-explorer

> Primary loop: **Issue Triage** (scaffolded by loop-init)

## Daily limits

| Loop | Max runs/day | Max tokens/day | Max sub-agent spawns/run |
|------|--------------|----------------|--------------------------|
| Issue Triage | 2 (manual only, no scheduler) | 80k | 0 (L1) |

## On budget exceed

1. Stop: no scheduler is configured, so do not start another manual run that day
2. Append event to `loop-run-log.md`
3. Tell the owner in the session; do not write to GitHub

## Kill switch

- A file named `loop-pause-all` in the repository root, created by the owner: if it exists, a run exits immediately
- Resume only after the owner deletes that file

## Estimate spend

```bash
npx @cobusgreyling/loop-cost --pattern issue-triage
```
