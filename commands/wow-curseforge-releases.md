---
description: Record every Ka0s addon release on CurseForge in the collection's journal. For each file it captures the tag, release type, date, game versions, changelog and download count, appends this run's download counts, reports what is new since the last run and commits the journal. The scope is the addon at the cwd, the addons you name, or `all`. The journal lives in Ka0sAddonsCommonTasks/journal/curseforge and never in an addon repo or this plugin. Needs a CurseForge Core API key. Pushes only with `push`.
argument-hint: [all | <Addon>...] [push] [--dry-run]
allowed-tools: [Bash, Read]
---

Record the CurseForge release history of one addon, several addons or the whole roster in the
collection's CurseForge journal, and say what changed since the last run.

This is half of a pair. `/dev-copilot:wow-curseforge-comments` records the comments; this command
records the files and their download counts. Both write to the same journal, whose `README.md` is the
schema. Design: `docs/superpowers/specs/2026-10-10-curseforge-journal-design.md` in this plugin.

## Before anything — confirm this is a WoW repo

Run `dev-copilot-profile` (Bash; if not found, `"${CLAUDE_PLUGIN_ROOT}/bin/dev-copilot-profile"`). It prints `profile=`, `kind=`, `repo=`, `name=`, `root=`, `reason=`.

- **`profile=generic`**: print exactly this and stop: "`/dev-copilot:wow-curseforge-releases` is for the Ka0s WoW collection; this repo is detected as generic (<reason>). Add a `.dev-copilot` file with `profile=wow` to override." Do nothing else.
- **`profile=wow`**: continue. With no addon named, `kind` must be `addon`. From `Ka0sAddonsCommonTasks` or any other non-addon repo, the user names addons or passes `all`.

## Step 1 — Parse the arguments

`$ARGUMENTS` holds the scope words, plus two flags that may appear anywhere:

- `push`: push the journal commit after making it. Without it, never push.
- `--dry-run`: fetch and report, but write and commit nothing.

What is left is the scope: nothing (the addon at the cwd), `all` (every addon in the roster), or one or
more addon names as they appear in the roster's Folder column (`AuraMaster`, `KickCD`). Matching
ignores case.

## Step 2 — Resolve the scope

Run `ka0s-curseforge scope <scope words>`. If the bare name is not found, use
`"${CLAUDE_PLUGIN_ROOT}/bin/ka0s-curseforge"`. It prints JSON: `journal`, `journalRepo`, `addons[]`
(name, path, repo, projectId) and `skipped[]` (with a reason).

The script owns the rules, so do not work around them:

- The roster is the `## In-scope addons` table of `WowAddonStandards/standards/ADDONS.md`, found
  through the journal's `journal.config.json`. An addon on the owner's CurseForge page that is not in
  the roster is out of scope.
- The project id is the TOC's `## X-Curse-Project-ID:` line. An addon without one is skipped and
  listed, never dropped silently.
- The journal is `$KA0S_CF_JOURNAL`, or `Ka0sAddonsCommonTasks/journal/curseforge` beside the repo at
  the cwd. The script refuses a journal inside an addon repo or inside this plugin: **journal data never
  goes into either.**

On exit code 2, print the script's error line and stop. Typical causes are an addon not in the roster,
a cwd that is not an addon, or no journal found. Never write journal files by hand to get around it.

Before going further, check that the journal repo can take the commit:
`git -C <journalRepo> branch --show-current` must be the repo's default branch (`master`). If it is
not, or if `git -C <journalRepo> status --porcelain -- journal/curseforge` shows uncommitted journal
changes, report it and stop. Someone else's journal edit must not be swept into this run's commit.

## Step 3 — Fetch and record

Run `ka0s-curseforge releases <scope words>` (add `--dry-run` if given). The script:

- reads the Core API key from `$CURSEFORGE_API_KEY` or `~/.claude/dev-copilot/curseforge.env`. On a
  missing key it stops with an error that tells the owner where the key goes. **Never print, echo or
  write the key**, and never pass it on a command line.
