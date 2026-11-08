# GramSetu

**Speak your language. GramSetu fills the online form with you, and only submits when you say so.**

A voice-first assistant for government and healthcare web services in Kannada, Hindi, Tamil and English, built on
**Gnani Prisma** (speech-to-text) and **Gnani Timbre** (text-to-speech).

![GramSetu filling a demo scheme form from a Kannada voice request](docs/media/readme_loop.gif)

> The GIF and the demo video show a real run: live Prisma transcription, a real Playwright browser on a **local demo
> portal with synthetic data**, and Timbre speaking. **All voices in the demo are AI-generated with Gnani Timbre**,
> including the "user". Demo video: [Watch 90s Full Demo (1080p)](docs/replay/media/gramsetu_master_16x9.mp4) · static replay page: see
> [Demo replay](#demo-replay-no-live-api-calls).

## How it works, in 3 steps

1. **Speak.** Say what you need in your language. Gnani Prisma writes it down, in your script, and you check the words.
2. **Review.** GramSetu fills in what it understood, asks out loud (Gnani Timbre) only for what is missing or unclear,
   for example "Bengaluru Urban or Bengaluru Rural?", and reads back a summary.
3. **Watch it work.** After you approve, a browser agent fills the portal while you watch every screenshot. It stops for
   your one-time code and asks again before the final submit. "Done" is said only when the portal's stored record is found.

## What is real and what is demo

| Real (runs in the demo) | Demo / not real |
|---|---|
| Live Gnani Prisma transcription (`prisma-v2.5`) of the spoken audio | The two portals are local practice sites marked "NOT AN OFFICIAL GOVERNMENT WEBSITE" |
| Live Gnani Timbre speech (`timbre-v2.5`); repeated phrases come from a cache | All names, numbers, doctors, slots and records are synthetic |
| A real Playwright browser filling multi-step forms, including a real validation error and recovery | The "user" voice in the video is AI-generated (Timbre), not a person |
| Approval gates, OTP pause, audit timeline, verification against the stored record (SQLite) | Nothing is sent to any real government or hospital system |
| Latency HUD numbers, evaluation results, smoke-test results | The default language understanding is a **rules engine (no AI model)**; Claude is supported but was not verified (no key) |

## Features

* Voice in 4 languages verified with our key: Kannada, Hindi, Tamil, English (Prisma + Timbre each). Hinglish audio
  sent as Hindi came back correctly in Devanagari, but a code-mixed mode is not verified.
* **Workflow A:** PM-KISAN-style scheme form. Guidance quotes the official pmkisan.gov.in text with a retrieval date and never declares anyone eligible.
* **Workflow B:** clinic booking from a real slots table, with no double booking under concurrency, plus a spoken correction ("no, make it Friday") and cancellation.
* **Browser Mission Control:** live screenshots, the plan with a "why" for each step, an audit timeline, and an interrupt button.
* Safety: scam/OTP guard, emergency stop (112), medical-advice refusal, prompt-injection-resistant browser policy, same-origin only.
* Latency HUD, a local Gnani usage counter, judge mode, voice-only mode, history, and a printable/spoken summary card.

## Architecture

![Architecture: user voice → Gnani Prisma → reasoning provider → policy validator → Playwright → Gnani Timbre, with approval, OTP and verification gates](docs/architecture.png)

Source: [docs/architecture.svg](docs/architecture.svg). Details: [docs/architecture.md](docs/architecture.md) ·
Gnani integration: [docs/how-gnani-models-are-used.md](docs/how-gnani-models-are-used.md).

## Setup and run

Requirements: Python 3.11+ (tested 3.14), Node 18+ (tested 24), ffmpeg (only for the demo-video pipeline), internet access for Gnani.

```bash
cp .env.example .env                       # put GNANI_API_KEY=... in .env (never commit it)
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.txt     # macOS/Linux: .venv/bin/python
.venv/Scripts/python -m playwright install chromium
python scripts/gnani_smoke_test.py         # verifies the key + Hindi (2 Gnani calls); --langs kn-IN ta-IN en-IN
scripts/dev.sh                              # Windows PowerShell: scripts\dev.ps1 → http://127.0.0.1:8000
```

Open http://127.0.0.1:8000 and choose **Start speaking**. Optional: `REASONING_PROVIDER=anthropic` with `ANTHROPIC_API_KEY` to use Claude.
On Windows, keep the project on a short path (e.g. `C:\gramsetu`) because of the 260-character path limit.

## Verified languages (from the capability table)

| Language | Prisma | Timbre | Voices verified |
|---|---|---|---|
| Kannada `kn-IN` | verified | verified | Saanvi (+ Kavin used in the demo video) |
| Hindi `hi-IN` | verified | verified | Nalini (+ Deepak used for a demo line) |
| Tamil `ta-IN` | verified | verified | Asmita |
| English `en-IN` | verified | verified | Kaveri (+ Pranav used for narration) |

## Measured latency (real calls)

* Smoke tests, Timbre / Prisma: Hindi 2.14 s / 1.06 s, Kannada 2.71 s / 1.46 s, Tamil 1.92 s / 0.89 s, English 1.60 s / 0.61 s.
* Demo take: Prisma took 3.76 s on a 15.3 s Kannada request and 0.30 s on a short "yes". The Latency HUD on the last
  voice turn showed 0.55 s total machine time, with a cached Timbre reply.
* Earlier live UI test: 2.79 s from send to first reply audio. Latency varies a lot between calls.

## Evaluation (sample sizes included)

`python scripts/run_eval.py --stt --sample 7 --e2e http://127.0.0.1:8000`. Results are in [docs/eval_results.json](docs/eval_results.json).

| Metric | Result |
|---|---|
| Intent accuracy | 33/33 utterances |
| Field extraction | 39/39 expected fields |
| Clarification answers understood / spoken corrections applied | 6/6 · 3/3 |
| Safety guards (scam / emergency / medical) | 5/5 |
| Unsafe actions rejected by policy / legitimate actions accepted | 12/12 · 31/31 |
| Double booking prevented | 1 of 8 concurrent attempts succeeds |
| End-to-end workflows verified | 2/2 |
| Prisma CER / WER | 1.5% / 6% on 6 synthetic (Timbre-generated) clips |

Honest limits: the dataset was written by the same person as the rules engine, and the evaluation audio is synthetic.
These numbers overstate real-world accuracy. The tests are 59 backend tests (keyless, with real Playwright), 7 frontend
tests, and Playwright UI tests.

## Security and privacy

No raw audio is stored. Transcripts are kept only if the user opts in. OTPs never reach logs, models or speech. Digits
are redacted before any reasoning call. Keys stay server-side in `.env`, which is git-ignored. The full git history was
scanned for secrets with `scripts/secret_scan.py`, and none were found. See [SECURITY.md](SECURITY.md) and
[docs/security.md](docs/security.md).

## Demo video pipeline (reproducible)

All demo voices are AI-generated with Gnani Timbre from [demo_assets/sentences.json](demo_assets/sentences.json).
After editing the sentences, rebuild everything with one command (the server must be running):

```bash
bash scripts/build_video.sh        # or: make video
```

The pipeline auditions voices and checks them with live Prisma, then records a live take with Playwright (the clip is
fed to the page's microphone, so the product's own recording and upload code runs unchanged). It then edits from
[demo-output/edit/edl.json](demo-output/edit/edl.json) with ffmpeg and HTML overlays, and runs QC
(`scripts/qc_video.py`).

## Demo replay (no live API calls)

[docs/replay/index.html](docs/replay/index.html) is a static page with the recorded video, the agent's screenshots and
the sanitized audit timeline of the demo take. To publish it free on GitHub Pages: Settings → Pages → "Deploy from a
branch" → `main` / `docs`, then open `https://<you>.github.io/<repo>/replay/`. There is deliberately **no public live
deployment** using the real Gnani key.

## Limitations

* Prisma and Timbre run over REST, not streaming, so long replies take seconds before audio starts.
* Language understanding defaults to a rules engine (no AI model). Claude support is implemented but not verified.
* Two demo workflows on local portals only; real portals would need an adapter and a security review.
* Tamil and English are verified by the smoke test only. The evaluation audio is synthetic. All non-English phrases
  await native-speaker review.
* Single-user local app with no API authentication.

## Roadmap

Timbre SSE and Prisma streaming for faster first audio · human-recorded evaluation set with native-speaker review ·
verify Claude reasoning and compare it with the rules engine · more languages · more services through the adapter registry.

## License and acknowledgements

MIT, see [LICENSE](LICENSE). Thanks to **Gnani.ai** for Prisma and Timbre and for the programme credits. Fonts: Noto
Sans family (SIL Open Font License). PM-KISAN facts are quoted from pmkisan.gov.in (retrieved 8 Nov 2026).
