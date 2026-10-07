# 03 — Evidence: dev-copilot (2026-10-07, standard v2.76.1)

Every `file:line` below was re-read during this run, and its text is quoted beside it. Every count gives its command, its real output and its scope. "Tracked set" means `git ls-files` from the repo root at `b43200c` (62 files). This repo has no `libs/`, no `tests/_kit/` and no generated data, so the default and whole-set scopes coincide here. Where `docs/superpowers/` (dated design and plan notes, a frozen store under `documentation-§3`) is excluded, the evidence says so.

## E0. Kind resolution and standard version

```
$ dev-copilot-profile
profile=wow  kind=tooling  repo=…/dev-copilot  name=dev-copilot  reason=override
$ cat .dev-copilot            # :3-4
profile=wow
kind=tooling
$ git ls-files '*.lua' | wc -l ; git ls-files '*.toc' | wc -l ; git ls-files 'libs/*' | wc -l ; git ls-files 'tests/*' | wc -l
0 0 0 0
```

- `ADDONS.md:61` (fetched): "| dev-copilot | [`../../dev-copilot/`](../../dev-copilot/) | https://github.com/tusharsaxena/dev-copilot |" sits under *Documentation-and-tooling repos*.
- `STANDARDS.md:1` (fetched): "# Ka0s WoW Addon Standard (v2.76.1, 2026-10-07)".
- Section files fetched: 27, discovered from the Sections list (`grep -oE '\]\((\./)?standards/[a-z0-9_-]+\.md' STANDARDS.md`).

## E1. Register read

```
$ gh issue list --state all --limit 200 --json number,title,state,labels,url        # dev-copilot
(no output: 0 issues)
$ gh label list --json name --jq '.[].name'
bug documentation duplicate enhancement good first issue help wanted invalid question wontfix
$ ls docs/ARCHITECTURE.md docs/scope.md docs/pending
ls: cannot access 'docs/ARCHITECTURE.md': No such file or directory   (likewise scope.md, pending)
$ grep -niE 'deviat|accepted|ratif|will-not-do' CLAUDE.md
122: … (complexity "Accepted" disposition prose)   129: … (state:will-not-do label definition)
```

No ratified row and no accepted-deviation note exist. `gh issue list -R tusharsaxena/wow-addon --state all` also returned 0 issues (the repo is archived: `isArchived=true`).

## E2. Line endings (`line-endings-§1`–`§5`, `§7`), all passing

```
$ test -f .gitattributes && echo PRESENT                                   → PRESENT
$ grep -n '^\* text=auto eol=\(crlf\|lf\)$' .gitattributes                 → 28:* text=auto eol=lf
$ grep -nE '^\*\.(sh|py) text eol=lf$' .gitattributes                      → 38:*.sh text eol=lf / 39:*.py text eol=lf
$ grep -c ' binary$' .gitattributes                                        → 20
$ (e) one-liner, verbatim from the agent spec / line-endings-§7              → 0
$ head -85 .gitattributes | diff <canonical non-client body, line-endings.md:255-339> -   → (empty) BODY-IDENTICAL
$ tail -n +86 .gitattributes | wc -l                                        → 0   (no appendix)
$ git ls-files --eol | awk '{print $1,$2,$3}' | sort | uniq -c
      8 i/lf w/lf attr/text
     54 i/lf w/lf attr/text=auto
$ git ls-files -s bin scripts      → all 11 entries 100755
```

Scope: the whole tracked set (62 files) with no exclusions, as the line-ending check requires.

## E3. `docs/ARCHITECTURE.md` absent (DC-01, DC-02, DC-03, DC-04)

