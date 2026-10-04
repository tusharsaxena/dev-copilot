---
description: Deep-analyze the current state of the project and rewrite README.md, CLAUDE*/AGENTS*.md, ARCHITECTURE*.md, DEPENDENCIES.md (when present), TODO.md, and (conservatively) CHANGELOG.md to match — eliminating documentation drift. Includes count-claim verification, command/script parity, config/env drift, dependency-vs-manifest drift, dead-export detection, and a comment-citation check over the project's own source (a comment naming a path that does not exist, a line past the end of a file, or a symbol with no definition — reported with file:line and corrected only on confirmation, comment-only).
allowed-tools: [Read, Glob, Grep, Bash, Edit, Write]
---

Deep-analyze the current state of the project in the cwd, then rewrite its documentation files so they accurately describe what the code does today. Language- and framework-agnostic.

## Step 0 — Detect the repo profile

Run `dev-copilot-profile` (Bash; if not found, `"${CLAUDE_PLUGIN_ROOT}/bin/dev-copilot-profile"`). It prints `profile=`, `kind=`, `repo=`, `name=`, `root=`, `reason=`.

- **`profile=wow`** — Read `<root>/profiles/wow/sync-docs.md` now. Each of its sections names a hook point in this spec (`<!-- overlay: <id> -->`) and says whether it **adds to** or **replaces** that section; `extra` sections say where they run. Apply them as you go. `kind` (`addon`, `library`, `standards`, `tooling`) refines WoW behavior where the overlay says so.
- **`profile=generic`** — follow this spec as written. Do not read the overlay.
- **Neither invocation works** (no detector on PATH, and no plugin root substituted) — treat the repo as `profile=generic`, say so in one line, and do not read any overlay.

## Step 1 — Doc layout decisions

<!-- overlay: layout-rule -->
Before doing anything else, decide whether the project needs ARCHITECTURE and CLAUDE/AGENTS docs, and — if it does — whether they should be a single file or a split layout.

Count the project's first-party source files (the languages' primary extensions under the source roots from Step 2 — and, in a repo whose product is prose the tool loads, such as command, prompt or agent specs, those spec files too; they are what the module map describes — **excluding** vendored/generated dirs: `node_modules/`, `vendor/`, `dist/`, `build/`, `target/`, `.venv/`, `third_party/`, generated code, and lockfiles). The same count drives both decisions below.

<!-- overlay: architecture-decision -->
### ARCHITECTURE.md decision

Check if `ARCHITECTURE.md` exists at the project root, and if `docs/ARCHITECTURE_*.md` files exist.

Apply this rule:
- **< 10 source files**: a single `ARCHITECTURE.md` at the root is appropriate. If absent, propose creating one with sections: Purpose, Module/package map, Entry points & boot, Data flow, Configuration, Public API surface, External dependencies, Conventions.
- **≥ 10 source files**: a top-level `ARCHITECTURE.md` index pointing to `docs/ARCHITECTURE_*.md` per topic is appropriate. If absent, propose the split layout.

If ARCHITECTURE docs already exist in some form (single root file, `docs/ARCHITECTURE_*.md` split, or any other variant), leave the structure alone — just sync content.

<!-- overlay: claude-decision -->
### CLAUDE.md / AGENTS.md decision

Check if `CLAUDE.md` or `AGENTS.md` exists at the project root, and if `CLAUDE/*.md` or `docs/CLAUDE_*.md` files exist. **Respect whichever convention the project already uses** — if it has `AGENTS.md`, sync that; if `CLAUDE.md`, sync that; if both, sync both. Do not introduce a second variant.

Apply this rule (to whichever file the project uses; default to `CLAUDE.md` if neither exists and you propose creating one):
- **< 10 source files**: a single root file is appropriate. If absent, propose creating one with sections: Purpose & stack, Project-internal conventions, Module/package map, Entry points & lifecycle, Configuration & env, Build/test/run commands, Hot zones / footguns, Known TODOs. Keep it concise — this file loads into every future session's context.
- **≥ 10 source files**: a top-level concise index (pointers only) plus `docs/CLAUDE_*.md` per topic (e.g. `CLAUDE_CONVENTIONS.md`, `CLAUDE_MODULES.md`, `CLAUDE_LIFECYCLE.md`, `CLAUDE_CONFIG.md`, `CLAUDE_HOT_ZONES.md`) is appropriate. If absent, propose the split layout.

