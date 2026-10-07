# 04 — Execution plan: dev-copilot review, 2026-10-07

All work lands on `feat/2026-10-07-review-audit-remediation`, the branch name shared with the collection-wide exercise. Each commit subject starts with its task id (`DC-R-<n>: `) so `resume-state.sh`-style tracking can read progress from git. Each commit ends with the session's attribution trailers. Do not push, merge or bump the version without the owner's go-ahead.

Gate after every task, from the repo root:

```sh
for t in test_detect_profile test_check_overlays test_bounded_runs; do ~/.claude/dev-copilot/bin/ka0s-bounded python3 scripts/$t.py; done
[ -f scripts/test_normalize_eol.py ] && ~/.claude/dev-copilot/bin/ka0s-bounded python3 scripts/test_normalize_eol.py
python3 scripts/check_overlays.py
```

## M1: runner and hook correctness (F-001, F-002, F-003, F-006, F-008, F-013, F-014)

**Done when:** all four test files pass, with bounded-runs at 21 cases and normalize-eol at 8, and every new case was observed **red** against the pre-change code before its fix landed.

| Task | Role | Changes / findings | Files |
|---|---|---|---|
| DC-R-01 | test-author, then shell-fixer | C-01 (F-001). Write `test_timeout_kills_children` first and watch it fail; then fix. | `scripts/ka0s-bounded`, `scripts/test_bounded_runs.py`, `DEPENDENCIES.md:47` |
| DC-R-02 | shell-fixer | C-08 (F-008) | `scripts/ka0s-bounded` |
| DC-R-03 | py-fixer | C-02 (F-002), C-09 (F-013), with test-first assertions | `scripts/bounded_runs.py`, `scripts/test_bounded_runs.py` |
| DC-R-04 | test-author | C-11 (F-014) | `scripts/test_bounded_runs.py` |
| DC-R-05 | test-author, then shell-fixer | C-04 harness (F-006) first, with case 6 red; then C-03 (F-003). Set the exec bit with `git update-index --chmod=+x`. | `scripts/test_normalize_eol.py` (new), `scripts/normalize-eol.sh` |

**Concurrency map:**
- DC-R-01 and DC-R-02 both touch `scripts/ka0s-bounded`, so they run in that order.
- DC-R-01, DC-R-03 and DC-R-04 all touch `scripts/test_bounded_runs.py`, so they run in the order 01 → 03 → 04.
- DC-R-05 shares no file with the others and **can run in parallel** with the 01→02→03→04 chain.

**Checkpoint CP-1:** a human reads the C-01 diff, which is the guard's core, and runs smoke checks C-01 and C-03 in a live session before M2.

## M2: spec consistency (F-004, F-005, F-007, F-012)

**Done when:** `check_overlays.py` prints `OK: 13 overlays`, and the four issue overlays carry the identical `all` bullet.

| Task | Role | Changes / findings | Files |
|---|---|---|---|
| DC-R-06 | spec-editor | C-05 (F-004, the `wow-addon` part of F-010) | `profiles/wow/issue-audit.md`, `issue-triage.md`, `issue-summary.md`, `issue-details.md`, `README.md:42-49` |
| DC-R-07 | spec-editor | C-06 (F-005) | `profiles/wow/agent-review.md` |
| DC-R-08 | spec-editor | C-07 (F-007) | `commands/wow-new-addon.md` |
| DC-R-09 | spec-editor | C-10 (F-012) | `commands/finalize.md` |

**Concurrency map:** DC-R-06 through DC-R-09 have disjoint files and **can all run in parallel**. DC-R-06's `README.md` lines are distinct from M3's, but M3 runs after M2 anyway.

**Checkpoint CP-2:** owner runs smoke check C-05 (scope print only) and `/reload-plugins`.

## M3: documentation sync (F-009, F-010, F-011, F-015)

**Done when:**
- every Evidence `file:line` in `DEPENDENCIES.md` resolves to the tool it names, re-read and quoted;
- `git grep -n 'wow-addon' -- ':!docs'` shows only the allowed hits;
- both manifests parse;
- the `CLAUDE.md` test counts read 17, 15, 21 and 8.

| Task | Role | Changes / findings | Files |
|---|---|---|---|
| DC-R-10 | doc-sync | C-12 (F-009, F-010, F-015), plus the C-04 doc moves | `DEPENDENCIES.md`, `CLAUDE.md`, `README.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` |
| DC-R-11 | doc-sync (optional) | C-12's F-011 baseline refresh, re-measured from `GIT/` at the then-current LibKa0s tag | `profiles/wow/agent-review.md` |

**Concurrency map:** DC-R-10 runs alone, after M1 and M2, because counts and line numbers move. DC-R-11 touches `agent-review.md`, so it runs after DC-R-07.

**Checkpoint CP-3:** run the full pre-flight and regression rows of `03_SMOKE_TESTS.md`. The owner decides on push, merge (`--no-ff`, via `/dev-copilot:finalize`) and any 2.0.2 release via `/dev-copilot:bump-version`.

## Commit strategy (one commit per task)

| Task | Suggested subject |
|---|---|
| DC-R-01 | `DC-R-01: Time out the whole process group outside a terminal` |
| DC-R-02 | `DC-R-02: Recompute the slot count while waiting` |
| DC-R-03 | `DC-R-03: Let command -v through and catch sh -c runs` |
| DC-R-04 | `DC-R-04: Clean up bounded-runs test temp dirs` |
| DC-R-05 | `DC-R-05: Test the line-ending hook and keep symlinks intact` |
| DC-R-06 | `DC-R-06: Give the issue commands one collection scope` |
| DC-R-07 | `DC-R-07: Use a per-run roots file in the cross-addon pass` |
| DC-R-08 | `DC-R-08: Edit the roster on a branch and never push from wow-new-addon` |
| DC-R-09 | `DC-R-09: Describe finalize's push rejection as a stop` |
| DC-R-10 | `DC-R-10: Sync docs after the review fixes` |
| DC-R-11 | `DC-R-11: Re-measure the cross-addon baseline` |

## Finding ↔ change ↔ task trace

| Finding | Change | Task |
|---|---|---|
| F-001 | C-01 | DC-R-01 |
| F-002 | C-02 | DC-R-03 |
| F-003 | C-03 | DC-R-05 |
| F-004 | C-05 | DC-R-06 |
| F-005 | C-06 | DC-R-07 |
| F-006 | C-04 | DC-R-05 |
| F-007 | C-07 | DC-R-08 |
| F-008 | C-08 | DC-R-02 |
| F-009 | C-12 | DC-R-10 |
| F-010 | C-05, C-12 | DC-R-06, DC-R-10 |
| F-011 | C-12 | DC-R-11 |
| F-012 | C-10 | DC-R-09 |
| F-013 | C-09 | DC-R-03 |
| F-014 | C-11 | DC-R-04 |
| F-015 | C-12 | DC-R-10 |
