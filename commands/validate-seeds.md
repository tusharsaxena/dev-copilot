---
description: Re-validate a repo's seed data (hand-curated or generated id lists) against its upstream source for one flavor, by the procedure the repo itself declares in docs/validate-seeds.md — check for a newer source build, freeze it, derive candidates, rule only what is new (rulings recorded as data), apply, regenerate, gate. Each repo brings its own scripts and nuances; this command supplies the loop and its rules. Commits only when passed `commit`.
argument-hint: <repo name> <flavor> [commit] [--build <version>]
allowed-tools: [Read, Glob, Grep, Bash, Edit, Write]
---

Re-validate one repo's seed data for one flavor against the upstream it is derived from. Seed data
here means an id list a repo ships that mirrors a source it does not own: spell or item ids taken
from a game client's data tables, a list of codes from a registry, and so on. Such a list drifts
one upstream release at a time, and nothing in the repo turns red when it does.

**This command owns the loop. The repo owns the procedure.** Every repo that supports it carries a
**seed-validation contract** at `docs/validate-seeds.md`. The contract names the flavors, the
scripts, the files they write, the precedent a ruling must follow and the gate. This command reads
that contract and runs it under the rules below, so two repos with different tools, sources and
nuances get the same discipline. A repo without a contract is not guessed at.

## Step 0 — Detect the repo profile

Run `dev-copilot-profile` (Bash; if not found, `"${CLAUDE_PLUGIN_ROOT}/bin/dev-copilot-profile"`). It prints `profile=`, `kind=`, `repo=`, `name=`, `root=`, `reason=`.

- **`profile=wow`** — Read `<root>/profiles/wow/validate-seeds.md` now. Each of its sections names a hook point in this spec (`<!-- overlay: <id> -->`) and says whether it **adds to** or **replaces** that section; `extra` sections say where they run. Apply them as you go. `kind` (`addon`, `library`, `standards`, `tooling`) refines WoW behavior where the overlay says so.
- **`profile=generic`** — follow this spec as written. Do not read the overlay.
- **Neither invocation works** (no detector on PATH, and no plugin root substituted) — treat the repo as `profile=generic`, say so in one line, and do not read any overlay.

The profile that decides is the **target repo's**, not the cwd's. Once Step 1 has resolved the
target, run the detector on it (`dev-copilot-profile <target path>`). If that profile differs from
the cwd's, apply (or drop) the overlay by the target's profile.

## Step 1 — Resolve the target and the flavor

Parse `$ARGUMENTS` as words: the first is the **repo name**, the second the **flavor**. `commit`
anywhere turns on the commit in Step 8. `--build <version>` pins a source build instead of the
newest one. An overlay applied in Step 0 may define more pins of the same `--<name> <value>` form
for its own sources; pass each one through as that overlay says. A pin that no applied overlay
defines means stop, with the usage line. Missing either of the first two words means stop: print the usage line
(`/dev-copilot:validate-seeds <repo name> <flavor> [commit] [--build <version>]`). Then list the
repos that offer validation and their flavors, read from each contract's `## Flavors` table, using
the search below.

Resolve the repo name to a checkout, and never guess:

1. If the cwd's git top-level is named exactly that (case-insensitive), that is the target.
2. Else look for a sibling directory of that name next to the cwd's git top-level, then next to
   its parent (a workspace repo such as `Ka0sAddonsCommonTasks` sits beside the repos it serves).
3. Else stop, and say where you looked.

The target must hold `docs/validate-seeds.md`. If it does not, stop and say that this repo declares
no seed validation, naming the contract path it would need. Do not improvise one from the repo's
tools: the contract is where the repo's own rules live, and a run without them is a run without its
precedent.

<!-- overlay: flavor -->
Read the contract whole. Its `## Flavors` table lists the flavors it supports. The flavor argument
must match one row exactly, case-insensitively. Otherwise stop and print the supported flavors. Read
that flavor's section, `## Flavor: <flavor>`, and the contract's shared sections (`## Rules`,
`## Gate`, and any `## Notes`).

### The contract's shape

A contract is ordinary Markdown with these headings. This command reads them by name, so the names
are the interface:

