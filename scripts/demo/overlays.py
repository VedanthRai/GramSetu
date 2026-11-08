"""HTML/CSS overlays and cards rendered with Playwright (crisp Indic text in Noto Sans), saved as PNGs for ffmpeg.

Overlays are NOT part of the product UI: they are drawn on top of the recorded footage in the edit.
"""
from __future__ import annotations

import base64
import hashlib
import html
import json
from pathlib import Path

from playwright.async_api import async_playwright

FONTS = ("https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;600;700;800&family=Noto+Sans+Devanagari:wght@500;700"
         "&family=Noto+Sans+Kannada:wght@500;700&family=Noto+Sans+Tamil:wght@500;700&display=block")

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:transparent;width:100%;height:100%;overflow:hidden}
body{font-family:'Noto Sans','Noto Sans Kannada','Noto Sans Devanagari','Noto Sans Tamil',sans-serif;color:#fff;position:relative}
:root{--ink:#14213a;--saffron:#e07b1a;--green:#1f8a4c;--card:#fffdf8}
.pill{display:inline-flex;align-items:center;gap:10px;border-radius:999px;font-weight:700;white-space:nowrap}
.steps{position:absolute;left:var(--m);top:var(--m);display:flex;gap:8px;background:rgba(20,33,58,.92);padding:8px;border-radius:999px;
  box-shadow:0 6px 24px rgba(0,0,0,.25)}
.steps .s{padding:10px 20px;border-radius:999px;font-size:var(--fs-step);color:#c9d1e0;font-weight:700}
.steps .s.on{background:var(--saffron);color:#fff}
.labels{position:absolute;right:var(--m);top:var(--m);display:flex;flex-direction:column;align-items:flex-end;gap:8px}
.lab{background:rgba(255,253,248,.96);color:var(--ink);padding:8px 16px;font-size:var(--fs-lab);border:2px solid var(--ink);border-radius:12px;font-weight:700}
.lab.v{border-color:var(--saffron)}
.speed{position:absolute;left:50%;top:var(--m);transform:translateX(-50%);background:#b42318;color:#fff;font-size:var(--fs-speed);
  padding:8px 22px;border-radius:999px;font-weight:800}
.cap{position:absolute;left:50%;transform:translateX(-50%);bottom:var(--capb);width:var(--capw);background:rgba(10,16,30,.86);
  border-radius:18px;padding:16px 28px;text-align:center;box-shadow:0 8px 30px rgba(0,0,0,.35)}
.cap .n{font-size:var(--fs-nat);line-height:1.35;color:#ffd9ad;font-weight:600}
.cap .e{font-size:var(--fs-en);line-height:1.3;font-weight:700;margin-top:4px}
.cap .who{font-size:calc(var(--fs-lab)*.9);color:#9fb0cc;font-weight:700;letter-spacing:.06em;text-transform:uppercase;margin-bottom:4px}
.hl{position:absolute;border:5px solid var(--saffron);border-radius:16px;box-shadow:0 0 0 9999px rgba(10,16,30,.28)}
.hl.nodim{box-shadow:none}
.call{position:absolute;background:var(--saffron);color:#fff;font-weight:800;font-size:var(--fs-call);padding:12px 20px;border-radius:14px;
  max-width:var(--callw);line-height:1.25;box-shadow:0 8px 24px rgba(0,0,0,.3)}
.call.green{background:var(--green)} .call.ink{background:var(--ink)}
.inset{position:absolute;border:6px solid var(--ink);border-radius:14px;overflow:hidden;background:#fff;box-shadow:0 18px 50px rgba(0,0,0,.45)}
.inset img{display:block;width:100%}
.inset .t{position:absolute;left:0;right:0;bottom:0;background:rgba(20,33,58,.92);color:#fff;font-size:var(--fs-lab);font-weight:700;padding:8px 14px}
/* cards */
.card{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;padding:6%}
.card.bg{background:#0f1a2e} .card.scrim{background:linear-gradient(180deg,rgba(8,14,28,.80),rgba(8,14,28,.55))}
.card .bgimg{position:absolute;inset:0;background-size:cover;background-position:center;filter:brightness(.42) saturate(.9)}
.card .z{position:relative}
.hook{font-size:var(--fs-hook);font-weight:800;line-height:1.08;letter-spacing:-.01em;text-shadow:0 4px 30px rgba(0,0,0,.5)}
.hook em{font-style:normal;color:#ffb05c}
.sub{font-size:var(--fs-sub);color:#e6ebf5;margin-top:22px;font-weight:600}
.small{font-size:calc(var(--fs-sub)*.72);color:#c6d0e2;margin-top:14px;font-weight:600}
.brand{font-size:var(--fs-brand);font-weight:800}
.tags{margin-top:20px;font-size:var(--fs-sub);color:#ffb05c;font-weight:800}
.q{margin-top:26px;font-size:var(--fs-sub);background:#fff;color:var(--ink);padding:12px 26px;border-radius:999px;font-weight:800;display:inline-block}
"""

SIZES = {  # per output format: margins and type scale tuned for phone viewing
    "16x9": {"w": 1920, "h": 1080, "m": "28px", "fs-step": "26px", "fs-lab": "22px", "fs-speed": "30px", "fs-nat": "34px", "fs-en": "38px",
             "capw": "1500px", "capb": "40px", "fs-call": "32px", "callw": "560px", "fs-hook": "104px", "fs-sub": "40px", "fs-brand": "120px"},
    "1x1": {"w": 1080, "h": 1080, "m": "22px", "fs-step": "22px", "fs-lab": "19px", "fs-speed": "26px", "fs-nat": "30px", "fs-en": "34px",
            "capw": "1020px", "capb": "26px", "fs-call": "28px", "callw": "460px", "fs-hook": "80px", "fs-sub": "34px", "fs-brand": "96px"},
    "9x16": {"w": 1080, "h": 1920, "m": "40px", "fs-step": "26px", "fs-lab": "22px", "fs-speed": "30px", "fs-nat": "36px", "fs-en": "42px",
             "capw": "1000px", "capb": "150px", "fs-call": "32px", "callw": "560px", "fs-hook": "92px", "fs-sub": "40px", "fs-brand": "110px"},
}

STEPS = ["1 Speak", "2 Review", "3 Watch it work", "4 Approve"]


def _img_uri(path: str | Path) -> str:
    data = Path(path).read_bytes()
    mime = "image/png" if str(path).lower().endswith(".png") else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(data).decode()


def layer_html(spec: dict) -> str:
    e = html.escape
    parts = []
    for h in spec.get("highlights", []):
        x, y, w, hh = h["box"]
        parts.append(f'<div class="hl {"nodim" if not h.get("dim", True) else ""}" style="left:{x}px;top:{y}px;width:{w}px;height:{hh}px"></div>')
    if spec.get("inset"):
        i = spec["inset"]
        x, y, w = i["x"], i["y"], i["w"]
        parts.append(f'<div class="inset" style="left:{x}px;top:{y}px;width:{w}px"><img src="{_img_uri(i["src"])}">'
                     + (f'<div class="t">{e(i["title"])}</div>' if i.get("title") else "") + "</div>")
    if spec.get("step") is not None:
        parts.append('<div class="steps">' + "".join(f'<div class="s {"on" if k == spec["step"] else ""}">{e(s)}</div>'
                                                     for k, s in enumerate(STEPS)) + "</div>")
    if spec.get("labels"):
        parts.append('<div class="labels">' + "".join(f'<div class="lab {"v" if "Voice" in lb else ""}">{e(lb)}</div>'
                                                      for lb in spec["labels"]) + "</div>")
    if spec.get("speed"):
        parts.append(f'<div class="speed">{e(spec["speed"])}</div>')
    for c in spec.get("callouts", []):
        st = ";".join(f"{k}:{v}px" for k, v in c.get("pos", {}).items())
        parts.append(f'<div class="call {c.get("tone", "")}" style="{st}">{e(c["text"])}</div>')
    if spec.get("caption"):
        c = spec["caption"]
        nat = f'<div class="n" lang="{e(c.get("lang", ""))}">{e(c["native"])}</div>' if c.get("native") else ""
        en = f'<div class="e">{e(c["en"])}</div>' if c.get("en") else ""
        who = f'<div class="who">{e(c["who"])}</div>' if c.get("who") else ""
        parts.append(f'<div class="cap">{who}{nat}{en}</div>')
    return "".join(parts)


def card_html(spec: dict) -> str:
    e = html.escape
    bg = f'<div class="bgimg" style="background-image:url({_img_uri(spec["bg"])})"></div>' if spec.get("bg") else ""
    if spec["card"] == "hook":
        lines = "".join(f"<div>{ln}</div>" for ln in spec["lines"])  # trusted text from edl.json (may contain <em>)
        sub = f'<div class="sub">{e(spec["sub"])}</div>' if spec.get("sub") else ""
        cls = "scrim" if spec.get("scrim") else ("" if bg else "bg")
        return f'<div class="card {cls}">{bg}<div class="z"><div class="hook">{lines}</div>{sub}</div></div>'
    if spec["card"] == "end":
        return (f'<div class="card bg"><div class="z"><div class="brand">GramSetu</div>'
                f'<div class="sub">{e(spec["line1"])}</div><div class="small">{e(spec["line2"])}</div>'
                f'<div class="small">{e(spec["repo"])}</div><div class="tags">{e(spec["tags"])}</div>'
                f'<div class="q">{e(spec["question"])}</div></div></div>')
    if spec["card"] == "thumb":
        lines = "".join(f"<div>{ln}</div>" for ln in spec["lines"])
        return (f'<div class="card {"" if bg else "bg"}">{bg}<div class="z"><div class="hook">{lines}</div>'
                f'<div class="sub">{e(spec.get("sub", ""))}</div><div class="tags">{e(spec.get("tags", ""))}</div></div></div>')
    raise ValueError(spec["card"])


class Renderer:
    def __init__(self, cache: Path) -> None:
        self.cache = cache
        cache.mkdir(parents=True, exist_ok=True)
        self._pw = self._browser = None
        self.pages: dict[str, object] = {}

    async def __aenter__(self):
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch()
        return self

    async def __aexit__(self, *a):
        await self._browser.close()
        await self._pw.stop()

    async def _page(self, fmt: str):
        if fmt not in self.pages:
            sz = SIZES[fmt]
            ctx = await self._browser.new_context(viewport={"width": sz["w"], "height": sz["h"]})
            p = await ctx.new_page()
            vars_ = ";".join(f"--{k}:{v}" for k, v in sz.items() if k not in ("w", "h"))
            if fmt == "9x16":  # tall frame: stack the honesty labels under the step badges instead of beside them
                vars_ += "} .labels{left:var(--m);right:auto;top:calc(var(--m) + 74px);align-items:flex-start} .speed{top:calc(var(--m) + 170px);left:auto;right:var(--m);transform:none} .x{"
            await p.set_content(f'<html><head><link rel="stylesheet" href="{FONTS}"><style>{CSS} :root{{{vars_}}}</style></head>'
                                '<body><div id="r"></div><div style="position:absolute;opacity:0">ಕನ್ನಡ हिन्दी தமிழ் Latin</div></body></html>')
            await p.evaluate("document.fonts.ready")
            await p.wait_for_timeout(300)
            self.pages[fmt] = p
        return self.pages[fmt]

    async def render(self, fmt: str, spec: dict, transparent: bool = True) -> Path:
        key = hashlib.sha256(json.dumps([fmt, spec, transparent, CSS, SIZES[fmt]], sort_keys=True, default=str).encode()).hexdigest()[:20]
        out = self.cache / f"{fmt}_{key}.png"
        if out.exists():
            return out
        p = await self._page(fmt)
        body = card_html(spec) if spec.get("card") else layer_html(spec)
        await p.evaluate("(h) => { document.getElementById('r').innerHTML = h; }", body)
        await p.evaluate("document.fonts.ready")
        await p.evaluate("Promise.all([...document.images].map(i => i.decode().catch(() => null)))")
        await p.screenshot(path=str(out), omit_background=transparent)
        return out
