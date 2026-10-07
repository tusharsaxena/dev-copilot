# 01 — Current state: dev-copilot (standards audit, 2026-10-07)

## Run identity

| Item | Value |
|---|---|
| Repository | `dev-copilot` at `/mnt/d/Profile/Users/Tushar/Documents/GIT/dev-copilot` |
| Branch / HEAD | `feat/2026-10-07-review-audit-remediation` @ `b43200c` (identical to `master` and `origin/master`); working tree clean at audit start |
| Standard audited against | **Ka0s WoW Addon Standard v2.76.1 (2026-10-07)**, `standards/STANDARDS.md` line 1 |
| How it was resolved | `curl -fsSL` from `https://raw.githubusercontent.com/tusharsaxena/WowAddonStandards/master`: `AUDIT.md` (1156 lines, sha256 `40eb10d3…8a73`), `standards/STANDARDS.md` (255 lines, sha256 `ef6fa854…8d55`), `standards/ADDONS.md`, and all **27** section files linked from the Sections list (discovered from the index, not hard-coded). The local `../WowAddonStandards` checkout is at `f472389`, equal to `origin/master`, so the published copy and the working tree agree. |
| Repo kind | **Documentation-and-tooling** (`kind=tooling`). Detector output: `profile=wow`, `kind=tooling`, `reason=override` (from the root `.dev-copilot` file). Confirmed against `ADDONS.md` → *Documentation-and-tooling repos* (row `dev-copilot`, line 61) and the `documentation-§8` discriminator: no `.toc`, no vendored `libs/` payload. Detector and table agree. |
| Rule set used | `documentation-§8`'s three applicability lists (*Applies unchanged*, *Does not apply*, *Applies, read for this kind*) plus the four *Substitutes*, run through the **documentation lane**: internal consistency between rules, cross-references resolve, worked examples match the trees they cite, and inventories match the trees they count. Grades key on **reproduction** (how many runs a defect changes), not on player reach. |
| Prior audits | None. `docs/audits/` did not exist before this run, and the archived `wow-addon` repo has no `docs/audits/` either. This run assigns the prefix **`DC-`**. |
| Not the WowAddonStandards hazard | This is not `WowAddonStandards`, so the rules were read from the fetched `master` as Step 0 prescribes. |

## What the repository is

A Claude Code plugin with one plugin and two profiles. Every command classifies the repo it runs in with `dev-copilot-profile` and either stays generic or loads a WoW overlay. `CLAUDE.md:5-9` describes it as Markdown command, agent and overlay specs, a stdlib-only Python detector and overlay checker, hook scripts, and JSON manifests. The version is `2.0.1` (`.claude-plugin/plugin.json:4`). The repo has no git tags.

Tracked inventory (`git ls-files`, 62 files):

| Group | Count | Members |
|---|---|---|
| Command specs | 22 | `commands/*.md`: 14 shared, 8 `wow-*` |
| Agent specs | 2 | `agents/review.md`, `agents/wow-standards-audit.md` |
| WoW overlays | 13 | `profiles/wow/*.md` |
| Design and plan notes | 4 | `docs/superpowers/specs/` (2), `docs/superpowers/plans/` (2) |
| Root docs | 3 | `README.md`, `CLAUDE.md`, `DEPENDENCIES.md` |
| JSON | 3 | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `hooks/hooks.json` |
| Python | 6 | `scripts/{detect_profile,check_overlays,bounded_runs}.py` and a `test_*.py` for each |
| Shell (`.sh`) | 2 | `scripts/normalize-eol.sh`, `scripts/bounded-runs-hook.sh` |
| Extensionless executables | 3 | `scripts/ka0s-bounded` (Bash), `bin/ka0s-bounded`, `bin/dev-copilot-profile` (POSIX sh) |
| Other | 4 | `LICENSE`, `.gitattributes`, `.gitignore`, `.dev-copilot` |

