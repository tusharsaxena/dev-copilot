#!/usr/bin/env python3
"""dev-copilot plugin: classify the repository a command is running in.

    dev-copilot-profile [path]        # default: cwd

Prints key=value lines, always in this order:

    profile=wow|generic
    kind=addon|library|standards|tooling|generic
    repo=<repo root, or the path itself outside git>
    name=<basename of repo>
    root=<plugin root>
    reason=<rule that matched>

Shared commands read profiles/wow/<name>.md from `root` when profile=wow. Rules, first match wins,
evaluated at the git top-level:

    override   .dev-copilot file at the root with profile=wow|generic (and optional kind=)
    standards  dir or origin name WowAddonStandards
    tooling    dir or origin name Ka0sAddonsCommonTasks (the cross-repo workspace the collection's
               finalize/issue-*/revendor runs start from); dev-copilot is tooling via its override
    library    dir or origin name LibKa0s, or a root LibKa0s.toc
    addon      a root *.toc with a line starting "## Interface:"
    generic    otherwise
"""

import glob
import os
import subprocess
import sys

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
KEYS = ("profile", "kind", "repo", "name", "root", "reason")
WOW_KINDS = ("addon", "library", "standards", "tooling")
NAMED = (("WowAddonStandards", "standards"), ("Ka0sAddonsCommonTasks", "tooling"),
         ("LibKa0s", "library"))


def _git(path, *args):
    try:
        out = subprocess.run(["git", "-C", path, *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def _origin_name(repo):
    url = _git(repo, "config", "--get", "remote.origin.url").rstrip("/")
    name = url.replace(":", "/").rsplit("/", 1)[-1]
    return name[:-4] if name.endswith(".git") else name


def _read_override(repo):
    path = os.path.join(repo, ".dev-copilot")
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return None
    values = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = (part.strip().lower() for part in line.split("=", 1))
        values[key] = value
    profile = values.get("profile")
    if profile == "generic":
        return "generic", "generic"
    if profile == "wow":
        kind = values.get("kind")
        return "wow", kind if kind in WOW_KINDS else "addon"
    return None


def _has_interface_toc(repo):
    for toc in glob.glob(os.path.join(repo, "*.toc")):
        try:
            with open(toc, encoding="utf-8", errors="replace") as f:
                if any(line.lstrip("﻿").startswith("## Interface:") for line in f):
                    return True
        except OSError:
            continue
    return False


def detect(path=None):
    path = os.path.realpath(path or os.getcwd())
    repo = os.path.realpath(_git(path, "rev-parse", "--show-toplevel") or path)
    result = {"repo": repo, "name": os.path.basename(repo), "root": PLUGIN_ROOT}

    override = _read_override(repo)
    if override:
        result.update(profile=override[0], kind=override[1], reason="override")
        return result

    names = {result["name"], _origin_name(repo)}
    for name, kind in NAMED:
        if name in names:
            result.update(profile="wow", kind=kind, reason="name:" + name)
            return result
    if os.path.isfile(os.path.join(repo, "LibKa0s.toc")):
        result.update(profile="wow", kind="library", reason="toc:LibKa0s.toc")
    elif _has_interface_toc(repo):
        result.update(profile="wow", kind="addon", reason="toc:## Interface")
    else:
        result.update(profile="generic", kind="generic", reason="default")
    return result


def main(argv):
    result = detect(argv[1] if len(argv) > 1 else None)
    for key in KEYS:
        print(f"{key}={result[key]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
