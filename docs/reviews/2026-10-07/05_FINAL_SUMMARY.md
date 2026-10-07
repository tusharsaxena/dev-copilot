# 05 — Final summary: dev-copilot review, 2026-10-07

*Written on the assumption that every change in `02_PROPOSED_CHANGES.md` landed per `04_EXECUTION_PLAN.md` and every row of `03_SMOKE_TESTS.md` passed. Until the sign-off table is filled in, this is the intended record, not a shipped one.*

## Headline

The plugin's safety net now does what its documentation says:
- The bounded runner's time limit stops the whole process tree rather than just its first process.
- The bounded-runs hook no longer blocks a harmless `command -v luacheck`, and it now catches heavy runs wrapped in `bash -c`.
- The line-ending hook no longer turns a symlinked file into a copy, and it finally has an automated test.

The four issue commands agree on what "the whole collection" means, so a collection triage now reaches LibKa0s, WowAddonStandards and dev-copilot. A few specs that broke the plugin's own rules were corrected: a shared `/tmp` path, an implied push, and a recovery step that could never succeed. The docs were brought back in line with the tree.

## Counts

Critical fixed: 0, High fixed: 0, Medium fixed: 7, Low fixed: 8.

Deferred: none required. F-011, the baseline refresh, is marked optional. If the owner skips it, the overlay's own "tag moved → stale brief" rule continues to cover it.

## Changes by theme

### A: the safety net does what it says
- **What changed:** Outside a terminal, `ka0s-bounded` times out the whole process group, and it recomputes its slot count while it waits. The hook treats `command -v` as a lookup, scans `sh -c` strings, and no longer counts `ulimit -v unlimited` as a bound.
- **Why it mattered:** A timed-out run could leave children running and holding a slot while the runner reported them stopped. A plain tool probe was refused with a misleading message.
- **Findings / changes:** F-001, F-002, F-008, F-013 / C-01, C-02, C-08, C-09.
- **Files:** `scripts/ka0s-bounded`, `scripts/bounded_runs.py`, `scripts/test_bounded_runs.py`.

### B: the byte-rewriting hook gets a harness
- **What changed:** A new `scripts/test_normalize_eol.py` has 8 cases: both arms, no `eol`, binary in a CRLF repo, symlinked file, symlinked directory, and garbage input. The hook now resolves a symlinked file to its target before rewriting.
- **Why it mattered:** It is the only hook that changes user bytes, and it was validated by hand only. A symlink was being silently replaced by a regular file.
- **Findings / changes:** F-003, F-006 / C-03, C-04.
- **Files:** `scripts/normalize-eol.sh`, `scripts/test_normalize_eol.py`.

### C: one collection
- **What changed:** In a WoW repo, `issue-audit`, `issue-triage`, `issue-summary` and `issue-details` all read `all` as every row of `ADDONS.md`: addons, library and repos. The archived `wow-addon` clause is gone.
- **Why it mattered:** Summary showed upstream issues that no `all`-scope audit or triage could reach.
- **Findings / changes:** F-004, F-010 (part) / C-05.
- **Files:** `profiles/wow/issue-audit.md`, `issue-triage.md`, `issue-summary.md`, `issue-details.md`, `README.md`.

### D: specs follow the plugin's own rules
- **What changed:**
  - The cross-addon pass uses a `mktemp` roots file.
  - `wow-new-addon` has `Edit` and commits the roster row on a branch without pushing.
  - `finalize` describes a push rejection as a stop.
- **Why it mattered:**
  - Parallel reviews could read each other's partial file.
  - The roster could be clobbered or pushed unasked.
  - `finalize` described a recovery that could not happen.
- **Findings / changes:** F-005, F-007, F-012 / C-06, C-07, C-10.
- **Files:** `profiles/wow/agent-review.md`, `commands/wow-new-addon.md`, `commands/finalize.md`.

