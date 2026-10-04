---
description: Bump the project version to X.Y.Z everywhere it appears — package manifests, code constants, README badges, CLAUDE*/AGENTS*.md, the project's own entry in lockfiles — and roll the git history since the last tag into CHANGELOG.md (matching its existing style, Keep a Changelog by default). Gated: runs the repo's full lint/test battery FIRST and refuses to bump anything unless it passes. Asks for the version if not provided. Never commits, tags or pushes unless asked.
argument-hint: [X.Y.Z] [commit] [tag] [push]
allowed-tools: [Read, Glob, Grep, Bash, Edit, Write]
---

Bump the version of the project in the current working directory.

## Step 0 — Detect the repo profile

Run `dev-copilot-profile` (Bash; if not found, `"${CLAUDE_PLUGIN_ROOT}/bin/dev-copilot-profile"`). It prints `profile=`, `kind=`, `repo=`, `name=`, `root=`, `reason=`.

- **`profile=wow`** — Read `<root>/profiles/wow/bump-version.md` now. Each of its sections names a hook point in this spec (`<!-- overlay: <id> -->`) and says whether it **adds to** or **replaces** that section; `extra` sections say where they run. Apply them as you go. `kind` (`addon`, `library`, `standards`, `tooling`) refines WoW behavior where the overlay says so.
- **`profile=generic`** — follow this spec as written. Do not read the overlay.

Work from the repository root (`repo=`).

## Step 1 — Determine the new version

Parse `$ARGUMENTS` as whitespace-separated tokens. A token that looks like a semver (`X.Y.Z` or
`X.Y.Z-tag`, an optional leading `v` stripped) is the new version. The words `commit`, `tag` and
`push` are opt-ins for Step 6 and are case-insensitive; anything else is an error — say what was not
understood and stop.

If no version was given:

<!-- overlay: current-version -->
1. Find the current version. Check, in this order, and stop at the first that has one: the primary
   manifest (`package.json` `version`, `pyproject.toml` `[project]`/`[tool.poetry]` `version`,
   `Cargo.toml` `[package]`/`[workspace.package]` `version`, `pom.xml` project `<version>`,
   `build.gradle(.kts)` / `gradle.properties` `version`, `*.csproj` `<Version>`/`<VersionPrefix>`,
   `*.gemspec` / `lib/**/version.rb`, `composer.json`, `mix.exs`, `Chart.yaml`,
   `.claude-plugin/plugin.json`, `manifest.json`), then a `VERSION` / `version.txt` file, then a
   version constant in code (`__version__`, `VERSION =`, `const Version =`), then the latest git tag
   (`git describe --tags --abbrev=0`), then the README's "Version" mention. If two sources disagree,
   report both and ask which is authoritative before going on. (Go modules carry no version in a
   file: the tag is the version.)
2. Propose a bump:
   - **patch** (`X.Y.Z` → `X.Y.Z+1`): the safe default for bugfixes / small changes
   - **minor** (`X.Y.Z` → `X.Y+1.0`): for new features
   - **major** (`X.Y.Z` → `X+1.0.0`): for breaking changes (for `0.y.z`, a breaking change bumps
     the minor unless the user says otherwise)
   Recommend one with a one-line reason based on what's in the working tree (`git status` /
   `git diff` if it's a git repo, otherwise a quick scan of recent file mtimes) and the commits since
   the last tag (Conventional Commit prefixes, `BREAKING CHANGE` footers, `!` markers).
3. Ask the user: "Current version is X.Y.Z. Propose bumping to A.B.C ([reason]). Confirm or specify
   another version."
4. Wait for the user's reply before proceeding.

<!-- overlay: gate -->
## Step 2 — The release gate (STOP on any failure)

A release is gated on the repo's full lint / type-check / test battery. This runs **before any file
is edited**, so a failed gate leaves the repo exactly as it was found.

1. **Run the battery** exactly as `/dev-copilot:run-tests` discovers it (its Steps 1–2: the repo's
   documented commands first, then the task runner, then ecosystem auto-detection; bounded runs;
   benchmarks and other non-gating runners excluded). Run it directly — do not stop to offer fixes.
2. **A skip is not a pass.** A suite the repo declares that could not run (tool absent, no
   interpreter) cannot vouch for the release: report it as **NOT EVALUATED** — visibly distinct from
   FAILED — with the install hint, and stop.
3. **No battery at all** (nothing declared, nothing detected): say so and ask whether to release
   ungated. Proceed only on an explicit yes, and carry "released without an automated test gate" into
   the Step 6 report.
4. **On any failure or non-evaluation: STOP.** Change nothing — no version string, no README, no
   CHANGELOG. Do not tag, do not commit, do not push. A partial bump is worse than a clean refusal,
   because the next attempt starts from a state nobody chose.
