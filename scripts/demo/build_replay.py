"""Build the static demo-replay page (docs/replay/) from a recorded take: no live API calls, safe to host on GitHub Pages.

Copies the master video, the agent's own screenshots (sensitive fields were already masked by the agent) and a
sanitised audit timeline (descriptions + times only; no OTP, no transcript beyond what the video shows). Also copies the
README GIF to docs/media/.
"""
from __future__ import annotations

import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "replay"


def main() -> None:
    edl = json.loads((ROOT / "demo-output" / "edit" / "edl.json").read_text(encoding="utf-8"))
    take = ROOT / "demo-output" / edl["take"]
    log = json.loads((take / "log_scheme.json").read_text(encoding="utf-8"))
    ev = log["evidence"]
    (OUT / "media").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs" / "media").mkdir(parents=True, exist_ok=True)
    final = ROOT / "demo-output" / "final"
    shutil.copy(final / "gramsetu_master_16x9.mp4", OUT / "media" / "gramsetu_master_16x9.mp4")
    shutil.copy(final / "gramsetu_master_16x9.captions_en.srt", OUT / "media" / "captions_en.srt")
    shutil.copy(final / "thumbnail_1920x1080.png", OUT / "media" / "poster.png")
    shutil.copy(final / "readme_loop.gif", ROOT / "docs" / "media" / "readme_loop.gif")
    shots = sorted((take / "agent_shots_scheme").glob("*.png"))
    for s in shots:
        shutil.copy(s, OUT / "media" / f"shot_{s.name}")
    t0 = log["frames"][0][0]
    timeline = []
    for e in log["events"]:
        if e["type"] == "app_event" and e.get("description"):
            d = re.sub(r"\b\d{4,}\b", "•••", e["description"])  # belt and braces: no long digit runs
            timeline.append({"t": round(e["t"] - t0, 1), "actor": e.get("actor"), "text": d})
    (OUT / "media" / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=0), encoding="utf-8")
    labels = ev.get("shot_labels", {})
    shot_html = "\n".join(
        f'<figure><img loading="lazy" src="media/shot_{s.name}" alt="Agent screenshot {s.stem}: {html.escape(labels.get(s.name, ""))}">'
        f'<figcaption>{s.stem} · {html.escape(labels.get(s.name, ""))}</figcaption></figure>' for s in shots)
    tl_html = "\n".join(f'<li><span class="t">{x["t"]:>6.1f}s</span><span class="a">{html.escape(x["actor"] or "")}</span>'
                        f'{html.escape(x["text"])}</li>' for x in timeline)
    page = TEMPLATE.replace("{{SHOTS}}", shot_html).replace("{{TIMELINE}}", tl_html).replace(
        "{{REF}}", html.escape((ev.get("result") or {}).get("reference", ""))).replace(
        "{{RECORD}}", html.escape(json.dumps(ev.get("db_record")))).replace(
        "{{RECOVERED}}", str(ev.get("validation_recovered"))).replace("{{INJECTION}}", str(ev.get("injection_ignored")))
    (OUT / "index.html").write_text(page, encoding="utf-8")
    print("wrote", OUT / "index.html", f"({len(shots)} screenshots, {len(timeline)} timeline events)")


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>GramSetu demo replay</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;600;800&family=Noto+Sans+Kannada:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{--bg:#f6f1e8;--card:#fffdf8;--ink:#14213a;--soft:#4a5870;--line:#e2d9c9;--acc:#c9640f;--ok:#1f7a45}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#0f1a2e;--card:#16223a;--ink:#e8edf6;--soft:#a9b5c9;--line:#2a3854;--acc:#ffa24d;--ok:#5fd08f}}
:root[data-theme="dark"]{--bg:#0f1a2e;--card:#16223a;--ink:#e8edf6;--soft:#a9b5c9;--line:#2a3854;--acc:#ffa24d;--ok:#5fd08f}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:'Noto Sans','Noto Sans Kannada',system-ui,sans-serif;line-height:1.5}
main{max-width:1100px;margin:0 auto;padding:32px 16px 64px}
h1{font-size:clamp(28px,5vw,44px);margin:0 0 6px;font-weight:800}h2{font-size:22px;margin:40px 0 12px}
.lede{color:var(--soft);max-width:70ch}
.note{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--acc);border-radius:10px;padding:12px 16px;margin:18px 0}
video{width:100%;border-radius:12px;border:1px solid var(--line);background:#000}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.facts div{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.facts b{display:block;font-size:13px;color:var(--soft);font-weight:600}
.shots{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}
figure{margin:0;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
figure img{display:block;width:100%;height:auto}figcaption{font-size:13px;padding:8px 10px;color:var(--soft)}
ol{list-style:none;padding:0;margin:0;background:var(--card);border:1px solid var(--line);border-radius:10px;max-height:480px;overflow:auto}
li{padding:6px 12px;border-bottom:1px solid var(--line);font-size:14px;display:flex;gap:10px;flex-wrap:wrap}
li .t{font-family:ui-monospace,monospace;color:var(--soft);min-width:58px}li .a{color:var(--acc);font-weight:600;min-width:70px}
a{color:var(--acc)}
</style></head>
<body><main>
<h1>GramSetu · demo replay</h1>
<p class="lede">A recording of one real run: a Kannada voice request, transcribed live by Gnani Prisma, answered by Gnani Timbre,
and a browser agent filling a <b>local demo portal with synthetic data</b>. This page is static. It makes no API calls and uses no keys.</p>
<div class="note">All voices in this video are AI-generated with Gnani Timbre, including the user's. The portal is a practice site,
not an official government website.</div>
<video controls preload="metadata" poster="media/poster.png" src="media/gramsetu_master_16x9.mp4">
<track kind="captions" srclang="en" label="English" src="media/captions_en.srt"></video>
<h2>Evidence from this take</h2>
<div class="facts">
<div><b>Demo reference</b>{{REF}}</div>
<div><b>Persisted demo record</b>{{RECORD}}</div>
<div><b>Validation error recovered</b>{{RECOVERED}}</div>
<div><b>Prompt-injection probe ignored</b>{{INJECTION}}</div>
</div>
<h2>The agent's own screenshots</h2>
<p class="lede">Captured by the agent during the run (sensitive fields masked). Shot 7 is the portal's validation error; shot 8 is the corrected value.</p>
<div class="shots">{{SHOTS}}</div>
<h2>Audit timeline (sanitised)</h2>
<ol>{{TIMELINE}}</ol>
<p class="lede" style="margin-top:24px">Source code and setup: see the repository README.</p>
</main></body></html>
"""

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