If these docs already exist in some form, leave the structure alone — just sync content.

<!-- overlay: dependencies-decision -->
### `DEPENDENCIES.md` decision

Some projects keep a root `DEPENDENCIES.md` (or an equivalent toolchain doc — `INSTALL.md`, a "Prerequisites" / "Development setup" section) listing the software needed to build, run, test or release the project. **If the project has one, it is in the sync set**; if it does not, do not propose one — that is the project's choice, not drift.

When it exists, every entry in it **must** be **evidence-based** — a `file:line`, a script's `import`, a manifest entry, a documented command, a CI step — and a speculative entry is worse than an omission, because a reader who installs three unnecessary things stops trusting the list and then misses the one that mattered. Sync it against the evidence: a tool added since it was written, or a tool no longer used, is drift like any other. Report each change with what proved it. Name each tool's **own** package manager and install command, not the one you reached for last, and check that each install command still works on the platform the file targets (e.g. `pip install <tool>` fails on a PEP 668 `EXTERNALLY-MANAGED` Python; `pipx` is the instruction that works there). If the file has a section with genuinely nothing in it, it says so plainly — "None" is a **result**; a missing section reads as an omission.

### Confirmation

If you propose creating either layout (ARCHITECTURE or CLAUDE/AGENTS), ask the user to confirm before scaffolding.

<!-- overlay: discover-project -->
## Step 2 — Discover the project

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
5. **Detect the toolchain** the project actually needs — interpreters and their versions, linters, test runners, anything the tests or a script shell out to or import, release/asset tooling — with the `file:line` that proves each. This is the evidence the `DEPENDENCIES.md` sync (Step 1) and the dependency drift axis (Step 3) are checked against.

## Step 3 — Discover the docs

<!-- overlay: doc-discovery -->
Find every documentation file: `README.md`, `README.*`, `CLAUDE.md`, `CLAUDE.*.md`, `CLAUDE/*.md`, `AGENTS.md`, `ARCHITECTURE.md`, `ARCHITECTURE.*.md`, `DEPENDENCIES.md`, `docs/**/*.md` (nested too), `CHANGELOG.md`, `TODO.md`. List them, then set aside the frozen dated records described below: they are read, never synced. **Always include `TODO.md` in the sync set** — if it exists, treat it as a first-class doc to reconcile; if it doesn't exist but the code carries `TODO`/`FIXME`/`HACK`/`XXX` markers (from Step 2.3), flag that one could be created (don't scaffold without asking).

**Generated docs are not synced by hand.** A doc a tool produces (an API reference, a generated inventory, a coverage or benchmark record) is refreshed by regenerating it, never by editing its numbers. Read it — a count claim elsewhere in the docs must agree with it — but if it is stale, that is a **finding** to report, not something to fix here. Frozen dated records (review or audit bundles under a dated directory, and dated design specs or plans such as `docs/<…>/specs/<YYYY-MM-DD>-*.md`, even one carrying a live status ledger: its owner updates it, not this command) are evidence of their date and are never edited.

For each, read the current contents and build a drift inventory across these axes:

<!-- overlay: stale-facts -->
**Stale facts** — claims in docs that contradict code:
- Numeric counts in prose or headings ("8 commands", "tracks 12 metrics", "5 modules") vs. the actual count from Step 2. Flag any mismatch.
- Wrong command/script names, wrong file paths, wrong config keys, wrong env-var names, wrong default values.
- Wrong/missing dependencies, removed-but-still-listed modules.
- **`DEPENDENCIES.md` (when present) vs. what the repo actually needs** — a tool the tests or a script now require but the file does not name; a tool named there that nothing in the repo uses any more; an install command that never worked or no longer does; a stated interpreter/runtime version that disagrees with what the code or its tooling requires. Cite the evidence for each direction.
- Outdated version number anywhere docs mention it (vs. the manifest version).

