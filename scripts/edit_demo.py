"""Reproducible edit: reads demo-output/edit/edl.json + a recorded take and renders every output.

  python scripts/edit_demo.py                       # all outputs from the take named in edl.json
  python scripts/edit_demo.py --take takes/take2 --only gramsetu_master_16x9

Integrity rules enforced here (see demo-output/edit/NOTES.md):
  * footage comes only from the take's frames; segments are cut in order (no reordering except the labelled hook preview)
  * any segment with speed != 1 gets a visible "N× speed" label and drops its audio
  * Timbre / voice clips are placed at their logged wall-clock times, so audio stays in sync with the speaking state
  * captions come from the logged clips: user lines from demo_assets/sentences.json, GramSetu lines translated with the
    app's own en-IN templates (scripts/demo/translate.py)
  * the voice label shows whenever the user voice plays; "Demo portal · synthetic data" shows on every footage segment
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
import shutil
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from demo.ff import lp, run  # noqa: E402
from demo.overlays import SIZES, Renderer  # noqa: E402
from demo.translate import to_english  # noqa: E402

OUT = ROOT / "demo-output"
FPS = 30
W, H = 1920, 1080
LABEL_VOICE = "Voice: AI-generated (Gnani Timbre). Transcribed live by Gnani Prisma."
LABEL_PORTAL = "Demo portal · synthetic data"
LABEL_RULES = "Understanding: rules engine (no AI model)"
LABEL_HISTORY = "Agent's own screenshots, replayed in Mission Control"
LENIENT = False


def wav_dur(p: Path) -> float:
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


# ====================================================================== take model
class Scene:
    def __init__(self, takedir: Path, name: str, sentences: dict) -> None:
        log = json.loads((takedir / f"log_{name}.json").read_text(encoding="utf-8"))
        self.name, self.dir = name, takedir
        self.frames = [(float(t), f) for t, f in log["frames"]]
        self.events = sorted(log["events"], key=lambda e: e["t"])
        self.tts = log["tts"]
        self.evidence = log["evidence"]
        self.marks = {}
        for e in self.events:
            if e["type"] == "mark":
                self.marks.setdefault(e["name"], e["t"])
        self.layouts = [e for e in self.events if e["type"] == "layout"]
        self.sent = sentences
        self.audio = self._audio_cues()

    # --- clips that were really audible: Timbre replies and injected user-voice clips
    def _audio_cues(self) -> list[dict]:
        cues = []
        playing = None
        for e in self.events:
            if e["type"] == "audio_playing":
                info = e.get("tts") or self._tts_by_sha(e.get("sha"))
                if not info:
                    continue
                f = self.dir / info["file"]
                playing = {"kind": "assistant", "start": e["t"], "file": f, "dur": wav_dur(f), "text": info["text"],
                           "lang": info["language"], "voice": info.get("voice"), "end": e["t"] + wav_dur(f)}
                cues.append(playing)
            elif e["type"] in ("audio_ended", "audio_paused") and playing:
                playing["end"] = min(playing["end"], e["t"])
                playing = None
            elif e["type"] == "mic_clip_start":
                u = self.sent.get(e["name"])
                f = ROOT / "demo_assets" / "generated" / f"{e['name']}.wav"
                st = e["t"] + float(e.get("offset", 0))
                cues.append({"kind": "user", "start": st, "file": f, "dur": wav_dur(f), "end": st + wav_dur(f),
                             "text": u["native"] if u else "", "en": u["english"] if u else "", "lang": u["language"] if u else "",
                             "id": e["name"]})
        return cues

    def _tts_by_sha(self, sha):
        return self.tts.get(sha or "")

    def anchor(self, spec: str) -> float:
        m = re.match(r"^(.*?)([+-]\d+(?:\.\d+)?)?$", spec.strip())
        base, off = m.group(1), float(m.group(2) or 0)
        kind, _, arg = base.partition(":") if ":" in base and base.split(":")[0] in (
            "mic_start", "mic_end", "audio", "audio_end", "shot", "state", "event", "mark") else ("mark", "", base)
        if kind == "mark":
            t = self.marks[arg or base]
        elif kind in ("mic_start", "mic_end"):
            c = next(c for c in self.audio if c["kind"] == "user" and c["id"] == arg)
            t = c["start"] if kind == "mic_start" else c["end"]
        elif kind in ("audio", "audio_end"):
            c = next(c for c in self.audio if c["kind"] == "assistant" and arg in c["text"])
            t = c["start"] if kind == "audio" else c["end"]
        elif kind == "shot":
            t = next(e["t"] for e in self.events if e["type"] == "history_shot" and e["index"] == int(arg))
        elif kind == "state":
            t = next(e["t"] for e in self.events if e["type"] == "state" and e["state"] == arg)
        else:
            t = next(e["t"] for e in self.events if e["type"] == "app_event" and arg in (e.get("description") or ""))
        return t + off

    def box(self, name: str, t: float) -> list[int] | None:
        best = None
        for e in self.layouts:
            if e["t"] > t + 0.05:
                break
            if name in e["boxes"]:
                best = e["boxes"][name]
        return best

    def frame_at(self, t: float) -> Path:
        cand = self.frames[0]
        for fr in self.frames:
            if fr[0] > t:
                break
            cand = fr
        return self.dir / f"frames_{self.name}" / cand[1]

    def history_at(self, t: float) -> int | None:
        idx = None
        for e in self.events:
            if e["t"] > t + 0.02:
                break
            if e["type"] == "history_shot":
                idx = e["index"]
        return idx


# ====================================================================== geometry
def zoom_params(box, pad=24, zmax=2.0, zmin=1.0):
    x, y, w, h = box
    x, y, w, h = x - pad, y - pad, w + 2 * pad, h + 2 * pad
    z = max(zmin, min(zmax, W / w, H / h))
    cx, cy = x + w / 2, y + h / 2
    return z, cx, cy


def crop_origin(z, cx, cy):
    cw, ch = W / z, H / z
    return min(max(0, cx - cw / 2), W - cw), min(max(0, cy - ch / 2), H - ch)


def map_box(box, z, cx, cy):
    ox, oy = crop_origin(z, cx, cy)
    x, y, w, h = box
    return [round((x - ox) * z), round((y - oy) * z), round(w * z), round(h * z)]


# ====================================================================== segment planning
class Plan:
    """Resolves an output's segment list into concrete pieces with output times, overlays and audio cues."""

    def __init__(self, edl: dict, scenes: dict[str, Scene], fmt: str, hook_variant: str | None) -> None:
        self.edl, self.scenes, self.fmt, self.hook_variant = edl, scenes, fmt, hook_variant
        self.pieces: list[dict] = []
        self.audio: list[dict] = []
        self.captions: list[dict] = []
        self.checks: list[str] = []
        self.t = 0.0

    def add(self, name: str) -> None:
        seg = dict(self.edl["segments"][name])
        seg["name"] = name
        if seg["type"] == "card":
            self._card(seg)
        else:
            self._footage(seg)

    # ---------------------------------------------------------------- cards
    def _card(self, seg: dict) -> None:
        spec = dict(seg["card"])
        if spec.get("bg"):
            sc = self.scenes[spec["bg"]["scene"]]
            spec["bg"] = str(sc.frame_at(sc.anchor(spec["bg"]["at"])))
        d = float(seg["duration"])
        piece = {"kind": "card", "name": seg["name"], "start": self.t, "dur": d, "spec": spec}
        self.pieces.append(piece)
        if seg.get("narration"):
            self._narration(seg["narration"], self.t)
        self.t += d

    def _narration(self, n: dict, t0: float) -> None:
        f = ROOT / "demo_assets" / "generated" / f"{n['id']}.wav"
        if f.exists():
            d = wav_dur(f)
            self.audio.append({"file": f, "out": t0 + n.get("at", 0), "src": 0, "dur": d, "kind": "narration"})
            text = next((x["text"] for x in self.edl["_sentences"]["narration"] if x["id"] == n["id"]), "")
            self.captions.append({"start": t0 + n.get("at", 0), "end": t0 + n.get("at", 0) + d, "en": text, "native": "",
                                  "lang": "en-IN", "who": "Narration (AI voice · Gnani Timbre)"})

    # ---------------------------------------------------------------- footage
    def _footage(self, seg: dict) -> None:
        sc = self.scenes[seg["scene"]]
        a, b = sc.anchor(seg["from"]), sc.anchor(seg["to"])
        if b <= a:
            raise ValueError(f"segment {seg['name']}: empty range")
        speed = float(seg.get("speed", 1))
        if seg.get("fit"):
            speed = max(1.0, (b - a) / float(seg["fit"]))
        if self.fmt != "16x9" and seg.get("speed_vertical"):
            speed = float(seg["speed_vertical"])
        dur = (b - a) / speed
        out0 = self.t
        zoom = None
        if seg.get("zoom") and seg["zoom"].get("box"):
            bx = sc.box(seg["zoom"]["box"], a + seg["zoom"].get("box_at", 0.6))
            if bx:
                z, cx, cy = zoom_params(bx, seg["zoom"].get("pad", 24), seg["zoom"].get("max", 2.0))
                if seg["zoom"].get("align") == "top":  # tall column: fit the width, keep its top in view
                    pad = seg["zoom"].get("pad", 24)
                    z = max(1.0, min(seg["zoom"].get("max", 2.0), W / (bx[2] + 2 * pad)))
                    cy = bx[1] - pad + (H / z) / 2 + seg["zoom"].get("dy", 0)
                elif seg["zoom"].get("align") == "bottom":
                    pad = seg["zoom"].get("pad", 24)
                    z = max(1.0, min(seg["zoom"].get("max", 2.0), W / (bx[2] + 2 * pad)))
                    cy = bx[1] + bx[3] + pad - (H / z) / 2 + seg["zoom"].get("dy", 0) / z
                zoom = {"z": z, "cx": cx, "cy": cy, "in": seg["zoom"].get("in", 0.5), "out": seg["zoom"].get("out", 0.0)}
            else:
                self.checks.append(f"WARN {seg['name']}: no layout box '{seg['zoom']['box']}' at segment start")
        # vertical/square crop region (static)
        vbox = None
        if self.fmt == "9x16":
            name = (seg.get("vertical") or {}).get("box") or (seg.get("zoom") or {}).get("box") or "voice"
            vbox = sc.box(name, a + 0.6) or [0, 0, W, H]
        piece = {"kind": "footage", "name": seg["name"], "scene": sc, "a": a, "b": b, "speed": speed, "start": out0, "dur": dur,
                 "zoom": zoom, "vbox": vbox, "layers": []}

        def to_out(t):
            return out0 + (t - a) / speed

        # --- audio + captions from the clips that really played inside [a, b]
        voice_windows = []
        if speed == 1 and seg.get("audio", True):
            for c in sc.audio:
                s, e = max(a, c["start"]), min(b, c["end"])
                if e - s < 0.25:
                    continue
                if s - c["start"] > 0.35:  # never start a clip mid-sentence after a cut: drop it (audio + caption)
                    self.checks.append(f"INFO {seg['name']}: dropped clip already playing before the cut ({c['text'][:30]}…)")
                    continue
                self.audio.append({"file": c["file"], "out": to_out(s), "src": s - c["start"], "dur": e - s, "kind": c["kind"],
                                   "fade_in": s > c["start"] + 0.01, "fade_out": e < c["end"] - 0.01})
                if c["kind"] == "user":
                    voice_windows.append((to_out(s), to_out(e)))
                if seg.get("captions", True):
                    self._caption_cue(c, to_out(s), to_out(e), s - c["start"], c["end"] - c["start"])
        # --- static caption (e.g. problem scene, sped montage)
        if seg.get("caption"):
            cap = dict(seg["caption"])
            if cap.get("transcript"):  # the REAL Prisma transcript shown in the UI for this utterance (from the take log)
                uid = cap["transcript"]
                t_stop = sc.marks[f"mic_stop:{uid}"]
                ev = next(e for e in sc.events if e["type"] == "transcript_ui" and e["t"] >= t_stop)
                u = sc.sent[uid]
                cap.update({"native": ev["text"], "lang": u["language"], "en": "Meaning: " + u["english"],
                            "who": "Prisma transcript (live)"})
            self.captions.append({"start": out0, "end": out0 + dur, "en": cap.get("en", ""), "native": cap.get("native", ""),
                                  "lang": cap.get("lang", "en-IN"), "who": cap.get("who", "")})
        if seg.get("narration"):
            self._narration(seg["narration"], out0)

        # --- change points for overlay states
        pts = {out0, out0 + dur}
        callouts = []
        for c in seg.get("callouts", []):
            s = to_out(sc.anchor(c["from"])) if "from" in c else out0 + c.get("at", 0)
            e = to_out(sc.anchor(c["to"])) if "to" in c else (s + c["dur"] if "dur" in c else out0 + dur)
            s, e = max(out0, s), min(out0 + dur, e)
            if c.get("text_from") == "hud":  # numbers quoted from the real Latency HUD text logged in this take
                c = {**c, "text": hud_summary(sc)}
            if e > s:
                callouts.append({**c, "s": s, "e": e})
                pts |= {s, e}
        hls = []
        for h in seg.get("highlights", []):
            bx = sc.box(h["box"], sc.anchor(h["from"]) + 0.2 if "from" in h else a + 0.6)
            if not bx:
                self.checks.append(f"WARN {seg['name']}: highlight box '{h['box']}' not found")
                continue
            s = to_out(sc.anchor(h["from"])) if "from" in h else out0 + (zoom["in"] if zoom else 0) + 0.1
            e = to_out(sc.anchor(h["to"])) if "to" in h else out0 + dur - (zoom["out"] if zoom else 0)
            pad = h.get("pad", 8)
            bx = [bx[0] - pad, bx[1] - pad, bx[2] + 2 * pad, bx[3] + 2 * pad]
            hls.append({"box": bx, "s": max(out0, s), "e": min(out0 + dur, e), "dim": h.get("dim", False)})
            pts |= {max(out0, s), min(out0 + dur, e)}
        inset_times = []
        if seg.get("inset") == "history":
            for e in sc.events:
                if e["type"] == "history_shot" and a <= e["t"] <= b:
                    inset_times.append((to_out(e["t"]), e["index"], e.get("of")))
                    pts.add(to_out(e["t"]))
        for (s, e) in voice_windows:
            pts |= {max(out0, s), min(out0 + dur, e)}
        caps_here = [c for c in self.captions if c["start"] < out0 + dur and c["end"] > out0]
        for c in caps_here:
            pts |= {max(out0, c["start"]), min(out0 + dur, c["end"])}
        pts = sorted(p for p in pts if out0 - 1e-6 <= p <= out0 + dur + 1e-6)

        for s, e in zip(pts, pts[1:], strict=False):
            if e - s < 1 / FPS:
                continue
            mid = (s + e) / 2
            labels = []
            if any(vs <= mid <= ve for vs, ve in voice_windows) or seg.get("voice_label"):
                labels.append(LABEL_VOICE)
            labels.append(LABEL_PORTAL)
            if seg.get("rules_label"):
                labels.append(LABEL_RULES)
            if seg.get("inset") == "history":
                labels.append(LABEL_HISTORY)
            spec: dict = {"step": seg.get("step"), "labels": labels}
            if speed != 1:
                whole = abs(speed - round(speed)) < 0.05
                spec["speed"] = f"{round(speed)}× speed" if whole else f"{speed:.1f}× speed"  # never understate
            cap = next((c for c in self.captions if c["start"] <= mid < c["end"]), None)
            if cap and not seg.get("no_caption_overlay"):
                spec["caption"] = {k: cap[k] for k in ("native", "en", "lang", "who")}
            spec["callouts"] = [{"text": c["text"], "pos": c.get("pos", {}), "tone": c.get("tone", "")}
                                for c in callouts if c["s"] <= mid < c["e"]]
            hl_now = [h for h in hls if h["s"] <= mid < h["e"]]
            if hl_now:
                spec["highlights"] = [{"box": self._place_box(h["box"], piece), "dim": h["dim"]} for h in hl_now]
            if inset_times:
                idx, of = None, None
                for tt, ix, o in inset_times:
                    if tt <= mid:
                        idx, of = ix, o
                if idx is None and seg.get("inset_before"):
                    idx, of = inset_times[0][1], inset_times[0][2]
                if idx:
                    src = sc.dir / f"agent_shots_{sc.name}" / f"{idx:03d}.png"
                    title = self._shot_title(sc, idx, of)
                    pos = (seg.get("inset_pos") or {}).get(self.fmt) or {"16x9": {"x": 200, "y": 96, "w": 900},
                                                                          "1x1": {"x": 140, "y": 250, "w": 800},
                                                                          "9x16": {"x": 40, "y": 980, "w": 1000}}[self.fmt]
                    spec["inset"] = {"src": str(src), "title": title, **pos}
            if seg.get("hook"):
                spec = {"card": "hook", "scrim": True, "lines": self.edl["hooks"][self.hook_variant or "A"]["lines"],
                        "sub": self.edl["hooks"][self.hook_variant or "A"].get("sub", "")}
            piece["layers"].append({"s": s - out0, "e": e - out0, "spec": spec})
        self.pieces.append(piece)
        self.t += dur

    def _shot_title(self, sc: Scene, idx: int, of: int | None = None) -> str:
        n = of or sc.evidence.get("agent_screenshots") or 0
        lab = (sc.evidence.get("shot_labels") or {}).get(f"{idx:03d}.png", "")
        return f"Agent screenshot {idx} of {n}" + (f" · {lab}" if lab else "") + " (enlarged)"

    def _place_box(self, bx, piece):
        z = piece["zoom"]
        if z:
            bx = map_box(bx, z["z"], z["cx"], z["cy"])
        if self.fmt == "1x1":
            s = 1080 / W
            return [round(bx[0] * s), round(bx[1] * s + 236), round(bx[2] * s), round(bx[3] * s)]
        if self.fmt == "9x16":
            vx, vy, vw, vh, sc_, oy = self._vcrop(piece)
            return [round((bx[0] - vx) * sc_), round((bx[1] - vy) * sc_ + oy), round(bx[2] * sc_), round(bx[3] * sc_)]
        return bx

    def _vcrop(self, piece):
        """Vertical: crop the focus element region to 1080x1240 (w:h) and place it at y=300."""
        x, y, w, h = piece["vbox"]
        pad = 20
        x, y, w, h = x - pad, y - pad, w + 2 * pad, h + 2 * pad
        ar = 1080 / 1240
        if w / h > ar:
            nh = w / ar
            y -= (nh - h) / 2
            h = nh
        else:
            nw = h * ar
            x -= (nw - w) / 2
            w = nw
        w, h = min(w, W), min(h, H)
        x, y = min(max(0, x), W - w), min(max(0, y), H - h)
        return round(x), round(y), round(w), round(h), 1080 / w, 300

    def _caption_cue(self, c, s, e, src_s, src_total):
        """Split long lines into readable chunks (<= 2 lines each), timed proportionally to the clip."""
        if c["kind"] == "user":
            en, nat, who = c["en"], c["text"], "User (AI voice · Gnani Timbre)"
        else:
            nat = c["text"]
            en = to_english(nat, c["lang"])
            who = "GramSetu (Gnani Timbre)"
            if en is None:
                self.checks.append(f"WARN caption: no English template match for '{nat[:40]}'")
                en = ""
        en_chunks = _chunks(en.replace("\n", " "), 95)
        nat_chunks = _split_like(nat.replace("\n", " "), len(en_chunks))
        n = len(en_chunks)
        for i in range(n):
            cs = src_total * i / n
            ce = src_total * (i + 1) / n
            os_, oe = s + (cs - src_s), s + (ce - src_s)
            os_, oe = max(s, os_), min(e, oe)
            if oe - os_ < 0.4:
                continue
            self.captions.append({"start": os_, "end": oe, "en": en_chunks[i], "native": nat_chunks[i], "lang": c["lang"], "who": who})