| Heading | Holds |
| --- | --- |
| `## Flavors` | A table, one row per flavor: the flavor name, the upstream source and product, the seed files it governs and the tools that do the work. |
| `## Rules` | The repo's standing rules for every flavor: which files only the tools may write, where its rulings live and who writes them, the precedent a ruling must follow, the privacy rules. |
| `## Flavor: <name>`, one per flavor | Subsections in this order: `### Status`, `### Freeze and derive`, `### Rule`, `### Apply`, `### After`, `### Stage`. Each holds the exact commands, with `<date>`, `<build>` and `<bundle>` placeholders, plus that flavor's nuances. |
| `## Gate` | The commands that must all be green before the hand-back. |
| `## Notes` (optional) | Anything else a run must know: known gaps, issues that track them, sizes, timings. |

A contract may add sections; it may not drop one this table names. A missing section means stop and
say which one. A contract that runs on assumptions is how a list goes stale without anyone noticing.

## Step 2 — Rules that hold for every run

These hold whatever the contract says. Where a contract is stricter, the stricter rule wins:

- **Clean tree first.** In the target, `git status --porcelain` must print nothing. Otherwise show
  it and stop: the run writes a bundle and a commit, and must not sweep up unrelated work.
- **One date.** Take `date +%F` once and use that `<date>` everywhere. Never let a tool read the
  clock.
- **A candidate is a proposal, never a conclusion.** Upstream data says what is possible, not what
  belongs. Every candidate gets a ruling with a one-line reason, recorded through the contract's
  ruling tool, which is the only writer of the rulings file. Never hand-edit a rulings file, and
  never hand-edit a file the contract says only its tools write.
- **Precedent is never re-litigated.** A ruling already recorded stands, and so does every source
  of precedent the contract's `## Rules` names (earlier reviews, curation notes, owner rulings).
  When a candidate looks like something precedent already decided, follow the precedent and cite it
  in the reason.
- **Rule by evidence.** Read each candidate's own data, plus any evidence store the contract names
  (usage logs, telemetry, an earlier review), before ruling. When the evidence is thin, say so in
  the reason. Never invent a citation.
- **Stop on a failed gate inside the tools.** If a coverage gate, sentinel check or refusal in the
  contract's commands fails, show its output and stop. The fix is in the pipeline, not the
  rulings.

## Step 3 — Status

Run the flavor's `### Status` commands. If they report the newest bundle **current** for the source's
newest build, and no `--build` (or overlay pin) was given, say so and **stop**: there is nothing
to do. Otherwise note the build this run is for, either the new one or the pinned one.

## Step 4 — Freeze and derive

Run the `### Freeze and derive` commands with `<date>` and `<build>` filled in. Report what they print
that the contract says to report: candidate counts by group, flag counts, the unruled count.

## Step 5 — Rule what is new

Run the `### Rule` section's listing command, which prints every unruled key. Rule each one under
Step 2 and the flavor's own guidance. Write every ruling to a TSV in the session's scratchpad (not
the repo), then record them with the contract's recording command, and re-run the listing: it must
report nothing unruled. When a candidate belongs somewhere other than where it was proposed, do
what the contract says (typically: reject it here and add a hand candidate with its reason).

## Step 6 — Apply and regenerate

Run the `### Apply` commands in the order written. Run its report or summary command before its
apply command when the contract says so. Then do every duty the `### After` section lists: rolled
test snapshots, regenerated derived files, a hand-written analysis in the bundle, new manual checks.

<!-- overlay: gate -->
## Step 7 — Gate

Run every command in the contract's `## Gate`. All must be green. **If any is red, show the output
and stop without committing**; the owner decides what happens next.

## Step 8 — Hand back, and commit only if asked

Summarize:

- the repo, the flavor and the build pair (previous to new);
- what was accepted, grouped as the contract groups it, with ids;
- how many were rejected, and why, in broad strokes;
- the flags and their rulings;
- any regenerated file's delta.

Then:

- **Without `commit`:** stop. List the paths to stage, taken from the flavor's `### Stage`, plus any
  test, doc or citation edits the run made.
- **With `commit`:** stage exactly those paths (never `-A` or `.`). Commit with the message form the
  contract's `### Stage` gives, or `Seeds (<flavor>): re-validated against <build> (<date>)`, with the
  summary as the body. **Never push.**
