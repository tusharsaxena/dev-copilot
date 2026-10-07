# 02 — Proposed changes: dev-copilot review, 2026-10-07

Standard resolved for the guardrail: **Ka0s WoW Addon Standard v2.76.1 (2026-10-07)**. The index and all 27 sections were fetched with `curl -fsSL`. Repo rules that shaped these changes come from `CLAUDE.md`: the five-touch rule (`:102-107`), the overlay contract (`:59-65`), "only `finalize` pushes" (`:147`), and the exec-bit footgun (`:65`).

## HLD

### Theme A: make the safety net do what it says (F-001, F-002, F-008, F-013)
The runner and the hook are the plugin's guard against a runaway suite taking down the VM. Today the guard has three problems. Its clock does not reach child processes. It blocks a harmless probe. Under contention it waits for one particular slot. The fixes stay inside the existing design: no new variables and no new bounds. The only change is that each existing bound now applies to everything it claims to cover.
- *Alternative rejected for F-001:* `systemd-run -p RuntimeMaxSec=`. It only works when the scope is available, and a no-systemd WSL would keep the hole. Dropping `--foreground` when there is no TTY fixes both paths, and when a TTY is present `--foreground` stays, so Ctrl-C keeps working.
- *Alternative rejected for F-002:* removing `command` from `TRANSPARENT`. That would let `command luacheck .`, which is a real run, through. Special-casing the `-v`/`-V` lookup form is the narrow fix.

### Theme B: the hook that rewrites bytes gets a harness (F-003, F-006)
Add `scripts/test_normalize_eol.py`, a stdlib `unittest` built on tempdir git repos, in the same shape as the other three test files. Fix the symlink case behind it, so the first new case starts red and finishes green.
- *Alternative rejected:* skipping symlinks entirely. The target would then stay unnormalized, while the user asked for the write to be normalized.

### Theme C: one definition of "the collection" (F-004, F-010 part)
All four WoW issue overlays read the same thing: every row of `WowAddonStandards/standards/ADDONS.md`'s in-scope-addon table plus its library and repo tables (`LibKa0s`, `WowAddonStandards`, `dev-copilot`). That roster now lists the upstreams itself, so no spec needs to name them. The `wow-addon` clause goes, because the repo is archived with 0 open issues.
- *Alternative rejected:* narrowing summary and details to addons only. That hides upstream debt (LibKa0s holds 5 triaged issues today) instead of making it reachable.

### Theme D: specs follow the plugin's own rules (F-005, F-007, F-012)
Use a shared-path-free roots file, give `wow-new-addon` the `Edit` tool with a no-push instruction, and make `finalize`'s rejection path honest.

### Theme E: doc drift (F-009, F-010, F-011, F-014, F-015)
Make these edits last, after Themes A–D have moved the counts. The `DEPENDENCIES.md` inventory is restated with its `git ls-files` command beside it, so the next drift can be checked rather than retyped.

## Upstream change-set

None. Nothing here lands in `LibKa0s` or `WowAddonStandards`.

## LLD

### C-01: the runner's timeout covers the process group (F-001)
- **File:** `scripts/ka0s-bounded`, at `:98-100` and in the header comment `:18-19`.
- **Change:**
  ```bash
  # before
  cmd=(timeout --foreground -k 10 "$secs" "${cmd[@]}")
  # after
  fg=(); [ -t 0 ] && fg=(--foreground)   # --foreground only for an interactive run (Ctrl-C);
                                         # without it timeout signals the whole process group
  cmd=(timeout ${fg[@]+"${fg[@]}"} -k 10 "$secs" "${cmd[@]}")
  ```
  The `${fg[@]+…}` form is safe under `set -u` on bash 4.2. `DEPENDENCIES.md` declares bash ≥ 4.2 at `:43`.
- **Header comment:** `--foreground` is used only on a TTY. Without one, the whole process group is timed out.
- **Risk:** A wrapped command that reads the TTY never loses it, because `--foreground` stays whenever stdin is a TTY. Claude Code's Bash tool has no TTY, so that path now kills the group.
- **Also edit:** `DEPENDENCIES.md:47`, which quotes `timeout --foreground -k 10`.
- **Test:** add `BinWrapper.test_timeout_kills_children` to `scripts/test_bounded_runs.py`. The bounded-runs count moves from 20 to 21, and `CLAUDE.md:91` moves in the same change.

### C-02: `command -v` is a lookup, not a run (F-002)
- **File:** `scripts/bounded_runs.py`, function `strip_prefix` (`:218-250`).
- **Change:** in the `TRANSPARENT` branch, before skipping options, return no command for the lookup form:
  ```python
  elif w in TRANSPARENT:
      if w == "command" and i + 1 < len(words) and words[i + 1] in ("-v", "-V"):
          return [], assignments, timed        # `command -v x` looks x up; it does not run it
      i += 1
  ```
