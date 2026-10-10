# CurseForge journal commands — plan

Spec: `docs/superpowers/specs/2026-10-10-curseforge-journal-design.md`.
Branch: `feat/2026-10-10-curseforge-journal` in dev-copilot, and the same name in Ka0sAddonsCommonTasks
for the journal README change.

**Git is the state.** An item is done when a commit whose subject starts `<ID>: ` exists in the repo
named in the Repo column. The journal data commits (CF-08) use the journal's own subject form instead.

| ID | Repo | Item | Depends on |
|---|---|---|---|
| CF-02 | dev-copilot | Write `scripts/curseforge_journal.py` (scope, key, journal guard, HTTP, releases merge, comments merge, classify, issue, report, html-to-md) and `bin/ka0s-curseforge`, test first in `scripts/test_curseforge_journal.py` with synthetic fixtures shaped like the spike's payloads (no real CurseForge data in this repo) | — |
| CF-03 | dev-copilot | Add `commands/wow-curseforge-releases.md` | CF-02 |
| CF-04 | dev-copilot | Add `commands/wow-curseforge-comments.md`, with the rubric and the issue hand-off | CF-02 |
| CF-05 | dev-copilot | Make the five-touch documentation changes: README WoW-only table, both manifest descriptions, `CLAUDE.md` (config and state, env vars, external needs, tests list), `docs/ARCHITECTURE.md` module map, `DEPENDENCIES.md`. The version bump is left for the owner's go-ahead at finalize | CF-03, CF-04 |
| CF-06 | Ka0sAddonsCommonTasks | Bring the journal README in line with the spike: `editedAt` semantics, `pinned`, `issueRef: declined`, per-command reports, the `runs.jsonl` command field | — |
| CF-07 | dev-copilot | Check: the four existing test files, the new test file, `check_overlays.py` (`OK: 13 overlays`), manifests parse, `dev-copilot-profile` unchanged | CF-02..CF-05 |
| CF-08 | Ka0sAddonsCommonTasks | First real run: `releases all`, then `comments all` with classification, committed on master; no issue is filed without the owner, and nothing is pushed without the owner | CF-06, CF-07 |

| CF-09 | dev-copilot + Ka0sAddonsCommonTasks | Store changelogs as one `- subject (sha7)` line per commit, plus `changelogCommits` (added during CF-08, see below) | CF-08 |
| CF-10 | dev-copilot + Ka0sAddonsCommonTasks | Reports in the owner's local time (`timezone` in `journal.config.json`), the releases report as one Addon / Version / Release Date / Downloads / Changes-since table, and `report-releases` to rebuild a run's report from the journal | CF-09 |
| CF-11 | dev-copilot + Ka0sAddonsCommonTasks | The releases table sorted by addon name, and always shown in full in chat | CF-10 |
| CF-12 | dev-copilot | The comments report as conversation trees: one `[author date] snippet` node per comment, replies nested | CF-11 |
| CF-13 | dev-copilot | Links in the comments tree: the addon's comments page on its heading, authors to their profiles, issue tags to the GitHub issue | CF-12 |

## Execution notes

- **CF-08 (2026-10-10).** The first releases run produced a 5.7 MB journal, and 5.6 MB of it was
  changelogs. CurseForge's packager writes each release's changelog as the full `git log` since the
  previous tag, bodies included, and the first release carries the whole history. The owner chose to
  keep **subjects only**, because the bodies are already in each addon's public git history. CF-09
  added that, and the uncommitted first-run data was migrated in place with the same function, which
  brought it to 352 KB. A hand-written changelog with no commit lines is kept whole, up to 4000
  characters.
- **CF-08 hand-off.** Two AbsorbTracker comments were linked to existing issues (#15, #13) and two were
  declined; no new issues were filed.

- **CF-10 (2026-10-10).** The owner asked for every time a person reads to be in IST, with the
  releases table in their own layout: a Total row per addon, then one row per version. The data stays
  UTC. The report is now derived from the journal alone, so the earlier runs' reports were rebuilt in
  the new form.
- **CF-11 (2026-10-10).** The owner asked for the full table in every chat summary, not an excerpt, and
  for the addons in name order instead of by downloads.
- **CF-12 (2026-10-10).** The owner asked to see the comments themselves in the report, as a conversation
  tree with `[<author> <date>] <comment>` nodes. Chat keeps the one-line gists.
- **CF-13 (2026-10-10).** The owner asked for a link to every comment. CurseForge has none: a
  Playwright check of the comments page found no anchor, id or permalink per comment, only Reply and
  Quote buttons. The owner chose one comments-page link per addon heading, with author profile links
  on each node, and real GitHub links for issues.

## Checkpoint

After CF-07 the feature branches are complete. Report to the owner. Merging, pushing, the dev-copilot
version bump and `/reload-plugins` all wait for the owner's go-ahead.
