---
description: GitHub issue counts — a status × repo grid, a severity × repo grid over the open backlog, and a status × severity crosstab, plus a short read of what the numbers imply. Defaults to the repo at the cwd; pass `all` for several repos (the ones you name, or the sibling checkouts), or a repo name. Counts only — for the issues themselves use `/dev-copilot:issue-details`. Read-only apart from repairing a missing status label.
argument-hint: [here|all|<repo>]
allowed-tools: [Bash, Read]
---

Report the state of pending work by reading GitHub issues, as counts.

## Step 0 — Detect the repo profile

Run `dev-copilot-profile` (Bash; if not found, `"${CLAUDE_PLUGIN_ROOT}/bin/dev-copilot-profile"`). It prints `profile=`, `kind=`, `repo=`, `name=`, `root=`, `reason=`.

- **`profile=wow`** — Read `<root>/profiles/wow/issue-summary.md` now. Each of its sections names a hook point in this spec (`<!-- overlay: <id> -->`) and says whether it **adds to** or **replaces** that section; `extra` sections say where they run. Apply them as you go. `kind` (`addon`, `library`, `standards`, `tooling`) refines WoW behavior where the overlay says so.
- **`profile=generic`** — follow this spec as written. Do not read the overlay.

This command can span several repos, so detection runs **per repo**: once at the cwd (which decides how the scope in Step 2 resolves), then `dev-copilot-profile <path>` for each repo in scope. A WoW repo's overlay applies only to that repo's portion of the report. If the cwd is not inside a git repo (an orchestration folder above several checkouts), also run `dev-copilot-profile` on each git checkout directly under it; if any reports `profile=wow`, read the overlay for the scope step as well.

This is the wide view in the issue command family:

- `/dev-copilot:issue-audit` — sweeps a repo and **files** what it finds as `state:untriaged`
- `/dev-copilot:issue-triage` — **decides** the untriaged ones, one at a time
- `/dev-copilot:issue-summary` — **how much, how bad, and where** (this command). Counts only; it never lists issues.
- `/dev-copilot:issue-details` — **what**, item by item with descriptions
- `/dev-copilot:issue-fetch-all` — a plain listing of one repo
- `/dev-copilot:issue-add` — files one new issue by hand

## Step 1 — Preflight

`gh auth status` — if `gh` is missing or unauthenticated, say so, tell the user to run `gh auth login`, and stop.

**GitHub API guardrail.** Issue work goes through the `gh` CLI subcommands — here that is `gh issue list` with `--json`. **Never use `gh api graphql`** or a hand-rolled query against `api.github.com/graphql`: agents reach for GraphQL first, spend a round trip on a deprecated path, and fall back to the subcommand that would have worked. Because status and severity are **labels**, every count below comes from the `labels` array on `gh issue list --json number,title,state,labels` — never from a title prefix, never from a `--search`.

## Step 2 — Resolve the scope

The `$ARGUMENTS` token:

<!-- overlay: scope -->
- **absent, or `here`** → the repo at the cwd. **This is the default.**
- **`all`** → the repos the user names (in the request, or as further repo tokens after `all`); if none are named, the git checkouts beside the cwd repo in its parent folder — or, when the cwd is not itself inside a repo, the checkouts directly under it — that have a GitHub remote `gh` can resolve. Say in the report how the list was formed (named, or discovered on disk): a discovered list can silently omit a repo, and a missing repo in a cross-repo report reads as "no open issues" rather than "not checked".
- **a repo name** → that repo alone: an `owner/name` is used as given; a bare name is matched case-insensitively against the sibling checkout folders. If it matches nothing, say so, list the valid names, and stop. Don't guess at a near-miss — reporting the wrong repo silently is worse than asking.

A one-row grid is still a useful report (the crosstab in 4c carries it), but the command earns most of its keep across repos: when the default `here` lands on a single repo, say in one line that `all` gives the cross-repo comparison.

If the cwd is not a repo `gh` can resolve and no scope was given, **ask** which scope to use — typically `all`, from an orchestration folder above several checkouts — rather than guessing.

## Step 3 — Fetch

For each repo in scope, one call:

```
gh issue list -R <owner>/<repo> --state all --limit 500 --json number,title,state,labels,createdAt,url
```

