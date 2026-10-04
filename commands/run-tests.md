---
description: Run the current repo's entire lint/test/type-check battery — prefers the commands the repo documents (README, CONTRIBUTING, CLAUDE.md, Makefile, CI workflows), otherwise auto-detects them across ecosystems (npm/pnpm/yarn/bun scripts, pytest/tox/nox/ruff/mypy, go vet/test, cargo clippy/test, make, Maven/Gradle, dotnet, rspec/rake, phpunit, luacheck/busted…) — then reports a combined pass/fail table. Offers to diagnose and fix failures.
argument-hint: [suite name or path to narrow the run]
allowed-tools: [Bash, Read, Glob, Grep, Edit]
---

Run the full test battery for the repository at the cwd and report the results.

## Step 0 — Detect the repo profile

Run `dev-copilot-profile` (Bash; if not found, `"${CLAUDE_PLUGIN_ROOT}/bin/dev-copilot-profile"`). It prints `profile=`, `kind=`, `repo=`, `name=`, `root=`, `reason=`.

- **`profile=wow`** — Read `<root>/profiles/wow/run-tests.md` now. Each of its sections names a hook point in this spec (`<!-- overlay: <id> -->`) and says whether it **adds to** or **replaces** that section; `extra` sections say where they run. Apply them as you go. `kind` (`addon`, `library`, `standards`, `tooling`) refines WoW behavior where the overlay says so.
- **`profile=generic`** — follow this spec as written. Do not read the overlay.

<!-- overlay: scope -->
**This is the fast green gate — it records nothing.** It runs what the repo already declares, reads
the results, and leaves no files behind. If `$ARGUMENTS` names a suite (`lint`, `tests`, `types`, a
tool name) or a path, run only what matches and say what was left out.

<!-- overlay: locate -->
## Step 1 — Locate the project

Work from the repository root (`repo=` from Step 0), not the subdirectory you were started in:
documented commands and most tool configs assume the root. Confirm there is something buildable or
testable there — a manifest, a build file, a test directory, a CI workflow. If nothing testable is
present at all, say so and stop; don't invent a harness.

In a monorepo (workspaces, multiple manifests in sibling packages), prefer the root-level command
that fans out across packages (`pnpm -r test`, `npm test --workspaces`, `cargo test --workspace`,
`go test ./...`, `nx`/`turbo` targets). Only fall back to per-package runs when no root command
exists, and report each package as its own suite.

## Step 2 — Discover and run suites

<!-- overlay: runner -->
**Bound every run.** Wrap each command in a wall-clock limit where the platform has one
(`timeout 900 <command>` on Linux, `gtimeout` on macOS with coreutils) so a hung suite cannot stall
the session. A run that exits **124** hit the time limit and **137** was killed (often by memory) —
report either as exactly that, never as a test failure or a pass. Running independent suites in
parallel is fine when they do not share state (a database, a port, a build directory); otherwise
run them one at a time.

<!-- overlay: suites -->
### Where the commands come from (in order of authority)

1. **What the repo documents.** Read, in this order, `CLAUDE.md` / `AGENTS.md`, `CONTRIBUTING*`,
   the README's development/testing section, and the CI workflow files (`.github/workflows/*.yml`,
   `.gitlab-ci.yml`, `azure-pipelines.yml`, `.circleci/config.yml`, `Jenkinsfile`,
   `bitbucket-pipelines.yml`). A command the repo tells contributors to run — or that CI runs on
   every push — is the canonical one. Use it verbatim, minus CI-only steps (deploys, uploads, cache
   priming, secrets-dependent jobs) and minus matrix fan-out (run the local default once).
2. **A task-runner entry point.** A root `Makefile` (`test`, `check`, `lint`, `verify`, `ci`
   targets), `justfile`, `Taskfile.yml`, `noxfile.py`, `tox.ini`, or `package.json` scripts named
   `test`, `lint`, `typecheck`/`type-check`/`tsc`, `check`, `verify`, `ci`. These usually already
   wrap the tools below. **De-dup:** if `make test` (or `npm test`, `tox`, `nox`, `just test`)
   clearly runs the same suites you would otherwise detect, run it **instead of** re-running those
   suites, and say so in the summary. If it does something additional, run it as its own suite.
