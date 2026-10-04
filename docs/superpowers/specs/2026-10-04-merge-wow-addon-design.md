# Merge wow-addon into dev-copilot — design

Date: 2026-10-04 · Status: approved in conversation (three sections), executing

## Intent

The user maintains two Claude Code plugins: `dev-copilot` (4 generic commands) and `wow-addon`
(22 WoW-addon commands, 2 agents, 2 hooks, v2.5.0). dev-copilot started as a de-WoW'd copy and has
already drifted (e.g. no `push` flag on `commit`). The user wants **one plugin, one source of
truth**, with every command aware of the repo it runs in: full current `/wow-addon` behavior in a
WoW repo, generic behavior everywhere else.

Success criteria:

1. One plugin (`dev-copilot` v2.0.0) carries every capability both plugins have today.
2. No WoW behavior is lost: in a WoW repo each command does what its `/wow-addon:` predecessor did.
3. Generic runs never load WoW-specific instructions.
4. Each piece of shared logic lives in exactly one file.
5. WoW-only commands decline cleanly outside a WoW repo.

## Decisions

| # | Decision | Choice |
|---|---|---|
| D1 | Fate of `wow-addon` | Retired. All commands become `/dev-copilot:*`; the repo is archived in phase 2. |
| D2 | Naming of WoW-only commands | `wow-` prefix (`/dev-copilot:wow-new-addon`). Shared commands keep plain names. |
| D3 | Structure | Generic core per command + WoW overlay under `profiles/wow/`, loaded only when detected. |
| D4 | History | wow-addon history merged into dev-copilot (`--allow-unrelated-histories`), then restructured. |
| D5 | Phasing | Phase 1 (this spec) builds the plugin. Phase 2 (separate plan) ripples the rename through WowAddonStandards → LibKa0s kit → addons, then archives wow-addon. |

## Layout

```
.claude-plugin/{plugin.json, marketplace.json}   v2.0.0; plugin.json is the version's only home
bin/dev-copilot-profile          on PATH; execs scripts/detect_profile.py
bin/ka0s-bounded                 unchanged
scripts/detect_profile.py        the detector
scripts/test_detect_profile.py   its unit test
scripts/check_overlays.py        overlay ↔ base consistency check
scripts/bounded*.{sh,py}, ka0s-bounded, normalize-eol.sh, test_bounded_runs.py   carried over
hooks/hooks.json                 both existing hooks, unchanged registration
commands/<shared>.md             generic core
commands/wow-<name>.md           WoW-only commands
agents/review.md                 generic core
agents/wow-standards-audit.md    WoW-only agent
profiles/wow/<shared>.md         WoW overlay for a shared command
profiles/wow/agent-review.md     WoW overlay for the review agent
```

## Detection

`dev-copilot-profile [path]` (default: cwd) prints `key=value` lines:

```
profile=wow|generic
kind=addon|library|standards|tooling|generic
repo=<absolute repo root, or the path if not a git repo>
name=<repo directory name>
root=<absolute plugin root>
reason=<which rule matched>
```

Rules, first match wins (evaluated at the git top-level, or the path itself outside git):

0. **Override** — a `.dev-copilot` file at the repo root with a `profile=wow|generic` line (and
   optional `kind=`) wins outright.
1. **standards** — repo dir name or `origin` URL basename is `WowAddonStandards`.
2. **tooling** — dir name or `origin` basename is `wow-addon` (the retired plugin repo, still in
   the audit rotation until phase 2).
3. **library** — dir name or `origin` basename is `LibKa0s`, or the root holds `LibKa0s.toc`.
4. **addon** — any `*.toc` at the root contains a line starting `## Interface:`.
5. **generic** — otherwise.

`profile=wow` for kinds 1–4. `root` is derived from the script's own real path, so it works without
`${CLAUDE_PLUGIN_ROOT}` substitution. Exit code is always 0 for a successful detection.

## Overlay contract

Every shared command/agent begins with the same **Step 0**:

> Run `dev-copilot-profile` (Bash). If the command is not found, run
> `"${CLAUDE_PLUGIN_ROOT}/bin/dev-copilot-profile"`. If `profile=wow`, Read
> `<root>/profiles/wow/<overlay>.md` now and apply it. If `profile=generic`, follow this spec as
> written and do not read the overlay. In multi-repo flows, run detection per repo.

Base specs mark hook points with an HTML comment on its own line directly above the section it
governs: `<!-- overlay: <id> -->`. Overlay files consist of a short preamble then sections headed
`## <id> — adds` or `## <id> — replaces`. An overlay may also have `## extra — adds` for WoW-only
steps with no generic counterpart (it states where in the flow they run). Overlays carry only WoW
deltas, never a copy of generic text.