- A repo that has no GitHub remote, doesn't exist, or that `gh` can't read is **not** a zero — record it as **unreadable** and carry that through to the report as its own state. A permission error rendered as `0` is a wrong answer, not a tidy one.
- If any repo hits the `--limit`, say so rather than reporting a truncated count.
- On an `all` run, space the calls out slightly; this is a read sweep over several repos.

## Step 4 — Classify

Every issue is classified twice, both times from its **labels**:

**Status** — exactly one `state:` label:

| Column | Label | Expected GitHub state |
|---|---|---|
| `done` | `state:done` | closed |
| `will-not-do` | `state:will-not-do` | closed |
| `triaged` | `state:triaged` | open |
| `untriaged` | `state:untriaged` | open |

**Severity** — exactly one `severity:` label: `severity:critical`, `severity:high`, `severity:medium`, `severity:low`.

**Every issue always carries one of each.** There is no unlabelled column, because there is no unlabelled state — an issue that arrives without a `state:` label (filed from the GitHub web UI, or by someone not using these commands) is **repaired on sight**:

- open → `gh issue edit <n> --add-label "state:untriaged"`
- closed → `state:done` if it was closed as completed, `state:will-not-do` if closed as not planned (`gh api repos/{owner}/{repo}/issues/<n>` reports `state_reason`)

An issue with no `severity:` label is **not** repaired here. Severity is a judgment call that needs the body read against the ladder, and this command deliberately doesn't read bodies. Count it in a **`—` column** on the severity grid, say how many there are, and point at `/dev-copilot:issue-audit`, which assigns one on sight. A guessed severity from a title alone would land in a grid people then reason from, and a fabricated number in a counts report is worse than a visible gap.

A **legacy `[status]` title prefix** is leftover text from the retired prefix scheme. If the label and the prefix disagree, the **label wins**. Don't strip the prefix here — that is a title edit, and this command's one sanctioned write is adding a missing status label. Note any issue where they disagree under *Inconsistencies*.

**This is the only write this command makes, and every repair must appear in the report**, with the issue number and the label added. A command people run to look at things must never change one quietly; announcing it is what keeps that true. If a repair fails, count the issue under `untriaged` anyway and say the label could not be added.

**Report any label/state disagreement** — a `state:triaged` issue that is closed, a `state:done` issue that is open, an issue carrying two `state:` labels — as a short **Inconsistencies** list under the grids, with repo, number and both values. The label and the open/closed state encode the same decision twice, so a disagreement means one of them is wrong and a human has to say which. Don't fix them, don't count them twice; surface them and point at `/dev-copilot:issue-triage`.

## Step 5 — The grids

Three cuts, in this order. They answer different questions and none of them is derivable from another.

### 5a. Status × repo — how much, and where

| Repo | done | will-not-do | triaged | untriaged | Total |
|---|---:|---:|---:|---:|---:|

On an `all` run: one row per repo in the order Step 2 resolved them, then a totals row. On a single-repo run it is one row and the totals line below carries the useful part.

- Right-align the numbers. Write `0` as `—` so the populated cells carry the eye.
- An unreadable repo gets a single `unreadable` spanning its row rather than four zeros.

### 5b. Severity × repo, **open issues only** — how bad the live backlog is

| Repo | critical | high | medium | low | — | Open |
|---|---:|---:|---:|---:|---:|---:|

**Open only, and say so in the heading.** Closed issues are settled: the severity of something already done or already declined tells you nothing about what to do next, and folding it in lets a repo with a long `done` history look dangerous. The actionable question this grid answers is *how much of what is still on the books is serious*, and that question is about `state:untriaged` + `state:triaged` alone.

The `—` column is issues with no `severity:` label. Keep it even when it is empty on every row: a column that vanishes when the data is clean is a column nobody notices when the data isn't.

### 5c. Status × severity — where the serious work is stuck

One small crosstab over the **whole scope**, all repos combined:

| | critical | high | medium | low | — |
|---|---:|---:|---:|---:|---:|
| untriaged | | | | | |
| triaged | | | | | |
| done | | | | | |
| will-not-do | | | | | |

This is the cut that says something neither of the other two can. `untriaged × critical` is the cell to read first — serious work nobody has even been asked about. `triaged × critical` is the second: serious work someone consciously parked. `will-not-do × critical` deserves a sentence of its own if it is non-zero, because declining something graded critical is a real decision and it should not pass as a number in a table.

