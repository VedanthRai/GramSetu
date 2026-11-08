"""Length-check the X thread drafts (280 characters per post; links counted as 23)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIMIT = 280


def x_len(text: str) -> int:
    text = re.sub(r"https?://\S+|\[FILL: GitHub repo URL\]", "x" * 23, text)
    # twitter-text v3 weighting: code points 0-4351 and 8192-8205, 8208-8223, 8242-8247 weigh 1, everything else 2
    light = [(0, 4351), (8192, 8205), (8208, 8223), (8242, 8247)]
    return sum(1 if any(a <= ord(ch) <= b for a, b in light) else 2 for ch in text)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    md = (ROOT / "demo-output" / "posts" / "x_thread.md").read_text(encoding="utf-8")
    posts = re.findall(r"\*\*(\d/\d)\*\*\n(.*?)(?=\n\*\*\d/\d\*\*|\Z)", md, re.S)
    bad = 0
    for n, body in posts:
        body = body.strip()
        # the tag placeholder will become a handle of ~10-15 characters
        L = x_len(body.replace("[TAG: official Gnani X handle: verify]", "@" + "x" * 15))
        ok = L <= LIMIT
        bad += not ok
        print(f"{n}: {L} chars {'OK' if ok else 'TOO LONG'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