- **Test:** add `"command -v luacheck lizard"` and `"command -V lizard"` to `test_mentions_are_not_runs`. Add `"command luacheck ."` to `test_refused_inside_compound_commands`. The case count is unchanged, since the assertions live inside existing cases.

### C-03: the line-ending hook rewrites a symlink's target, not the link (F-003)
- **File:** `scripts/normalize-eol.sh`, after `:32`.
- **Change:**
  ```bash
  # A symlinked file: normalize the file it points at, by that file's own repo and attributes.
  # perl -i on the link would replace the link with a regular file.
  if [[ -L "$file_path" ]]; then
      file_path="$(readlink -f -- "$file_path")" || exit 0
      [[ -f "$file_path" ]] || exit 0
  fi
  ```
  Everything below it already derives `file_dir`, `repo_root` and `rel_path` from `file_path`.
- **Risk:** A link pointing outside any repo now exits silently at the `repo_root` check, which is the correct outcome.

### C-04: line-ending hook harness (F-006; pins C-03)
- **New file:** `scripts/test_normalize_eol.py`. It is LF and carries a `#!/usr/bin/env python3` shebang (line-endings-§3). Its mode is set with `git update-index --chmod=+x` (`CLAUDE.md:65`). It uses stdlib `unittest` only.
- **Cases**, each in a fresh `TemporaryDirectory` git repo:
  1. CRLF repo, LF file → converted to all CRLF.
  2. CRLF repo, mixed file → no bare LF left.
  3. LF repo, CRLF file → 0 CRs.
  4. No `eol` declared → byte-identical (`filecmp.cmp(shallow=False)` against a copy).
  5. `*.png binary` in a CRLF repo, holding bytes with `\n` → byte-identical (the line-endings-§7 case).
  6. Symlinked file in a CRLF repo → the link is still a link and the target is converted. This case is red before C-03.
  7. Path through a symlinked directory → converted.
  8. Garbage stdin → exit 0, no output.
- **Doc moves in the same change:**
  - `CLAUDE.md:9`: "Three unit-test files" → four.
  - `CLAUDE.md:85-96`: add the run line and replace the "no harness" paragraph with a pointer to the file.
  - `DEPENDENCIES.md`: the short-version block and its Python-file count.

### C-05: one collection definition for the issue commands (F-004, F-010 part)
- **Files:**
  - `profiles/wow/issue-audit.md:22-23`
  - `profiles/wow/issue-triage.md:18-19`
  - `profiles/wow/issue-summary.md:9`
  - `profiles/wow/issue-details.md:9`
  - `README.md:42-43, :46, :49`
- **Change:** use one identical bullet in each, worded with that overlay's own fallback clause:
  > **`all`** → the whole collection: every row of `WowAddonStandards/standards/ADDONS.md`, meaning the in-scope addons plus its library and repo tables (`LibKa0s`, `WowAddonStandards`, `dev-copilot`). Read it, never hard-code it.
- **Removed:** the `wow-addon` clause.
- **Repo-name matching** is against that same roster, so `issue-triage LibKa0s` resolves.
- **Overlay contract:** markers and section ids are unchanged, so `check_overlays.py` stays `OK: 13 overlays`. Each section keeps its "Replaces only …" extent sentence (`CLAUDE.md:60`).

### C-06: per-run roots file in the cross-addon pass (F-005)
- **File:** `profiles/wow/agent-review.md:349-361` and the table row `:440`.
- **Change:** add `roots=$(mktemp)` before the first loop, use `tee "$roots"` and `cut -f1 "$roots"`, and change the table's count command to `wc -l < "$roots"`. Add one sentence citing the shared-path rule in `commands/wow-automated-tests.md:97`.

### C-07: `wow-new-addon` edits the roster safely and never pushes (F-007)
- **File:** `commands/wow-new-addon.md`.
  - `:4` adds `Edit` to `allowed-tools`.
  - `:246` becomes: "add the addon's row to `standards/ADDONS.md` in the `WowAddonStandards` checkout with `Edit`, on a feature branch, and commit it there. **Never push.** Pushing is the owner's, or `/dev-copilot:finalize`'s. If that checkout is absent or dirty, tell the user the row still needs adding."
- **Rule:** `CLAUDE.md:147`. This keeps `finalize` as the only spec that pushes on its own.

### C-08: recompute the slot count while waiting (F-008)
- **File:** `scripts/ka0s-bounded:65-93`.
- **Change:** move the `slots` computation inside `while [ "$acquired" -eq 0 ]` and re-read `MemAvailable` on each pass. An explicit `KA0S_KIT_SLOTS` still wins. The "waiting" message is still printed once.
- **Risk:** It adds one `awk` call per 0.5 s poll while waiting, which is negligible.

