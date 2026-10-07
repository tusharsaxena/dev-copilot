# 01 — Findings: dev-copilot review, 2026-10-07

**Verdict: minor issues.** The suites are green and nothing is blocking. Three runtime defects in the hooks and runner were reproduced today: the timeout leaves child processes running, `command -v luacheck` is wrongly denied, and the line-ending hook replaces a symlink with a regular file. There are also four spec-level inconsistencies and a set of documentation drift items.

**Resolved scope:** `all`, meaning the whole `dev-copilot` repository at `b43200c` on branch `feat/2026-10-07-review-audit-remediation` (clean tree): 62 tracked files from `git ls-files | wc -l`. Profile: `profile=wow kind=tooling reason=override` (`dev-copilot-profile`). The calling script did not pass a `Detected repo profile:` line, so there was nothing to compare against. Lua-shaped suites have no subject in a tooling repo and are recorded below as **not applicable**.

Standards guardrail: Ka0s WoW Addon Standard **v2.76.1 (2026-10-07)**. The index and all 27 section files listed in its Sections list were fetched verbatim with `curl -fsSL` into the scratchpad.

## Measurement run

All output went to the session scratchpad. Nothing was written into the repo apart from this bundle.

| Suite | Result | Command (from repo root) |
|---|---|---|
| Detector unit tests | **pass**, 17/17 | `~/.claude/dev-copilot/bin/ka0s-bounded python3 scripts/test_detect_profile.py` |
| Overlay-checker unit tests | **pass**, 15/15 | `~/.claude/dev-copilot/bin/ka0s-bounded python3 scripts/test_check_overlays.py` |
| Bounded-runs unit tests | **pass**, 20/20 | `~/.claude/dev-copilot/bin/ka0s-bounded python3 scripts/test_bounded_runs.py` |
| Live overlay check | **pass**, `OK: 13 overlays` | `python3 scripts/check_overlays.py` |
| Manifests parse | **pass** | `python3 -c "import json; [json.load(open(f)) for f in ('.claude-plugin/plugin.json', '.claude-plugin/marketplace.json')]"` |
| Detector against real repos | **pass**: AbsorbTracker `wow/addon`, LibKa0s `wow/library`, WowAddonStandards `wow/standards`, Ka0sAddonsCommonTasks `wow/tooling`, dev-copilot `wow/tooling reason=override`, steamdb `generic` | `bin/dev-copilot-profile <repo>` from `GIT/` |
| Line endings, whole tracked set | **pass**: 0 files containing CR; `git ls-files --eol` gives 62 × `i/lf w/lf` | `git ls-files -z \| xargs -0 grep -lU $'\r' \| wc -l` |
| Python / shell lint | **not part of this repo's battery**: no ruff, flake8 or shellcheck config | — |
| `luacheck`, headless `tests/run.lua`, `--list` inventory, `tests/perf.lua`, sighted complexity suite | **not applicable**: no `.luacheckrc`, no `tests/run.lua`, no Lua, no `tests/_kit/` (`kind=tooling`) | — |
| `make test` | **not applicable**: no Makefile | — |
| Vendor sync | **not applicable**: this repo vendors nothing | — |
| Cross-addon pass (4 classes) | **ran, clean**, measured at LibKa0s `v1.70.0` (`git -C LibKa0s describe --tags --abbrev=0`). Class 1: 22 roots across 11 addons, 0 duplicates, 0 raw `SLASH_*` in TOC-loaded source. Class 2: one line, `Bus:2 Compat:1 Core:10 DebugLog:19 Env:1 Item:2 Launcher:5 Lifecycle:3 Media:4 Options:28 Perf:14 Pool:3 Schema:2 Slash:19 Widgets:12`. Class 3: `diff -rq` against AbsorbTracker's copy gave 0 lines for every addon. Class 4: `## Interface: 120100`, uniform. All 11 provenance lines read `v1.70.0`. | The four loops in `profiles/wow/agent-review.md` *The cross-addon pass*, run from `GIT/` with the 11 `ADDONS.md` rows in `$@`. The roots file went to the scratchpad, not `/tmp/roots.txt` (see F-005). |
| Committed-artifact drift | The `agent-review.md` baseline table (recorded at v1.56.0) is behind today's tag v1.70.0. Per its own rule this is a **stale brief, not drift** (F-011). The `DEPENDENCIES.md` inventory disagrees with `git ls-files` (F-009). | see findings |