5. **Report every failed suite, not the first**, in one table, so a release blocked for a lint error
   that also has failing tests is understood once rather than across rounds:

   ```
   RELEASE GATE FAILED — version NOT bumped (still X.Y.Z)

   | Suite  | Result        | Detail                          |
   |--------|---------------|---------------------------------|
   | ruff   | PASS          | 0 findings                      |
   | mypy   | FAIL          | 4 errors in 2 files             |
   | pytest | FAIL          | 2 failed of 418                 |
   | eslint | NOT EVALUATED | eslint not installed (npm ci)   |

   Failing items:
     - test_parse_empty  (tests/test_parser.py:88)
     ...
   Nothing was modified. Fix the above and re-run /dev-copilot:bump-version.
   ```

   Name **every** failing test, lint and type error with its file:line — a count alone sends the user
   back to the log.
6. **Only when every suite passes**, print a one-line `RELEASE GATE PASSED` with the same table and
   continue.

## Step 3 — Find every version reference

<!-- overlay: targets -->
Search the repo root recursively (skip `.git/`, `node_modules/`, `vendor/`, `third_party/`,
`dist/`, `build/`, `target/`, `.venv/`, submodules and other vendored or generated directories) for
the **current** version string. Targets to check explicitly (don't rely on the regex search alone
for these — verify each):

**Manifests**
- Every manifest from Step 1 that carries the project's own version — including each package's
  manifest in a monorepo that versions in lockstep (if packages version independently, ask which
  ones this release covers).
- Plugin / extension manifests and their marketplace or registry mirrors (`plugin.json`,
  `marketplace.json`, `manifest.json`, `package.nls.json`, `extension.toml`).
- **Lockfiles — the project's own entry only, where the ecosystem expects it**: the root `version`
  (and `packages[""].version`) in `package-lock.json`; the project's own `[[package]]` entry in
  `Cargo.lock`; the root project in `poetry.lock`/`uv.lock` only if the tool records it. Edit just
  that field; never regenerate a lockfile or touch a dependency's version. Lockfiles that do not
  record the project's own version (`yarn.lock`, `pnpm-lock.yaml`, `go.sum`) are left alone.

**Code**
- Version constants: `__version__`, `VERSION =`, `version = `, `const Version`, `APP_VERSION`,
  user-agent strings, `--version` output literals, OpenAPI `info.version` when it tracks the release.
- Any other string literal matching the current semver in source — verify each one is the
  project's version and not a dependency's.

**README**
- The "Version" heading or text mention near the top; install snippets pinning the version
  (`pip install pkg==X.Y.Z`, `"pkg": "^X.Y.Z"`, `uses: owner/action@vX.Y.Z`, Docker tags).
- **Shields.io badge URLs** that include the version. Common shapes:
  - `https://img.shields.io/badge/version-X.Y.Z-...` (manually pinned — update)
  - `https://img.shields.io/npm/v/<pkg>`, `/pypi/v/<pkg>`, `/crates/v/<pkg>`,
    `/github/v/release/<owner>/<repo>` (auto-derived — leave alone)
  - Manually-pinned badges with the version in the path or `?label=` parameter

**Other docs**
- `CLAUDE*.md` / `AGENTS*.md`, `ARCHITECTURE*.md`, `CONTRIBUTING*`, `docs/` mentions of the current
  version — but not historical statements ("added in 1.2.0") and not past CHANGELOG entries.
- `CHANGELOG.md` (or the repo's equivalent: `HISTORY.md`, `NEWS.md`, `CHANGES.rst`,
  `docs/changelog.md`) — gets a new entry in Step 4; past entries are never rewritten.

**Auto-derived or substituted (do NOT touch)**
- Versions injected at build time (`@project-version@`, `${version}` placeholders,
  `setuptools_scm`/`hatch-vcs`/`versioneer` dynamic versions, `ldflags -X main.version=`), and the
  auto-derived badges above.
- Note any of these to the user as "skipped because auto-derived". If the version is entirely
  tag-derived, say so: the bump is then the CHANGELOG entry plus the tag the user creates.

Report the full list of matches **before** editing.

## Step 3b — Summarize changes since the last release

<!-- overlay: since -->
**Determine the "since" reference**, in this order:
1. **The last git tag** — `git describe --tags --abbrev=0` (fall back to
   `git tag --list --sort=-v:refname | head -1` if the repo has no annotated tags). This is the
   release boundary; prefer it over everything below.
2. Git tag matching the previous version specifically: `git tag --list 'v<previous>' '<previous>'`.
3. The commit that last set the version constant to the previous value. Find via
   `git log -G '"<previous>"' -- <files-from-Step-3>` and pick the most recent commit that
   *introduced* the previous version (typically the previous bump-version commit).
4. The date of the newest dated entry in the CHANGELOG — use `git log --since=<date>` as a fallback
   window.
5. If none of the above can be determined, skip the generated content, leave the CHANGELOG alone,
   and warn the user that no `since` reference was found. Never invent a change list.

