#!/usr/bin/env python3
"""Tests for scripts/roster_clients.py. Run: python3 scripts/test_roster_clients.py"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
SCRIPT = os.path.join(HERE, "roster_clients.py")

ROSTER = """# Roster

| Addon | Folder | Repository | Clients | Launcher |
|---|---|---|---|---|
| Ka0s Ported | `../../Ported/` | https://x/Ported | Retail · Forever | Enabled |
| Ka0s WhatGroup | `../../WhatGroup/` | https://x/WhatGroup | Retail | Enabled |
| Ka0s Pending | `../../Pending/` | https://x/Pending | Retail (port pending) | Enabled |
| Ka0s Skill Master | `../../SkillMaster/` | https://x/SkillMaster | Forever | Enabled |
| Ka0s Odd | `../../Odd/` | https://x/Odd | Classic | Enabled |

## Libraries

| Library repo | Folder | Repository |
|---|---|---|
| LibKa0s | `../../LibKa0s/` | https://x/LibKa0s |
"""

NO_CLIENTS = """| Addon | Folder | Repository |
|---|---|---|
| Ka0s Ported | `../../Ported/` | https://x/Ported |
"""


def run(addon, roster_text):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "ADDONS.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write(roster_text)
        return subprocess.run([sys.executable, SCRIPT, addon, "--roster", p],
                              capture_output=True, text=True)


class RosterClientsTest(unittest.TestCase):
    def test_retail_forever(self):
        r = run("Ported", ROSTER)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "retail+forever"))

    def test_retail(self):
        r = run("WhatGroup", ROSTER)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "retail"))

    def test_retail_pending(self):
        r = run("Pending", ROSTER)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "retail-pending"))

    def test_forever(self):
        r = run("SkillMaster", ROSTER)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "forever"))

    def test_unknown_value(self):
        r = run("Odd", ROSTER)
        self.assertEqual(r.returncode, 3)
        self.assertIn("unrecognized Clients value: Classic", r.stderr)

    def test_missing_addon(self):
        self.assertEqual(run("Nope", ROSTER).returncode, 2)

    def test_library_row_is_not_an_addon(self):
        self.assertEqual(run("LibKa0s", ROSTER).returncode, 2)

    def test_missing_clients_column(self):
        r = run("Ported", NO_CLIENTS)
        self.assertEqual(r.returncode, 3)
        self.assertIn("roster has no Clients column", r.stderr + r.stdout)


def git_init(path):
    os.makedirs(path, exist_ok=True)
    subprocess.run(["git", "init", "-q", path], check=True, capture_output=True)


@unittest.skipUnless(shutil.which("git"), "git not found")
class DefaultRosterTest(unittest.TestCase):
    """No --roster: the roster is found from the working directory's repo, not from where the
    script lives, so a copy run from the installed plugin cache still finds it."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = self.tmp.name
        # A plugin cache far from the collection, so the ROOT-relative fallback finds nothing.
        self.script = os.path.join(base, "cache", "dev-copilot", "2.11.0", "scripts", "roster_clients.py")
        os.makedirs(os.path.dirname(self.script))
        shutil.copy(SCRIPT, self.script)
        self.git = os.path.join(base, "GIT")
        self.std = os.path.join(self.git, "WowAddonStandards")
        os.makedirs(os.path.join(self.std, "standards"))
        with open(os.path.join(self.std, "standards", "ADDONS.md"), "w", encoding="utf-8") as f:
            f.write(ROSTER)
        git_init(self.std)
        self.addon = os.path.join(self.git, "SkillMaster")
        git_init(self.addon)
        os.makedirs(os.path.join(self.addon, "docs", "deep"))
        self.env = {k: v for k, v in os.environ.items() if k != "KA0S_GIT"}

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, addon, cwd, *extra, env=None):
        return subprocess.run([sys.executable, self.script, addon, *extra], cwd=cwd,
                              env=env or self.env, capture_output=True, text=True)

    def test_from_the_addon_repo_root(self):
        r = self.call("SkillMaster", self.addon)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "forever"), r.stderr)

    def test_from_a_subdirectory_uses_the_git_toplevel(self):
        r = self.call("Ported", os.path.join(self.addon, "docs", "deep"))
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "retail+forever"), r.stderr)

    def test_from_inside_the_standards_repo(self):
        r = self.call("WhatGroup", os.path.join(self.std, "standards"))
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "retail"), r.stderr)

    def test_ka0s_git_wins_over_the_working_directory(self):
        other = os.path.join(self.tmp.name, "OTHER")
        os.makedirs(os.path.join(other, "WowAddonStandards", "standards"))
        with open(os.path.join(other, "WowAddonStandards", "standards", "ADDONS.md"), "w",
                  encoding="utf-8") as f:
            f.write(ROSTER.replace("| Forever | Enabled |", "| Retail | Enabled |"))
        r = self.call("SkillMaster", self.addon, env=dict(self.env, KA0S_GIT=other))
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "retail"), r.stderr)

    def test_roster_flag_wins_over_everything(self):
        flag = os.path.join(self.tmp.name, "flag.md")
        with open(flag, "w", encoding="utf-8") as f:
            f.write(NO_CLIENTS)
        r = self.call("Ported", self.addon, "--roster", flag, env=dict(self.env, KA0S_GIT=self.git))
        self.assertEqual(r.returncode, 3)

    def test_no_roster_anywhere_names_where_it_looked(self):
        lone = os.path.join(self.tmp.name, "elsewhere", "Lone")
        git_init(lone)
        r = self.call("SkillMaster", lone)
        self.assertEqual(r.returncode, 2)
        self.assertIn("cannot read roster", r.stderr)
        self.assertIn(os.path.join("elsewhere", "WowAddonStandards", "standards", "ADDONS.md"), r.stderr)
        self.assertIn("KA0S_GIT", r.stderr)


if __name__ == "__main__":
    unittest.main()
