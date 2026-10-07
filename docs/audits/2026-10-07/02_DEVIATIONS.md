# 02 — Deviations: dev-copilot (2026-10-07, standard v2.76.1)

Prefix **`DC-`**, assigned on this first audit. Repo kind: **documentation-and-tooling**, so the run uses the documentation lane. Grades follow the lane's rule: impact is **reproduction**.

- **High:** the defect changes the output of a run somebody has already made.
- **Medium:** it will change the next run.
- **Low:** a reader notices it and works around it.
- **Info:** an observation.

A doc-only failure graded Low still names the MUST it fails.

## Register read

There is no `docs/ARCHITECTURE.md` and so no `## Documented deviations` register. The issue store is empty (0 issues). Root `CLAUDE.md` carries no accepted-deviation note, and there is no `docs/scope.md` and no `LEDGER.md`. **No gap below is covered by a ratified row**, so every row counts. No `state:will-not-do` issue exists without a row, because no issue exists.

## Tally

| Basis | High | Medium | Low | Info | Total | MUST failures |
|---|---|---|---|---|---|---|
| **Headline: roots only** | 0 | 2 | 7 | 1 | **10** | **9** |
| **Including `derived from` dependents** | 0 | 2 | 9 | 2 | **13** | **11** |

The MUST failures are counted the same way. All nine root MUST failures are graded Medium or Low. DC-13 fails no MUST. Of the dependents, DC-02 and DC-03 fail MUSTs and DC-04 is a partially met MUST recorded as Info.

## Deviations