Today's library-derived baseline figures: majors **15** (`git -C LibKa0s show v1.70.0:tests/majors.lua | grep -c 'major = "LibKa0s-'`), kit revision **37** (`Kit.VERSION = 37`), payload files at the tag **159**, AbsorbTracker copy **159**.

Extra probes run today to reproduce findings. Each command is quoted in its finding.
- The `ka0s-bounded` timeout was tested with and without the systemd scope (F-001).
- The bounded-runs matcher was probed with 24 edge-case commands (F-002, F-013).
- The line-ending hook was tested against a symlinked directory, which works, and a symlinked file, which is broken (F-003).
- Open issues were read on four upstream repos with `gh issue list` (read-only) for F-004.

## Medium

### F-001 `[concurrency]` The runner's wall-clock limit kills only the top process, then reports the run as "stopped"
- **Where:** `scripts/ka0s-bounded:99`: `cmd=(timeout --foreground -k 10 "$secs" "${cmd[@]}")`. The comment at `:18-19` reads `` `timeout --foreground` … --foreground keeps Ctrl-C working``. The message at `:118` reads `"…wall-clock limit and was stopped…"`.
- **Problem:** With `--foreground`, coreutils `timeout` signals only its direct child and does not time out that child's own children. A wrapped command that forks keeps running after the runner exits 124. The children also inherit the slot-pool lock fd opened at `:78` (`exec {slot_fd}>"$slot_dir/slot.$i"`), so they keep holding a slot the runner has reported as released.
- **Evidence (today):** `KA0S_KIT_TIMEOUT_S=2 KA0S_KIT_CGROUP=off scripts/ka0s-bounded bash -c 'sleep 47 ; echo done'` returned `rc=124` and printed "was stopped". One second later, `pgrep` still listed `sleep 47`. The same run with the systemd scope active (`sleep 53`) also left a survivor (`pgrep … | grep -c` → `1`).
- **Impact:** The runner exists to bound runaway runs. On a timeout its children escape the clock, though they stay under `ulimit -v` and the scope's `MemoryMax`. They also keep a slot, so later bounded runs queue behind a process the user was told had stopped.
- **Reachability:** Anyone who runs `ka0s-bounded <cmd>` where `<cmd>` forks and goes past `KA0S_KIT_TIMEOUT_S` (900 s by default). This is softened in the collection: every Lua process the LibKa0s kit launches carries its own `timeout` (`testkit/framework.lua:124`), and `luacheck`/`lizard` run as single processes. A generic forking command, or a hung non-kit grandchild, is not covered.
- **Coverage:** No case in `scripts/test_bounded_runs.py` covers a timeout. `BinWrapper` (lines 115-149) tests only pass-through and the usage error.

### F-002 `[correctness]` The bounded-runs hook denies `command -v luacheck`, a plain tool-presence probe
- **Where:** `scripts/bounded_runs.py:37` (`TRANSPARENT = {"env", "time", "nice", "exec", "command", "nohup", "stdbuf", "ionice"}`) together with `:231-237`, which skips any `-`-prefixed options after a transparent word. `command -v luacheck` is therefore reduced to `luacheck` in command position.
- **Evidence (today):** `bounded_runs.check("command -v luacheck", "/tmp")` returned `['luacheck']`. Piping `{"tool_name":"Bash","tool_input":{"command":"command -v luacheck lizard"},…}` into `scripts/bounded-runs-hook.sh` produced `"permissionDecision": "deny"` with the "Unbounded heavy run (luacheck)" reason. `which lizard` and `type luacheck` both pass.
- **Impact:** The documented contract is broken: "false positives on ordinary commands … are not" acceptable (`CLAUDE.md:37`; module docstring `scripts/bounded_runs.py:26`). `command -v` is the POSIX way to probe for a tool, and `run-tests` and `review` both must probe so they can record an absent tool as a skip. A denied probe with a misleading "unbounded heavy run" message wastes a turn and can be misread as "tool present but blocked".
- **Reachability:** Any session with the plugin enabled that probes with `command -v luacheck|lizard`. That covers every WoW `run-tests`/`review`/`bump-version` run whose agent picks that probe. The kit itself uses `command -v` inside scripts (`LibKa0s/testkit/run-automated-tests.sh:164`), but those run outside the Bash tool and are not seen by the hook.
- **Coverage:** `test_mentions_are_not_runs` (`scripts/test_bounded_runs.py:81-86`) covers `which luacheck lizard` but not `command -v`.

