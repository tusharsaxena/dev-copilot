#!/usr/bin/env python3
r"""ForeverDB as seed-validation evidence: the newest build tag, and a parsed, cached copy of one tag.

ForeverDB (github.com/foreverfraddons/forever-db, GPL-3.0 data) is the WoW Forever database of
creatures, spawns, vendors, quest givers, trainers and objects: the server-side facts DB2 does not
carry. A seed contract's `forever` flavor may name it as secondary evidence (standard clients-§10).
This script only reads it. Its rows never go into a repo: a seed bundle keeps verdicts and the
sha256 of every file read, and a replay re-fetches the pinned tag, which is immutable.

Usage:
  foreverdb.py status [--json]
      The newest vYYYY.MM.DD.N tag and its commit, from the GitHub tags API (no auth), falling
      back to `git ls-remote --tags`; plus whether that tag is cached.
  foreverdb.py fetch --tag <tag> --date <YYYY-MM-DD> [--from-install <AddOns/ForeverDB dir>]
      Read ForeverDB/ForeverDB.toc and every Lua file it lists, from raw.githubusercontent.com at
      the tag's resolved commit or, read-only, from an installed copy; refuse when the TOC's ## Version is not the
      tag without its `v`; parse the generated Lua; check the npc, item, quest and vend row counts
      against meta.counts; write foreverdb.json and SOURCES.json to
      ${XDG_CACHE_HOME:-~/.cache}/ka0s-seeds/foreverdb/<tag>/ and print that path. A cache whose
      sha256s still match is re-used. An install read and a GitHub fetch of the same tag confirm
      each other in either order (SOURCES.json then records both); a GitHub fetch that finds a
      cached install read is not the tag clears that cache and refuses.
  foreverdb.py get --tag <tag> <table> [<key> ...]
      Print rows of a cached tag as JSON (the whole table when no key is given), for a contract's
      own tools to read. Prints to stdout only; never redirect it into a repo.

foreverdb.json is the ForeverDB global itself: {"meta": {...}, "npc": {...}, ...}. Lua keys become
JSON object keys (a number key 1001 is "1001"); a table whose keys are exactly 1..n is a JSON array,
with a positional nil as null. An empty table, `{}` or one whose every slot is nil, is the JSON object
{}: Lua cannot tell an empty list from an empty map, so a consumer reads a dict-or-list row as
"positional or empty" and never indexes row[0] before checking its length. A string's escapes are
Lua's byte escapes (\ddd and \xHH are single bytes, \u{XXX} its UTF-8 bytes) and the result must be
valid UTF-8, else the read is refused. Exit codes: 0 ok, 1 refused or failed (stderr says why), 2 usage.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

REPO = "foreverfraddons/forever-db"
API_TAGS = "https://api.github.com/repos/" + REPO + "/tags?per_page=100"
GIT_URL = "https://github.com/" + REPO + ".git"
# Built from the tag's resolved commit, not the tag name, so the bytes read are bound to the commit
# that SOURCES.json records even if the tag were ever moved.
RAW = "https://raw.githubusercontent.com/" + REPO + "/{commit}/ForeverDB/{name}"
USER_AGENT = "ka0s-seed-check"
TAG_RE = re.compile(r"^v(\d{4})\.(\d{2})\.(\d{2})\.(\d+)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# The tables whose row count must equal meta.counts. Other counts in meta are not row counts
# (trn counts trainer groups, for example), so they are reported, never enforced.
COUNTED = ("npc", "item", "quest", "vend")
FORMAT = 1  # bump when foreverdb.json's shape changes, so an old cache is rebuilt


class FdbError(Exception):
    """A refusal or failure, printed as one line on stderr."""


# ---------------------------------------------------------------------------------------------
# The Lua reader. ForeverDB's files are generated (tools/slice.py), so the reader covers exactly
# that subset of Lua and raises on anything else, naming the line: a changed format must stop a
# run, not be half-read.

_TOKEN = re.compile(
    r"""(?P<ws>[ \t\r\n]+)
      | (?P<comment>--(?:\[(?P<ceq>=*)\[.*?\](?P=ceq)\]|[^\n]*))
      | (?P<num>-?(?:0[xX][0-9a-fA-F]+|(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?))
      | "(?P<dq>(?:[^"\\\n]|\\.|\\\n)*)"
      | '(?P<sq>(?:[^'\\\n]|\\.|\\\n)*)'
      | (?P<long>\[(?P<leq>=*)\[)
      | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
      | (?P<op>[{}\[\]=,;().])""",
    re.X | re.S)

_ESC = {"n": "\n", "t": "\t", "r": "\r", "a": "\a", "b": "\b", "f": "\f", "v": "\v",
        "\\": "\\", '"': '"', "'": "'", "\n": "\n"}
_ESC_RE = re.compile(r"\\(?:(\d{1,3})|x([0-9a-fA-F]{2})|u\{([0-9a-fA-F]+)\}|z\s*|(.))", re.S)
_KEYWORDS = {"nil", "true", "false", "and", "or", "not", "function", "local", "end", "return",
             "if", "then", "else", "elseif", "for", "while", "do", "repeat", "until", "in",
             "break", "goto"}


def _unescape(body):
    """A quoted string's body with Lua's escapes applied. Lua strings are bytes: \\ddd and \\xHH are
    one byte each and \\u{XXX} is its UTF-8 bytes, so the result is built as bytes and must decode
    as UTF-8 (a misread name would otherwise pass silently as mojibake)."""
    if "\\" not in body:
        return body
    out, pos = bytearray(), 0
    for m in _ESC_RE.finditer(body):
        out += body[pos:m.start()].encode("utf-8")
        pos = m.end()
        dec, hx, uni, other = m.groups()
        if dec is not None:
            n = int(dec)
            if n > 255:
                raise ValueError("decimal escape too large \\" + dec)
            out.append(n)
        elif hx is not None:
            out.append(int(hx, 16))
        elif uni is not None:
            n = int(uni, 16)
            if n > 0x10FFFF:
                raise ValueError("UTF-8 escape too large \\u{" + uni + "}")
            out += chr(n).encode("utf-8", "surrogatepass")
        elif other is None:  # \z skips the whitespace after it
            pass
        elif other in _ESC:
            out += _ESC[other].encode("utf-8")
        else:
            raise ValueError("invalid escape \\" + other)
    out += body[pos:].encode("utf-8")
    try:
        return out.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("string escapes do not form valid UTF-8")


class _Lexer:
    """Tokens as (kind, value): kind is 'num', 'str', 'name' (keywords included) or 'op'."""
    __slots__ = ("text", "pos", "name")

    def __init__(self, text, name):
        self.text, self.pos, self.name = text, 0, name

    def line(self, pos=None):
        return self.text.count("\n", 0, self.pos if pos is None else pos) + 1

    def error(self, msg, pos=None):
        return FdbError("%s:%d: %s" % (self.name, self.line(pos), msg))

    def next(self):
        text, match = self.text, _TOKEN.match
        while True:
            pos = self.pos
            if pos >= len(text):
                return ("eof", None)
            m = match(text, pos)
            if m is None:
                raise self.error("unexpected character %r" % text[pos])
            self.pos = m.end()
            kind = m.lastgroup
            if kind == "op":
                return ("op", m.group("op"))
            if kind == "num":
                s = m.group("num")
                if "x" in s or "X" in s:
                    neg = s.startswith("-")
                    v = int(s.lstrip("-"), 16)
                    return ("num", -v if neg else v)
                if "." in s or "e" in s or "E" in s:
                    return ("num", float(s))
                return ("num", int(s))
            if kind == "name":
                return ("name", m.group("name"))
            if kind == "dq" or kind == "sq":
                try:
                    return ("str", _unescape(m.group(kind)))
                except ValueError as e:
                    raise self.error(str(e), pos)
            if kind == "long":
                close = "]" + m.group("leq") + "]"
                end = text.find(close, self.pos)
                if end < 0:
                    raise self.error("unfinished long string", pos)
                body = text[self.pos:end]
                if body.startswith("\r\n"):
                    body = body[2:]
                elif body.startswith("\n"):
                    body = body[1:]
                self.pos = end + len(close)
                return ("str", body)
            # ws and comment: skip (the regex alternation names the last group matched)
            if kind not in ("ws", "comment", "ceq"):
                raise self.error("unexpected token", pos)


def _finish_table(arr, hsh):
    """A constructor's result: a list when its keys are exactly 1..n, else a dict. An empty
    constructor (or one of nils only) is a dict, so later `t[k] = v` stores into it work."""
    if not hsh:
        if not arr:
            return {}
        while arr and arr[-1] is None:  # a trailing positional nil has no slot in Lua either
            arr.pop()
        return arr if arr else {}
    if arr:
        for i, v in enumerate(arr, 1):
            if v is not None:
                hsh[i] = v
    n = len(hsh)
    if all(isinstance(k, int) and not isinstance(k, bool) for k in hsh) and \
            set(hsh) == set(range(1, n + 1)):
        return [hsh[i] for i in range(1, n + 1)]
    return hsh


class _Reader:
    """Executes one generated ForeverDB file against a shared globals dict."""

    def __init__(self, text, name, env):
        self.lx = _Lexer(text, name)
        self.env = env
        self.scopes = [{}]
        self.tok = self.lx.next()

    # -- token helpers
    def adv(self):
        self.tok = self.lx.next()

    def expect(self, kind, value=None):
        k, v = self.tok
        if k != kind or (value is not None and v != value):
            raise self.lx.error("expected %s, found %r" % (value or kind, v))
        self.adv()
        return v

    def accept(self, value):
        if self.tok[0] in ("op", "name") and self.tok[1] == value:
            self.adv()
            return True
        return False

    # -- values
    def table(self):
        """A table constructor; the opening brace is the current token."""
        self.expect("op", "{")
        arr, hsh = [], {}
        lx = self.lx
        while True:
            k, v = self.tok
            if k == "op" and v == "}":
                self.adv()
                return _finish_table(arr, hsh)
            if k == "op" and v == "[":
                self.adv()
                key = self.value()
                self.expect("op", "]")
                self.expect("op", "=")
                if key is None:
                    raise lx.error("nil table key")
                hsh[key] = self.value()
            elif k == "name" and v not in _KEYWORDS:
                save_pos, save_tok = lx.pos, self.tok
                self.adv()
                if self.tok == ("op", "="):
                    self.adv()
                    hsh[v] = self.value()
                else:
                    lx.pos, self.tok = save_pos, save_tok
                    arr.append(self.value())
            else:
                arr.append(self.value())
            if self.tok[0] == "op" and self.tok[1] in (",", ";"):
                self.adv()
            elif self.tok != ("op", "}"):
                raise lx.error("expected , or } in table, found %r" % (self.tok[1],))

    def value(self):
        """An expression: a literal, a table, a name path, or `a or b`."""
        v = self.simple()
        while self.tok == ("name", "or"):
            self.adv()
            rhs = self.simple()
            if v is None or v is False:
                v = rhs
        return v

    def simple(self):
        k, v = self.tok
        if k == "num" or k == "str":
            self.adv()
            return v
        if k == "op" and v == "{":
            return self.table()
        if k == "name":
            if v == "nil":
                self.adv()
                return None
            if v == "true":
                self.adv()
                return True
            if v == "false":
                self.adv()
                return False
            if v not in _KEYWORDS:
                return self.path_value()
        raise self.lx.error("unsupported expression %r" % (v,))

    def lookup(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return self.env.get(name)

    def path(self):
        """A name followed by .field / [key] steps, as (base name, [keys])."""
        base = self.expect("name")
        keys = []
        while True:
            if self.tok == ("op", "."):
                self.adv()
                keys.append(self.expect("name"))
            elif self.tok == ("op", "["):
                self.adv()
                keys.append(self.value())
                self.expect("op", "]")
            else:
                return base, keys

    def path_value(self):
        base, keys = self.path()
        cur = self.lookup(base)
        for key in keys:
            cur = _index(cur, key, self.lx)
        return cur

    # -- statements
    def run(self):
        while self.tok[0] != "eof":
            self.statement()
        return self.env

    def statement(self):
        k, v = self.tok
        if k == "op" and v == ";":
            self.adv()
            return
        if k == "op" and v == "(":
            self.call_block()
            return
        if k == "name" and v == "local":
            self.adv()
            name = self.expect("name")
            self.expect("op", "=")
            self.scopes[-1][name] = self.value()
            return
        if k == "name" and v not in _KEYWORDS:
            self.assignment()
            return
        raise self.lx.error("unsupported statement %r" % (v,))

    def call_block(self):
        """`(function() <statements> end)()`: run the body at once in its own local scope."""
        self.expect("op", "(")
        self.expect("name", "function")
        self.expect("op", "(")
        self.expect("op", ")")
        self.scopes.append({})
        while self.tok != ("name", "end"):
            if self.tok[0] == "eof":
                raise self.lx.error("unfinished function")
            self.statement()
        self.adv()
        self.scopes.pop()
        self.expect("op", ")")
        self.expect("op", "(")
        self.expect("op", ")")

    def assignment(self):
        base, keys = self.path()
        self.expect("op", "=")
        val = self.value()
        if not keys:
            for scope in reversed(self.scopes):
                if base in scope:
                    scope[base] = val
                    return
            self.env[base] = val
            return
        cur = self.lookup(base)
        for key in keys[:-1]:
            cur = _index(cur, key, self.lx)
        _store(cur, keys[-1], val, self.lx)


def _index(cur, key, lx):
    if isinstance(cur, dict):
        return cur.get(key)
    if isinstance(cur, list):
        if isinstance(key, int) and 1 <= key <= len(cur):
            return cur[key - 1]
        return None
    raise lx.error("index of a non-table value")


def _store(cur, key, val, lx):
    if isinstance(cur, dict):
        if val is None:
            cur.pop(key, None)
        else:
            cur[key] = val
        return
    if isinstance(cur, list) and isinstance(key, int) and 1 <= key <= len(cur) + 1:
        if key == len(cur) + 1:
            cur.append(val)
        else:
            cur[key - 1] = val
        return
    raise lx.error("assignment into a non-table value")


def parse_lua(text, name="<lua>", env=None):
    """Run one generated ForeverDB file; answers the globals dict (shared when env is passed)."""
    if env is None:
        env = {}
    return _Reader(text, name, env).run()


# ---------------------------------------------------------------------------------------------
# Sources, hashes and the cache.

def tag_key(tag):
    m = TAG_RE.match(tag)
    return tuple(int(x) for x in m.groups()) if m else None


def check_tag(tag):
    if not tag_key(tag):
        raise FdbError("bad tag %r: expected vYYYY.MM.DD.N" % tag)


def cache_root():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "ka0s-seeds", "foreverdb")


def cache_dir(tag):
    check_tag(tag)
    return os.path.join(cache_root(), tag)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def sha256_lf(data):
    """The hash of the bytes with CRLF as LF: an installed copy is CRLF, the git tag is LF."""
    return sha256(data.replace(b"\r\n", b"\n"))


def _http_get(url, accept=None):
    """Bytes of a GET, or FdbError. Retries three times on a network error or a 5xx."""
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code < 500:
                raise FdbError("GET %s: HTTP %d" % (url, e.code))
            last = e
        except (urllib.error.URLError, OSError) as e:
            last = e
        time.sleep(1 + attempt)
    raise FdbError("GET %s: %s" % (url, last))


def _ls_remote():
    try:
        r = subprocess.run(["git", "ls-remote", "--tags", GIT_URL], capture_output=True,
                           text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        raise FdbError("git ls-remote failed: %s" % e)
    if r.returncode != 0:
        raise FdbError("git ls-remote failed: %s" % r.stderr.strip())
    tags = {}
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) != 2 or not parts[1].startswith("refs/tags/"):
            continue
        sha, ref = parts
        name = ref[len("refs/tags/"):]
        peeled = name.endswith("^{}")
        name = name[:-3] if peeled else name
        if peeled or name not in tags:  # the peeled line names the commit of an annotated tag
            tags[name] = sha
    return tags


def _api_tags():
    tags, url, pages = {}, API_TAGS, 0
    while url and pages < 20:
        pages += 1
        body = _http_get(url, "application/vnd.github+json")
        try:
            rows = json.loads(body.decode("utf-8"))
        except ValueError:
            raise FdbError("tags API answered something that is not JSON")
        if not isinstance(rows, list):
            raise FdbError("tags API answered %s" % str(rows)[:200])
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("commit"), dict):
                tags[row.get("name")] = row["commit"].get("sha")
        url = API_TAGS + "&page=%d" % (pages + 1) if len(rows) == 100 else None
    return tags


def list_tags():
    """{tag: commit sha} for every vYYYY.MM.DD.N tag, and which source answered."""
    try:
        tags, source = _api_tags(), "api"
    except FdbError as api_err:
        try:
            tags, source = _ls_remote(), "ls-remote"
        except FdbError as git_err:
            raise FdbError("no tag source answered: %s; %s" % (api_err, git_err))
    return {t: s for t, s in tags.items() if t and tag_key(t)}, source


def newest(tags):
    return max(tags, key=tag_key) if tags else None


def parse_toc(data, label):
    """(version, [lua file names]) from a TOC's bytes."""
    text = data.decode("utf-8-sig").replace("\r\n", "\n")
    version, files = None, []
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            continue
        if s.startswith("##"):
            k, _, v = s[2:].partition(":")
            if k.strip() == "Version":
                version = v.strip()
            continue
        if s.startswith("#"):
            continue
        name = s.replace("\\", "/")
        if "/" in name or name.startswith("."):
            raise FdbError("%s lists %r: only flat file names are supported" % (label, s))
        if not name.lower().endswith(".lua"):
            raise FdbError("%s lists %r: only Lua files are supported" % (label, s))
        files.append(name)
    if not files:
        raise FdbError("%s lists no Lua files" % label)
    return version, files


def _write_json(path, obj, compact=False):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        if compact:
            json.dump(obj, f, separators=(",", ":"), ensure_ascii=False)
        else:
            json.dump(obj, f, indent=2, sort_keys=True, ensure_ascii=False)
            f.write("\n")
    os.replace(tmp, path)


def _file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_sources(tag):
    """The cache's SOURCES.json when foreverdb.json still matches it, else None."""
    d = cache_dir(tag)
    try:
        with open(os.path.join(d, "SOURCES.json"), encoding="utf-8") as f:
            src = json.load(f)
        if src.get("format") != FORMAT or src.get("tag") != tag:
            return None
        if _file_sha(os.path.join(d, "foreverdb.json")) != src["json"]["sha256"]:
            return None
        return src
    except (OSError, ValueError, KeyError, TypeError):
        return None


def build(tag, date, blobs, toc_name, origin, commit, urls, install):
    """Parse the blobs ({name: bytes}, TOC first), check them, and write the cache."""
    toc = blobs[toc_name]
    version, lua_files = parse_toc(toc, toc_name)
    env, timings = {}, {}
    for name in lua_files:
        t0 = time.perf_counter()
        text = blobs[name].decode("utf-8")
        parse_lua(text, name, env)
        timings[name] = round(time.perf_counter() - t0, 3)
    db = env.get("ForeverDB")
    if not isinstance(db, dict) or not isinstance(db.get("meta"), dict):
        raise FdbError("the files define no ForeverDB global with a meta table")
    counts = db["meta"].get("counts") if isinstance(db["meta"].get("counts"), dict) else {}
    check, bad = {}, []
    for tbl, want in sorted(counts.items()):
        rows = db.get(tbl)
        got = len(rows) if isinstance(rows, (dict, list)) else None
        check[tbl] = {"meta": want, "parsed": got}
        if tbl in COUNTED and got != want:
            bad.append("%s: meta.counts %s, parsed %s" % (tbl, want, got))
    for tbl in COUNTED:
        if tbl not in counts:
            bad.append("%s: missing from meta.counts" % tbl)
    if bad:
        raise FdbError("row counts disagree with meta.counts (" + "; ".join(bad) + ")")
    d = cache_dir(tag)
    os.makedirs(d, exist_ok=True)
    jpath = os.path.join(d, "foreverdb.json")
    _write_json(jpath, db, compact=True)
    files = []
    for name in [toc_name] + lua_files:
        data = blobs[name]
        files.append({"path": "ForeverDB/" + name, "bytes": len(data), "sha256": sha256(data),
                      "sha256LF": sha256_lf(data)})
    src = {
        "format": FORMAT,
        "tag": tag,
        "commit": commit,
        "date": date,
        "origin": origin,
        "repository": "https://github.com/" + REPO,
        "urls": urls,
        "install": install,
        "tocVersion": version,
        "meta": {k: db["meta"].get(k) for k in ("build", "hash")},
        "files": files,
        "counts": check,
        "parseSeconds": timings,
        "json": {"path": "foreverdb.json", "sha256": _file_sha(jpath)},
    }
    _write_json(os.path.join(d, "SOURCES.json"), src)
    return d, src


def _same_files(src, blobs):
    have = {f["path"]: f.get("sha256LF") for f in src.get("files", [])}
    want = {"ForeverDB/" + n: sha256_lf(b) for n, b in blobs.items()}
    return have == want


def _check_version(version, tag, label):
    if version != tag[1:]:
        raise FdbError("%s says ## Version %s, not %s: refusing" % (label, version, tag[1:]))


def _commit_for(tag):
    """The tag's commit sha, or None when no tag source answers (an offline install read)."""
    try:
        tags, _ = list_tags()
    except FdbError:
        return None
    return tags.get(tag)


def fetch_install(tag, date, install_dir):
    toc_name = "ForeverDB.toc"
    toc_path = os.path.join(install_dir, toc_name)
    try:
        with open(toc_path, "rb") as f:
            toc = f.read()
    except OSError as e:
        raise FdbError("cannot read %s: %s" % (toc_path, e))
    version, lua_files = parse_toc(toc, toc_path)
    _check_version(version, tag, toc_path)
    blobs = {toc_name: toc}
    for name in lua_files:
        try:
            with open(os.path.join(install_dir, name), "rb") as f:
                blobs[name] = f.read()
        except OSError as e:
            raise FdbError("cannot read %s: %s" % (os.path.join(install_dir, name), e))
    install = {"path": os.path.abspath(install_dir), "version": version,
               "sha256": {"ForeverDB/" + n: sha256(b) for n, b in blobs.items()}}
    src = read_sources(tag)
    if src and _same_files(src, blobs):
        if "install" not in src.get("origin", []):
            # A GitHub cache confirmed by this install: record it, so a bundle can name the
            # install's version (the parsed data is unchanged, so foreverdb.json stays).
            src["origin"] = list(src.get("origin", [])) + ["install"]
            src["install"] = install
            _write_json(os.path.join(cache_dir(tag), "SOURCES.json"), src)
        return cache_dir(tag), src, True
    if src and "github" in src.get("origin", []):
        raise FdbError("the install at %s differs from tag %s (CRLF-insensitive sha256): "
                       "it is not that build" % (install_dir, tag))
    d, src = build(tag, date, blobs, toc_name, ["install"], _commit_for(tag), [], install)
    return d, src, False


def fetch_github(tag, date):
    tags, _ = list_tags()
    commit = tags.get(tag)
    if commit is None:
        raise FdbError("tag %s does not exist in %s" % (tag, REPO))
    src = read_sources(tag)
    if src and "github" in src.get("origin", []) and src.get("commit") == commit:
        return cache_dir(tag), src, True
    toc_name = "ForeverDB.toc"
    urls = [RAW.format(commit=commit, name=toc_name)]
    blobs = {toc_name: _http_get(urls[0])}
    version, lua_files = parse_toc(blobs[toc_name], urls[0])
    _check_version(version, tag, urls[0])
    for name in lua_files:
        url = RAW.format(commit=commit, name=name)
        urls.append(url)
        blobs[name] = _http_get(url)
    origin, install = ["github"], None
    if src and "install" in src.get("origin", []):
        if not _same_files(src, blobs):
            # The cached data is not the tag's: stop serving it under the tag's name.
            d = cache_dir(tag)
            for name in ("SOURCES.json", "foreverdb.json"):
                try:
                    os.remove(os.path.join(d, name))
                except OSError:
                    pass
            raise FdbError("the cached install read differs from tag %s (CRLF-insensitive "
                           "sha256): the install is not that build. Cleared the cache at %s; "
                           "fetch again without --from-install to cache the tag" % (tag, d))
        origin, install = ["github", "install"], src.get("install")
    d, src = build(tag, date, blobs, toc_name, origin, commit, urls, install)
    return d, src, False


def load(tag):
    """The cached ForeverDB global as a dict; FdbError when the tag is not cached."""
    if read_sources(tag) is None:
        raise FdbError("tag %s is not cached; run: foreverdb.py fetch --tag %s --date <date>"
                       % (tag, tag))
    with open(os.path.join(cache_dir(tag), "foreverdb.json"), encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------------------------
# CLI

def cmd_status(args):
    tags, source = list_tags()
    tag = newest(tags)
    if tag is None:
        raise FdbError("no vYYYY.MM.DD.N tag found in %s" % REPO)
    cached = read_sources(tag) is not None
    out = {"repository": "https://github.com/" + REPO, "newest": tag, "commit": tags[tag],
           "source": source, "cached": cached, "cachePath": cache_dir(tag)}
    if args.json:
        print(json.dumps(out, indent=2, sort_keys=True))
    else:
        print("newest %s %s (from %s)" % (tag, tags[tag], source))
        print("cache  %s (%s)" % (out["cachePath"], "cached" if cached else "not cached"))
    return 0


def cmd_fetch(args):
    check_tag(args.tag)
    if not DATE_RE.match(args.date):
        raise FdbError("bad date %r: expected YYYY-MM-DD" % args.date)
    if args.from_install:
        d, src, reused = fetch_install(args.tag, args.date, args.from_install)
    else:
        d, src, reused = fetch_github(args.tag, args.date)
    note = "cache re-used" if reused else "parsed %s s" % round(sum(src["parseSeconds"].values()), 2)
    print("%s %s (%s; %s)" % (args.tag, src.get("commit") or "commit unknown",
                             "+".join(src["origin"]), note), file=sys.stderr)
    print(d)
    return 0


def cmd_get(args):
    db = load(args.tag)
    rows = db.get(args.table)
    if rows is None:
        raise FdbError("no table %r in %s" % (args.table, args.tag))
    if not args.keys:
        out = rows
    else:
        out = {}
        for k in args.keys:
            if isinstance(rows, dict):
                out[k] = rows.get(k)
            else:
                out[k] = rows[int(k) - 1] if k.isdigit() and 0 < int(k) <= len(rows) else None
    print(json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="foreverdb.py", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd")
    s = sub.add_parser("status")
    s.add_argument("--json", action="store_true")
    f = sub.add_parser("fetch")
    f.add_argument("--tag", required=True)
    f.add_argument("--date", required=True)
    f.add_argument("--from-install", metavar="DIR")
    g = sub.add_parser("get")
    g.add_argument("--tag", required=True)
    g.add_argument("table")
    g.add_argument("keys", nargs="*")
    args = p.parse_args(argv)
    if not args.cmd:
        p.print_usage(sys.stderr)
        return 2
    try:
        return {"status": cmd_status, "fetch": cmd_fetch, "get": cmd_get}[args.cmd](args)
    except FdbError as e:
        print("foreverdb: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
