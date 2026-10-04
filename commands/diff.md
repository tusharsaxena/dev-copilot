---
description: Summarize all uncommitted changes in the current repo — what changed, why it likely changed, and any risks.
allowed-tools: [Bash, Read, Glob, Grep]
---

Summarize all uncommitted changes in the repository at the cwd.

## Step 0 — Detect the repo profile

Run `dev-copilot-profile` (Bash; if not found, `"${CLAUDE_PLUGIN_ROOT}/bin/dev-copilot-profile"`). It prints `profile=`, `kind=`, `repo=`, `name=`, `root=`, `reason=`.

- **`profile=wow`** — Read `<root>/profiles/wow/diff.md` now. Each of its sections names a hook point in this spec (`<!-- overlay: <id> -->`) and says whether it **adds to** or **replaces** that section; `extra` sections say where they run. Apply them as you go. `kind` (`addon`, `library`, `standards`, `tooling`) refines WoW behavior where the overlay says so.
- **`profile=generic`** — follow this spec as written. Do not read the overlay.
- **Neither invocation works** (no detector on PATH, and no plugin root substituted) — treat the repo as `profile=generic`, say so in one line, and do not read any overlay.

<!-- overlay: subject -->
## Step 1 — Detect git

Run `git rev-parse --is-inside-work-tree` (silently). If not a git repo, tell the user the project isn't under git and stop.

## Step 2 — Gather changes

Run, in parallel:
- `git status --short` — list of changed/added/deleted/untracked files
- `git diff --stat` — per-file insertion/deletion counts for tracked changes
- `git diff` — full unstaged diff
- `git diff --cached` — full staged diff
- `git log -1 --format='%h %s (%cr)'` — the last commit, for context

If there are no changes (working tree clean and nothing staged), say so and stop.

## Step 3 — Report

Print a structured summary, in this order:

**Last commit**: hash, subject, time

<!-- overlay: examples -->
**Files changed** (table or bullet list):
- `path/to/file.ext` — `+12 -3` — one-line description of what changed (e.g. "added retry logic to HTTP client", "renamed `applyConfig` to `refreshConfig`")
- ...

Group related changes if there's a common theme (e.g. "Error-handling additions across client.go + server.go + handler.go").

**Likely intent** (1–3 short bullets): your inference about what the user is working on. Be specific (e.g. "Adding exponential backoff to the payment gateway client" not "Code improvements").

<!-- overlay: risks -->
**Risks / things to double-check**:
- New public symbols (exported functions/classes/types) added without callers (dead code?)
- Removed/renamed symbols still referenced elsewhere (broken references — run `grep` to verify)
- New `TODO`/`FIXME`/`HACK`/`XXX` comments added in this diff
- New imports/dependencies used but not declared in the manifest (`package.json`, `requirements.txt`/`pyproject.toml`, `go.mod`, `Cargo.toml`, `pom.xml`/`build.gradle`, `Gemfile`, `composer.json`, `*.csproj`, etc.)
- Resource lifecycle hazards introduced (opened files/sockets/handles/locks/subscriptions/listeners without a matching close/release/unsubscribe)
- Version field changed in a manifest but no other release-coordination changes (`CHANGELOG` entry, etc.) — or vice-versa
- Generated/lockfiles changed inconsistently with their source (e.g. `package.json` edited but `package-lock.json` untouched)
- Debug leftovers added (`console.log`, `print`, `dbg!`, `fmt.Println`, `System.out.println`, commented-out blocks)

<!-- overlay: untracked -->
**Untracked files** (if any): list them. Flag anything that looks like it shouldn't be committed (`.bak`, `*.swp`, IDE files `.idea/`/`.vscode/`, build output `dist/`/`target/`/`node_modules/`, secrets, large binaries).

## Hard rules

- **Read-only.** Don't run `git add`, `git stash`, `git reset`, or any mutation.
- **Don't paste the full diff** unless the user asks — the summary is the point.
<!-- overlay: specificity -->
- **Be specific in inference.** "Refactored the UI" is useless; name the actual functions, modules, or endpoints.
