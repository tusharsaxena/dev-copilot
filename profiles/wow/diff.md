# WoW overlay — diff

Applied by `/dev-copilot:diff` when `dev-copilot-profile` reports `profile=wow`. Read-only, like the base. Every `kind` takes the same deltas below.

## subject — adds

In a WoW repo the subject is **the addon at the cwd** ("Summarize all uncommitted changes in the addon at the cwd"). If it is not a git repo, tell the user **the addon isn't under git** and stop.

## examples — replaces

Replaces only the **example strings** in Step 3's Files changed, grouping and Likely intent paragraphs — the report structure and order (Last commit, Files changed, Likely intent, Risks, Untracked) stay as the base has them. Use WoW-shaped examples, so the summary speaks the addon's vocabulary:

- **Files changed**: `path/to/file.lua` — `+12 -3` — one-line description of what changed (e.g. "added new aura filter handler", "renamed `ApplyConfig` to `RefreshConfig`").
- **Grouping**: group related changes under a common theme (e.g. "Localization additions across enUS.lua + Core.lua + Settings.lua").
- **Likely intent**: be specific (e.g. "Adding support for tracking interrupts on raid frames" not "Code improvements").

## specificity — replaces

**Be specific in inference.** "Refactored UI" is useless; name the actual frames or functions.

## risks — adds

Add these WoW checks to the base list:

- New events registered but never unregistered (the WoW form of the base's resource-lifecycle check — `RegisterEvent`/`RegisterMessage`/`RegisterCallback`/hooks without a matching unregister/unhook).
- New library/dependency requirements not yet in the TOC (the TOC is the addon's manifest: a new `LibStub("…")` consumer, an embedded lib under `libs/` not listed in the TOC or its aggregate `.xml`, or a missing `## Dependencies`/`## OptionalDeps` entry).
- Version field changed but no other release-coordination changes (CHANGELOG, etc.) — for an addon the version lives in the TOC `## Version:` and in code constants.
- `## Interface:` not bumped if needed.

## untracked — adds

Also flag `.lua.swp` (editor swap files next to Lua sources) and IDE files of any kind as things that shouldn't be committed.
