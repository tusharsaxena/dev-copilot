# 04 — Technical design: dev-copilot remediation (2026-10-07)

This is the design for closing every DC-* row in `02_DEVIATIONS.md`. The audit changes nothing itself: everything below is for a separate remediation engagement. Every change is to documentation or specs except **DC-06**, which touches `scripts/bounded_runs.py` and its test.

## Design principles

- **The standard is pointed at, not copied.** The new hub states this repo's own facts and cites `documentation-§8` for the exemptions. It does not restate them (§8: "restating it per repo is the duplication it exists to end").
- **One sweep per root.** DC-07, DC-08, DC-09 and DC-11 are each a single edit pass with a recorded command, not file-by-file work items.
- **Re-derive, don't re-type.** Every count and `file:line` written during remediation is produced by a command run at that moment, in line with the evidence rule this audit applied.
- **The overlay checker stays green.** Any edit to `commands/`, `agents/` or `profiles/` re-runs `python3 scripts/check_overlays.py` and the three unit tests (`CLAUDE.md:87-92`).

## DC-01 (with DC-02, DC-03, DC-04): author `docs/ARCHITECTURE.md`

Create `docs/ARCHITECTURE.md` with **exactly** the five sections `documentation-§8` names, in this order:

1. `## Overview`: two paragraphs covering what the plugin is (one plugin, two profiles), the repo kind (`kind=tooling` via `.dev-copilot`, documentation-and-tooling under `documentation-§8`), and how it is consumed (the Claude Code marketplace, `/reload-plugins`).
2. `## Module Map`, as the **file-and-path map**. Move the content of `CLAUDE.md` § *Module/package map* (`:21-40`) here and leave a one-line pointer in `CLAUDE.md`, or keep it in `CLAUDE.md` and point the hub at it. Pick one home; never two copies. It must add the column §8 asks for: **which paths are addressed by name or URL and are therefore breaking to rename**. Those are:
   - `bin/dev-copilot-profile` and `bin/ka0s-bounded` (bare names on PATH).
   - `scripts/bounded-runs-hook.sh` and `scripts/normalize-eol.sh` (named in `hooks/hooks.json`).
   - `scripts/ka0s-bounded`, the symlink target behind `~/.claude/dev-copilot/bin/ka0s-bounded`, which the standard's `AUDIT.md`, the agents and every addon's specs name.
   - `profiles/wow/<name>.md` (read by path at run time).
   - `commands/<name>.md` and `agents/<name>.md` (their filenames are the public `/dev-copilot:<name>` surface).
3. `## Known Limitations`. Carry the **DC-04** record here: the `lint`/`testing`/`automated-tests` re-read for `documentation-§8`'s executable-content clause. The Lua trigger has not fired (0 `.lua`). The Python suites (`scripts/test_*.py`, 52 cases) and `check_overlays.py` are the repo's commit gate. The scripts are on no complexity gate, by decision. Also record known matcher limits: false negatives on exotic shell are accepted.
4. `## Documentation map`. **DC-03.** Root docs (README, CLAUDE, DEPENDENCIES) are outside `docs/` and are not rows. Name the frozen stores once each: `docs/superpowers/` (dated design and plan notes) and `docs/audits/` (this bundle onward), plus `docs/reviews/` once one is committed. Register `docs/ARCHITECTURE.md` itself or not: it is a MAY, and neither choice is a finding.
5. `## Documented deviations`. **DC-02.** It may hold exactly one row (DC-12) or the word **None**. Each row carries its Rule (`filename-§N`), Decision, Reason, Decided date, evidence ids and re-check trigger, per `documentation-§3`.

Also update `CLAUDE.md:119`'s closing parenthesis so it says the repo is bound by §8's reduced hub, and name the file.

Risk: low. No spec reads `docs/ARCHITECTURE.md` from this repo at run time. Ordering: DC-01 lands before DC-12's row and before DC-05's rewrite, so the rewrite can say "both repos carry it" truthfully.

## DC-05: fix the audit agent's register substitution