State which reference you used and how many commits it spans before writing anything.

<!-- overlay: material -->
**Collect change material**:
1. `git log <since>..HEAD` — full subjects *and* bodies; bodies carry the "why" for non-trivial
   commits.
2. `git diff --stat <since>..HEAD` — scope, and a cross-check that nothing sizeable is missing from
   the log.
3. If a `CHANGELOG.md` exists and has a populated `## [Unreleased]` (or equivalent) section, treat
   those bullets as **authoritative** change material — keep their wording and merge anything from
   git they don't already cover, rather than rewriting them.

<!-- overlay: release-notes -->
**Write the full list** (the CHANGELOG entry):
- Group by the categories the file already uses; if it has none, use Keep a Changelog's: **Added**,
  **Changed**, **Deprecated**, **Removed**, **Fixed**, **Security**. Skip empty categories.
- Cover every user-relevant change — the list is exhaustive.
- Past tense, user-visible language ("Added the `--json` flag", "Fixed a crash on empty input") —
  not commit-message phrasing.
- Roll up genuine trivia (whitespace, lint, formatting, dependency bumps) into a single bullet.
- No commit hashes, PR numbers, or author names unless the file's existing entries carry them.
- If the release is purely internal (no user-visible change), say so in one line rather than
  padding with trivia.

## Step 4 — Update

<!-- overlay: update -->
For each match, replace the old version with the new version using `Edit`. Be precise — match the
exact context to avoid touching unrelated strings (e.g. don't replace `1.0.0` if it's a dependency's
version, a minimum runtime version, a schema or API version, or a file-format version).

<!-- overlay: history -->
**The CHANGELOG entry.** If a `CHANGELOG.md` (or the repo's equivalent from Step 3) exists, write a
full entry for this release — `## [X.Y.Z] - YYYY-MM-DD` with today's date (match the file's heading
shape and dash), followed by the Step 3b full list. If an `## [Unreleased]` header exists, that entry
becomes this one: retitle it and merge its existing bullets in, then leave a fresh empty
`## [Unreleased]` above it if the file keeps one. Follow the file's established formatting (Keep a
Changelog style, link refs at the bottom, etc.) rather than imposing a new one; if the file
maintains comparison links, update `[Unreleased]` and add one for the new version. Do NOT rewrite
past entries.

If **no** changelog exists, offer to create `CHANGELOG.md` in Keep a Changelog format with this
release as its first entry. Create it only on a yes; otherwise print the entry in the Step 5 report
so it can go into the release notes.

## Step 5 — Report

<!-- overlay: report -->
Print:
- `RELEASE GATE PASSED` with the Step 2 table (or that the user chose to release ungated)
- Old version → New version
- The `<since>` reference used and the commit count it spanned
- Every file changed (path + the line that was updated)
- Every version-shaped string found but NOT changed, with the reason (e.g. "dependency version, not
  the project's", "auto-derived npm badge", "setuptools_scm dynamic version")
- Where the release history was written (CHANGELOG path), or that none was written and why
- The next step, as a command the user can copy: `git commit -am "Release vX.Y.Z"` and
  `git tag -a vX.Y.Z -m "vX.Y.Z"`, matching the tag shape existing tags use (`v1.2.3` vs `1.2.3`)

## Step 6 — Commit, tag, push (only when asked)

<!-- overlay: no-commit -->
Do these only for the opt-ins `$ARGUMENTS` carried (or the user asked for in the conversation), in
this order, and only after the gate passed and Step 4 finished:
- `commit` — stage exactly the files Step 4 changed and commit them as `Release vX.Y.Z` (match the
  repo's existing release-commit subject if there is one).
- `tag` — create an annotated tag on that commit, in the existing tag shape. Requires `commit`
  (or a clean tree where the bump is already committed); refuse otherwise.
- `push` — push the branch, and the tag if one was created (`git push origin <branch> vX.Y.Z`;
  never `--tags`, never `--force`).

Without an opt-in, stop after Step 5.

## Hard rules

<!-- overlay: hard-rules -->
- **Don't commit, tag or push unless asked** (Step 6). The user reviews the diffs first.
- **Don't create a CHANGELOG without a yes**, and never delete or reorganize an existing one.
- **Don't modify past CHANGELOG entries** — only add the new version's entry.
- **Don't let the generated text outrun the commits.** Every bullet in the CHANGELOG entry must
  trace to a real change between `<since>` and HEAD. No aspirational or filler entries; if there's
  nothing since the last tag, say so and bump the version only.
- **Don't bump anything when the Step 2 gate fails.** No version string, no README, no CHANGELOG, no
  tag, no commit, no push. Report every failed suite with its detail and stop. Never "bump anyway and
  note it" — a release the gate refused is not a release with a caveat.
- **Don't touch dependency versions or regenerate lockfiles.** A version bump changes the project's
  own version and nothing else.
