"""Playwright end-to-end test of the REAL user interface (typed turns; autoplay off so no Gnani credits are spent).

Usage: python scripts/ui_e2e.py [--base http://127.0.0.1:8000] [--shots docs/screens]
Drives: landing -> workspace (Kannada clinic booking via chips + typing) -> approvals -> verified result,
then visits every page and checks for console errors. Saves screenshots for the docs.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright, expect

sys.stdout.reconfigure(encoding="utf-8")
SETTINGS = '{"language":"kn-IN","voice":null,"autoplay":false,"voiceOnly":false,"retainHistory":false}'


async def main(base: str, shots: Path) -> None:
    shots.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        ctx = await b.new_context(viewport={"width": 1440, "height": 1000})
        await ctx.add_init_script(f"localStorage.setItem('gramsetu.settings.v1', '{SETTINGS}')")
        page = await ctx.new_page()
        page.on("console", lambda m: m.type == "error" and errors.append(m.text))
        page.on("pageerror", lambda e: errors.append(str(e)))

        await page.goto(base + "/")
        await expect(page.get_by_role("heading", name="Government and healthcare services.")).to_be_visible()
        await page.screenshot(path=str(shots / "landing.png"))
        await page.get_by_role("link", name="Start speaking").click()
        await expect(page.get_by_text("ನಮಸ್ಕಾರ")).to_be_visible()

        async def typed(text: str) -> None:
            box = page.get_by_label("Type your message")
            if not await box.count():
                await page.get_by_role("button", name="ಟೈಪ್ ಮಾಡಿ").click()
            await box.fill(text)
            await box.press("Enter")

        await typed("ನನಗೆ ನಾಳೆ ಬೆಳಿಗ್ಗೆ ವೈದ್ಯರ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಬೇಕು")
        await page.get_by_role("button", name="ಸಾಮಾನ್ಯ ವೈದ್ಯಕೀಯ").click()   # department chip
        await page.get_by_role("button", name="ಬೆಂಗಳೂರು", exact=True).click()  # location chip
        slot = page.locator("button.rounded-full").filter(has_text=":").first
        if not await slot.count():  # tomorrow may be Sunday: answer the date question
            await typed("ನಾಡಿದ್ದು")
        await slot.click()
        await typed("ಸುಮಾ")
        await expect(page.get_by_role("button", name="ಸರಿಯಾಗಿದೆ")).to_be_visible()
        await page.screenshot(path=str(shots / "workspace-review.png"))
        await page.get_by_role("button", name="ಸರಿಯಾಗಿದೆ").click()
        await page.get_by_role("button", name="ಅನುಮತಿಸಿ ಮತ್ತು ಪ್ರಾರಂಭಿಸಿ").click()
        await expect(page.get_by_role("button", name="ಅಂತಿಮ ಹಂತಕ್ಕೆ ಅನುಮತಿಸಿ")).to_be_visible(timeout=45000)
        await page.screenshot(path=str(shots / "workspace-final-approval.png"))
        await page.get_by_role("button", name="ಅಂತಿಮ ಹಂತಕ್ಕೆ ಅನುಮತಿಸಿ").click()
        await expect(page.get_by_text("Verified from the portal's stored record")).to_be_visible(timeout=45000)
        ref = await page.locator("text=/Demo reference: GS-CL-/").first.inner_text()
        await page.screenshot(path=str(shots / "workspace-verified.png"), full_page=True)
        print("UI booking verified:", ref)

        for path, marker in [("/judge", "Judge mode"), ("/speak-your-way", "Speak your way"), ("/history", "Task history"),
                             ("/sources", "Sources and verification"), ("/eval", "Evaluation"), ("/status", "Providers and usage"),
                             ("/settings", "Settings"), ("/privacy", "Privacy and consent")]:
            await page.goto(base + path)
            await expect(page.get_by_role("heading", name=marker, exact=True)).to_be_visible()
            await page.screenshot(path=str(shots / f"{path.strip('/')}.png"))

        mobile = await b.new_context(viewport={"width": 390, "height": 844})
        await mobile.add_init_script(f"localStorage.setItem('gramsetu.settings.v1', '{SETTINGS}')")
        mp = await mobile.new_page()
        await mp.goto(base + "/app")
        await expect(mp.get_by_text("ನಮಸ್ಕಾರ")).to_be_visible()
        width = await mp.evaluate("document.documentElement.scrollWidth")
        assert width <= 390, f"horizontal scroll on mobile: {width}px"
        await mp.screenshot(path=str(shots / "mobile-workspace.png"))
        await b.close()
    real_errors = [e for e in errors if "favicon" not in e]
    assert not real_errors, f"console errors: {real_errors}"
    print("UI E2E PASSED (no console errors)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--shots", default=str(Path(__file__).resolve().parents[1] / "docs" / "screens"))
    a = ap.parse_args()
    asyncio.run(main(a.base, Path(a.shots)))