- `ls docs` → `superpowers` (plus an untracked, in-progress `reviews/` written by a parallel run today, outside `git ls-files`).
- Standard `documentation.md:709` (fetched): "3. A **`docs/ARCHITECTURE.md`** carrying the five sections named above, including the deviation register."
- Standard `documentation.md:698`: "The mandated set here is **five**: **Overview**, **Module Map** *read as the file-and-path map* … **Known Limitations**, **`## Documentation map`**, and **`## Documented deviations`**."
- `AUDIT.md:77` (fetched): "`documentation-§8` reduces `ARCHITECTURE.md` to five sections rather than ten."
- `CLAUDE.md:119` (tail): "(This repo is `kind=tooling` and is *not* bound by the addon doc set; its root `CLAUDE.md` is a full brief by design.)"
- `CLAUDE.md:21`: "## Module/package map". This is the closest existing file-and-path map, running `:21-40`.
- DC-03: `git ls-files 'docs/*.md'` → 4 files, all under `docs/superpowers/`. Standard `documentation.md:353-355`: "`docs/superpowers/` and `docs/investigations/` are named as directories, once each."
- DC-04: `DEPENDENCIES.md:92`: "| **lizard** | **not used here** | Cyclomatic complexity over zero Lua functions is not a measurement. The six Python files and five shell scripts are on no complexity gate. |". The suites were run (E9): 17 + 15 + 20 = 52 cases.

## E4. The audit agent's false register substitution (DC-05)

- `agents/wow-standards-audit.md:82`: "substitution: neither repo has a `docs/ARCHITECTURE.md`, so the ratified-decision register is the root".
- `agents/wow-standards-audit.md:83`: "`CLAUDE.md` plus the repo's own GitHub issue store, read through `gh` under the same rules."
- `../WowAddonStandards/docs/ARCHITECTURE.md:90`: "## Documented deviations", and `:92`: "**None.**"

```
$ git -C ../WowAddonStandards log --diff-filter=A --format='%h %ad %s' --date=short -- docs/ARCHITECTURE.md
56e9e29 2026-09-16 docs: this repo gets the doc set it asks addons for, and the exemptions it needs
$ git log --all -S'neither repo has a' --format='%h %ad %s' --date=short | tail -1
92fe8df 2026-09-07 M1-WA-06: the two documents every pass runs on enter the rotation
```

- `AUDIT.md:431-433` (fetched): "`docs/ARCHITECTURE.md`'s `## Documented deviations` is the **single** home of a ratified decision (documentation-§3)".

## E5. The bounded-runs hook false positive (DC-06)

This run's own Bash call `… type lizard luacheck lua5.1` was first written with `command -v lizard luacheck lua lua5.1`, and the plugin's hook refused it:

```
PreToolUse:Bash hook error: Unbounded heavy run (lizard). Prefix it with the bounded runner: …
```