The repo tracks no `.lua`, no `.toc`, no `libs/`, no `tests/`, no `.luacheckrc` and no `.pkgmeta`. That is what this repo kind is, so none of those absences is filed.

## Section-by-section snapshot (documentation-§8 lists)

### Applies unchanged

| Section | State today |
|---|---|
| `line-endings` | `.gitattributes` is present. Its first 85 lines are byte-identical to the canonical non-client body in `line-endings-§5`, and nothing follows them (no appendix). The pin is `* text=auto eol=lf` at `:28`. Both shebang carve-outs are present (`*.sh` at `:38`, `*.py` at `:39`), and 20 lines are marked `binary`. Check (e) found **0** tracked files that disagree with the pin. All eight scripts are mode `100755` in the index. **Compliant.** |
| `versioning-git` | Semver `2.0.1` in `plugin.json`, the single source of truth (`CLAUDE.md:23`). No tags. The workflow is **feature branches merged `--no-ff`** (`CLAUDE.md:111`), not trunk-based. See DC-12. A stale `origin/main` (the 2026-06-20 initial commit) sits beside `origin/master`. See DC-13. |
| `documentation-§4` | No `TODO.md` anywhere. `CLAUDE.md:150-154` says "None tracked" and explains why spec text that mentions TODO is not a backlog. **Compliant.** |
| `documentation-§5` | Docs are mostly in sync, with drift found in four places: DEPENDENCIES inventory and citations (DC-08), the rotation and kind text left behind by the phase-2 close (DC-07), the bounded-runs contract (DC-06), and rotted worked examples (DC-09). |
| `documentation-§6` | 270 `filename-§N` occurrences across the tracked set. Every one resolves inside its section's range, except three in `commands/wow-revendor-standards.md:115-116,266`, which are **deliberate illustrations** of malformed and out-of-range forms. No retired global `§N.M` appears outside illustrative example blocks. **Compliant.** |
| `localization-§5` | 42 hits from the canonical `BRITISH`/`ALLOWED` lists across the tracked set: 37 in live specs and root docs, and 5 in dated design notes under `docs/superpowers/`. See DC-11. |
| `audit-review-history` | No `docs/audits/`, `docs/reviews/` or `docs/revendor/` store has been committed yet. No `docs/pending/LEDGER.md`. The GitHub issue store is **empty**: `gh issue list --state all` returned 0 issues, the eight `state:`/`severity:` labels are not created yet, and there are no `[status]` title prefixes. There is no deviation register to read (DC-01/DC-02). |
| `open-evolutions` | Record only. Nothing to file. |

### Applies, read for this kind

