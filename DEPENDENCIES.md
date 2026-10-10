# DEPENDENCIES.md — dev-copilot

The toolchain contract for **this** repository (documentation-§7).

> **Read this first.** This is a **documentation-and-tooling repo** (`documentation-§8`; it declares
> `kind=tooling` in its `.dev-copilot` file), not an addon: no `.toc`, no Lua, no `libs/`, no
> `tests/` harness, nothing that loads in the WoW client. `documentation-§7` still binds, but it is
> read for that repo kind — a short **required** list, an explicit **not used here** list with
> reasons, and no invented rows. Every entry below names the `file:line` in *this* tree that needs
> it; an entry with no such line does not belong here.
>
> The inventory is stated by the commands that produce it, not by counts that drift with every
> commit: `git ls-files | wc -l` for the whole tree, `git ls-files '*.md' | wc -l` for the Markdown,
> and `git ls-files docs` for the docs store. The Markdown is the command specs (`commands/`), the
> agent specs (`agents/`), the WoW overlays (`profiles/wow/`), the root docs, and `docs/` — the
> `docs/ARCHITECTURE.md` hub plus three frozen stores it registers as directory rows:
> `docs/superpowers/` (design specs and plans), `docs/audits/<date>/` and `docs/reviews/<date>/`.
> Beside the Markdown sit the two JSON manifests under `.claude-plugin/`, `hooks/hooks.json`, the
> Python under `scripts/` — the modules (the detector, the overlay checker, the bounded-runs matcher, the CurseForge journal
> fetcher) and one `test_*.py` each for those four and for the line-ending hook — the Bash hook scripts
> (`scripts/*.sh`), four extensionless executables — the Bash runner `scripts/ka0s-bounded` and the
> three POSIX `sh` exec wrappers on the plugin's PATH entry, `bin/ka0s-bounded`,
> `bin/dev-copilot-profile` and `bin/ka0s-curseforge` — plus `LICENSE`, `.gitattributes`, `.gitignore` and the `.dev-copilot`
> profile override. Line endings are **LF** here, not the CRLF the client-bound addon repos pin.

## The short version

Clone it, then point Claude Code at it as a plugin. There is no build step and no package manifest —
the Python files are standard-library-only and the shell scripts are Bash, apart from the three
one-line POSIX `sh` wrappers in `bin/`, which only `exec` the Bash runner, the Python detector and the
Python CurseForge fetcher.

```sh
git clone https://github.com/tusharsaxena/dev-copilot.git
cd dev-copilot
python3 scripts/test_detect_profile.py    # the detector
python3 scripts/test_check_overlays.py    # the overlay checker
python3 scripts/test_bounded_runs.py      # the bounded-runs matcher and hook
python3 scripts/test_normalize_eol.py     # the line-ending hook
python3 scripts/test_curseforge_journal.py  # the CurseForge journal fetcher
python3 scripts/check_overlays.py         # the live overlays against their bases
```

## Runtime — what the plugin needs on the machine running Claude Code

The hooks run on every Bash call and every file write, and every shared or `wow-*` command runs the
detector as its Step 0, so an absence here is felt immediately. All six ship with a stock WSL2
Ubuntu install; none needs a language package manager.

