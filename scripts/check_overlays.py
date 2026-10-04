#!/usr/bin/env python3
"""dev-copilot plugin: check that WoW overlays and the specs they extend still agree.

    python3 scripts/check_overlays.py [plugin-root]

A shared command (commands/<n>.md) or agent (agents/<n>.md) runs `dev-copilot-profile` in its
Step 0 and, in a WoW repo, reads profiles/wow/<n>.md (agent-<n>.md for an agent). The overlay's
`## <id> — adds|replaces` sections attach to `<!-- overlay: <id> -->` markers in the base; an
`## extra — adds` section carries WoW-only steps and needs no marker. This fails when the two drift:
an overlay with no base, a section naming a marker the base lacks, a marker no section uses, a
duplicate marker or section id, an `extra` that replaces, a base pointing at an overlay that is not
there or is not its own, a heading that is not one of the two forms, a shared / wow-* command
without the detection step, or a base whose Step 0 is not the verbatim block (STEP0_BLOCK) naming
its own overlay.
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
# The Step 0 every overlay-bearing base carries word for word; only the overlay name differs.
STEP0_BLOCK = """## Step 0 — Detect the repo profile

Run `dev-copilot-profile` (Bash; if not found, `"${{CLAUDE_PLUGIN_ROOT}}/bin/dev-copilot-profile"`). \
It prints `profile=`, `kind=`, `repo=`, `name=`, `root=`, `reason=`.

- **`profile=wow`** — Read `<root>/profiles/wow/{overlay}.md` now. Each of its sections names a hook \
point in this spec (`<!-- overlay: <id> -->`) and says whether it **adds to** or **replaces** that \
section; `extra` sections say where they run. Apply them as you go. `kind` (`addon`, `library`, \
`standards`, `tooling`) refines WoW behavior where the overlay says so.
- **`profile=generic`** — follow this spec as written. Do not read the overlay.
- **Neither invocation works** (no detector on PATH, and no plugin root substituted) — treat the \
repo as `profile=generic`, say so in one line, and do not read any overlay.
"""


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
        base_text = _read(base)
        if STEP0_BLOCK.format(overlay=name) not in base_text:
            errors.append(f"{rel(base)}: Step 0 is not the verbatim block naming "
                          f"profiles/wow/{name}.md (see STEP0_BLOCK)")
        found = MARKER.findall(base_text)
        markers = set(found)
        for dup in sorted(m for m in markers if found.count(m) > 1):
            errors.append(f"{rel(base)}: marker '{dup}' appears {found.count(dup)} times")
        used = []
        for heading in HEADING.findall(_read(path)):
            m = SECTION.match(heading.strip())
            if not m:
                errors.append(f"{rel(path)}: heading '## {heading}' is not '<id> — adds|replaces'")
            elif m.group(1) == "extra":
                if m.group(2) != "adds":
                    errors.append(f"{rel(path)}: '## extra' may only add, not replace")
            elif m.group(1) not in markers:
                errors.append(f"{rel(path)}: section '{m.group(1)}' has no "
                              f"<!-- overlay: {m.group(1)} --> marker in {rel(base)}")
            else:
                if m.group(1) in used:
                    errors.append(f"{rel(path)}: section '{m.group(1)}' appears more than once")
                used.append(m.group(1))
        for unused in sorted(markers - set(used)):
            errors.append(f"{rel(base)}: marker '{unused}' has no section in {rel(path)}")

    for path in sorted(glob.glob(os.path.join(root, "commands", "*.md")) +
                       glob.glob(os.path.join(root, "agents", "*.md"))):
        own = os.path.basename(path)[:-3]
        if os.path.basename(os.path.dirname(path)) == "agents":
            own = "agent-" + own
        for ref in sorted(set(REFERENCE.findall(_read(path)))):
            if not os.path.isfile(os.path.join(root, "profiles", "wow", ref + ".md")):
                errors.append(f"{rel(path)}: references missing profiles/wow/{ref}.md")
            elif ref != own:
                errors.append(f"{rel(path)}: references profiles/wow/{ref}.md, not its own overlay "
                              f"(profiles/wow/{own}.md)")
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
