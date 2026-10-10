# CurseForge journal commands — design

Date: 2026-10-10. Status: agreed with the owner in conversation; this records it.

## Goal

Two WoW-only commands that keep a running journal of each Ka0s addon's CurseForge page:

- `/dev-copilot:wow-curseforge-releases`: every released file, with its tag, release type, date, game
  versions, changelog, and download count. Each run appends the counts, so the journal is a time
  series.
- `/dev-copilot:wow-curseforge-comments`: every comment and reply, threaded, with author, date and text.
  Claude classifies each comment as `bug`, `feature`, `feedback` or `general`, then walks the owner
  through filing the bug and feature comments as GitHub issues.

## Where the data goes

The journal is `Ka0sAddonsCommonTasks/journal/curseforge/`. Its `README.md` is the schema, and its
`journal.config.json` holds the owner's CurseForge username, the roster path and the schema version.
The repo is public, and the owner accepted that.

**Data is never written into an addon repo or into dev-copilot.** dev-copilot ships the commands, the
script, the classification rubric and the tests. The script enforces this: it refuses a journal path
that is inside dev-copilot or inside any roster addon.

The journal path is `$KA0S_CF_JOURNAL` when that is set. Otherwise it is
`<collection root>/Ka0sAddonsCommonTasks/journal/curseforge`, where the collection root is the parent
of the git top-level the command runs in. If the folder or its `journal.config.json` is missing, the
command stops.

## Sources (verified by a spike on 2026-10-10)

| Data | Endpoint | Auth |
|---|---|---|
| Project totals | `GET https://api.curseforge.com/v1/mods/{id}` | `x-api-key` |
| Files | `GET https://api.curseforge.com/v1/mods/{id}/files?index=N&pageSize=50` | `x-api-key` |
| Changelog | `GET https://api.curseforge.com/v1/mods/{id}/files/{fileId}/changelog` (HTML) | `x-api-key` |
| Comments | `GET https://www.curseforge.com/api/v1/mods/{id}/comments?page=N&size=20` | none |

- **The comments endpoint is undocumented.** It is the website's own call. It answered plain HTTP with
  no Cloudflare challenge, so no browser is needed. `size` is capped at 20. Pagination counts every
  comment *including replies*, but returns threads: replies nest under `replies` up to depth 2, and a
  reply whose parent fell on an earlier page comes back at top level. The fetch therefore walks pages
  until one is empty, flattens every thread, dedupes by `id` and rebuilds threads from `parentId`.
  `totalCount` is checked against the unique count, and a mismatch is reported, never hidden. Each
  comment has `id`, `text` (plain), `body` (HTML), `author.username`, `author.displayName`,
  `datePosted` (epoch ms), `parentId`, `status` and `isPinned`. There is no edit date.
- **The API key** is a Core API key from console.curseforge.com. It is read from `$CURSEFORGE_API_KEY`,
  or failing that from `~/.claude/dev-copilot/curseforge.env` (`CURSEFORGE_API_KEY=...`). The file is
  read **literally**, never sourced: the key contains `$` characters that a shell would expand. It is
  never printed, logged or written to the journal. The name is deliberately not `CF_API_KEY`, which the
  packager uses for the author upload token.
- **Changelogs** are the packager's git log. They include commit author emails that are already public
  in the addons' git history and on CurseForge.

## Scope argument (both commands)

- **No argument:** the addon at the cwd. The command refuses unless the git top-level is a roster
  addon. The roster is the `## In-scope addons` table of `WowAddonStandards/standards/ADDONS.md`.
- **`<Addon> [<Addon>...]`:** the named addons, each validated against the roster. An unknown name stops
  the run before anything is fetched.
- **`all`:** every roster addon.

The project id is the TOC's `## X-Curse-Project-ID:` line. An addon without one is **skipped and
listed**, never dropped silently. Addons on the owner's CurseForge page that are not in the roster,
such as Outfitter Reborn, are out of scope.

Flags: `push` pushes the journal commit. `--dry-run` fetches and reports but writes nothing.

## The script

`scripts/curseforge_journal.py` is stdlib-only Python 3, reached through `bin/ka0s-curseforge`, a `sh`
wrapper like `bin/dev-copilot-profile`. Subcommands:

- `scope [args]`: resolves the scope and prints JSON (`journal`, `addons[]` with `name`, `path`,
  `projectId`, and `skipped[]` with reasons). It writes nothing.
- `releases [args] [--dry-run]`: fetches the project, the files and any changelogs not yet stored, then
  writes `project.jsonl`, `files.json`, `downloads.jsonl`, `runs.jsonl` and a report. Prints a JSON
  summary.
- `comments [args] [--dry-run]`: fetches comments and merges them into `comments.json`, which sets
  `firstSeen`/`lastSeen`, `deleted` for a comment that vanished, and `editedAt` (the run that first saw
  a changed text). Prints the comments still needing a class.
- `classify <verdicts.json>`: writes Claude's verdicts (`class`, `confidence`, `reason`) into
  `comments.json`. It never touches a comment that has an `override`, and never touches the owner's
  comments.
- `issue <Addon> <commentId> <ref>`: records `issueRef` (`<repo>#<n>`, or `declined`).
- `report comments [args]`: writes the comments report once classification and filing are done, and
  appends the run to `runs.jsonl`.

Writing rules, from the journal README: append-only files are only appended to; keyed files are
rewritten with sorted keys, 2-space indent and a trailing newline, so a run's diff is exactly what
changed. Requests are spaced 0.5 s apart. A request or shape failure for one addon is recorded in that
run's `errors[]`, and the other addons continue.

## The commands

Both commands are WoW-only. Each opens with `## Before anything — confirm this is a WoW repo` and
detects the profile with `dev-copilot-profile`. Each then runs the script, reads its JSON, and owns the
parts that need judgement or a person:

- **Releases:** run the script, show what is new (files and download deltas), then commit.
- **Comments:**
  1. Run the script.
  2. Classify every comment it lists against the rubric in the command, and write the verdicts with
     `classify`.
  3. Show the new comments, grouped by class.
  4. Run the issue hand-off.
  5. Write the report, then commit.

**Classification rubric:** `bug` is something that does not work as intended (errors, wrong behavior, a
regression). `feature` asks for something new or changed. `feedback` gives an opinion on existing
behavior, such as praise, a complaint or a UX remark, with no defect and no ask. `general` is
everything else: thanks, questions answered by the docs, chat. A mixed comment takes the most
actionable class (`bug` over `feature` over `feedback` over `general`). `confidence` is between 0 and 1,
and `reason` is one line. The owner's comments are not classified; a reply from the owner marks a
thread as answered.

**Issue hand-off:** it covers `bug` and `feature` comments (after any `override`) that have no
`issueRef`, newest first, one at a time, with AskUserQuestion offering *File it*, *Not an issue* and
*Stop here*.
- *File it* drafts the issue in `/dev-copilot:issue-add`'s shape: the title carries no status or
  severity, the labels are `state:untriaged` plus a severity from the collection ladder plus
  `bug`/`enhancement`, and the body links the comment and quotes it. A `source:curseforge` label is
  added as well. The draft is shown for approval and filed with `gh issue create` in the addon's repo,
  then `issueRef` is recorded.
- *Not an issue* records `declined`.
- *Stop here* leaves the rest untouched for the next run.

Issue creation is spaced out, because the store is public.

**Commit:** `git -C <journal repo> commit -- journal/curseforge` with the subject
`curseforge: <releases|comments> run <ts>: <summary>`, made on the journal repo's default branch only.
If that repo is on another branch, the command stops and reports instead of committing. It pushes only
with `push`.

## Out of scope

- Wago and WoWInterface.
- Replying to CurseForge comments (the API has no write path).
- A combined `wow-curseforge-journal` command.
- Scheduling.

## Testing

`scripts/test_curseforge_journal.py` uses unittest with the HTTP layer stubbed by **synthetic** payloads
shaped like the spike's responses. No real CurseForge data goes into this repo. It covers:
- scope resolution, including an unknown addon, a missing project id, and refusal outside a roster addon;
- the key read literally, including a value containing `$`;
- the journal-path guard;
- files merge, append and idempotence (two runs give one new download line per file and no other diff);
- comment flattening across the reply-on-a-later-page case, dedupe, the totalCount check, deletion and
  edit detection;
- `classify` respecting `override` and owner comments;
- `issue` refs;
- HTML-to-markdown conversion of a changelog.
