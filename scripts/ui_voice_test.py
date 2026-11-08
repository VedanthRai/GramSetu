"""LIVE voice-loop test through the real UI: Chromium's fake microphone plays a WAV, the page records it,
encodes 16 kHz WAV in the browser, sends it to live Gnani Prisma, and plays replies via live Gnani Timbre.

Spends Gnani credits (about 1 STT + 1-3 TTS calls; repeated phrases come from the TTS cache).
Usage: python scripts/ui_voice_test.py [--wav fixtures/audio/timbre_hi-IN_Nalini.wav] [--lang hi-IN]
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright, expect

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]


async def main(base: str, wav: Path, lang: str) -> None:
    settings = f'{{"language":"{lang}","voice":null,"autoplay":true,"voiceOnly":false,"retainHistory":false}}'
    async with async_playwright() as pw:
        b = await pw.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
                                           f"--use-file-for-fake-audio-capture={wav}", "--autoplay-policy=no-user-gesture-required"])
        ctx = await b.new_context(viewport={"width": 1440, "height": 1000}, permissions=["microphone"])
        await ctx.add_init_script(f"localStorage.setItem('gramsetu.settings.v1', '{settings}')")
        page = await ctx.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        await page.goto(base + "/app")
        await page.wait_for_timeout(1500)
        mic = page.locator("button[aria-pressed]").first
        await mic.click()                     # shows the consent explainer first
        await page.get_by_role("button", name="Allow microphone and start").click()
        await page.wait_for_timeout(3800)     # fake mic loops the file; record ~one pass
        await mic.click()                     # stop -> encode -> live Prisma
        transcript = page.get_by_test_id("transcript")
        await expect(transcript).to_be_visible(timeout=30000)
        text = await transcript.inner_text()
        print("Prisma transcript shown in UI:", text)
        await page.locator("button.btn-primary").filter(has_text="भेजें").first.click()
        await expect(page.locator("text=Latency HUD")).to_be_visible()
        await page.wait_for_function("document.body.innerText.includes('Timbre time-to-first-audio') && !/time-to-first-audio\\n—/.test(document.body.innerText)", timeout=60000)
        hud = await page.locator("dl").last.inner_text()
        print("Latency HUD:", " | ".join(hud.split("\n")))
        await page.screenshot(path=str(ROOT / "docs" / "screens" / "live-voice-turn.png"))
        await b.close()
        assert not errors, errors
    print("LIVE VOICE LOOP PASSED")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--wav", default=str(ROOT / "fixtures" / "audio" / "timbre_hi-IN_Nalini.wav"))
    ap.add_argument("--lang", default="hi-IN")
    a = ap.parse_args()
    asyncio.run(main(a.base, Path(a.wav), a.lang))
