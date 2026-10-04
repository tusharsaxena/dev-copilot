#!/usr/bin/env python3
"""dev-copilot plugin: check that WoW overlays and the specs they extend still agree.

    python3 scripts/check_overlays.py [plugin-root]

A shared command (commands/<n>.md) or agent (agents/<n>.md) runs `dev-copilot-profile` in its
Step 0 and, in a WoW repo, reads profiles/wow/<n>.md (agent-<n>.md for an agent). The overlay's
`## <id> — adds|replaces` sections attach to `<!-- overlay: <id> -->` markers in the base; an
`## extra — adds` section carries WoW-only steps and needs no marker. This fails when the two drift:
an overlay with no base, a section naming a marker the base lacks, a base pointing at an overlay
that is not there, a heading that is not one of the two forms, or a shared / wow-* command without
the detection step.
"""

import glob
import os
import re
import sys

SHARED = ("diff", "commit", "sync-docs", "review", "run-tests", "bump-version", "finalize",
          "execution-status", "issue-add", "issue-audit", "issue-triage", "issue-details",
          "issue-fetch-all", "issue-summary")
DETECTOR = "dev-copilot-profile"
MARKER = re.compile(r"<!--\s*overlay:\s*([\w.-]+)\s*-->")
HEADING = re.compile(r"^## (.+)$", re.M)
SECTION = re.compile(r"^([\w.-]+) — (adds|replaces)$")
REFERENCE = re.compile(r"profiles/wow/([\w.-]+)\.md")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _base_for(root, overlay_name):
    if overlay_name.startswith("agent-"):
        return os.path.join(root, "agents", overlay_name[len("agent-"):] + ".md")
    return os.path.join(root, "commands", overlay_name + ".md")


def check(root, shared=SHARED):
    errors = []
    rel = lambda p: os.path.relpath(p, root)  # noqa: E731

    for name in shared:
        path = os.path.join(root, "commands", name + ".md")
        if not os.path.isfile(path):
            errors.append(f"commands/{name}.md: shared command missing")
        elif DETECTOR not in _read(path):
            errors.append(f"commands/{name}.md: no `{DETECTOR}` Step 0")
    for path in sorted(glob.glob(os.path.join(root, "commands", "wow-*.md"))):
        if DETECTOR not in _read(path):
            errors.append(f"{rel(path)}: wow-* command has no `{DETECTOR}` Step 0")

    overlays = sorted(glob.glob(os.path.join(root, "profiles", "wow", "*.md")))
    for path in overlays:
        name = os.path.basename(path)[:-3]
        base = _base_for(root, name)
        if not os.path.isfile(base):
            errors.append(f"{rel(path)}: no base spec ({rel(base)})")
            continue
        markers = set(MARKER.findall(_read(base)))
        for heading in HEADING.findall(_read(path)):
            m = SECTION.match(heading.strip())
            if not m:
                errors.append(f"{rel(path)}: heading '## {heading}' is not '<id> — adds|replaces'")
            elif m.group(1) != "extra" and m.group(1) not in markers:
                errors.append(f"{rel(path)}: section '{m.group(1)}' has no "
                              f"<!-- overlay: {m.group(1)} --> marker in {rel(base)}")

    for path in sorted(glob.glob(os.path.join(root, "commands", "*.md")) +
                       glob.glob(os.path.join(root, "agents", "*.md"))):
        for ref in set(REFERENCE.findall(_read(path))):
            if not os.path.isfile(os.path.join(root, "profiles", "wow", ref + ".md")):
                errors.append(f"{rel(path)}: references missing profiles/wow/{ref}.md")
    return errors


def main(argv):
    root = argv[1] if len(argv) > 1 else os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    errors = check(root)
    for e in errors:
        print("ERROR:", e)
    if errors:
        return 1
    print(f"OK: {len(glob.glob(os.path.join(root, 'profiles', 'wow', '*.md')))} overlays")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
