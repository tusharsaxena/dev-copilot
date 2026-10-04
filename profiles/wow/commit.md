# WoW overlay — commit

Applied by `/dev-copilot:commit` when `dev-copilot-profile` reports `profile=wow`. The base spec's argument parsing, push flag, plan, commit, push and hard rules apply unchanged in every `kind`; this overlay only widens what counts as an unusual untracked file for a WoW addon tree.

## untracked — adds

In a WoW repo, "the project's normal file types" means **the addon's normal file types** (`.lua`, `.toc`, `.xml`, the addon's docs and tests, and the vendored `libs/` and `tests/_kit/` trees). In addition to the base list, treat these as unusual and **always ask** before staging them:

- `.lua.swp` (and other editor swap/backup files next to Lua sources)
- IDE files of any kind (not just `.idea/`/`.vscode/`)
- large binaries the addon doesn't ship

The rest of the base rule is unchanged: skip any the user declines, and the check applies in every mode including default/auto and when the push flag was given.
