---
description: Run the dev-copilot:review subagent — a principal-engineer-level review of the project in cwd. It re-runs the repo's own lint, tests and type-check first so findings rest on today's numbers. Defaults to the current changes (working-tree diff, or branch-vs-base if clean); pass a path to review a subtree, "all" for the whole repo, or "branch" to compare against the base branch. Produces 01_FINDINGS.md … 05_FINAL_SUMMARY.md under reviews/<YYYY-MM-DD>/, plus a chat summary. In a WoW addon repo (detected by dev-copilot-profile) it runs the WoW-specific review instead — whole-addon by default, writing to docs/reviews/<YYYY-MM-DD>/.
argument-hint: [path | "all" | "branch"]
---

Invoke the `dev-copilot:review` subagent on the project in the current working directory.

## Step 0 — Detect the repo profile

Run `dev-copilot-profile` (Bash; if not found, `"${CLAUDE_PLUGIN_ROOT}/bin/dev-copilot-profile"`). It prints `profile=`, `kind=`, `repo=`, `name=`, `root=`, `reason=`.

Record `profile` and `kind`. This wrapper has no overlay of its own and reads none: the review agent carries the profile-specific behavior, and it applies it from its own Step 0. Your only use of the result is to pass it along in Step 1.

## Step 1 — Dispatch the agent

Use the Task tool with `subagent_type: "dev-copilot:review"`. In the prompt, pass:

- **The scope directive** — `$ARGUMENTS`, verbatim. The agent resolves it in its Step 0a:
  - **empty** → its default scope (in a generic repo, the current changes: the uncommitted working-tree diff; if the tree is clean, the current branch vs. its base);
  - **a path** (file or directory that exists) → that subtree;
  - **`all`** / **`repo`** / **`full`** → the whole repository;
  - **`branch`** → the current branch against its base branch;
  - anything else → additional context for the reviewer.
- **The detected profile** — one line, `Detected repo profile: profile=<profile> kind=<kind> (dev-copilot-profile, reason=<reason>)`. The agent still runs its own Step 0; the line lets it confirm the two agree and say so if they do not.

The agent's first real step is **measurement**: it re-runs every suite the repo can run headless (lint, tests, type-check, and whatever else its profile adds) and reviews against those fresh results rather than committed records. **Do not pre-run any of them here, and do not hand the agent numbers from earlier in the session** — a stale figure passed in is exactly what that step exists to prevent. Anything that needs a live environment, credentials or a login stays out of it and lands in the agent's manual checklist for a human.

Do not perform the review yourself in the main thread — delegate fully to the subagent so its findings, proposed changes, and execution plan are written to disk in the dated bundle its spec names (`reviews/<YYYY-MM-DD>/` by default; the agent's profile can move it). After the agent returns, surface its chat summary verbatim to the user.
