# WoW overlay — issue-audit

Applied by `/dev-copilot:issue-audit` to every repo in scope for which `dev-copilot-profile` reports `profile=wow`, and to the scope step when the cwd (or a checkout under an orchestration folder) is WoW. The base spec's label vocabulary, stray repair, discovery record (ID, location, verbatim evidence, evidence hash, age), git and memory sweeps, reconciliation, filing rules, report and hard rules apply unchanged. This overlay carries what the Ka0s collection adds: the retired ledger, the WoW severity ladder, the collection roster as the `all` scope, the addon check, Lua as the code to sweep, and the `docs/audits/` + `docs/reviews/` bundles as the plan items to check.

## store-intro — adds

The heading reads **The store: GitHub issues on the addon's own repo**. `docs/pending/LEDGER.md` is **retired** — the durable record is the set of GitHub issues on the addon's repo, and no run may create, recreate or mirror that ledger.

## severity-ladder — replaces

| Severity | Label | Color | Meaning |
|---|---|---|---|
| Critical | `severity:critical` | red `110000` | Taint, combat-lockdown breakage, saved-variable corruption or data loss, an error on a common path |
| High | `severity:high` | orange `110800` | A user-visible defect, or a Ka0s standard deviation carried from an audit bundle |
| Medium | `severity:medium` | yellow `111100` | Maintainability: a stub callers depend on, code/doc drift, a dead path |
| Low | `severity:low` | green `001100` | Polish, naming, cosmetic, speculative-future notes |

## scope — replaces

Replaces only the `all` and repo-name bullets; the base's `absent, or here` default stands. The paragraphs after them apply alongside the base's.

- **`all`** → every addon repo in the collection. Read the roster from `WowAddonStandards/standards/ADDONS.md` (folder + repository per row) rather than hardcoding it; if that repo isn't checked out, fall back to sibling directories containing a `.toc` and **say in the report that the roster was inferred**.
- **a repo name** → that repo alone, matched case-insensitively against the roster. If it matches nothing, say so, list the valid names, and stop. Don't guess at a near-miss.

If the cwd is not an addon repo and no scope was given, **ask** which scope to use rather than guessing — sweeping the wrong repo wastes a run, and sweeping `all` when the user meant one repo files issues on ten repos they weren't thinking about.

The roster is the confirmation: the base's "show the resolved list and confirm it" step is not run separately for a roster read from `ADDONS.md` — the per-repo approval in Step 4 stands. An *inferred* roster is shown with the warning that it was inferred.

## repo-check — replaces

For each repo in scope, confirm it is a WoW addon (at least one `.toc`, or a `docs/`+`.lua` layout), then preflight with the base's two `gh` checks and the same stop-and-say-so rule.

`kind=addon` and `kind=library` pass the addon check (LibKa0s ships a TOC). A `kind=standards` (WowAddonStandards) or `kind=tooling` repo carries no TOC and is not an addon: say so and ask whether to sweep it anyway rather than assuming either way. If the user says yes, sweep it with the base's generic code-marker scope (its own files, which are not Lua) and this overlay's plan-bundle sweep.

## label-set — replaces

Run the base block with one line changed — these are the eight **collection labels**, identical on every Ka0s repo:

```
gh label create "severity:critical" --color 110000 --description "Taint, lockdown, data loss, common-path error"  --force
```

Every other line, and the read-`gh label list`-first rule, stand.

## code-scope — replaces

Grep the addon's own `.lua` and `.xml` files — **exclude `libs/`, `Libs/` and any vendored library directory**. The marker list and the deferral vocabulary are the base's; for an addon read them as Lua:

- **stub functions** — a body that is empty, only a comment, or only `return` / `return nil`
- **commented-out blocks** — three or more consecutive commented lines that parse as Lua rather than prose

A bare `-- TODO` with no context is itself a finding ("marker with no stated intent").

In the Step 4 filing example, the record reads like a Lua find: `**Location:** modules/Aura.lua:212`, evidence `> -- TODO: handle the pet-swap case before 11.2`.

## plan-bundles — replaces

Then the high-value one: **unexecuted plan items.** Find the newest `docs/audits/<YYYY-MM-DD>/05_EXECUTION_PLAN.md` (written by `/dev-copilot:wow-standards-audit`) and the newest `docs/reviews/<YYYY-MM-DD>/04_EXECUTION_PLAN.md` (written by `/dev-copilot:review` in a WoW repo). For each step or deviation ID, check the current code to see whether it was carried out. Report executed / not executed / partially executed **with the evidence you used to decide** — a plan row is a pending item only if the code still shows the pre-remediation state. Carry the original deviation ID into the evidence so it stays traceable to the frozen bundle.

The `docs/` sweep's Known Limitations live in **`docs/ARCHITECTURE.md`** in a Ka0s repo.

`docs/revendor/<date>-v<tag>/` bundles are **not** swept for pending items: `/dev-copilot:wow-revendor-libka0s` already files every decline its interview records as a GitHub issue, so its bundle is a record of filed work, not a source of new work.

## hard-rules — adds

- **Don't touch `libs/`** (or `Libs/`, or `tests/_kit/`) — vendored copies are re-vendored from their source, never edited in place.
- **Don't edit frozen artifacts.** `docs/audits/<date>/` and `docs/reviews/<date>/` are history — and so are `docs/revendor/` and `docs/automated-tests/` bundles. This command reads the audit and review execution plans to find unexecuted rows but never edits them.
