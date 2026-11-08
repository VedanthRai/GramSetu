# Build log — 2026-11-08

## Environment
Windows 11, Python 3.14.7, Node 24.20, git 2.55. No ffmpeg (not needed: WAV is encoded in the browser). Playwright
Chromium installed. The session folder path is very long, which hit Windows' 260-character path limit three times
(venv native modules, TTS cache filenames, git repack) — venv placed at `C:\Users\Anushree\.venvs\gramsetu`, cache names
shortened, `core.longpaths` enabled for the repo. **Recommendation: move the project to a short path such as `C:\gramsetu`.**

## Phase 0 — verification
- Read docs.gnani.ai (base URL, `X-API-Key-ID`, STT `/stt/v3`, TTS `/api/v1/tts/inference`, voices, limits, errors).
- Minimal smoke test per the credit restriction: Hindi Timbre ✅ (0.59 s) + Prisma ✅ (0.29 s, exact sentence).
  First Prisma result was lost to a console-encoding crash in my script (1 wasted call) — fixed and re-run.
- Kannada Timbre ✅ (2.71 s) + Prisma ✅ (1.46 s). Tamil/English deliberately not tested (credit implications unknown;
  no usage data in API responses).
- Discovered Timbre returns WAV headers with placeholder lengths → normaliser added.
- PM-KISAN facts: pmkisan.gov.in has an incomplete TLS chain (plain HTTP clients fail; verification not disabled);
  myscheme.gov.in renders client-side. Read pmkisan.gov.in in a real browser and copied 11 statements verbatim.
  Required documents are not on the page → "verification pending".
- No `ANTHROPIC_API_KEY` provided → app runs the labelled rules fallback; Anthropic provider implemented but unverified.

## Phases 1–4 — backend, portals, agent
Built config, sanitised logging, SQLite schema + seeded synthetic clinic, contracts, state machine, guards, i18n templates,
Gnani providers with cache/usage guard/lock, three reasoning providers, adapter registry, demo portals, policy, Playwright
executor, verifier, orchestrator, API + WebSocket.
First end-to-end run failures and fixes:
1. `tzdata` missing on Windows → added to requirements.
2. "ग्रामीण" (rural) matched the village keyword "ग्राम" → word-boundary-aware pattern.
3. Submit step expected an exact route but the portal redirects to `/confirmation/{ref}` → `route_prefix` expectation.
   (Verifier correctly refused to claim success in the meantime.)
4. Event data truncated mid-JSON broke the events endpoint → validated JSON storage.
5. Transcripts were being written to the events table → now only persisted with explicit retention.
6. Booking reference regex broken by removing spaces → normalise separators instead.
Result: Hindi scheme (with OTP pause, validation-error recovery, injection ignored), Kannada booking, and cancellation all
complete with verified records.

## Phase 5 — frontend
React 18 + strict TS + Vite + Tailwind. Workspace (voice / task / Mission Control), latency HUD, provider strip, judge mode,
speak-your-way, history + replay, sources, evaluation, status, settings (voice-only mode), privacy. Playwright UI test passes
at desktop and 390 px mobile with no console errors.

## Phase 6 — hardening
- Backend: 56 pytest tests pass (keyless; real Playwright; isolated DB). A real guard gap ("share my upi pin") was found
  by the tests and fixed. A test hang came from reusing the server-thread's browser on another event loop → fixed in test.
- ruff clean; frontend `tsc --noEmit`, ESLint (`--max-warnings=0`), 7 Vitest tests, production build all pass.

## Phase 7 — evaluation and live voice
- `run_eval.py`: 33 utterances. Found and fixed a real Kannada/Tamil inflection miss ("ಮೈಸೂರಿನಲ್ಲಿ").
- Live STT eval surfaced the TTS-cache long-path bug (5 Timbre calls wasted, audio lost) → fixed, re-run.
- Prisma CER 1.5% / WER 6% on 6 comparable synthetic items (+1 Hinglish item excluded: correct output in Devanagari vs
  Latin reference).
- `ui_voice_test.py`: real UI, fake microphone, live Prisma + Timbre. Found the HUD total measured playback *end* and
  included human review time → now Prisma + send→first audio. Measured 2.79 s.

## Follow-up — Tamil and English
With the user's go-ahead, `gnani_smoke_test.py --langs ta-IN en-IN` (4 calls): both transcripts exact; Timbre 1.92 s / 1.60 s,
Prisma 0.89 s / 0.61 s. The capability table updated itself and the UI now offers all four languages.

## Gnani usage
33 live calls total (9 smoke-test calls outside the app counter, 24 counted in-app: 11 Prisma, 13 Timbre). See `/status`.

## Phase 2: demo video, social assets, submission package
- ffmpeg 9.0.2 installed (winget). gitleaks could not be installed (download 504); a documented history scan is used instead (`scripts/secret_scan.py`).
- Product fixes found while recording (each with a regression test; now 59 backend tests):
  1. "बैंक खाता भी है … भरना है": the "ना " of भरना was read as "no" → yes/no is now evaluated in the clause that mentions the bank.
  2. Colloquial Kannada ownership "ನನ್ನ ಹೆಸರಲ್ಲೇ" was not recognised → added.
  3. Real Prisma Kannada output has **no punctuation**, so the name absorbed the rest of the sentence → inline names stop at known vocabulary (max 3 words).
  4. The agent only screenshotted page loads, so the filled form and the validation error were invisible in Mission Control → screenshots after entering details, on the validation error and after the correction.
  5. Stable ids/test ids on panels (no visual change) for the recorder.
- Voices: every voice is Gnani Timbre. Audition with live Prisma (`demo_assets/voices.json`): Kavin chosen for the user (kn), Saanvi stays GramSetu's voice, Pranav narrates. All accepted on the first attempt.
- Recorder: Chrome DevTools screencast (1920×1080, page zoom 1.25) instead of Playwright video; getUserMedia replaced by a Web Audio stream of the Timbre clip; layout, audio and state logged.
- Disk filled up (C: at 0 bytes free) during the first final take; deleted only this run's rehearsal frames and added free-space guards.
- Edit: `scripts/edit_demo.py` + `demo-output/edit/edl.json`; QC: `scripts/qc_video.py`; one-command rebuild: `scripts/build_video.sh` / `make video`.