Reproduced in isolation (scope: `scripts/bounded_runs.py` fed the hook's JSON on stdin):

```
$ printf '{"tool_name":"Bash","tool_input":{"command":"<cmd>"}}' | python3 scripts/bounded_runs.py
[command -v lizard]          deny=1
[which lizard]               deny=0
[type lizard]                deny=0
[command -v luacheck lua]    deny=1
[hash lizard]                deny=0
[lizard --version]           deny=0
[man luacheck]               deny=0
```

- `scripts/bounded_runs.py:37`: `TRANSPARENT = {"env", "time", "nice", "exec", "command", "nohup", "stdbuf", "ionice"}`
- `scripts/bounded_runs.py:231-234`: `elif w in TRANSPARENT:` / `i += 1` / `` # `env -i`, `nice -n 5`, `stdbuf -oL`: skip their options `` / `while i < len(words) and words[i].startswith("-"):`. This skips `command`'s `-v`, which leaves `lizard` in command position.
- `scripts/test_bounded_runs.py:85`: `"lua tools/gen-api-members.lua", "which luacheck lizard"):`. `which` is covered and `command -v` is not.
- `CLAUDE.md:37` (tail): "False negatives on exotic shell are acceptable, false positives on ordinary commands (`grep lua tests/run.lua`, prose that names a tool) are not."

## E6. Stale rotation and kind text (DC-07)

- `agents/wow-standards-audit.md:3`: "… and the two documentation-and-tooling repos (WowAddonStandards, wow-addon) against the documentation lane; …"
- `commands/wow-standards-audit.md:2`: "… and the two documentation-and-tooling repos (WowAddonStandards, wow-addon). …"
- Corrected bodies: `agents/wow-standards-audit.md:28`: "| `WowAddonStandards`, `dev-copilot` (the plugin repo; the archived `wow-addon` before it) |". `commands/wow-standards-audit.md:19`: "`WowAddonStandards` and `dev-copilot` (the plugin repo, formerly `wow-addon`) take the **documentation".
- `README.md:73`: "The two documentation-and-tooling repos, `WowAddonStandards` and `wow-addon`, take the documentation lane."
- `CLAUDE.md:110`: "The only intentional live mentions of `wow-addon` are: the README migration note, the legacy symlink and journal paths, the detector's `tooling` rule, the audit rotation's naming of the `wow-addon` **repo** (… unchanged until phase 2), and this file's history."
- `CLAUDE.md:82`: "- **No legacy paths.** 2.0.0 shipped transitional support for the retired plugin (the hook also maintained `~/.claude/wow-addon/bin/ka0s-bounded`, `issue-triage` also read `~/.claude/wow-addon/issue-triage/`, and the detector classed a `wow-addon` ch[eckout as `tooling`)] … All three were removed".
- `scripts/test_detect_profile.py:93-94`: `# The retired wow-addon plugin repo is archived and out of the rotation: no rule names it.` / `self.assertKind(self.repo("wow-addon"), "generic", "generic")`
- `CLAUDE.md:91`: "- `python3 scripts/test_bounded_runs.py` — the bounded-runs matcher and hook script, including both symlinks (20 cases)." Compare `scripts/bounded-runs-hook.sh:16-20`, which maintains one link (`link_dir="$HOME/.claude/dev-copilot/bin"`).
- `README.md:5`: "In a WoW addon repo (or `LibKa0s`, or `WowAddonStandards`) it applies the full Ka0s WoW Addon Standard behavi[or]". `README.md:51`: "### WoW-only — WoW addon, `LibKa0s` and `WowAddonStandards` repos". `README.md:14`: "| `tooling` | the repo is the `Ka0sAddonsCommonTasks` workspace, or opts in (this repo does) | wow |". `.claude-plugin/plugin.json:3` and `marketplace.json:12` say "… via WoW overlays in WoW addon, LibKa0s and WowAddonStandards repos."

```
$ git show --stat --format='%h %s' 1cfe0b5   → agents/wow-standards-audit.md | 9 ; commands/wow-standards-audit.md | 2
$ git show --stat --format='%h %s' af92781   → scripts/bounded-runs-hook.sh | 13 ; scripts/detect_profile.py | 8 ; …
```

## E7. DEPENDENCIES.md drift (DC-08)

```
$ git ls-files | wc -l                    → 62
$ git ls-files '*.md' | wc -l             → 44
$ git ls-files 'docs/*.md' | wc -l        → 4
$ git log --diff-filter=A --format='%h %ad %s' --date=short -- docs/superpowers/plans/2026-10-04-phase2-rename-ripple.md
c878a6a 2026-10-04 Plan phase 2 of the wow-addon rename
$ git log --format='%h %ad %s' --date=short -1 -- DEPENDENCIES.md
e2c827d 2026-10-04 Rewrite CLAUDE.md and DEPENDENCIES.md for the merged plugin
$ wc -l scripts/bounded-runs-hook.sh      → 31
```

- `DEPENDENCIES.md:12`: "> The repo is 61 tracked files: 43 Markdown (22 command specs, 2 agent specs, 13 WoW overlays,"
- `DEPENDENCIES.md:13`: "> 3 design/plan notes under `docs/`, and the 3 root docs), two JSON manifests plus `hooks/hooks.json`,"
- `DEPENDENCIES.md:44` cites `scripts/bounded-runs-hook.sh:33`, which is past the end of the file. The `python3` call is `scripts/bounded-runs-hook.sh:30`: `printf '%s' "$input" | python3 "$root/scripts/bounded_runs.py" 2>/dev/null || true`.
- `DEPENDENCIES.md:81` cites `profiles/wow/finalize.md:28-29`. `:28` is blank and `:29` is "## gate-commands — replaces". The gate is `:31-34` (fence, `…ka0s-bounded lua tests/run.lua`, `…ka0s-bounded luacheck .`, fence).
- `DEPENDENCIES.md:81` cites `commands/wow-revendor-libka0s.md:316`. `:316` is "```sh", and `:317` is "cd <Addon> && ~/.claude/dev-copilot/bin/ka0s-bounded luacheck . && ~/.claude/dev-copilot/bin/ka0s-bounded lua tests/run.lua".
- Version floors: `DEPENDENCIES.md:44` "**python3** ≥ 3.8", `:45` "**git** ≥ 2.34", `:46` "**perl** ≥ 5.10", `:47` "**coreutils** (`readlink -f`, `timeout`) ≥ 8.30". None states a reason. `:43` "**bash** ≥ 4.2" does give one ("arrays, `exec {fd}>`").
- `CLAUDE.md:38`: "today that is `docs/superpowers/specs/` (the `revendor-libka0s` design from wow-addon, and the merge design) and `docs/superpowers/plans/` (the merge plan with its execution ledger)." The phase-2 plan is missing.
- The other `DEPENDENCIES.md` citations re-read correct: `hooks/hooks.json:9,20`, `scripts/ka0s-bounded:1,78,98-99,103-106,65,79`, `scripts/detect_profile.py:1,27-30,41,48,89`, `scripts/bounded_runs.py:1,29-32`, `scripts/normalize-eol.sh:15,36,52,63,68,76`, `scripts/test_detect_profile.py:25,27`, `CLAUDE.md:89-92,95,117,120,125,134,135`, `commands/wow-new-addon.md:244`.

## E8. Worked examples against the trees they cite (DC-09)

**LootHistory** (`git -C ../LootHistory log -1` → `b9c1271 2026-10-07`):
- `commands/wow-new-addon.md:155`: "`LootHistory/core/Compat.lua:194-201` hard-codes the English". `:157`: "… reaches them at `:213-214` and `:237`,".
- `grep -nE 'WARBAND_LINES|BIND_TO_WARBAND_PREFIX|UE_LITERAL|ONLY witness' core/Compat.lua` → `210:local WARBAND_LINES = {`, `216:local BIND_TO_WARBAND_PREFIX = "binds to warband"`, `217:local UE_LITERAL = "until equipped"`, `229:  if WARBAND_LINES[lower] then return true end`, `230:  return lower:sub(1, #BIND_TO_WARBAND_PREFIX) == …`, `235:-- … the tooltip is the ONLY witness …`, `253: … lower:find(UE_LITERAL, 1, true) …`. Lines `:194-201` now hold the `WARBAND_ANY_GLOBALS` list.
- `commands/wow-new-addon.md:160` "(`tests/test_compat.lua:62-65` …)" still resolves: `:63` `_G.AUCTION_HOUSE = "Auction House"`, `:64` `_G.AUCTION_WON_MAIL_SUBJECT = "Auction won: %s"`.

**PrettyChat** (`8626790 2026-10-07`). Scope: the TOC load list with `libs\` excluded (22 files: `locales/enUS.lua`, `core/*` ×12, `defaults/*` ×2, `modules/*` ×2, `settings/*` ×5):
- `commands/wow-new-addon.md:161-162`: "… across 4957 lines of / loaded source, against a 120-line `locales/enUS.lua`."
- `grep -vE '^#|^\s*$|^##' PrettyChat.toc | tr -d '\r' | grep -v '^libs' | grep '\.lua$' | tr '\\' '/' | xargs wc -l | tail -1` → `6292 total`. `wc -l locales/enUS.lua` → `132`.

**MultiMeters / LibKa0s** (`LibKa0s` latest tag `v1.70.0`):
- `commands/wow-revendor-libka0s.md:214`: "… `MultiMeters/settings/Schema.lua:670` supplies `C.LSMValues = function(mediaType) return lsmValues(mediaType)() end` … The library states the tightened half in the seam itself, at `OptionsCompose.lua:182` …".
- `grep -n 'LSMValues' ../MultiMeters/settings/Schema.lua` → no output. `git -C ../MultiMeters log -S'C.LSMValues' --oneline -- settings/Schema.lua` → `7b8efb0 CP-2a: the seven source files peeled …`, `fe264cb …`.
- `grep -n LSMValues ../LibKa0s/LibKa0s/OptionsCompose.lua` → `245:--- host's for it to close over. It takes \`O\` because the media-backed rows call O.LSMValues …`, `248:--- CONTRACT, for a host that supplies its own \`O.LSMValues\`: it MUST RETURN A FUNCTION …`. `:182` now reads `--- row rather than a canonical leaf and there is no leaf name to prefix.`
- `version-14.13.3.3-docs.md:50` still resolves: "### The one contract that tightened, for a host that supplies its own `LSMValues`".

**`.luacheckrc` claim**: `commands/wow-revendor-libka0s.md:322`: "… `exclude_files`, which in a consumer usually excludes `libs/` and `tests/`." Across all 11 addons' `.luacheckrc`, `exclude_files` lists `tests/_kit/` and never bare `tests/` (for example, AbsorbTracker: `{ "libs/", "docs/audits/", "docs/reviews/", "_dev/", "tests/_kit/" }`). Standard `lint.md:11` is the same shape.

**AceConfigCmd census**: `profiles/wow/agent-review.md:313`: "It is a comment inside vendored `AceConfigCmd-3.0.lua`, present in seven of the eleven repos."
`for r in <11 addons>; git -C $r grep -l mychat -- libs` → `libs/AceConfig-3.0/AceConfigCmd-3.0/AceConfigCmd-3.0.lua` in **11 of 11**.

**SLASH_ census**: `profiles/wow/agent-review.md:314`: "A raw-`SLASH_*` census scoped to "the repo minus `libs/`" reports **359 hits in PrettyChat**". `:316`: "reports **0**. Every one of those 359 lives in `GlobalStrings/GlobalStrings.lua`, a tracked but". `:320`: "So: derive the file list from the TOC, and **report every count with the command and the scope beside".
`git -C ../PrettyChat ls-files '*.lua' | grep -v '^libs/' | xargs grep -cE 'SLASH_' | grep -v ':0$'` → `GlobalStrings/GlobalStrings.lua:968`, `GlobalStrings_006.lua:1`, `_009.lua:16`, `_021.lua:706`, `_022.lua:245`, `tests/_kit/mock_base.lua:3`. No pattern was recorded for 359, so the figure cannot be reproduced. Its "every one" claim fails for any `SLASH_` pattern, because the split chunks carry hits too. The TOC-scoped result of **0** holds: none of the 22 loaded files contains `SLASH_`.

**Perf skippers**: `profiles/wow/bump-version.md:298`: "retro-fitted, per the hard rules — five addons in the collection are permanent perf-skippers and".
`git -C <addon> ls-files tests/perf.lua core/PerfSetup.lua` across 11: no `core/PerfSetup.lua` in BankLedger, PanelMaster, PrettyChat, WhatGroup (4). No `tests/perf.lua` in BankLedger, PanelMaster, PrettyChat (3).

**Re-read and correct:** `profiles/wow/agent-review.md:339`: "`local name = "ACECONSOLE_"..command:upper()` (`libs/AceConsole-3.0/AceConsole-3.0.lua:86`)". `AbsorbTracker/libs/AceConsole-3.0/AceConsole-3.0.lua:86`: `local name = "ACECONSOLE_"..command:upper()`, and `:89-95` hold the `SlashCmdList[name]` and `_G["SLASH_"..name.."1"]` writes.

## E9. Agent line-ending check (DC-10)

- `agents/wow-standards-audit.md:343`: "neither; (c) `*.sh text eol=lf` is present, mandatory in **both** kinds; (d) binaries are marked".
- Standard `line-endings.md:102-107`: "Both variants **MUST** carry: … `*.sh text eol=lf` / `*.py text eol=lf`".
- `AUDIT.md:177-178`: "# (c) the shebang carve-outs, both mandatory in BOTH kinds (line-endings-§3)" / "grep -nE '^\*\.(sh|py) text eol=lf$' .gitattributes".

## E10. US English (DC-11)

The command applies the canonical lists extracted verbatim from `localization.md` (`BRITISH` 92 entries, `ALLOWED` 33, matching the published counts). `ALLOWED` is removed as whole words first, then `BRITISH` substrings are matched case-insensitively per line:

```
$ python3 -I uscheck.py british.txt allowed.txt <repo>      # scope: git ls-files, all 62 tracked files
TOTAL 42        (37 outside docs/superpowers/, 5 inside it)
```

Hits outside `docs/superpowers/`, by token:
- `labelled` ×13: `CLAUDE.md:133`, `README.md:42`, `commands/issue-audit.md:2,45,104,179,218`, `commands/issue-details.md:73`, `commands/issue-summary.md:74,76,142`, `commands/issue-triage.md:87`, `commands/wow-harvest-standards.md:61`.
- `catalogue` ×15: `CLAUDE.md:144`, `README.md:61`, `agents/wow-standards-audit.md:127`, `commands/wow-harvest-standards.md:67,184`, `commands/wow-new-addon.md:235`, `commands/wow-revendor-standards.md:29,142,144,149,150,159,162`, `profiles/wow/bump-version.md:217`, `profiles/wow/sync-docs.md:241`.
- `honour` ×3: `commands/finalize.md:93`, `commands/issue-fetch-all.md:66`, `scripts/bounded_runs.py:52`.
- `cancelled` ×3: `agents/wow-standards-audit.md:215`, `commands/wow-standards-audit.md:38`, `profiles/wow/agent-review.md:529`.
- `generalis` `CLAUDE.md:141`. `summaris` `commands/wow-revendor-libka0s.md:409` ("## Step 8 — Summarise → `05_SUMMARY.md`, and report in chat"). `judgement` `commands/wow-revendor-standards.md:172`.

Inside `docs/superpowers/specs/2026-08-24-revendor-libka0s-design.md`, excluded as dated record: `:31` judgement, `:95,:103` normalis, `:194` colour, `:211` behaviour.

The standard's own term is "catalog": `grep -o -i 'quirks catalog[a-z]*' STANDARDS.md` → `quirks catalog` ×2. No `quirks catalogue` appears.

## E11. Trunk-based workflow and the stale branch (DC-12, DC-13)

- `CLAUDE.md:111`: "… work lands on a feature branch (`feat/<date>-<topic>`) merged into `master` with `--no-ff`, then the branch is deleted; …"
- Standard `versioning-git.md:13`: "- **MUST** work trunk-based: commit directly to the addon's default branch. Do **NOT** create feature/topic branches for routine work — branch **only** when the human explicitly asks".
- `../WowAddonStandards/CLAUDE.md:117`: "- **Trunk-based.** Work directly on the current branch (usually `master`) by default; branch when a".

```
$ git log -1 --format='%h %ad %s' --date=short origin/main     → d2ed30d 2026-06-20 Initial commit ... yay!
$ git merge-base --is-ancestor origin/main master && echo yes  → yes
$ gh repo view --json defaultBranchRef --jq .defaultBranchRef.name → master
```

## E12. Documentation-lane checks that passed

```
# filename-§N range check. Scope: all 62 tracked files.
$ git ls-files | xargs grep -noE '\b[a-z][a-z-]+-§[0-9]+' | wc -l        → 270
  ranges from each fetched section's '^### N.' headings (e.g. options-ui max 18, testing 15, documentation 9)
  → OUT-OF-RANGE options-ui-§41 (commands/wow-revendor-standards.md:116,266)
  → UNKNOWN-SECTION perf-§2 (commands/wow-revendor-standards.md:115)
```

All three are illustrations of malformed and out-of-range forms. `:115` reads "an abbreviated filename (`perf-§2` for `performance`)". `:116` reads "`options-ui-§41` against a file whose own heading count … is far short of 41". `:266` is in the example report block.

```
# retired global notation. Scope: all 62 tracked files.
$ git ls-files | xargs grep -cE '(^|[^-a-z])§[0-9]+(\.[0-9]+)?' | grep -v ':0$'
commands/wow-revendor-standards.md:5      (lines 112, 251, 264, 266, 267, all example text)

# anti-pattern numbers cited: #1 #3 #34 #43 #45 #47 #48 #49 #50 #51 #52 #53 #54 #55 #58 #59 #65 #77 #85 #90 #92
# anti-patterns.md range: 1..92 (92 entries). All in range, and each sampled entry's subject matches its use.

# path references (commands/ agents/ profiles/wow/ scripts/ bin/ hooks/), excluding docs/superpowers:
  every hit resolves, except fixtures and placeholders: profiles/wow/agent-X.md (CLAUDE.md:61),
  profiles/wow/ghost.md (scripts/test_check_overlays.py:56), scripts/tasks (commands/sync-docs.md:59, a generic example)
# /dev-copilot:<name>: every name resolves to commands/ or agents/ (the "wow-<x>" hits are placeholders)
# intra-spec and overlay→base "Step N": every reference resolves to a heading (0 misses)
# upstream fixed paths: AUDIT.md, NEW_ADDON.md, AUTOMATED_TESTS.md, PERF_ANALYSIS.md,
#   standards/STANDARDS.md, standards/ADDONS.md, standards/NEW_ADDON_CONTEXT.md all exist at
#   WowAddonStandards origin/master (git cat-file -e)
```

## E13. The repo's own suites (documentation lane, run as evidence for the stated counts)

```
$ python3 scripts/test_detect_profile.py    → Ran 17 tests … OK
$ python3 scripts/test_check_overlays.py    → Ran 15 tests … OK
$ python3 scripts/test_bounded_runs.py      → Ran 20 tests … OK
$ python3 scripts/check_overlays.py         → OK: 13 overlays   (exit 0)
$ python3 -c "import json; [json.load(open(f)) for f in (plugin.json, marketplace.json, hooks.json)]" → manifests OK
```

These match `CLAUDE.md:89-92` ("(17 cases)", "(15 cases)", "(20 cases)", "prints `OK: 13 overlays`").

## E14. Not applicable (stated, not skipped)

`luacheck`, the headless Lua runner, the sighted complexity suite, `lizard`, both vendored `diff -r`, the provenance-line greps, the re-vendor bundle census, the packaging dot-entry checks and the disabled-state census have nothing to bind to: 0 `.lua`, 0 `.toc`, 0 `libs/`, 0 `tests/_kit/`, no `.pkgmeta` (E0). The tools themselves are installed on this machine (`type` → `/home/tushar/.local/bin/lizard`, `/usr/local/bin/luacheck`, `/usr/bin/lua5.1`). The checks are inapplicable, not "not run".
