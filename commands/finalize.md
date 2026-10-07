---
description: Finish a changeset — sync docs, commit, merge any feature branch to the default branch, push, and delete the branch. Works on the current repo alone or on several sibling repos in dependency order; establishes which by evidence and asks when the scope is not certain.
argument-hint: [repo names or paths, space-separated | "here" for this repo only]  |  omit to establish scope
allowed-tools: [Bash, Read, Glob, Grep, Edit, Write, Task, Skill]
---

Finish a piece of work: get it synced, gated, committed, merged and **pushed**. The changeset may live in one repo or span several sibling repos — this command handles both, and the first thing it does is establish which.

## Step 0 — Detect the repo profile

Run `dev-copilot-profile` (Bash; if not found, `"${CLAUDE_PLUGIN_ROOT}/bin/dev-copilot-profile"`). It prints `profile=`, `kind=`, `repo=`, `name=`, `root=`, `reason=`.

- **`profile=wow`** — Read `<root>/profiles/wow/finalize.md` now. Each of its sections names a hook point in this spec (`<!-- overlay: <id> -->`) and says whether it **adds to** or **replaces** that section; `extra` sections say where they run. Apply them as you go. `kind` (`addon`, `library`, `standards`, `tooling`) refines WoW behavior where the overlay says so.
- **`profile=generic`** — follow this spec as written. Do not read the overlay.
- **Neither invocation works** (no detector on PATH, and no plugin root substituted) — treat the repo as `profile=generic`, say so in one line, and do not read any overlay.

**Detection runs per repo.** This command can span several repos, so run `dev-copilot-profile <path>` for every repo that becomes a candidate in Step 1 and record each one's `profile` and `kind`. A WoW repo's overlay applies only to that repo's portion of the run (its doc sync, its gate, its report row). The overlay's scope and dependency-chain sections (Steps 1–2) apply to the edges between repos when either end of an edge is a WoW repo. When no repo in scope is WoW, do not read the overlay at all.

Per repo, in this order: `/dev-copilot:sync-docs` → gate → `/dev-copilot:commit` → merge any feature branch to the repo's default branch → push to origin → delete the branch. When more than one repo is in scope, repos that depend on another repo wait for it.

`$ARGUMENTS` is optional. It may name the repos to finalize (names relative to the parent directory, or paths), or be `here` to mean the current repo and nothing else. Omit it and the scope is established in Step 1.

## Step 1 — Establish the scope

The unit of work is a **changeset**: the repos that were changed together, for one reason. Getting this wrong in either direction is expensive — too narrow and half the changeset sits unpushed while the other half references it on origin; too wide and unrelated work-in-progress gets committed under a message that is now wrong for both.

**Never guess the scope.**

1. If `$ARGUMENTS` is `here` (or names exactly the cwd repo), the scope is this repo alone. Skip to Step 2.
2. If `$ARGUMENTS` names repos, use exactly those — but still run the status check on each and say so if one is already clean, rather than pretending you finalized it. Skip to Step 2.
3. Otherwise, survey (below).

<!-- overlay: survey -->
**Which repos the survey looks at:** the cwd repo, plus any sibling checkout (`../<name>`) that this session's own work touched or that a changed file cites (`../<Repo>/…`). Do not walk the whole parent folder: a general workspace is full of unrelated repos, and listing their dirt only forces a question nobody needed.

For each, run `git -C <repo> status --porcelain` and `git -C <repo> log --oneline HEAD --not --remotes`. The second lists commits no remote-tracking ref holds, so it also covers a branch with no upstream and a repo created locally and pushed without `origin/HEAD` (where `origin/HEAD..HEAD` fails and shows nothing). Keep its stderr: an error there is a fact to report, not an empty answer. A repo is a **candidate** if it has uncommitted changes **or** unpushed commits; note "no upstream" or "no remote" when that is why its commits are unpushed.

Then decide, and only proceed without asking when the answer is certain:

- **No candidates** → stop: "Nothing to finalize."
- **Exactly one candidate** → that is the scope. Say which repo and continue.
<!-- overlay: scope-evidence -->
- **Several candidates, conclusively one changeset** → the scope is all of them. "Conclusively" means hard evidence, not a hunch: this session's own work touched each of them; or a vendored copy of a library in one is a byte-for-byte match for the changed source in another; or a changed file in one cites a sibling path (`../<Repo>/…`) that changed in this same set. Print the evidence per repo, then continue.
- **Anything else** → **ask.** This includes: candidates whose changes look unrelated to each other, candidates you did not touch this session, or any repo holding changes you cannot account for (an unrelated feature half-written, a stash-shaped mess). Do not resolve it by picking the likely answer.