| Software | Package manager | Why this repo needs it | Evidence | Install (WSL2 / Ubuntu) | Verify |
|---|---|---|---|---|---|
| **bash** ≥ 4.2 | `apt` (`bash`) | Both hooks are invoked as `bash <script>`, and `scripts/ka0s-bounded` uses Bash-only syntax (arrays, `exec {fd}>`). | `hooks/hooks.json:9`, `hooks/hooks.json:20`; `scripts/ka0s-bounded:1`, `:86`, `:117` | preinstalled; `sudo apt update && sudo apt install -y bash` | `bash --version` |
| **python3** ≥ 3.9 (the CurseForge fetcher's report times use `zoneinfo`, new in 3.9, with the system tz database in `/usr/share/zoneinfo`; Ubuntu 22.04 ships 3.10) | `apt` (`python3`) | The repo profile detector every command's Step 0 runs (`bin/dev-copilot-profile` `exec`s it), the PreToolUse guard, and the PostToolUse hook's `python3 -c` JSON parse, plus the CurseForge journal fetcher `bin/ka0s-curseforge` `exec`s. Standard library only — `argparse`, `datetime`, `glob`, `html.parser`, `json`, `os`, `re`, `subprocess`, `sys`, `time`, `urllib`. | `bin/dev-copilot-profile:8`; `scripts/detect_profile.py:1`, `:27-30`; `scripts/bounded_runs.py:1`, `:33-36`; `scripts/bounded-runs-hook.sh:30`; `scripts/normalize-eol.sh:15`; `bin/ka0s-curseforge:8`; `scripts/curseforge_journal.py:1` | `sudo apt install -y python3` | `python3 --version` |
| **git** ≥ 2.34 (Ubuntu 22.04's; any recent git has `check-attr` and `rev-parse --show-toplevel`) | `apt` (`git`) | The detector classifies at the git top-level and reads the `origin` URL; the line-ending hook asks git — and only git — what a written file's declared ending is (`git rev-parse --show-toplevel`, then `git check-attr text eol`). | `scripts/detect_profile.py:41`, `:48`, `:89`; `scripts/normalize-eol.sh:41`, `:57`; `scripts/test_normalize_eol.py:40`; `scripts/curseforge_journal.py:92` (the fetcher finds the journal and the cwd addon by git top-level) | `sudo apt install -y git` | `git --version` |
| **perl** ≥ 5.10 (the hook uses only `-i`, `-0777` and a fixed-width lookbehind, all far older; any recent perl) | `apt` (`perl`) | The line-ending hook does the byte rewrite in perl rather than sed, deliberately, because BSD and GNU `sed -i` differ. Both the CRLF and the LF branch use it. | `scripts/normalize-eol.sh:68`, `:73`, `:81`; `scripts/test_normalize_eol.py:57-60` | preinstalled; `sudo apt install -y perl` | `perl --version` |
| **coreutils** (`readlink -f`, `timeout`) ≥ 8.30 (Ubuntu 20.04's; any recent GNU coreutils has `readlink -f` and `timeout -k`) | `apt` (`coreutils`) | `bin/dev-copilot-profile` and `bin/ka0s-bounded` resolve their own location with `readlink -f` (GNU), and the line-ending hook resolves a symlinked file to its target with it before rewriting. `ka0s-bounded`'s wall-clock bound is `timeout -k 10`, with `--foreground` added only when stdin is a terminal (it keeps Ctrl-C working there; off a terminal, timeout signals the whole process group so forked children die with the run); `timeout` is probed with `command -v`, so an absence drops the bound rather than failing the run. | `bin/dev-copilot-profile:8`; `bin/ka0s-bounded:10`; `scripts/normalize-eol.sh:36`; `scripts/ka0s-bounded:106-111` | preinstalled; `sudo apt install -y coreutils` | `readlink --version`; `timeout --version` |
| **grep**, **sed** | `apt` (`grep`, `sed`; both Essential, always present) | The line-ending hook reads `git check-attr`'s two answers with `sed` and tests a file for CR bytes with `grep`. | `scripts/normalize-eol.sh:58-59`, `:78` | preinstalled; `sudo apt install -y grep sed` | `grep --version`; `sed --version` |

If the plugin's `bin/` is not on PATH, the bare `dev-copilot-profile` is not found and every Step 0
falls back to `"${CLAUDE_PLUGIN_ROOT}/bin/dev-copilot-profile"` — same script, same python3.

## Runtime — optional, and degraded gracefully when absent

`ka0s-bounded` probes each of these and drops the bound it provides rather than refusing to run. They
are listed because losing one silently weakens the guard the bounded-runs hook exists to enforce.

| Software | Package manager | Why this repo needs it | Evidence | Install (WSL2 / Ubuntu) | Verify |
|---|---|---|---|---|---|
| **util-linux** (`flock`) | `apt` (`util-linux`) | The machine-wide slot pool, so several repos and agents can start bounded runs in parallel without piling onto the same RAM. | `scripts/ka0s-bounded:70`, `:87` | preinstalled; `sudo apt install -y util-linux` | `flock --version` |
| **awk** | `apt` (`mawk`, preinstalled; or `gawk`) | `ka0s-bounded` reads `MemTotal`/`MemAvailable` from `/proc/meminfo` to size the tree cap and the slot pool; without it, it falls back to fixed 4096/16384 MB guesses. | `scripts/ka0s-bounded:51`, `:55`, `:57` | preinstalled; `sudo apt install -y mawk` | `awk -W version 2>/dev/null \|\| awk --version` |
| **systemd** (`systemd-run`) | `apt` (`systemd`) | The process-*tree* memory cap — a transient `--user --scope` with `MemoryMax`, `MemorySwapMax=0` and `TasksMax`, so a runaway runner is killed as one unit instead of by the kernel choosing among everything on the machine. Needs a user session bus; skipped where there is none. | `scripts/ka0s-bounded:114-118` | preinstalled on systemd WSL2; `sudo apt install -y systemd` | `systemd-run --version` |

## Development — what you need to change this repo

| Software | Package manager | Why this repo needs it | Evidence | Install (WSL2 / Ubuntu) | Verify |
|---|---|---|---|---|---|
| **python3** (with `unittest`) | `apt` (`python3`) | The `test_*.py` files, and the overlay checker that guards every edit to `commands/`, `agents/` or `profiles/`. | `scripts/test_detect_profile.py:1-14`; `scripts/test_check_overlays.py:1-12`; `scripts/test_bounded_runs.py:1-13`; `scripts/test_normalize_eol.py:1`; `scripts/test_curseforge_journal.py:1-20`; `scripts/check_overlays.py:1-20`; `CLAUDE.md:78-83` | `sudo apt install -y python3` | `python3 scripts/check_overlays.py` |
| **git** | `apt` (`git`) | The detector's tests build fixture repos with `git init` and `git remote add`, and the line-ending hook's tests build one per case with `git init` and a `.gitattributes`. `.gitattributes` pins this repo to **LF**, and `git check-attr` is the only correct reader of that pin. | `scripts/test_detect_profile.py:25`, `:27`; `scripts/test_normalize_eol.py:40`; `.gitattributes`; `scripts/normalize-eol.sh:57` | `sudo apt install -y git` | `git check-attr text eol -- CLAUDE.md` |
| **Claude Code** | its own installer | The specs in `commands/`, `agents/` and `profiles/wow/` are only executable as plugin slash commands and subagents; `/reload-plugins` is the load check. | `.claude-plugin/plugin.json`; `CLAUDE.md:86` | see the Claude Code docs | `/reload-plugins` in a session |

## Required on the machine of whoever *runs* a command (not of this repo)

Several specs shell out. These are not dependencies of this tree — nothing here imports or invokes
them, except that `scripts/curseforge_journal.py` calls the two CurseForge endpoints itself — but a command will report a skip or a stall without them, so they are named once.

| Software | Package manager | Which specs need it | What happens without it |
|---|---|---|---|
| **`gh`** (GitHub CLI), authenticated | `apt` (`gh`, from the GitHub apt repository) | the six `issue-*` commands (any repo), `wow-harvest-standards`, `wow-revendor-libka0s`'s decline filing, `wow-curseforge-comments`' issue hand-off, the `wow-standards-audit` agent's register read | the `issue-*` commands stop rather than degrade (`commands/issue-audit.md:72`, `CLAUDE.md:126`); the others report an unfiled write rather than degrading silently (`CLAUDE.md:72`) |
| **network access to raw GitHub** | — | `wow-standards-audit`, `wow-new-addon`, `wow-revendor-standards`, `wow-automated-tests`, `wow-perf-analysis` fetch the `WowAddonStandards` playbooks at runtime, with `curl -fsSL` (`apt` `curl`; `commands/wow-new-addon.md:212`, `commands/wow-automated-tests.md:39`, `commands/wow-perf-analysis.md:39`); the WoW review fetches the standard for its guardrail | the first three hard-stop rather than work from memory; the review proceeds and says the cross-check was skipped (`CLAUDE.md:109`) |
| **a CurseForge Core API key** and network access to `api.curseforge.com` and `www.curseforge.com` | console.curseforge.com issues the key; it goes in `CURSEFORGE_API_KEY` or `~/.claude/dev-copilot/curseforge.env` | `wow-curseforge-releases`, `wow-curseforge-comments` | the fetcher stops with an error naming where the key goes; a 403 means a wrong or revoked key (`scripts/curseforge_journal.py`, `commands/wow-curseforge-releases.md`) |
| **sibling checkouts on local disk** | — | `wow-revendor-libka0s` reads `../LibKa0s` at a git tag; `wow-harvest-standards` reads every addon repo and the standards working tree; `finalize` and the issue commands' `all` scope read sibling repos; `wow-curseforge-releases` and `wow-curseforge-comments` read the `Ka0sAddonsCommonTasks` journal (or `$KA0S_CF_JOURNAL`) and every roster addon's TOC for its project id | reported as not run, never inferred (`commands/wow-revendor-libka0s.md`, `commands/wow-harvest-standards.md`) |
| **the target repo's own toolchain** | whatever that repo uses | `run-tests`, `review`, `bump-version` and `finalize`'s gate run the lint/test/type-check tools a *generic* repo declares (npm/pnpm/yarn, pytest/ruff/mypy, go, cargo, make, gradle/maven, dotnet, …) | a **stated skip**, never an inferred pass (`commands/run-tests.md`) |
| **Lua 5.1**, **luacheck**, **lizard** | `apt` (`lua5.1`), `luarocks` (`luacheck`), `pipx` (`lizard`; bare `pip` fails on Ubuntu 24.04's PEP 668 marker) | in a WoW repo: `run-tests`, `review`, `bump-version`, `wow-standards-audit`, `wow-automated-tests`, `wow-new-addon` (its first automated-test bundle), plus Lua and `luacheck` for the gates `finalize` and `wow-revendor-libka0s` run — all of which execute **inside an addon repo**, never here (`commands/wow-new-addon.md:246`, `profiles/wow/finalize.md:32-33`, `commands/wow-revendor-libka0s.md:317`) | a **stated skip** / *not run*, never an inferred pass and never a fabricated number (`CLAUDE.md:117`, `CLAUDE.md:112`) |

## Not used here, and why

Listed so a reader arriving from an addon's `DEPENDENCIES.md` can tell "not installed" from "not
applicable".

| Software | Status | Why |
|---|---|---|
| **Lua 5.1** | **not used here** | No `.lua` file is tracked in this repo. The Lua the specs talk about runs in the addon repo the command is invoked from. |
| **luacheck** | **not used here** | Lint needs Lua to lint, and there is no `.luacheckrc`. |
| **lizard** | **not used here** | Cyclomatic complexity over zero Lua functions is not a measurement. The Python files and shell scripts are on no complexity gate. |
| **A WoW client** | **not used here** | Nothing here loads as an addon; there is no `.toc` and no `docs/smoke-tests.md`. |
| **pip / a `requirements.txt` / `pyproject.toml`** | **not used here** | All the Python files import only the standard library (`argparse`, `contextlib`, `datetime`, `glob`, `html.parser`, `io`, `json`, `os`, `re`, `shutil`, `subprocess`, `sys`, `tempfile`, `time`, `unittest`, `urllib`, `zoneinfo`). Adding a manifest would be the first thing to go stale. |
| **packager / release tooling** | **not used here** | No `.pkgmeta` and no artifact to publish. The plugin is consumed from the repo by Claude Code (the repo is its own marketplace), not released as a build. |
