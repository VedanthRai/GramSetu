# Edit notes

## Takes and selection

| Take | Kind | Scenes | Result | Used? |
|---|---|---|---|---|
| REHEARSAL_take1 (fixture mode) | rehearsal, typed input, cached TTS only | problem, scheme, clinic | all OK; showed the WebSocket follower bug and empty audio bodies → fixed | no |
| REHEARSAL_take1 (live, re-run) | rehearsal, live | all | OK, but the contact sheet showed a **name-extraction bug** (unpunctuated Kannada transcript), a Timbre 502, and Mission Control scrolled off-screen during the fill | no |
| REHEARSAL_take2 | rehearsal, live | all | OK; showed the agent never screenshotted filled forms or the validation error (product fix), and the receipt was not framed | no |
| REHEARSAL_take3 | rehearsal, live | all | scheme OK; clinic failed because earlier rehearsals had booked the morning slots (recorder now tries other days); used to build and tune the edit | no |
| take1 (first attempt) | live | problem, scheme | **aborted: the disk filled up** while saving screenshots; renamed FAILED_take1_diskfull | no |
| **take1** | **live, final** | problem, scheme | all OK: live Prisma ×3 (exact Kannada transcripts), validation error + recovery, injection probe ignored, receipt GS-SC-2D2959 found in `demo_applications` | **yes, all outputs** |

Why take1: it is the only final live take with every integrity check passing (see `demo-output/qc/qc_report.md`), and
its contact sheet (`demo-output/qc/sheet_gramsetu_master_16x9_*.jpg`) shows no stuck spinners, error toasts or
permission prompts. The rehearsal contact sheets are in `demo-output/qc/REHEARSAL_*`.

The clinic montage was dropped from the master: it ran over 90 s, and the brief says "never at the cost of clarity".
The clinic scene still works (`python scripts/record_demo.py --live --take N --scene clinic`; the `montage` segment is
in edl.json).

## Analysis pass (take1, scheme scene: 208 s raw)

* Dead time cut, identified from the event log and the frame log (no repaints = idle):
  * about 3.5 s between the mic click and the clip starting (getUserMedia + decode): cut between `speak` and `speak_voice`
  * the 20 s PM-KISAN guidance reply: only its first 4 s are kept (`understand`), cut on a sentence of the caption
  * the mobile number, 25 s summary read-back and voice confirmation: compressed into `fast_review`, labelled "15× speed"
  * readability holds and speech-idle waits between steps
* Waits kept in real time because they are informative: the Prisma wait after the long request (callout "Waiting for
  Gnani Prisma (real time)"), and the 2 s live fill in Mission Control.
* The three "wow" moments, each with a zoom and a callout: (1) the live Kannada transcript appearing; (2) the form filling
  itself, shown as the agent's own screenshots enlarged, including the portal's validation error and the corrected
  "2.00"; (3) the verified receipt read aloud by Timbre, zoomed on "Verified from the portal's stored record".

## Integrity rules as implemented

* Order is preserved; the only out-of-order shot is the 2.3 s hook preview (a frame from the history replay under the
  hook text), the standard "preview" convention.
* Every speed change is labelled on screen ("15× speed", "2× speed", "2.5× speed") and drops audio.
* The validation error and recovery are always shown (screenshots 7 and 8, plus a callout) in every cut except the
  20 s hook, which shows them at 2.5× speed.
* The voice label shows whenever the user voice plays; "Demo portal · synthetic data" is on every footage frame;
  "Understanding: rules engine (no AI model)" shows while the reasoning result is on screen.
* Captions: user lines from `sentences.json`; GramSetu lines in English from the app's own en-IN templates
  (`scripts/demo/translate.py`); the transcript caption quotes the real Prisma output logged in the take.
* Audio: clips placed at logged wall-clock times; a clip that was already playing before a cut is dropped (no
  mid-sentence starts). Long replies may be faded out at a segment end; QC lists every such clip.
* Latency numbers on screen come only from the Latency HUD text logged in the take.
