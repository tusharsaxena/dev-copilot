# 03 — Smoke tests: dev-copilot review, 2026-10-07

This repo ships nothing to the WoW client, so the "in-client" half here is a **live Claude Code session**: the hooks firing on real tool calls, `/reload-plugins`, and commands dispatched as skills. Headless checks ran in Step 0b and are listed once below as pre-flight. Do not mark any row passed on an agent's behalf. These rows are the owner's to run.

## Pre-flight (headless, from the repo root, after the changes land)

```sh
cd /mnt/d/Profile/Users/Tushar/Documents/GIT/dev-copilot
for t in test_detect_profile test_check_overlays test_bounded_runs test_normalize_eol; do
  ~/.claude/dev-copilot/bin/ka0s-bounded python3 scripts/$t.py || echo "FAIL $t"
done
python3 scripts/check_overlays.py            # expect: OK: 13 overlays
python3 -c "import json; [json.load(open(f)) for f in ('.claude-plugin/plugin.json', '.claude-plugin/marketplace.json')]"
git ls-files -s scripts/test_normalize_eol.py # expect mode 100755
git ls-files -z | xargs -0 grep -lU $'\r' | wc -l   # expect 0
```

Expected counts are 17, 15, 21 and 8 cases, all OK.

Setup for the session: open a Claude Code session with the plugin installed from this checkout's branch, user scope, and run `/reload-plugins`.

## Per-change checks

### C-01: the timeout reaches child processes
- **Setup:** a shell in the session (no TTY).
- **Steps:**
  1. Ask Claude to run `KA0S_KIT_TIMEOUT_S=2 ka0s-bounded bash -c 'sleep 61; echo done'`.
  2. Then run `pgrep -x sleep -a | grep -c ' 61$'`.
- **Expected:** step 1 exits 124 with the "wall-clock limit" line. Step 2 prints `0`.
- **Pass:** `0` survivors. Fail if `1`.
- **Also:** in a real terminal (with a TTY), run `ka0s-bounded sleep 30`, press Ctrl-C, and confirm it stops at once (the `--foreground` path kept for TTYs).

### C-02: `command -v` probe passes the hook
- **Steps:**
  1. Ask Claude to run `command -v luacheck lizard`.
  2. Ask it to run `command luacheck --version`, then `luacheck .` inside any addon repo.
- **Expected:** step 1 runs with no hook denial. In step 2, `luacheck .` is **denied**, and the denial names `~/.claude/dev-copilot/bin/ka0s-bounded`.
- **Pass:** no denial in step 1, denial in step 2.

### C-03 and C-04: the line-ending hook keeps symlinks
- **Setup:** a scratch git repo outside the collection holding `* text=auto eol=crlf`, `real.md` with LF content, and `ln -s real.md link.md`.
- **Steps:** ask Claude to Edit `link.md` (change one word). Then run `ls -l link.md` and `tr -dc '\r' < real.md | wc -c`.
- **Expected:** `link.md` is still `link.md -> real.md`, and the CR count of `real.md` equals its line count.
- **Pass:** the link survives and the target is CRLF.
- **Regression arms**, with the same Edit flow. Check each with `cmp` against a pre-edit copy:
  - a file in **this** repo, LF arm: 0 CRs after the edit;
  - a **copy** of an addon repo (never a live one), CRLF arm;
  - a PNG marked `binary` in that copy: byte-identical;
  - a path with no declared `eol`: byte-identical.

### C-05: the issue commands share one collection
- **Steps:** from `Ka0sAddonsCommonTasks`, run `/dev-copilot:issue-summary all`, then start `/dev-copilot:issue-triage all` and stop at its scope print (answer nothing).
- **Expected:** both list the same repos: the 11 addons plus `LibKa0s`, `WowAddonStandards` and `dev-copilot`, with no `wow-addon`.
- **Pass:** identical repo lists. `issue-triage LibKa0s` resolves to LibKa0s rather than "no match".

### C-06: parallel reviews do not share a roots file
- **Steps:** launch two WoW reviews at once (for example `/dev-copilot:review` in AbsorbTracker and in KickCD). Afterwards, run `ls /tmp/roots.txt`.
- **Expected:** `No such file or directory`. Both bundles record class 1 as 22 roots and 0 collisions, or the then-current figure.
- **Pass:** no shared file is created, and both class-1 lines agree.

