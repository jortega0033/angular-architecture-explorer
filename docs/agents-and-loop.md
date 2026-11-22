# Project agent roles and the triage loop

Set up on 2026-11-22. Everything here is project-local: it lives in this repository and changes nothing in a user profile.

## Agent roles

Nine role definitions from Agency Agents are installed in `.claude/agents/`. Pinned revision, upstream paths, blob hashes and the MIT attribution are in [.claude/agency-agents/README.md](../.claude/agency-agents/README.md).

| Role (`name`) | Tools | Use it for | Tickets |
|---|---|---|---|
| Software Architect | Read, Grep, Glob | Reviewing a design before code: snapshot storage, migration, the API contract for new endpoints, the edge classification rule, the browser-tool decision | #2, #3, #4, #5, #9 |
| Code Reviewer | Read, Grep, Glob | Reviewing a diff for correctness, guards, transaction boundaries and scope | every pull request |
| Codebase Onboarding Engineer | Read, Grep, Glob | Tracing a code path with source lines before changing it | first contact with a module |
| Reality Checker | Read, Grep, Glob | Checking a "done" claim against the evidence list in `CLAUDE.md` | every pull request, #7 |
| Accessibility Auditor | Read, Grep, Glob | Auditing the UI source (`index.html`, `app.css`, `app.js`) against the PRD §1.5 targets (labels, focus, keyboard, live regions, contrast, 800x600), and judging browser evidence that an implementer or the browser harness supplies | UI changes, #6, #7 |
| Backend Architect | all | Implementing `server.py`, `store.py`, import, index, tokenizer and graph code | #2, #3, #4, #5, #8 |
| Frontend Developer | all | Implementing the plain HTML, CSS and JavaScript UI in `architecture_explorer/static/` | #2 to #5 UI parts |
| API Tester | all | Writing `unittest` API tests against real loopback servers | #2 to #5 |
| Test Automation Engineer | all | The table tests of the tokenizer, the browser harness, the scripted headless-Chrome flow and the CI workflow | #8, #9, #6, #10 |

The five review and audit roles (the first five rows) are read-only: they cannot edit files or run commands, so they report findings and somebody else acts on them. Upstream definitions carry no `tools` field; the line `tools: Read, Grep, Glob` was added here. The other four roles write code or tests and keep every tool.

A read-only Accessibility Auditor cannot open a browser. It audits markup, styles and key handlers by reading them, and it judges observations (keyboard runs, live-region text, an 800x600 view) that the implementer or the browser harness recorded. Its upstream text asks for screen-reader testing; that stays a manual step for a person.

Read each role as a way of working, not as a stack choice. The upstream texts mention frameworks, cloud services, Playwright and microservices that this project does not use. The repository rules win: Python standard library only, no pip or npm dependency in the app, loopback only (see [CLAUDE.md](../CLAUDE.md)).

`loop-verifier` in the same directory comes from Loop Engineering, not Agency Agents. It is a checker, so it is read-only as well (`tools: Read, Grep, Glob`, added here), and it is unused at the current loop level. Its generated text tells it to run the tests; with read-only tools it cannot, and its own rule then makes it answer ESCALATE_HUMAN. A higher loop level that wants this role to run `python -m unittest discover -s tests -v` needs the owner's decision to grant it a test runner (see [LOOP.md](../LOOP.md)).

### Name collisions

The owner's user-level `~/.claude/agents/` already holds Agency Agents definitions with the same `name` values for all nine roles. Claude Code gives the project-level definition precedence, so inside this repository the names resolve to the pinned project copies. Two consequences:

- A session started from this repository gets the read-only review and audit roles. A session started elsewhere gets the user-level versions with all tools.
- A session that was already running before these files existed keeps the definitions it loaded at start. Restart the session to pick up the project copies.

### Verifying that the roles load

`claude agents` lists sessions in Claude Code 2.1.323, not agent definitions, so loading is checked headless from the repository root:

```
claude -p "For each of these agent types say PRESENT or MISSING and list its tools exactly as your Agent tool description states them: Software Architect, Code Reviewer, Codebase Onboarding Engineer, Reality Checker, Accessibility Auditor, Backend Architect, Frontend Developer, API Tester, Test Automation Engineer, loop-verifier. Then launch the 'loop-verifier' agent with the task 'Do not use any tool. Reply with only the comma-separated names of the tools you are able to call.' and quote its reply. Then launch the 'Accessibility Auditor' agent with the same task and quote its reply." --model haiku --output-format stream-json --verbose --strict-mcp-config --mcp-config '{"mcpServers":{}}'
```

The two MCP options start the check without any MCP server, which keeps it light; they do not affect which agents load.

Observed on 2026-11-22 (Claude Code 2.1.323, model reported by the session: `claude-haiku-5-5`), second run, after `loop-verifier` and Accessibility Auditor were made read-only:

- The session's init event listed all nine role names and `loop-verifier` among its agents, and `issue-triage`, `loop-budget`, `loop-constraints`, `loop-intake` among its skills.
- All ten were reported PRESENT. Software Architect, Code Reviewer, Codebase Onboarding Engineer, Reality Checker, Accessibility Auditor and `loop-verifier` were listed with `Read, Grep, Glob`; Backend Architect, Frontend Developer, API Tester and Test Automation Engineer with all tools. The user-level copies have no `tools` line, so this shows the project copies are the ones in effect.
- The launched `loop-verifier` replied `Read, Grep, Glob`.
- The launched Accessibility Auditor started but did not answer the question: it declined to list its tools and offered an audit instead. Its restriction is therefore shown by the session's agent listing only, not by its own reply.

