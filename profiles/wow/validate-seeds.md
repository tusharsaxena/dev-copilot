# validate-seeds — WoW overlay

Applies when the **target** repo detects as `profile=wow`. In the Ka0s collection a seed list is
per client (Ka0s WoW Addon Standard `clients-§5`), and it is derived from, or re-validated
against, that client's own DB2 data on wago.tools (`clients-§10`). So the flavor is a game client,
and the overlay ties the contract's flavors to the client set the roster declares for the addon.
Each section below attaches to the `<!-- overlay: <id> -->` marker of the same id in
`commands/validate-seeds.md`.

### How kind changes this overlay

- **`kind=addon`** — the whole overlay applies.
- **`kind=library`** (LibKa0s) — a library seeds no per-client lists of its own today. If it ever
  ships a contract, apply `gate` and treat `flavor` as the generic spec (the roster does not list a
  library's clients).
- **`kind=standards` / `kind=tooling`** — not applicable: these repos ship no seed data. If one
  carries a contract anyway, follow the generic spec.

## flavor — adds

**A WoW flavor is a client token** from `clients-§1`: `retail` or `forever`. After the contract's
flavor check passes, cross-check it against the roster:

```sh
python3 "<root>/scripts/roster_clients.py" "<target folder name>"
```

`<root>` is the detector's plugin root. The helper ships in the plugin but finds the roster from the working directory, not from where it is installed: run it with the cwd inside the addon repo (any sibling collection checkout works too) and it reads `../WowAddonStandards/standards/ADDONS.md` beside that repo's git top-level; `KA0S_GIT=<GIT dir>` or `--roster <path>` overrides it. The script prints the addon's Clients value from
`WowAddonStandards/standards/ADDONS.md`:

| Clients value | Flavors that may run |
| --- | --- |
| `retail+forever` | `retail`, `forever` |
| `retail` | `retail` |
| `retail-pending` | `retail` (a Forever port is pending, so there is nothing to validate on Forever yet) |
| `forever` | `forever` |

- **The flavor is outside the addon's client set:** stop. Say which clients the roster declares.
  The contract and the roster disagree, so fix one of them first.
- **Exit 2** (the addon is not in the roster) **or 3** (the roster has no Clients column): say so
  in one line and continue on the contract alone.

**The source product follows the client:** wago.tools `wow` for `retail`, `wowf` for `forever`
(`clients-§10`). If the contract's `## Flavors` row names a different product for a client, stop
and say so. A list derived from another client's data is a filtered list in disguise, which
`clients-§5` forbids.

## gate — adds

**Every Lua and lint run goes through the bounded runner**, `~/.claude/dev-copilot/bin/ka0s-bounded`,
exactly as the contract's `## Gate` writes it. The plugin's hook refuses an unbounded `luacheck`,
`lua tests/run.lua` or `lizard`. A run that exits **124** hit the time limit and one that exits
**137** was killed, most likely by the memory limit. Report either as exactly that, never as a test
failure or a pass.

**A `retail+forever` addon runs its headless suite under both kit profiles**,
`lua tests/run.lua` and `KA0S_KIT_CLIENT=forever lua tests/run.lua` (`clients-§6`), whichever
flavor this run validated. A seed file is picked per client at load, and a change to one
client's list can still break the other client's load path. If the contract's `## Gate` lists only
one profile, run both anyway and say so.
