"""Locate ffmpeg/ffprobe and small helpers shared by the demo scripts."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path


def _find(name: str) -> str:
    p = shutil.which(name)
    if p:
        return p
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    for c in base.glob(f"Gyan.FFmpeg*/*/bin/{name}.exe"):
        return str(c)
    raise SystemExit(f"{name} not found: install ffmpeg (winget install Gyan.FFmpeg / apt install ffmpeg)")


FFMPEG = _find("ffmpeg")
FFPROBE = _find("ffprobe")


def run(args: list[str], quiet: bool = True) -> subprocess.CompletedProcess:
    r = subprocess.run([FFMPEG, "-hide_banner", "-y", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError("ffmpeg failed:\n" + r.stderr[-3000:])
    return r


def probe(path: Path) -> dict:
    r = subprocess.run([FFPROBE, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
                       capture_output=True, text=True, encoding="utf-8")
    return json.loads(r.stdout)


def loudness(path: Path) -> dict:
    """EBU R128 integrated loudness (LUFS), true peak (dBTP) and LRA via ffmpeg's ebur128 filter."""
    r = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", str(path), "-filter_complex", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = r.stderr[r.stderr.rfind("Summary:"):]
    def num(label: str) -> float | None:
        m = re.search(label + r":\s+(-?[\d.]+|-inf)", tail)
        return None if not m or m.group(1) == "-inf" else float(m.group(1))
    return {"integrated_lufs": num("I"), "true_peak_dbtp": num("Peak"), "lra": num("LRA")}


def lp(path) -> Path:
    """Long-path-safe Path on Windows (extended-length prefix), so deep project folders don't hit the 260-char limit."""
    prefix = "\\\\?\\"
    p = Path(path).resolve()
    if os.name == "nt" and not str(p).startswith(prefix):
        return Path(prefix + str(p))
    return p
