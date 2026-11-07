#!/usr/bin/env python3
"""Rewrite a TOC's ## Interface line per client slot, in place.

Usage: bump_interface.py <toc> --retail N [--forever M]
Retail slot = the 6-digit number, Forever slot = the 5-digit 16xxx number. The
output order is Retail first. A single-number line stays a single number (a
--forever value is ignored there). The file's own line endings are preserved
byte for byte. Prints "<old> -> <new>". Exit 2 bad argument, 4 no Interface line.
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


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("toc")
    ap.add_argument("--retail", required=True)
    ap.add_argument("--forever")
    a = ap.parse_args(argv)
    if classify(a.retail) != "retail":
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
    kinds = [classify(x) for x in nums]
    if len(nums) == 2 and set(kinds) == {"retail", "forever"}:
        forever = a.forever if a.forever is not None else nums[kinds.index("forever")]
        new = "%s, %s" % (a.retail, forever)
    elif len(nums) == 1:
        new = a.retail
    else:
        print("unrecognized Interface shape: %s" % old, file=sys.stderr)
        return 2
    out = data[:m.start()] + m.group(1) + b" " + new.encode() + data[m.end():]
    with open(a.toc, "wb") as f:
        f.write(out)
    print("%s -> %s" % (old, new))
    return 0


if __name__ == "__main__":
    sys.exit(main())