### F-003 `[correctness]` The line-ending hook replaces a symlinked file with a regular file
- **Where:** `scripts/normalize-eol.sh:32` (`[[ ! -f "$file_path" ]] && exit 0`, which follows symlinks), then `perl -i` at `:68` (CRLF arm) and `:76` (LF arm).
- **Problem:** `perl -i` writes a new file at the given path. When that path is a symlink, the link itself is replaced by a regular file holding the converted bytes, and the target is left unconverted.
- **Evidence (today):** In a scratch repo with `* text=auto eol=crlf`, `target.lua` held LF content and `alias.lua -> target.lua`. After feeding `{"tool_input":{"file_path":".../alias.lua"}}` to the hook, `ls -l` showed `alias.lua` as a regular 6-byte file and `target.lua` with 0 CRs. A symlinked *directory* is handled correctly: same repo, `link/x.lua` → 2 CRs.
- **Impact:** A tracked symlink silently becomes a type-changed regular file, and the two documents diverge. The common generic-repo case is `CLAUDE.md -> AGENTS.md`. The hook is advertised as never doing harm: "it never blocks a write", README:77.
- **Reachability:** Any plugin user editing a symlinked file in a repo whose `.gitattributes` declares an `eol` the content does not yet match. The Ka0s collection has none today: a `git ls-files -s | grep -c '^120000'` sweep over every sibling under `GIT/` found 0 tracked symlinks. Generic repos using the shared-doc symlink pattern can hit it.

### F-004 `[design]` The four issue commands disagree on what `all` means in a WoW repo
- **Where:**
  - `profiles/wow/issue-audit.md:22`: "**`all`** → every addon repo in the collection."
  - `profiles/wow/issue-triage.md:18`: "**`all`** → every addon repo in the collection".
  - Against these, `profiles/wow/issue-summary.md:9` and `profiles/wow/issue-details.md:9` both say "add the upstreams: `WowAddonStandards` … `LibKa0s` … `dev-copilot`, plus the legacy `wow-addon` …".
  - `README.md:49` states the wider meaning for every issue command ("plus `WowAddonStandards`, `LibKa0s` and this plugin"), while `README.md:42-43` say "`all` = the Ka0s roster from `ADDONS.md`".
- **Problem:** `issue-summary all` counts upstream issues that `issue-triage all` never walks and `issue-audit all` never sweeps.
- **Evidence (today, read-only):** `gh issue list -R tusharsaxena/LibKa0s --state open` shows `state:triaged=5`. Those five are reported by summary, but a collection triage pass skips them. Today's own request ("all Ka0s addons and upstreams") falls into this gap.
- **Impact:** Collection-wide discovery and triage silently leave out the three upstream repos. Upstream debt then shows up in the summary grid with no `all`-scope command that can act on it.
- **Reachability:** The owner running `/dev-copilot:issue-audit all` or `/dev-copilot:issue-triage all` from any Ka0s repo or from `Ka0sAddonsCommonTasks`.

### F-005 `[concurrency]` The cross-addon pass writes a fixed shared path, `/tmp/roots.txt`, which the plugin's own rule forbids
- **Where:** `profiles/wow/agent-review.md:354` (`done | sort | tee /tmp/roots.txt`), `:355` (`cut -f1 /tmp/roots.txt | uniq -d`), and `:440` (``wc -l < /tmp/roots.txt``).
- **Problem:** `commands/wow-automated-tests.md:97-100` says: "Capture the run's console output to a path no other run can share … a fixed name such as `/tmp/run.log` … lets one run overwrite another's log mid-read". The review overlay breaks that rule.
- **Impact:** Parallel WoW reviews run the same loop. Today's workflow dispatches one per repo at once, so one review's `tee` can truncate the file while another's `cut | uniq -d` is reading it. That produces a partial read, and a collision can be reported clean.
- **Reachability:** Any two WoW reviews whose cross-addon passes overlap in time. This is the normal shape of a collection sweep.