First run, earlier the same day, before that change: the same ten were PRESENT, the four review roles were listed with `Read, Grep, Glob` and the other six with all tools, and a launched Code Reviewer replied `Read, Grep, Glob`.

## Loop Engineering

- Tool: `@cobusgreyling/loop@0.2.0` (MIT), https://github.com/cobusgreyling/loop-engineering.
- Pattern: `issue-triage`. Operating level: **L1, report-only, manual**.
- Files: `LOOP.md`, `loop-constraints.md`, `loop-budget.md`, `issue-triage-state.md`, `loop-run-log.md`, `AGENTS.md`, `.claude/skills/{issue-triage,loop-budget,loop-constraints,loop-intake}/SKILL.md`, `.claude/agents/loop-verifier.md`.

What the scaffold produced and what was changed:

| Item | Action |
|---|---|
| `.grok/` and `.codex/` variants | Removed. This setup is for Claude Code only. |
| Scheduled workflow | None was generated; there is no `.github/` directory. Nothing to disable. |
| `AGENTS.md` | Generated with `npm test` and `npm run lint`, which do not exist here. Rewritten with the real commands and a pointer to `CLAUDE.md`. |
| `LOOP.md` | Cadence changed from "2h–1d" to manual; broken relative links replaced; report-only rules, human gates and run inputs written for this repository. |
| `loop-budget.md` | Project name filled in; 12 runs per day reduced to 2 manual runs; sub-agent spawns 0; kill switch defined as a file named `loop-pause-all` in the repository root. |
| `loop-constraints.md` | Generated rules kept; a binding project section appended (report-only, no GitHub writes, no source edits, no scheduler, no sub-agents). |
| `issue-triage-state.md`, `loop-run-log.md` | Project name filled in; otherwise as generated. No run has been made. |
| Skills | As generated. Where a skill text mentions a cadence, labels or fixes, `loop-constraints.md` overrides it. |
| `loop-verifier.md` | Generated without a `tools` line (every tool). `tools: Read, Grep, Glob` and a short project note were added, because the role is a checker and is not used at L1. |

### Recorded results

`npx --yes @cobusgreyling/loop@0.2.0 init . --pattern issue-triage --tool claude`: exit 0. It printed "no claude variant for issue-triage — using issue-triage (Grok paths)" and still wrote the `.claude/` files.

`npx --yes @cobusgreyling/loop@0.2.0 doctor .` (after the adaptations above), exit 0:

```
Ready:   100/100 L2
         Strong structure but no proven loop runs yet — run one L1 cycle and commit state before L3.
Sync:    n/a
Files:   state=issue-triage-state.md  LOOP.md=yes  budget=yes  run-log=yes  gate=no
Status:  HEALTHY (exit 0)

Top next actions:
  1. Copy or create docs/safety.md (denylists, auto-merge policy, MCP scopes)
  2. Add .github/ISSUE_TEMPLATE, PULL_REQUEST_TEMPLATE, and workflows (see this repo for examples)
  3. Document MCP usage (or note "MCP not required for this pattern") in LOOP.md or skills

Notes:
  · Could not parse loop-sync JSON output
```

`npx --yes @cobusgreyling/loop@0.2.0 status .`, exit 0:

```
  Pattern:  issue-triage
  Ready:    100/100  L2
  State:    issue-triage-state.md · not yet run
  Budget:   loop-budget.md  · gate=no  · constraints=yes

  Recent runs:
    (none in loop-run-log.md)

  Next: Schedule a report-only first run and append loop-run-log.md
```

Reading these results: "100/100 L2" is the tool's structural readiness score, not the operating level. The operating level documented here stays L1. The three "next actions" and the tool's suggestion to schedule a run were deliberately not followed: no scheduler and no workflow that runs the loop. (The epic has a separate ticket, #10, for an ordinary test workflow on pull requests; it has no schedule and does not run the loop.)

`doctor` was run once more on 2026-11-22 after `tools: Read, Grep, Glob` was added to `loop-verifier.md` and the wording fixes in `LOOP.md` and `loop-constraints.md`: exit 0, `Status: HEALTHY`, same file line, same three next actions, same note. The first line changed to:

```
Ready:   100/100 L3
         Strong loop readiness — good candidate for L3 with explicit gates.
```

The label moved from L2 to L3 because the tool counts any commit from the last 14 days that touches `loop-run-log.md` or a `*-state.md` file as loop activity (`detectLoopActivity` in `@cobusgreyling/loop-audit`), and the scaffold commit that added those files now exists. It is not evidence of a run: no loop run has been made, and the operating level stays L1. `status` was not run again. MCP is not required for this pattern; a run reads issues with `gh`.

### Next manual triage run

From the repository root, on a branch (not `main`):

1. Start `claude` and run `/issue-triage`.
2. Check that only `issue-triage-state.md` and `loop-run-log.md` changed: `git status --short`.
3. Run `npx --yes @cobusgreyling/loop@0.2.0 doctor .` and keep its output with the change.

The run proposes priorities and labels in `issue-triage-state.md`. A person applies anything on GitHub.
