# LinkedIn drafts (you post these yourself)

Video to attach: `demo-output/final/gramsetu_master_16x9.mp4` (91.5 s, captions burned in, so it works muted).
Also upload `gramsetu_master_16x9.captions_en.srt` as the caption file if LinkedIn offers it.
Alternative for a phone-first feed: `gramsetu_square_1x1.mp4`.

Checklist before posting:
* Replace `[TAG: official Gnani AI LinkedIn page: verify exact page name before posting]` by typing "@" and choosing
  Gnani's official company page from the list. Do not guess the name.
* Put the GitHub link in the **first comment** (draft below), not in the post. LinkedIn tends to show posts with
  outside links to fewer people. The tradeoff: some readers won't open the comments, so the post says "link in the
  first comment".

---

## Variant 1 (main post)

I built a voice agent that fills an English-only government form from a request spoken in Kannada.

Many people know exactly what they need. The English-first online form is what stops them.

GramSetu listens with Gnani Prisma (speech-to-text) and shows the words in Kannada script. It asks only what is
missing, out loud, with Gnani Timbre ("Bengaluru Urban or Rural?"). Then a browser agent fills the form while you watch
every step.

You stay in control. Nothing is typed until you approve. Your one-time code never goes to the AI. The final submit
needs a second "yes". It only says "done" after it finds the portal's stored record.

What's real vs demo: the transcription, voices, browser actions and validation-error recovery in the video are a real
run. The portal is a local demo site with synthetic data. All voices are AI-generated with Gnani Timbre, including the
user.

Which language or service should I add next?

[TAG: official Gnani AI LinkedIn page: verify exact page name before posting]
#GnaniAI #GreatIndianAIInternshipChallenge #VoiceAI #IndianLanguages

### First comment (post it yourself right after publishing)

Code and setup: [FILL: GitHub repo URL]
How Gnani Prisma and Timbre are used: [FILL: repo URL]/blob/main/docs/how-gnani-models-are-used.md
Honest limits: REST, not streaming, so long replies take a few seconds. Language understanding in this build is a rules
engine (no AI model). The evaluation audio is synthetic. Feedback very welcome.

---

## Variant 2 (shorter, Kannada opening line)

ಕನ್ನಡದಲ್ಲಿ ಹೇಳಿ, ಫಾರ್ಮ್ ತಾನೇ ತುಂಬುತ್ತದೆ. [pending native review]
(Say it in Kannada. The form fills itself.)

GramSetu: Gnani Prisma hears the request, Gnani Timbre asks only what's missing, and a browser agent fills a demo
government form with approval gates. OTPs never go to the AI.

Real run on a local demo portal with synthetic data. All voices AI-generated with Gnani Timbre.

Which language should I add next?

[TAG: official Gnani AI LinkedIn page: verify exact page name before posting]
#GnaniAI #GreatIndianAIInternshipChallenge #Accessibility

Video for this variant: `demo-output/final/gramsetu_teaser_45s.mp4` (or `gramsetu_vertical_9x16.mp4` for mobile).

(Hindi opening line, if you prefer: "हिंदी में बोलिए, फ़ॉर्म खुद भर जाएगा।" [pending native review] "Speak in
Hindi, the form fills itself." The video shows Kannada, so the Kannada line matches better.)
