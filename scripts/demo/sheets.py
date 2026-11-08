"""Contact sheets: a grid of frames every N seconds, from a raw take (frame log) or from an MP4.

  python scripts/demo/sheets.py take demo-output/takes/take1 scheme --every 3
  python scripts/demo/sheets.py video demo-output/final/gramsetu_master_16x9.mp4 --every 1.5
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from demo.ff import FFMPEG  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def grid(images: list[tuple[str, Image.Image]], out: Path, cols: int = 4, w: int = 640) -> list[Path]:
    """Writes one or more sheets of up to 16 tiles each; returns their paths."""
    paths = []
    per = cols * 4
    for page in range(0, len(images), per):
        chunk = images[page:page + per]
        h = int(w * chunk[0][1].height / chunk[0][1].width)
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * w, rows * (h + 24)), "white")
        d = ImageDraw.Draw(sheet)
        font = ImageFont.load_default(18)
        for i, (label, im) in enumerate(chunk):
            x, y = (i % cols) * w, (i // cols) * (h + 24)
            sheet.paste(im.resize((w, h)), (x, y + 24))
            d.text((x + 6, y + 3), label, fill="black", font=font)
        p = out.with_name(f"{out.stem}_{page // per + 1:02d}.jpg")
        p.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(p, quality=85)
        paths.append(p)
    return paths


def from_take(takedir: Path, scene: str, every: float, out: Path) -> list[Path]:
    log = json.loads((takedir / f"log_{scene}.json").read_text(encoding="utf-8"))
    frames = log["frames"]
    t0 = frames[0][0]
    imgs, t = [], t0
    j = 0
    while t <= frames[-1][0]:
        while j + 1 < len(frames) and frames[j + 1][0] <= t:
            j += 1
        imgs.append((f"{t - t0:6.1f}s", Image.open(takedir / f"frames_{scene}" / frames[j][1])))
        t += every
    return grid(imgs, out)


def from_video(video: Path, every: float, out: Path, width: int = 640) -> list[Path]:
    with tempfile.TemporaryDirectory() as td:
        subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-i", str(video), "-vf", f"fps=1/{every},scale={width}:-2",
                        str(Path(td) / "f%04d.png")], check=True)
        files = sorted(Path(td).glob("f*.png"))
        imgs = [(f"{i * every:6.1f}s", Image.open(f).copy()) for i, f in enumerate(files)]
    return grid(imgs, out, w=width)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["take", "video"])
    ap.add_argument("path")
    ap.add_argument("scene", nargs="?")
    ap.add_argument("--every", type=float, default=3)
    ap.add_argument("--out")
    a = ap.parse_args()
    p = Path(a.path)
    if a.kind == "take":
        out = Path(a.out) if a.out else ROOT / "demo-output" / "qc" / f"sheet_{p.name}_{a.scene}.jpg"
        print("\n".join(map(str, from_take(p, a.scene, a.every, out))))
    else:
        out = Path(a.out) if a.out else ROOT / "demo-output" / "qc" / f"sheet_{p.stem}.jpg"
        print("\n".join(map(str, from_video(p, a.every, out))))
