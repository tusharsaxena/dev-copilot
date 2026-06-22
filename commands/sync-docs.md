---
description: Deep-analyze the current state of the project and rewrite README.md, CLAUDE*/AGENTS*.md, ARCHITECTURE*.md, TODO.md, and (conservatively) CHANGELOG.md to match — eliminating documentation drift. Includes count-claim verification, command/script parity, config/env drift, dependency-vs-manifest drift, and dead-export detection.
allowed-tools: [Read, Glob, Grep, Bash, Edit, Write]
---

Deep-analyze the current state of the project in the cwd, then rewrite its documentation files so they accurately describe what the code does today. Language- and framework-agnostic.

## Step 0 — Doc layout decisions

Before doing anything else, decide whether the project needs ARCHITECTURE and CLAUDE/AGENTS docs, and — if it does — whether they should be a single file or a split layout.

Count the project's first-party source files (the languages' primary extensions under the source roots from Step 1, **excluding** vendored/generated dirs: `node_modules/`, `vendor/`, `dist/`, `build/`, `target/`, `.venv/`, `third_party/`, generated code, and lockfiles). The same count drives both decisions below.

### ARCHITECTURE.md decision

Check if `ARCHITECTURE.md` exists at the project root, and if `docs/ARCHITECTURE_*.md` files exist.

Apply this rule:
- **< 10 source files**: a single `ARCHITECTURE.md` at the root is appropriate. If absent, propose creating one with sections: Purpose, Module/package map, Entry points & boot, Data flow, Configuration, Public API surface, External dependencies, Conventions.
- **≥ 10 source files**: a top-level `ARCHITECTURE.md` index pointing to `docs/ARCHITECTURE_*.md` per topic is appropriate. If absent, propose the split layout.

If ARCHITECTURE docs already exist in some form (single root file, `docs/ARCHITECTURE_*.md` split, or any other variant), leave the structure alone — just sync content.

### CLAUDE.md / AGENTS.md decision

Check if `CLAUDE.md` or `AGENTS.md` exists at the project root, and if `CLAUDE/*.md` or `docs/CLAUDE_*.md` files exist. **Respect whichever convention the project already uses** — if it has `AGENTS.md`, sync that; if `CLAUDE.md`, sync that; if both, sync both. Do not introduce a second variant.

Apply this rule (to whichever file the project uses; default to `CLAUDE.md` if neither exists and you propose creating one):
- **< 10 source files**: a single root file is appropriate. If absent, propose creating one with sections: Purpose & stack, Project-internal conventions, Module/package map, Entry points & lifecycle, Configuration & env, Build/test/run commands, Hot zones / footguns, Known TODOs. Keep it concise — this file loads into every future session's context.
- **≥ 10 source files**: a top-level concise index (pointers only) plus `docs/CLAUDE_*.md` per topic (e.g. `CLAUDE_CONVENTIONS.md`, `CLAUDE_MODULES.md`, `CLAUDE_LIFECYCLE.md`, `CLAUDE_CONFIG.md`, `CLAUDE_HOT_ZONES.md`) is appropriate. If absent, propose the split layout.

If these docs already exist in some form, leave the structure alone — just sync content.

### Confirmation

If you propose creating either layout (ARCHITECTURE or CLAUDE/AGENTS), ask the user to confirm before scaffolding.

## Step 1 — Discover the project

1. **Detect project type** from manifest/build files in the root (and workspaces): `package.json`, `pyproject.toml`/`setup.py`/`requirements.txt`, `go.mod`, `Cargo.toml`, `pom.xml`/`build.gradle(.kts)`, `Gemfile`, `composer.json`, `*.csproj`/`*.sln`, `mix.exs`, etc. Read every one. Extract: project name, version, declared dependencies, declared scripts/tasks, entry points (`main`/`bin`/`module`), and workspace/monorepo layout.
2. **Map the source layout**: identify source roots (`src/`, `lib/`, `app/`, `cmd/`, `pkg/`, `internal/`, language-default layouts). List the first-party source files. Identify the core entry point(s), modules/packages, CLI/command surface, configuration loading, and public API surface (exported symbols).
3. **Read the first-party source** (skip vendored/generated dirs). Identify:
   - The init/bootstrap pattern (main function, framework entry, server setup, CLI dispatcher).
   - All user-facing commands / CLI subcommands / scripts (and how they're dispatched — argument parser tables, route maps, a command registry).
   - All public APIs the project exposes (exported functions/classes/types/endpoints, published package surface).
   - All configuration inputs: config files, environment variables, flags, and their defaults.
   - All persistent state / storage schemas the project defines (DB schema, on-disk format, saved settings) and their shape.
   - Any `TODO`/`FIXME`/`HACK`/`XXX` comments and their locations.
4. **Detect build/test/run commands** from the manifest (npm scripts, Makefile targets, `cargo`/`go`/`pytest` conventions, CI config) — these belong in the docs.

## Step 2 — Discover the docs

Find every documentation file: `README.md`, `README.*`, `CLAUDE.md`, `CLAUDE.*.md`, `CLAUDE/*.md`, `AGENTS.md`, `ARCHITECTURE.md`, `ARCHITECTURE.*.md`, `docs/*.md`, `CHANGELOG.md`, `TODO.md`. List them. **Always include `TODO.md` in the sync set** — if it exists, treat it as a first-class doc to reconcile; if it doesn't exist but the code carries `TODO`/`FIXME`/`HACK`/`XXX` markers (from Step 1.3), flag that one could be created (don't scaffold without asking).

