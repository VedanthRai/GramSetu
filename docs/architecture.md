# Architecture

```
Browser (React + TS)                         FastAPI backend (Python 3.11+)                         Gnani / AI
┌──────────────────────────┐   REST + WS   ┌─────────────────────────────────────────────┐
│ VoicePanel               │──────────────▶│ api/routes.py  (thin, typed, validated)      │
│  mic → AudioWorklet →    │  /speech/*    │ speech/gnani.py ─ Prisma STT ───────────────────▶ api.vachana.ai/stt/v3
│  16 kHz WAV (wav.ts)     │               │                 ─ Timbre TTS + cache ───────────▶ api.vachana.ai/api/v1/tts/inference
│ TaskPanel (review/approve)│  /sessions/* │ orchestrator.py                              │
│ MissionControl (shots,   │◀──── WS ──────│  guards → reasoning → validate → state machine│──▶ Claude (optional) / rules
│  timeline, OTP box)      │  events       │ portals/ (adapter registry)                  │
│ LatencyHud, ProviderStrip│               │ browser/executor.py (Playwright, 1 ctx/task) │
└──────────────────────────┘               │  policy.py → act → observe → verify          │
                                           │ demo_portals/ scheme + clinic (same origin)  │
                                           │ SQLite: sessions, tasks, events, audit, ...  │
                                           └─────────────────────────────────────────────┘
```

## A turn, end to end

1. **Capture** – after an explicit click and a consent explainer, an `AudioWorklet` taps the mic; on stop the browser
   resamples to 16 kHz mono and encodes 16-bit WAV (`frontend/src/audio/wav.ts`, unit-tested). Max 30 s with a countdown.
2. **Prisma** – `POST /api/speech/transcribe` validates the WAV (empty / too short / too long / silence), checks the
   usage ceiling, calls Prisma, and returns the transcript. The UI shows it, editable, before anything is sent.
3. **Guards** (`security/guards.py`) – OTP/PIN/bank-detail/scam-caller text is withheld and answered with a warning;
   emergencies stop the booking and say "call 112". These run before any model.
4. **Reasoning** – the provider returns only `ReasoningOutput` JSON (intent + fields). Choice chips bypass interpretation
   entirely (structured input).
5. **Validation** (`orchestrator._merge`) – every value is checked against the portal adapter: select values must be
   real options, dates within the bookable window, slot times must exist and be free in SQLite, districts must belong
   to the state, ambiguous places ("Bengaluru") become a question. Invalid model output is dropped, never guessed.
6. **Dialogue** – the next missing field becomes a templated question in the user's language (`services/i18n.py`).
   The **same string** is displayed and spoken by Timbre, so meaning never drifts. When nothing is missing, a review
   summary is shown (with "You said / You corrected / Derived" provenance badges).
7. **Approval** – review confirmation → explicit "Approve and start" (button or voice "yes" at the consent step).
8. **Browser agent** – the adapter (not the model) builds a typed plan of `BrowserAction`s. For each action:
   policy check (enum, origin + route, target defined by adapter, secret fields user-only, consequential steps need
   approval) → semantic locator must match exactly one element → execute → screenshot (sensitive fields masked) →
   verify expected state → sanitised audit row → WebSocket event. One bounded, evidence-based recovery per error key.
9. **Pauses** – OTP: `AWAITING_USER_ACTION`; the user types the code into a secure box relayed straight to the portal
   field (or types it in the headed browser). Final submit / booking / cancel: `PAUSED_FOR_CONFIRMATION` with portal,
   action, data and consequence shown.
10. **Verification** – completion only when the portal's own SQLite record exists for this task's idempotency key and
    matches what was approved (`browser/verifier.py`). Then a success message, a printable demo summary card and a
    downloadable Timbre audio version.

## Key modules

| Path | Role |
|---|---|
| `backend/app/schemas/contracts.py` | `TaskIntent`, `ExtractedField`, `BrowserAction` (12-action enum), `TaskEvidence`, `ReasoningOutput` — strict Pydantic 2 |
| `backend/app/services/state_machine.py` | 15 states, explicit transition table, cancel from any non-terminal state |
| `backend/app/services/orchestrator.py` | dialogue, validation, approvals, execution hand-off, outcomes |
| `backend/app/portals/` | adapter registry: `demo_scheme`, `demo_clinic` (+ cancel), disabled read-only `live_assistance` |
| `backend/app/services/browser/` | `policy.py`, `executor.py` (Playwright), `verifier.py` |
| `backend/app/demo_portals/` | locally hosted multi-page HTML portals with real validation, demo OTP, review pages, hidden injection probe |
| `backend/app/services/speech/` | Gnani providers, WAV handling, verified capability table, mock providers (tests only) |
| `backend/app/services/reasoning/` | Anthropic / OpenAI-compatible / rules providers, versioned prompt |
| `backend/app/services/usage/guard.py` | local request counter + daily ceiling |
| `frontend/src/` | pages, components, typed API client, audio capture/playback |

## Extending to more services

Add an adapter in `backend/app/portals/` declaring fields, semantic locators, consequential and secret targets,
completion evidence and recovery rules, plus ask-templates in `i18n.py`. The executor, policy, verifier interface,
approvals and UI work unchanged. Real third-party portals are deliberately not automated; `live_assistance` shows where
a read-only mode would plug in after a per-portal security review.
