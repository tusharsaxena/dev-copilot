#!/usr/bin/env python3
"""Rewrite a TOC's ## Interface line per client slot, in place.

Usage: bump_interface.py <toc> [--retail N] [--forever M]   (at least one)
Retail slot = the 6-digit number, Forever slot = the 5-digit 16xxx number. The
output order is Retail first. Each slot takes its own value and a slot with no
value passed keeps the number it has. A single-number line stays a single
number of its own kind: a Retail line (a `Retail` or `Retail (port pending)`
addon) needs --retail and ignores --forever, a Forever line (a `Forever` addon)
needs --forever and ignores --retail, so no slot is ever invented. The file's
own line endings are preserved byte for byte. Prints "<old> -> <new>".
Exit 2 bad argument or shape, 4 no Interface line.
"""

import argparse
import re
import sys

LINE = re.compile(rb"^(##\s*Interface\s*:)([^\r\n]*)", re.I | re.M)


def classify(n):
    if re.fullmatch(r"\d{6}", n):
        return "retail"
    if re.fullmatch(r"16\d{3}", n):
        return "forever"
    return None


def new_value(nums, retail, forever):
    """Return (value, error) for the rewritten Interface value."""
    kinds = [classify(x) for x in nums]
    if len(nums) == 2 and set(kinds) == {"retail", "forever"}:
        r = retail if retail is not None else nums[kinds.index("retail")]
        f = forever if forever is not None else nums[kinds.index("forever")]
        return "%s, %s" % (r, f), None
    if len(nums) == 1 and kinds[0] == "retail":
        if retail is None:
            return None, "a Retail Interface line needs --retail"
        return retail, None
    if len(nums) == 1 and kinds[0] == "forever":
        if forever is None:
            return None, "a Forever Interface line needs --forever"
        return forever, None
    return None, "unrecognized Interface shape: %s" % ", ".join(nums)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("toc")
    ap.add_argument("--retail")
    ap.add_argument("--forever")
    a = ap.parse_args(argv)
    if a.retail is None and a.forever is None:
        print("pass --retail, --forever or both", file=sys.stderr)
        return 2
    if a.retail is not None and classify(a.retail) != "retail":
        print("--retail must be a 6-digit number", file=sys.stderr)
        return 2
    if a.forever is not None and classify(a.forever) != "forever":
        print("--forever must be a 5-digit 16xxx number", file=sys.stderr)
        return 2
    with open(a.toc, "rb") as f:
        data = f.read()
    m = LINE.search(data)
    if not m:
        print("no ## Interface line", file=sys.stderr)
        return 4
    old = m.group(2).decode().strip()
    nums = [x.strip() for x in old.split(",") if x.strip()]
    new, err = new_value(nums, a.retail, a.forever)
    if err:
        print(err, file=sys.stderr)
        return 2
    out = data[:m.start()] + m.group(1) + b" " + new.encode() + data[m.end():]
    with open(a.toc, "wb") as f:
        f.write(out)
    print("%s -> %s" % (old, new))
    return 0

if __name__ == "__main__":
    sys.exit(main())
