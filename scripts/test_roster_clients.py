#!/usr/bin/env python3
"""Tests for scripts/roster_clients.py. Run: python3 scripts/test_roster_clients.py"""

import os
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

    def test_missing_addon(self):
        self.assertEqual(run("Nope", ROSTER).returncode, 2)

    def test_library_row_is_not_an_addon(self):
        self.assertEqual(run("LibKa0s", ROSTER).returncode, 2)

    def test_missing_clients_column(self):
        r = run("Ported", NO_CLIENTS)
        self.assertEqual(r.returncode, 3)
        self.assertIn("roster has no Clients column", r.stderr + r.stdout)


if __name__ == "__main__":
    unittest.main()
