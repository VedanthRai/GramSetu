# GramSetu demo: final report

## Rebuild everything with one command

Last rebuild: 8 Nov 2026, take2. Prisma on the three Kannada lines: 3,353 / 2,591 / 278 ms. All QC checks passed, and raw frames and render caches were deleted afterwards to save disk.

After a native speaker has reviewed `demo_assets/NATIVE_REVIEW.md` and you have edited `demo_assets/sentences.json`,
start the app (`scripts/dev.sh` or `scripts\dev.ps1`), then run:

```bash
bash scripts/build_video.sh        # or: make video
```

This re-auditions the Timbre voices, checks each line with live Prisma, records a new live take, re-edits every output
from `demo-output/edit/edl.json` into `demo-output/final/`, and runs QC (`demo-output/qc/qc_report.md`). It needs about
1 GB of free disk (the recorder refuses below 1.5 GB) and roughly 20 to 30 minutes, mostly rendering.

## What was recorded and how

* **Method:** headless Chromium driven by Playwright, captured with the Chrome DevTools screencast (JPEG frames at
  1920×1080 with timestamps; the page is zoomed 1.25× so the UI reads like a 1536 px screen). Playwright's own video
  was tested as well: VP9 at about 1.4 Mb/s and 25 fps, and acceptable, but it has no exact frame timestamps for audio
  sync, so the screencast was chosen. No display or Xvfb is needed. The recorder injects a visible cursor and click
  ripples; captions, step badges and labels are drawn in the edit with HTML/CSS (Noto Sans), not in the product UI.
* **Voice input:** an init script replaces `navigator.mediaDevices.getUserMedia` with a Web Audio stream that plays the
  Timbre clip. The product's own recorder, WAV encoder and Prisma upload run unchanged, so the on-screen transcript is a
  genuine Prisma result. This was verified: all three Kannada transcripts appear in the UI exactly as Prisma returned
  them and are logged in the take. Chromium's fake-capture flags were not needed.
* **Audio:** every Timbre reply the page played (captured in the page with a SHA-256 match) and every injected voice
  clip are logged with wall-clock start times, then mixed with ffmpeg (`atrim`, `adelay`, `amix`), with narration
  ducking, each clip pre-normalised, and a final two-pass EBU R128 normalisation to −16 LUFS, true peak ≤ −1.5 dBTP.
* **Final footage:** `takes/take2` (rebuilt with `bash scripts/build_video.sh`), a live run of the Kannada scheme flow (plus the "problem" portal scene). The clinic
  scene works (rehearsals) but was left out of the final cuts to keep the master under about 90 s.

## Voices (all AI-generated with Gnani Timbre `timbre-v2.5`; transcribed by Prisma `prisma-v2.5`)

| Role | Voice | Audition |
|---|---|---|
| User, Kannada (3 lines) | **Kavin** | vs Saanvi; both transcribed correctly (CER Kavin 0.026 / 0 / 0, Saanvi 0.013 / 0 / 0). Kavin chosen so the user sounds clearly different from GramSetu (Saanvi). |
| User, Hindi (clinic line) | **Deepak** | vs Vikrant, Bhavna: all CER 0 |
| GramSetu (assistant) | **Saanvi** (app default for Kannada) | from the capability table |
| Narration (English) | **Pranav** | vs Kaveri: both CER 0, equal length; Pranav is a third distinct voice |

Attempts per utterance: **1** for every line. The only Prisma difference was ಖಾತೆನೂ → ಖಾತೆಯೂ (a spoken variant), shown
as-is; transcripts are never edited. One honest failure found along the way: the real Prisma Kannada transcript has no
punctuation, which made GramSetu's rules engine read "ರಮೇಶ್ ಕುಮಾರ್ ಬೆಂಗಳೂರು ಕಡೆ …" as the name. That was a product bug,
fixed and covered by a test, and the utterance was not changed to hide it.

Details: `demo_assets/voices.json`.

## Takes and Gnani usage

