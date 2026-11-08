# Posting plan

**Gnani verifies engagement. Bots, engagement pods, bought likes or any artificial engagement would hurt you and could
disqualify you.** Everything below is about reaching real people and talking with them honestly.

## Which file where

| Use | File |
|---|---|
| LinkedIn main post | `demo-output/final/gramsetu_master_16x9.mp4` (+ `captions_en.srt` if offered) |
| X post 1 | `gramsetu_master_16x9.mp4` (91.5 s, under the 140 s non-Premium limit) |
| First-hour reply clip / quote post | `gramsetu_hook_20s_16x9.mp4` |
| Phone-first feeds, WhatsApp status, Instagram | `gramsetu_vertical_9x16.mp4` |
| Later teaser post | `gramsetu_teaser_45s.mp4` |
| A/B testing the opening line on follow-up posts | `hook_variant_A/B/C.mp4` |
| GitHub README | `docs/media/readme_loop.gif` |
| Link previews | `social_card_1200x627.png`, thumbnails |

## When (IST)

* Best first try: **Tuesday to Thursday, 8:30 to 10:00** (before work or class) or **12:30 to 13:30** (lunch).
* Avoid late nights and Friday evenings. Post LinkedIn first; post the X thread 30 to 60 minutes later so you can
  answer both.
* Block the next 60 to 90 minutes in your calendar for replies.

## First hour

1. Post. Immediately add the first comment with the GitHub link (LinkedIn).
2. Reply to **every** comment within minutes, with a real answer or a follow-up question, not just "thanks".
3. If someone asks how something works, answer in two or three lines and point to the right doc in the repo.
4. If someone finds a problem, thank them, say what you will check, and later post what you found.
5. Do not ask anyone to like or comment on a schedule. Ask for honest feedback instead.

## Reaching people genuinely

* Your college groups (department, coding club, alumni). Share it as "I built this, honest feedback welcome".
* Developer communities you already take part in, following each community's self-promotion rules.
* The Gnani community or Discord, if there is a showcase channel. Check the rules first.
* People who helped you (testers, the native speaker who reviews the Kannada): thank them by name **with their permission**.
* Kannada, Hindi and Tamil speakers in your network: ask them to try a sentence and tell you what broke.

## Follow-up ladder (one post every few days)

1. **Behind the scenes: the browser agent.** How the approval gates work, why page text is treated as data, and the
   validation-error recovery ("2" → "2.00") from the portal's own error message. Use `hook_variant_B.mp4` or screenshots.
2. **30 to 45 second teaser** for people who missed it: `gramsetu_teaser_45s.mp4` or the vertical cut.
3. **"What I learned about Indic voice AI"**, using only measured numbers from the repo:
   * Prisma took 3.76 s on a 15 s Kannada request and 0.30 s on a short reply. Smoke tests ran 0.61 to 1.46 s per language.
   * Prisma CER was 1.5% on 6 synthetic clips, and the AI-voice auditions transcribed with CER 0 to 0.026.
   * The Kannada transcript came back without punctuation, which broke a name-extraction rule. What I changed and why.
   * Timbre's REST latency (about 1.6 to 2.7 s per sentence in smoke tests) is why streaming is next.
4. **A "what's next" post** that answers the most common "add this language/service" comments.

## After submitting: thank-you post draft

> Submitted GramSetu to the #GreatIndianAIInternshipChallenge 🙏
> Thank you to everyone who tried it, asked hard questions, or pointed out what broke, especially [FILL: names, with
> permission]. Your comments shaped the next steps: [FILL: 1-2 real changes].
> The code stays open: [FILL: repo URL]. Built with Gnani Prisma and Timbre. #GnaniAI
