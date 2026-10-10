---
description: Record every comment and reply on the Ka0s addons' CurseForge pages in the collection's journal, threaded and with author and date. Claude classifies each new comment as bug report, feature request, feedback or general. Then it walks you through the unfiled bug reports and feature requests one at a time and files the ones you accept as GitHub issues in the addon's repo. The scope is the addon at the cwd, the addons you name, or `all`. The journal lives in Ka0sAddonsCommonTasks/journal/curseforge and never in an addon repo or this plugin. Needs a CurseForge Core API key. Pushes only with `push`.
argument-hint: [all | <Addon>...] [push] [--dry-run] [--no-issues]
allowed-tools: [Bash, Read, Write, AskUserQuestion]
---

Record the CurseForge comments of one addon, several addons or the whole roster in the collection's
CurseForge journal. Classify what is new, and turn the bug reports and feature requests the owner
accepts into GitHub issues.

This is half of a pair. `/dev-copilot:wow-curseforge-releases` records the files and download counts.
Both write to the same journal, whose `README.md` is the schema. Design:
`docs/superpowers/specs/2026-10-10-curseforge-journal-design.md` in this plugin.

## Before anything — confirm this is a WoW repo

Run `dev-copilot-profile` (Bash; if not found, `"${CLAUDE_PLUGIN_ROOT}/bin/dev-copilot-profile"`). It prints `profile=`, `kind=`, `repo=`, `name=`, `root=`, `reason=`.

- **`profile=generic`**: print exactly this and stop: "`/dev-copilot:wow-curseforge-comments` is for the Ka0s WoW collection; this repo is detected as generic (<reason>). Add a `.dev-copilot` file with `profile=wow` to override." Do nothing else.
- **`profile=wow`**: continue. With no addon named, `kind` must be `addon`. From `Ka0sAddonsCommonTasks` or any other non-addon repo, the user names addons or passes `all`.

## Step 1 — Parse the arguments

`$ARGUMENTS` holds the scope words plus flags that may appear anywhere:

- `push`: push the journal commit after making it. Without it, never push.
- `--dry-run`: fetch and show, but write, classify, file and commit nothing.
- `--no-issues`: skip the issue hand-off (Step 5). The candidates stay for the next run.

What is left is the scope: nothing (the addon at the cwd), `all` (every roster addon), or roster
Folder names, matched ignoring case.

## Step 2 — Resolve the scope

Run `ka0s-curseforge scope <scope words>`. If the bare name is not found, use
`"${CLAUDE_PLUGIN_ROOT}/bin/ka0s-curseforge"`. The rules are the same as in
`/dev-copilot:wow-curseforge-releases`:

- The roster comes from `ADDONS.md`, and the project id from the TOC's `## X-Curse-Project-ID:` line.
- An addon without an id is skipped and listed.
- The script refuses a journal inside an addon repo or this plugin. **Journal data never goes into
  either.**

On exit code 2, print the error and stop.

Check that the journal repo is on its default branch (`master`) with no uncommitted changes under
`journal/curseforge`. If it isn't, report it and stop.

## Step 3 — Fetch and record

Run `ka0s-curseforge comments <scope words>` (add `--dry-run` if given) and keep its JSON. Note its
`ts`, because later steps key on it.

The comments come from the CurseForge site's own endpoint, which is undocumented. The script walks every
page, flattens the reply threads, dedupes by id and merges into `<Addon>/comments.json`:

- A new comment gets `firstSeen`.
- A comment whose text changed gets `editedAt`, and its class is cleared so it is classified again.
- A comment that vanished gets `deleted` and `deletedAt`. Rows are never removed.

The output lists, per addon, `new`, `edited`, `deleted`, `total` and `warnings`. A `totalCount`
mismatch is a warning to report, not hide. It also lists `pending`: every comment that still needs a
class, with its thread context (`parentText`, `ownerReplied`).

A shape error means the site changed its endpoint. Report it as such and stop for that addon; never
fall back to scraping the page.

## Step 4 — Classify

Skip this step on `--dry-run`.

Read each `pending` comment, using its parent text where it is a reply. Give each exactly one class:

| Class | Use it when |
|---|---|
| `bug` | Something does not work as intended: an error, a Lua error, wrong behavior, a regression after an update, a conflict with another addon. |
| `feature` | It asks for something new or changed: an option, a module, support for a class or spec, a different default. |
| `feedback` | An opinion on existing behavior, with no defect and no ask: praise, a complaint about how something looks or feels, a UX remark. |
| `general` | Everything else: thanks, a question the docs answer, a reply that only acknowledges, chat. |

