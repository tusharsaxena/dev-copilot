# 05 — Execution plan: dev-copilot remediation (2026-10-07)

This plan hands off to a separate remediation engagement. Each step is tied to its DC-* ids (`02_DEVIATIONS.md`) and designed in `04_TECHNICAL_DESIGN.md`. The figures quoted here are the ones in `02`/`03`: 10 roots, 13 rows in total, 9 root MUST failures, 37 live British spellings, 62/44/4 tracked/Markdown/`docs/` files.

**Gate after every sprint** (`CLAUDE.md:87-92`):
`python3 scripts/test_detect_profile.py && python3 scripts/test_check_overlays.py && python3 scripts/test_bounded_runs.py && python3 scripts/check_overlays.py`, plus the manifest-parse one-liner. `/reload-plugins` then confirms the counts.

**Git:** one commit per step, subjects prefixed with the DC id (e.g. `DC-06: …`). Never push, merge or bump without the owner's go-ahead (the collection's git rules).

## Sprint 1: behavior and run-changing defects (Medium)

| # | IDs | Step | Done when |
|---|---|---|---|
| 1.1 | DC-06 | In `scripts/bounded_runs.py` `strip_prefix`, treat `command -v`/`-V` as a lookup (no command-position run). Add the `command -v lizard`, `command -V luacheck` and `command -v luacheck lua` pass cases and a `command lizard .` deny case to `scripts/test_bounded_runs.py`. | The reproduction loop in `03_EVIDENCE.md` §E5 prints `deny=0` for every `command -v`/`-V` probe and `deny=1` for `command lizard .`. All three unit suites are green. `CLAUDE.md:91`'s case count matches `Ran N tests`. |
| 1.2 | DC-05 | Rewrite `agents/wow-standards-audit.md:80-86` so the documentation-lane register is `docs/ARCHITECTURE.md` § `## Documented deviations` in both repos, and a missing hub is a `documentation-§8` finding. | `grep -n 'neither repo has a' agents/wow-standards-audit.md` returns nothing, and `check_overlays.py` is OK. |
| 1.3 | DC-10 | `agents/wow-standards-audit.md:343`: name `*.sh` **and** `*.py` in check (c). | `grep -n 'eol=lf. is present' agents/wow-standards-audit.md` shows both carve-outs. |
| 1.4 | DC-06 | Bump `.claude-plugin/plugin.json` `2.0.1 → 2.0.2` (patch: a fix), on the owner's go-ahead per the release rule. | Version updated in `plugin.json` only (the single source, `CLAUDE.md:23`). |

## Sprint 2: the missing hub (Low, MUST)

| # | IDs | Step | Done when |
|---|---|---|---|
| 2.1 | DC-01 | Create `docs/ARCHITECTURE.md` with exactly five sections: Overview, Module Map (the file-and-path map with its breaking-to-rename column), Known Limitations, `## Documentation map`, `## Documented deviations`. Give the file-and-path map one home (hub or `CLAUDE.md`), with a pointer from the other. | `grep -c '^## ' docs/ARCHITECTURE.md` is 5 and the headings match §8. |
| 2.2 | DC-04 | Write the executable-content re-read outcome in Known Limitations: Lua trigger not fired, Python suites as the commit gate, scripts on no complexity gate. | The paragraph cites `documentation-§8` and the 52-case total from a fresh run. |
| 2.3 | DC-03 | `## Documentation map`: name `docs/superpowers/` and `docs/audits/` once each as frozen stores. No per-file rows under them. | Every `.md` under `docs/` outside those stores appears exactly once, and no row dangles. |
| 2.4 | DC-02 | `## Documented deviations`: present, with "None" or the DC-12 row (see 4.1). | The heading exists. |
| 2.5 | DC-01 | `CLAUDE.md:119`: replace the parenthesis with a pointer to `docs/ARCHITECTURE.md` and `documentation-§8`'s reduced hub. `CLAUDE.md:38`: add the hub and the phase-2 plan to the `docs/` inventory (shared with DC-08). | Re-read both lines. |

## Sprint 3: documentation sweeps (Low, MUST)

| # | IDs | Step | Done when |
|---|---|---|---|
| 3.1 | DC-07 | Phase-2 text sweep across the agent and command descriptions, `README.md:5,51,73`, `CLAUDE.md:91,110` and both manifest descriptions (kept byte-identical). | `git ls-files \| grep -v '^docs/superpowers' \| xargs grep -n 'wow-addon'` lists only the survivors the new `CLAUDE.md:110` names. `diff <(jq -r .description .claude-plugin/plugin.json) <(jq -r '.plugins[0].description' .claude-plugin/marketplace.json)` is empty. |
| 3.2 | DC-08 | `DEPENDENCIES.md`: re-derive the `:12-18` inventory from `git ls-files` (after 2.1, `docs/` holds 5 `.md`). Re-cite `bounded-runs-hook.sh:30`, `finalize.md:31-34` and `wow-revendor-libka0s.md:317`. Give each version floor a reason or "any recent". | Every `file:line` in `DEPENDENCIES.md` re-reads to the claimed content (one pass, quoted). The counts match the commands. |
| 3.3 | DC-09 | Refresh or date the seven worked-example sites in `04_TECHNICAL_DESIGN.md` § DC-09, re-measuring each figure at fix time with its command recorded in the commit message. | Each site either matches today's tree or carries an explicit "as of <SHA/tag>". The SLASH_ example states its command and scope. |
| 3.4 | DC-11 | US English sweep over the 37 live hits, leaving `docs/superpowers/` alone. | Re-running E10's command reports `TOTAL 5`, all of them inside `docs/superpowers/`. |

## Sprint 4: owner decisions

| # | IDs | Step | Done when |
|---|---|---|---|
| 4.1 | DC-12 | Owner chooses between ratifying the feature-branch flow as a register row (Rule `versioning-git`, Decided date, evidence DC-12, re-check trigger) and raising U-3 upstream. | The row exists in `## Documented deviations`, or an upstream issue is filed and linked. |
| 4.2 | DC-13 | Owner authorizes `git push origin --delete main`. | `git ls-remote origin` shows no `refs/heads/main`. |

## Upstream hand-off (not executed here)

File U-1, U-2 and U-3 (`02_DEVIATIONS.md` § Upstream observations) against `WowAddonStandards`, or carry them into that repo's own documentation-lane audit. No step above waits on them.

## Ordering constraints

- 2.1 comes before 1.2's final wording can say "both repos carry it", but 1.2 may land first with that phrase if 2.1 lands in the same release.
- 2.1 comes before 3.2's inventory recount, because the hub changes the `docs/` count.
- 2.4 comes before 4.1(a).
- 1.4 (the version bump) waits for the owner's release go-ahead, and for 1.1 at least.
