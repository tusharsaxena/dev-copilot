# Merge wow-addon into dev-copilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One `dev-copilot` v2.0.0 plugin carrying every dev-copilot and wow-addon capability, with each shared command generic by default and WoW-specific via an overlay when the repo is detected as WoW.

**Architecture:** A Python detector on the plugin's `bin/` PATH entry classifies the repo. Shared command/agent specs start with a Step 0 that runs it and, on `profile=wow`, reads `profiles/wow/<name>.md`, whose sections add to or replace `<!-- overlay: id -->` hook points in the base. WoW-only commands are renamed `wow-*` and refuse in generic repos.

**Tech Stack:** Claude Code plugin (Markdown command/agent specs, hooks.json), Python 3 (stdlib only), POSIX sh / Bash.

**Spec:** `docs/superpowers/specs/2026-10-04-merge-wow-addon-design.md`

## Execution ledger (resume here)

Branch: `feat/2026-10-04-merge-wow-addon` (pushed to `origin` at milestones; **not merged** without the user's go-ahead). To resume: `git switch feat/2026-10-04-merge-wow-addon`, read this ledger, pick the first row not `done`, verify its predecessor's commit exists in `git log`.

| Task | Status | Commit |
|---|---|---|
| T0 Merge wow-addon history | done | 4914203 |
| T1 Detector + bin + test | pending | |
| T2 Hook/state path migration | pending | |
| T3 Overlay checker | pending | |
| T4 WoW-only commands + agent renamed, refusal step | pending | |
| — Milestone M1: push | pending | |
| T5 commit + diff | pending | |
| T6 sync-docs | pending | |
| T7 review command + agent | pending | |
| T8 run-tests + bump-version | pending | |
| T9 finalize + execution-status | pending | |
| T10 issue-* family | pending | |
| — Milestone M2: push | pending | |
| T11 Cross-ref sweep, manifests, README, CLAUDE.md, DEPENDENCIES.md, v2.0.0 | pending | |
| T12 Verification | pending | |
| — Milestone M3: push, report, await merge go-ahead | pending | |
| T13 After go-ahead: merge `--no-ff`, push, delete branch/remote `wowaddon`/stashes/worktrees | pending | |

T5–T10 are independent (disjoint files) and run in parallel as one workflow; each agent writes files only, the orchestrator verifies and commits one commit per task.

## Global Constraints

- Plugin name `dev-copilot`; version `2.0.0` in `.claude-plugin/plugin.json` only; `marketplace.json` mirrors the description.
- LF line endings everywhere (repo `.gitattributes`); scripts executable.
- Python stdlib only; Python ≥ 3.8.
- Shared command names: `diff commit sync-docs review run-tests bump-version finalize execution-status issue-add issue-audit issue-triage issue-details issue-fetch-all issue-summary`.
- WoW-only command names: `wow-new-addon wow-bump-interface wow-automated-tests wow-perf-analysis wow-revendor-libka0s wow-revendor-standards wow-harvest-standards wow-standards-audit`. Agents: `review`, `wow-standards-audit`.
- Detector output keys exactly: `profile kind repo name root reason`.
- Hook marker exactly `<!-- overlay: <id> -->`; overlay headings exactly `## <id> — adds` / `## <id> — replaces` / `## extra — adds`.
- State dir `~/.claude/dev-copilot/`; legacy `~/.claude/wow-addon/bin/ka0s-bounded` symlink still maintained.
- Never edit files outside this repo in phase 1. WoW behavior in a WoW repo must equal the wow-addon v2.5.0+master spec it came from (`git show wowaddon/master:<path>`; also reachable as the merge's second parent `4914203^2`).

## Review Focus

1. Detector run from a **subdirectory** of a repo → must classify the repo root, not the subdir.
2. Detector in a **non-git directory** (e.g. `~`) → `profile=generic`, `repo=<path>`, no traceback.
3. A generic repo that merely **contains** a `.toc` without `## Interface:` (or with it in a nested dir) → generic.
4. A `.dev-copilot` override with odd whitespace / CRLF / comments → still honored.
5. Overlay referencing a hook id the base renamed → `check_overlays.py` fails loudly.

Tests for 1–4 are in T1; 5 is in T3.

---

### Task T1: Detector, bin wrapper, unit test

**Files:**
- Create: `scripts/detect_profile.py`, `bin/dev-copilot-profile`, `scripts/test_detect_profile.py`

**Interfaces:**
- Produces: `detect(path:str) -> dict` with keys `profile, kind, repo, name, root, reason`; CLI `dev-copilot-profile [path]` printing `key=value` lines in that key order.

- [ ] **Step 1: Write the failing test** — `scripts/test_detect_profile.py` (unittest, tempdir fixtures; `git init` where a repo is needed):
  - addon: `Foo.toc` with `## Interface: 120000` → `wow/addon`
  - addon detected from `Foo/modules/` subdir → `wow/addon`, `repo` = root
  - toc without Interface line → `generic`
  - toc only in nested dir → `generic`
  - dir named `LibKa0s` → `wow/library`; root `LibKa0s.toc` in any-named dir → `wow/library`
  - dir named `WowAddonStandards` → `wow/standards`; `origin` URL `.../WowAddonStandards.git` in other-named dir → `wow/standards`
  - dir named `wow-addon` → `wow/tooling`
  - non-git tempdir → `generic`, `repo` = that path
  - `.dev-copilot` with `profile=generic\r\n# c\n` in an addon → `generic`, reason `override`
  - `.dev-copilot` `profile = wow` + `kind=library` in generic dir → `wow/library`
  - CLI output: lines are exactly the six keys in order; `root` = repo's plugin root.
- [ ] **Step 2:** `python3 scripts/test_detect_profile.py` → FAIL (module missing).
- [ ] **Step 3:** Implement `detect_profile.py` per spec §Detection (git top-level via `git -C path rev-parse --show-toplevel`, fallback to path; origin via `git config --get remote.origin.url`, basename stripped of `.git`; root = `dirname(dirname(realpath(__file__)))`). `bin/dev-copilot-profile`: `#!/bin/sh` + `exec python3 "$(dirname "$(readlink -f "$0")")/../scripts/detect_profile.py" "$@"`. chmod +x both.
- [ ] **Step 4:** test → PASS; run against `../AbsorbTracker ../LibKa0s ../WowAddonStandards ../wow-addon . ../steamdb` → addon/library/standards/tooling/generic/generic.
- [ ] **Step 5:** Commit `Add repo profile detector`.

### Task T2: Hook and state path migration

**Files:** Modify `scripts/bounded-runs-hook.sh`, `scripts/bounded_runs.py`, `scripts/test_bounded_runs.py`, `scripts/ka0s-bounded`, `bin/ka0s-bounded`, `scripts/normalize-eol.sh` (header comments).

- [ ] **Step 1:** Update `test_bounded_runs.py` expectations: link at `~/.claude/dev-copilot/bin/ka0s-bounded` **and** legacy `~/.claude/wow-addon/bin/ka0s-bounded` both created; refusal message names the new path; a command invoking the legacy path is still treated as bounded.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Hook maintains both symlinks (loop over two link dirs); `bounded_runs.py` message uses new path; header comments say `dev-copilot plugin`.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `Move plugin state to ~/.claude/dev-copilot, keep legacy runner link`.

### Task T3: Overlay checker

**Files:** Create `scripts/check_overlays.py`, `scripts/test_check_overlays.py`.

**Interfaces:**
- Consumes: layout `commands/*.md`, `agents/*.md`, `profiles/wow/*.md` (overlay for agent X is `profiles/wow/agent-X.md`).
- Produces: `check(root) -> list[str]` errors; CLI exits 1 on errors, prints `OK: N overlays` otherwise.

Rules: every `profiles/wow/<n>.md` maps to `commands/<n>.md` or (for `agent-<n>`) `agents/<n>.md`; every `## <id> — adds|replaces` id other than `extra` appears as `<!-- overlay: <id> -->` in the base; every base that mentions `profiles/wow/<x>.md` has that file; every shared command (Global Constraints list) contains `dev-copilot-profile`; every `wow-*` command contains `dev-copilot-profile`.

- [ ] **Step 1:** Test with tempdir fixtures: valid pair → no errors; overlay with unknown id → error naming id; orphan overlay → error; base referencing missing overlay → error.
- [ ] **Step 2:** FAIL → **Step 3:** implement → **Step 4:** PASS.
- [ ] **Step 5:** Commit `Add overlay consistency checker`.

### Task T4: WoW-only commands and agent

**Files:** `git mv commands/{new-addon,bump-interface,automated-tests,perf-analysis,revendor-libka0s,revendor-standards,harvest-standards,standards-audit}.md commands/wow-<same>.md`; `git mv agents/standards-audit.md agents/wow-standards-audit.md`.

- [ ] **Step 1:** Rename (git mv, separate commit so history follows: `Rename WoW-only commands with wow- prefix`).
- [ ] **Step 2:** In each, insert after the title a `## Step 0 — Confirm this is a WoW repo` block: run `dev-copilot-profile` (fallback `"${CLAUDE_PLUGIN_ROOT}/bin/dev-copilot-profile"`); on `profile=generic` print the refusal line from the spec and stop; otherwise record `kind` for later steps. `wow-new-addon` is the exception: it creates a new addon so it checks the **parent** target dir is not itself inside a non-WoW git repo only as a warning, never refuses (the new addon does not exist yet).
- [ ] **Step 3:** Rewrite references: `/wow-addon:<x>` → mapping; `wow-addon:standards-audit` agent → `dev-copilot:wow-standards-audit`; `wow-addon:review` → `dev-copilot:review`; `~/.claude/wow-addon/` → `~/.claude/dev-copilot/`; agent frontmatter `name: wow-standards-audit`; command wrapper dispatches `dev-copilot:wow-standards-audit`. Keep references to the **repo** `wow-addon` inside audit-rotation text unchanged (upstream data).
- [ ] **Step 4:** `grep -n 'wow-addon:' commands/wow-* agents/wow-*` → only none; commit `Make WoW-only commands profile-aware and dev-copilot-namespaced`.

### Milestone M1: `git push -u origin feat/2026-10-04-merge-wow-addon`; update ledger.

### Tasks T5–T10: shared command ports (parallel workflow)

Each agent receives: the spec, this plan's Global Constraints, the overlay contract, the generic source (`git show 436ab09:<path>` = dev-copilot original, absent for new-to-generic commands) and the WoW source (`git show wowaddon/master:<path>`). It writes the base `commands/<n>.md` (and agent) with the standard Step 0 block and hook markers, plus `profiles/wow/<n>.md` containing only WoW deltas, such that base+overlay in a WoW repo reproduces every instruction of the WoW source (agent self-checks by walking the WoW source section by section and naming where each lands). All `/wow-addon:` refs rewritten per mapping. Must pass `python3 scripts/check_overlays.py` for its files.

Standard Step 0 block (verbatim in every shared base):

```markdown
## Step 0 — Detect the repo profile

Run `dev-copilot-profile` (Bash; if not found, `"${CLAUDE_PLUGIN_ROOT}/bin/dev-copilot-profile"`). It prints `profile=`, `kind=`, `repo=`, `name=`, `root=`, `reason=`.

- **`profile=wow`** — Read `<root>/profiles/wow/<OVERLAY>.md` now. Each of its sections names a hook point in this spec (`<!-- overlay: <id> -->`) and says whether it **adds to** or **replaces** that section; `extra` sections say where they run. Apply them as you go. `kind` (`addon`, `library`, `standards`, `tooling`) refines WoW behavior where the overlay says so.
- **`profile=generic`** — follow this spec as written. Do not read the overlay.
```

- **T5 commit + diff** — commit base = wow-addon version generalized (push flag, parsing table with generic examples); diff base = dev-copilot version. Overlays small.
- **T6 sync-docs** — base = dev-copilot version + comment-citation check + DEPENDENCIES.md drift (when file exists) from WoW source, generalized. Overlay = all Ka0s-specific doc rules.
- **T7 review** — `commands/review.md` wrapper dispatches `dev-copilot:review` and passes args; agent base = dev-copilot agent + generic "measure first" step; overlay `agent-review.md` = WoW Step 0 suites, WoW checks, standard guardrail, output path/artifact names, cross-addon pass. The wrapper itself needs no overlay but still runs Step 0 and passes `profile`/`kind` into the agent prompt.
- **T8 run-tests + bump-version** — generic bases newly written (ecosystem auto-detect table: npm/pnpm/yarn scripts, pytest/tox/ruff, go test/vet, cargo test/clippy, make test, mvn/gradle, dotnet test, luacheck-generic); overlays carry WoW specifics verbatim.
- **T9 finalize + execution-status** — finalize base generic (calls `/dev-copilot:sync-docs`, `/dev-copilot:commit`), overlay = collection order/LibKa0s evidence. execution-status moves with a short Step 0 variant: run `dev-copilot-profile` only to record `profile`/`kind` per repo in its report; it names no overlay file (none exists), which the checker allows because the base does not mention `profiles/wow/`.
- **T10 issue-*** — six bases: generic label workflow, default scope `here`, `all` = named/sibling repos; journal path `~/.claude/dev-copilot/issue-triage/` with legacy read fallback. Overlays: collection scope from `ADDONS.md`, bundle sweeps, any Ka0s-specific label/repo lists.

Each task: verify `check_overlays.py` passes, grep for `wow-addon:`, commit `Port <names> to core + WoW overlay`.

### Milestone M2: push; update ledger.

### Task T11: Docs, manifests, version

- [ ] `plugin.json` / `marketplace.json`: v2.0.0, one description covering generic + WoW (mirror).
- [ ] `README.md`: rewrite — what it is, profile detection + override, shared commands table, WoW-only table, subagents, hooks, migrating from wow-addon (uninstall it; command name map), install/update.
- [ ] `CLAUDE.md`: rewrite from wow-addon's for the merged plugin — layout, overlay contract, five-touch rule, all retained WoW footguns that concern spec authoring, testing commands.
- [ ] `DEPENDENCIES.md`: update names/paths; add python3 for detector.
- [ ] Repo-wide grep: `wow-addon:` / `/wow-addon` / `.claude/wow-addon` only in intentional legacy places.
- [ ] Commit `Document the merged plugin and bump to 2.0.0`.

### Task T12: Verification

- [ ] All three Python tests pass; `check_overlays.py` OK; both manifests parse; `ls commands | wc -l` = 22, `ls agents` = 2, profiles count matches.
- [ ] Real detector runs (T1 step 4) re-run.
- [ ] Fresh-eyes review subagent over the whole branch diff vs `436ab09` and vs `wowaddon/master` for lost WoW instructions; fix findings.
- [ ] Update ledger; commit.

### Milestone M3: push; report to user; wait for merge go-ahead.

### Task T13 (after go-ahead)

`git switch master && git merge --no-ff feat/2026-10-04-merge-wow-addon && git push origin master`; `git branch -d` + `git push origin --delete` the feature branch; `git remote remove wowaddon`; `git worktree prune`; drop any stash created this run. Tell the user to `/plugin uninstall wow-addon`, `/plugin marketplace update dev-copilot`, `/reload-plugins`.