`scripts/check_overlays.py` fails when an overlay has no base, references a hook id the base does
not declare, or a base references an overlay file that does not exist.

WoW-only commands run Step 0 too; on `profile=generic` they print one line ("`/dev-copilot:wow-…`
is for WoW addon repos; this repo is detected as generic — add `.dev-copilot` with `profile=wow` to
override") and stop. Where a WoW-only command accepts `kind`-specific behavior (standards-audit,
harvest-standards), it uses the detector's `kind` rather than re-deriving it.

## Command mapping

Shared (generic core; overlay where noted):

| Command | Generic core | WoW overlay |
|---|---|---|
| `diff` | dev-copilot version | events, TOC deps, `## Interface`, Lua examples |
| `commit` | wow-addon version, generalized; gains the `push` flag with leading-token parsing | Lua/TOC untracked patterns |
| `sync-docs` | dev-copilot doc set + comment-citation check + `DEPENDENCIES.md` drift when present | Ka0s root-doc rules, docs/ trio, slash/COMMANDS parity, no library inventory, retired `docs/complexity.md`, LibKa0s provenance, scaffolding |
| `review` + agent | dev-copilot agent + "measure first" step (detected lint/tests) → `reviews/<date>/` | full Step 0 suites, WoW checks, standard guardrail, `docs/reviews/<date>/`, `03_SMOKE_TESTS.md` |
| `run-tests` | auto-detect lint/tests across ecosystems | luacheck, `tests/run.lua`, Makefile, via `ka0s-bounded` |
| `bump-version` | manifests/constants/badges + CHANGELOG roll, gated on tests | TOC, README Version History, four-suite release gate, automated-test bundle |
| `finalize` | sync-docs → commit → merge → push → delete branch; evidence-based scope | collection dependency order, vendored-folder evidence |
| `execution-status` | unchanged | none |
| `issue-add/-audit/-triage/-details/-fetch-all/-summary` | label workflow on any GitHub repo; default scope `here`; `all` = repos named or sibling checkouts | default scope = Ka0s collection from `ADDONS.md`; audit/review bundle sweep |

WoW-only (content moved, renamed, refusal + `/dev-copilot:` references only):
`wow-new-addon`, `wow-bump-interface`, `wow-automated-tests`, `wow-perf-analysis`,
`wow-revendor-libka0s`, `wow-revendor-standards`, `wow-harvest-standards`, `wow-standards-audit`
(+ agent `wow-standards-audit`).

Total: 22 commands (14 shared, 8 WoW-only), 2 agents, 2 hooks.

## In-plugin renames

- `/wow-addon:<x>` → `/dev-copilot:<x>` or `/dev-copilot:wow-<x>` per the mapping, everywhere in
  specs, overlays, scripts and docs. Agent `wow-addon:review` → `dev-copilot:review`;
  `wow-addon:standards-audit` → `dev-copilot:wow-standards-audit`.
- State: `~/.claude/wow-addon/` → `~/.claude/dev-copilot/` (bin symlink, issue-triage journal).
  The bounded-runs hook maintains the new symlink **and** keeps the legacy
  `~/.claude/wow-addon/bin/ka0s-bounded` symlink until phase 2, because addon docs and the vendored
  kit name that path. issue-triage reads the legacy journal dir when the new one has no match.
- References to the standard's audit rotation naming the `wow-addon` repo are **not** changed in
  phase 1 (that is upstream text the plugin fetches).

## Out of scope (phase 2)

Editing WowAddonStandards playbooks/rotation, LibKa0s kit text, any addon repo, and archiving the
wow-addon repo. Frozen dated bundles anywhere are never edited.

## Testing

- `python3 scripts/test_detect_profile.py` — fixtures for each kind, override, non-git dir.
- `python3 scripts/test_bounded_runs.py` — must still pass after path changes.
- `python3 scripts/check_overlays.py` — passes.
- Real detection against AbsorbTracker (addon), LibKa0s (library), WowAddonStandards (standards),
  wow-addon (tooling), dev-copilot and steamdb (generic).
- Manifest JSON parses; command/agent counts match README and manifests.
- A grep for `wow-addon:` / `/wow-addon` in live plugin files returns only intentional legacy
  mentions (README migration note, legacy symlink, CLAUDE.md history).
- Manual: `/reload-plugins` reports the new counts.

## Conventions carried over

LF repo (`.gitattributes` from wow-addon). Adding/removing a command is a five-touch change: the
file, its overlay (if shared), the README table, both manifest descriptions, the version.
