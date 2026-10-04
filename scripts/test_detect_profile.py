#!/usr/bin/env python3
"""Tests for scripts/detect_profile.py. Run: python3 scripts/test_detect_profile.py"""

import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
PLUGIN_ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import detect_profile  # noqa: E402


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def git_init(path, origin=None):
    os.makedirs(path, exist_ok=True)
    subprocess.run(["git", "init", "-q", path], check=True)
    if origin:
        subprocess.run(["git", "-C", path, "remote", "add", "origin", origin], check=True)


class DetectTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = os.path.realpath(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def repo(self, name, origin=None):
        path = os.path.join(self.tmp, name)
        git_init(path, origin)
        return path

    def assertKind(self, path, profile, kind):
        got = detect_profile.detect(path)
        self.assertEqual((got["profile"], got["kind"]), (profile, kind), got)
        return got

    def test_addon(self):
        r = self.repo("Foo")
        write(os.path.join(r, "Foo.toc"), "## Interface: 120000\n## Title: Foo\n")
        self.assertKind(r, "wow", "addon")

    def test_addon_with_crlf_toc(self):
        r = self.repo("Foo")
        write(os.path.join(r, "Foo.toc"), "## Title: Foo\r\n## Interface: 120000\r\n")
        self.assertKind(r, "wow", "addon")

    def test_addon_from_subdir_reports_root(self):
        r = self.repo("Foo")
        write(os.path.join(r, "Foo.toc"), "## Interface: 120000\n")
        sub = os.path.join(r, "modules", "ui")
        os.makedirs(sub)
        got = self.assertKind(sub, "wow", "addon")
        self.assertEqual(got["repo"], r)
        self.assertEqual(got["name"], "Foo")

    def test_toc_without_interface_is_generic(self):
        r = self.repo("Docs")
        write(os.path.join(r, "book.toc"), "Chapter 1\nChapter 2\n")
        self.assertKind(r, "generic", "generic")

    def test_nested_toc_is_generic(self):
        r = self.repo("Monorepo")
        write(os.path.join(r, "vendor", "Foo", "Foo.toc"), "## Interface: 120000\n")
        self.assertKind(r, "generic", "generic")

    def test_library_by_name(self):
        self.assertKind(self.repo("LibKa0s"), "wow", "library")

    def test_library_by_toc(self):
        r = self.repo("checkout")
        write(os.path.join(r, "LibKa0s.toc"), "## Interface: 120000\n")
        self.assertKind(r, "wow", "library")

    def test_standards_by_name(self):
        self.assertKind(self.repo("WowAddonStandards"), "wow", "standards")

    def test_standards_by_origin(self):
        r = self.repo("std", origin="https://github.com/x/WowAddonStandards.git")
        self.assertKind(r, "wow", "standards")

    def test_retired_wow_addon_is_generic(self):
        # The retired wow-addon plugin repo is archived and out of the rotation: no rule names it.
        self.assertKind(self.repo("wow-addon"), "generic", "generic")

    def test_workspace_is_tooling(self):
        r = self.repo("ws", origin="git@github.com:x/Ka0sAddonsCommonTasks.git")
        got = self.assertKind(r, "wow", "tooling")
        self.assertEqual(got["reason"], "name:Ka0sAddonsCommonTasks")

    def test_non_git_dir(self):
        d = os.path.join(self.tmp, "plain")
        os.makedirs(d)
        got = self.assertKind(d, "generic", "generic")
        self.assertEqual(got["repo"], d)

    def test_override_generic(self):
        r = self.repo("Foo")
        write(os.path.join(r, "Foo.toc"), "## Interface: 120000\n")
        write(os.path.join(r, ".dev-copilot"), "# local override\r\nprofile=generic\r\n")
        got = self.assertKind(r, "generic", "generic")
        self.assertEqual(got["reason"], "override")

    def test_override_wow_with_kind(self):
        r = self.repo("thing")
        write(os.path.join(r, ".dev-copilot"), "  profile = wow \nkind=library\n")
        self.assertKind(r, "wow", "library")

    def test_override_wow_without_kind_defaults_addon(self):
        r = self.repo("thing")
        write(os.path.join(r, ".dev-copilot"), "profile=wow\n")
        self.assertKind(r, "wow", "addon")

    def test_root_is_plugin_root(self):
        self.assertEqual(detect_profile.detect(self.tmp)["root"], PLUGIN_ROOT)

    def test_cli_output_shape(self):
        r = self.repo("Foo")
        write(os.path.join(r, "Foo.toc"), "## Interface: 120000\n")
        out = subprocess.run([os.path.join(PLUGIN_ROOT, "bin", "dev-copilot-profile"), r],
                             check=True, capture_output=True, text=True).stdout
        keys = [line.split("=", 1)[0] for line in out.splitlines()]
        self.assertEqual(keys, ["profile", "kind", "repo", "name", "root", "reason"])
        self.assertIn("profile=wow", out.splitlines())


if __name__ == "__main__":
    unittest.main(verbosity=1)
