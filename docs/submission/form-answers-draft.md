# Form answers (draft, paste and edit)

**Project name:** GramSetu

**One-liner:** Speak your language and GramSetu fills the online form with you: Gnani Prisma hears you, Gnani Timbre
asks what's missing, and a browser agent fills the form only after you approve.

**Problem:** Government and healthcare services are online, but the forms are English-first, dense and unforgiving
about formats. People who can describe their need perfectly in Kannada, Hindi or Tamil end up depending on agents or
cyber cafés, which costs money, time and privacy, and exposes them to OTP scams.

**Target users:** Farmers applying for income-support schemes, patients booking clinic visits, and the volunteers and
front-line workers who help them; people with limited English literacy on shared or low-end phones.

**Solution / what it does:** A voice-first agent. Speak, check the transcript in your own script, answer only the
questions that are unclear, approve, then watch a browser agent fill the form step by step. One-time codes stay with
the user. The final submit needs a second approval. "Done" is said only after the portal's stored record is found.

**Technology:** FastAPI + Pydantic (strict contracts, explicit state machine), SQLite, async Playwright (isolated
browser context, action allow-list, same-origin policy), React + TypeScript + Vite + Tailwind, Web Audio microphone
capture with in-browser WAV encoding. Reasoning: rules engine (configured in this build); Claude and OpenAI-compatible
providers implemented behind the same contract.

**Gnani models used:** Gnani Prisma `prisma-v2.5` (`/stt/v3`) for every voice turn; Gnani Timbre `timbre-v2.5`
(`/api/v1/tts/inference`) for every spoken reply and for the demo video's voices. Verified with our key in Kannada,
Hindi, Tamil and English.

**Impact:** Lets people complete online services by voice, in their language, without giving up control or their OTP.
The pattern (speak, review, watch, approve, verify) extends to any service through one adapter file.

**What is real vs demo:** Real: live Prisma and Timbre, real browser actions, the validation-error recovery, approval
gates, the persisted demo record and the measured latency. Demo: local practice portals with synthetic data. All voices
in the video are AI-generated with Gnani Timbre.

**Measured results:** Intent 33/33 and fields 39/39 on a 33-utterance evaluation (self-written dataset). 12/12 unsafe
browser actions rejected. 2/2 end-to-end workflows verified. Prisma CER 1.5% on 6 synthetic clips. Prisma took 3.76 s
on a 15.3 s Kannada request.

**Challenges:** Unpunctuated speech transcripts broke rule-based extraction (a name swallowed the rest of the sentence;
a "no" in another clause flipped an answer), so I fixed both with regression tests. Timbre returns streaming-style WAV
headers that needed rewriting. Windows path-length limits broke caches. Keeping the demo honest meant feeding
AI-generated audio through the real microphone code path instead of faking transcripts.

**Next steps:** Streaming Prisma and Timbre, human-recorded evaluation audio with native-speaker review, verified LLM
reasoning, more languages and services.

**Team:** [FILL: your name], [FILL: college / year / branch]

**Contact:** [FILL: email] · [FILL: phone, only if the form requires it]

**Links:** Repo [FILL: GitHub URL] · LinkedIn post [FILL: URL] · X post [FILL: URL] · Video [FILL: URL] · Demo replay [FILL: GitHub Pages URL]
