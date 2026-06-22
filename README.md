# dev-copilot

A generic development co-pilot plugin for Claude Code. Automates the repetitive git and documentation chores of day-to-day development, plus a deep principal-engineer review — all language- and framework-agnostic.

It's a de-WoW'd descendant of the [`wow-addon`](https://github.com/tusharsaxena/wow-addon) plugin: same shape (commands + a review subagent), with every World-of-Warcraft–specific concern stripped out and replaced by generic engineering checks.

## Commands

| Command | What it does |
|---|---|
| `/dev-copilot:diff` | Read-only summary of all uncommitted changes — what changed, the likely intent, and risks (dead exports, broken refs, undeclared deps, leftover debug, staged secrets). Never dumps the raw diff. |
| `/dev-copilot:commit` | Stages named files and commits with a generated, style-matched message. Auto-commits by default; pass `ask` to require approval, or a string to use it verbatim as the subject. Never pushes, amends, or `git add -A`; gates on secret-looking files. |
| `/dev-copilot:sync-docs` | Deep-analyzes the project and rewrites `README.md`, `CLAUDE.md`/`AGENTS.md`, `ARCHITECTURE.md`, `TODO.md`, and (conservatively) `CHANGELOG.md` to match the code — eliminating documentation drift. Shows a drift inventory before writing; never bumps versions or auto-deletes code. |
| `/dev-copilot:review` | Runs the `dev-copilot:review` subagent. |

## Sub-agent

`/dev-copilot:review [path | "all" | "branch"]` runs a principal-engineer-level review.

- **Scope is argument-driven.** No argument → the current changes (working-tree diff, or branch-vs-base if clean). A path → that subtree. `all` → the whole repository. `branch` → current branch vs. its base.
- **Full-scope checks**: design & structure, correctness & logic, error handling & resilience, security, concurrency, performance, API & dependency hygiene, tests & observability, naming, and dead code. It detects your stack and conventions first and only applies checks that fit.
- **Output**: five artifacts under `reviews/<YYYY-MM-DD>/` — `01_FINDINGS.md`, `02_PROPOSED_CHANGES.md`, `03_TEST_PLAN.md`, `04_EXECUTION_PLAN.md`, `05_FINAL_SUMMARY.md` — plus a chat summary (verdict, severity counts, top findings).

## Design principles

- **Read before write.** `diff` and `review` never mutate. `sync-docs` shows its drift inventory before editing and preserves each file's voice and line endings.
- **Never surprises you with destructive git.** `commit` stages only named files, never pushes or amends, and refuses to stage anything that looks like a secret without asking.
- **Stays in its lane.** `sync-docs` doesn't bump versions or delete code; `review` proposes changes but writes findings, not fixes.
- **Stack-agnostic.** Project type, build/test commands, and conventions are detected from the manifest and config, not assumed.

## Install

The repo is its own Claude Code marketplace (it ships a `.claude-plugin/marketplace.json`), so installing is three commands. Run these inside any Claude Code session:

1. **Add this repo as a marketplace:**

   ```
   /plugin marketplace add tusharsaxena/dev-copilot
   ```

   (`owner/repo` shorthand works for GitHub. You can also use the full URL: `/plugin marketplace add https://github.com/tusharsaxena/dev-copilot.git`)

2. **Install the plugin:**

   ```
   /plugin install dev-copilot@dev-copilot
   ```

   When prompted for install scope, choose **user** to enable it in every project on this machine, or **project** to enable it only in the current project.

3. **Activate it:**

   ```
   /reload-plugins
   ```

After install, the commands and the `review` subagent are available in every Claude Code session under the `dev-copilot:` namespace.

## Updating

When the repo changes (updated commands or agent), pull the latest and reactivate:

```
/plugin marketplace update dev-copilot
/reload-plugins
```

## License

MIT © 2026 Tushar Saxena
