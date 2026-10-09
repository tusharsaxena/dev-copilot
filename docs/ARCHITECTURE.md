# ARCHITECTURE.md — dev-copilot

Engineer context for **this** repository, and the hub of its doc set (`documentation-§8`).

> **This repo is a documentation-and-tooling repo** (`documentation-§8`), the collection's third repo
> kind beside addons and Ka0s-owned library repos. It ships nothing to the WoW client and vendors no
> payload into any addon's `libs/`, so §8's applicability lists govern it rather than the addon rule
> set. §8 reduces this file's mandated sections to **five**: Overview, Module Map read as the
> file-and-path map, Known Limitations, the documentation map and the deviation register. The five
> addon-runtime sections (Settings Schema, Message Bus, Slash Commands, Event Subscriptions, Taint
> Notes) are not written here as "not applicable" headings, because §8 says they **SHOULD NOT** be:
> the exemption is granted once, in the standard.

## Overview

A **Claude Code plugin**: Markdown command, agent and overlay specs, a stdlib-only Python profile
detector and overlay checker, two hooks (line endings and bounded runs) with the bounded runner they
point at, and two JSON manifests. There is no compiled code and no package manifest. The root
`CLAUDE.md` is the full agent brief (purpose, repo profiles, the overlay contract, conventions and
footguns); `README.md` is the user-facing description of every command; `DEPENDENCIES.md` is the
toolchain contract. This file holds what those three point at: the file-and-path map, the known
limitations and the doc register.

**How it is consumed.** The repo is its own marketplace. A user installs it with
`/plugin install dev-copilot@dev-copilot`; Claude Code copies it into its plugin cache, auto-discovers
`commands/` and `agents/` by directory (there is no registration file), puts `bin/` on `PATH` and
registers both hooks from `hooks/hooks.json`. `profiles/` is not discovered: overlays are plain files a
command Reads at run time from the detector's `root`.

**One plugin, two profiles.** Every command first runs `dev-copilot-profile` to classify the repo it is
in. In a `generic` repo it follows its base spec and never reads WoW text; in a `wow` repo (a Ka0s
addon, `LibKa0s`, `WowAddonStandards`, or a tooling repo such as this one, which opts in through its
`.dev-copilot` override) it also applies its `profiles/wow/<name>.md` overlay. Seven of the eight
`wow-*` commands refuse in a generic repo; `wow-new-addon` never refuses, because the addon it
scaffolds does not exist yet. Five of the WoW commands and the WoW review fetch the living
Ka0s WoW Addon Standard over HTTPS at run time, so the standard can change without a plugin release.

## Module Map

Read as the **file-and-path map** (`documentation-§8`): which paths exist, what reads each one, and
which are **addressed by name or path** and therefore breaking to rename.

- `.claude-plugin/plugin.json` — plugin manifest; **the single source of truth for the version**.
  Read by Claude Code at install and reload.
- `.claude-plugin/marketplace.json` — marketplace entry; carries a **mirror of the description** (no
  version field of its own). Read by `/plugin marketplace add|update`.
- `.dev-copilot` — this repo's own profile override (`profile=wow`, `kind=tooling`), so its docs and
  reviews follow the WoW documentation lane. Without it the detector would call this repo `generic`.
  Read by `scripts/detect_profile.py`.
- `bin/dev-copilot-profile` — POSIX `sh` one-liner that `exec`s `python3 ../scripts/detect_profile.py`
  (resolved through `readlink -f`). Claude Code puts the plugin's `bin/` on `PATH`, so this is what
  makes the **bare** `dev-copilot-profile` in every Step 0 resolve. Keep it LF and `+x`.
- `bin/ka0s-bounded` — the same shape for the bounded runner: a POSIX `sh` one-liner that `exec`s
  `../scripts/ka0s-bounded`, making the **bare** name `ka0s-bounded` resolve. Keep it LF and `+x`.
- `scripts/detect_profile.py` — the repo profile detector (`CLAUDE.md` § *Repo profiles*).
  `scripts/test_detect_profile.py` — its unit test (tempdir fixtures per kind, subdirectory, non-git
  dir, nested/Interface-less `.toc`, override with CRLF/comments/odd spacing, CLI key order).
- `scripts/check_overlays.py` — overlay ↔ base consistency checker (`CLAUDE.md` § *Overlay contract*);
  holds `STEP0_BLOCK` and the `SHARED` command list. `scripts/test_check_overlays.py` — its unit test.
- `commands/*.md` — **22** slash-command specs (`/dev-copilot:<name>`), each also invocable as a Skill
  of the same name:
  - **14 shared**: `diff`, `commit`, `sync-docs`, `review`, `run-tests`, `bump-version`, `finalize`,
    `execution-status`, `issue-add`, `issue-audit`, `issue-triage`, `issue-details`,
    `issue-fetch-all`, `issue-summary`. Generic core; WoW behavior in an overlay.
  - **8 WoW-only**: `wow-new-addon`, `wow-bump-interface`, `wow-automated-tests`,
    `wow-perf-analysis`, `wow-revendor-libka0s`, `wow-revendor-standards`, `wow-harvest-standards`,
    `wow-standards-audit`. Each opens with a guard step (a refusal, or for
    `wow-new-addon` a nesting check); no overlay.
  - Two are thin **wrappers that dispatch to a subagent**: `review` → `dev-copilot:review`,
    `wow-standards-audit` → `dev-copilot:wow-standards-audit`. The other twenty act directly.
