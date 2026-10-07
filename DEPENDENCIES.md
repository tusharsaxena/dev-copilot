# DEPENDENCIES.md — dev-copilot

The toolchain contract for **this** repository (documentation-§7).

> **Read this first.** This is a **documentation-and-tooling repo** (`documentation-§8`; it declares
> `kind=tooling` in its `.dev-copilot` file), not an addon: no `.toc`, no Lua, no `libs/`, no
> `tests/` harness, nothing that loads in the WoW client. `documentation-§7` still binds, but it is
> read for that repo kind — a short **required** list, an explicit **not used here** list with
> reasons, and no invented rows. Every entry below names the `file:line` in *this* tree that needs
> it; an entry with no such line does not belong here.
>
> The repo is 61 tracked files: 43 Markdown (22 command specs, 2 agent specs, 13 WoW overlays,
> 3 design/plan notes under `docs/`, and the 3 root docs), two JSON manifests plus `hooks/hooks.json`,
> six Python files (the detector, the overlay checker, the bounded-runs matcher and a unit test for
> each), two Bash scripts, three extensionless executables — the Bash runner `scripts/ka0s-bounded`
> and the two POSIX `sh` exec wrappers on the plugin's PATH entry, `bin/ka0s-bounded` and
> `bin/dev-copilot-profile` — plus `LICENSE`, `.gitattributes`, `.gitignore` and the `.dev-copilot`
> profile override. Line endings are **LF** here, not the CRLF the client-bound addon repos pin.

## The short version

Clone it, then point Claude Code at it as a plugin. There is no build step and no package manifest —
the six Python files are standard-library-only and the shell scripts are Bash, apart from the two
one-line POSIX `sh` wrappers in `bin/`, which only `exec` the Bash runner and the Python detector.

```sh
git clone https://github.com/tusharsaxena/dev-copilot.git
cd dev-copilot
python3 scripts/test_detect_profile.py    # the detector
python3 scripts/test_check_overlays.py    # the overlay checker
python3 scripts/test_bounded_runs.py      # the bounded-runs matcher and hook
python3 scripts/check_overlays.py         # the live overlays against their bases
```

## Runtime — what the plugin needs on the machine running Claude Code

The hooks run on every Bash call and every file write, and every shared or `wow-*` command runs the
detector as its Step 0, so an absence here is felt immediately. All five ship with a stock WSL2
Ubuntu install; none needs a language package manager.

| Software | Package manager | Why this repo needs it | Evidence | Install (WSL2 / Ubuntu) | Verify |
|---|---|---|---|---|---|
| **bash** ≥ 4.2 | `apt` (`bash`) | Both hooks are invoked as `bash <script>`, and `scripts/ka0s-bounded` uses Bash-only syntax (arrays, `exec {fd}>`). | `hooks/hooks.json:9`, `hooks/hooks.json:20`; `scripts/ka0s-bounded:1`, `:86`, `:117` | preinstalled; `sudo apt update && sudo apt install -y bash` | `bash --version` |
| **python3** ≥ 3.8 | `apt` (`python3`) | The repo profile detector every command's Step 0 runs (`bin/dev-copilot-profile` `exec`s it), the PreToolUse guard, and the PostToolUse hook's `python3 -c` JSON parse. Standard library only — `glob`, `json`, `os`, `re`, `subprocess`, `sys`. | `bin/dev-copilot-profile:8`; `scripts/detect_profile.py:1`, `:27-30`; `scripts/bounded_runs.py:1`, `:33-36`; `scripts/bounded-runs-hook.sh:33`; `scripts/normalize-eol.sh:15` | `sudo apt install -y python3` | `python3 --version` |
| **git** ≥ 2.34 | `apt` (`git`) | The detector classifies at the git top-level and reads the `origin` URL; the line-ending hook asks git — and only git — what a written file's declared ending is (`git rev-parse --show-toplevel`, then `git check-attr text eol`). | `scripts/detect_profile.py:41`, `:48`, `:89`; `scripts/normalize-eol.sh:36`, `:52` | `sudo apt install -y git` | `git --version` |
| **perl** ≥ 5.10 | `apt` (`perl`) | The line-ending hook does the byte rewrite in perl rather than sed, deliberately, because BSD and GNU `sed -i` differ. Both the CRLF and the LF branch use it. | `scripts/normalize-eol.sh:63`, `:68`, `:76` | preinstalled; `sudo apt install -y perl` | `perl --version` |
| **coreutils** (`readlink -f`, `timeout`) ≥ 8.30 | `apt` (`coreutils`) | `bin/dev-copilot-profile` and `bin/ka0s-bounded` resolve their own location with `readlink -f` (GNU). `ka0s-bounded`'s wall-clock bound is `timeout -k 10`, with `--foreground` added only when stdin is a terminal (it keeps Ctrl-C working there; off a terminal, timeout signals the whole process group so forked children die with the run); `timeout` is probed with `command -v`, so an absence drops the bound rather than failing the run. | `bin/dev-copilot-profile:8`; `bin/ka0s-bounded:10`; `scripts/ka0s-bounded:106-111` | preinstalled; `sudo apt install -y coreutils` | `readlink --version`; `timeout --version` |

