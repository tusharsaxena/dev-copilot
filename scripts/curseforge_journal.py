#!/usr/bin/env python3
"""dev-copilot: the CurseForge journal fetcher behind the wow-curseforge-* commands.

Usage (normally through bin/ka0s-curseforge):
  curseforge_journal.py scope    [all | <Addon>...]
  curseforge_journal.py releases [all | <Addon>...] [--dry-run]
  curseforge_journal.py comments [all | <Addon>...] [--dry-run]
  curseforge_journal.py classify <verdicts.json>
  curseforge_journal.py handoff  [all | <Addon>...]
  curseforge_journal.py issue    <Addon> <commentId> <owner/repo#N | declined>
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


class JournalError(Exception):
    pass


def now_ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stamp(ts):
    return ts.replace("-", "").replace(":", "").replace("T", "-").rstrip("Z")


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
    return html_to_md(payload.get("data") if isinstance(payload, dict) else "")


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
        return cls(journal, config, roster, cwd)

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
        if not dry_run:
            out["report"] = self._write_report(ts, "releases", render_releases(out))
            append_lines(os.path.join(self.journal, "runs.jsonl"), [run_line(ts, "releases", out)])
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
                files[key] = {"fileId": f["id"], "fileName": f.get("fileName"), "firstSeen": ts,
                              "changelog": None if dry_run else fetch_changelog(http, pid, f["id"])}
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
            sections.append(render_comment_section(addon["name"], data, run_ts))
        body = "# CurseForge comments — run %s\n\n%s" % (run_ts, "\n".join(sections))
        return {"report": self._write_report(run_ts, "comments", body)}

    def _write_report(self, ts, kind, body):
        path = os.path.join(self.journal, "reports", "%s-%s.md" % (stamp(ts), kind))
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


def render_releases(out):
    lines = ["# CurseForge releases — run %s" % out["ts"], ""]
    for a in out["addons"]:
        lines += ["## %s" % a["name"], "",
                  "Total downloads: %d (%s since the last run)." % (a["totalDownloads"], fmt_delta(a["downloadDelta"]))]
        if a["newFiles"]:
            lines.append("New files: %s." % ", ".join(a["newFiles"]))
        if a["removedFiles"]:
            lines.append("No longer listed: %s." % ", ".join(a["removedFiles"]))
        lines += ["", "| File | Date | Downloads | Change |", "|---|---|---|---|"]
        for f in sorted(a["files"], key=lambda f: f["fileDate"] or "", reverse=True):
            lines.append("| %s | %s | %d | %s |" % (f["displayName"], (f["fileDate"] or "")[:10], f["downloads"],
                                                   fmt_delta(f["delta"])))
        lines.append("")
    for s in out["skipped"]:
        lines.append("Skipped %s: %s." % (s["name"], s["reason"]))
    for e in out["errors"]:
        lines.append("Failed %s: %s." % (e["addon"], e["error"]))
    return "\n".join(lines)


def quote(text, limit=300):
    text = (text or "").strip()
    text = text if len(text) <= limit else text[:limit].rstrip() + "…"
    return "\n".join("> " + l for l in text.split("\n"))


def render_comment_section(name, data, run_ts):
    recs = sorted(data.values(), key=lambda r: r.get("postedAt") or "")
    new = [r for r in recs if r.get("firstSeen") == run_ts]
    edited = [r for r in recs if r.get("editedAt") == run_ts]
    deleted = [r for r in recs if r.get("deletedAt") == run_ts]
    filed = [r for r in recs if (r.get("issueAt") or "") >= run_ts and r.get("issueRef")]
    open_ = [r for r in recs if effective_class(r) in ("bug", "feature") and not r.get("issueRef")
             and not r.get("deleted")]
    lines = ["## %s" % name, "",
             "%d comments on record; this run: %d new, %d edited, %d deleted." % (len(recs), len(new), len(edited),
                                                                                len(deleted)), ""]
    for title, group in (("New", new), ("Edited", edited), ("Deleted", deleted)):
        for r in group:
            who = "owner" if r.get("isOwner") else effective_class(r) or "unclassified"
            lines += ["**%s · %s** — %s, %s" % (title, who, r.get("author"), (r.get("postedAt") or "")[:10]),
                      quote(r.get("text")), ""]
    for r in filed:
        lines.append("Issue for comment %s (%s): %s" % (r["commentId"], r.get("author"), r["issueRef"]))
    if open_:
        lines.append("Bug and feature comments with no issue yet: %d." % len(open_))
    return "\n".join(lines) + "\n"


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
    p = sub.add_parser("report-comments")
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
        else:
            result = ctx.report_comments(args.targets, args.run_ts)
    except JournalError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