| Section | State today |
|---|---|
| `documentation-§3` → `docs/ARCHITECTURE.md` (five sections) | **Absent.** `docs/` holds only `superpowers/`. The closest content is `CLAUDE.md` § *Module/package map* (`:21-40`), which works as a file-and-path map. There is no Overview hub, no Known Limitations, no `## Documentation map` and no `## Documented deviations`. See DC-01, DC-02, DC-03. |
| `documentation-§7` → `DEPENDENCIES.md` | Present, in the honest shape §8 asks for: a short required list, an optional list, a development list, a "needed by whoever runs a command" list and a **Not used here** list with reasons. Most rows cite `file:line`. The inventory paragraph and three citations have drifted, and four version floors give no reason. See DC-08. |
| `layout` | Folder casing is lowercase throughout (`agents/ bin/ commands/ docs/ hooks/ profiles/ scripts/`). There is no authored `.lua`, so the 1500-line cap, the census and its gate have no instance. `scripts/` holds hooks, the runner, helpers and their tests. None of them is a generator, so `layout-§1`'s `tools/` rule does not reach them (§8 names this repo's `scripts/` explicitly). **Compliant.** |
| `naming-cheatsheet` | Python tests follow `test_<module>.py`, and the manifests use the conventional keys. The one gap is the absent `docs/ARCHITECTURE.md` engineer-context file (DC-01). |
| `anti-patterns` | Bound whole. No `docs/agent-context.md` (#49). The toolchain is documented (#50). No stored scaffolding pack. Entries keyed to addon artifacts have no instance. |
| `lint` / `testing` / `automated-tests` (if executable content appears) | No `.lua` is tracked, so the stated trigger has not fired. The repo does carry a Python harness: 3 test files with 17 + 15 + 20 = 52 cases, all green today. It also carries executable hooks. The re-read outcome is recorded in `DEPENDENCIES.md:88-95` ("not used here", "on no complexity gate") rather than in a hub. See DC-04. |

### Substitutes (MUST carry)

| Substitute | State |
|---|---|
| 1. Root `CLAUDE.md` with `## Standards compliance (read first)` or an equivalent *what this repo is* opening | Present: `## Purpose & stack` at `CLAUDE.md:3-19` is the equivalent opening and names the LF pin and its standard sections. **Compliant.** |
| 2. Root `DEPENDENCIES.md` in the honest shape | Present (DC-08 covers its drift). |
| 3. `docs/ARCHITECTURE.md` with the five sections | **Absent** (DC-01). |
| 4. Contributor- and agent-facing `README.md` | Present. It names what the repo is, the profiles, the commands, the hooks, migration and install. **Compliant.** |

### Does not apply (recorded so a reader does not read absence as a gap)

`toc-file`, `options-ui`, `slash-commands`, `preview-mode`, `launcher`, `savedvariables`, `standalone-windows`, `debug-logging`, `events-frames-taint`, `compat`, `public-api`, `packaging`, `architecture`, `library-stack`, `lint`, `testing`, `performance`, `automated-tests`, the player-README structure in `documentation-§1` with its five README and `CLAUDE.md` greps, the addon stub in `documentation-§2`, and the addon tier model and record docs in `documentation-§3`.

## Mechanical checks: what ran and what does not apply

| Check | Status |
|---|---|
| Line-ending (a)-(e) plus the §5 body diff | **Run.** All pass. (e) = 0. |
| Register read (`gh`, root `CLAUDE.md`, `docs/scope.md`, `LEDGER.md`) | **Run.** 0 issues. `CLAUDE.md` carries no accepted-deviation note. No `docs/scope.md`, no `LEDGER.md`. |
| `filename-§N` range check, retired-notation sweep, path and command-name resolution, intra-spec `Step N` resolution | **Run** (documentation lane). |
| Worked-example and inventory re-derivation | **Run** against the sibling repos `LootHistory` (`b9c1271`), `PrettyChat` (`8626790`), `MultiMeters`, `LibKa0s` (`v1.70.0`), `AbsorbTracker` and the other addons. |
| The repo's own suites (`python3 scripts/test_*.py`, `check_overlays.py`, manifest parse) | **Run.** 17/15/20 OK, `OK: 13 overlays`, manifests parse. |
| `luacheck`, the headless Lua runner, `lizard` and the sighted complexity suite | **Not applicable.** No `.lua` is tracked and there is no `tests/_kit/`. This is not "not run". |
| Vendored-library `diff -r` (both payloads), provenance line, re-vendor bundle census | **Not applicable.** No `libs/` and no `tests/_kit/`. The `Bundles [LibKa0s]` strings in `CLAUDE.md:137-138` and `README.md:59,62` are template text describing addons, not a provenance claim. |
| Packaging ignore list | **Not applicable.** No `.pkgmeta`, because `packaging` does not apply. |
| Disabled-state census | **Not applicable.** No Lua and no registrations. |

## Incidental observation made during the run

The plugin's own `PreToolUse(Bash)` hook **denied** an ordinary command during this audit: a tool-presence probe written `command -v lizard`. The run had to re-phrase it as `type lizard`. This is reproducible and is filed as DC-06.