On a single-repo run this grid is still worth printing; it is the same shape and it is the whole report's payload once the per-repo dimension collapses.

### Under the grids

State the totals in one line: how many issues, how many **open**, how many of those are `state:untriaged`, and how many open issues are `critical` or `high`. Those last two numbers are the backlog nobody has decided on and the part of it that is serious, and they are the two worth reading first.

## Step 6 — Read the grids

**This command prints counts and what they mean. It does not list issues.** Per-issue tables — titles, descriptions, ages, URLs — are `/dev-copilot:issue-details`, and duplicating them here would mean two commands doing the same job with the shorter one always out of date.

So after the grids, write a few sentences of analysis. Not a restatement of the numbers the reader can already see — the things the numbers *imply* that a column of totals does not show on its own:

- **Concentration.** Which repo carries a disproportionate share of the open work, and how disproportionate. One repo holding a third of the scope's open issues is a fact about that repo, not about the whole.
- **Severity concentration is a different fact from volume.** A repo with four open issues, two of them `high`, is in worse shape than one with twenty `low`. Say so where the grids show it, and say so explicitly when volume and severity point at different repos — that divergence is the single most useful thing these two grids produce together.
- **The `untriaged` count**, and how much of it is serious. This is the backlog nobody has decided on and it is the first number worth reading. Zero across the board is worth stating plainly — it means every open issue has a recorded decision behind it.
- **Anything critical or high that is `triaged` rather than open work.** Something graded serious and consciously parked is the most interesting row, in either direction: either the grade is wrong or the parking is.
- **Shape of the closed work.** A repo whose `will-not-do` outnumbers its `done` is deciding more than it is building; the reverse is the opposite. Neither is wrong, and both are worth noticing.
- **Unlabelled severity.** A large `—` column means the backlog has not been sized, so the severity grid is measuring less than it appears to. Say how much of it is unsized before drawing any conclusion from it.
- **Empty repos.** A repo with no issues at all is either genuinely clear or never swept. The grid cannot tell those apart, so say which one you can and cannot distinguish. A repo with no `state:` labels at all has never been swept — that one the grid *can* tell you.
- **Movement**, only where you can source it — a figure from a previous run in this session, for instance. Never infer a trend from a single snapshot.

**Ground every observation in the grids.** If a claim cannot be checked against a number in a table above it, it does not belong here. No recommendations the counts do not support, no guesses about why a repo looks the way it does, and no advice about what to work on next — that is a judgment the reader makes with context this command does not have.

Keep it to a short paragraph or a few bullets. The grids are the deliverable; the analysis earns its place only by saying something they do not.

## Hard rules

- **Read-only, with exactly one exception:** adding a missing `state:` label. Never create, close, reopen or comment, never edit a title or a body, and **never assign a severity** — that needs the body read and belongs to `/dev-copilot:issue-audit`.
- **Never list issues.** No per-repo tables of titles, no URLs. Counts and analysis only — `/dev-copilot:issue-details` owns the per-issue view, and two commands printing the same listing means the shorter one silently goes stale.
- **The severity grid is open-only.** Folding closed issues into it makes a well-maintained repo look dangerous and is the one way these grids can actively mislead.
- **Never assert what the grids cannot support.** Every sentence of analysis traces to a number in a table. No trends from one snapshot, no advice on what to work on next.
- **Announce every repair**, with the issue number and the label added.
- **Never use `gh api graphql`.** Use the `gh issue` subcommands with `--json`. `gh api repos/{owner}/{repo}/issues/<n>` is the sanctioned REST fallback for `state_reason`, which `gh issue view` does not expose on every `gh` version.
- **Never report an unreadable repo as zero.** Unreadable and empty are different answers, and collapsing them hides exactly the repo someone needs to look at.
- **Never infer status or severity from the title.** The labels are the data; a leftover `[triaged]` prefix is stale text, and a title that sounds alarming is not a `severity:critical`.
- **Never hide the `—` column.** An unsized backlog is a finding, not a rounding error.
<!-- overlay: roster-rule -->
- **Don't invent the repo list.** Use the repos named, or the ones discovered on disk, and say which.
