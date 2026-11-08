"""Automated demo recorder: drives the REAL GramSetu UI against a running server and records it.

What is real in a --live take: the voice clip is fed to the page's microphone (getUserMedia is replaced by a stream that
plays the clip through Web Audio; the product's own recording, WAV encoding and Prisma upload code run unchanged), the
transcript comes from a live Gnani Prisma call, replies are spoken with live Gnani Timbre (repeated phrases come from the
TTS cache), and Playwright fills the local demo portal. Nothing is pre-edited.

Recording method: Chrome DevTools screencast (lossless-ish JPEG frames at 1920x1080 device pixels, timestamped), not
Playwright's built-in video (VP8 ~1 Mbit/s; blurry text). A Playwright video is also saved for comparison with --compare.

Every Timbre clip the page plays and every injected voice clip is logged with its wall-clock start, so
scripts/demo/build_video.py can mix the sound back in (Playwright video has no audio).

Usage:
  python scripts/record_demo.py --rehearsal --take 1          # live calls; output named REHEARSAL_take1 (never final)
  python scripts/record_demo.py --live --take 1               # final footage (live Prisma + Timbre)
  python scripts/record_demo.py --live --take 1 --scene clinic
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import shutil
import sqlite3
import sys
import time
from pathlib import Path

import httpx
import websockets
from playwright.async_api import Page, async_playwright

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from demo.clips import resolve_clips  # noqa: E402

VIEW_W, VIEW_H, DSF, ZOOM = 1920, 1080, 1, 1.25  # 1920x1080 frames; page zoomed 1.25x (layout of a 1536 px screen,
                                                  # rendered crisply at 1920). DevTools screencast captures CSS px.
UI = {  # labels from frontend/src/lib/ui.ts
    "hi-IN": {"send": "यही भेजें", "type": "टाइप करें", "start": "अनुमति दें और शुरू करें", "final": "अंतिम कदम की अनुमति दें",
              "submit_code": "पोर्टल पर कोड डालें", "looks_right": "सही है"},
    "kn-IN": {"send": "ಇದನ್ನು ಕಳುಹಿಸಿ", "type": "ಟೈಪ್ ಮಾಡಿ", "start": "ಅನುಮತಿಸಿ ಮತ್ತು ಪ್ರಾರಂಭಿಸಿ", "final": "ಅಂತಿಮ ಹಂತಕ್ಕೆ ಅನುಮತಿಸಿ",
              "submit_code": "ಪೋರ್ಟಲ್‌ನಲ್ಲಿ ಕೋಡ್ ನಮೂದಿಸಿ", "looks_right": "ಸರಿಯಾಗಿದೆ"},
}

INIT_JS = r"""
(() => {
  if (window.__gsDemo) return; window.__gsDemo = true;
  const log = (o) => { try { window.__gsLog(Object.assign({t: Date.now() / 1000}, o)); } catch (e) {} };
  // ---- visible cursor + click ripple (recorded video otherwise hides the pointer). Recorder-only, not product UI.
  const mount = () => {
    if (document.getElementById('__gs_cursor')) return;
    const st = document.createElement('style');
    st.textContent = `#__gs_cursor{position:fixed;left:0;top:0;width:28px;height:28px;z-index:2147483647;pointer-events:none;
      transform:translate(-3px,-2px);filter:drop-shadow(0 2px 3px rgba(0,0,0,.45));transition:opacity .2s}
      .__gs_ripple{position:fixed;z-index:2147483646;pointer-events:none;width:16px;height:16px;margin:-8px 0 0 -8px;border-radius:50%;
      border:3px solid #d9771f;animation:__gsr .6s ease-out forwards}
      @keyframes __gsr{from{transform:scale(.6);opacity:1}to{transform:scale(3.4);opacity:0}}`;
    document.documentElement.appendChild(st);
    const c = document.createElement('div'); c.id = '__gs_cursor';
    c.innerHTML = '<svg viewBox="0 0 24 24" width="28" height="28"><path d="M3 2l7.5 19 2.6-7.9L21 10.5z" fill="#fff" stroke="#111" stroke-width="1.6" stroke-linejoin="round"/></svg>';
    c.style.left = (window.__gsX || -50) + 'px'; c.style.top = (window.__gsY || -50) + 'px';
    document.documentElement.appendChild(c);
  };
  document.addEventListener('mousemove', (e) => { window.__gsX = e.clientX; window.__gsY = e.clientY; mount();
    const c = document.getElementById('__gs_cursor'); c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
  document.addEventListener('mousedown', (e) => { const r = document.createElement('div'); r.className = '__gs_ripple';
    r.style.left = e.clientX + 'px'; r.style.top = e.clientY + 'px'; document.documentElement.appendChild(r); setTimeout(() => r.remove(), 700); }, true);
  const zoom = () => { if (document.body) document.body.style.zoom = '__ZOOM__'; };
  document.addEventListener('DOMContentLoaded', () => { zoom(); mount(); });
  zoom();

  // ---- microphone: a stream that plays the clip the recorder queued (window.__gsNextClip). The app's MicRecorder,
  // WAV encoder and Prisma upload run unchanged on this stream.
  const realGUM = navigator.mediaDevices && navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
  if (navigator.mediaDevices) navigator.mediaDevices.getUserMedia = async (c) => {
    if (!c || !c.audio || !window.__gsNextClip) return realGUM(c);
    const clip = window.__gsNextClip; window.__gsNextClip = null;
    const ctx = new AudioContext();
    const buf = await ctx.decodeAudioData(await (await fetch(clip.url)).arrayBuffer());
    const dest = ctx.createMediaStreamDestination();
    const src = ctx.createBufferSource(); src.buffer = buf; src.connect(dest);
    const lead = 0.35; src.start(ctx.currentTime + lead);
    log({type: 'mic_clip_start', name: clip.name, offset: lead, dur: buf.duration});
    src.onended = () => log({type: 'mic_clip_end', name: clip.name});
    dest.stream.getTracks().forEach((tr) => { const stop = tr.stop.bind(tr); tr.stop = () => { stop(); ctx.close(); }; });
    return dest.stream;
  };

  // ---- capture each Timbre response in the page (text, headers, bytes) so the recorder can mix it back in later.
  const realFetch = window.fetch.bind(window);
  window.fetch = async (input, init) => {
    const url = typeof input === 'string' ? input : input.url;
    if (!url.endsWith('/api/speech/synthesize')) return realFetch(input, init);
    log({type: 'tts_request'});
    let req = {}; try { req = JSON.parse(init && init.body || '{}'); } catch (e) {}
    const r = await realFetch(input, init);
    try {
      const buf = await r.clone().arrayBuffer();
      const d = await crypto.subtle.digest('SHA-256', buf);
      const sha = Array.from(new Uint8Array(d)).map((x) => x.toString(16).padStart(2, '0')).join('');
      let bin = ''; const u8 = new Uint8Array(buf); for (let i = 0; i < u8.length; i += 0x8000) bin += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000));
      log({type: 'tts_response', status: r.status, sha, text: req.text, language: req.language, purpose: req.purpose,
           voice: r.headers.get('X-Voice'), cache: r.headers.get('X-Cache'), source: r.headers.get('X-Source'),
           server_ms: r.headers.get('X-Latency-Ms'), b64: r.ok ? btoa(bin) : null});
    } catch (e) { log({type: 'tts_response', status: -1, error: String(e)}); }
    return r;
  };

  // ---- log every audio clip the page plays (Timbre replies): sha256 of the bytes + start/end wall-clock times.
  const blobs = new Map();
  const createURL = URL.createObjectURL.bind(URL);
  URL.createObjectURL = (b) => { const u = createURL(b); if (b && b.type && b.type.startsWith('audio')) blobs.set(u, b); return u; };
  const play = HTMLMediaElement.prototype.play;
  HTMLMediaElement.prototype.play = function () {
    const el = this;
    if (!el.__gsHooked) {
      el.__gsHooked = true;
      el.addEventListener('playing', async () => {
        const t = Date.now() / 1000; const b = blobs.get(el.currentSrc || el.src);
        let sha = null; if (b) { const d = await crypto.subtle.digest('SHA-256', await b.arrayBuffer());
          sha = Array.from(new Uint8Array(d)).map((x) => x.toString(16).padStart(2, '0')).join(''); }
        window.__gsLog({type: 'audio_playing', t, sha, dur: el.duration});
      });
      el.addEventListener('ended', () => log({type: 'audio_ended'}));
      el.addEventListener('pause', () => { if (!el.ended) log({type: 'audio_paused', at: el.currentTime}); });
    }
    return play.apply(this, arguments);
  };
})();
"""


class Take:
    def __init__(self, out: Path, scene: str, base: str, live: bool, lang: str, autoplay: bool) -> None:
        self.dir = out
        self.scene, self.base, self.live, self.lang, self.autoplay = scene, base, live, lang, autoplay
        self.frames_dir = out / f"frames_{scene}"
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        (out / "tts").mkdir(exist_ok=True)
        self.frames: list[tuple[float, str]] = []
        self.events: list[dict] = []
        self.tts_by_sha: dict[str, dict] = {}
        self.sid: str | None = None
        self.session: dict = {}
        self.state_cv = asyncio.Condition()
        self.playing = 0
        self.pending_tts = 0
        self.mic_done = asyncio.Event()
        self.mx, self.my = VIEW_W / 2, VIEW_H / 2
        self.page: Page | None = None
        self.http = httpx.AsyncClient(base_url=base, timeout=60)

    # ------------------------------------------------------------------ logging
    def log(self, etype: str, **kw) -> None:
        ev = {"t": time.time(), "type": etype, **kw}
        self.events.append(ev)
        short = {k: v for k, v in ev.items() if k not in ("t",)}
        print(f"[{ev['t']:.2f}] {json.dumps(short, ensure_ascii=False)[:180]}")

    def mark(self, name: str) -> None:
        self.log("mark", name=name)

    async def on_page_log(self, _source, ev: dict) -> None:
        self.events.append(ev)
        if ev["type"] == "tts_request":
            self.pending_tts += 1
            return
        if ev["type"] == "tts_response":
            self.pending_tts = max(0, self.pending_tts - 1)
            b64 = ev.pop("b64", None)
            if ev.get("status") != 200 or not b64:
                print(f"[{ev['t']:.2f}] TIMBRE ERROR {ev.get('status')} {str(ev.get('text'))[:60]!r}")
                return
            path = self.dir / "tts" / f"{ev['sha'][:16]}.wav"
            path.write_bytes(base64.b64decode(b64))
            info = {k: ev.get(k) for k in ("text", "language", "voice", "cache", "source", "server_ms", "purpose")}
            info["file"] = str(path.relative_to(self.dir)).replace("\\", "/")
            self.tts_by_sha[ev["sha"]] = info
            print(f"[{ev['t']:.2f}] TIMBRE FETCHED cache={info['cache']} source={info['source']} {str(info['text'])[:50]!r}")
            return
        if ev["type"] == "audio_playing":
            self.playing += 1
            info = self.tts_by_sha.get(ev.get("sha") or "")
            ev["tts"] = info
            print(f"[{ev['t']:.2f}] TIMBRE PLAYING {info and info['text'][:60]!r} dur={ev.get('dur')}")
        elif ev["type"] in ("audio_ended", "audio_paused"):
            self.playing = max(0, self.playing - 1)
        elif ev["type"] == "mic_clip_end":
            self.mic_done.set()
        elif ev["type"] == "mic_clip_start":
            print(f"[{ev['t']:.2f}] MIC CLIP {ev['name']} ({ev['dur']:.1f}s)")

    async def on_response(self, resp) -> None:
        url = resp.url
        try:
            if url.endswith("/api/sessions") and resp.request.method == "POST":
                self.sid = (await resp.json())["session"]["id"]
                self.log("session_created", sid=self.sid)
            elif "/api/speech/transcribe" in url:
                j = await resp.json()
                self.log("prisma_result", status=resp.status, latency_ms=j.get("latency_ms"), transcript=j.get("transcript"),
                         source=j.get("source"))
        except Exception as e:  # never let logging break the take
            print("response log error:", type(e).__name__, e)

    # ------------------------------------------------------------------ live state via the app's WebSocket
    async def follow_ws(self) -> None:
        while not self.sid:
            await asyncio.sleep(0.05)
        sid = self.sid
        url = self.base.replace("http", "ws") + f"/api/ws/sessions/{sid}"
        while self.sid == sid:
            try:
                async with websockets.connect(url) as ws:
                    await self.refresh()
                    async for msg in ws:
                        if self.sid != sid:
                            return
                        try:
                            m = json.loads(msg)
                        except ValueError:
                            continue
                        if m.get("type") == "event" and m.get("kind") != "message":
                            self.log("app_event", actor=m.get("actor"), event_kind=m.get("kind"), description=m.get("description"))
                        await self.refresh()
            except Exception as e:  # reconnect, like the UI does
                print("ws reconnect:", type(e).__name__, e)
                await asyncio.sleep(0.5)

    async def refresh(self) -> None:
        r = await self.http.get(f"/api/sessions/{self.sid}")
        s = r.json()["session"]
        async with self.state_cv:
            if s["state"] != self.session.get("state"):
                self.log("state", state=s["state"], expected=s.get("expected_field"))
            self.session = s
            self.state_cv.notify_all()

    async def wait_state(self, states: set[str], timeout: float = 90, expected: str | None = None) -> dict:
        async def ok() -> bool:
            return self.session.get("state") in states and (expected is None or self.session.get("expected_field") == expected)
        async with self.state_cv:
            await asyncio.wait_for(self.state_cv.wait_for(lambda: self.session.get("state") in states and
                                                          (expected is None or self.session.get("expected_field") == expected)), timeout)
        if self.session["state"] == "FAILED":
            raise RuntimeError("task FAILED: " + self.session["messages"][-1]["text"])
        return self.session

    async def speech_idle(self, quiet: float = 1.2, timeout: float = 120) -> None:
        """Wait until Timbre playback has finished and nothing is queued (real playback events, not a fixed sleep)."""
        if not self.autoplay:
            return
        t0 = time.time()
        calm_since = None
        while time.time() - t0 < timeout:
            busy = self.playing > 0 or self.pending_tts > 0
            if busy:
                calm_since = None
            elif calm_since is None:
                calm_since = time.time()
            elif time.time() - calm_since >= quiet:
                return
            await asyncio.sleep(0.1)
        self.log("warn", msg="speech_idle timeout")

    # ------------------------------------------------------------------ human-like input
    async def move_to(self, x: float, y: float) -> None:
        dist = ((x - self.mx) ** 2 + (y - self.my) ** 2) ** 0.5
        await self.page.mouse.move(x, y, steps=max(8, int(dist / 18)))
        self.mx, self.my = x, y

    async def click(self, locator, pause: float = 0.35) -> None:
        await locator.scroll_into_view_if_needed()
        box = await locator.bounding_box()
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        await self.move_to(x, y)
        await asyncio.sleep(pause)
        await self.page.mouse.click(x, y)
        await asyncio.sleep(0.15)

    async def hold(self, seconds: float) -> None:
        """Readability pause (minimum on-screen time). Content timing itself always follows real events."""
        await asyncio.sleep(seconds)

    async def element_box(self, selector: str, name: str) -> None:
        b = await self.page.evaluate("""(sel) => { const e = document.querySelector(sel); if (!e) return null;
            const r = e.getBoundingClientRect(); return {x: r.x, y: r.y, w: r.width, h: r.height}; }""", selector)
        if b:
            self.log("box", name=name, **{k: round(v) for k, v in b.items()})

    async def scroll_to(self, selector: str, block: str = "start") -> None:
        """Scroll with the mouse wheel until the element sits where we want it (scrollIntoView is unreliable with the
        page zoom). Visible as a normal scroll in the recording."""
        loc = self.page.locator(selector).first
        await loc.wait_for(timeout=15000)
        for _ in range(6):
            box = await loc.bounding_box()
            if not box:
                break
            target = 70 if block == "start" else (VIEW_H - box["height"]) / 2 if block == "center" else VIEW_H - box["height"] - 20
            delta = box["y"] - max(70, target)
            if abs(delta) < 12:
                break
            await self.page.mouse.wheel(0, delta)
            await asyncio.sleep(0.45)


LAYOUT_SELECTORS = {
    "voice": "#voice-panel", "task": "#task-panel", "mc": "#mission-control",
    "mc_shot": "#mission-control img[alt^='Portal screenshot']", "transcript": "[data-testid='transcript']",
    "receipt": "[data-testid='verified-receipt']", "hud": "[data-testid='latency-hud']", "phone": "[aria-label='Simulated phone']",
    "otp": "#otp-box", "timeline": "#mission-control ol[aria-live]", "portal_form": "form", "fields": "#task-panel dl, #task-panel table",
}


async def layout_sampler(take: Take) -> None:
    """Every 0.4 s, log where key elements are on screen (frame px), so the editor zooms onto real elements."""
    while True:
        try:
            boxes = await take.page.evaluate("""(sels) => { const o = {}; for (const [k, s] of Object.entries(sels)) {
                const e = document.querySelector(s); if (!e) continue; const r = e.getBoundingClientRect();
                if (r.width && r.height) o[k] = [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)]; }
                return o; }""", LAYOUT_SELECTORS)
            take.events.append({"t": time.time(), "type": "layout", "boxes": boxes})
        except Exception:
            pass
        await asyncio.sleep(0.4)


async def screencast(take: Take, cdp) -> None:
    n = 0

    async def on_frame(params):
        nonlocal n
        n += 1
        if n % 200 == 0 and shutil.disk_usage(take.frames_dir).free < 1.2e9:
            raise SystemExit("Stopping: less than 1.2 GB free on disk")
        ts = params["metadata"].get("timestamp") or time.time()
        name = f"{n:06d}.jpg"
        (take.frames_dir / name).write_bytes(base64.b64decode(params["data"]))
        take.frames.append((ts, name))
        try:
            await cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})
        except Exception:
            pass

    cdp.on("Page.screencastFrame", lambda p: asyncio.ensure_future(on_frame(p)))
    await cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 82, "maxWidth": 1920, "maxHeight": 1080, "everyNthFrame": 1})


# ====================================================================== scenes
async def say(take: Take, clip: dict, typed_fallback: bool) -> None:
    """Speak a clip into the real microphone path (live), or type its text (rehearsal: fixture mode has no Prisma)."""
    page = take.page
    lang = take.lang
    if typed_fallback:
        await type_text(take, clip["text"])
        return
    take.mic_done.clear()
    await page.evaluate("(c) => { window.__gsNextClip = c; }", {"url": f"/__demo_audio/{clip['file_name']}", "name": clip["name"]})
    mic = page.locator("button[aria-pressed]").first
    take.mark(f"mic_click:{clip['name']}")
    await take.click(mic)
    allow = page.get_by_role("button", name="Allow microphone and start")
    if await allow.count():
        await take.hold(1.2)  # the consent explainer is part of the product; let viewers see it
        await take.click(allow)
    await asyncio.wait_for(take.mic_done.wait(), 40)
    await take.hold(0.6)
    take.mark(f"mic_stop:{clip['name']}")
    await take.click(mic, pause=0.1)
    tr = page.get_by_test_id("transcript")
    await tr.wait_for(timeout=40000)
    take.mark(f"transcript_shown:{clip['name']}")
    take.log("transcript_ui", text=await tr.inner_text())
    await take.hold(2.4)  # time to read the transcript before sending
    await take.click(page.locator("button.btn-primary").filter(has_text=UI[lang]["send"]).first)
    take.mark(f"sent:{clip['name']}")


async def type_text(take: Take, text: str) -> None:
    page = take.page
    box = page.locator("#typed")
    if not await box.is_visible():
        await take.click(page.get_by_role("button", name=UI[take.lang]["type"]))
    await take.click(box, pause=0.2)
    await page.keyboard.type(text, delay=70)
    await take.hold(0.6)
    take.mark("typed_send")
    await take.click(page.locator("form button.btn-primary"))


async def open_app(take: Take, ctx, lang: str) -> Page:
    settings = json.dumps({"language": lang, "voice": None, "autoplay": take.autoplay, "voiceOnly": False, "retainHistory": False})
    await ctx.add_init_script(f"localStorage.setItem('gramsetu.settings.v1', {json.dumps(settings)})")
    page = take.page
    await page.goto(take.base + "/app")
    await page.get_by_text("Browser Mission Control").wait_for()
    asyncio.ensure_future(take.follow_ws())
    while not take.session:
        await asyncio.sleep(0.1)
    return page


async def scene_problem(take: Take, ctx, clips) -> None:
    page = take.page
    take.mark("problem_start")
    await page.goto(take.base + "/portal/scheme/")
    await take.hold(1.0)
    await take.click(page.get_by_role("button", name="Start demo application"))
    await page.wait_for_load_state("networkidle")
    take.mark("problem_form")
    await take.move_to(VIEW_W * 0.45, VIEW_H * 0.55)
    for _ in range(4):
        await page.mouse.wheel(0, 140)
        await take.hold(0.7)
    await take.hold(1.5)
    take.mark("problem_end")


async def scene_scheme(take: Take, ctx, clips, rehearsal: bool) -> None:
    L = take.lang
    page = await open_app(take, ctx, L)
    take.mark("app_loaded")
    await take.speech_idle()
    await take.element_box("main", "main")
    await take.hold(1.0)
    take.mark("scheme_start")
    await say(take, clips["kn_request"], rehearsal)
    await take.wait_state({"NEEDS_CLARIFICATION", "FAILED"}, expected="district")
    take.mark("district_question")
    await take.speech_idle()
    await take.hold(0.8)
    await say(take, clips["kn_district"], rehearsal)
    await take.wait_state({"NEEDS_CLARIFICATION", "FAILED"}, expected="mobile")
    take.mark("mobile_question")
    await take.speech_idle()
    await type_text(take, "9876543210")  # synthetic demo number (typed, as the prompt suggests)
    await take.wait_state({"PREVIEWING_TASK", "FAILED"})
    take.mark("review_shown")
    await take.speech_idle()
    await take.hold(1.0)
    await say(take, clips["kn_confirm"], rehearsal)
    await take.wait_state({"AWAITING_CONSENT", "FAILED"})
    take.mark("consent_shown")
    await take.speech_idle()
    await take.hold(1.2)
    approve = page.get_by_role("button", name=UI[L]["start"])
    await approve.scroll_into_view_if_needed()
    await take.click(approve)
    take.mark("approve_start_click")
    await take.scroll_to("#mission-control")
    await take.element_box("#mission-control", "mission_control")
    await take.wait_state({"EXECUTING", "FAILED"}, timeout=20)
    take.mark("executing")
    await take.wait_state({"AWAITING_USER_ACTION", "FAILED"}, timeout=120)
    take.mark("otp_pause")
    phone = page.locator("[aria-label='Simulated phone'] .font-mono")
    await phone.wait_for(timeout=30000)
    await take.hold(1.0)
    # Review what the agent did, using Mission Control's own screenshot history (real screenshots it captured).
    thumbs = page.locator("button[aria-label^='Show screenshot']")
    n = await thumbs.count()
    await take.scroll_to("#mission-control")
    await take.element_box("#mission-control", "mission_control")
    take.mark("history_start")
    for i in range(n):
        await take.click(thumbs.nth(i), pause=0.15)
        take.log("history_shot", index=i + 1, of=n)
        await take.hold(1.1)
    take.mark("history_end")
    await take.speech_idle()
    await take.element_box("[aria-label='Simulated phone']", "phone")
    await take.hold(1.0)
    code = (await phone.inner_text()).strip()  # read off the simulated phone like a user; never logged
    await take.click(page.locator("#otp-box"), pause=0.3)
    await page.keyboard.type(code, delay=160)
    del code
    await take.hold(0.5)
    take.mark("otp_submit")
    await take.click(page.get_by_role("button", name=UI[L]["submit_code"]))
    await take.wait_state({"PAUSED_FOR_CONFIRMATION", "FAILED"}, timeout=120)
    take.mark("final_approval_shown")
    await take.speech_idle()
    await take.hold(2.0)
    take.mark("approve_final_click")
    await take.click(page.get_by_role("button", name=UI[L]["final"]))
    await take.wait_state({"COMPLETED", "FAILED"}, timeout=120)
    take.mark("completed")
    await take.scroll_to("[data-testid='verified-receipt']", "center")
    await take.element_box("[data-testid='verified-receipt']", "receipt")
    take.mark("receipt_shown")
    await take.speech_idle()
    await take.hold(1.0)
    await take.scroll_to("[data-testid='latency-hud']", "center")
    await take.element_box("[data-testid='latency-hud']", "hud")
    await take.move_to(VIEW_W * 0.3, VIEW_H * 0.8)
    take.mark("hud_shown")
    await take.hold(3.5)
    take.log("hud_text", text=await page.locator("dl").last.inner_text())
    take.mark("scheme_end")


async def scene_clinic(take: Take, ctx, clips, rehearsal: bool) -> None:
    L = take.lang
    page = await open_app(take, ctx, L)
    take.mark("clinic_start")
    await take.hold(0.8)
    await say(take, clips["hi_clinic"], rehearsal)
    # Per field, answers to try in order (a repeated question means the previous answer had no free slot).
    answers = {"hi-IN": {"department": ["सामान्य"], "location": ["बेंगलुरु"], "appointment_date": ["परसों", "शुक्रवार", "सोमवार", "मंगलवार"],
                         "time_preference": ["दोपहर", "शाम", "सुबह"], "slot_time": ["पहला"], "slot": ["पहला"], "patient_name": ["सुमा"]},
               "kn-IN": {"department": ["ಸಾಮಾನ್ಯ"], "location": ["ಬೆಂಗಳೂರು"], "appointment_date": ["ನಾಡಿದ್ದು", "ಶುಕ್ರವಾರ", "ಸೋಮವಾರ"],
                         "time_preference": ["ಮಧ್ಯಾಹ್ನ", "ಸಂಜೆ"], "slot_time": ["ಮೊದಲ"], "slot": ["ಮೊದಲ"], "patient_name": ["ಸುಮಾ"]}}[L]
    asked: dict[str, int] = {}
    for _ in range(12):
        s = await take.wait_state({"NEEDS_CLARIFICATION", "PREVIEWING_TASK", "FAILED"})
        if s["state"] == "PREVIEWING_TASK":
            break
        field = s.get("expected_field")
        opts = answers.get(field, [""])
        want = opts[min(asked.get(field, 0), len(opts) - 1)]
        asked[field] = asked.get(field, 0) + 1
        if field == "time_preference" or (field == "appointment_date" and asked[field] > 1):
            # "no free <period> slots": move to the next day and a different time of day
            pass
        await take.hold(0.9)
        chip = page.locator("button.rounded-full").filter(has_text=want) if want else None
        before = len(s["messages"])
        if chip is not None and await chip.count():
            await take.click(chip.first)
        elif want:
            await type_text(take, want)
        else:  # unknown question: pick the first offered option, like a user would
            await take.click(page.locator("button.rounded-full").first)
        async with take.state_cv:
            await asyncio.wait_for(take.state_cv.wait_for(lambda before=before: len(take.session["messages"]) > before + 1), 30)
    take.mark("clinic_review")
    await take.hold(1.0)
    await take.click(page.get_by_role("button", name=UI[L]["looks_right"]))
    await take.wait_state({"AWAITING_CONSENT", "FAILED"})
    await take.hold(0.8)
    await take.click(page.get_by_role("button", name=UI[L]["start"]))
    await take.wait_state({"PAUSED_FOR_CONFIRMATION", "FAILED"}, timeout=120)
    take.mark("clinic_final")
    await take.hold(1.2)
    await take.click(page.get_by_role("button", name=UI[L]["final"]))
    await take.wait_state({"COMPLETED", "FAILED"}, timeout=120)
    take.mark("clinic_completed")
    await take.hold(2.5)
    take.mark("clinic_end")


# ====================================================================== runner
def db_has_record(ref: str) -> dict:
    """Independent check that the receipt came from a persisted demo record (reads the SQLite file directly)."""
    con = sqlite3.connect(ROOT / "data" / "gramsetu.db")
    out = {}
    for (table,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        cols = [r[1] for r in con.execute(f"PRAGMA table_info({table})")]
        for col in cols:
            if "ref" in col.lower():
                n = con.execute(f"SELECT COUNT(*) FROM {table} WHERE {col}=?", (ref,)).fetchone()[0]
                if n:
                    out[f"{table}.{col}"] = n
    con.close()
    return out


async def run_scene(scene: str, args, takedir: Path, clips: dict) -> dict:
    lang = {"problem": "en-IN", "scheme": "kn-IN", "clinic": "hi-IN"}[scene]
    take = Take(takedir, scene, args.base, True, lang, autoplay=(scene == "scheme"))
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(args=["--autoplay-policy=no-user-gesture-required", "--use-fake-ui-for-media-stream",
                                                 "--hide-scrollbars", "--force-color-profile=srgb"])
        kw = dict(viewport={"width": VIEW_W, "height": VIEW_H}, device_scale_factor=DSF, permissions=["microphone"],
                  locale="en-IN", timezone_id="Asia/Kolkata")
        if args.compare:
            kw.update(record_video_dir=str(takedir / f"pw_video_{scene}"), record_video_size={"width": 1920, "height": 1080})
        ctx = await browser.new_context(**kw)
        await ctx.expose_binding("__gsLog", take.on_page_log)
        await ctx.add_init_script(INIT_JS.replace("__ZOOM__", str(ZOOM)))

        async def serve_clip(route):
            name = route.request.url.rsplit("/", 1)[-1]
            await route.fulfill(path=str(clips["_by_file"][name]), content_type="audio/wav")
        await ctx.route("**/__demo_audio/*", serve_clip)
        page = await ctx.new_page()
        take.page = page
        page.on("response", lambda r: asyncio.ensure_future(take.on_response(r)))
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: asyncio.ensure_future(d.dismiss()))
        cdp = await ctx.new_cdp_session(page)
        await page.goto("about:blank")
        await screencast(take, cdp)
        sampler = asyncio.ensure_future(layout_sampler(take))
        take.mark("record_start")
        ok, err = True, None
        try:
            if scene == "problem":
                await scene_problem(take, ctx, clips)
            elif scene == "scheme":
                await scene_scheme(take, ctx, clips, rehearsal=False)
            else:
                await scene_clinic(take, ctx, clips, rehearsal=False)
        except Exception as e:
            ok, err = False, f"{type(e).__name__}: {e}"
            take.log("scene_error", error=err)
            await page.screenshot(path=str(takedir / f"error_{scene}.png"))
        await asyncio.sleep(0.5)
        take.mark("record_end")
        sampler.cancel()
        await cdp.send("Page.stopScreencast")
        await asyncio.sleep(0.3)
        await ctx.close()
        await browser.close()
    # evidence: audit log + persisted record
    evidence: dict = {"scene": scene, "ok": ok, "error": err, "page_errors": errors, "session_id": take.sid}
    if take.sid and scene != "problem":
        evs = (await take.http.get(f"/api/sessions/{take.sid}/events")).json()["events"]
        evidence["audit"] = [e["description"] for e in evs if e["kind"] != "message"]
        evidence["shot_labels"] = {}
        for e in evs:
            d = e.get("data") or {}
            if isinstance(d, str):
                try:
                    d = json.loads(d)
                except ValueError:
                    d = {}
            if isinstance(d, dict) and d.get("screenshot"):
                evidence["shot_labels"].setdefault(d["screenshot"], e["description"].replace("Browser: ", ""))
        s = take.session
        evidence["final_state"] = s.get("state")
        evidence["result"] = s.get("result")
        evidence["validation_recovered"] = any("recovered" in d for d in evidence["audit"])
        evidence["injection_ignored"] = any("instruction-like" in d or "injection" in d.lower() for d in evidence["audit"])
        ref = (s.get("result") or {}).get("reference")
        evidence["db_record"] = db_has_record(ref) if ref else {}
        shots = takedir / f"agent_shots_{scene}"   # the agent's own screenshots (same images Mission Control shows)
        shots.mkdir(exist_ok=True)
        for i in range(1, 100):
            r = await take.http.get(f"/api/sessions/{take.sid}/screenshot", params={"name": f"{i:03d}.png"})
            if r.status_code != 200:
                break
            (shots / f"{i:03d}.png").write_bytes(r.content)
        evidence["agent_screenshots"] = i - 1
    usage = (await take.http.get("/api/usage")).json()
    evidence["usage_after"] = {"today_calls": usage["today_calls"], "rows": usage["rows"]}
    await take.http.aclose()
    (takedir / f"log_{scene}.json").write_text(json.dumps({"frames": take.frames, "events": take.events,
                                                          "tts": take.tts_by_sha, "evidence": evidence,
                                                          "viewport": [VIEW_W, VIEW_H, DSF]}, ensure_ascii=False, indent=1),
                                              encoding="utf-8")
    print(f"== scene {scene}: ok={ok} frames={len(take.frames)} err={err}")
    return evidence


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--take", type=int, default=1)
    ap.add_argument("--scene", choices=["problem", "scheme", "clinic", "all"], default="all")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--rehearsal", action="store_true", help="live calls, output named REHEARSAL_ (never used in final/)")
    mode.add_argument("--live", action="store_true", help="final footage: live Prisma + Timbre")
    ap.add_argument("--output", default=str(ROOT / "demo-output"))
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--compare", action="store_true", help="also save Playwright's own video for a quality comparison")
    args = ap.parse_args()

    free = shutil.disk_usage(ROOT).free
    if free < 1.5e9:
        sys.exit(f"Refusing to record: only {free / 1e9:.1f} GB free on disk (a take needs about 0.6-1 GB).")
    status = httpx.get(args.base + "/api/usage").json()
    if status["fixture_mode"]:
        sys.exit("Refusing: the server runs with GNANI_FIXTURE_MODE=true; recordings must use live Gnani calls.")
    name = f"take{args.take}" if args.live else f"REHEARSAL_take{args.take}"
    takedir = Path(args.output) / "takes" / name
    takedir.mkdir(parents=True, exist_ok=True)
    clips = resolve_clips(args.base, generate=True)
    scenes = ["problem", "scheme"] if args.scene == "all" else [args.scene]  # clinic: --scene clinic
    t0 = time.time()
    before = status["today_calls"]
    results = [await run_scene(sc, args, takedir, clips) for sc in scenes]
    after = httpx.get(args.base + "/api/usage").json()["today_calls"]
    summary = {"take": name, "live": args.live, "scenes": results, "seconds": round(time.time() - t0, 1),
               "gnani_calls_counted_by_app": after - before,
               "clips": {k: {kk: vv for kk, vv in v.items() if kk != "path"} for k, v in clips.items() if not k.startswith("_")}}
    prev = takedir / "summary.json"
    if prev.exists() and args.scene != "all":
        old = json.loads(prev.read_text(encoding="utf-8"))
        old_sc = [r for r in old.get("scenes", []) if r["scene"] not in scenes]
        summary["scenes"] = old_sc + results
        summary["gnani_calls_counted_by_app"] += old.get("gnani_calls_counted_by_app", 0)
    prev.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("take", "seconds", "gnani_calls_counted_by_app")}))
    print("ALL OK" if all(r["ok"] for r in results) else "SOME SCENES FAILED")


if __name__ == "__main__":
    asyncio.run(main())