3. **Auto-detection** — only for what 1–2 did not already cover. Detect by the config file, run with
   the repo's own toolchain (its package manager, its virtualenv, its wrapper script):

   | Signal | Lint / static | Type-check | Tests |
   |---|---|---|---|
   | `package.json` (+ `pnpm-lock.yaml` → pnpm, `yarn.lock` → yarn, `bun.lockb`/`bun.lock` → bun, else npm) | `<pm> run lint` if declared; else `eslint .` / `biome check` when configured | `<pm> run typecheck` if declared; else `tsc --noEmit` when `tsconfig.json` exists | `<pm> test` / `<pm> run test` |
   | `pyproject.toml`, `setup.cfg`, `setup.py`, `requirements*.txt` (use the repo's runner: `uv run`, `poetry run`, `pdm run`, `hatch run`, or the active venv) | `ruff check .`; else `flake8` when configured; `pylint` only if configured | `mypy` / `pyright` when configured (`[tool.mypy]`, `mypy.ini`, `pyrightconfig.json`) | `tox` / `nox` when present, else `pytest`; else `python -m unittest discover` |
   | `go.mod` | `go vet ./...`; `golangci-lint run` when `.golangci.*` exists | (compiler) | `go test ./...` |
   | `Cargo.toml` | `cargo clippy --all-targets -- -D warnings` only if the repo's CI uses `-D warnings`, else `cargo clippy --all-targets`; `cargo fmt --check` when CI runs it | (compiler) | `cargo test` (`--workspace` in a workspace) |
   | `pom.xml` / `build.gradle(.kts)` (prefer `./mvnw` / `./gradlew`) | `checkstyle`/`spotless` goals when configured | (compiler) | `mvn -q test` / `./gradlew test` (or `check`) |
   | `*.sln` / `*.csproj` / `*.fsproj` | `dotnet format --verify-no-changes` when CI runs it | (compiler) | `dotnet test` |
   | `Gemfile` | `bundle exec rubocop` when `.rubocop.yml` exists | `srb tc` / `steep check` when configured | `bundle exec rspec` (spec/) or `bundle exec rake test` |
   | `composer.json` | `phpcs` / `php-cs-fixer --dry-run` when configured | `phpstan` / `psalm` when configured | `composer test` if declared, else `vendor/bin/phpunit` |
   | `mix.exs` | `mix credo` when present; `mix format --check-formatted` | `mix dialyzer` when configured | `mix test` |
   | `.luacheckrc`, `*.rockspec`, `.busted` | `luacheck .` | — | `busted`, or the repo's own `tests/` runner |
   | Shell scripts / `*.sh` with a `.shellcheckrc` or CI shellcheck step | `shellcheck` | — | `bats test/` when present |
   | `CMakeLists.txt` / `meson.build` | — | — | `ctest --test-dir <build>` / `meson test -C <build>` against an existing build dir only |

   Run a tool only when the repo shows it is part of the battery (a config file, a declared script,
   a CI step, a dev dependency). Do not lint a repo with a linter it never adopted.

<!-- overlay: not-suites -->
### Not part of the battery

Benchmarks, load and soak tests, coverage upload, mutation testing, end-to-end suites that need
external services the repo does not start itself, release/deploy jobs, and formatters in write mode
(`--fix`, `fmt` without `--check`) are **not** suites here. If one exists, note in one line that it
is available and move on — never count its results in the pass/fail summary.

Report every suite as **pass**, **fail**, or **skipped (tooling absent)** — a missing tool is a
skip, not a failure. Install nothing without asking; say what the install would be.

Run suites read-only — none of this edits code.

## Step 3 — Combined summary

<!-- overlay: summary -->
Print a compact summary:
- A table, one row per suite: name — command run — **pass / fail / skipped** — counts (e.g.
  `ruff — pass — 0 findings`, `pytest — fail — 213 passed, 2 failed`, `tsc — skipped — typescript
  not installed`).
- A headline verdict (e.g. `3/4 suites passed` or `All suites passed`).
- Where each command came from (documented, task runner, auto-detected), so the user can tell a
  canonical command from a guess.
- The wall-clock time of the slowest suite, on its own line.
- For failures, show the **relevant failing output** — the failed assertions / lint lines / type
  errors with file:line — not the entire log.

<!-- overlay: no-suites -->
If **no** suites were found at all, tell the user the repo has no test battery yet and suggest the
conventional starting point for its ecosystem (one line, no scaffolding).

## Step 4 — On failure, offer to fix

If any suite failed, after printing the summary ask:

> "Want me to diagnose and fix the N failure(s)? (y/n)"

<!-- overlay: fix -->
- **y** → investigate the failures, propose fixes, and apply them **with approval before editing**
  any file. Re-run the affected suite(s) to confirm. If a fix changes a number the repo publishes
  (a test-count badge, a generated test inventory), move it in the same change.
- **n** → stop. The user handles it.

## Hard rules

<!-- overlay: hard-rules -->
- **Read-only during the run.** The only time this command edits code is the opt-in fix phase in
  Step 4, after the user says yes.
- **Vendored code is never edited — not even to make a test pass.** `vendor/`, `third_party/`,
  `node_modules/`, git submodules and any folder the repo documents as copied from elsewhere: a
  failure whose real cause is there is an upstream fix plus a re-vendor. Say so and stop; never
  weaken or delete the test that caught it.
- **A missing tool is a skip, not a failure.** Report it as skipped with an install hint.
- **Don't dump full logs.** Show the failing lines; summarize the rest.
- **Don't fabricate results.** If a suite can't run, say why; never report a pass you didn't
  observe.