| ID | Section | Grade | MUST? | Description | Fix direction |
|---|---|---|---|---|---|
| **DC-01** | `documentation-§8` (Substitutes #3), `documentation-§3` | Low | MUST | `docs/ARCHITECTURE.md` is absent. A documentation-and-tooling repo **MUST** carry it with five sections: Overview, Module Map (as a file-and-path map), Known Limitations, `## Documentation map` and `## Documented deviations`. `CLAUDE.md:119` says the repo "is *not* bound by the addon doc set", which is true, but it never mentions the reduced hub §8 still requires. | Author `docs/ARCHITECTURE.md` with exactly the five sections. Move or point the file-and-path map from `CLAUDE.md:21-40`. Name the URL- and path-addressed surfaces (`bin/` names, `hooks.json` script paths, `profiles/wow/<name>.md`, `~/.claude/dev-copilot/bin/ka0s-bounded`) as breaking to rename. |
| DC-02 | `documentation-§3` (`## Documented deviations`), `audit-review-history` | Low | MUST | *derived from DC-01.* There is no deviation register, so this repo has nowhere to ratify a decline. DC-12 cannot be accepted until it exists. | Add the heading, even if its only content is "None". File DC-12's row there if the owner keeps feature branches. |
| DC-03 | `documentation-§3` (`## Documentation map`) | Low | MUST | *derived from DC-01.* There is no Documentation map. The four `.md` files under `docs/superpowers/` belong to a store `documentation-§3` names as frozen, so the map owes that store one line and no per-file rows. | Name `docs/superpowers/` once as an out-of-scope store, plus `docs/audits/` once this bundle lands. |
| DC-04 | `documentation-§8` (*if executable content appears*) | Info | MUST (partially met) | *derived from DC-01.* The repo has a Python test harness (52 cases) and executable hooks. Its re-read of `lint`, `testing` and `automated-tests` is recorded only as rows in `DEPENDENCIES.md:88-95`, because there is no hub to record it in. | Record the outcome in the new hub's Known Limitations. Say that the Lua trigger has not fired and that the Python suites are the commit gate. |
| **DC-05** | `documentation-§8` (Substitutes #3), `documentation-§3` (the register's single home), `audit-review-history` | **Medium** | MUST | `agents/wow-standards-audit.md:82` tells every documentation-lane run that "neither repo has a `docs/ARCHITECTURE.md`", and on that basis redirects the register read to root `CLAUDE.md` plus the issue store. That is false for `WowAddonStandards`, which has carried `docs/ARCHITECTURE.md` with `## Documented deviations` since `56e9e29` (2026-09-16). It also contradicts the rule the agent executes, because §8 makes that file a MUST for this kind. The sentence was true when written (`92fe8df`, 2026-09-07) and went stale nine days later. Every future WAS or dev-copilot audit that follows it skips the real register. | Rewrite the sentence: the register is `docs/ARCHITECTURE.md` § `## Documented deviations` in both repos (dev-copilot's arrives with DC-01). Keep the issue store as the second input, as for addons. |
| **DC-06** | `documentation-§5` (the matcher contract stated at `CLAUDE.md:37`) | **Medium** | MUST | The bounded-runs hook **denies** the ordinary tool-presence probe `command -v lizard` (and `command -v luacheck lua`). `bounded_runs.py:37` treats `command` as a transparent wrapper and skips its `-v`, which leaves the probed tool name in command position. `CLAUDE.md:37` promises "false positives on ordinary commands … are not" acceptable, and the test suite covers `which luacheck lizard` (`test_bounded_runs.py:85`) but not `command -v`. Reproduced in this run, which the hook blocked. | In `strip_prefix`, treat `command -v`/`-V` (and `type`/`hash`, already harmless) as a lookup, not a run: when `command` is followed by `-v` or `-V`, the words are not a command. Add `command -v lizard` and `command -V luacheck` to `test_mentions_are_not_runs`. |
| **DC-07** | `documentation-§5` | Low | MUST | The phase-2 close (`1cfe0b5`, `af92781`) left stale text in six places. The **frontmatter descriptions** the dispatcher reads still name the documentation repos as "(WowAddonStandards, wow-addon)" (`agents/wow-standards-audit.md:3`, `commands/wow-standards-audit.md:2`), and so does `README.md:73`. The bodies were corrected (`agents/…:28`, `commands/…:19`). `CLAUDE.md:110` lists "the legacy symlink and journal paths, the detector's `tooling` rule" as intentional live `wow-addon` mentions, but `CLAUDE.md:82` and `af92781` removed all three. `CLAUDE.md:91` says the bounded-runs tests cover "both symlinks", but one symlink remains. `README.md:5,51` and both manifest descriptions list the WoW repos as addon, `LibKa0s` and `WowAddonStandards`, leaving out the `tooling` kind the detector table on `README.md:14` defines. | One sweep: replace `wow-addon` with `dev-copilot` in the two descriptions and `README.md:73`, cut `CLAUDE.md:110`'s list down to what survives, change "both symlinks" to "the runner symlink", and add the tooling kind to `README.md:5,51` and the manifest descriptions, keeping both manifest descriptions identical. |
| **DC-08** | `documentation-§7` (evidence-based; MUST NOT drift), `documentation-§5` | Low | MUST | `DEPENDENCIES.md` has drifted. **Inventory** (`:12-13`): it says "61 tracked files: 43 Markdown … 3 design/plan notes", but the tree has 62, 44 and 4 (the phase-2 plan was added after `e2c827d`). **Citations:** `scripts/bounded-runs-hook.sh:33` is past the end of a 31-line file (the `python3` call is now `:30`). `profiles/wow/finalize.md:28-29` points at a blank line and a heading, while the Lua and luacheck gate is at `:31-34`. `commands/wow-revendor-libka0s.md:316` is the code fence, and the command is at `:317`. **Version floors** (`:44-47`: python ≥ 3.8, git ≥ 2.34, perl ≥ 5.10, coreutils ≥ 8.30) carry no reason. §7 asks for a version only where one matters, with the reason. `CLAUDE.md:38`'s `docs/` inventory also omits the phase-2 plan. | Recount from `git ls-files` and re-cite the three lines. Either give each floor its reason or replace it with "any recent", as §7 does for `lizard`. Add the phase-2 plan to `CLAUDE.md:38`. |
| **DC-09** | `documentation-§5` (the lane's worked-example and inventory checks) | Low | MUST | Worked examples in the specs no longer match the trees they cite. **LootHistory** (`commands/wow-new-addon.md:155,157`): `Compat.lua:194-201` is now `:210-217`, and `:213-214`/`:237` are now `:229-230`/`:253`. **PrettyChat** (`:161-162`): "4957 lines of loaded source … 120-line `locales/enUS.lua`" now measures 6292 and 132. **MultiMeters** (`commands/wow-revendor-libka0s.md:214`): `settings/Schema.lua:670`'s `C.LSMValues` no longer exists anywhere in the repo, but the text reads as a live defect. `OptionsCompose.lua:182` is now `:245-248` at v1.70.0. `commands/wow-revendor-libka0s.md:322` says a consumer `.luacheckrc` "usually excludes `libs/` and `tests/`", but **0 of 11** do: all exclude only `tests/_kit/`, as `lint` requires. `profiles/wow/agent-review.md:313` says "seven of the eleven repos", and the census is now 11 of 11. `:314-317`'s "359 hits" quotes no command, and its claim that "every one … lives in `GlobalStrings/GlobalStrings.lua`" fails any `SLASH_` grep, which also hits `_006`, `_009`, `_021` and `_022`. That paragraph violates the count-with-command rule it teaches (`:320-321`). `profiles/wow/bump-version.md:298` says "five addons … are permanent perf-skippers", but four lack `core/PerfSetup.lua` and three lack `tests/perf.lua`. | Re-derive each figure and quote the current `file:line`. Mark historical examples as dated ("as of <date>/<SHA>"), or re-measure them. Give the 359 figure its command and scope, or drop the number. |
| **DC-10** | `line-endings-§3` | Low | MUST | `agents/wow-standards-audit.md:343` says check (c) is "`*.sh text eol=lf` is present, mandatory in **both** kinds", but `line-endings-§3` makes `*.py text eol=lf` mandatory beside it, and `AUDIT.md`'s own (c) greps `^\*\.(sh|py)`. A run reading the agent before the playbook under-checks. The fetched playbook is authoritative and mitigates this, so the grade is Low. | Name both carve-outs in the agent's (c). |
| **DC-11** | `localization-§5` | Low | MUST | 37 British spellings appear in live specs and root docs: `labelled` ×13, `catalogue` ×15, `honour` ×3, `cancelled` ×3, `generalis`, `summaris` (a step **heading**, `commands/wow-revendor-libka0s.md:409`) and `judgement`. Another 5 sit in dated design notes under `docs/superpowers/`. Filed as **one** rolled-up finding. The standard itself writes *quirks catalog*. | One sweep over the live specs with the canonical `BRITISH`/`ALLOWED` lists. Leave `docs/superpowers/` alone as dated record. |
| **DC-12** | `versioning-git` (trunk-based) | Low | MUST | `CLAUDE.md:111` makes feature branches (`feat/<date>-<topic>`, merged `--no-ff`) the standing workflow. `versioning-git` **MUST**s trunk-based work and branching "only when the human explicitly asks". There is no register row (DC-02). The practice is collection-wide and owner-directed (Ka0sAddonsCommonTasks `CLAUDE.md`), so this is a decision to record, not a behavior to reverse. | Once DC-02 exists, file a `## Documented deviations` row ratifying the feature-branch flow with its reason and a re-check trigger, or raise it upstream (see Upstream observations). |
| **DC-13** | `versioning-git` (hygiene) | Info | — | `origin/main` still points at `d2ed30d` ("Initial commit … yay!", 2026-06-20), an ancestor of `master`. The repo's default branch is `master`. | Delete the remote `main` branch on the owner's go-ahead. |

## Upstream observations (not counted; they belong to `WowAddonStandards`' own audit)

Each of these is a standard-side text issue found while measuring this repo. Each is reported to its owner rather than filed here.

- **U-1:** `line-endings-§7` says "Every repo **MUST** carry the vendored EOL gate `tests/_kit/test_eol.lua`", while `documentation-§8` applies `line-endings` *unchanged* to a kind for which `testing` does not apply. §7 itself concedes "the two repos that run no suite at all", but the MUST is not scoped. This is a contradiction between two MUSTs.
- **U-2:** In `documentation-§8`, the *if executable content appears* row names three triggers ("a Lua file, a test harness or a script complex enough to have a failure mode") and then says "The trigger … **the first `.lua` file**". dev-copilot meets the second and third and not the first.
- **U-3:** `versioning-git`'s trunk-based MUST matches neither the collection's practice (cross-repo exercises on same-named feature branches) nor `WowAddonStandards/CLAUDE.md:117` ("branch when a changeset genuinely warrants isolation").

## Confirmed compliant (not entries)

These all pass:

- The line-ending policy (a)-(e) and the §5 body diff.
- No `TODO.md`.
- All 270 `filename-§N` citations are in range, and no retired notation appears outside example blocks.
- Every `commands/`, `agents/` and `profiles/wow/` path named resolves.
- Every `/dev-copilot:<name>` resolves.
- Every overlay `Step N` resolves in its base.
- `check_overlays.py` returns `OK: 13 overlays`.
- All 52 Python cases are green.
- The manifests parse.
- Folder casing is correct.
- `CLAUDE.md` and README meet substitutes 1 and 4.
- The issue store is clean: no LEDGER and no `[status]` prefixes.
- The counts in `CLAUDE.md:30-35` are correct: 22/14/8 commands, 2 agents, 13 overlays.
- The runner defaults in `README.md:78` match `scripts/ka0s-bounded:54-68`.
- The `AceConsole-3.0.lua:86` and `:89-95` citations in `profiles/wow/agent-review.md:339-340` are correct.
- `CLAUDE.md:83`'s "thirty-two `.lua` files as of v1.66.0" is correct as dated. v1.70.0 has 34.