def hud_summary(sc: Scene) -> str:
    txt = next(e["text"] for e in sc.events if e["type"] == "hud_text")
    parts = txt.splitlines()
    rows = dict(zip(parts[0::2], parts[1::2], strict=False))
    get = lambda k: next((v for kk, v in rows.items() if kk.startswith(k)), "—")  # noqa: E731
    return (f"Measured, last voice turn: Prisma {get('Prisma')} · Timbre first audio {get('Timbre')} · "
            f"total machine time {get('Total')}")


def _chunks(text: str, maxlen: int) -> list[str]:
    sents = [s for s in re.split(r"(?<=[.?!।])\s+", text.strip()) if s]
    out, cur = [], ""
    for s in sents:
        if cur and len(cur) + 1 + len(s) > maxlen:
            out.append(cur)
            cur = s
        else:
            cur = (cur + " " + s).strip()
    if cur:
        out.append(cur)
    final = []
    for c in out:  # very long single sentences: split on commas/words
        while len(c) > maxlen * 1.25:
            cut = c.rfind(" ", 0, maxlen)
            final.append(c[:cut])
            c = c[cut + 1:]
        final.append(c)
    return final or [""]


def _split_like(text: str, n: int) -> list[str]:
    if n <= 1:
        return [text]
    sents = [s for s in re.split(r"(?<=[.?!।])\s+", text.strip()) if s]
    if len(sents) < n:
        words = text.split()
        k = math.ceil(len(words) / n)
        return [" ".join(words[i * k:(i + 1) * k]) for i in range(n)]
    total = sum(len(s) for s in sents)
    out, cur, acc, target = [], [], 0, total / n
    for s in sents:
        cur.append(s)
        acc += len(s)
        if acc >= target * (len(out) + 1) and len(out) < n - 1:
            out.append(" ".join(cur))
            cur = []
    out.append(" ".join(cur))
    while len(out) < n:
        out.append("")
    return out