| Take | Result | Gnani calls (app counter) |
|---|---|---|
| Voice audition (4 lines × 2-3 voices + narration) | all accepted first time | 23 (Timbre + Prisma) |
| REHEARSAL_take1 (fixture mode, then live re-run) | OK; found 3 recorder/product issues | 0, then 15 |
| REHEARSAL_take2 | OK; found the missing agent screenshots | 7 |
| REHEARSAL_take3 | scheme OK; clinic out of free slots (fixed) | 5 |
| take1 (first attempt) | aborted: disk full | 3 |
| take1 (previous final) | all checks pass | 4 (3 Prisma + 1 Timbre receipt) |
| **take2 (rebuild, final)** | **all checks pass** | **4** (3 Prisma + 1 Timbre receipt; other replies were cache hits) |

App counter for 2026-11-08 (local, **not official credits**): **81 calls** (40 Prisma, 41 Timbre, 1 error = a Timbre 502
in a rehearsal), plus 11 smoke-test calls outside the counter. The official balance is only visible at app.gnani.ai.

## QC results

See `demo-output/qc/qc_report.md` (generated) for every number. Summary at the time of writing:

| file | res | fps | dur s | MB | audio | LUFS | TP dBTP | faststart | issues |
|---|---|---|---|---|---|---|---|---|---|
| gramsetu_hook_20s_16x9.mp4 | 1920x1080 | 30.0 | 20.0 | 3.25 | aac 48000 2ch | -16.0 | -3.5 | True | none |
| gramsetu_master_16x9.mp4 | 1920x1080 | 30.0 | 91.53 | 12.71 | aac 48000 2ch | -16.0 | -2.7 | True | none |
| gramsetu_square_1x1.mp4 | 1080x1080 | 30.0 | 91.53 | 7.03 | aac 48000 2ch | -16.0 | -2.7 | True | none |
| gramsetu_teaser_45s.mp4 | 1920x1080 | 30.0 | 43.22 | 6.69 | aac 48000 2ch | -16.0 | -3.0 | True | none |
| gramsetu_vertical_9x16.mp4 | 1080x1920 | 30.0 | 37.92 | 3.5 | aac 48000 2ch | -16.0 | -3.1 | True | none |
| hook_variant_A.mp4 | 1920x1080 | 30.0 | 67.13 | 9.6 | aac 48000 2ch | -16.0 | -2.8 | True | none |
| hook_variant_B.mp4 | 1920x1080 | 30.0 | 67.13 | 9.6 | aac 48000 2ch | -16.0 | -2.8 | True | none |
| hook_variant_C.mp4 | 1920x1080 | 30.0 | 67.13 | 9.6 | aac 48000 2ch | -16.0 | -2.8 | True | none |

All 8 videos: H.264 yuv420p, 30 fps, AAC 48 kHz stereo, +faststart, metadata stripped; QC issues: none.

