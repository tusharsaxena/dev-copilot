# WoW overlay — issue-summary

Applied by `/dev-copilot:issue-summary` when the scope step runs from a WoW repo (or from an orchestration folder above WoW checkouts), and to every repo in scope for which `dev-copilot-profile` reports `profile=wow`. The base spec's fetch, classification, the one sanctioned repair, the three grids, the analysis rules and the hard rules apply unchanged in every `kind`. What changes is the scope: in the Ka0s collection this command **defaults to the whole collection**, not to `here`.

## scope — replaces

This replaces the whole of Step 2 from the marker down (the scope bullets, the one-row-grid note and the ask-when-unresolvable paragraph):

- **absent, or `all`** → the whole collection. **This is the default.** Read the addon roster from `WowAddonStandards/standards/ADDONS.md` (folder + repository per row) — it is the living list — then add the upstreams: **`WowAddonStandards`** (`kind=standards`), **`LibKa0s`** (`kind=library`) and the plugin repo (`kind=tooling`) — **`dev-copilot`**, plus the legacy **`wow-addon`** repo for as long as it still holds issues.
- **`here`** → the repo at the cwd.
- **a repo name** → that repo alone, matched case-insensitively against the roster (addons plus the upstreams). If it matches nothing, say so, list the valid names, and stop. Don't guess at a near-miss — reporting the wrong repo silently is worse than asking.

**Why the collection is the default here, when every other issue command defaults to `here`:** this is the only one whose whole value is the cross-repo comparison. A one-row grid is strictly worse than `/dev-copilot:issue-details here`. It is also routinely run from an orchestration directory that is not itself a GitHub repo, where a `here` default cannot resolve at all and can only produce a question.

If `ADDONS.md` isn't reachable on an `all` run, fall back to the sibling directories next to the cwd that contain a `.toc`, and **say in the report that the roster was inferred from disk rather than read from the standard**. An inferred roster can silently omit a repo, and a missing repo in a collection-wide report reads as "no open issues" rather than "not checked".

If `here` was passed explicitly and the cwd is not a repo `gh` can resolve, say so and stop — the user named a scope that does not exist. This can no longer happen by default, since the default is `all`.

**Order** (used by the status × repo grid in 5a and the severity × repo grid in 5b): addons first in roster order, then the upstreams, then a totals row. The base's "this is a read sweep over several repos" is, on the default run, a read sweep over a dozen repos.

## roster-rule — replaces

- **Don't invent the roster.** Read it from `ADDONS.md`, or say plainly that you inferred it.
