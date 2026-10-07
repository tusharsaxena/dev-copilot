# WoW overlay — issue-summary

Applied by `/dev-copilot:issue-summary` when the scope step runs from a WoW repo (or from an orchestration folder above WoW checkouts), and to every repo in scope for which `dev-copilot-profile` reports `profile=wow`. The base spec's fetch, classification, the one sanctioned repair, the three grids, the analysis rules and the hard rules apply unchanged in every `kind`. What changes is the scope: in the Ka0s collection this command **defaults to the whole collection**, not to `here`.

## scope — replaces

This replaces the whole of Step 2 from the marker down (the scope bullets, the one-row-grid note and the ask-when-unresolvable paragraph):

- **`all`** → every row of `WowAddonStandards/standards/ADDONS.md`, read rather than hardcoded (folder + repository per row): the *In-scope addons* table, then the *Ka0s-owned library repos* table (`LibKa0s`), then the *Documentation-and-tooling repos* table (`WowAddonStandards`, `dev-copilot`), each in its table's row order. Tag every repo with its kind — `addon` for an addon-table row, `library` for a library-table row, `standards` for `WowAddonStandards` and `tooling` for any other documentation-and-tooling row, the same `kind` `dev-copilot-profile` reports for it. If `ADDONS.md` is unreachable, fall back to the sibling directories next to the cwd that contain a `.toc` (`addon`, except `LibKa0s`) plus the three known upstreams `LibKa0s` (`library`), `WowAddonStandards` (`standards`) and `dev-copilot` (`tooling`), and **say in the report that the roster was inferred** — an inferred roster can silently omit a repo, and a missing repo reads as "nothing here" rather than "not checked".
- **absent** → the same roster as `all`. **This is the default.**
- **`here`** → the repo at the cwd.
- **a repo name** → that repo alone, with its kind tag, matched case-insensitively against the same roster (every row, upstreams included). If it matches nothing, say so, list the valid names, and stop. Don't guess at a near-miss — reporting the wrong repo silently is worse than asking.

**Why the collection is the default here, when every other issue command defaults to `here`:** this is the only one whose whole value is the cross-repo comparison. A one-row grid is strictly worse than `/dev-copilot:issue-details here`. It is also routinely run from an orchestration directory that is not itself a GitHub repo, where a `here` default cannot resolve at all and can only produce a question.

If `here` was passed explicitly and the cwd is not a repo `gh` can resolve, say so and stop — the user named a scope that does not exist. This can no longer happen by default, since the default is `all`.

**Order** (used by the status × repo grid in 5a and the severity × repo grid in 5b): roster order — the addon rows, then the library row, then the documentation-and-tooling rows, each in `ADDONS.md`'s row order — then a totals row. The base's "this is a read sweep over several repos" is, on the default run, a read sweep over every roster row.

## roster-rule — replaces

- **Don't invent the roster.** Read it from `ADDONS.md`, or say plainly that you inferred it.