* **Integrity (asserted from take1's audit log and the DB):** validation error in the audit log ✅, recovery
  ("entered 2.00") ✅, prompt-injection probe ignored ✅, final state COMPLETED ✅, receipt **GS-SC-57A608** found in
  `demo_applications` ✅, no page errors ✅.
* **Speed-ups labelled:** master "15× speed" (typing + summary read-back + voice confirmation) and "2× speed" (OTP
  typing); hook "7.7× speed" (rest of the spoken request) and "2.5× speed" (screenshot history); teaser and vertical
  "2.5× speed". The labels are drawn on every frame of those pieces.
* **Labels:** voice label whenever the user voice plays; "Demo portal · synthetic data" on every footage frame; "rules
  engine (no AI model)" while understanding is shown.
* **Sync:** no overlapping Timbre clips (no doubled audio). Clips that were already playing before a cut are dropped
  rather than started mid-sentence. Long replies faded at a segment end are listed in the QC report.
* **Visual review:** contact sheets every 1.5 s (`qc/sheet_*.jpg`) and 390 px phone sheets (`qc/phone390_*.jpg`) were
  viewed. No tofu boxes in Kannada, Devanagari or Latin; no permission prompts, dev tools, error toasts or stuck
  spinners. The demo OTP is visible on the *simulated phone* (synthetic, by design). On a 390 px phone the 16:9 UI text
  is too small to read and only the captions, callouts and labels are legible, which is why the vertical cut exists.
* **Secrets:** `scripts/secret_scan.py` scanned the working tree, all 5 commits of history (full patches) and the
  outputs (captions, EDL, logs, posts) for the configured key and key patterns: **none found**. `.env` is git-ignored
  and was never committed. Container metadata is stripped (`-map_metadata -1`). gitleaks could not be installed
  (download returned 504), so the scan is the documented grep.

## Outputs

Durations, sizes and loudness: see the QC table above. Also in `final/`: `.captions_en.srt` and `.captions_kn.srt` per video, `readme_loop.gif`, `thumbnail_1920x1080.png`, `thumbnail_1080x1350.png`, `social_card_1200x627.png`.

Fixed in the last pass: the vertical cut's labels no longer overlap the step badges, and a rounding bug that showed the
2.5× speed-up as "2×" (understating it) was found in a frame check and fixed. Speed labels now show one decimal unless
the speed is a whole number.

Recommended use:
* **LinkedIn main post:** `gramsetu_master_16x9.mp4` (+ `.captions_en.srt`); square alternative `gramsetu_square_1x1.mp4`.
* **X main post:** `gramsetu_master_16x9.mp4` (under the 140 s non-Premium limit).
* **First-hour reply clip:** `gramsetu_hook_20s_16x9.mp4`.
* **Mobile-first / stories:** `gramsetu_vertical_9x16.mp4`.
* **GitHub README:** `docs/media/readme_loop.gif`; replay page `docs/replay/`.

Platform limits (checked 8 Nov 2026 on official help pages):
* **LinkedIn** (linkedin.com/help/linkedin/answer/a548372): 3 s to 15 min; 75 KB to 5 GB; 256×144 to 4096×2304;
  aspect 1:2.4 to 2.4:1; 10 to 60 fps; MP4 supported. A newer help page (a564109) says "The file size cannot exceed
  100 MB". All outputs are under 15 MB, so both are satisfied. The LinkedIn post character limit is not stated on those pages.
* **X** (help.x.com/en/using-x/x-videos, how-to-post): without Premium, videos up to **140 s** and **512 MB**; posts up
  to **280 characters**. The thread drafts were length-checked with weighted counting.

## Weak spots and how to improve them

* **The spoken request is long (15 s of a mostly static listening screen).** Captions carry it, but a shorter request
  would be punchier. Changing it means re-running `make video`. A human voice would also be more convincing; the
  pipeline can take one, but the labels must change.
* **The Prisma wait after the request (3.8 s) is shown in real time.** It's honest, but slow; streaming STT is the real fix.
* **The validation error happens in under a second in real time,** so it is shown through the agent's own screenshots
  (enlarged) replayed from Mission Control, with a callout. Real time would be invisible.
* **Assistant replies in the final take came from the Timbre cache.** They were generated live in the rehearsals; the
  receipt was live. The Latency HUD shows "(cached phrase)", which is honest but undersells live latency.
* **The master is 91.5 s,** slightly over the 75 to 90 s target (well under the 120 s cap and X's 140 s).
* **Captions for GramSetu's long replies are chunked by time,** so a chunk can lead or trail the speech by a second.
* **Language understanding is the rules engine.** The brief asked for a reasoning-provider translation for the
  subtitles; instead the English captions come from GramSetu's own en-IN templates for the same message, and the user
  lines come from `sentences.json`. Both are pending native review.

## Things only you can do

1. Have a native speaker review `demo_assets/NATIVE_REVIEW.md`, then run `bash scripts/build_video.sh`.
2. Watch the final cut twice, once with sound and once muted.
3. Look up Gnani's official LinkedIn page and X handle and replace the `[TAG: …]` placeholders.
4. Post (`demo-output/posts/`), nominate the posts, and reply to every comment genuinely.
5. Fill and submit the form when it opens (`docs/submission/form-answers-draft.md`, `[FILL: …]` fields).
6. Fill `[FILL: your name]` in `LICENSE` and the contact in `SECURITY.md`; rotate the Gnani key after the
   challenge (it was pasted into a chat during the build).
7. Free some disk space: drive C: had under 2 GB free during this run.

## Pre-posting checklist

- [ ] Native review done and video rebuilt (or posted with "pending review" phrases accepted knowingly)
- [ ] Watched with sound and muted; captions readable on your phone
- [ ] Tag placeholders replaced with verified handles
- [ ] Repo public, `python scripts/secret_scan.py` passes, README GIF shows, replay page live
- [ ] First comment with the repo link ready (LinkedIn)
- [ ] 60 to 90 minutes free after posting to reply
