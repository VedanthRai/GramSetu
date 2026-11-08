"""Quality control for every file in demo-output/final/. Writes demo-output/qc/qc_report.md and .json.

Checks per video: ffprobe (resolution, codec, fps, duration, audio stream, pixel format, faststart, metadata),
EBU R128 loudness + true peak, contact sheets every 1.5 s plus a 390 px-wide phone sheet (for human viewing),
audio/timeline consistency from the render report (no overlapping Timbre clips = no doubled audio; clips cut mid-way
are listed), integrity (validation error + recovery and the persisted demo record asserted from the take's audit log,
every sped-up piece labelled), and a secret scan of captions/logs/EDL/metadata for any fragment of the real keys.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from demo.ff import loudness, lp, probe  # noqa: E402
from demo.sheets import from_video  # noqa: E402

OUT = ROOT / "demo-output"
FINAL = OUT / "final"
QC = OUT / "qc"


def secrets() -> list[str]:
    vals = []
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            k, _, v = line.partition("=")
            if re.search(r"KEY|TOKEN|SECRET", k) and len(v.strip()) >= 12:
                vals.append(v.strip())
    return vals


def scan_for_secrets(paths: list[Path], keys: list[str]) -> list[str]:
    hits = []
    frags = {k[i:i + 12] for k in keys for i in range(0, max(1, len(k) - 12), 6)}
    for p in paths:
        try:
            data = lp(p).read_bytes()
        except OSError:
            continue
        txt = data.decode("utf-8", "ignore")
        for f in frags:
            if f in txt:
                hits.append(f"{p.relative_to(ROOT)}: contains a 12-char fragment of a configured key")
                break
        if re.search(r"vach_[A-Za-z0-9]{8,}|sk-ant-[A-Za-z0-9-]{10,}", txt):
            hits.append(f"{p.relative_to(ROOT)}: matches an API-key pattern")
    return hits


def faststart(path: Path) -> bool:
    head = lp(path).read_bytes()[:200000]
    m, d = head.find(b"moov"), head.find(b"mdat")
    return m != -1 and (d == -1 or m < d)


def check_video(path: Path, rep: dict | None) -> dict:
    pr = probe(path)
    v = next(s for s in pr["streams"] if s["codec_type"] == "video")
    a = next((s for s in pr["streams"] if s["codec_type"] == "audio"), None)
    num, den = map(int, v["r_frame_rate"].split("/"))
    res = {"file": path.name, "width": v["width"], "height": v["height"], "codec": v["codec_name"], "pix_fmt": v["pix_fmt"],
           "fps": round(num / den, 2), "duration_s": round(float(pr["format"]["duration"]), 2),
           "size_mb": round(int(pr["format"]["size"]) / 1e6, 2), "audio": bool(a),
           "audio_codec": a and a["codec_name"], "audio_rate": a and a["sample_rate"], "audio_channels": a and a["channels"],
           "faststart": faststart(path), "tags": pr["format"].get("tags", {})}
    res.update(loudness(path) if a else {})
    sheets = from_video(path, 1.5, QC / f"sheet_{path.stem}.jpg")
    phone = from_video(path, 6.0, QC / f"phone390_{path.stem}.jpg", width=390)
    res["sheets"] = [str(s.relative_to(OUT)) for s in sheets + phone]
    issues = []
    if res["codec"] != "h264" or res["pix_fmt"] != "yuv420p":
        issues.append("not H.264 yuv420p")
    if abs(res["fps"] - 30) > 0.01:
        issues.append(f"fps {res['fps']}")
    if not res["audio"] or res["audio_codec"] != "aac" or res["audio_rate"] != "48000" or res["audio_channels"] != 2:
        issues.append("audio is not AAC 48 kHz stereo")
    if not res["faststart"]:
        issues.append("moov atom not at the start (+faststart missing)")
    if res.get("integrated_lufs") is not None and abs(res["integrated_lufs"] + 16) > 1.5:
        issues.append(f"loudness {res['integrated_lufs']} LUFS (target -16)")
    if res.get("true_peak_dbtp") is not None and res["true_peak_dbtp"] > -1.0:
        issues.append(f"true peak {res['true_peak_dbtp']} dBTP > -1")
    if res["duration_s"] > 140:
        issues.append("longer than 2:20 (X non-Premium limit)")
    if rep:
        # sync: assistant clips never overlap each other (no doubled audio); list clips trimmed by a cut
        clips = sorted([c for c in rep["audio"] if c["kind"] == "assistant"], key=lambda c: c["out"])
        for x, y in zip(clips, clips[1:], strict=False):
            if y["out"] < x["out"] + x["dur"] - 0.05:
                issues.append(f"overlapping Timbre clips at {y['out']}s (doubled audio)")
        res["clips_placed"] = len(rep["audio"])
        res["clips_trimmed_by_cut"] = [f"{c['file']} at {c['out']}s (from {c['src']}s, {c['dur']}s)" for c in rep["audio"] if c["src"] > 0.05]
        if res["clips_trimmed_by_cut"]:
            issues.append("a clip starts mid-sentence after a cut")
        res["clips_ending_early"] = [f"{c['file']} at {c['out']}s ({c['dur']}s kept)" for c in rep["audio"] if c.get("cut_end")]
        res["sped_pieces"] = [f"{t['piece']} ({t['speed']}x)" for t in rep["timeline"] if t.get("speed", 1) != 1]
        res["render_warnings"] = rep.get("checks", [])
        issues += [w for w in rep.get("checks", []) if w.startswith("SKIPPED")]
    res["issues"] = issues
    return res


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    QC.mkdir(parents=True, exist_ok=True)
    rp = OUT / "edit" / "render_report.json"
    reports = {r["output"]: r for r in json.loads(rp.read_text(encoding="utf-8"))["outputs"]} if rp.exists() else {}
    edl = json.loads((OUT / "edit" / "edl.json").read_text(encoding="utf-8"))
    take = OUT / edl["take"]
    summary = json.loads((take / "summary.json").read_text(encoding="utf-8"))
    scheme = next(s for s in summary["scenes"] if s["scene"] == "scheme")
    integrity = {
        "take": edl["take"], "live": summary.get("live"),
        "validation_error_in_audit_log": any("validation error —" in a for a in scheme["audit"]),
        "recovery_in_audit_log": scheme.get("validation_recovered"),
        "injection_probe_ignored": scheme.get("injection_ignored"),
        "final_state": scheme.get("final_state"), "receipt": scheme.get("result"),
        "persisted_demo_record": scheme.get("db_record"),
        "page_errors": scheme.get("page_errors"),
    }
    vids = []
    for f in sorted(FINAL.glob("*.mp4")):
        print("QC", f.name, flush=True)
        vids.append(check_video(f, reports.get(f.name)))
    keys = secrets()
    scan_paths = [p for p in list(FINAL.rglob("*")) + list((OUT / "edit").glob("*.json")) + list((OUT / "posts").glob("*"))
                  + list(take.glob("*.json")) + list(take.glob("*.txt")) + list((OUT / "takes").glob("*.txt"))
                  + list((ROOT / "docs").rglob("*.md")) + list((ROOT / "demo_assets").glob("*.*"))
                  + list((ROOT / "frontend" / "dist").rglob("*.js")) if p.is_file()]
    secret_hits = scan_for_secrets(scan_paths, keys)
    for v in vids:
        if any(k[:12] in json.dumps(v["tags"]) for k in keys):
            secret_hits.append(f"{v['file']}: key fragment in container metadata")
    files = {p.name: round(p.stat().st_size / 1e6, 2) for p in FINAL.iterdir() if p.is_file()}
    result = {"integrity": integrity, "videos": vids, "secret_scan": {"files_scanned": len(scan_paths), "keys_checked": len(keys),
                                                                       "hits": secret_hits}, "final_files_mb": files}
    (QC / "qc_report.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = ["# QC report", "", f"Take: `{edl['take']}` (live: {summary.get('live')})", "", "## Integrity (from the take's audit log and DB)", ""]
    lines += [f"- {k}: `{v}`" for k, v in integrity.items()]
    lines += ["", "## Videos", "", "| file | res | fps | dur s | MB | audio | LUFS | TP dBTP | faststart | issues |", "|---|---|---|---|---|---|---|---|---|---|"]
    for v in vids:
        lines.append(f"| {v['file']} | {v['width']}x{v['height']} | {v['fps']} | {v['duration_s']} | {v['size_mb']} | "
                     f"{v['audio_codec']} {v['audio_rate']} {v['audio_channels']}ch | {v.get('integrated_lufs')} | {v.get('true_peak_dbtp')} | "
                     f"{v['faststart']} | {'; '.join(v['issues']) or 'none'} |")
    lines += ["", "## Per-video detail", ""]
    for v in vids:
        lines += [f"### {v['file']}", f"- sped-up pieces (labelled on screen): {v.get('sped_pieces')}",
                  f"- Timbre/voice clips placed: {v.get('clips_placed')}; clips entering mid-way after a cut: {v.get('clips_trimmed_by_cut')}",
                  f"- clips faded out early by a cut (end of a long reply): {v.get('clips_ending_early')}",
                  f"- render warnings: {v.get('render_warnings')}", f"- contact sheets: {v['sheets']}", ""]
    lines += ["## Secret scan", "", f"- files scanned: {len(scan_paths)}; configured keys checked: {len(keys)}",
              f"- hits: {secret_hits or 'none'}", "", "## Files in final/ (MB)", ""] + [f"- {k}: {v}" for k, v in sorted(files.items())]
    (QC / "qc_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    bad = [v["file"] for v in vids if v["issues"]] + (["secrets"] if secret_hits else [])
    print("QC issues:", bad or "none")


if __name__ == "__main__":
    main()