`agents/wow-standards-audit.md:80-86` (*Which of the mechanical checks below apply*): replace "neither repo has a `docs/ARCHITECTURE.md`, so the ratified-decision register is the root `CLAUDE.md` plus the repo's own GitHub issue store" with: the register is `docs/ARCHITECTURE.md` § `## Documented deviations`, which `documentation-§8` requires in both documentation-and-tooling repos, read alongside the issue store and root `CLAUDE.md` exactly as for an addon. Add that a missing hub is itself a `documentation-§8` finding (Substitutes #3) and not a reason to read elsewhere.

Keep the wrapper `commands/wow-standards-audit.md` consistent with this (it does not currently repeat the claim). Risk: none at run time. Because the agent is fetched from the installed plugin, the fix reaches the collection on the next `/reload-plugins` after release.

## DC-06: stop the bounded-runs hook refusing `command -v`

`scripts/bounded_runs.py`, `strip_prefix` (`:218-…`): `command` is a transparent wrapper only when it **runs** something (`command lizard …`). With `-v` or `-V` it **looks a name up** and runs nothing. Design:

- In the `TRANSPARENT` branch, when `w == "command"` and the next word is `-v` or `-V`, return an empty word list, because the command has no run in command position.
- Leave `type`, `hash` and `which` as they are. They already pass because they are not transparent.
- Add `"command -v lizard"`, `"command -V luacheck"` and `"command -v luacheck lua"` to `test_mentions_are_not_runs` (`scripts/test_bounded_runs.py:81-86`). Add a guard case in the refused set showing that `command lizard .` is still denied.
- Update the case count in `CLAUDE.md:91` (20 → 21 if added as a new test method; unchanged if appended to the existing loop).

This changes plugin behavior, so it needs a **patch** version bump (`2.0.1 → 2.0.2`) per `versioning-git` and `CLAUDE.md:107`. Risk: very low. The change narrows a deny path and cannot introduce a false negative for a real run.

## DC-07: phase-2 descriptive-text sweep

One commit touching:

- `agents/wow-standards-audit.md:3` and `commands/wow-standards-audit.md:2`: "(WowAddonStandards, wow-addon)" becomes "(WowAddonStandards, dev-copilot)".
- `README.md:73`: "`WowAddonStandards` and `wow-addon`" becomes "`WowAddonStandards` and `dev-copilot` (this plugin)".
- `CLAUDE.md:110`: rewrite the intentional-mentions list to what survives, which is the README migration note, the `.dev-copilot` comment, two negative tests (`test_detect_profile.py:93-94`, `test_bounded_runs.py:169-170`) and this file's history. Keep the closing grep sentence.
- `CLAUDE.md:91`: "including both symlinks" becomes "including the runner symlink".
- `README.md:5`, `README.md:51`, `.claude-plugin/plugin.json:3` and `.claude-plugin/marketplace.json:12`: add the tooling kind, e.g. "WoW addon, `LibKa0s`, `WowAddonStandards` and Ka0s tooling repos". **Both manifest descriptions must stay byte-identical** (`CLAUDE.md:24`, `:106`).

Verification: `git ls-files | grep -v '^docs/superpowers' | xargs grep -n 'wow-addon'` lists only the survivors named in the new `CLAUDE.md:110`.

## DC-08: DEPENDENCIES.md re-derivation

- Regenerate the `:12-18` inventory from `git ls-files` (62 / 44 Markdown / 4 notes under `docs/`, or whatever the tree says at fix time, since DC-01 adds a fifth `docs/` file). Consider replacing exact totals with the command that produces them, so the paragraph cannot rot again.
- Re-cite `scripts/bounded-runs-hook.sh:30`, `profiles/wow/finalize.md:31-34` and `commands/wow-revendor-libka0s.md:317`.
- Version floors: for each of python ≥ 3.8, git ≥ 2.34, perl ≥ 5.10 and coreutils ≥ 8.30, either name the feature that needs it or write "any recent (no version-specific feature used)". Do not invent reasons. `documentation-§7`'s evidence MUST forbids it.
- `CLAUDE.md:38`: add `docs/superpowers/plans/2026-10-04-phase2-rename-ripple.md` (the phase-2 ledger) to the `docs/` inventory, and `docs/ARCHITECTURE.md` once DC-01 lands.

## DC-09: worked-example refresh

For each example, choose **re-measure** (it is meant to be current) or **date it** (it is historical evidence for why a rule exists):

| Site | Choice | New text |
|---|---|---|
| `commands/wow-new-addon.md:155,157` | re-measure | `LootHistory/core/Compat.lua:210-217`, reached at `:229-230` and `:253` (re-derive at fix time) |
| `commands/wow-new-addon.md:161-162` | re-measure | the TOC-loaded figure (6292) and the `enUS.lua` lines (132), with the command that produced them |
| `commands/wow-revendor-libka0s.md:214` | date it | "as of LibKa0s v1.6x / MultiMeters `<SHA>` (since fixed in `7b8efb0`)", and `OptionsCompose.lua` at the tag it was read from, or `:245-248` at v1.70.0 |
| `commands/wow-revendor-libka0s.md:322` | correct | consumers exclude `tests/_kit/` (never bare `tests/`) under `lint`, so a clean run covers the host's own tests |
| `profiles/wow/agent-review.md:313` | re-measure | "in all eleven repos" |
| `profiles/wow/agent-review.md:314-317` | fix the example to obey its own rule | state the exact `grep` and scope that produced the figure, or drop the number and keep the TOC-scope point. Correct "every one … lives in `GlobalStrings.lua`" to cover the split chunks. |
| `profiles/wow/bump-version.md:298` | re-measure or generalize | "the addons holding a `performance-§12` exemption", with no number, or the measured count |

## DC-10: agent line-ending (c)

`agents/wow-standards-audit.md:343`: "(c) `*.sh text eol=lf` **and** `*.py text eol=lf` are present, both mandatory in **both** kinds (`line-endings-§3`)".

## DC-11: US English sweep

Run the canonical-list check (E10's command) over the live tree and fix the 37 hits:

- labelled → labeled
- catalogue → catalog
- honour/honoured → honor/honored
- cancelled → canceled
- generalise → generalize
- Summarise → Summarize
- judgement → judgment

`docs/superpowers/` stays as written, because it is dated record. A heading rename in `commands/wow-revendor-libka0s.md:409` (`Summarise → Summarize`) changes no anchor that another spec cites. Verified: no spec references "Step 8 — Summarise". Optionally add the check to `scripts/` as a fourth unit test that reads the lists from the fetched standard, keeping it whole per `localization-§5`'s "copy both lists whole". This is a SHOULD-level hardening, not required for closure.

## DC-12: record the feature-branch decision

This is the owner's decision. Two options:

- **(a) Ratify.** File a `## Documented deviations` row in the new hub:
  - Rule `versioning-git`.
  - Decision: work lands on `feat/<date>-<topic>` and is merged `--no-ff`.
  - Reason: cross-repo exercises need same-named branches in every touched repo, and `finalize` enforces push order.
  - Decided date; evidence `DC-12` (this bundle).
  - Re-check trigger: the standard adopts or rejects branch-based flow.
- **(b) Upstream.** Raise U-3 in `WowAddonStandards` so `versioning-git` describes the collection's real practice, then retire the row.

Recommended: (a) now and (b) in parallel.

## DC-13: stale remote branch

`git push origin --delete main`, owner-authorized only (`Ka0sAddonsCommonTasks` git rules). No content is lost, because `main` is an ancestor of `master`.

## Upstream items (not this repo's work)

U-1 (`line-endings-§7` vs `documentation-§8` on the EOL gate), U-2 (the §8 trigger wording) and U-3 (trunk-based vs practice) go to `WowAddonStandards`. Its own documentation-lane audit or a `/dev-copilot:wow-harvest-standards` run should pick them up. Nothing here depends on them.