For each, read the current contents and build a drift inventory across these axes:

**Stale facts** — claims in docs that contradict code:
- Numeric counts in prose or headings ("8 commands", "tracks 12 metrics", "5 modules") vs. the actual count from Step 1. Flag any mismatch.
- Wrong command/script names, wrong file paths, wrong config keys, wrong env-var names, wrong default values.
- Wrong/missing dependencies, removed-but-still-listed modules.
- Outdated version number anywhere docs mention it (vs. the manifest version).

**Command / script parity (manifest & CLI ↔ README)**
- Every script/task declared in the manifest (`package.json` scripts, Makefile targets, etc.) that's intended for users should appear in the README's usage docs.
- Every CLI subcommand the code dispatches should be documented; every command the README documents should exist in the code.
- Flag both directions.

**Configuration / environment drift**
- Every config key or environment variable the code reads should be discoverable in the docs (if the project documents configuration at all).
- Every config/env key the docs cite should still be read somewhere in the code. Flag orphans.

**Dependency drift**
- Dependencies the docs claim are required → verify they're in the manifest.
- Major dependencies in the manifest that the docs' stack/requirements section omits → flag if user-relevant.

**Public API parity**
- Every public/exported symbol docs claim exists → verify it's still there.
- Every prominent public/exported symbol docs DON'T mention → flag if it looks like an intended public API (not a private/underscore/internal name).

**Orphaned references**
- Links in docs to deleted files (`docs/foo.md` that no longer exists).
- Mentions of removed functions, modules, commands, or flags.

**Missing coverage**
- Code features with no doc footprint (a new module not in any module list, a new command not documented).

**Dead exports** (separate finding)
- Exported/public symbols with **zero callers** anywhere in the first-party source. Use `grep -r` (exclude vendored/generated dirs) to verify before flagging. List as candidates for deletion — don't auto-delete. Skip symbols that are a published package's API surface, called via reflection, or string-keyed dispatch (note the uncertainty).

## Step 3 — Show drift before writing

Print the drift inventory to the user as a structured summary, grouped by doc file. One line per item. Example:

```
DRIFT INVENTORY

README.md
  STALE: "8 commands" — actual count is 10 (registry in src/cli/commands.ts:42)
  STALE: documents `npm run build:prod` — script not in package.json
  ORPHAN: links to docs/old-design.md (file deleted in 73a2f1c)
  MISSING: `sync` subcommand documented nowhere

CLAUDE.md
  STALE: claims config lives in config.js — moved to src/config/index.ts

ARCHITECTURE.md
  MISSING: queue worker added in v1.4, not in the module map

DEAD EXPORTS (candidates for deletion, not auto-removed)
  src/util/color.ts:88    parseColor    (zero callers)
  src/util/list.ts:103    printList     (zero callers)
```

If the drift list is large (>10 items) or any item is ambiguous, ask for confirmation before applying. For small/obvious drift, proceed.

## Step 4 — Rewrite

For each doc file:
- **README.md**: keep its overall shape. Update each section to reflect current state. Don't invent sections that weren't there. Preserve the user's voice — match the existing tone, formatting, and emoji usage (or absence).
- **CLAUDE.md / AGENTS.md** (and split variants): project context for future AI sessions. Update against your Step 1 map. Keep it concise (it's loaded into every session's context).
- **ARCHITECTURE.md** (and variants): structural/design documentation. Update component descriptions, dataflow, dependency relationships, lifecycle.
- **TODO.md**: reconcile against the actual `TODO`/`FIXME`/`HACK`/`XXX` markers found in Step 1.3 and the current feature state. Tick off / remove items that are clearly done in the code, and add entries for in-code markers that aren't tracked yet (cite their `file:line`). Preserve the existing structure, grouping, and any manually-authored items you can't verify either way — don't delete an item just because you can't find a matching marker. Match the file's existing format (checklist, headings, sections).
- **CHANGELOG.md** (conservative): only reconcile entries against what the code/manifest already states. You may fix wrong dates, broken links, or a misdescribed existing entry, and you may flag that the `Unreleased` section appears out of date relative to recent changes. **Never invent a version number, never bump the version, never fabricate release entries.** If substantial unreleased work is undocumented, surface it for the user rather than writing speculative entries.

Use `Edit` for surgical updates. Only `Write` (full rewrite) if the file is completely out of date or the diff would be larger than the rewrite.

**Preserve line endings.** Detect each file's existing line endings (LF or CRLF) and write the same, to keep diffs clean.

## Step 5 — Report

Print a summary:
- Files updated (with line-count delta per file)
- Files unchanged (already accurate)
- **Dead exports flagged** (separate section — these are NOT auto-removed; the user decides)
- Anything you couldn't reconcile (e.g. ambiguous intent, missing context) — flag for the user
- A reminder to review the diffs before committing

## Hard rules

- **Don't invent features.** If a doc claims a feature you can't find in code, ASK before deleting — it might be intentional/aspirational.
- **Don't add documentation for things the user didn't document.** If there's no "Configuration" section currently, don't add one.
- **Don't bump the version.** Even if you find version drift, do NOT change the version in any manifest, code constant, README badge, or CHANGELOG. Changing the version is out of scope for this command.
- **Don't auto-delete dead exports.** Surface them; the user decides.
- **Don't touch LICENSE, or any file that isn't a project doc.**
- **Don't commit.**
