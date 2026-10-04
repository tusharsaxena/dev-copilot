#!/usr/bin/env python3
"""Tests for scripts/check_overlays.py. Run: python3 scripts/test_check_overlays.py"""

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)

import check_overlays  # noqa: E402

STEP0 = "Run `dev-copilot-profile`. If wow, Read `<root>/profiles/wow/{name}.md`.\n"


def write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class CheckTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def errors(self):
        return check_overlays.check(self.root, shared=["diff"])

    def valid(self):
        write(self.root, "commands/diff.md",
              "# diff\n" + STEP0.format(name="diff") + "<!-- overlay: risks -->\n## Risks\n")
        write(self.root, "profiles/wow/diff.md", "Preamble.\n\n## risks — adds\n- events\n\n## extra — adds\nx\n")

    def test_valid_pair(self):
        self.valid()
        self.assertEqual(self.errors(), [])

    def test_unknown_hook_id(self):
        self.valid()
        write(self.root, "profiles/wow/diff.md", "## risky — replaces\nx\n")
        errs = self.errors()
        self.assertEqual(len(errs), 1)
        self.assertIn("risky", errs[0])

    def test_orphan_overlay(self):
        self.valid()
        write(self.root, "profiles/wow/ghost.md", "## a — adds\n")
        self.assertTrue(any("ghost" in e for e in self.errors()))

    def test_base_references_missing_overlay(self):
        write(self.root, "commands/diff.md", STEP0.format(name="diff"))
        self.assertTrue(any("profiles/wow/diff.md" in e for e in self.errors()))

    def test_agent_overlay_maps_to_agent(self):
        self.valid()
        write(self.root, "agents/review.md", STEP0.format(name="agent-review") + "<!-- overlay: out -->\n")
        write(self.root, "profiles/wow/agent-review.md", "## out — replaces\n")
        self.assertEqual(self.errors(), [])

    def test_shared_command_without_step0(self):
        self.valid()
        write(self.root, "commands/diff.md", "# diff\n<!-- overlay: risks -->\n")
        self.assertTrue(any("dev-copilot-profile" in e for e in self.errors()))

    def test_wow_command_without_step0(self):
        self.valid()
        write(self.root, "commands/wow-new-addon.md", "# new addon\n")
        self.assertTrue(any("wow-new-addon" in e for e in self.errors()))

    def test_missing_shared_command(self):
        self.assertTrue(any("commands/diff.md" in e for e in self.errors()))

    def test_bad_heading_suffix(self):
        self.valid()
        write(self.root, "profiles/wow/diff.md", "## risks — appends\n")
        self.assertTrue(any("appends" in e for e in self.errors()))


if __name__ == "__main__":
    unittest.main(verbosity=1)