### C-09: matcher false negatives (F-013)
- **File:** `scripts/bounded_runs.py:273-277` and `:307`.
- **Change 1:** when a shell has `-c`, scan its command string. Replace the shell branch with:
  ```python
  if name in SHELLS and args:
      if "-c" in args and args.index("-c") + 1 < len(args):
          inner = args[args.index("-c") + 1]
          kinds = [k for w in segments(inner) for k in [heavy(strip_prefix(w)[0], cwd)] if k]
          return kinds[0] if kinds else None
      ...
  ```
- **Change 2:** make the `ulimit` regex require a numeric argument: `\bulimit\s+(-[A-Za-z]*v|-v)\s+\d+`.
- **Tests:** extend `test_plain_runs_are_refused` with `bash -c "lua tests/run.lua"` and `sh -c 'luacheck .'`. Extend `test_mentions_are_not_runs` with `bash -c "grep lua tests/run.lua"`. Add `ulimit -v unlimited; timeout 60 lua tests/run.lua` as refused. No new case count.

### C-10: `finalize` rejection path (F-012)
- **File:** `commands/finalize.md:114`.
- **Change:** "If the push is rejected, origin moved. A fast-forward is impossible while your merge commit is unpushed, so stop that repo, report the rejection verbatim, and leave the merge for the user. Never `--force`, and never rebase or merge origin in on your own."
- **Risk:** None. Behavior is unchanged; only the description becomes accurate.

### C-11: test temp-dir hygiene (F-014)
- **File:** `scripts/test_bounded_runs.py:16-22, :135-138, :153-158, :183-184`.
- **Change:** `repo()` takes the test case and registers `self.addCleanup(shutil.rmtree, d, True)`. The `HOME` and `XDG_CACHE_HOME` tempdirs are created through the same helper. Case count is unchanged.

### C-12: documentation sync (F-009, F-010, F-011, F-015). Run last.
- **`DEPENDENCIES.md:12-18`:** restate the inventory with its command (`git ls-files | wc -l`, `git ls-files '*.md' | wc -l`), and name `docs/` as "design notes and frozen review bundles" rather than a fixed count, because this bundle adds 5 Markdown files under `docs/reviews/`.
- **`DEPENDENCIES.md` citations:** `:44` → `scripts/bounded-runs-hook.sh:30`. `:81` → `profiles/wow/finalize.md:32-33` and `commands/wow-revendor-libka0s.md:317`. Re-resolve each against the post-change tree.
- **`CLAUDE.md:110`:** rewrite the "only intentional live mentions" list to what survives: the README migration note, this file's history, the audit agent's "(the archived `wow-addon` before it)" and the two regression-guard tests.
- **`README.md:73`:** `wow-addon` → `dev-copilot`.
- **`README.md:5`, `:51`:** add `tooling` repos.
- **`plugin.json:3` and `marketplace.json:12`:** add the tooling kind to the description. Edit both together, because the marketplace copy is a mirror (`CLAUDE.md:24`).
- **`profiles/wow/agent-review.md:419-443` (F-011, optional):** re-measure the baseline at the then-current tag with the table's own commands and record the result with its date. Per the table's own rule, never copy a figure from this bundle.
- **Version:** this review proposes no bump. A spec and behavior fix release is a patch, 2.0.1 → 2.0.2, made by `/dev-copilot:bump-version` when the owner releases.

## Standards conformance

| Change | Conformance note |
|---|---|
| C-01, C-08 | Script behavior only. LF is kept, as `.gitattributes` `*.sh`/extensionless files require (line-endings-§2, §3). |
| C-02, C-09, C-11 | Python, stdlib only. No manifest is added (`DEPENDENCIES.md` *Not used here*). |
| C-03 | Keeps the hook asking `text` and `eol` together (line-endings-§7). The resolved target goes through the same query. |
| C-04 | The new script follows line-endings-§3 (shebang, LF) and the exec bit is set via `git update-index --chmod=+x` (`CLAUDE.md:65`). |
| C-05 | Overlay sections keep their ids and extent sentences (`CLAUDE.md:59-61`). The roster is read rather than copied, per the workspace rule "Never copy that list". |
| C-06 | Spec text only. It follows the plugin's own shared-path rule. |
| C-07 | Keeps `finalize` as the sole pushing spec (`CLAUDE.md:147`). |
| C-10 | Keeps "never `--force`" (`finalize.md:152`). |
| C-12 | `DEPENDENCIES.md` keeps one evidence `file:line` per row (documentation-§7, read for a tooling repo under documentation-§8). Counts are stated with their command, per this bundle's census rule. |

No change targets `libs/` or `tests/_kit/`; this repo has neither.

## Count movement

- Bounded-runs tests go from 20 to 21 (C-01).
- A new line-ending test file adds 8 cases (C-04).
- `CLAUDE.md:89-92` moves to match: 17 + 15 + 21 + 8.
- The overlay count stays at 13.
- The tracked-file count moves: +1 test file, plus 5 bundle files.
