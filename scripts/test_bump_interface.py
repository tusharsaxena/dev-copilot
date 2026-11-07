#!/usr/bin/env python3
"""Tests for scripts/bump_interface.py. Run: python3 scripts/test_bump_interface.py"""

import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
SCRIPT = os.path.join(HERE, "bump_interface.py")


def bump(content, *args):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "A.toc")
        with open(p, "wb") as f:
            f.write(content)
        r = subprocess.run([sys.executable, SCRIPT, p, *args], capture_output=True, text=True)
        with open(p, "rb") as f:
            return r, f.read()


class BumpInterfaceTest(unittest.TestCase):
    def test_bump_interface_dual(self):
        r, out = bump(b"## Title: A\n## Interface: 120105, 16001\n## Version: 1\n",
                      "--retail", "120107")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(out, b"## Title: A\n## Interface: 120107, 16001\n## Version: 1\n")

    def test_bump_interface_retail_only(self):
        r, out = bump(b"## Interface: 120105\n", "--retail", "120107")
        self.assertEqual(out, b"## Interface: 120107\n")

    def test_bump_interface_retail_only_ignores_forever_on_single(self):
        # A single-number line stays single: no Forever slot is invented.
        r, out = bump(b"## Interface: 120105\n", "--retail", "120107", "--forever", "16002")
        self.assertEqual(out, b"## Interface: 120107\n")

    def test_bump_interface_forever_slot(self):
        r, out = bump(b"## Interface: 120105, 16001\n", "--retail", "120105", "--forever", "16002")
        self.assertEqual(out, b"## Interface: 120105, 16002\n")

    def test_bump_interface_forever_slot_order_independent(self):
        r, out = bump(b"## Interface: 16001, 120105\n", "--retail", "120107", "--forever", "16002")
        self.assertEqual(out, b"## Interface: 120107, 16002\n")

    def test_bump_interface_eol_crlf(self):
        r, out = bump(b"## Interface: 120105, 16001\r\n## Version: 1\r\n",
                      "--retail", "120107", "--forever", "16002")
        self.assertEqual(out, b"## Interface: 120107, 16002\r\n## Version: 1\r\n")

    def test_no_interface_line_is_skipped(self):
        r, out = bump(b"## Title: A\n", "--retail", "120107")
        self.assertEqual(r.returncode, 4)
        self.assertEqual(out, b"## Title: A\n")

    def test_rejects_bad_numbers(self):
        r, _ = bump(b"## Interface: 120105\n", "--retail", "16001")
        self.assertEqual(r.returncode, 2)
        r, _ = bump(b"## Interface: 120105, 16001\n", "--retail", "120107", "--forever", "120107")
        self.assertEqual(r.returncode, 2)

    def test_prints_old_and_new(self):
        r, _ = bump(b"## Interface: 120105, 16001\n", "--retail", "120107")
        self.assertEqual(r.stdout.strip(), "120105, 16001 -> 120107, 16001")


if __name__ == "__main__":
    unittest.main()