### F-006 `[tests]` The line-ending hook rewrites user files on every Write and Edit and has no automated test
- **Where:** `CLAUDE.md:96`: "The line-ending hook script is Bash; there's no harness for it beyond running the flow that triggers `Write|Edit|MultiEdit`…". `scripts/` has unit tests for the other three executable modules only.
- **Problem:** The four cases `CLAUDE.md` itself calls essential are validated by hand: CRLF arm, LF arm, no declared `eol`, and `binary` inside a CRLF repo. So is the binary-corruption fix it records (line-endings-§7). F-003 is exactly the kind of defect a tempdir harness catches. It took one scratch repo to reproduce today.
- **Impact:** Any regression in the one hook that mutates user bytes is found by a user, in their repo.
- **Reachability:** Maintainers changing `scripts/normalize-eol.sh`. The runtime effect reaches every plugin user via F-003-class defects.

### F-007 `[design]` `wow-new-addon` must edit another repo's roster without the `Edit` tool, and its wording implies it may push
- **Where:**
  - `commands/wow-new-addon.md:4`: `allowed-tools: [Read, Glob, Grep, Bash, Write, WebFetch]`, with no `Edit`.
  - `:246`: "add the addon's row to `standards/ADDONS.md` in the `WowAddonStandards` repo … if you can't push there, tell the user this row still needs adding".
- **Problem:** Appending one row to an existing file with only `Write` means rewriting the whole of `ADDONS.md`, which is the collection's single source of truth, or improvising with `sed`. "If you can't push there" reads as permission to push to the standards repo. That conflicts with the plugin rule that only `finalize` pushes on its own (`CLAUDE.md:147`) and with the owner's rule that pushes need explicit authorization.
- **Impact:** There is a risk of clobbering the roster, or of an unrequested push to `WowAddonStandards`.
- **Reachability:** The owner scaffolding a new addon with `/dev-copilot:wow-new-addon`. This is rare, but it is the only path that writes the roster.

## Low

### F-008 `[perf]` The slot count is computed once, before the wait loop
- **Where:** `scripts/ka0s-bounded:66-70` computes `slots=$(( avail_mb * 6 / 10 / slot_mb ))` once. The poll loop at `:75-93` then probes only `slot.1..slot.$slots` for the rest of the wait.
- **Impact:** A caller that started when memory was tight and computed `slots=1` waits for `slot.1` specifically, even after memory frees and slots 2..N sit unused. Runs serialize more than the machine needs.
- **Reachability:** Parallel collection sweeps, like today's multi-repo run, when a caller starts while other bounded runs hold memory.