- `agents/*.md` — **2** subagent specs: `review` (generic principal-level review → `reviews/<date>/`;
  in a WoW repo, via its overlay, the WoW review → `docs/reviews/<date>/` with `03_SMOKE_TESTS.md`;
  fetches the standard only to keep its own remediation compliant, and does **not** audit) and
  `wow-standards-audit` (read-only compliance audit → `docs/audits/<date>/`, over a three-kind
  rotation rather than addons alone).
- `profiles/wow/*.md` — **13** WoW overlays: one per shared command that has WoW deltas
  (`bump-version`, `commit`, `diff`, `finalize`, the six `issue-*`, `run-tests`, `sync-docs`) plus
  `agent-review.md` for the review agent. `review` (the wrapper) and `execution-status` have none.
  Read by the matching base's Step 0, only when the profile is `wow`.
- `hooks/hooks.json` — registers both hooks: `PreToolUse(Bash)` → `scripts/bounded-runs-hook.sh` and
  `PostToolUse(Write|Edit|MultiEdit)` → `scripts/normalize-eol.sh`, each by
  `${CLAUDE_PLUGIN_ROOT}`-relative path.
- `scripts/normalize-eol.sh` — the line-ending-normalization hook. It normalizes a just-written file
  to whatever `.gitattributes` declares for it, **CRLF** or **LF**, and exits silently when nothing is
  declared (`line-endings-§2`). It reads `text` **and** `eol`, never `eol` alone: `binary` expands to
  `-text` and says nothing about `eol`, so a marked PNG in a CRLF-pinned repo answers `eol: crlf` for a
  file git will never convert, and rewriting its bytes on that answer corrupts the asset
  (`line-endings-§7`). It resolves a symlinked path with `readlink -f` before anything else, because
  `perl -i` on a link path would replace the link with a regular file and leave the target
  unconverted; the target's own repo and `.gitattributes` decide. Renamed from `normalize-crlf.sh`
  when it gained the LF arm. `scripts/test_normalize_eol.py` — its harness (a throwaway git repo per
  case; both arms, binary and `-text` inside a CRLF pin, symlinks, files outside any repo).
- `scripts/bounded-runs-hook.sh` + `scripts/bounded_runs.py` + `scripts/ka0s-bounded` — the
  **bounded-runs** hook, its Python matcher and the runner it points at. The hook refreshes one
  symlink to the installed runner, `~/.claude/dev-copilot/bin/ka0s-bounded` (the path specs and the
  refusal message name, stable across plugin-cache version directories), then denies a heavy run
  (`lua tests/run.lua`/`tests/perf.lua`, `run-automated-tests.sh`, `luacheck`, `lizard`) that is not
  prefixed with the runner, not bounded by hand (a numeric `ulimit -v <kB>` **and** `timeout`;
  `ulimit -v unlimited` is no bound), not opted out (`KA0S_BOUNDED_HOOK=off`), and, for Lua runners
  only, not in a repo whose `tests/_kit` is kit revision **23+** (that kit self-bounds with the same
  `KA0S_KIT_*` variables). It **fails open**: any error exits 0 silently. The matcher looks only at
  **command position**: a word inside quotes or a heredoc body is prose, while `$(…)`, backticks,
  subshells, a heredoc fed to a bare shell (`bash <<EOF`) and a shell's `-c` script string (two levels
  deep) are scanned as commands. A probe such as `command -v luacheck` is not a run. The runner caps
  process memory, process-tree memory and tasks, and wall-clock time (a timeout kills the whole run,
  children included), and queues on a machine-wide `flock` slot pool whose size it recomputes while
  it waits. `scripts/test_bounded_runs.py` — the matcher, the hook script, the runner symlink (and
  that the retired `~/.claude/wow-addon/` dir is never recreated), the `bin/ka0s-bounded` wrapper and
  the runner's timeout.
- `docs/` — design notes and frozen records kept out of the root docs: this hub, the
  `docs/superpowers/` specs and plans, and this repo's own `docs/audits/<date>/` and
  `docs/reviews/<date>/` bundles (see *Documentation map*). Nothing here is loaded by Claude Code.
- `DEPENDENCIES.md` — the root toolchain contract (`documentation-§7`, read for a
  documentation-and-tooling repo under `documentation-§8`).
- `README.md` — user-facing docs. `CLAUDE.md` — the agent brief. `LICENSE` — MIT.
- `.gitattributes` — the LF pin with the `*.sh`/`*.py` shebang carve-outs (`line-endings-§2`,
  `§3`, `§5`). `.gitignore` — Python bytecode only.

### Path-addressed surfaces — renaming any of these breaks callers

