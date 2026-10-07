#!/usr/bin/env python3
"""Tests for scripts/normalize-eol.sh -- run: python3 scripts/test_normalize_eol.py

Each case builds a throwaway git repo with its own .gitattributes, writes a file into it, pipes the
PostToolUse hook JSON into the hook script and compares the bytes left on disk.
"""

import json
import os
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "normalize-eol.sh")

CRLF_PIN = "* text=auto eol=crlf\n"
LF_PIN = "* text=auto eol=lf\n"


def git_env(ceiling):
    """The environment for git and the hook: no user or system config, and no repo above `ceiling`."""
    env = dict(os.environ)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CEILING_DIRECTORIES"] = ceiling
    return env


class Hook(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = os.path.realpath(td.name)
        self.env = git_env(self.root)

    def repo(self, attributes):
        d = os.path.join(self.root, "repo")
        os.makedirs(d)
        subprocess.run(["git", "init", "-q", d], check=True, env=self.env)
        if attributes is not None:
            with open(os.path.join(d, ".gitattributes"), "w", newline="") as f:
                f.write(attributes)
        return d

    def write(self, directory, name, data):
        path = os.path.join(directory, name)
        with open(path, "wb") as f:
            f.write(data)
        return path

    def read(self, path):
        with open(path, "rb") as f:
            return f.read()

    def hook(self, payload):
        p = subprocess.run(["bash", HOOK], input=payload, capture_output=True, text=True,
                           env=self.env, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p

    def run_on(self, path):
        return self.hook(json.dumps({"tool_input": {"file_path": path}}))

    def assertConverted(self, attributes, name, before, after):
        path = self.write(self.repo(attributes), name, before)
        self.run_on(path)
        self.assertEqual(self.read(path), after)

    # ── the CRLF arm ──
    def test_crlf_arm_converts_lf(self):
        self.assertConverted(CRLF_PIN, "a.lua", b"one\ntwo\n", b"one\r\ntwo\r\n")

    def test_crlf_arm_converts_a_mixed_file_completely(self):
        self.assertConverted(CRLF_PIN, "a.lua", b"one\r\ntwo\nthree\r\nfour\n",
                             b"one\r\ntwo\r\nthree\r\nfour\r\n")

    def test_crlf_arm_leaves_a_crlf_file_byte_identical(self):
        self.assertConverted(CRLF_PIN, "a.lua", b"one\r\ntwo\r\n", b"one\r\ntwo\r\n")

    # ── the LF arm ──
    def test_lf_arm_converts_crlf(self):
        self.assertConverted(LF_PIN, "a.md", b"one\r\ntwo\r\n", b"one\ntwo\n")

    def test_lf_arm_leaves_an_lf_file_byte_identical(self):
        self.assertConverted(LF_PIN, "a.md", b"one\ntwo\n", b"one\ntwo\n")

    # ── files the hook must not touch ──
    def test_no_declared_eol_is_untouched(self):
        self.assertConverted("* text=auto\n", "a.lua", b"one\ntwo\r\n", b"one\ntwo\r\n")

    def test_repo_without_gitattributes_is_untouched(self):
        self.assertConverted(None, "a.lua", b"one\ntwo\r\n", b"one\ntwo\r\n")

    def test_binary_in_a_crlf_repo_is_untouched(self):
        # The pin still answers `eol: crlf` for a `binary` file; only the `text` query saves it
        # (line-endings-§7).
        data = b"\x89PNG\r\n\x1a\n\x00\x01\nraw\nbytes\n"
        self.assertConverted(CRLF_PIN + "*.png binary\n", "a.png", data, data)

    def test_minus_text_in_a_crlf_repo_is_untouched(self):
        data = b"one\ntwo\n"
        self.assertConverted(CRLF_PIN + "*.dat -text\n", "a.dat", data, data)

    def test_file_outside_any_repo_is_untouched(self):
        path = self.write(self.root, "loose.lua", b"one\ntwo\r\n")
        self.run_on(path)
        self.assertEqual(self.read(path), b"one\ntwo\r\n")

    # ── inputs with nothing to act on ──
    def test_empty_or_missing_file_path_exits_quietly(self):
        before = sorted(os.listdir(self.root))
        for payload in ("", "not json", "{}", json.dumps({"tool_input": {}}),
                        json.dumps({"tool_input": {"file_path": ""}}),
                        json.dumps({"tool_input": {"file_path": os.path.join(self.root, "absent.lua")}})):
            p = self.hook(payload)
            self.assertEqual(p.stdout, "", payload)
        self.assertEqual(sorted(os.listdir(self.root)), before)

    # ── symlinks ──
    # `perl -i` on a link path would replace the link with a regular file and leave the target
    # unconverted; the hook resolves the link first, so the target's own repo decides.
    def test_symlink_converts_the_target_and_keeps_the_link(self):
        d = self.repo(CRLF_PIN)
        target = self.write(d, "target.lua", b"one\ntwo\n")
        alias = os.path.join(d, "alias.lua")
        os.symlink("target.lua", alias)
        self.run_on(alias)
        self.assertTrue(os.path.islink(alias), "the alias is no longer a symlink")
        self.assertEqual(self.read(target), b"one\r\ntwo\r\n")

    def test_symlink_to_a_file_outside_any_repo_leaves_the_target_untouched(self):
        # The link lives in a CRLF-pinned repo, but the target is outside any repo: the target's
        # location decides, so nothing is rewritten and the link survives.
        d = self.repo(CRLF_PIN)
        outside = os.path.join(self.root, "outside")
        os.makedirs(outside)
        target = self.write(outside, "loose.lua", b"one\ntwo\n")
        alias = os.path.join(d, "alias.lua")
        os.symlink(target, alias)
        self.run_on(alias)
        self.assertTrue(os.path.islink(alias), "the alias is no longer a symlink")
        self.assertEqual(self.read(target), b"one\ntwo\n")


if __name__ == "__main__":
    unittest.main()
