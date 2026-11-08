# Internship pitch (one page)

**[FILL: your name]**, [FILL: college, year, branch] · [FILL: email] · [FILL: GitHub / LinkedIn]

**About me:** [FILL: my background, 2-3 lines in your own words: what you study, what you have built before, why voice
AI for Indian languages matters to you]

## What I built: GramSetu

A voice-first agent that helps people complete English-first government and healthcare web forms in Kannada, Hindi,
Tamil or English, using **Gnani Prisma** and **Gnani Timbre**, with approval gates, an OTP-safe flow and verification
against the stored record.

## Skills the project demonstrates

* **Speech integration:** direct REST integration of Prisma and Timbre, with in-browser WAV encoding, a fix for
  Timbre's streaming WAV headers, a single-in-flight lock, retry limits, a TTS cache and a usage guard. All four
  languages were verified with live smoke tests that drive the UI's capability table.
* **Agent safety engineering:** an action allow-list, same-origin policy, page text treated as data (a
  prompt-injection probe is ignored), two human approval gates, an OTP path that never touches a model, and
  verification before declaring success.
* **Backend design:** FastAPI, strict Pydantic contracts, an explicit 15-state machine, SQLite transactions with
  idempotency (no double booking under concurrency), and WebSocket live updates.
* **Frontend:** React and TypeScript with Web Audio capture, a live transcript editor, Browser Mission Control and a
  Latency HUD.
* **Evaluation and honesty:** a 33-utterance evaluation with denominators, CER/WER, 59 backend tests and Playwright UI
  tests; limitations stated up front.
* **Reproducible demo engineering:** an automated recorder that feeds Timbre-generated speech through the real
  microphone path, an edit-decision-list video pipeline (ffmpeg plus HTML overlays) and automated QC (loudness, sync,
  integrity, secret scan).

## What I would like to work on at Gnani

[FILL: 2-3 lines, e.g. streaming voice agents, Indic evaluation datasets, latency work, in your own words]
