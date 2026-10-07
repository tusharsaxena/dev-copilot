# WoW overlay — issue-details

Applied by `/dev-copilot:issue-details` when the scope step runs from a WoW repo (or from an orchestration folder above WoW checkouts), and to every repo in scope for which `dev-copilot-profile` reports `profile=wow`. The base spec's state and severity filters, fetch, classification, the one sanctioned repair, the per-status layout, the row-width arithmetic, the build-quietly rule and the hard rules apply unchanged in every `kind`. This overlay carries the Ka0s collection as the `all` scope and its measured URL width.

## scope — replaces

Replaces only the `all` and repo-name bullets; the base's `absent, or here` default stands. The paragraphs after them apply alongside the base's.

- **`all`** → every row of `WowAddonStandards/standards/ADDONS.md`, read rather than hardcoded (folder + repository per row): the *In-scope addons* table, then the *Ka0s-owned library repos* table (`LibKa0s`), then the *Documentation-and-tooling repos* table (`WowAddonStandards`, `dev-copilot`), each in its table's row order. Tag every repo with its kind — `addon` for an addon-table row, `library` for a library-table row, `standards` for `WowAddonStandards` and `tooling` for any other documentation-and-tooling row, the same `kind` `dev-copilot-profile` reports for it. If `ADDONS.md` is unreachable, fall back to the sibling directories next to the cwd that contain a `.toc` (`addon`, except `LibKa0s`) plus the three known upstreams `LibKa0s` (`library`), `WowAddonStandards` (`standards`) and `dev-copilot` (`tooling`), and **say in the report that the roster was inferred** — an inferred roster can silently omit a repo, and a missing repo reads as "nothing here" rather than "not checked".
- **a repo name** → that repo alone, with its kind tag, matched case-insensitively against the same roster (every row, upstreams included). If it matches nothing, say so, list the valid names, and stop. Don't guess at a near-miss.

If the cwd is not a repo `gh` can resolve and no scope was given, **ask** which scope to use rather than guessing.

"Scope order" in the print step is **roster order**: the addon rows, then the library row, then the documentation-and-tooling rows, each as `ADDONS.md` lists them.

## row-width — adds

At the collection's roster the longest full issue URL runs to **58 characters**, which is where the worked figures come from — so at the current roster the budget is exactly the base's: **Title ≤ 40, Description ≤ 38**, ~170 per row. When the roster changes (a new addon with a longer name, the tooling repo renamed), recompute the floor rather than carrying 58 forward.

## roster-rule — replaces

- **Don't invent the roster.** Read it from `ADDONS.md` or say plainly that you inferred it.
