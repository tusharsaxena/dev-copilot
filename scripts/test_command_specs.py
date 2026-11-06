#!/usr/bin/env python3
"""Regression tests over the command specs' shell. Run: python3 scripts/test_command_specs.py

Two failures these pin down (FU-DC1, 2026-11-06):

- Claude Code substitutes positional parameters (a dollar sign followed by a digit, braced or not)
  and $ARGUMENTS in every commands/*.md before the model reads it. A shell or awk positional in a
  spec snippet therefore arrives as the user's argument words: wow-revendor-libka0s's Step 0
  `tag_at` helper ran `git -C "Ka0s" show "repos:CLAUDE.md"`. $ARGUMENTS is the intended use.
- The roster in WowAddonStandards/standards/ADDONS.md writes each folder as a backticked
  `../../<Folder>/` table cell, not as a markdown link, so a link-shaped pattern extracts nothing.
"""

import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

POSITIONAL = re.compile(r"\$(\d|\{\d)")

# A fixture copy of ADDONS.md's shape: a few In-scope rows, then the library and the
# documentation-and-tooling tables, whose folders must never be read as addons.
ROSTER_FIXTURE = """\
# Ka0s Addon Roster

## In-scope addons

Paths below are relative to this file (`standards/`).

| Addon | Folder | Repository | Launcher menu entries (launcher-§2) | Skin picker preview (skinning-§10) | Sim mode checkbox (options-ui-§15) |
|---|---|---|---|---|---|
| Ka0s Absorb Tracker | `../../AbsorbTracker/` | https://github.com/tusharsaxena/AbsorbTracker | Enabled · Locked · Sim mode | unlock | next to Lock frame |
| Ka0s Skin Tester | `../../LibKa0sSkinTester/` | https://github.com/tusharsaxena/LibKa0sSkinTester | Enabled · Show window (the skin showroom) | window (the skin showroom) | none |
| Ka0s Outfitter Reborn | `../../OutfitterReborn/` | https://github.com/tusharsaxena/Outfitter | Enabled · Locked (the outfit bar) · Test mode · Show window (the outfit window) | test | none |
| Ka0s Premade Groups Filter Extension | `../../PremadeGroupsFilterExtension/` | https://github.com/tusharsaxena/PremadeGroupsFilterExtension | Enabled · Test mode (the attached panel shown on its own) | test | none |

**The launcher column is normative input to an audit, not decoration.** See `../../NotAnAddon/`.

## Ka0s-owned library repos

| Library repo | Folder | Repository |
|---|---|---|
| LibKa0s | `../../LibKa0s/` | https://github.com/tusharsaxena/LibKa0s |

## Documentation-and-tooling repos

| Repo | Folder | Repository |
|---|---|---|
| WowAddonStandards | `../../WowAddonStandards/` | https://github.com/tusharsaxena/WowAddonStandards |
| dev-copilot | `../../dev-copilot/` | https://github.com/tusharsaxena/dev-copilot |
"""

EXPECTED = ["AbsorbTracker", "LibKa0sSkinTester", "OutfitterReborn", "PremadeGroupsFilterExtension"]


def positional_hits(text):
    """(line number, line) for every positional parameter in text."""
    return [(n, line) for n, line in enumerate(text.splitlines(), 1) if POSITIONAL.search(line)]


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def sh_block_after(text, heading):
    """The first ```sh fence after the line starting with heading."""
    start = text.index(heading)
    fence = text.index("```sh\n", start) + len("```sh\n")
    return text[fence:text.index("```", fence)]


def run_sh(script):
    out = subprocess.run(["sh", "-c", script], capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        raise AssertionError("sh failed (%d): %s" % (out.returncode, out.stderr))
    return out.stdout.split()


class PositionalTest(unittest.TestCase):
    def test_detector_flags_positionals_only(self):
        self.assertTrue(positional_hits('git show "$1:CLAUDE.md"'))
        self.assertTrue(positional_hits("awk '{print $2}'"))
        self.assertTrue(positional_hits('echo "${3}"'))
        self.assertTrue(positional_hits("sh -c 'echo $0' x"))
        self.assertEqual(positional_hits("The `$ARGUMENTS` tokens, in any order"), [])
        self.assertEqual(positional_hits('echo "$a" "${repo}" "$#" "$@" "$rev^"'), [])

    def test_no_command_spec_uses_a_positional(self):
        specs = sorted(glob.glob(os.path.join(ROOT, "commands", "*.md")))
        self.assertTrue(specs, "no commands/*.md found")
        hits = ["%s:%d: %s" % (os.path.relpath(p, ROOT), n, line.strip())
                for p in specs for n, line in positional_hits(read(os.path.relpath(p, ROOT)))]
        self.assertEqual(hits, [], "Claude Code substitutes these with the user's arguments; use a "
                                   "named variable, awk -v, or a script:\n" + "\n".join(hits))


class RosterPatternTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.fixture = os.path.join(self._tmp.name, "ADDONS.md")
        with open(self.fixture, "w", encoding="utf-8") as f:
            f.write(ROSTER_FIXTURE)

    def tearDown(self):
        self._tmp.cleanup()

    def test_revendor_libka0s_step0_roster(self):
        block = sh_block_after(read("commands/wow-revendor-libka0s.md"), "## Step 0")
        lines = block.splitlines()
        start = next(i for i, l in enumerate(lines) if l.startswith("sed -n '/^## In-scope addons/"))
        end = next(i for i in range(start, len(lines)) if "| while read -r a; do" in lines[i])
        pipeline = "\n".join(lines[start:end + 1]).replace("| while read -r a; do", "")
        self.assertIn('"$roster"', pipeline, "Step 0 must read the roster through $roster")
        got = run_sh("roster='%s'\n%s" % (self.fixture, pipeline))
        self.assertEqual(got, EXPECTED)

    def test_agent_review_roster(self):
        lines = read("profiles/wow/agent-review.md").splitlines()
        start = next(i for i, l in enumerate(lines) if l.startswith("set -- $(awk"))
        stmt = [lines[start]]
        while stmt[-1].rstrip().endswith("\\"):
            stmt.append(lines[start + len(stmt)])
        cmd = "\n".join(stmt).replace("WowAddonStandards/standards/ADDONS.md", "'%s'" % self.fixture)
        self.assertNotEqual(cmd, "\n".join(stmt), "agent-review no longer reads ADDONS.md by that path")
        got = run_sh(cmd + '\nprintf "%s\\n" "$@"')
        self.assertEqual(got, EXPECTED)


if __name__ == "__main__":
    if not shutil.which("sh"):
        sys.exit("sh not found")
    unittest.main(verbosity=1)