Each of these is reached **by its name or path** from outside the file that defines it, so a rename is
a breaking change (a major version bump), not a refactor:

- **`bin/dev-copilot-profile` and `bin/ka0s-bounded`** — the bare command names every Step 0, every
  suite-running spec and every user's shell history call through `PATH`.
- **The script paths in `hooks/hooks.json`** — `scripts/bounded-runs-hook.sh` and
  `scripts/normalize-eol.sh`, invoked by `${CLAUDE_PLUGIN_ROOT}`-relative path. A renamed script turns
  the hook into a silent no-op, not an error. `scripts/ka0s-bounded` is the symlink target the hook
  maintains and `bin/ka0s-bounded` execs.
- **`profiles/wow/<name>.md` overlay names** — each base's Step 0 Reads its overlay by this exact path,
  and `scripts/check_overlays.py` checks the pairing; an overlay is named after its command
  (`agent-<name>.md` for an agent).
- **`~/.claude/dev-copilot/bin/ka0s-bounded`** — the stable runner path the hook keeps pointed at the
  installed runner, named in specs, in the hook's refusal message, in the README and in other repos'
  plans and briefs. Moving the state dir from `~/.claude/wow-addon/` is what made 2.0.0 a major.
- **`commands/<name>.md` and `agents/<name>.md` filenames** — the filename **is** the public name:
  `/dev-copilot:<name>`, the Skill `dev-copilot:<name>`, and the subagent `dev-copilot:<name>`. Every
  other repo's docs, plans and memory cite these names.

## Known Limitations

- **The bounded-runs matcher is a tokenizer, not a shell parser.** It is quote- and heredoc-aware and
  reads only command position. False negatives on exotic shell (an alias, a variable holding the
  command name, `eval` of a string built from pieces) are accepted; false positives on ordinary commands are not. It also
  **fails open** on any internal error, so a broken hook allows rather than blocks.
- **The plugin Claude Code runs is the installed copy, not this checkout.** It lives under
  `~/.claude/plugins/cache/dev-copilot/dev-copilot/<version>/`. An edit here takes effect in a session
  only after it reaches the marketplace source and `/plugin marketplace update` plus `/reload-plugins`
  are run; until then the hooks and specs in use are the cached ones.
- **The line-ending hook acts only where `.gitattributes` declares an `eol`.** A file with no declared
  `eol`, or one outside any git repo, is left exactly as written; the hook never blocks a write, so a
  failure is silent.
- **Lua runs in a repo on kit revision 23+ are let through unprefixed**, on the strength of the kit
  bounding itself. A repo that pins an older kit gets the hook's refusal instead.
- **`scripts/check_overlays.py` does not check file modes.** `core.fileMode=false` on this DrvFs
  checkout hides them, so a new script's exec bit is set with `git update-index --chmod=+x` and
  checked by hand.
- **Base + overlay parity with the retired `/wow-addon:` specs is checked by hand.** The checker
  verifies markers, sections and the Step 0 block, not that every WoW instruction survived; that walk
  is a human or agent reading `4914203^2:commands/<x>.md` section by section.
- **The runtime-fetch commands need network and a reachable standard.** `wow-standards-audit`,
  `wow-new-addon` and `wow-revendor-standards` hard-stop without it; `review` degrades and says so.
  The `issue-*` family stops without an authenticated `gh`.

## Documentation map

Every `.md` this repo tracks is covered by exactly one row below: a file row, a directory row for a
tree of executable specs, or a single row for a frozen store.

| Doc | What it is |
|---|---|
| `README.md` | User-facing docs: what the plugin is, every command, the hooks, install and migration |
| `CLAUDE.md` | The agent brief: purpose, repo profiles, overlay contract, conventions and footguns |
| `DEPENDENCIES.md` | The toolchain contract (`documentation-§7`, read per `documentation-§8`) |
| `docs/ARCHITECTURE.md` | This file, the hub |
| `LICENSE` | MIT |
| `commands/*.md` (22 files) | Slash-command specs: executable instructions Claude Code runs, not documentation |
| `agents/*.md` (2 files) | Subagent specs: executable, not documentation |
| `profiles/wow/*.md` (13 files) | WoW overlays read by the bases' Step 0: executable, not documentation |
| `docs/superpowers/` | Frozen design specs and plans with their execution ledgers, named once here rather than per file |
| `docs/audits/<date>/` | Frozen bundles of this repo's own documentation-lane audits (audit-review-history), named once here rather than per file |
| `docs/reviews/<date>/` | Frozen bundles of this repo's own reviews (audit-review-history), named once here rather than per file |

The addon doc set (`docs/testing.md`, `docs/smoke-tests.md`, the topic-detail tiers and the
verification-and-record docs) is absent, and that is **compliance rather than deviation**:
`documentation-§8` places all of it in its *does not apply* list for this repo kind. How the Python
and shell scripts are verified is recorded in `DEPENDENCIES.md`, as §8 requires.

## Documented deviations

**None.**

No decline is ratified for this repo. The heading stays, empty, because `documentation-§3` requires
it present even when there is nothing in it: an absent section is indistinguishable from an unwritten
one.
