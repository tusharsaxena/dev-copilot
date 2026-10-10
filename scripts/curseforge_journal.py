#!/usr/bin/env python3
"""dev-copilot: the CurseForge journal fetcher behind the wow-curseforge-* commands.

Usage (normally through bin/ka0s-curseforge):
  curseforge_journal.py scope    [all | <Addon>...]
  curseforge_journal.py releases [all | <Addon>...] [--dry-run]
  curseforge_journal.py comments [all | <Addon>...] [--dry-run]
  curseforge_journal.py classify <verdicts.json>
  curseforge_journal.py handoff  [all | <Addon>...]
  curseforge_journal.py issue    <Addon> <commentId> <owner/repo#N | declined>
  curseforge_journal.py report-releases <run-ts> [all | <Addon>...]
  curseforge_journal.py report-comments <run-ts> [all | <Addon>...]

Every subcommand prints one JSON object. Errors print to stderr and exit 2.

The journal lives outside this plugin, in Ka0sAddonsCommonTasks/journal/curseforge (or
$KA0S_CF_JOURNAL); its README is the schema. This script refuses a journal inside the plugin or inside
any roster addon, because journal data never goes into either. The API key is read from
$CURSEFORGE_API_KEY or ~/.claude/dev-copilot/curseforge.env, literally and never sourced, since the
key holds `$` characters a shell would expand. It is never printed.

Design: docs/superpowers/specs/2026-10-10-curseforge-journal-design.md.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

CORE = "https://api.curseforge.com"
SITE = "https://www.curseforge.com"
KEY_NAME = "CURSEFORGE_API_KEY"
KEY_FILE = os.path.expanduser("~/.claude/dev-copilot/curseforge.env")
JOURNAL_ENV = "KA0S_CF_JOURNAL"
CLASSES = ("bug", "feature", "feedback", "general")
RELEASE_TYPES = {1: "release", 2: "beta", 3: "alpha"}
ISSUE_REF = re.compile(r"^[\w.-]+/[\w.-]+#\d+$")
PAUSE_S = 0.5
COMMENT_PAGE = 20
FILE_PAGE = 50
CHANGELOG_CAP = 4000
COMMIT_LINE = re.compile(r"^commit ([0-9a-f]{7,40})\b")


class JournalError(Exception):
    pass


def now_ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(ts):
    """A journal or API UTC timestamp (`2026-10-09T17:30:24.77Z`) as an aware datetime."""
    return datetime.strptime(re.sub(r"\.\d+", "", ts).rstrip("Z"), "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)


def local_tz(name):
    """The journal's report timezone: `timezone` in journal.config.json, else the machine's own."""
    if not name:
        return datetime.now().astimezone().tzinfo
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception:
        raise JournalError("unknown timezone %r in journal.config.json" % name)


def fmt_local(ts, tz):
    return parse_ts(ts).astimezone(tz).strftime("%Y-%m-%d %H:%M %Z") if ts else "—"


def stamp(ts, tz):
    return parse_ts(ts).astimezone(tz).strftime("%Y%m%d-%H%M%S")


def version_label(display_name):
    return re.sub(r"-release$", "", display_name or "")


def ms_to_ts(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- key, git, files

def read_key(env, path=KEY_FILE):
    value = (env.get(KEY_NAME) or "").strip()
    if value:
        return value
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        raise JournalError("no API key: set %s or create %s" % (KEY_NAME, path))
    for line in lines:
        line = line.strip()
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        if line.startswith(KEY_NAME + "="):
            value = line.split("=", 1)[1].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1]
            if value:
                return value
    raise JournalError("%s has no %s= line" % (path, KEY_NAME))


def git_top(path):
    r = subprocess.run(["git", "-C", path, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return os.path.realpath(r.stdout.strip()) if r.returncode == 0 else None


def is_within(path, parent):
    return path == parent or path.startswith(parent.rstrip(os.sep) + os.sep)


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")


def load_lines(path):
    try:
        with open(path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []


def append_lines(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


# ---------------------------------------------------------------- roster and scope

def parse_roster(path):
    """The `## In-scope addons` table: {name: {"path", "repo"}} in roster order."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        raise JournalError("roster not found: %s" % path)
    section = re.search(r"^## In-scope addons[ \t]*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    roster = {}
    for line in (section.group(1) if section else "").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        folder = re.fullmatch(r"`([^`]+)`", cells[1]) if len(cells) > 2 else None
        if not folder:
            continue
        path_ = os.path.realpath(os.path.join(os.path.dirname(path), folder.group(1)))
        repo = re.search(r"github\.com/([\w.-]+/[\w.-]+)", cells[2])
        roster[os.path.basename(path_)] = {"path": path_, "repo": repo.group(1) if repo else None}
    if not roster:
        raise JournalError("no addons in the In-scope table of %s" % path)
    return roster


def project_id(addon_path, name):
    tocs = [os.path.join(addon_path, name + ".toc")]
    if os.path.isdir(addon_path):
        tocs += sorted(os.path.join(addon_path, f) for f in os.listdir(addon_path) if f.endswith(".toc"))
    for toc in tocs:
        try:
            with open(toc, encoding="utf-8-sig") as f:
                m = re.search(r"^## X-Curse-Project-ID:[ \t]*(\d+)", f.read(), re.M)
        except OSError:
            continue
        if m:
            return int(m.group(1))
    return None


# ---------------------------------------------------------------- HTTP

class Http:
    def __init__(self, key=None, pause=PAUSE_S):
        self.key = key
        self.pause = pause
        self._last = 0.0

    def get_json(self, url, auth=False):
        wait = self._last + self.pause - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        headers = {"Accept": "application/json", "User-Agent": "dev-copilot-curseforge-journal"}
        if auth:
            if not self.key:
                raise JournalError("the CurseForge API key is required")
            headers["x-api-key"] = self.key
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raise JournalError("HTTP %d from %s" % (e.code, url.split("?")[0]))
        except (urllib.error.URLError, ValueError, OSError) as e:
            raise JournalError("request to %s failed: %s" % (url.split("?")[0], e))
        finally:
            self._last = time.monotonic()


def paged(payload, url):
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list) \
            or not isinstance(payload.get("pagination"), dict):
        raise JournalError("unexpected response shape from %s" % url.split("?")[0])
    return payload["data"], payload["pagination"].get("totalCount", 0)


