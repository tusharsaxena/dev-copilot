#!/usr/bin/env python3
"""Tests for scripts/curseforge_journal.py. Run: python3 scripts/test_curseforge_journal.py

Every payload here is synthetic, shaped like the CurseForge responses the 2026-10-10 spike recorded.
No real CurseForge data belongs in this repo.
"""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)

import curseforge_journal as cj  # noqa: E402

ROSTER = """# Ka0s Addon Roster

## In-scope addons

| Addon | Folder | Repository | Launcher menu entries |
|---|---|---|---|
| Ka0s Alpha | `../../Alpha/` | https://github.com/example/Alpha | Enabled |
| Ka0s Beta | `../../Beta/` | https://github.com/example/Beta | Enabled |
| Ka0s Gamma | `../../Gamma/` | https://github.com/example/Gamma | Enabled |

## Ka0s-owned library repos

| Library repo | Folder | Repository |
|---|---|---|
| LibThing | `../../LibThing/` | https://github.com/example/LibThing |
"""


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read_lines(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def mod(pid, downloads):
    return {"data": {"id": pid, "name": "Ka0s Alpha", "downloadCount": downloads,
                     "links": {"websiteUrl": "https://www.curseforge.com/wow/addons/ka0s-alpha"}}}


def cf_file(fid, name, downloads, date="2026-10-01T10:00:00.5Z"):
    return {"id": fid, "displayName": name, "fileName": "Alpha-%s.zip" % name, "releaseType": 1,
            "fileStatus": 4, "isAvailable": True, "fileDate": date, "downloadCount": downloads,
            "gameVersions": ["12.1.0"]}


def files_page(files, index=0, total=None):
    return {"data": files, "pagination": {"index": index, "pageSize": 50, "resultCount": len(files),
                                          "totalCount": len(files) if total is None else total}}


def comment(cid, user, text, posted=1789904117537, parent=None, replies=()):
    c = {"id": cid, "text": text, "body": "<p>%s</p>" % text, "projectId": 100,
         "author": {"username": user, "displayName": user.title(), "id": 1},
         "datePosted": posted, "status": 1, "isPinned": False, "replies": list(replies)}
    if parent is not None:
        c["parentId"] = parent
    return c


def comments_page(items, total, index=0):
    return {"data": items, "pagination": {"index": index, "totalCount": total, "pageSize": 20}}


class FakeHttp:
    """Answers get_json from a url-substring map and records every call."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get_json(self, url, auth=False):
        self.calls.append((url, auth))
        for needle, payload in self.routes.items():
            if needle in url:
                if isinstance(payload, Exception):
                    raise payload
                return payload
        raise AssertionError("unrouted url " + url)


class Collection(unittest.TestCase):
    """A temp collection: roster, three addons, a journal folder, and a plugin root."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self._tmp.name)
        write(os.path.join(self.root, "WowAddonStandards/standards/ADDONS.md"), ROSTER)
        write(os.path.join(self.root, "Alpha/Alpha.toc"), "## Interface: 120100\n## X-Curse-Project-ID: 100\n")
        write(os.path.join(self.root, "Beta/Beta.toc"), "## Interface: 120100\n## X-Curse-Project-ID: 200\n")
        write(os.path.join(self.root, "Gamma/Gamma.toc"),
              "## Interface: 120100\n# X-Curse-Project-ID: not published yet\n")
        self.journal = os.path.join(self.root, "Ka0sAddonsCommonTasks/journal/curseforge")
        write(os.path.join(self.journal, "journal.config.json"), json.dumps({
            "schemaVersion": 1, "pathsRelativeTo": "repository root",
            "roster": "../WowAddonStandards/standards/ADDONS.md", "ownerAuthor": "TheOwner"}))
        write(os.path.join(self.journal, "runs.jsonl"), "")
        self.env = {cj.JOURNAL_ENV: self.journal}

    def tearDown(self):
        self._tmp.cleanup()

    def ctx(self, cwd=None):
        return cj.Context.load(cwd or self.root, self.env, plugin_root=os.path.join(self.root, "dev-copilot"))


class KeyTest(unittest.TestCase):
    def test_env_wins(self):
        self.assertEqual(cj.read_key({cj.KEY_NAME: "abc"}, "/nonexistent"), "abc")

    def test_file_read_literally_keeps_dollars(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "curseforge.env")
            write(p, "# comment\nCURSEFORGE_API_KEY=$2a$10$abcDEF\n")
            self.assertEqual(cj.read_key({}, p), "$2a$10$abcDEF")

    def test_file_strips_quotes_and_export(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "curseforge.env")
            write(p, "export CURSEFORGE_API_KEY='$2a$x'\r\n")
            self.assertEqual(cj.read_key({}, p), "$2a$x")

    def test_missing_key_is_an_error_without_the_value(self):
        with self.assertRaises(cj.JournalError):
            cj.read_key({}, "/nonexistent/curseforge.env")


class ScopeTest(Collection):
    def test_all_resolves_roster_and_skips_missing_id(self):
        scope = self.ctx().scope(["all"])
        self.assertEqual([a["name"] for a in scope["addons"]], ["Alpha", "Beta"])
        self.assertEqual(scope["addons"][0]["projectId"], 100)
        self.assertEqual([s["name"] for s in scope["skipped"]], ["Gamma"])
        self.assertNotIn("LibThing", json.dumps(scope))

    def test_named_addons_case_insensitive(self):
        scope = self.ctx().scope(["beta"])
        self.assertEqual([a["name"] for a in scope["addons"]], ["Beta"])

    def test_unknown_addon_stops(self):
        with self.assertRaises(cj.JournalError):
            self.ctx().scope(["Alpha", "Outfitter"])

    def test_all_mixed_with_names_stops(self):
        with self.assertRaises(cj.JournalError):
            self.ctx().scope(["all", "Alpha"])

    def test_no_argument_uses_cwd_addon(self):
        subprocess.run(["git", "init", "-q", os.path.join(self.root, "Beta")], check=True)
        scope = self.ctx(cwd=os.path.join(self.root, "Beta")).scope([])
        self.assertEqual([a["name"] for a in scope["addons"]], ["Beta"])

    def test_no_argument_outside_an_addon_stops(self):
        with self.assertRaises(cj.JournalError):
            self.ctx(cwd=self.journal).scope([])


class JournalGuardTest(Collection):
    def test_missing_journal_stops(self):
        self.env[cj.JOURNAL_ENV] = os.path.join(self.root, "nowhere")
        with self.assertRaises(cj.JournalError):
            self.ctx()

    def test_journal_inside_an_addon_is_refused(self):
        inside = os.path.join(self.root, "Alpha/docs/journal")
        write(os.path.join(inside, "journal.config.json"), read_json_text(self.journal))
        self.env[cj.JOURNAL_ENV] = inside
        with self.assertRaises(cj.JournalError):
            self.ctx()

    def test_journal_inside_the_plugin_is_refused(self):
        inside = os.path.join(self.root, "dev-copilot/docs/journal")
        write(os.path.join(inside, "journal.config.json"), read_json_text(self.journal))
        self.env[cj.JOURNAL_ENV] = inside
        with self.assertRaises(cj.JournalError):
            self.ctx()

    def test_default_journal_is_the_sibling_workspace(self):
        del self.env[cj.JOURNAL_ENV]
        self.assertEqual(self.ctx(cwd=os.path.join(self.root, "Alpha")).journal, self.journal)


def read_json_text(journal):
    with open(os.path.join(journal, "journal.config.json"), encoding="utf-8") as f:
        return f.read()


class ReleasesTest(Collection):
    def http(self, files, downloads=50):
        return FakeHttp({"/files?": files_page(files), "/changelog": {"data": "<p>Release <b>1</b></p>"},
                         "/v1/mods/100": mod(100, downloads)})

    def test_first_run_writes_every_file(self):
        ctx = self.ctx()
        out = ctx.releases(["Alpha"], self.http([cf_file(1, "1.0.0", 5), cf_file(2, "1.1.0", 7)]),
                           ts="2026-10-10T00:00:00Z")
        adir = os.path.join(self.journal, "Alpha")
        files = read_json(os.path.join(adir, "files.json"))
        self.assertEqual(sorted(files), ["1", "2"])
        self.assertEqual(files["1"]["changelog"], "Release **1**")
        self.assertIsNone(files["1"]["changelogCommits"])
        self.assertEqual(files["1"]["releaseType"], "release")
        self.assertEqual(len(read_lines(os.path.join(adir, "downloads.jsonl"))), 2)
        self.assertEqual(read_lines(os.path.join(adir, "project.jsonl"))[0]["totalDownloads"], 50)
        self.assertEqual(out["addons"][0]["newFiles"], ["1.0.0", "1.1.0"])
        run = read_lines(os.path.join(self.journal, "runs.jsonl"))[0]
        self.assertEqual(run["command"], "releases")
        self.assertTrue(os.path.isfile(os.path.join(self.journal, "reports", "20261010-000000-releases.md")))

    def test_second_run_only_appends_counts_and_fetches_no_old_changelog(self):
        ctx = self.ctx()
        ctx.releases(["Alpha"], self.http([cf_file(1, "1.0.0", 5)]), ts="2026-10-10T00:00:00Z")
        adir = os.path.join(self.journal, "Alpha")
        before = read_text(os.path.join(adir, "files.json"))
        http = self.http([cf_file(1, "1.0.0", 9)], downloads=60)
        out = ctx.releases(["Alpha"], http, ts="2026-10-11T00:00:00Z")
        self.assertEqual(read_text(os.path.join(adir, "files.json")), before)
        self.assertFalse(any("/changelog" in u for u, _ in http.calls))
        lines = read_lines(os.path.join(adir, "downloads.jsonl"))
        self.assertEqual([x["downloadCount"] for x in lines], [5, 9])
        self.assertEqual(out["addons"][0]["downloadDelta"], 10)
        self.assertEqual(out["addons"][0]["files"][0]["delta"], 4)

    def test_vanished_file_is_marked_removed_not_deleted(self):
        ctx = self.ctx()
        ctx.releases(["Alpha"], self.http([cf_file(1, "1.0.0", 5)]), ts="2026-10-10T00:00:00Z")
        ctx.releases(["Alpha"], self.http([]), ts="2026-10-11T00:00:00Z")
        files = read_json(os.path.join(self.journal, "Alpha", "files.json"))
        self.assertTrue(files["1"]["removed"])

    def test_paginates_files(self):
        http = FakeHttp({"index=0": files_page([cf_file(1, "a", 1)], total=2),
                         "index=1": files_page([cf_file(2, "b", 1)], index=1, total=2)})
        self.assertEqual([f["id"] for f in cj.fetch_files(http, 100)], [1, 2])

    def test_dry_run_writes_nothing(self):
        self.ctx().releases(["Alpha"], self.http([cf_file(1, "1.0.0", 5)]), ts="2026-10-10T00:00:00Z",
                            dry_run=True)
        self.assertFalse(os.path.exists(os.path.join(self.journal, "Alpha")))
        self.assertEqual(read_lines(os.path.join(self.journal, "runs.jsonl")), [])

    def test_one_addon_failing_does_not_stop_the_other(self):
        http = FakeHttp({"/v1/mods/200": cj.JournalError("HTTP 500"),
                         "/files?": files_page([cf_file(1, "1.0.0", 5)]),
                         "/changelog": {"data": ""}, "/v1/mods/100": mod(100, 5)})
        out = self.ctx().releases(["all"], http, ts="2026-10-10T00:00:00Z")
        self.assertEqual([a["name"] for a in out["addons"]], ["Alpha"])
        self.assertEqual(out["errors"][0]["addon"], "Beta")


class CommentsTest(Collection):
    def http(self, *pages):
        routes = {"page=%d&" % i: p for i, p in enumerate(pages)}
        routes["page=%d&" % len(pages)] = comments_page([], 0)
        routes["/v1/mods/100"] = mod(100, 1)
        return FakeHttp(routes)

    def thread_pages(self):
        # Page 0 holds two threads; the second thread's late reply arrives on page 1 at top level,
        # as the real endpoint does when a parent fell on an earlier page.
        reply = comment(12, "TheOwner", "Fixed in 1.1", parent=11)
        nested = comment(13, "carol", "Still broken", parent=12)
        reply["replies"] = [nested]
        p0 = comments_page([comment(11, "alice", "It errors on login", replies=[reply]),
                            comment(20, "bob", "Please add a scale slider")], total=5)
        p1 = comments_page([comment(21, "dave", "Thanks!", parent=20)], total=5, index=1)
        return p0, p1

    def test_flattens_threads_and_dedupes(self):
        p0, p1 = self.thread_pages()
        nodes, total = cj.fetch_comments(self.http(p0, p1, p0), 100)
        self.assertEqual(sorted(nodes), [11, 12, 13, 20, 21])
        self.assertEqual(nodes[13]["parentId"], 12)
        self.assertEqual(total, 5)

    def test_first_run_records_and_lists_pending_without_owner(self):
        p0, p1 = self.thread_pages()
        out = self.ctx().comments(["Alpha"], self.http(p0, p1), ts="2026-10-10T00:00:00Z")
        stored = read_json(os.path.join(self.journal, "Alpha", "comments.json"))
        self.assertTrue(stored["12"]["isOwner"])
        self.assertEqual(stored["11"]["postedAt"], "2026-09-20T11:35:17Z")
        self.assertEqual(stored["11"]["url"], "https://www.curseforge.com/wow/addons/ka0s-alpha/comments")
        pending = {p["commentId"] for p in out["pending"]}
        self.assertEqual(pending, {11, 13, 20, 21})
        self.assertEqual(out["addons"][0]["new"], 5)

    def test_edit_clears_class_and_vanish_marks_deleted(self):
        ctx = self.ctx()
        ctx.comments(["Alpha"], self.http(comments_page([comment(11, "alice", "v1"),
                                                         comment(20, "bob", "hi")], total=2)),
                     ts="2026-10-10T00:00:00Z")
        self.write_verdicts(ctx, [("Alpha", 11, "bug"), ("Alpha", 20, "general")])
        out = ctx.comments(["Alpha"], self.http(comments_page([comment(11, "alice", "v2")], total=1)),
                           ts="2026-10-11T00:00:00Z")
        stored = read_json(os.path.join(self.journal, "Alpha", "comments.json"))
        self.assertEqual(stored["11"]["editedAt"], "2026-10-11T00:00:00Z")
        self.assertIsNone(stored["11"]["class"])
        self.assertTrue(stored["20"]["deleted"])
        self.assertEqual(stored["20"]["class"], "general")
        self.assertEqual([p["commentId"] for p in out["pending"]], [11])

    def test_unchanged_second_run_leaves_comments_file_identical(self):
        ctx = self.ctx()
        page = comments_page([comment(11, "alice", "same")], total=1)
        ctx.comments(["Alpha"], self.http(page), ts="2026-10-10T00:00:00Z")
        path = os.path.join(self.journal, "Alpha", "comments.json")
        before = read_text(path)
        ctx.comments(["Alpha"], self.http(page), ts="2026-10-11T00:00:00Z")
        self.assertEqual(read_text(path), before)

    def test_total_mismatch_is_reported(self):
        out = self.ctx().comments(["Alpha"], self.http(comments_page([comment(11, "a", "x")], total=3)),
                                  ts="2026-10-10T00:00:00Z")
        self.assertIn("totalCount", out["addons"][0]["warnings"][0])

    def write_verdicts(self, ctx, rows, override=None):
        path = os.path.join(self.root, "verdicts.json")
        write(path, json.dumps([{"addon": a, "commentId": c, "class": k, "confidence": 0.9,
                                 "reason": "r"} for a, c, k in rows]))
        return ctx.classify(path)

    def test_classify_respects_override_and_owner(self):
        p0, p1 = self.thread_pages()
        ctx = self.ctx()
        ctx.comments(["Alpha"], self.http(p0, p1), ts="2026-10-10T00:00:00Z")
        path = os.path.join(self.journal, "Alpha", "comments.json")
        data = read_json(path)
        data["20"]["override"] = "feature"
        write(path, json.dumps(data))
        out = self.write_verdicts(ctx, [("Alpha", 11, "bug"), ("Alpha", 12, "bug"),
                                        ("Alpha", 20, "general"), ("Alpha", 21, "nonsense")])
        data = read_json(path)
        self.assertEqual(data["11"]["class"], "bug")
        self.assertIsNone(data["12"]["class"])
        self.assertIsNone(data["20"]["class"])
        self.assertEqual(out["applied"], 1)
        self.assertEqual(len(out["rejected"]), 3)

    def test_handoff_lists_unfiled_bug_and_feature_newest_first(self):
        ctx = self.ctx()
        ctx.comments(["Alpha"], self.http(comments_page([
            comment(11, "alice", "old bug", posted=1000), comment(20, "bob", "new idea", posted=2000),
            comment(30, "eve", "nice", posted=3000)], total=3)), ts="2026-10-10T00:00:00Z")
        self.write_verdicts(ctx, [("Alpha", 11, "bug"), ("Alpha", 20, "feature"), ("Alpha", 30, "feedback")])
        ctx.issue("Alpha", 11, "declined")
        out = ctx.handoff(["Alpha"])
        self.assertEqual([c["commentId"] for c in out["candidates"]], [20])
        self.assertEqual(out["candidates"][0]["repo"], "example/Alpha")

    def test_issue_ref_validated(self):
        ctx = self.ctx()
        ctx.comments(["Alpha"], self.http(comments_page([comment(11, "a", "x")], total=1)),
                     ts="2026-10-10T00:00:00Z")
        ctx.issue("Alpha", 11, "example/Alpha#4")
        self.assertEqual(read_json(os.path.join(self.journal, "Alpha", "comments.json"))["11"]["issueRef"],
                         "example/Alpha#4")
        with self.assertRaises(cj.JournalError):
            ctx.issue("Alpha", 11, "four")
        with self.assertRaises(cj.JournalError):
            ctx.issue("Alpha", 99, "declined")

    def test_report_derives_from_run_stamp(self):
        ctx = self.ctx()
        ctx.comments(["Alpha"], self.http(comments_page([comment(11, "alice", "It errors")], total=1)),
                     ts="2026-10-10T00:00:00Z")
        self.write_verdicts(ctx, [("Alpha", 11, "bug")])
        ctx.issue("Alpha", 11, "example/Alpha#4")
        out = ctx.report_comments(["Alpha"], "2026-10-10T00:00:00Z")
        text = read_text(out["report"])
        self.assertIn("It errors", text)
        self.assertIn("example/Alpha#4", text)
        self.assertTrue(out["report"].endswith("20261010-000000-comments.md"))


PACKAGER_LOG = """tag 0123456789abcdef0123456789abcdef01234567 1.1.0-release
Author: Someone <someone@example.com>
Date:   Fri Oct 9 19:24:19 2026 +0530

Release 1.1.0

commit 1111111111111111111111111111111111111111
Author: Someone <someone@example.com>
Date:   Fri Oct 9 19:20:00 2026 +0530

    Release 1.1.0: version bump

    - A body line that is not kept.

commit 2222222222222222222222222222222222222222
Merge: 3333333 4444444
Author: Someone <someone@example.com>
Date:   Thu Oct 8 10:00:00 2026 +0530

    Merge branch 'feat/x'
"""


class ChangelogSummaryTest(unittest.TestCase):
    def test_packager_log_keeps_one_line_per_commit(self):
        text, count = cj.summarize_changelog(PACKAGER_LOG)
        self.assertEqual(text, "- Release 1.1.0: version bump (1111111)\n- Merge branch 'feat/x' (2222222)")
        self.assertEqual(count, 2)

    def test_a_commit_listed_twice_is_kept_once(self):
        text, count = cj.summarize_changelog(PACKAGER_LOG + "\n" + PACKAGER_LOG)
        self.assertEqual(count, 2)

    def test_hand_written_changelog_is_kept_whole(self):
        self.assertEqual(cj.summarize_changelog("Fixed the bar."), ("Fixed the bar.", None))

    def test_long_hand_written_changelog_is_capped(self):
        text, count = cj.summarize_changelog("x" * (cj.CHANGELOG_CAP + 50))
        self.assertTrue(text.endswith("[truncated]"))
        self.assertLess(len(text), cj.CHANGELOG_CAP + 20)


class HtmlToMarkdownTest(unittest.TestCase):
    def test_changelog_shape(self):
        src = ("<p>tag abc 1.0.0<br>Author:&nbsp; &nbsp; Someone &lt;a@b.c&gt;</p>"
               "<ul><li>One</li><li>Two <a href=\"https://x.y\">link</a></li></ul><h2>Head</h2>")
        self.assertEqual(cj.html_to_md(src),
                         "tag abc 1.0.0\nAuthor:    Someone <a@b.c>\n\n- One\n- Two [link](https://x.y)\n\n## Head")

    def test_empty(self):
        self.assertEqual(cj.html_to_md(""), "")
        self.assertEqual(cj.html_to_md(None), "")


class CliTest(Collection):
    def test_scope_prints_json_and_errors_exit_2(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cj.main(["scope", "all"], env=self.env, cwd=self.root)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(buf.getvalue())["journal"], self.journal)
        err = io.StringIO()
        with redirect_stdout(io.StringIO()):
            sys.stderr, saved = err, sys.stderr
            try:
                code = cj.main(["scope", "Nope"], env=self.env, cwd=self.root)
            finally:
                sys.stderr = saved
        self.assertEqual(code, 2)
        self.assertIn("Nope", err.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=1)