To ask, print one block per candidate — repo name, branch, unpushed commit subjects, and the changed files with a one-line reading of what the change is — then ask which repos are in scope for this finalize. Offer the obvious groupings (all of them / just the cwd repo / a named subset) rather than an open-ended question. Wait for the answer; do not start Step 2 on a provisional scope.

Print the final scope as a list before doing anything, with each repo's detected `profile` (and `kind` for a WoW repo).

## Step 2 — Derive the dependency chain

**Single repo in scope?** There is nothing to order. Note it ("single-repo changeset — no dependency chain") and go to Step 3.

With more than one repo, order is not cosmetic. Get it wrong and a repo lands on origin citing a path or a version that does not exist there yet.

Establish, with evidence rather than assumption:

<!-- overlay: dependency-chain -->
- **Vendored or path-linked shared code.** If repo B carries a vendored copy of repo A (a copied-in library folder, a git submodule or subtree), or depends on it by local path (a `file:`/`link:` dependency in `package.json`, a `replace … => ../A` in `go.mod`, a `path =` dependency in `Cargo.toml`, an editable/path dependency in `pyproject.toml` or `requirements*.txt`, a `<ProjectReference>` to `../A`), then **A precedes B**. Confirm the relationship — for a vendored copy, `diff -r --strip-trailing-cr A/<lib> B/<vendor-dir>/<lib>`; for a path dependency, the manifest line itself — rather than inferring it from the name.
- **Cross-repo references in the changed files themselves.** `grep` the diff for sibling paths (`../<Repo>/…`). A doc line in B that cites a file in A is a dependency: A must be committed and pushed first, or B's reference points at nothing on origin.
- **Release order.** If the changeset includes a version tag in A that B's docs, manifest or lockfile name, A goes first.

Repos with **no** dependency on each other are independent and should be finalized **in parallel**. Print the chain you derived — e.g. `shared-lib → (api | web | worker)` — and the evidence for each edge, before executing.

## Step 3 — Execute, per repo

Run the stages below **in the repo's own root**. When several repos are independent, run them concurrently — one `Task` per repo, or a workflow if the user has opted into multi-agent orchestration — but never let two agents touch the same repo, and never start a dependent repo before its dependency has **pushed**. With a single repo in scope, run the stages inline; there is nothing to fan out. Hand each per-repo agent its repo's detected `profile`/`kind`, and, for a WoW repo, the overlay path, so it applies the overlay to that repo only.

<!-- overlay: doc-sync -->
### 3a. Sync the docs

Run `/dev-copilot:sync-docs` for that repo. One binding that matters when the scope is more than one repo:

- **Content sync only.** That command asks the user to confirm before scaffolding, creating or restructuring documents. In a multi-repo run — especially a parallel one — nobody is there to answer per repo. Do not create or move documents; record what you would have proposed and surface it in the final report. In a **single-repo** run the user is right there: ask, as that command normally would.

### 3b. Re-run that repo's gate

Docs edits are not supposed to move a gate, which is exactly why running it is cheap and the omission is expensive — a doc sync that regenerates a generated inventory or count can disagree with the suite that produced it.

<!-- overlay: gate-commands -->
Run the repo's lint and test suites — whatever `/dev-copilot:run-tests` discovers for it (its `test`/`lint` scripts, `make test`, `pytest`, `go test ./...`, `cargo test`, and so on). A run that times out or is killed is reported as exactly that, never as a failure of the code or a pass.

<!-- overlay: vendor-drift -->
Plus, in any repo that vendors a copy of another repo in scope, the vendor-drift gate: `diff -r --strip-trailing-cr <source> <vendored-copy>` — it **must** be empty. A copy that differs from its source in content means the changeset is half-landed.

**A red gate stops that repo.** Do not commit it, do not push it, and do not start anything that depends on it. Finish the other repos, then report the failure with its real output.

<!-- overlay: release-gate -->
**Release checks are not part of *this* gate.** A version bump's own gate lives in `/dev-copilot:bump-version`; this command neither evaluates nor re-evaluates it, and does not hold a push for it.

### 3c. Commit

Run `/dev-copilot:commit` for that repo, in its default (auto) mode, and honour everything that command already says: named files only, never `git add -A`, never `--amend`, never `--no-verify`, match the repo's own commit-message style, and pause for anything secret-shaped. Do not pass it `push` — pushing happens in 3e, after the merge.