- fetches the project, every file, and the changelog of each file not yet in the journal, spacing
  requests 0.5 s apart.
- writes `<Addon>/files.json` (one record per file, written once), and appends to
  `<Addon>/downloads.jsonl`, `<Addon>/project.jsonl` and `runs.jsonl`. It also writes
  `reports/releases/<YYYYMMDD-HHMMSS>-releases.md`.
- prints a JSON summary: per addon, `totalDownloads`, `downloadDelta`, `newFiles`, `removedFiles` and
  `files[]` with each file's `downloads` and `delta`. It also prints `skipped`, `errors` and `report`.

A failure for one addon lands in `errors` and the rest continue. Report every error. Do not retry in a
loop: a 403 from the Core API means the key is wrong or revoked, which only the owner can fix.

## Step 4 — Report

**Every time shown is local time**, in the journal's timezone: `timezone` in
`journal.config.json` (an IANA name such as `Asia/Kolkata`), or the machine's own when it is unset. The
journal's data stays in UTC; only what a person reads is converted. The script's JSON already carries
`tsLocal` and, per addon, `sinceLocal` (the previous run, or `null` on a first run), and its report file
is named and written in local time.

**The report file holds the full table; the chat summary does not.** The report
(`reports/releases/<YYYYMMDD-HHMMSS>-releases.md`) lists every addon and every file. In chat, show only **two rows
per addon**: its `Total` and its **latest release** (the newest file). Never paste the full table into
chat; link the report file for it. Take both rows from the script's JSON, which formats them the way the
report does: per addon, `totalDownloads` and `totalChange`, and `latest` (`version`, `releaseDate`,
`downloads`, `change`), or `null` when the addon has no files yet, in which case show the `Total` row
alone.

It is one table for the whole run, with the addons in name order (A to Z, ignoring case):

```
| Addon | Version | Release Date | Downloads | Changes since <sinceLocal> |
|---|---|---|---:|---|
| AbsorbTracker | Total | - | 2025 | +9 |
|  | 1.12.0 | 2026-10-09 23:00 IST | 72 | +11 |
| AuraMaster | Total | - | 34 | +0 |
|  | 1.1.0 | 2026-10-09 23:00 IST | 9 | +0 |
```

The report file's table has the same columns and order, with every file row under each `Total`, newest
release first.

- **Version** is the file's display name without a `-release` suffix. A `-beta` or `-alpha` suffix is
  kept, because it says something.
- **Changes since** is a signed change (`+3`), or `—` for a file or project with no earlier count.
- The header names the previous run's time when every addon that has a previous run shares it. An addon
  on its **first run** does not change that: its rows show `—`, and a `First run for:` line under the
  table names it. Only when the previous runs really differ does the header read
  `Changes since last run`, with a line under the table giving each addon's own previous run.

Below the table, list the new releases, any files no longer listed, and anything skipped or failed, with
the reason. Link the report file. Don't paste whole changelogs; they are in `files.json`.

To rebuild a run's report from the journal, for example after the timezone changes, run
`ka0s-curseforge report-releases <run-ts> <scope words>`. The report is derived from the journal alone.

## Step 5 — Commit

Skip this step on `--dry-run`.

```bash
git -C <journalRepo> add journal/curseforge
git -C <journalRepo> commit -m "curseforge: releases run <ts>: <n> new files across <m> addons" -m "<trailers>" -- journal/curseforge
```

Commit only the `journal/curseforge` path, directly on the default branch. A journal run is data, so it
takes no feature branch. End the message with the session's attribution trailers. If the run changed
nothing, say so and make no commit; that can't happen in practice, because every run appends counts.

Push with `git -C <journalRepo> push` only when `push` was given. Otherwise, say the commit is local.

## Never

- Never write journal data anywhere except the journal folder: not into the addon, not into this plugin.
- Never edit `files.json`, `downloads.jsonl` or `project.jsonl` by hand. The script owns them, and
  hand edits break the append-only history.
- Never print the API key.