If the plugin's `bin/` is not on PATH, the bare `dev-copilot-profile` is not found and every Step 0
falls back to `"${CLAUDE_PLUGIN_ROOT}/bin/dev-copilot-profile"` — same script, same python3.

## Runtime — optional, and degraded gracefully when absent

`ka0s-bounded` probes each of these and drops the bound it provides rather than refusing to run. They
are listed because losing one silently weakens the guard the bounded-runs hook exists to enforce.

| Software | Package manager | Why this repo needs it | Evidence | Install (WSL2 / Ubuntu) | Verify |
|---|---|---|---|---|---|
| **util-linux** (`flock`) | `apt` (`util-linux`) | The machine-wide slot pool, so several repos and agents can start bounded runs in parallel without piling onto the same RAM. | `scripts/ka0s-bounded:70`, `:87` | preinstalled; `sudo apt install -y util-linux` | `flock --version` |
| **systemd** (`systemd-run`) | `apt` (`systemd`) | The process-*tree* memory cap — a transient `--user --scope` with `MemoryMax`, `MemorySwapMax=0` and `TasksMax`, so a runaway runner is killed as one unit instead of by the kernel choosing among everything on the machine. Needs a user session bus; skipped where there is none. | `scripts/ka0s-bounded:114-118` | preinstalled on systemd WSL2; `sudo apt install -y systemd` | `systemd-run --version` |

## Development — what you need to change this repo

| Software | Package manager | Why this repo needs it | Evidence | Install (WSL2 / Ubuntu) | Verify |
|---|---|---|---|---|---|
| **python3** (with `unittest`) | `apt` (`python3`) | The three test files, and the overlay checker that guards every edit to `commands/`, `agents/` or `profiles/`. | `scripts/test_detect_profile.py:1-14`; `scripts/test_check_overlays.py:1-12`; `scripts/test_bounded_runs.py:1-13`; `scripts/check_overlays.py:1-20`; `CLAUDE.md:89-92` | `sudo apt install -y python3` | `python3 scripts/check_overlays.py` |
| **git** | `apt` (`git`) | The detector's tests build fixture repos with `git init` and `git remote add`. `.gitattributes` pins this repo to **LF**, and `git check-attr` is the only correct reader of that pin. | `scripts/test_detect_profile.py:25`, `:27`; `.gitattributes`; `scripts/normalize-eol.sh:52` | `sudo apt install -y git` | `git check-attr text eol -- CLAUDE.md` |
| **Claude Code** | its own installer | The specs in `commands/`, `agents/` and `profiles/wow/` are only executable as plugin slash commands and subagents; `/reload-plugins` is the load check. | `.claude-plugin/plugin.json`; `CLAUDE.md:95` | see the Claude Code docs | `/reload-plugins` in a session |

