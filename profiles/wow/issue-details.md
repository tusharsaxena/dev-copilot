# WoW overlay — issue-details

Applied by `/dev-copilot:issue-details` when the scope step runs from a WoW repo (or from an orchestration folder above WoW checkouts), and to every repo in scope for which `dev-copilot-profile` reports `profile=wow`. The base spec's state and severity filters, fetch, classification, the one sanctioned repair, the per-status layout, the row-width arithmetic, the build-quietly rule and the hard rules apply unchanged in every `kind`. This overlay carries the Ka0s collection as the `all` scope and its measured URL width.

## scope — replaces

Replaces only the `all` and repo-name bullets; the base's `absent, or here` default stands. The paragraphs after them apply alongside the base's.

- **`all`** → every addon repo plus the upstreams: `WowAddonStandards` (`kind=standards`), `LibKa0s` (`kind=library`) and the plugin repo (`kind=tooling`) — `dev-copilot`, plus `wow-addon` for as long as that legacy repo still holds issues. Read the addon roster from `WowAddonStandards/standards/ADDONS.md`; if unreachable, fall back to sibling directories with a `.toc` and **say the roster was inferred** — an inferred roster can silently omit a repo, and a missing repo reads as "nothing here" rather than "not checked".
- **a repo name** → that repo alone, matched case-insensitively against the roster (addons plus the upstreams). No match → say so, list the valid names, and stop. Don't guess at a near-miss.

If the cwd is not a repo `gh` can resolve and no scope was given, **ask** which scope to use rather than guessing.

"Scope order" in the print step is **roster order**: the addons as `ADDONS.md` lists them, then the upstreams.

## row-width — adds

At the collection's roster the longest full issue URL runs to **58 characters**, which is where the worked figures come from — so at the current roster the budget is exactly the base's: **Title ≤ 40, Description ≤ 38**, ~170 per row. When the roster changes (a new addon with a longer name, the tooling repo renamed), recompute the floor rather than carrying 58 forward.

## roster-rule — replaces

- **Don't invent the roster.** Read it from `ADDONS.md` or say plainly that you inferred it.
