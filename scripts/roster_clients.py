#!/usr/bin/env python3
"""Print an addon's Clients value from the standard's roster (ADDONS.md).

Usage: roster_clients.py <AddonFolder> [--roster <path>]
Prints retail+forever | retail | retail-pending | forever and exits 0; exits 2 when the
addon is not in the roster, 3 when the roster table has no Clients column.
Roster lookup, first hit wins: --roster <path>; $KA0S_GIT/WowAddonStandards/standards/ADDONS.md;
../WowAddonStandards/standards/ADDONS.md beside the git top-level of the working directory (the
addon repo the command runs in, or any sibling checkout; standards/ADDONS.md when that top-level is
WowAddonStandards itself); last, ../WowAddonStandards/standards/ADDONS.md beside this plugin's own
root, which only a development checkout has (the installed plugin cache does not).
"""

import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

VALUES = {
    "retail · forever": "retail+forever",
    "retail": "retail",
    "retail (port pending)": "retail-pending",
    "forever": "forever",
}


def _toplevel(cwd):
    """The git top-level of cwd, or cwd itself outside git (or without git)."""
    try:
        r = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return cwd
    top = r.stdout.strip()
    return top if r.returncode == 0 and top else cwd


def roster_candidates(cwd=None):
    """Where the roster is looked for, in order (the --roster flag is handled by main)."""
    out = []
    git = os.environ.get("KA0S_GIT")
    if git:
        out.append(os.path.join(git, "WowAddonStandards", "standards", "ADDONS.md"))
    top = _toplevel(os.path.abspath(cwd or os.getcwd()))
    if os.path.basename(top) == "WowAddonStandards":
        out.append(os.path.join(top, "standards", "ADDONS.md"))
    out.append(os.path.normpath(os.path.join(top, "..", "WowAddonStandards", "standards", "ADDONS.md")))
    out.append(os.path.normpath(os.path.join(ROOT, "..", "WowAddonStandards", "standards", "ADDONS.md")))
    seen = []
    for p in out:
        if p not in seen:
            seen.append(p)
    return seen


def default_roster(cwd=None):
    """The first candidate that exists, else None."""
    for p in roster_candidates(cwd):
        if os.path.isfile(p):
            return p
    return None


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def lookup(text, folder):
    """Return (status, value). status is ok, missing or nocolumn."""
    clients_col = None
    seen_addon_table = False
    for line in text.splitlines():
        if not line.startswith("|"):
            clients_col = None
            continue
        c = cells(line)
        if c and c[0] == "Addon" and len(c) > 1 and c[1] == "Folder":
            seen_addon_table = True
            clients_col = c.index("Clients") if "Clients" in c else -1
            continue
        if re.fullmatch(r"[-: |]+", line):
            continue
        if clients_col is None or len(c) < 2:
            continue
        m = re.fullmatch(r"`?\.\./(?:\.\./)?([^/`]+)/?`?", c[1])
        if not m or m.group(1) != folder:
            continue
        if clients_col == -1:
            return "nocolumn", None
        raw = c[clients_col].lower() if clients_col < len(c) else ""
        return "ok", VALUES.get(raw, "unknown:" + c[clients_col])
    if seen_addon_table and clients_col == -1:
        return "nocolumn", None
    return "missing", None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("addon")
    ap.add_argument("--roster")
    a = ap.parse_args(argv)
    path = a.roster or default_roster()
    if path is None:
        print("cannot read roster: no ADDONS.md at any of %s; run from inside a collection "
              "checkout, set KA0S_GIT or pass --roster" % ", ".join(roster_candidates()),
              file=sys.stderr)
        return 2
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print("cannot read roster: %s" % e, file=sys.stderr)
        return 2
    status, value = lookup(text, a.addon)
    if status == "nocolumn":
        print("roster has no Clients column", file=sys.stderr)
        return 3
    if status == "missing":
        print("addon %s is not in the roster" % a.addon, file=sys.stderr)
        return 2
    if value.startswith("unknown:"):
        print("unrecognized Clients value: %s" % value[8:], file=sys.stderr)
        return 3
    print(value)
    return 0


if __name__ == "__main__":
    sys.exit(main())