<!-- overlay: command-parity -->
**Command / script parity (manifest & CLI ↔ README)**
- Every script/task declared in the manifest (`package.json` scripts, Makefile targets, etc.) that's intended for users should appear in the README's usage docs.
- Every CLI subcommand the code dispatches should be documented; every command the README documents should exist in the code.
- Flag both directions.

<!-- overlay: config-drift -->
**Configuration / environment drift**
- Every config key or environment variable the code reads should be discoverable in the docs (if the project documents configuration at all).
- Every config/env key the docs cite should still be read somewhere in the code. Flag orphans.

<!-- overlay: dependency-drift -->
**Dependency drift**
- Dependencies the docs claim are required → verify they're in the manifest.
- Major dependencies in the manifest that the docs' stack/requirements section omits → flag if user-relevant.

<!-- overlay: api-parity -->
**Public API parity**
- Every public/exported symbol docs claim exists → verify it's still there.
- Every prominent public/exported symbol docs DON'T mention → flag if it looks like an intended public API (not a private/underscore/internal name).

**Orphaned references**
- Links in docs to deleted files (`docs/foo.md` that no longer exists).
- Mentions of removed functions, modules, commands, or flags.

**Missing coverage**
- Code features with no doc footprint (a new module not in any module list, a new command not documented).

<!-- overlay: dead-exports -->
**Dead exports** (separate finding, often surfaces while building the API parity check)
- Exported/public symbols with **zero callers** anywhere in the first-party source. Use `grep -r` (exclude vendored/generated dirs) to verify before flagging. List as candidates for deletion — don't auto-delete. Skip symbols that are a published package's API surface, called via reflection, or string-keyed dispatch (note the uncertainty).

### Comment-citation check

A comment that names a file, a line or a symbol is documentation, and it drifts exactly like a README does — except that nothing reads it but the next person to touch that function, and no gate can see it. A linter does not read prose, no test covers a comment, and a header block naming `src/util/log.ts` in a repo whose `src/util/` never held that file survives every green build indefinitely. The same class shows up as a comment naming a caller that does not call, a member that no longer exists, or a `file:line` that resolves to something unrelated. Treat it as a drift axis of its own.

<!-- overlay: citation-scope -->
**Scope.** The project's *own* source and config — the first-party files from Step 2, plus build/CI/lint config. **Exclude vendored and generated dirs** (`node_modules/`, `vendor/`, `third_party/`, `dist/`, `build/`, `target/`, `.venv/`, generated code, and any directory the project copies verbatim from an upstream) — a comment inside a vendored payload is upstream's to fix. Read only **comment** text, in each language's comment syntax (`//`, `/* … */`, `#`, `--`, `<!-- … -->`, docstrings). A path or a name inside a string literal, a key or a value is not a citation and is not in scope.

<!-- overlay: citation-tokens -->
**Extract three kinds of token, and resolve each:**

- **Path-like tokens** — anything shaped `some/dir/file.ext`, `file.ext`, `docs/setup.md`, with an optional `:N` or `:N-M` suffix. Resolve the path relative to the repo root first, then relative to the commenting file's own directory. Report it when **no such file exists**. When the path resolves and carries a line suffix, check the suffix too: report a `:N` (or a range whose end) that is **past the end of the file**. A line number that resolves but now points at unrelated code is *not* mechanically detectable — see the limits below.
- **`Symbol.Member` references** — dotted, colon- or `::`-qualified names such as `Logger.addLine`, `Core::apply_skin`, `config.Loader.read`. Report one that has **no definition and no call site**: `grep -rn` the member name across the project's own source (same exclusions) and find zero definition and zero call. Resolve against vendored dirs as well when the root is a vendored module — a comment may legitimately name a library member the project only calls indirectly, and a hit anywhere in the loaded tree clears it.
- **Version citations** — a comment naming a version the tree itself records somewhere authoritative: a migration step (`v6->v9`, "bumps the schema to 2") checked against the migration table's highest target, or a vendored dependency's version checked against the manifest/lockfile or provenance line that records it. Report a version that authority does not carry. A version with no such authority in the tree is prose, and stays unreported.

