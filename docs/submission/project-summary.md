# GramSetu: project summary

## 100 words

GramSetu is a voice-first assistant that helps people complete English-first government and healthcare web forms in
Kannada, Hindi, Tamil or English. Gnani Prisma transcribes the spoken request in the user's own script. GramSetu then
asks only for what is missing, out loud, with Gnani Timbre. After the user approves, a browser agent fills the form
while the user watches every step. One-time codes never reach the AI, the final submit needs a second approval, and
"done" is declared only when the portal's stored record is found. The demo runs on local practice portals with
synthetic data.

## 300 words

Many people can say exactly what they need, but get stuck on online forms that are English-first, dense and
unforgiving. GramSetu lets them speak instead.

A user presses the microphone and speaks, for example in Kannada: "I'm a farmer, my name is Ramesh Kumar, from the
Bengaluru side, village Harohalli, two acres in my own name, I have a bank account, please help me fill the PM-KISAN
demo form." **Gnani Prisma** transcribes it live and shows the words in Kannada script, so the user can check them
before anything happens. GramSetu extracts the fields and notices what is unclear: there are two Bengaluru districts.
It asks "Bengaluru Urban or Bengaluru Rural?" out loud with **Gnani Timbre** instead of guessing. The user answers by
voice, types the mobile number, and hears a summary read back.

Nothing is typed into the portal until the user approves. Then a Playwright browser agent fills the multi-step demo
form while **Browser Mission Control** shows its screenshots and an audit timeline. When the portal rejects "2" acres
and asks for "2.00", the agent recovers using the portal's own error message. It pauses for the one-time code, which
the user types into a secure box that is never logged, spoken or sent to a model. It asks again before the final
submit. The result is read aloud only after the portal's stored record is found.

A second workflow books clinic appointments from a real slots table without double booking. Guards catch OTP scams and
medical emergencies. The scheme guidance quotes the official PM-KISAN website and never declares eligibility.

Everything shown is measured: a Latency HUD per turn, a 33-utterance evaluation with denominators, 59 backend tests
and live smoke tests in four languages. The portals are local demo sites with synthetic data. All voices in the demo
video are AI-generated with Gnani Timbre.

## 600 words

**Problem.** Government and healthcare services are increasingly online, but the forms are mostly English-first and
assume the user can read dense labels, pick the right district from a list and type values in the exact format the
portal expects. Many people who can describe their need perfectly well in Kannada, Hindi or Tamil depend on an agent,
a relative or a cyber café, and that dependence costs money, time and privacy.

**Users.** Farmers applying for income-support schemes, patients booking a clinic visit, and the volunteers and
front-line workers who help them. The design assumes low literacy in English, a shared or low-end phone, and
legitimate fear of scams.

**Solution.** GramSetu is a voice-first agent with a human in charge. The user speaks; **Gnani Prisma** (`/stt/v3`,
Prisma v2.5) returns a transcript in the user's own script, which the user can correct before sending. A reasoning layer
turns the transcript into a typed task with fields, missing fields and clarification questions, validated by strict
Pydantic contracts and an explicit state machine. **Gnani Timbre** (`timbre-v2.5`) speaks every reply in the user's
language. This includes questions that resolve ambiguity instead of guessing, a read-back summary and the final receipt.

**Reasoning layer.** The configured provider in this build is a deterministic rules engine for four languages, labelled
"Rules fallback (no AI model)" in the app. A Claude provider (Anthropic SDK, structured JSON output) and an
OpenAI-compatible provider are implemented behind the same contract, but were not verified because no key was
available. Building the demo exposed real gaps in the rules engine: unpunctuated Kannada transcripts made a name absorb
the rest of the sentence, and a "no" in another clause flipped a bank-account answer. Both were fixed with regression tests.

**Browser agent and safety.** After explicit approval, a Playwright agent in an isolated context fills a multi-step
demo portal. Each action is checked against a 12-action allow-list and same-origin policy. Text on the page is treated
as data; a hidden prompt-injection probe in the demo portal is ignored and logged. Validation errors are recovered once,
using the portal's own error key. One-time codes go from a secure box straight into the portal field and are never
logged, stored, spoken or sent to a model. The final submit needs a second approval. Completion is declared only after
the portal's stored record is found. Guards catch OTP-sharing scams, medical emergencies (stop and call 112) and
requests for medical advice.

**How Gnani is used.** Prisma for every voice turn, with a 30-second limit and a single in-flight request. Timbre for
every assistant message, with a cache so repeated phrases cost nothing. All four languages were verified with live
smoke tests, which update a capability table that drives the UI. The demo video's user voice is also Timbre (voice
Kavin), auditioned against Saanvi and checked with live Prisma.

**Impact.** The same pattern of speak, review, watch, approve and verify applies to many services: a new portal is one
adapter file. Users keep control and get evidence instead of promises.

**Demo vs real.** Real: Prisma and Timbre calls, the browser actions, the validation error and recovery, the approval
gates, the persisted demo record, and the measured latencies. Demo: the portals are local practice sites with synthetic
data, and all voices in the video are AI-generated.

**Measured.** A 33-utterance evaluation (intent 33/33, fields 39/39, 12/12 unsafe actions rejected) on a dataset
written by the same developer. Prisma CER is 1.5% on 6 synthetic clips. The demo take's Prisma latency was 3.76 s on a
15.3 s Kannada request.

**Roadmap.** Streaming Prisma and Timbre for faster first audio, human-recorded evaluation audio with native-speaker
review, verified LLM reasoning compared with the rules engine, and more languages and services.
