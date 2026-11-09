---
description: Bump the ## Interface line in the current addon's TOC(s) per client slot, the Retail number and, for a ported addon, the WoW Forever number (a Forever-only addon carries the Forever number alone). Operates on this repo only (not recursive). Pass the numbers explicitly, or the command determines the current Live values and asks you to confirm if unsure.
argument-hint: [retail-number] [forever-number] (optional, e.g. 120107 16002, or 16002 alone for a Forever-only addon — omit to use the current Live values)
allowed-tools: [Read, Glob, Grep, Edit, Bash]
---

Bump the `## Interface:` line in the **current addon repo's** TOC file(s) per client slot: the current **Retail / Live Servers** number and, for an addon ported to WoW Forever, the current **Forever** number. A Forever-only addon carries the Forever number and no Retail number. Scope is this one addon — do **not** walk into subdirectories hunting for other addons.

## Before anything — confirm this is a WoW repo

Run `dev-copilot-profile` (Bash; if not found, `"${CLAUDE_PLUGIN_ROOT}/bin/dev-copilot-profile"`). It prints `profile=`, `kind=`, `repo=`, `name=`, `root=`, `reason=`.

- **`profile=generic`** — print exactly this and stop: "`/dev-copilot:wow-bump-interface` is for WoW addon repos; this repo is detected as generic (<reason>). Add a `.dev-copilot` file with `profile=wow` to override." Do nothing else.
- **`profile=wow`** — Continue. A `kind` other than `addon` has no player-facing TOC to bump: say so and stop.

## Resolve the client set

Resolve the addon's Clients value from the roster with the helper, run from the plugin root (`root=` above): `python3 "<root>/scripts/roster_clients.py" <AddonFolder>`, where `<AddonFolder>` is the basename of the repo. It prints one of `retail+forever`, `retail`, `retail-pending` or `forever`. Exit 2 means the addon is not in the roster and exit 3 means the roster has no Clients column or an unknown value: stop and say so, never guess the value.

- **`retail+forever`**: the TOC line carries two numbers, Retail first: `## Interface: <retail>, <forever>`. Both slots are bumped.
- **`retail`** and **`retail-pending`**: the TOC line carries one number and only the Retail slot is bumped. Never add a Forever number.
- **`forever`**: the TOC line carries one number, the Forever one, and only the Forever slot is bumped. Never add a Retail number, and leave the Forever load-gating lines the roster names for this value untouched.

## Resolve the target interface numbers

Interface numbers are `(major * 10000) + (minor * 100) + patch`, so Retail patch 12.1.5 is `120105`. The WoW Forever slot is the 5-digit `16xxx` form: client 1.60.1 is `16001`. As of 2026-11-07 Live Retail is `120105` and Live Forever is `16001`.

1. If `$ARGUMENTS` is non-empty, take the first number as the Retail target and, for a `retail+forever` addon, the second as the Forever target. Validate: Retail is 6 digits and Forever is 5 digits starting `16`. Accept a lone Retail number for a `retail+forever` addon and keep the Forever slot as it stands. For a `forever` addon take the one `16xxx` number as the Forever target; a 6-digit number passed to a `forever` addon is a mistake, so stop and ask. If a format looks wrong, stop and ask.
2. If `$ARGUMENTS` is empty, determine the current Live value of each slot the addon carries (Forever alone for a `forever` addon). **If you are not certain** of one (it changes every patch and your knowledge may be stale), **do not guess**. Ask: *"What are the current Live interface numbers? (Retail, e.g. 120105, and for a ported addon WoW Forever, e.g. 16001)"* and use the answer. A wrong number makes the addon show as out-of-date in-game, so confirming beats guessing.

## Find the TOC(s)

Look for `*.toc` files at the **top level of the current repo only** (the addon root). The standard shape is one unsuffixed TOC (`clients-§2`). Do **not** recurse into subfolders, and skip `libs/`, `Libs/`, `.git/`.

- If there are zero top-level `.toc` files, stop and tell the user this doesn't look like an addon repo root (suggest they `cd` into the addon).
- A per-client TOC (`_Mainline`, `_Forever`, `_Camelot`) is a **forbidden shape** under `clients-§2`: leave it alone and report it as skipped, naming the file, so the audit can flag it. A TOC for any other flavor (`_Vanilla`, `_Cata`, `_Wrath`, `_Mists`) is likewise left alone and reported as skipped.

## Apply

For each remaining TOC run `python3 "<root>/scripts/bump_interface.py" <toc> --retail <N> [--forever <M>]`, or `--forever <M>` alone for a `forever` addon. It rewrites only the `## Interface:` line, writes Retail first, keeps a single-number line single and of its own kind (a Forever-only line never gains a Retail slot), and preserves the file's line endings byte for byte (the `line-endings-§2` rule: a `.toc` sitting LF inside a CRLF-pinned repo is a straggler, and an interface bump must not re-bless it). Exit 4 means there is no `## Interface:` line: leave the file alone and report it as skipped. A two-number line in a `retail`, `retail-pending` or `forever` addon, or a single number of the wrong kind for the Clients value (a 6-digit line in a `forever` addon, a `16xxx` line in a `retail` one), is reported as a finding and not rewritten silently: say so and ask. Exit 2 from the script on a single-number line means the number for its slot was not passed: report it as skipped with the script's message.

If the standard requires the README to carry a supported-clients line for this Clients value, update it to match the new numbers and leave any other README text alone. Check `clients.md` in the standard's section files before editing, and do nothing when it names no such line.

## Report

Print a summary table: `TOC | Old value | New value | Status (updated / unchanged / skipped)`, plus the addon's Clients value. State which numbers were used and how each was resolved (passed as argument / determined as current Live / confirmed by user).

Do **not** commit or stage anything — the user reviews the diff themselves.
