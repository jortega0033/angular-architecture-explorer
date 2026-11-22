# Agency Agents: provenance of the project agent roles

The role definitions in `.claude/agents/` (except `loop-verifier.md`, which comes from Loop Engineering) are copied from **Agency Agents**.

- Upstream: https://github.com/msitarzewski/agency-agents
- Pinned revision: `8ae6164602c95ca78828b148b9052460ee426885` (branch `main`, 2026-11-09)
- License: MIT, Copyright (c) 2025 AgentLand Contributors. The full text at the pinned revision is in [LICENSE](LICENSE) next to this file (upstream blob `523078c01624b9b1b1c551e75054b9d3a9f953ab`).
- Fetched with `gh api "repos/msitarzewski/agency-agents/contents/<path>?ref=<sha>"` on 2026-11-22.

## Installed roles

| File in `.claude/agents/` | `name` | Upstream path | Upstream blob | Local change |
|---|---|---|---|---|
| `engineering-software-architect.md` | Software Architect | `engineering/engineering-software-architect.md` | `1a69148c99b2c170e36e035a0c7a341e98e634e9` | added `tools: Read, Grep, Glob` |
| `engineering-code-reviewer.md` | Code Reviewer | `engineering/engineering-code-reviewer.md` | `fb93291f4b94a8d5687aa1cc0d05741c3352dd22` | added `tools: Read, Grep, Glob` |
| `engineering-codebase-onboarding-engineer.md` | Codebase Onboarding Engineer | `engineering/engineering-codebase-onboarding-engineer.md` | `cc36ec153ebe38ebf51515d8591a44e1213e5aa1` | added `tools: Read, Grep, Glob` |
| `testing-reality-checker.md` | Reality Checker | `testing/testing-reality-checker.md` | `e534cfbd20d3115d5265387f19db7d3b25649421` | added `tools: Read, Grep, Glob` |
| `testing-accessibility-auditor.md` | Accessibility Auditor | `testing/testing-accessibility-auditor.md` | `350dc3d468b96015a6b3cdefbb06f4a33f673cb1` | added `tools: Read, Grep, Glob` |
| `engineering-backend-architect.md` | Backend Architect | `engineering/engineering-backend-architect.md` | `e9272ed505b03f8487fc78715d69847b9a7c0d06` | none |
| `engineering-frontend-developer.md` | Frontend Developer | `engineering/engineering-frontend-developer.md` | `7fc1a355bf6cc53b5f2b8b58db52ae2860fc0616` | none |
| `testing-api-tester.md` | API Tester | `testing/testing-api-tester.md` | `9b9efe53685b250e0c66fd99c71921fd0827355b` | none |
| `testing-test-automation-engineer.md` | Test Automation Engineer | `testing/testing-test-automation-engineer.md` | `59650291b60ed280f8f5d5da69f15fec2aea3dca` | none |

The only local change is one added frontmatter line, `tools: Read, Grep, Glob`, directly after `description:` in the five review and audit roles. Upstream definitions have no `tools` field, which gives a role every tool; the added line makes those five read-only. The four unchanged files are byte-identical to upstream: `git hash-object --no-filters <file>` equals the blob in the table. For the five changed files, removing the added line gives the upstream blob again.

Why these roles, how they map to the backlog, and the name-collision note are in [docs/agents-and-loop.md](../../docs/agents-and-loop.md).

## Updating

Pick a new upstream revision, fetch the same paths at that revision, re-apply the `tools` line to the five review and audit roles, update the revision and blob columns here, and verify loading as described in `docs/agents-and-loop.md`.

## Local change: automatic delegation (2026-11-22)

One sentence beginning "Use proactively" was appended to the `description:` line of every Agency Agents role in `.claude/agents/` (not to `loop-verifier`). Claude Code uses that field to decide when to delegate, so the roles now run during ticket work without being named. Nothing else in the role files changed.

This supersedes any statement above that a role file is unmodified or that the `tools:` line is the only local change. To compare a role with the pinned upstream file, remove that sentence (and the `tools:` line where one was added) first.

The steps at which each role runs are in `.claude/skills/implement-ticket/SKILL.md`.

A section headed "In this repository" was also inserted directly after the frontmatter of every Agency Agents role (not in `loop-verifier`), before the upstream text. It is project-specific text written for this repository: the stack and constraints, the files the role owns or reviews, the commands, the invariants with their source documents, the parts of the generic text that do not apply here, and what the role hands back. It is not upstream text. To compare a role with the pinned upstream file, remove that section as well: everything from the line `## In this repository` up to and including the blank line after the sentence "This section and CLAUDE.md override the generic text below wherever they differ." Checked on 2026-11-22 for all nine roles: with the section, the "Use proactively" sentence and any added `tools:` line removed, the file hashes to the upstream blob in the table again. In four roles (Reality Checker, Backend Architect, Frontend Developer, API Tester) the upstream description has no final full stop, so the full stop that was added in front of the sentence has to be removed too.

When updating to a new upstream revision, re-insert each section and check it against the repository as it is then; the sections quote commands, paths and document sections that can change.

Verification, 2026-11-22 (Claude Code 2.1.323, Windows 11), one run from the repository root after the sections were inserted:

```
claude -p "List every project subagent defined in .claude/agents with its exact name and tools, say for each whether its instructions begin with a section titled In this repository, and say whether a skill named implement-ticket is available. Plain list, no commentary." --model haiku
```

Exit code 0. The reply listed all nine Agency Agents roles by their exact names and `loop-verifier`. Software Architect, Code Reviewer, Codebase Onboarding Engineer, Reality Checker, Accessibility Auditor and `loop-verifier` were reported with `Read, Grep, Glob`; Backend Architect, Frontend Developer, API Tester and Test Automation Engineer with no `tools` field. All nine roles were reported as beginning with "In this repository"; `loop-verifier` was reported as not, which is intended. The skill `implement-ticket` was reported as available. The reply is the model's reading of the files; no role was launched in this run.
