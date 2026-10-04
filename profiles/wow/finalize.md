# WoW overlay — finalize

Applied by `/dev-copilot:finalize` to every repo in scope for which `dev-copilot-profile` reports `profile=wow`, and to every scope or dependency edge with a WoW repo at either end. The base spec's scope rules, default-branch detection (Ka0s repos default to `master`; detect it anyway), merge, push, branch deletion and report shape apply unchanged. This overlay carries what the Ka0s collection adds: its folder layout and vendored trees as scope evidence, the LibKa0s provenance line as dependency evidence, the bounded runner and the vendor-drift gate, the commit-vs-release complexity split, and how a non-addon `kind` changes the doc sync.

The collection is one parent directory of sibling checkouts: the Ka0s addons, `LibKa0s` (`kind=library`), `WowAddonStandards` (`kind=standards`) and the tooling repos (`kind=tooling`). The `survey` section below widens the base's survey to exactly that directory.

## survey — replaces

Replaces only the paragraph naming which repos the survey looks at. In the collection, take the parent directory as the collection root and list every sibling that is a git repo (`ls -d ../*/.git`); survey each of them plus the cwd repo, with the two commands of the next paragraph.

## scope-evidence — adds

In the collection, "a vendored copy of a library" means an addon's `libs/<Lib>/` (or `tests/_kit/`) whose source is a sibling repo — `LibKa0s` today. When a sibling library changed and a candidate's `libs/<Lib>/` or `tests/_kit/` is a byte-for-byte match for that changed source, that is hard evidence the two are one changeset (a re-vendor that landed with the library change), not a hunch.

## dependency-chain — adds

For WoW repos the edges read concretely as follows:

- **Vendored shared libraries.** If repo B carries `libs/<Lib>/` (or `tests/_kit/`) whose source is repo A in the same collection, then **A precedes B**. Confirm the relationship — `diff -r --strip-trailing-cr A/<Lib> B/libs/<Lib>` — rather than inferring it from the name. In practice `LibKa0s` precedes every addon that vendors it.
- **Release order.** If the changeset includes a version tag in A that B's docs or provenance line name, A goes first. For `LibKa0s` that provenance line is in B's **root `CLAUDE.md`** — `Bundles [LibKa0s](…) vX.Y.Z (MIT).` — not its `README.md`, since LibKa0s v1.8.1 / test-kit revision 9; grep `CLAUDE.md` for it, and treat a copy still sitting in `README.md` as a defect to report rather than a second source to read. The same rule orders `WowAddonStandards` ahead of any addon whose changed docs cite a standard version or section it publishes in this changeset.

Print the chain in the collection's terms — e.g. `LibKa0s → (AbsorbTracker | BankLedger | ConsumableMaster | KickCD)` — with the evidence for each edge.

## doc-sync — adds

- **Content sync only, concretely.** In a WoW repo, the scaffolding `/dev-copilot:sync-docs` asks to confirm is creating or restructuring a missing `docs/ARCHITECTURE.md` or root `CLAUDE.md` stub. The base binding holds: in a multi-repo run, do not create or move them — record the proposal for the report; in a single-repo run, ask.
- **A repo in the collection may not be an addon.** When `kind` is not `addon` (`library`, `standards`, `tooling`), there is no `.toc`, no slash commands, no schema — a shared library like `LibKa0s` has none. Skip the TOC-derived steps and apply the rest: does the README still describe what it ships, do the counts hold, is the version claim true.

## gate-commands — replaces

```
~/.claude/dev-copilot/bin/ka0s-bounded lua tests/run.lua        # or whatever /dev-copilot:run-tests discovers
~/.claude/dev-copilot/bin/ka0s-bounded luacheck .
```

**Every run goes through the bounded runner.** Prefix each command with `~/.claude/dev-copilot/bin/ka0s-bounded` (e.g. `~/.claude/dev-copilot/bin/ka0s-bounded lua tests/run.lua`). It caps process memory, process-tree memory and wall-clock time, and queues on a machine-wide slot pool, so running several repos' suites **in parallel** is fine — the pool, not you, decides how many run at once. The plugin's `PreToolUse` hook refuses an unbounded `lua tests/run.lua` / `tests/perf.lua`, `run-automated-tests.sh`, `luacheck` or `lizard` (a repo whose `tests/_kit` is kit revision 23+ self-bounds its Lua runs and is let through). A run that exits **124** hit the time limit and **137** was killed, most likely by the memory limit — report either as exactly that, never as a test failure or a pass.

## vendor-drift — replaces

In any repo that vendors a shared library, the vendor-drift gate — both readings:

```
diff -r --strip-trailing-cr ../<Lib>/<Lib> libs/<Lib>   # content — MUST be empty
diff -r ../<Lib>/<Lib> libs/<Lib>                       # bytes  — SHOULD be empty
```

## release-gate — replaces

**The complexity record is not part of *this* gate.** (The **release** gate is all four suites plus zero CCN > 15 and `blindFiles` at 0, and it lives in `/dev-copilot:bump-version`, which refuses to bump when any of them fails — `automated-tests-§3`. This command neither evaluates nor re-evaluates it.) Do not run `lizard` here and do not let the complexity record block a commit: its checkpoint is **release, not commit** (`performance-§10`), and a complexity gate on commits is the fastest way to teach a collection to reach for `--no-verify`. There is one thing to *check*, without regenerating anything: if this changeset bumps the version — a new `## Version:` in the TOC, or a fresh `## Version History` row — then it is a release change, and the release change is where the report is refreshed. If no fresh `docs/automated-tests/<run>/` bundle is present in it, say so in the Step 4 report and name `/dev-copilot:bump-version` as the command that owns the refresh. Do not regenerate it yourself, do not hold the push for it, and never hand-edit it.

## report-example — replaces

| Repo | Profile | Docs synced | Gate | Commit | Branch | Pushed |
|---|---|---|---|---|---|---|
| LibKa0s | wow / library | 2 files | 407 pass, 0/0 | `a1b2c3d` | master (no branch — merge/delete n/a) | ✅ |

The partial-success example in the collection's terms: "Four of five repos are pushed; ConsumableMaster stopped on a red gate and is committed but unpushed."

## hard-rules — adds

- **Never edit a vendored folder** (`libs/`, `tests/_kit/`) to make anything pass. A defect there is an upstream finding: fix it in the library repo, bump the file's LibStub minor, re-vendor as its own commit. A local patch is reverted silently by the next copy.
- **Never gate a commit on the complexity record, and never regenerate it here.** Report a release changeset that produced no fresh automated-test bundle; that is the whole of this command's involvement.