- **A mixed comment takes the most actionable class**, in the order `bug` > `feature` > `feedback` >
  `general`. "Love it, but it errors on login" is a `bug`.
- **Judge a reply in its thread.** "Still broken" under the owner's "fixed in 1.1" is a `bug`.
- Give each verdict a `confidence` between 0 and 1 and a one-line `reason` that names what in the text
  decided it. Use a confidence below 0.6 when the text is ambiguous, and say so in the reason.
- The owner's comments are never pending, so they are never classified.

Write the verdicts as a JSON list to the session scratchpad, never into a repo:
`[{"addon": "...", "commentId": 123, "class": "bug", "confidence": 0.9, "reason": "..."}]`. Then run
`ka0s-curseforge classify <that file>`. It rejects a verdict for an owner comment, a comment with an
`override`, or an unknown class. Report any rejection rather than forcing it.

Then show the new comments grouped by class, each with its author, date, a one-line gist, and whether
the owner has replied.

## Step 5 — Issue hand-off

Skip this step on `--dry-run` or `--no-issues`.

Run `ka0s-curseforge handoff <scope words>`. It lists every `bug` and `feature` comment (an `override`
wins over `class`) that has no `issueRef` and is not deleted, newest first, with the addon's GitHub
`repo`. If the list is empty, say so and move on.

Say once, before the first question, that **an issue filed here is public**.

Take the candidates **one at a time**. For each, show the comment, its thread, the class and reason, and
whether the owner has replied. Ask with AskUserQuestion:

- **File it**: draft the issue the way `/dev-copilot:issue-add` does in a WoW repo.
  - **Title:** a plain statement of the problem or request. No status prefix and no severity word.
  - **Labels:** `state:untriaged`, a `severity:` label chosen against the collection's severity ladder
    that `issue-add` uses in a WoW repo, `bug` or `enhancement` to match the class, and
    `source:curseforge`.
  - **Body:** the CurseForge comment URL, the author and date, the comment quoted (and its parent when
    it is a reply), and the classification reason. A short note on what to check first is optional.

  Show the draft and get approval before filing. Once approved:
  1. Make sure the labels exist on the addon's repo with `gh label create --force`. That covers the
     four `state:` and four `severity:` labels exactly as `issue-add` defines them, plus
     `gh label create "source:curseforge" --color f16436 --description "Reported in a CurseForge comment" --force`.
  2. Run `gh issue create -R <repo> --title ... --body-file <scratch file> --label ...`.
  3. Record the issue with `ka0s-curseforge issue <Addon> <commentId> <repo>#<n>`.

  Wait a few seconds between creates. Bulk GitHub writes get rate-limited.
- **Not an issue**: run `ka0s-curseforge issue <Addon> <commentId> declined`. That comment is never
  offered again.
- **Stop here**: end the hand-off. What is left stays unfiled and comes back on the next run. Silence is
  never a decision.

Use the `gh` CLI subcommands only, never `gh api graphql`. If `gh` is missing or unauthenticated, say
so, skip the hand-off and leave every candidate as it is.

## Step 6 — Report and commit

Skip this step on `--dry-run`.

Run `ka0s-curseforge report-comments <ts> <scope words>` with the `ts` from Step 3. It writes
`reports/<YYYYMMDD-HHMMSS>-comments.md` from the journal itself: what was new, edited or deleted in
that run, the issues filed, and the bug and feature comments still unfiled.

```bash
git -C <journalRepo> add journal/curseforge
git -C <journalRepo> commit -m "curseforge: comments run <ts>: <n> new comments, <k> issues filed" -m "<trailers>" -- journal/curseforge
```

Commit only the `journal/curseforge` path, directly on the default branch, with the session's
attribution trailers. Make no commit if nothing under the journal changed. Push with
`git -C <journalRepo> push` only when `push` was given.

## Never

- Never write journal data anywhere except the journal folder: not into the addon, not into this plugin.
- Never edit `comments.json` by hand, except that the owner may set `override` on a comment. A run
  never touches an `override`.
- Never file an issue the owner has not approved, and never reply on CurseForge. There is no API for it,
  and the site is not to be driven.
- Never print the API key.
