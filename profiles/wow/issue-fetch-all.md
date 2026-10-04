# WoW overlay — issue-fetch-all

Applied by `/dev-copilot:issue-fetch-all` when `dev-copilot-profile` reports `profile=wow`. The base spec's argument parsing, fetch, report table and read-only rules apply unchanged in every `kind`; this overlay only carries the Ka0s store's retired ledger and its WoW-shaped severity ladder.

## store-intro — adds

Issues on a Ka0s addon repo are the durable store of pending work — `docs/pending/LEDGER.md` is **retired** and `/dev-copilot:issue-audit` reads and writes this store.

## severity-ladder — replaces

| Label | Color | Meaning |
|---|---|---|
| `severity:critical` | red `110000` | Taint, combat-lockdown breakage, saved-variable corruption or data loss, an error on a common path |
| `severity:high` | orange `110800` | A user-visible defect, or a Ka0s standard deviation carried from an audit bundle |
| `severity:medium` | yellow `111100` | Maintainability: a stub callers depend on, code/doc drift, a dead path |
| `severity:low` | green `001100` | Polish, naming, cosmetic, speculative-future notes |