### E: documentation drift
- **What changed:**
  - The `DEPENDENCIES.md` inventory is restated with its command, and its citations are re-resolved.
  - The stale `wow-addon` mentions in `CLAUDE.md` and `README.md` are removed.
  - The `tooling` kind is named in the README and both manifest descriptions.
  - The test-temp-dir cleanup also lands in this pass.
  - Optionally, the cross-addon baseline is re-measured.
- **Findings / changes:** F-009, F-010, F-011, F-014, F-015 / C-11, C-12.
- **Files:** `DEPENDENCIES.md`, `CLAUDE.md`, `README.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `profiles/wow/agent-review.md`, `scripts/test_bounded_runs.py`.

## API / behavior changes

- `ka0s-bounded`: without a TTY, a timeout now kills the wrapped command's whole process group. Exit codes 124 and 137 and their messages are unchanged. With a TTY, `--foreground` is kept.
- `ka0s-bounded`: the slot count follows current `MemAvailable` while waiting. `KA0S_KIT_SLOTS` still overrides it.
- Bounded-runs hook:
  - `command -v|-V <tool>` is allowed.
  - `bash|sh -c "<heavy run>"` is denied.
  - `ulimit -v unlimited` no longer counts as a hand bound.
- Line-ending hook: edits through a symlinked file normalize the target and keep the link.
- WoW `issue-audit all` and `issue-triage all` now include `LibKa0s`, `WowAddonStandards` and `dev-copilot`. `issue-summary` and `issue-details` drop `wow-addon`.
- `wow-new-addon`: gains the `Edit` tool. The roster row is committed on a branch and never pushed.
- No config keys, environment variables, commands or agents were added or removed.

## Migration notes

None. There is no data or state format change. `~/.claude/dev-copilot/` is untouched.

## Dependency changes

None. Everything stays stdlib Python and Bash. The bash ≥ 4.2 floor in `DEPENDENCIES.md:43` is unchanged.

## Test movement

Before (measured 2026-10-07):
- detector 17
- checker 15
- bounded-runs 20
- no line-ending tests

After (expected):
- detector 17
- checker 15
- bounded-runs 21
- line-ending 8 (new file)

`CLAUDE.md:89-92` and `:9` ("Three unit-test files" → four) move in the same change, along with `DEPENDENCIES.md`'s short-version block. There is no badge or generated inventory in this repo.

## Known follow-ups

- **F-011:** baseline refresh, if skipped. Low value, and the overlay already handles a moved tag.
- **Release:** 2.0.1 → 2.0.2 through `/dev-copilot:bump-version` when the owner releases. Not part of this cycle.

## Verification evidence

- `docs/reviews/2026-10-07/03_SMOKE_TESTS.md` with its sign-off table filled in by the owner.
- Commit range on `feat/2026-10-07-review-audit-remediation`, starting after `b43200c`, with commits `DC-R-01` … `DC-R-11`.

## Suggested PR description

```
Fix the bounded runner's timeout, two hook defects, and spec drift (review 2026-10-07)

- Time out the whole process group outside a terminal; recompute slots while waiting (F-001, F-008)
- Let `command -v` through the bounded-runs hook; catch `sh -c` runs and `ulimit -v unlimited` (F-002, F-013)
- Keep symlinks intact in the line-ending hook, and add its first test harness: 8 cases (F-003, F-006)
- One collection scope for the WoW issue commands, upstreams included (F-004)
- Per-run roots file in the cross-addon pass; wow-new-addon edits the roster without pushing;
  finalize treats a push rejection as a stop (F-005, F-007, F-012)
- Docs: DEPENDENCIES inventory and citations, stale wow-addon mentions, tooling kind,
  test temp-dir cleanup (F-009, F-010, F-014, F-015; F-011 optional)

Tests: detector 17, checker 15, bounded-runs 21, line-ending 8 — all green; OK: 13 overlays.
Review bundle: docs/reviews/2026-10-07/
```