### C-07: `wow-new-addon` roster step
- **Setup:** dry-read only. Do not scaffold a real addon for this check.
- **Steps:** open `commands/wow-new-addon.md` and confirm `Edit` is in `allowed-tools` and that step 10 says "Never push". Then `/reload-plugins` and confirm the skill still loads.
- **Pass:** both are present, and the reload reports no load error.

### C-08: the slot pool re-reads memory while waiting
- **Steps:** in two terminals, run `KA0S_KIT_SLOTS= KA0S_KIT_SLOT_MB=999999 ka0s-bounded sleep 20` (this forces `slots=1`). While it runs, start a second copy with the default `KA0S_KIT_SLOT_MB`.
- **Expected:** the second copy acquires a free slot without waiting for the first to finish, because its count is recomputed from current `MemAvailable`.
- **Pass:** the second run starts within about 1 s.

### C-09: `bash -c` runs are caught
- **Steps:** ask Claude to run `bash -c "luacheck ."` inside an addon repo.
- **Expected:** denied, with the ka0s-bounded message. `bash -c "grep lua tests/run.lua"` is not denied.
- **Pass:** both behave as described.

### C-10: `finalize` rejection wording
- **Steps:** read `commands/finalize.md` 3e.
- **Expected:** no `pull --ff-only` retry; rejection means stop and report.
- **Pass:** the text matches C-10.

### C-11: no temp-dir leak
- **Steps:**
  1. `before=$(ls /tmp | wc -l)`.
  2. `python3 scripts/test_bounded_runs.py`.
  3. `after=$(ls /tmp | wc -l)`.
- **Pass:** `after` equals `before`, allowing for unrelated processes; repeat once if in doubt.

### C-12: doc sync
- **Steps:** for every `file:line` in `DEPENDENCIES.md`'s Evidence column, open the cited line. Then run `git grep -n 'wow-addon' -- ':!docs'`.
- **Expected:** each citation shows the tool it names. The `wow-addon` hits are only the README migration note, `CLAUDE.md` history, the audit agent's "archived `wow-addon` before it", and the two tests.
- **Pass:** no unresolved citation, and no other `wow-addon` hit.

## Regression suite (live session)

- `/reload-plugins` reports the same counts as before: 22 commands, 2 agents and 2 hooks under dev-copilot.
- `dev-copilot-profile` in AbsorbTracker, LibKa0s, WowAddonStandards, Ka0sAddonsCommonTasks, dev-copilot and steamdb gives addon, library, standards, tooling, tooling (override) and generic respectively.
- Each of these runs, and none is denied:
  - `git commit -m "lizard is fine"` (dry: `git commit --dry-run -m …`)
  - `cat > /tmp/x.md <<'EOF'` followed by a line reading `lizard -l lua .` and then `EOF`
  - `grep lua tests/run.lua`
- Each of these is denied: `lua tests/run.lua` in a repo with kit < 23 (use a fixture copy), `luacheck .` and `lizard -l lua .`.
- `ka0s-bounded lua tests/run.lua` in AbsorbTracker runs green and its exit code passes through.
- `/dev-copilot:review` in a generic repo writes `reviews/<date>/` and does not read `profiles/wow/agent-review.md`.

## Cross-addon in-session check (from the overlay; not optional)

With several Ka0s addons loaded in a WoW session:
1. Type each of the 11 slash roots and confirm each reaches its own addon.
2. Open Settings → AddOns and confirm each addon appears exactly once, and each multi-page addon's pages appear once each.

## Sign-off

| ID | Tested? | Pass/Fail | Notes |
|---|---|---|---|
| C-01 | | | |
| C-02 | | | |
| C-03 | | | |
| C-04 | | | |
| C-05 | | | |
| C-06 | | | |
| C-07 | | | |
| C-08 | | | |
| C-09 | | | |
| C-10 | | | |
| C-11 | | | |
| C-12 | | | |
| Regression | | | |
| Cross-addon in-session | | | |
