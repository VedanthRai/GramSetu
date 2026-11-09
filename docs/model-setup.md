# Model setup and verified capabilities

Everything the UI exposes (languages, voices, modes) comes from
`backend/app/services/speech/verified_capabilities.json`, which `scripts/gnani_smoke_test.py` updates
only after a real Timbre synthesis **and** a non-empty Prisma transcript succeed for that language.

## Gnani — how it is called and why

Source of truth: https://docs.gnani.ai/api (read 2026-11-08). Integration is **direct HTTP from the backend** (`httpx`),
not the `gnani-vachana` SDK, because the SDK still defaults TTS to the deprecated `timbre-v2.0` (the docs warn about this)
and two plain endpoints are easier to meter, cache and audit. The key never reaches the browser.

| | Prisma (speech-to-text) | Timbre (text-to-speech) |
|---|---|---|
| Endpoint | `POST https://api.vachana.ai/stt/v3` (multipart: `audio_file`, `language_code`) | `POST https://api.vachana.ai/api/v1/tts/inference` (JSON) |
| Auth | header `X-API-Key-ID` | header `X-API-Key-ID` |
| Model used | Prisma v2.5 (default; response reports `prisma-v2.5`) | `timbre-v2.5` |
| Audio | We send 16 kHz mono 16-bit PCM WAV encoded in the browser (docs accept WAV/MP3/OGG/FLAC/AAC/M4A) | We request WAV, 16 kHz, mono, 16-bit |
| Limit | 30 s per REST request (docs); enforced in UI countdown and server | not documented |
| Mode in GramSetu | REST — **not streaming** | REST — **not streaming** |

Observed quirk: Timbre's WAV header declares a placeholder data length (a streaming-style header); GramSetu rewrites it
(`speech/wav.py: normalise_wav`). Docs also state only **one active request at a time** (429 otherwise), so all Gnani
calls are serialised with a lock and retried at most once.

### Verified capability table (this key, 2026-11-08)

| Language | Prisma STT | Timbre TTS | Voices verified | Evidence |
|---|---|---|---|---|
| Hindi `hi-IN` | verified | verified | Nalini | smoke test + 4 eval items + live UI voice test |
| Kannada `kn-IN` | verified | verified | Saanvi | smoke test + 3 eval items |
| Tamil `ta-IN` | verified | verified | Asmita | smoke test: exact transcript, Timbre 1.92 s / Prisma 0.89 s |
| English `en-IN` | verified | verified | Kaveri | smoke test: exact transcript, Timbre 1.60 s / Prisma 0.61 s |
| Hinglish code-mixed | not verified as a mode | — | — | docs list no `en-hi-IN-latn`; `format=codemix` exists on Prisma v3.0 only (untested). Latin-script Hinglish *audio* sent to `hi-IN` came back correctly in Devanagari. |

Re-verify any language with `python scripts/gnani_smoke_test.py --langs ta-IN en-IN` (2 calls per language);
add `--voices 2` to also verify a second voice (1 extra Timbre call each).

### Measured latency (real calls, not estimates)

| Call | Result |
|---|---|
| Smoke test, Hindi: Timbre / Prisma | 0.59 s / 0.29 s |
| Smoke test, Kannada: Timbre / Prisma | 2.71 s / 1.46 s |
| Prisma through the app endpoint (2.9 s clip) | 470 ms |
| Prisma, eval run (7 calls) | mean 2,092 ms (range ~270–5,300 ms) |
| Timbre greeting through the app (78 chars) | 2,634 ms, then 0 ms on cache hit |
| Live UI turn (fake mic → browser WAV → Prisma → reply audio) | 2.79 s machine time |

Latency varies a lot between calls. Time-to-first-audio for long messages is the main cost because REST returns the whole
file; Timbre SSE (`/api/v1/tts/sse`) is documented and is the next step (see Known limitations).

### Credits and usage

Gnani's documented API returns **no credit or balance information** (no endpoint, no headers — checked on every call).
GramSetu therefore keeps a **local request count** (`/status` page, labelled "not official Gnani credits"):

* Live calls during this build: **33** — 9 by the smoke test (outside the app counter: Hindi, Kannada, then Tamil +
  English), and 24 counted by the app (11 Prisma, 13 Timbre). 5 of those Timbre calls were wasted by a Windows path-length bug that was then fixed.
* Check the official balance at https://app.gnani.ai.
* Guards: TTS cache keyed by (text, language, voice, model, rate); `DAILY_GNANI_REQUEST_LIMIT`; at most 1 retry;
  `GNANI_FIXTURE_MODE=true` serves only previously recorded real responses and the UI shows "Fixture mode".
* Automated tests run with an empty key and never call Gnani.

## Reasoning provider

`REASONING_PROVIDER` selects one of:

1. **`rules`** (default): deterministic keyword + slot-filling engine for hi/kn/ta/en, always labelled
   **"Rules fallback (no AI model)"**. This is what the current build runs and what the evaluation numbers measure.
2. **`openai_compatible`**: any OpenAI-compatible `/chat/completions` endpoint (`REASONING_BASE_URL`, `REASONING_API_KEY`,
   `REASONING_MODEL`), JSON mode. Output is validated with Pydantic; on failure it retries once with the validation error,
   then the user is asked to rephrase. Not verified yet.

Prompt: `backend/app/services/reasoning/prompts/interpret_v1.md` (version-controlled). User text is wrapped in
`<user_text>` and declared to be data. Before any model call, digit runs (phones, IDs, codes) are redacted, OTP/scam text
is intercepted by a deterministic guard, and only field *names* (not values) of what is already known are sent.