<!-- overlay: citation-false-positives -->
**Keep the false-positive rate near zero, because a noisy check gets ignored and then the real hit rides through with it.** Do not report:

- A root that is a language builtin, a standard-library module, or a platform/runtime API — the project does not define it and is not expected to.
- Prose that merely contains a dot: sentence-ending words, `e.g.`, ellipses, a decimal number, a URL's host, and a version string with **no authority in the tree**. Require a path token to end in a known source/doc extension, and a symbol token to be at least two identifier segments with the final segment either starting upper-case or matching a name Step 2 actually found in the project.
- A member reached only through a vendored library's own dispatch, when a grep of the loaded tree finds it.
- A path in **the repo a tool operates on**, not this one: a script or spec that runs `tests/run.lua` or reads `CLAUDE.md` in whatever repo it is pointed at names a path relative to that target. When the surrounding code treats the path as a runtime argument, a target-repo path or a `cd`-relative command, it is not a citation of this repo.

<!-- overlay: citation-limits -->
**What this check cannot see, stated plainly so nobody assumes it is covered:** a comment that is *countably* wrong — "all four exits of `poll()`" over a function with two — parses as prose, names nothing that fails to resolve, and is out of this check's reach. So is a self-referential explanation, a stale rationale whose code still exists, and a duplicated paragraph. Those stay a reviewer's job. This check closes the mechanical half: **a named path that is not there, a named line past the end of its file, a named symbol with no definition, and a named version the tree does not record.**

<!-- overlay: citation-boundary -->
**The edit boundary.** Widening what this command *reads* does not widen what it may *write*. Every comment-citation hit is **reported with `file:line`** in the Step 4 inventory and applied **only on the user's explicit confirmation**; silence is a decline, not a default. When they confirm, the edit is **comment-only** — the text of a comment or a commented header line, and nothing else. If correcting the citation would require touching a line that runs, do not edit it: report it and say why. And **never guess a target** — a comment naming a file that does not exist may mean the file was renamed, was deleted, or was never right; the user names the replacement, or the item stays flagged. Deleting a comment outright is a correction like any other, and needs the same confirmation.

## Step 4 — Show drift before writing

Print the drift inventory to the user as a structured summary, grouped by doc file. One line per item. Example:

<!-- overlay: drift-example -->
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

DEPENDENCIES.md
  STALE: names `black` — nothing in the repo runs it since ruff replaced it (pyproject.toml:41)

DEAD EXPORTS (candidates for deletion, not auto-removed)
  src/util/color.ts:88    parseColor    (zero callers)
  src/util/list.ts:103    printList     (zero callers)

COMMENT CITATIONS — comment-only, needs your confirmation before anything is written
  src/server/app.ts:5     NO SUCH PATH: "src/util/log.ts" — src/util/ holds logger.ts
  src/cli/run.ts:111      NO DEFINITION: comment names Config.loadAll; no definition or call
  src/util/fmt.ts:40      LINE PAST EOF: "docs/setup.md:210" — the file has 96 lines
  src/db/migrate.ts:195   NO SUCH VERSION: comment describes the "v6->v9" migration;
                          the MIGRATIONS table at :19 stops at version 8
