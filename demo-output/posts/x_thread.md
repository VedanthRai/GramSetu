# X thread draft (you post this yourself)

Limits checked on help.x.com (8 Nov 2026): 280 characters per post and videos up to 140 s / 512 MB without Premium.
Every post below was length-checked with `scripts/demo/check_posts.py`. Links are counted as 23 characters (X's
t.co shortening). The help page does not state that number, so the drafts leave a margin.

Video for post 1: `demo-output/final/gramsetu_master_16x9.mp4` (91.5 s, under 140 s) or the shorter
`gramsetu_hook_20s_16x9.mp4` as a reply clip. Replace the tag placeholder with Gnani's official handle (verify it on
their website); do not guess.

---

**1/6**
Speak Kannada. Watch the government form fill itself.

I built GramSetu: Gnani Prisma hears you, Gnani Timbre asks what's missing, a browser agent fills the form with you.

Real run, demo portal, AI voices. [TAG: official Gnani X handle: verify]
#GnaniAI #GreatIndianAIInternshipChallenge

**2/6**
The problem: many people know exactly what they need, but online forms are English-first and dense, field after field.

GramSetu lets them say it in Kannada, Hindi, Tamil or English, and shows the words back in their own script before anything happens.

**3/6**
How it works:
1. Gnani Prisma transcribes the voice (Kannada script)
2. It fills what it understood and asks only what's unclear ("Bengaluru Urban or Rural?") with Gnani Timbre
3. You approve, then Playwright fills the portal while you watch

**4/6**
Safety by design:
• nothing is typed before you approve
• the one-time code goes from your hand to the portal, never to the AI
• final submit needs a second "yes"
• "done" only when the portal's stored record is found
• page text is treated as data, not instructions

**5/6**
Measured, not claimed: Prisma took 3.76 s on a 15 s Kannada request and 0.30 s on a short reply. Eval: intent 33/33, fields 39/39, 12/12 unsafe actions blocked.

Limits: synthetic eval audio, rules engine (no AI model), demo portal only.

**6/6**
Code, setup and the honest limits: [FILL: GitHub repo URL]

All voices in the video are AI-generated with Gnani Timbre. I'd love feedback: which language or service should I add next?
