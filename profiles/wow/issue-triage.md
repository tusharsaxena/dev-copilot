# WoW overlay — issue-triage

Applied by `/dev-copilot:issue-triage` to every repo in scope for which `dev-copilot-profile` reports `profile=wow`, and to the scope step when the cwd (or a checkout under an orchestration folder) is WoW. The base spec's vocabulary, stray repair, resume check (including the legacy journal directory), queue order, one-at-a-time interview, journal-first background writes, reconciliation, report and hard rules apply unchanged in every `kind`. This overlay carries what the Ka0s collection adds: the WoW severity ladder and label description, the collection roster as the `all` scope, audit deviations as the plan items being decided, the harvest that reads `will-not-do` rationales, and the vendored and frozen trees left alone.

## severity-ladder — replaces

| Severity | Label | Color | Meaning |
|---|---|---|---|
| Critical | `severity:critical` | red `110000` | Taint, combat-lockdown breakage, saved-variable corruption or data loss, an error on a common path |
| High | `severity:high` | orange `110800` | A user-visible defect, or a Ka0s standard deviation carried from an audit bundle |
| Medium | `severity:medium` | yellow `111100` | Maintainability: a stub callers depend on, code/doc drift, a dead path |
| Low | `severity:low` | green `001100` | Polish, naming, cosmetic, speculative-future notes |

## scope — replaces

Replaces only the `all` and repo-name bullets; the base's `absent, or here` default stands. The paragraphs after them apply alongside the base's.

- **`all`** → every row of `WowAddonStandards/standards/ADDONS.md`, read rather than hardcoded (folder + repository per row): the *In-scope addons* table, then the *Ka0s-owned library repos* table (`LibKa0s`), then the *Documentation-and-tooling repos* table (`WowAddonStandards`, `dev-copilot`), each in its table's row order. Tag every repo with its kind — `addon` for an addon-table row, `library` for a library-table row, `standards` for `WowAddonStandards` and `tooling` for any other documentation-and-tooling row, the same `kind` `dev-copilot-profile` reports for it. If `ADDONS.md` is unreachable, fall back to the sibling directories next to the cwd that contain a `.toc` (`addon`, except `LibKa0s`) plus the three known upstreams `LibKa0s` (`library`), `WowAddonStandards` (`standards`) and `dev-copilot` (`tooling`), and **say in the report that the roster was inferred** — an inferred roster can silently omit a repo, and a missing repo reads as "nothing here" rather than "not checked".
- **a repo name** → that repo alone, with its kind tag, matched case-insensitively against the same roster (every row, upstreams included). If it matches nothing, say so, list the valid names, and stop. Don't guess at a near-miss.

**What each row gets depends on its kind.** Upstream rows (`library`, `standards`, `tooling`) get the base triage only: this overlay's `resolutions` section, which frames its options around an addon's code and audit bundle, applies on `addon` rows only, and an upstream item is offered the base's resolutions. The collection label set, the severity ladder, the rationale rule and the hard rules apply to every row.

If the cwd is not an addon repo and no scope was given, **ask**. Don't guess.

A roster read from `ADDONS.md` needs no separate list confirmation; the base's "say which repo you're in before its first question" rule is what keeps place on an `all` run. In the journal, `<scope>` is the repo name, or `all` for a collection run.

## label-set — replaces

Run the base block with one line changed — these are the eight **collection labels**, identical on every Ka0s repo:

```
gh label create "severity:critical" --color 110000 --description "Taint, lockdown, data loss, common-path error"  --force
```

Every other line, and the read-`gh label list`-first rule, stand.

## resolutions — replaces

- **2–3 concrete resolutions specific to that item.** Not "fix it" / "don't fix it" — say what fixing it would mean *here*. For a stub: implement it / delete it and its callers / leave it and document the limitation. For an unexecuted audit deviation: apply the remediation the bundle already designed / apply a different fix you describe / accept the deviation.
- **"Keep it open — real work, not now"** — always present, as in the base.
- **"Will not do"** — always present, always last. A permanent close. Say plainly in the option text that it is permanent, and say what stays behind (the `TODO` still sits in the code, the deviation stays in the frozen bundle) so the choice is made with eyes open.

## rationale — adds

For `state:will-not-do` the rationale is also what `/dev-copilot:wow-harvest-standards` mines to find rules the collection has collectively declined — a blank or vague one silently weakens the standard's harvest, not just this repo's record.

## hard-rules — adds

- **Don't touch `libs/`** or any vendored library, and don't edit frozen `docs/audits/` or `docs/reviews/` bundles.