One addition when the scope spans repos: **one commit per repo, and the message is written for that repo's reader.** The same changeset looks different from each side — the library's commit is about what it published, the consumer's is about what it now carries and what changed for its users. A message that only makes sense if you have read the other repos' commits is the wrong message.

### 3d. Merge the branch, if there is one

First find the repo's default branch — **do not assume `main` or `master`**: `git symbolic-ref --short refs/remotes/origin/HEAD` (strip the `origin/` prefix); if that is unset, `git remote show origin | sed -n 's/.*HEAD branch: //p'`; if both fail, ask. Call it `<default>` below.

`git branch --show-current`. If it is already `<default>`, the merge and delete stages are **no-ops — say so explicitly in the report** rather than skipping them silently. A reader cannot tell "there was no branch" from "the step was forgotten" unless you write it down.

If there is a feature branch:

1. `git checkout <default> && git fetch origin <default> && git merge --ff-only origin/<default>` — a diverged `<default>` is a stop, not something to force.
2. `git merge --no-ff <branch>` — `--no-ff` so the branch's shape survives in history.
3. Conflicts are a **stop**. Do not resolve a conflict you did not anticipate as part of a finalize; report it and leave the repo mid-merge for the user, naming the conflicted paths.
4. Re-run the gate on the merge result. A merge that compiles is not a merge that passes.

### 3e. Push

`git push origin <default>`. This command **does** push on its own — that is the point of it, and it is the only spec in this plugin that pushes without being asked (`/dev-copilot:commit` pushes only when passed `push`). Paste the real output; a push that says `Everything up-to-date` when you expected a new ref is a finding.

If the push is rejected (someone else moved origin), **stop that repo**. Local `<default>` carries the unpushed merge from 3d (or the commit from 3c), so a rejection means the histories have diverged and no fast-forward can reconcile them. Paste the push output verbatim. You may `git fetch origin` and report how far each side has moved with `git rev-list --left-right --count <default>...origin/<default>` (left: local-only commits, right: origin-only commits), but leave the reconciliation to the user. Never `--force`, and never rebase or merge origin in on your own.

If the repo has no `origin` remote at all, there is nothing to push: say so in the report, and run 3f after the merge instead of after a push.

### 3f. Delete the branch

Only after the push, and only if 3d actually merged something:

```
git branch -d <branch>              # -d, never -D: it refuses if the work is not merged
git push origin --delete <branch>
```

`-d` failing is information, not an obstacle to route around. If it refuses, something is unmerged — report it and leave the branch alone.

## Step 4 — Report

One table, one row per repo — even when there is only one:

<!-- overlay: report-example -->
| Repo | Profile | Docs synced | Gate | Commit | Branch | Pushed |
|---|---|---|---|---|---|---|
| shared-lib | generic | 2 files | 212 pass, lint clean | `a1b2c3d` | main (no branch — merge/delete n/a) | ✅ |

Then, below it:

- **What was deliberately not done** — every restructuring 3a declined to make, per repo, so the user can decide.
- **Dead exports** surfaced by the doc sync (never deleted).
- **Anything that stopped** — a red gate, a conflict, a rejected push — with the real output and what state that repo is in now.
- The scope you finalized and, when it was more than one repo, the dependency chain you executed — so the ordering is auditable after the fact.

Be exact about partial success. "Four of five repos are pushed; `worker` stopped on a red gate and is committed but unpushed" is useful. "Done" is not.

## Hard rules

- **Never guess the scope.** When the candidates are not conclusively one changeset, present them and ask. A wrong scope is not fixable by a revert.
- **Never assume the default branch.** Detect it per repo (3d); a collection can mix `main` and `master`.
- **Never `git add -A` / `git add .`** — named files only, in every repo.
- **Never `--force`, `--amend`, `--no-verify`, or `git branch -D`.** Each of them turns a stop into silent data loss.
- **Never commit a repo whose gate is red**, and never push one, even if the failure looks unrelated to the changeset.
- **Never start a dependent repo before its dependency has pushed.** The whole reason for Step 2.
<!-- overlay: hard-rules -->
- **Never edit a vendored copy to make anything pass.** A defect there is an upstream finding: fix it in the source repo, release or bump it there, and re-vendor as its own commit. A local patch is reverted silently by the next copy.
- **Do not bump versions or write CHANGELOG entries.** That is `/dev-copilot:bump-version`'s job, and a changeset's CHANGELOG entry is usually already written by the work itself.
- **Do not tag.** If the changeset needs a release tag, that is a separate, deliberate act.
- **One repo, one agent.** Concurrency is per repo; two agents in one working tree will interleave `git add` and stage each other's files.
