# WoW overlay — issue-add

Applied by `/dev-copilot:issue-add` when `dev-copilot-profile` reports `profile=wow`. The base spec's label set, preflight, input gathering, approval gate, create call and hard rules apply unchanged in every `kind`. This overlay carries what a Ka0s repo adds: the retired ledger, the WoW-shaped severity ladder and `severity:critical` label description, and the TOC as the source of environment facts.

## store-intro — adds

Issues on a Ka0s addon repo are the durable store of pending work — `docs/pending/LEDGER.md` is **retired** and `/dev-copilot:issue-audit` reads and writes this store. Never create, recreate or mirror that ledger.

## severity-ladder — replaces

| Label | Color | Meaning |
|---|---|---|
| `severity:critical` | red `110000` | Taint, combat-lockdown breakage, saved-variable corruption or data loss, an error on a common path |
| `severity:high` | orange `110800` | A user-visible defect, or a Ka0s standard deviation carried from an audit bundle |
| `severity:medium` | yellow `111100` | Maintainability: a stub callers depend on, code/doc drift, a dead path |
| `severity:low` | green `001100` | Polish, naming, cosmetic, speculative-future notes |

The base's title example becomes WoW-shaped: "aura timer flickers on target swap" → `Aura timer flickers when swapping targets`.

## label-set — replaces

Run the base block with one line changed — the eight labels are the **collection labels** and every Ka0s repo carries the same descriptions:

```
gh label create "severity:critical" --color 110000 --description "Taint, lockdown, data loss, common-path error"  --force
```

Every other line of the block, the "only the missing or wrong ones" rule and the spacing stand.

## environment — replaces

  - **bug** → `### Description` · `### Steps to reproduce` · `### Expected` · `### Actual` · `### Environment` (fill in the addon version and `## Interface:` from the TOC if determinable; otherwise leave a clearly-marked blank for the user).
  - **enhancement** → as in the base.

"Repo-derived environment facts" means **TOC-derived** facts.

## no-fabricate — replaces

- **Don't fabricate.** Reproduction steps, versions, and acceptance criteria come from the user or the TOC, never from imagination — mark unknowns `_TBD_`.