```

If the drift list is large (>10 items) or any item is ambiguous, ask for confirmation before applying. For small/obvious drift, proceed. **The `COMMENT CITATIONS` block is exempt from "small/obvious proceeds"** — every item in it is confirmed before anything is written, however mechanical it looks, and each correction's replacement text is named by the user, not guessed.

## Step 5 — Rewrite

For each doc file:
<!-- overlay: readme-rewrite -->
- **README.md**: keep its overall shape. Update each section to reflect current state. Don't invent sections that weren't there. Preserve the user's voice — match the existing tone, formatting, and emoji usage (or absence).

<!-- overlay: claude-rewrite -->
- **CLAUDE.md / AGENTS.md** (and split variants): project context for future AI sessions. Update against your Step 2 map. Keep it concise (it's loaded into every session's context).

- **ARCHITECTURE.md** (and variants): structural/design documentation. Update component descriptions, dataflow, dependency relationships, lifecycle.

<!-- overlay: dependencies-rewrite -->
- **DEPENDENCIES.md** (only if it exists): the toolchain contract. Update entries against the evidence from Step 2, keeping the file's existing structure and each entry's install command and verification line where it has them. Never add an entry you cannot point at a file for.

<!-- overlay: todo-changelog -->
- **TODO.md**: reconcile against the actual `TODO`/`FIXME`/`HACK`/`XXX` markers found in Step 2.3 and the current feature state. Tick off / remove items that are clearly done in the code, and add entries for in-code markers that aren't tracked yet (cite their `file:line`). Preserve the existing structure, grouping, and any manually-authored items you can't verify either way — don't delete an item just because you can't find a matching marker. Match the file's existing format (checklist, headings, sections).
- **CHANGELOG.md** (conservative): only reconcile entries against what the code/manifest already states. You may fix wrong dates, broken links, or a misdescribed existing entry, and you may flag that the `Unreleased` section appears out of date relative to recent changes. **Never invent a version number, never bump the version, never fabricate release entries.** If substantial unreleased work is undocumented, surface it for the user rather than writing speculative entries.

Then, and only after the user has confirmed the `COMMENT CITATIONS` block item by item, apply the confirmed **comment-only** corrections in the source files those items name. Nothing in that block applies without an answer, nothing outside a comment is touched, and an item whose replacement text the user did not name stays flagged and unedited.

Use `Edit` for surgical updates. Only `Write` (full rewrite) if the file is completely out of date or the diff would be larger than the rewrite.

<!-- overlay: line-endings -->
**Write the declared line ending, not merely the observed one.** Ask git what the repo declares for the file — `git check-attr text eol -- <path>` — and write that. A file whose endings disagree with the declaration is a **straggler**, and mirroring it faithfully propagates the defect. Where nothing is declared, detect the file's existing line endings (LF or CRLF) and preserve them, to keep diffs clean.

## Step 6 — Report

<!-- overlay: report -->
Print a summary:
- Files updated (with line-count delta per file)
- Files unchanged (already accurate)
- **Dead exports flagged** (separate section — these are NOT auto-removed; the user decides)
- **Comment citations**, split into applied-after-confirmation and declined-or-unresolved, and the fact that each applied one was comment-only
- Anything you couldn't reconcile (e.g. ambiguous intent, missing context) — flag for the user
- A reminder to review the diffs before committing

## Hard rules

<!-- overlay: hard-rules -->
- **Don't invent features.** If a doc claims a feature you can't find in code, ASK before deleting — it might be intentional/aspirational.
- **Don't add documentation for things the user didn't document.** If there's no "Configuration" section currently, don't add one.
- **Don't bump the version.** Even if you find version drift, do NOT change the version in any manifest, code constant, README badge, or CHANGELOG. Changing the version is `/dev-copilot:bump-version`'s job.
- **Don't auto-delete dead exports.** Surface them; the user decides.
- **Documentation only, with exactly one named exception: a confirmed comment-only comment-citation correction.** This command rewrites docs; it does not otherwise edit source, config or build files. The one exception is the Step 3 comment-citation check, and it is fenced on all four sides — **this check only** (never any other drift the command notices in code), **comments only** (a string literal, a key or a value is reported, never edited), **explicit confirmation every time** (an unanswered prompt is a decline), and **never a guessed target** (the user names the replacement or the item stays flagged). This exception cannot reach a line that runs.
- **Never edit vendored payloads.** A directory copied verbatim from an upstream stays byte-identical to it — a defect in there is fixed upstream and re-vendored, never patched in place.
- **Don't hand-edit a generated doc.** Report staleness; regenerate or leave it.
- **Don't invent a dependency.** Every `DEPENDENCIES.md` entry traces to something in this repo. If you suspect a requirement but cannot evidence it, say so in words or leave it out.
- **Don't commit.**

<!-- overlay: out-of-scope -->
**Files out of scope:** don't touch `LICENSE`, or any file that isn't a project doc (apart from the confirmed comment-only corrections above).