def fetch_mod(http, pid):
    payload = http.get_json("%s/v1/mods/%d" % (CORE, pid), auth=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        raise JournalError("unexpected response shape from /v1/mods/%d" % pid)
    return payload["data"]


def fetch_files(http, pid):
    files, index = [], 0
    while True:
        url = "%s/v1/mods/%d/files?index=%d&pageSize=%d" % (CORE, pid, index, FILE_PAGE)
        data, total = paged(http.get_json(url, auth=True), url)
        files += data
        index += len(data)
        if not data or index >= total:
            return files


def fetch_changelog(http, pid, fid):
    payload = http.get_json("%s/v1/mods/%d/files/%d/changelog" % (CORE, pid, fid), auth=True)
    return summarize_changelog(html_to_md(payload.get("data") if isinstance(payload, dict) else ""))


def summarize_changelog(text):
    """(summary, commitCount). A packager changelog is the full git log since the previous tag, bodies
    included, and the bodies already live in the addon's public history, so only `- subject (sha7)` is
    kept, once per commit (the packager can list one twice). A hand-written changelog has no commit lines and is kept as written, up to CHANGELOG_CAP."""
    lines, out, seen, i = (text or "").split("\n"), [], set(), 0
    while i < len(lines):
        m = COMMIT_LINE.match(lines[i])
        i += 1
        if not m or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        while i < len(lines) and re.match(r"^(Author|Date|Merge|Commit|AuthorDate|CommitDate):", lines[i]):
            i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1
        subject = lines[i].strip() if i < len(lines) and not COMMIT_LINE.match(lines[i]) else ""
        out.append("- %s (%s)" % (subject, m.group(1)[:7]))
    if out:
        return "\n".join(out), len(out)
    text = (text or "").strip()
    return (text if len(text) <= CHANGELOG_CAP else text[:CHANGELOG_CAP].rstrip() + "\n[truncated]"), None


def fetch_comments(http, pid):
    """Walk every page; pages count replies too, and a reply can arrive detached from its parent."""
    nodes, page, total = {}, 0, 0
    while True:
        url = "%s/api/v1/mods/%d/comments?page=%d&size=%d" % (SITE, pid, page, COMMENT_PAGE)
        data, total = paged(http.get_json(url), url)
        if not data:
            return nodes, total
        for c in data:
            flatten_comment(c, None, nodes)
        page += 1
        if len(nodes) >= total:
            return nodes, total


def flatten_comment(c, parent, nodes):
    author = c.get("author") or {}
    nodes[c["id"]] = {
        "commentId": c["id"],
        "parentId": c.get("parentId") or parent,
        "author": author.get("username"),
        "authorDisplay": author.get("displayName"),
        "postedAt": ms_to_ts(c["datePosted"]) if c.get("datePosted") else None,
        "text": clean_text(c.get("text") if c.get("text") is not None else html_to_md(c.get("body"))),
        "pinned": bool(c.get("isPinned")),
    }
    for reply in c.get("replies") or []:
        flatten_comment(reply, c["id"], nodes)


def clean_text(text):
    lines = (text or "").replace("\r\n", "\n").replace("\r", "\n").replace(" ", " ").split("\n")
    return re.sub(r"\n{3,}", "\n\n", "\n".join(l.rstrip() for l in lines)).strip()


# ---------------------------------------------------------------- HTML to markdown

class _Md(HTMLParser):
    BLOCK = {"p", "div", "ul", "ol", "pre", "blockquote", "table"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.href = [], None

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCK:
            self.out.append("\n\n")
        elif tag == "br":
            self.out.append("\n")
        elif tag == "li":
            self.out.append("\n- ")
        elif re.fullmatch(r"h[1-6]", tag):
            self.out.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag in ("strong", "b"):
            self.out.append("**")
        elif tag in ("em", "i"):
            self.out.append("*")
        elif tag == "code":
            self.out.append("`")
        elif tag == "a":
            self.href = dict(attrs).get("href")
            self.out.append("[")

    def handle_endtag(self, tag):
        if tag in self.BLOCK or re.fullmatch(r"h[1-6]", tag):
            self.out.append("\n\n")
        elif tag in ("strong", "b"):
            self.out.append("**")
        elif tag in ("em", "i"):
            self.out.append("*")
        elif tag == "code":
            self.out.append("`")
        elif tag == "a":
            self.out.append("](%s)" % self.href if self.href else "]")
            self.href = None

    def handle_data(self, data):
        self.out.append(data)


def html_to_md(src):
    if not src:
        return ""
    parser = _Md()
    parser.feed(src)
    parser.close()
    return clean_text("".join(parser.out))


# ---------------------------------------------------------------- the journal

class Context:
    def __init__(self, journal, config, roster, cwd):
        self.journal, self.config, self.roster, self.cwd = journal, config, roster, cwd

    @classmethod
    def load(cls, cwd, env, plugin_root=None):
        cwd = os.path.realpath(cwd)
        journal = env.get(JOURNAL_ENV)
        if not journal:
            base = os.path.dirname(git_top(cwd) or cwd)
            journal = os.path.join(base, "Ka0sAddonsCommonTasks", "journal", "curseforge")
        journal = os.path.realpath(journal)
        config = load_json(os.path.join(journal, "journal.config.json"), None)
        if not isinstance(config, dict):
            raise JournalError("no journal at %s (expected journal.config.json); set %s" % (journal, JOURNAL_ENV))
        repo_root = git_top(journal) or os.path.dirname(os.path.dirname(journal))
        roster = parse_roster(os.path.realpath(os.path.join(repo_root, config.get("roster", ""))))
        plugin_root = os.path.realpath(plugin_root or os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
        for forbidden in [plugin_root] + [a["path"] for a in roster.values()]:
            if is_within(journal, forbidden):
                raise JournalError("refusing a journal inside %s: journal data never goes into an addon "
                                   "repo or dev-copilot" % forbidden)
        ctx = cls(journal, config, roster, cwd)
        ctx.tz = local_tz(config.get("timezone"))
        return ctx

    # -- scope

    def scope(self, args):
        lower = {n.lower(): n for n in self.roster}
        if not args:
            top = git_top(self.cwd)
            names = [n for n, a in self.roster.items() if a["path"] == top]
            if not names:
                raise JournalError("the cwd is not a roster addon; name addons or pass `all`")
        elif "all" in args:
            if len(args) > 1:
                raise JournalError("`all` cannot be combined with addon names")
            names = list(self.roster)
        else:
            unknown = [a for a in args if a.lower() not in lower]
            if unknown:
                raise JournalError("not in the roster: %s (roster: %s)" % (", ".join(unknown), ", ".join(self.roster)))
            names = list(dict.fromkeys(lower[a.lower()] for a in args))
        addons, skipped = [], []
        for name in names:
            pid = project_id(self.roster[name]["path"], name)
            entry = {"name": name, "path": self.roster[name]["path"], "repo": self.roster[name]["repo"]}
            if pid is None:
                skipped.append(dict(entry, reason="no ## X-Curse-Project-ID line in the TOC"))
            else:
                addons.append(dict(entry, projectId=pid))
        return {"journal": self.journal, "journalRepo": git_top(self.journal), "addons": addons,
                "skipped": skipped}

    def adir(self, name):
        return os.path.join(self.journal, name)

    def owner(self):
        return (self.config.get("ownerAuthor") or "").lower()

    # -- releases

    def releases(self, args, http, ts=None, dry_run=False):
        ts = ts or now_ts()
        scope = self.scope(args)
        out = {"ts": ts, "dryRun": dry_run, "addons": [], "skipped": scope["skipped"], "errors": []}
        for addon in scope["addons"]:
            try:
                out["addons"].append(self._release_one(addon, http, ts, dry_run))
            except JournalError as e:
                out["errors"].append({"addon": addon["name"], "error": str(e)})
        out["tsLocal"] = fmt_local(ts, self.tz)
        for a in out["addons"]:
            a["sinceLocal"] = fmt_local(a["previousTs"], self.tz) if a["previousTs"] else None
            a["totalChange"] = fmt_delta(a["downloadDelta"])
            newest = max(a["files"], key=lambda f: f["fileDate"] or "", default=None)
            a["latest"] = None if newest is None else {
                "version": version_label(newest["displayName"]), "releaseDate": fmt_local(newest["fileDate"], self.tz),
                "downloads": newest["downloads"], "change": fmt_delta(newest["delta"])}
        if not dry_run:
            append_lines(os.path.join(self.journal, "runs.jsonl"), [run_line(ts, "releases", out)])
            out["report"] = self._render_releases([a["name"] for a in out["addons"]], ts)
        return out

    def _release_one(self, addon, http, ts, dry_run):
        pid, adir = addon["projectId"], self.adir(addon["name"])
        mod = fetch_mod(http, pid)
        api_files = fetch_files(http, pid)
        files = load_json(os.path.join(adir, "files.json"), {})
        last = {}
        for row in load_lines(os.path.join(adir, "downloads.jsonl")):
            last[str(row["fileId"])] = row["downloadCount"]
        projects = load_lines(os.path.join(adir, "project.jsonl"))
        new, rows, summary = [], [], []
        for f in sorted(api_files, key=lambda f: (f.get("fileDate") or "", f["id"])):
            key = str(f["id"])
            if key not in files:
                new.append(f.get("displayName"))
                changelog, commits = (None, None) if dry_run else fetch_changelog(http, pid, f["id"])
                files[key] = {"fileId": f["id"], "fileName": f.get("fileName"), "firstSeen": ts,
                              "changelog": changelog, "changelogCommits": commits}
            files[key].update({"displayName": f.get("displayName"), "fileDate": f.get("fileDate"),
                               "releaseType": RELEASE_TYPES.get(f.get("releaseType"), f.get("releaseType")),
                               "fileStatus": f.get("fileStatus"), "isAvailable": f.get("isAvailable"),
                               "gameVersions": f.get("gameVersions") or [], "removed": False})
            count = f.get("downloadCount", 0)
            rows.append({"ts": ts, "fileId": f["id"], "downloadCount": count})
            prev = last.get(key)
            summary.append({"fileId": f["id"], "displayName": f.get("displayName"), "fileDate": f.get("fileDate"),
                            "downloads": count, "delta": None if prev is None else count - prev})
        present = {str(f["id"]) for f in api_files}
        removed = [rec.get("displayName") for k, rec in files.items() if k not in present and not rec.get("removed")]
        for k, rec in files.items():
            if k not in present:
                rec["removed"] = True
        total = mod.get("downloadCount", 0)
        prev_total = projects[-1]["totalDownloads"] if projects else None
        if not dry_run:
            save_json(os.path.join(adir, "files.json"), files)
            append_lines(os.path.join(adir, "downloads.jsonl"), rows)
            append_lines(os.path.join(adir, "project.jsonl"), [{
                "ts": ts, "projectId": pid, "totalDownloads": total,
                "websiteUrl": (mod.get("links") or {}).get("websiteUrl")}])
        return {"name": addon["name"], "projectId": pid, "totalDownloads": total,
                "previousTs": projects[-1]["ts"] if projects else None,
                "downloadDelta": None if prev_total is None else total - prev_total,
                "newFiles": new, "removedFiles": removed, "files": summary}

    # -- comments

    def comments(self, args, http, ts=None, dry_run=False):
        ts = ts or now_ts()
        scope = self.scope(args)
        out = {"ts": ts, "dryRun": dry_run, "addons": [], "skipped": scope["skipped"], "errors": [], "pending": []}
        for addon in scope["addons"]:
            try:
                result, pending = self._comments_one(addon, http, ts, dry_run)
            except JournalError as e:
                out["errors"].append({"addon": addon["name"], "error": str(e)})
                continue
            out["addons"].append(result)
            out["pending"] += pending
        if not dry_run:
            append_lines(os.path.join(self.journal, "runs.jsonl"), [run_line(ts, "comments", out)])
        return out

    def _comments_one(self, addon, http, ts, dry_run):
        pid, path = addon["projectId"], os.path.join(self.adir(addon["name"]), "comments.json")
        site = (fetch_mod(http, pid).get("links") or {}).get("websiteUrl")
        url = site.rstrip("/") + "/comments" if site else None
        nodes, total = fetch_comments(http, pid)
        stored = load_json(path, {})
        counts = {"new": 0, "edited": 0, "deleted": 0}
        for cid, node in nodes.items():
            rec = stored.get(str(cid))
            if rec is None:
                counts["new"] += 1
                rec = stored[str(cid)] = {"firstSeen": ts, "editedAt": None, "deleted": False, "deletedAt": None,
                                          "class": None, "confidence": None, "reason": None, "classifiedBy": None,
                                          "override": None, "issueRef": None, "issueAt": None}
            elif rec["text"] != node["text"]:
                counts["edited"] += 1
                rec.update({"editedAt": ts, "class": None, "confidence": None, "reason": None, "classifiedBy": None})
            if rec.get("deleted"):
                rec.update({"deleted": False, "deletedAt": None})
            rec.update(node)
            rec["isOwner"] = (node["author"] or "").lower() == self.owner()
            rec["url"] = url or rec.get("url")
        for cid, rec in stored.items():
            if int(cid) not in nodes and not rec.get("deleted"):
                counts["deleted"] += 1
                rec.update({"deleted": True, "deletedAt": ts})
        if not dry_run and (stored or os.path.exists(path)):
            save_json(path, stored)
        warnings = []
        if len(nodes) != total:
            warnings.append("fetched %d unique comments but the page reports totalCount %d" % (len(nodes), total))
        pending = [dict(pending_view(rec, stored), addon=addon["name"]) for rec in stored.values()
                   if needs_class(rec)]
        result = dict(counts, name=addon["name"], projectId=pid, total=len(nodes), warnings=warnings)
        return result, sorted(pending, key=lambda p: p["postedAt"] or "")

    def classify(self, verdicts_path):
        verdicts = load_json(verdicts_path, None)
        if not isinstance(verdicts, list):
            raise JournalError("%s must hold a JSON list of verdicts" % verdicts_path)
        applied, rejected, by_addon = 0, [], {}
        for v in verdicts:
            name = v.get("addon")
            if name not in self.roster:
                rejected.append(dict(v, why="unknown addon"))
                continue
            data = by_addon.setdefault(name, load_json(os.path.join(self.adir(name), "comments.json"), {}))
            rec = data.get(str(v.get("commentId")))
            why = verdict_problem(rec, v.get("class"))
            if why:
                rejected.append(dict(v, why=why))
                continue
            rec.update({"class": v["class"], "confidence": v.get("confidence"), "reason": v.get("reason"),
                        "classifiedBy": v.get("by", "claude")})
            applied += 1
        for name, data in by_addon.items():
            save_json(os.path.join(self.adir(name), "comments.json"), data)
        return {"applied": applied, "rejected": rejected}

    def handoff(self, args):
        candidates = []
        for addon in self.scope(args)["addons"]:
            data = load_json(os.path.join(self.adir(addon["name"]), "comments.json"), {})
            for rec in data.values():
                if effective_class(rec) in ("bug", "feature") and not rec.get("issueRef") \
                        and not rec.get("deleted") and not rec.get("isOwner"):
                    candidates.append(dict(pending_view(rec, data), addon=addon["name"], repo=addon["repo"],
                                           cls=effective_class(rec), reason=rec.get("reason"),
                                           confidence=rec.get("confidence")))
        candidates.sort(key=lambda c: c["postedAt"] or "", reverse=True)
        return {"candidates": candidates}

    def issue(self, name, comment_id, ref):
        if name not in self.roster:
            raise JournalError("not in the roster: %s" % name)
        if ref != "declined" and not ISSUE_REF.match(ref):
            raise JournalError("issue ref must be owner/repo#N or `declined`, got %r" % ref)
        path = os.path.join(self.adir(name), "comments.json")
        data = load_json(path, {})
        rec = data.get(str(comment_id))
        if rec is None:
            raise JournalError("no comment %s in %s" % (comment_id, name))
        rec.update({"issueRef": ref, "issueAt": now_ts()})
        save_json(path, data)
        return {"addon": name, "commentId": int(comment_id), "issueRef": ref}

    def report_comments(self, args, run_ts):
        sections = []
        for addon in self.scope(args)["addons"]:
            data = load_json(os.path.join(self.adir(addon["name"]), "comments.json"), {})
            sections.append(render_comment_section(addon["name"], data, run_ts, self.tz))
        body = "# CurseForge comments — run %s\n\n%s" % (fmt_local(run_ts, self.tz), "\n".join(sections))
        return {"report": self._write_report(run_ts, "comments", body)}

    def report_releases(self, args, run_ts):
        return {"report": self._render_releases([a["name"] for a in self.scope(args)["addons"]], run_ts)}

    def _render_releases(self, names, run_ts):
        """The releases report for one run, derived from the journal alone, so it can be regenerated."""
        addons = [a for a in (self._release_view(n, run_ts) for n in names) if a]
        addons.sort(key=lambda a: a["name"].lower())
        run = next((r for r in load_lines(os.path.join(self.journal, "runs.jsonl"))
                    if r.get("ts") == run_ts and r.get("command") == "releases"), {})
        body = render_releases(addons, run, run_ts, self.tz)
        return self._write_report(run_ts, "releases", body)

    def _release_view(self, name, run_ts):
        adir = self.adir(name)
        projects = load_lines(os.path.join(adir, "project.jsonl"))
        current = [p for p in projects if p["ts"] == run_ts]
        if not current:
            return None
        before = [p for p in projects if p["ts"] < run_ts]
        counts, previous = {}, {}
        for row in load_lines(os.path.join(adir, "downloads.jsonl")):
            if row["ts"] == run_ts:
                counts[row["fileId"]] = row["downloadCount"]
            elif row["ts"] < run_ts:
                previous[row["fileId"]] = row["downloadCount"]
        files = load_json(os.path.join(adir, "files.json"), {})
        rows = []
        for fid, count in counts.items():
            rec = files.get(str(fid), {})
            rows.append({"version": version_label(rec.get("displayName")), "fileDate": rec.get("fileDate"),
                         "downloads": count, "delta": None if fid not in previous else count - previous[fid],
                         "new": rec.get("firstSeen") == run_ts})
        rows.sort(key=lambda r: r["fileDate"] or "", reverse=True)
        total = current[-1]["totalDownloads"]
        prev_total = before[-1]["totalDownloads"] if before else None
        return {"name": name, "total": total, "delta": None if prev_total is None else total - prev_total,
                "since": before[-1]["ts"] if before else None, "files": rows,
                "removed": [version_label(r.get("displayName")) for r in files.values()
                            if r.get("removed") and int(r["fileId"]) not in counts]}

    def _write_report(self, ts, kind, body):
        path = os.path.join(self.journal, "reports", "%s-%s.md" % (stamp(ts, self.tz), kind))
        write_text(path, body.rstrip() + "\n")
        return path


def verdict_problem(rec, cls):
    if rec is None:
        return "unknown comment"
    if rec.get("isOwner"):
        return "owner comment"
    if rec.get("override"):
        return "has an override"
    if cls not in CLASSES:
        return "class must be one of " + "/".join(CLASSES)
    return None


def effective_class(rec):
    return rec.get("override") or rec.get("class")


def needs_class(rec):
    return not rec.get("isOwner") and not rec.get("deleted") and not rec.get("override") and not rec.get("class")


def pending_view(rec, data):
    replies = [r for r in data.values() if r.get("parentId") == rec["commentId"]]
    parent = data.get(str(rec.get("parentId"))) if rec.get("parentId") else None
    return {"commentId": rec["commentId"], "parentId": rec.get("parentId"), "author": rec.get("author"),
            "postedAt": rec.get("postedAt"), "text": rec.get("text"), "url": rec.get("url"),
            "parentText": parent.get("text") if parent else None,
            "ownerReplied": any(r.get("isOwner") for r in replies)}


def run_line(ts, command, out):
    line = {"ts": ts, "command": command, "addons": [a["name"] for a in out["addons"]],
            "skipped": [s["name"] for s in out["skipped"]], "errors": out["errors"]}
    if command == "releases":
        line["newFiles"] = sum(len(a["newFiles"]) for a in out["addons"])
    else:
        for k in ("new", "edited", "deleted"):
            line[k + "Comments"] = sum(a[k] for a in out["addons"])
    return line


def fmt_delta(d):
    return "—" if d is None else "%+d" % d


def render_releases(addons, run, run_ts, tz):
    sinces = {a["since"] for a in addons}
    since = fmt_local(next(iter(sinces)), tz) if len(sinces) == 1 and None not in sinces else None
    head = "Changes since %s" % since if since else "Changes since last run"
    lines = ["# CurseForge releases — run %s" % fmt_local(run_ts, tz), "",
             "| Addon | Version | Release Date | Downloads | %s |" % head, "|---|---|---|---:|---|"]
    for a in addons:
        lines.append("| %s | Total | - | %d | %s |" % (a["name"], a["total"], fmt_delta(a["delta"])))
        for f in a["files"]:
            lines.append("|  | %s | %s | %d | %s |" % (f["version"], fmt_local(f["fileDate"], tz), f["downloads"],
                                                      fmt_delta(f["delta"])))
    lines.append("")
    if not since and len(sinces - {None}) > 1:
        lines.append("Each addon's change is since its own previous run: %s." % "; ".join(
            "%s %s" % (a["name"], fmt_local(a["since"], tz) if a["since"] else "first run") for a in addons))
    new = ["%s %s" % (a["name"], f["version"]) for a in addons for f in a["files"] if f["new"] and a["since"]]
    if new:
        lines.append("New this run: %s." % "; ".join(new))
    removed = ["%s %s" % (a["name"], v) for a in addons for v in a["removed"]]
    if removed:
        lines.append("No longer listed: %s." % "; ".join(removed))
    for name in run.get("skipped") or []:
        lines.append("Skipped %s: no ## X-Curse-Project-ID line in the TOC." % name)
    for e in run.get("errors") or []:
        lines.append("Failed %s: %s." % (e["addon"], e["error"]))
    return "\n".join(lines)


SNIPPET = 200
MEMBERS = SITE + "/members/"


def author_link(name):
    """CurseForge has no per-comment URL, so a node links its author's profile instead."""
    return "[%s](%s%s)" % (name, MEMBERS, urllib.parse.quote(name or "")) if name else "?"


def issue_link(ref):
    """`owner/repo#N` as a real GitHub link, labelled `repo#N`."""
    repo, num = ref.rsplit("#", 1)
    return "[%s#%s](https://github.com/%s/issues/%s)" % (repo.split("/")[-1], num, repo, num)


def snippet(text, limit=SNIPPET):
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def node_tags(rec, run_ts):
    tags = ["owner" if rec.get("isOwner") else effective_class(rec) or "unclassified"]
    if rec.get("firstSeen") == run_ts:
        tags.append("new")
    if rec.get("editedAt") == run_ts:
        tags.append("edited")
    if rec.get("deleted"):
        tags.append("deleted")
    if rec.get("issueRef") == "declined":
        tags.append("issue declined")
    elif rec.get("issueRef"):
        tags.append("issue " + issue_link(rec["issueRef"]))
    return tags


def render_comment_section(name, data, run_ts, tz):
    """One addon's comments as conversation trees: every thread on record, newest thread first, each
    reply nested under the comment it answers, oldest reply first."""
    recs = list(data.values())
    children = {}
    for r in recs:
        parent = r.get("parentId")
        children.setdefault(parent if str(parent) in data else None, []).append(r)
    by_date = lambda r: (r.get("postedAt") or "", r["commentId"])
    lines = []

    def walk(rec, depth):
        lines.append("%s- [%s %s] %s _(%s)_" % ("  " * depth, author_link(rec.get("author")),
                                             fmt_local(rec.get("postedAt"), tz),
                                             snippet(rec.get("text")), ", ".join(node_tags(rec, run_ts))))
        for child in sorted(children.get(rec["commentId"], []), key=by_date):
            walk(child, depth + 1)

    for root in sorted(children.get(None, []), key=by_date, reverse=True):
        walk(root, 0)
    count = lambda key: sum(1 for r in recs if r.get(key) == run_ts)
    page = next((r["url"] for r in recs if r.get("url")), None)
    head = ["## %s — [CurseForge comments](%s)" % (name, page) if page else "## %s" % name, "",
            "%d comments on record; this run: %d new, %d edited, %d deleted." % (
                len(recs), count("firstSeen"), count("editedAt"), count("deletedAt")), ""]
    open_ = [r for r in recs if effective_class(r) in ("bug", "feature") and not r.get("issueRef")
             and not r.get("deleted")]
    tail = [""] + (["Bug and feature comments with no issue yet: %d." % len(open_)] if open_ else [])
    return "\n".join(head + (lines or ["No comments on record."]) + tail) + "\n"


# ---------------------------------------------------------------- CLI

def main(argv=None, env=None, cwd=None):
    env = os.environ if env is None else env
    parser = argparse.ArgumentParser(prog="ka0s-curseforge")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("scope", "releases", "comments", "handoff"):
        p = sub.add_parser(name)
        p.add_argument("targets", nargs="*")
        if name in ("releases", "comments"):
            p.add_argument("--dry-run", action="store_true")
    sub.add_parser("classify").add_argument("verdicts")
    p = sub.add_parser("issue")
    p.add_argument("addon")
    p.add_argument("comment_id", type=int)
    p.add_argument("ref")
    for name in ("report-comments", "report-releases"):
        p = sub.add_parser(name)
        p.add_argument("run_ts")
        p.add_argument("targets", nargs="*")
    args = parser.parse_args(argv)
    try:
        ctx = Context.load(cwd or os.getcwd(), env)
        if args.cmd == "scope":
            result = ctx.scope(args.targets)
        elif args.cmd == "releases":
            result = ctx.releases(args.targets, Http(read_key(env)), dry_run=args.dry_run)
        elif args.cmd == "comments":
            result = ctx.comments(args.targets, Http(read_key(env)), dry_run=args.dry_run)
        elif args.cmd == "classify":
            result = ctx.classify(args.verdicts)
        elif args.cmd == "handoff":
            result = ctx.handoff(args.targets)
        elif args.cmd == "issue":
            result = ctx.issue(args.addon, args.comment_id, args.ref)
        elif args.cmd == "report-releases":
            result = ctx.report_releases(args.targets, args.run_ts)
        else:
            result = ctx.report_comments(args.targets, args.run_ts)
    except JournalError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
