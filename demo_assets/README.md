# demo_assets

Inputs for the demo video. **All voices are AI-generated with Gnani Timbre** (no human recordings are used).

| File | What it is |
|---|---|
| `sentences.json` | The user's spoken lines (native script, English meaning, task) and the narration lines, plus the candidate Timbre voices to audition. **Edit this, then run `bash scripts/build_video.sh` (or `make video`).** |
| `NATIVE_REVIEW.md` | Review sheet for a native speaker. Every line is `[pending native review]`. |
| `voices.json` | Result of the last voice audition: per voice, duration, loudness (LUFS), the live Prisma transcript, CER vs. the sentence, and the chosen voice. Written by `scripts/demo/clips.py --audition`. |
| `generated/<id>.wav` | The chosen Timbre clip for each line, with 0.4 s of silence before and after (16 kHz mono). These are fed into the app as the microphone. |
| `generated/auditions/` | Every audition clip (each candidate voice). |

How the voice reaches the app: `scripts/record_demo.py` replaces the page's `getUserMedia` with a Web Audio stream that
plays the clip. The product's own recorder, WAV encoder and Prisma upload run unchanged, so the transcript on screen
is a real, unedited Gnani Prisma result.

If you later want to use your own voice instead (optional): put `kn_request.wav` etc. in `demo_assets/audio/`
(mono WAV, 16 kHz, 16-bit, under 30 s, a quiet room). The current pipeline uses Timbre clips; wiring human clips back in
is a one-line change in `scripts/demo/clips.py` (`resolve_clips`). The video labels would then need to change from
"AI-generated" to "recorded by …".