### F-009 `[docs]` The `DEPENDENCIES.md` inventory and three of its citations are stale
- **Where:** `DEPENDENCIES.md:12-13` says "The repo is 61 tracked files: 43 Markdown (… 3 design/plan notes under `docs/` …)". Today `git ls-files | wc -l` → **62**, `git ls-files '*.md' | wc -l` → **44**, and `git ls-files docs` lists **4** notes, because `docs/superpowers/plans/2026-10-04-phase2-rename-ripple.md` was added after the rewrite `e2c827d`. Scope: the whole tracked set, no exclusions, matching the doc's own claim.
- **Stale citations:**
  - `:44` cites `scripts/bounded-runs-hook.sh:33`, but the file is 31 lines (`wc -l`). The `python3` call is at `:30`.
  - `:81` cites `profiles/wow/finalize.md:28-29`, which is now a blank line and `## gate-commands — replaces`. The commands are at `:32-33`.
  - `:81` also cites `commands/wow-revendor-libka0s.md:316`, which is now a ```` ```sh ```` fence. The command is at `:317`.
- **Reachability:** A comment or doc; no runtime effect.

### F-010 `[docs]` Stale `wow-addon` mentions survive after phase 2 closed
- **Where:**
  - `CLAUDE.md:110` still lists "the legacy symlink and journal paths, the detector's `tooling` rule, the audit rotation's naming of the `wow-addon` **repo** … unchanged until phase 2" as intentional live mentions. `CLAUDE.md:82` and `:152` say all of these were removed and that phase 2 finished 2026-10-04.
  - `README.md:73` names the documentation-lane repos as "`WowAddonStandards` and `wow-addon`". The agent says `dev-copilot` (`agents/wow-standards-audit.md:28`).
  - `profiles/wow/issue-details.md:9` and `issue-summary.md:9` keep "plus the legacy `wow-addon` repo for as long as it still holds issues". Today `gh repo view tusharsaxena/wow-addon --json isArchived` → `true` with 0 open issues.
- **Reachability:** Doc text, plus an extra repo row in collection summaries.

### F-011 `[docs]` The cross-addon baseline table is fourteen library releases behind
- **Where:** `profiles/wow/agent-review.md:421` ("measured … on **2026-09-23** … against **LibKa0s v1.56.0**") and the table at `:432-443`. Today: tag v1.70.0, kit 37, 159 payload files, and the per-major minors listed in the measurement block.
- **Impact:** Every pass now has to fall into the "tag moved → stale brief" branch. The baseline no longer serves its stated purpose: "so the next pass diffs against it instead of re-deriving it".
- **Reachability:** Reviewers only; no runtime effect.

### F-012 `[correctness]` `finalize`'s push-rejection recovery path cannot succeed
- **Where:** `commands/finalize.md:114`: "If the push is rejected … run `git pull --ff-only origin <default>` once. If it fast-forwards, re-run the gate and push again".
- **Problem:** By 3e the local `<default>` carries an unpushed `--no-ff` merge commit, or the 3c commit when there was no branch. A rejection means origin moved, so local and origin have diverged and `--ff-only` must fail. The "fast-forwards" branch is unreachable, and every rejection ends in the stop branch.
- **Impact:** The outcome is safe, since it stops, but the spec describes a recovery that never happens and costs a doomed pull.
- **Reachability:** A `finalize` run where origin moved between 3d's pull and 3e's push.

### F-013 `[correctness]` The matcher's false negatives on `sh -c` and `ulimit -v unlimited`
- **Where:**
  - `scripts/bounded_runs.py:273-277`: for a shell with args, only a script basename of `run-automated-tests.sh` is considered. So `bash -c "lua tests/run.lua"` and `sh -c "luacheck ."` both returned `[]` today.
  - `:307`: `\bulimit\s+(-[A-Za-z]*v|-v)\b` counts `ulimit -v unlimited; timeout 0 lua tests/run.lua` as bounded (returned `[]`).
- **Impact:** The documented design accepts false negatives, but `sh -c` is ordinary rather than exotic, and the hook is the backstop the runner relies on.
- **Reachability:** An agent that wraps a heavy run in `bash -c`.

### F-014 `[tests]` The bounded-runs tests leak temporary directories on every run
- **Where:** `scripts/test_bounded_runs.py:17` (`d = tempfile.mkdtemp()` in `repo()`), `:136` (`XDG_CACHE_HOME=tempfile.mkdtemp()`), `:155` (`HOME=tempfile.mkdtemp()`). None are removed. Compare `test_detect_profile.py:31-36`, which uses `TemporaryDirectory` with cleanup.
- **Reachability:** The test suite only.

### F-015 `[docs]` The user-facing profile list omits the `tooling` kind
- **Where:**
  - `README.md:5`: "In a WoW addon repo (or `LibKa0s`, or `WowAddonStandards`)…".
  - `README.md:51`: "### WoW-only — WoW addon, `LibKa0s` and `WowAddonStandards` repos".
  - `.claude-plugin/plugin.json:3`: "…via WoW overlays in WoW addon, LibKa0s and WowAddonStandards repos", mirrored in `marketplace.json:12`.
- **Problem:** None of these mention the `tooling` kind that the table at `README.md:14` defines.
- **Reachability:** Doc text.

## Upstream findings

None. The LibKa0s kit uses the same `timeout --foreground` pattern (`testkit/framework.lua:124`, `testkit/run-automated-tests.sh:152`), but each process it launches carries its own guard, as its comment at `framework.lua:43` says ("a grandchild is still bounded, by its own guard"). That is a deliberate design rather than a defect, so it is not raised upstream.

## Fix directions (one line each, standards-checked)

- F-001: drop `--foreground` when stdin is not a TTY, so `timeout` signals the whole process group.
- F-002: treat `command -v|-V` as a lookup.
- F-003: resolve a symlinked path to its target before rewriting.
- F-004: give all four overlays one collection definition.
- F-005: use `mktemp`.
- F-006: add a tempdir harness. New scripts are LF with the exec bit set through `git update-index --chmod=+x` (line-endings-§3; `CLAUDE.md:65`).
- F-007: grant `Edit`, and say "commit on a branch, never push".
- The rest are doc and spec edits.

None of these touches `libs/` or `tests/_kit/`, and none introduces a deviation from standard v2.76.1.