# ====================================================================== rendering
async def render_output(name: str, cfg: dict, edl: dict, scenes: dict, outdir: Path, work: Path, rnd: Renderer) -> dict:
    fmt = cfg["format"]
    plan = Plan(edl, scenes, fmt, cfg.get("hook"))
    for s in cfg["segments"]:
        try:
            plan.add(s)
        except (KeyError, StopIteration) as e:
            if not LENIENT:
                raise RuntimeError(f"segment {s}: anchor not found in take ({e!r})") from e
            plan.checks.append(f"SKIPPED segment {s}: anchor not found ({e!r})")
    sz = SIZES[fmt]
    ow, oh = sz["w"], sz["h"]
    wd = work / name
    if wd.exists():
        shutil.rmtree(wd)
    wd.mkdir(parents=True)
    clips = []
    for i, p in enumerate(plan.pieces):
        out = wd / f"p{i:02d}.mp4"
        if p["kind"] == "card":
            png = await rnd.render(fmt, p["spec"], transparent=False)
            run(["-loop", "1", "-framerate", str(FPS), "-i", str(png), "-t", f"{p['dur']:.3f}", "-vf", "format=yuv420p",
                 "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", str(FPS), str(out)])
        else:
            await _render_footage(p, fmt, ow, oh, wd, out, rnd)
        clips.append(out)
    lst = wd / "concat.txt"
    lst.write_text("".join(f"file '{c.as_posix()}'\n" for c in clips), encoding="utf-8")
    video = wd / "video.mp4"
    run(["-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(video)])
    total = plan.t
    audio = wd / "audio.wav"
    _mix_audio(plan.audio, total, audio, wd)
    final = outdir / f"{name}.mp4"
    run(["-i", str(video), "-i", str(audio), "-map", "0:v", "-map", "1:a", "-vf", "scale=out_range=tv,format=yuv420p",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", str(FPS), "-color_range", "tv", "-colorspace", "bt709",
         "-color_primaries", "bt709", "-color_trc", "bt709", "-c:a", "aac", "-b:a", "192k",
         "-ar", "48000", "-ac", "2", "-shortest", "-movflags", "+faststart", "-map_metadata", "-1", "-map_chapters", "-1",
         "-metadata", "title=GramSetu demo", "-metadata", "comment=Demo portals with synthetic data. All voices AI-generated with Gnani Timbre.",
         str(final)])
    _write_srts(plan.captions, outdir, name)
    shutil.rmtree(wd, ignore_errors=True)  # intermediates (disk space)
    timeline = [{"piece": p["name"], "start": round(p["start"], 2), "dur": round(p["dur"], 2),
                 **({"speed": round(p["speed"], 2), "raw_from": round(p["a"] - p["scene"].frames[0][0], 2),
                     "raw_to": round(p["b"] - p["scene"].frames[0][0], 2), "scene": p["scene"].name} if p["kind"] == "footage" else {})}
                for p in plan.pieces]
    audio_log = [{"file": Path(a["file"]).name, "kind": a["kind"], "out": round(a["out"], 2), "src": round(a["src"], 2),
                  "dur": round(a["dur"], 2), "cut_end": bool(a.get("fade_out"))} for a in plan.audio]
    return {"output": final.name, "format": fmt, "duration": round(total, 2), "timeline": timeline, "audio": audio_log,
            "captions": len(plan.captions), "checks": plan.checks}


async def _render_footage(p, fmt, ow, oh, wd, out, rnd):
    sc: Scene = p["scene"]
    a, b, speed = p["a"], p["b"], p["speed"]
    frs = [f for f in sc.frames if a <= f[0] < b]
    first = sc.frame_at(a)
    entries = [(a, first)] + [(t, sc.dir / f"frames_{sc.name}" / n) for t, n in frs if t > a]
    lst = out.with_suffix(".txt")
    lines = []
    for (t, f), nxt in zip(entries, entries[1:] + [(b, None)], strict=False):
        d = max(0.001, (nxt[0] - t) / speed)
        lines.append(f"file '{Path(f).as_posix()}'\nduration {d:.4f}\n")
    lines.append(f"file '{Path(entries[-1][1]).as_posix()}'\n")
    lst.write_text("".join(lines), encoding="utf-8")
    dur = p["dur"]
    vf = [f"fps={FPS}", "setsar=1"]
    z = p["zoom"]
    if fmt == "9x16":
        x, y, w, h, s, oy = Plan._vcrop(None, p)
        vf += [f"crop={w}:{h}:{x}:{y}", "scale=1080:1240:flags=lanczos", "pad=1080:1920:0:300:color=0x0f1a2e"]
    else:
        if z:
            Z = z["z"]
            T_in, T_out = max(0.01, z["in"]), z["out"]
            e_in = f"((1-cos(PI*clip(it/{T_in},0,1)))/2)"
            e = e_in if not T_out else f"min({e_in},((1-cos(PI*clip(({dur:.3f}-it)/{T_out},0,1)))/2))"
            # zoompan on a 2x upscale for smooth sub-pixel motion; 'it' = input time
            zexpr = f"1+({Z - 1:.4f})*{e}".replace("it", "in/" + str(FPS))
            cxe = f"(960+({z['cx'] - 960:.2f})*{e})*2".replace("it", "in/" + str(FPS))
            cye = f"(540+({z['cy'] - 540:.2f})*{e})*2".replace("it", "in/" + str(FPS))
            vf += ["scale=3840:2160:flags=lanczos",
                   f"zoompan=z='{zexpr}':x='clip({cxe}-iw/zoom/2,0,iw-iw/zoom)':y='clip({cye}-ih/zoom/2,0,ih-ih/zoom)'"
                   f":d=1:s=1920x1080:fps={FPS}"]
        if fmt == "1x1":
            vf += ["scale=1080:608:flags=lanczos", "pad=1080:1080:0:236:color=0x0f1a2e"]
    inputs = ["-f", "concat", "-safe", "0", "-i", str(lst)]
    fc = f"[0:v]{','.join(vf)},format=yuv420p[b0]"
    last = "b0"
    for i, L in enumerate(p["layers"]):
        png = await rnd.render(fmt, L["spec"], transparent=True)
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", str(png)]
        fc += f";[{last}][{i + 1}:v]overlay=0:0:enable='between(t,{L['s']:.3f},{L['e'] - 0.0005:.3f})'[b{i + 1}]"
        last = f"b{i + 1}"
    fc += f";[{last}]format=yuv420p[v]"
    run([*inputs, "-filter_complex", fc, "-map", "[v]", "-t", f"{dur:.3f}", "-r", str(FPS), "-c:v", "libx264", "-preset", "medium",
         "-crf", "18", "-pix_fmt", "yuv420p", str(out)])


def _norm_clip(f: Path, cache: Path) -> Path:
    """Normalise each source clip to -19 LUFS so voices sit at a similar level before mixing."""
    cache.mkdir(parents=True, exist_ok=True)
    out = cache / (f.stem + "_n.wav")
    if not out.exists():
        run(["-i", str(f), "-af", "loudnorm=I=-19:TP=-3:LRA=11", "-ar", "48000", "-ac", "1", str(out)])
    return out


def _mix_audio(cues, total, out, wd):
    cache = OUT / "edit" / "cache" / "norm"
    if not cues:
        run(["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{total:.3f}", str(out)])
        return
    narr = [(c["out"], c["out"] + c["dur"]) for c in cues if c["kind"] == "narration"]
    inputs, parts = [], []
    for i, c in enumerate(cues):
        inputs += ["-i", str(_norm_clip(Path(c["file"]), cache))]
        fi = "afade=t=in:d=0.06," if c.get("fade_in") else ""
        fo = f"afade=t=out:st={max(0, c['dur'] - 0.12):.3f}:d=0.12," if c.get("fade_out") else ""
        duck = ""
        if c["kind"] != "narration":
            for s, e in narr:  # duck product audio under narration
                if s < c["out"] + c["dur"] and e > c["out"]:
                    duck += f"volume=0.35:enable='between(t,{s - c['out']:.3f},{e - c['out']:.3f})',"
        ms = int(round(c["out"] * 1000))
        parts.append(f"[{i}:a]atrim=start={c['src']:.3f}:duration={c['dur']:.3f},asetpts=PTS-STARTPTS,{fi}{fo}{duck}"
                     f"adelay={ms}:all=1[a{i}]")
    fc = ";".join(parts) + ";" + "".join(f"[a{i}]" for i in range(len(cues))) + \
        f"amix=inputs={len(cues)}:normalize=0:dropout_transition=0,apad=whole_dur={total:.3f},atrim=duration={total:.3f}[m]"
    raw = wd / "mix_raw.wav"
    run([*inputs, "-filter_complex", fc, "-map", "[m]", "-ar", "48000", "-ac", "2", str(raw)])
    # two-pass EBU R128 loudness normalisation to -16 LUFS, true peak <= -1.5 dBTP
    r = run(["-i", str(raw), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"])
    js = json.loads(r.stderr[r.stderr.rfind("{"):r.stderr.rfind("}") + 1])
    run(["-i", str(raw), "-af", f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
         f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true",
         "-ar", "48000", "-ac", "2", str(out)])


def _ts(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def _write_srts(caps, outdir, name):
    caps = sorted(caps, key=lambda c: c["start"])
    def write(path, items):
        lp(path).write_text("".join(f"{i}\n{_ts(s)} --> {_ts(e)}\n{txt}\n\n" for i, (s, e, txt) in enumerate(items, 1)), encoding="utf-8")
    write(outdir / f"{name}.captions_en.srt", [(c["start"], c["end"], c["en"]) for c in caps if c["en"]])
    langs = {c["lang"] for c in caps if c["native"] and c["lang"] != "en-IN"}
    for lg in langs:
        write(outdir / f"{name}.captions_{lg.split('-')[0]}.srt", [(c["start"], c["end"], c["native"]) for c in caps
                                                                     if c["native"] and c["lang"] == lg])


# ====================================================================== extras: gif, thumbnails, social card
async def extras(edl, scenes, outdir, rnd):
    ex = edl["extras"]
    master = outdir / f"{ex['gif_from']}.mp4"
    pal = OUT / "edit" / "cache" / "palette.png"
    s, d = ex["gif_start"], ex["gif_dur"]
    run(["-ss", str(s), "-t", str(d), "-i", str(master), "-vf", "fps=12,scale=960:-1:flags=lanczos,palettegen=max_colors=128", str(pal)])
    run(["-ss", str(s), "-t", str(d), "-i", str(master), "-i", str(pal), "-lavfi",
         "fps=12,scale=960:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4", str(outdir / "readme_loop.gif")])
    for spec in ex["cards"]:
        sc = scenes[spec["bg"]["scene"]]
        bg = str(sc.frame_at(sc.anchor(spec["bg"]["at"])))
        card = {"card": "thumb", "bg": bg, "lines": spec["lines"], "sub": spec.get("sub", ""), "tags": spec.get("tags", "")}
        fmt = spec["format"]
        png = await rnd.render(fmt, card, transparent=False)
        w, h = spec["size"]
        run(["-i", str(png), "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}", str(outdir / spec["file"])])


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--edl", default=str(OUT / "edit" / "edl.json"))
    ap.add_argument("--take")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--outdir", default=str(OUT / "final"))
    ap.add_argument("--no-extras", action="store_true")
    ap.add_argument("--lenient", action="store_true", help="skip segments whose anchors are missing (rehearsals only)")
    a = ap.parse_args()
    global LENIENT
    LENIENT = a.lenient
    edl = json.loads(Path(a.edl).read_text(encoding="utf-8"))
    sentences = json.loads((ROOT / "demo_assets" / "sentences.json").read_text(encoding="utf-8"))
    edl["_sentences"] = sentences
    by_id = {u["id"]: u for u in sentences["utterances"]}
    takedir = OUT / (a.take or edl["take"])
    if "REHEARSAL" in takedir.name and "final" in Path(a.outdir).parts:
        sys.exit("Refusing to render a REHEARSAL take into demo-output/final/. Use --outdir demo-output/takes/<name>/edit.")
    scenes = {n: Scene(takedir, n, by_id) for n in ("problem", "scheme", "clinic") if (takedir / f"log_{n}.json").exists()}
    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    work = OUT / "edit" / "work"
    report = {"take": str(takedir.relative_to(OUT)), "outputs": []}
    async with Renderer(OUT / "edit" / "cache" / "overlays") as rnd:
        for name, cfg in edl["outputs"].items():
            if a.only and name not in a.only:
                continue
            print("rendering", name, flush=True)
            r = await render_output(name, cfg, edl, scenes, outdir, work, rnd)
            print(f"  {r['duration']} s, {len(r['timeline'])} pieces, {r['captions']} captions", *r["checks"], sep="\n  ")
            report["outputs"].append(r)
        if not a.no_extras and not a.only:
            await extras(edl, scenes, outdir, rnd)
    rp = OUT / "edit" / f"render_report{'_' + takedir.name if 'REHEARSAL' in takedir.name else ''}.json"
    lp(rp).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", rp)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(main())