## Required on the machine of whoever *runs* a command (not of this repo)

Several specs shell out. These are not dependencies of this tree — nothing here imports or invokes
them — but a command will report a skip or a stall without them, so they are named once.

| Software | Package manager | Which specs need it | What happens without it |
|---|---|---|---|
| **`gh`** (GitHub CLI), authenticated | `apt` (`gh`, from the GitHub apt repository) | the six `issue-*` commands (any repo), `wow-harvest-standards`, `wow-revendor-libka0s`'s decline filing, the `wow-standards-audit` agent's register read | `issue-audit` treats it as a skipped sweep; the others stop or report an unfiled write rather than degrading silently (`CLAUDE.md:134`, `CLAUDE.md:135`) |
| **network access to raw GitHub** | — | `wow-standards-audit`, `wow-new-addon`, `wow-revendor-standards`, `wow-automated-tests`, `wow-perf-analysis` fetch the `WowAddonStandards` playbooks at runtime; the WoW review fetches the standard for its guardrail | the first three hard-stop rather than work from memory; the review proceeds and says the cross-check was skipped (`CLAUDE.md:117`) |
| **sibling checkouts on local disk** | — | `wow-revendor-libka0s` reads `../LibKa0s` at a git tag; `wow-harvest-standards` reads every addon repo and the standards working tree; `finalize` and the issue commands' `all` scope read sibling repos | reported as not run, never inferred (`commands/wow-revendor-libka0s.md`, `commands/wow-harvest-standards.md`) |
| **the target repo's own toolchain** | whatever that repo uses | `run-tests`, `review`, `bump-version` and `finalize`'s gate run the lint/test/type-check tools a *generic* repo declares (npm/pnpm/yarn, pytest/ruff/mypy, go, cargo, make, gradle/maven, dotnet, …) | a **stated skip**, never an inferred pass (`commands/run-tests.md`) |
| **Lua 5.1**, **luacheck**, **lizard** | `apt` (`lua5.1`), `luarocks` (`luacheck`), `pipx` (`lizard`; bare `pip` fails on Ubuntu 24.04's PEP 668 marker) | in a WoW repo: `run-tests`, `review`, `bump-version`, `wow-standards-audit`, `wow-automated-tests`, `wow-new-addon` (its first automated-test bundle), plus Lua and `luacheck` for the gates `finalize` and `wow-revendor-libka0s` run — all of which execute **inside an addon repo**, never here (`commands/wow-new-addon.md:244`, `profiles/wow/finalize.md:28-29`, `commands/wow-revendor-libka0s.md:316`) | a **stated skip** / *not run*, never an inferred pass and never a fabricated number (`CLAUDE.md:125`, `CLAUDE.md:120`) |

## Not used here, and why

Listed so a reader arriving from an addon's `DEPENDENCIES.md` can tell "not installed" from "not
applicable".

| Software | Status | Why |
|---|---|---|
| **Lua 5.1** | **not used here** | No `.lua` file is tracked in this repo. The Lua the specs talk about runs in the addon repo the command is invoked from. |
| **luacheck** | **not used here** | Lint needs Lua to lint, and there is no `.luacheckrc`. |
| **lizard** | **not used here** | Cyclomatic complexity over zero Lua functions is not a measurement. The six Python files and five shell scripts are on no complexity gate. |
| **A WoW client** | **not used here** | Nothing here loads as an addon; there is no `.toc` and no `docs/smoke-tests.md`. |
| **pip / a `requirements.txt` / `pyproject.toml`** | **not used here** | All six Python files import only the standard library (`glob`, `json`, `os`, `re`, `subprocess`, `sys`, `tempfile`, `unittest`). Adding a manifest would be the first thing to go stale. |
| **packager / release tooling** | **not used here** | No `.pkgmeta` and no artifact to publish. The plugin is consumed from the repo by Claude Code (the repo is its own marketplace), not released as a build. |
