> **Superseded:** the demo video is now recorded and edited automatically: `bash scripts/build_video.sh` (see `demo-output/REPORT.md`). The final video features the Kannada scheme flow. This manual script remains as a fallback for recording by hand.

# 90-second demo video script

All sample phrases are **pending native-speaker review** — please have a Hindi and a Kannada speaker check them (and the
spoken templates in `backend/app/services/i18n.py`) before recording.

## Before recording (checklist)

- [ ] `.env` has `GNANI_API_KEY`; optionally `REASONING_PROVIDER=anthropic` + `ANTHROPIC_API_KEY` (otherwise the UI
      honestly shows "Rules fallback (no AI model)" — say so in the video or configure Claude).
- [ ] `BROWSER_HEADLESS=false` if you want the real Chromium window visible next to the app (needs a display).
- [ ] Start: `scripts\dev.ps1` (Windows) or `scripts/dev.sh`, open http://127.0.0.1:8000.
- [ ] Dry run once with the mic (this also warms the Timbre cache for fixed phrases → faster on camera).
- [ ] `/status`: Prisma and Timbre show green "reachable"; note the local request count and the daily limit.
- [ ] Browser mic permission granted; speakers on; system notifications off.
- [ ] Recording tips: use a real phone or laptop mic; record one take in a slightly noisy room to show robustness;
      keep the Mission Control panel large (zoom the browser to 90% on a 1440p screen).

## Scenes

| Time | Scene | What to show / say |
|---|---|---|
| 0:00–0:15 | **The problem** | A farmer looking at an English-only portal. Voice-over: "Millions of people can speak their need, but can't navigate English-first forms." Cut to the GramSetu landing page. |
| 0:15–0:30 | **Speak** | Workspace in Hindi. Press the mic, say: *"मैं किसान हूँ। मेरे पास दो एकड़ जमीन है। मुझे बताइए कि इस योजना के लिए क्या जानकारी चाहिए और डेमो फॉर्म भरने में मदद कीजिए।"* Show the Prisma transcript appearing, editable. |
| 0:30–0:45 | **Follow-up by voice** | GramSetu speaks the source-backed guidance (point at the "Source: official PM-KISAN website" link) and asks for the name. Answer by voice. When it asks the state, say *"बेंगलुरु"* — it asks "Urban or Rural?" instead of guessing. |
| 0:45–1:05 | **Mission Control** | Approve. Show screenshots streaming, the plan with "why" for each step, and the timeline line **"Browser: validation error, recovered (entered 2.00)"**. Show the OTP pause: the simulated phone, the secure code box, and the line "not shown, logged, stored, spoken or sent to any AI model". |
| 1:05–1:20 | **Approval and verified receipt** | Final approval card (portal, action, data, consequence) → approve → green "Verified from the portal's stored record" + demo reference, read aloud by Timbre. Flash the printable summary card. |
| 1:20–1:30 | **Engineering proof** | Latency HUD (Prisma ms, Timbre time-to-first-audio), `/eval` page with denominators, and one line: "The AI never gets to click: every action is checked against an allow-list and the final step is always yours." |

Alternative scene 2–5 in Kannada (Workflow B): *"ನನಗೆ ನಾಳೆ ಬೆಳಿಗ್ಗೆ ವೈದ್ಯರ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಬೇಕು. ಕನ್ನಡದಲ್ಲಿ ಸಹಾಯ ಮಾಡಿ."*
→ department chips → real free slots from the clinic table → say a time → final approval → verified booking.
Then show a correction: *"ಬೇಡ, ಶುಕ್ರವಾರಕ್ಕೆ ಬದಲಾಯಿಸಿ"* ("no, change it to Friday") before approving.

## Exact reproduction (both demos, no microphone needed)

```bash
python scripts/e2e_flow.py              # Hindi scheme (OTP + recovery) and Kannada booking + cancellation, via the API
python scripts/ui_e2e.py                # same booking through the real UI with Playwright (saves docs/screens/*.png)
python scripts/ui_voice_test.py         # LIVE voice loop with a fake microphone (spends ~1-3 Gnani calls)
```
