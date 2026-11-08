> **Superseded:** the current submission package is in [docs/submission/](submission/) and the post drafts are in `demo-output/posts/`. This file is kept for history.

# Submission kit

## 150-word project description

GramSetu is a voice-first assistant that helps people use government and healthcare web services in their own language.
A farmer can say, in Hindi, "I have two acres — help me with the scheme form", and GramSetu transcribes it with
Gnani Prisma, asks only for the missing details in a natural Gnani Timbre voice, shows a review in the user's language,
and — after explicit approval — drives a real browser through a multi-step demo portal while the user watches live
screenshots. One-time codes and the final submit always stay with the user. Completion is declared only after the
portal's own stored record is found. Scheme guidance quotes the official PM-KISAN website with a retrieval date and never
declares anyone eligible. A Kannada clinic-booking flow books real slots from a database without double booking.
Safety guards catch OTP scams and medical emergencies in four languages. Everything shown — latency, evaluation,
timelines — comes from real measured runs.

## What is real and what is demo (honesty note)

Real: Gnani Prisma speech recognition and Gnani Timbre speech synthesis (live API calls, Hindi and Kannada verified with
our key); the Playwright browser actually fills the forms; validation errors, OTP pauses, approvals, verification,
latency numbers and evaluation results are all genuine. Demo: the two portals are locally hosted practice sites marked
"not an official government website"; their records, doctors and slots are synthetic; nothing is sent to real government
or hospital systems. In this build the language understanding runs on a clearly labelled rules engine (no AI model) unless
an Anthropic key is configured. Hindi, Kannada, Tamil and English are verified with our key; native-speaker review of the phrases is still pending.

## LinkedIn / X post draft

> Built **GramSetu** for the @Gnani.ai hackathon 🇮🇳 — speak in Hindi, Kannada, Tamil or English, and it fills government and clinic
> forms *with* you. Gnani **Prisma** hears you, Gnani **Timbre** answers in your language, and a real browser does the
> clicking while you watch. OTPs and the final "submit" never leave your hands, and it only says "done" after it finds
> the stored record. Measured, not claimed: Prisma CER 1.5% on our (synthetic) eval set, ~2.8 s from send to spoken reply
> on a cached turn. #VoiceAI #IndianLanguages #GovTech #Accessibility #Gnani

(Replace the handle with Gnani's exact LinkedIn/X handle before posting.)

## Judge Q&A

**What are the limits?** Two demo workflows on local portals; four languages verified (Tamil/English by smoke test only); REST, not streaming, so long replies take a few seconds before audio starts; the default language understanding is
a rules engine unless a Claude key is set; evaluation audio is synthetic (Timbre-generated), not human speech.

**Why not automate real portals?** Real portals have CAPTCHAs, terms of use and real consequences. GramSetu's adapter
registry shows how a portal would be added after a security review; the `live_assistance` adapter exists, disabled and
read-only.

**Privacy?** No raw audio kept; transcripts not stored unless the user opts in; OTPs never reach logs, models or
speech; minimum data to the reasoning model (digits redacted); delete-session wipes events and screenshots.

**How does it extend?** A new service = one adapter file (fields, semantic locators, consequential steps, completion
evidence) + question templates. Policy, approvals, verification, Mission Control and voice all apply unchanged.

**How do you know it works?** 56 backend tests (incl. full Playwright workflows, prompt injection, origin blocking,
idempotency under concurrency), 7 frontend tests, a Playwright UI test, a live voice-loop test, and an evaluation
harness whose results page shows every denominator.

## Commands

```bash
python scripts/gnani_smoke_test.py               # verify key + Hindi (2 calls); --langs kn-IN ta-IN en-IN to expand
scripts\dev.ps1                                  # Windows: build UI + start http://127.0.0.1:8000
python scripts/run_eval.py --stt --sample 7 --e2e http://127.0.0.1:8000
```
