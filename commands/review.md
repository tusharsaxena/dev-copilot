---
description: Run the dev-copilot:review subagent — a principal-engineer-level review of the project in cwd. Defaults to the current changes (working-tree diff, or branch-vs-base if clean); pass a path to review a subtree, "all" for the whole repo, or "branch" to compare against the base branch. Produces 01_FINDINGS.md … 05_FINAL_SUMMARY.md under reviews/<YYYY-MM-DD>/, plus a chat summary.
argument-hint: [path | "all" | "branch"]
---

Invoke the `dev-copilot:review` subagent on the project in the current working directory.

Use the Task tool with `subagent_type: "dev-copilot:review"`. Pass through `$ARGUMENTS` verbatim as the scope directive for the reviewer:

- **empty** → review the current changes: the uncommitted working-tree diff; if the tree is clean, the current branch vs. its base.
- **a path** (file or directory that exists) → review that subtree.
- **`all`** / **`repo`** / **`full`** → review the whole repository.
- **`branch`** → review the current branch against its base branch.

Do not perform the review yourself in the main thread — delegate fully to the subagent so its findings, proposed changes, and execution plan are written to disk under `reviews/<YYYY-MM-DD>/` per the agent's spec. After the agent returns, surface its chat summary verbatim to the user.
