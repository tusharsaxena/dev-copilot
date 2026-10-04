# Phase 2: ripple the wow-addon → dev-copilot rename through the collection

**Spec:** `docs/superpowers/specs/2026-10-04-merge-wow-addon-design.md` (D5, "Out of scope (phase 2)").
**Goal:** no live document, spec, comment or printed string in the collection names `/wow-addon:*`, the
wow-addon plugin, or `~/.claude/wow-addon/`, except dated history.

## Rules

- Branch `feat/2026-10-04-dev-copilot-rename` in every touched repo; commit in the repo's own log style;
  push the branch. **No merge, no tag, no archive without the user's go-ahead.**
- Rename map: `/wow-addon:<x>` → `/dev-copilot:<x>` (shared) or `/dev-copilot:wow-<x>` (new-addon,
  bump-interface, automated-tests, perf-analysis, revendor-libka0s, revendor-standards,
  harvest-standards, standards-audit); agents `wow-addon:review` → `dev-copilot:review`,
  `wow-addon:standards-audit` → `dev-copilot:wow-standards-audit`; "the wow-addon plugin" → "the
  dev-copilot plugin"; `~/.claude/wow-addon/` → `~/.claude/dev-copilot/`; repo URL → dev-copilot; the
  audit rotation's tooling repo `wow-addon` → `dev-copilot`.
- **Unchanged:** dated history — changelog entries, `audit-review-history` dated rows, frozen bundles
  (`docs/audits|reviews|automated-tests|perf-analysis|revendor|superpowers/`, harvests, dated planning
  dirs). A sentence describing what *was* true on a date stays.
- Byte-exact line endings (CRLF in client-bound repos). Vendored `libs/` and `tests/_kit/` in addons are
  read-only — they change only by re-vendoring (Stage B).
- Each repo's own commit gate must pass before committing (addons: `ka0s-bounded luacheck .` and
  `ka0s-bounded lua tests/run.lua`; LibKa0s: its full suite; standards repo: its own checks).

## Ledger

| Step | Repo(s) | Status |
|---|---|---|
| A1 | WowAddonStandards — text + version bump + changelog entry | done — v2.76.0, fa02fb6 |
| A2 | LibKa0s — docs + testkit/ (+ its own tests/_kit copy), kit revision bump, release prep per docs/releasing.md (no tag) | done — v1.68.1 / kit 36; release record 9000cbd (tag target), all tag preconditions hold |
| A3 | 12 addons — own docs, own test comments, AuraMaster `.claude/commands` path, Outfitter CLAUDE.md | done — 12 addons, gates green; 7 got a DC-REN-02 for docs/automated-tests/README.md |
| A4 | Ka0sAddonsCommonTasks README/CLAUDE.md; wow-addon README "moved" notice | done |
| A5 | dev-copilot — drop transitional wording once the rotation names dev-copilot | done — 1cfe0b5 + CLAUDE.md |
| A6 | Verify: residual grep across all repos, gates green, branches pushed | done — verifier: all branches pushed, masters untouched, line endings intact |
| G1 | **User go-ahead:** merge A-branches; tag LibKa0s release | pending |
| B1 | Re-vendor the LibKa0s tag into the 11 addons (`/dev-copilot:wow-revendor-libka0s`) | pending |
| G2 | **User go-ahead:** merge B-branches; archive wow-addon on GitHub (ask) | pending |
| Z | Memory: rewrite `/wow-addon` → `/dev-copilot` in Claude memory files; delete run branches/stashes/worktrees | pending |
