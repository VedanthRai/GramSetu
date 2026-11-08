# QC report

Take: `takes/take2` (live: True)

## Integrity (from the take's audit log and DB)

- take: `takes/take2`
- live: `True`
- validation_error_in_audit_log: `True`
- recovery_in_audit_log: `True`
- injection_probe_ignored: `True`
- final_state: `COMPLETED`
- receipt: `{'reference': 'GS-SC-57A608', 'description': 'record found — demo application GS-SC-57A608 stored'}`
- persisted_demo_record: `{'demo_applications.reference': 1}`
- page_errors: `[]`

## Videos

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

## Per-video detail

### gramsetu_hook_20s_16x9.mp4
- sped-up pieces (labelled on screen): ['speak_fast (7.33x)', 'history_short (2.5x)']
- Timbre/voice clips placed: 2; clips entering mid-way after a cut: []
- clips faded out early by a cut (end of a long reply): ['kn_request.wav at 2.9s (4.0s kept)', 'd801869e53e504ad.wav at 14.1s (3.4s kept)']
- render warnings: []
- contact sheets: ['qc\\sheet_gramsetu_hook_20s_16x9_01.jpg', 'qc\\phone390_gramsetu_hook_20s_16x9_01.jpg']

### gramsetu_master_16x9.mp4
- sped-up pieces (labelled on screen): ['fast_review (14.76x)', 'otp (2.0x)']
- Timbre/voice clips placed: 10; clips entering mid-way after a cut: []
- clips faded out early by a cut (end of a long reply): ['326f50c46827b384.wav at 28.26s (3.8s kept)', '91ad3c7a4ed3b90c.wav at 46.41s (1.78s kept)', '153ce55a9812e2eb.wav at 52.41s (2.55s kept)']
- render warnings: ['INFO history: dropped clip already playing before the cut (ಪೋರ್ಟಲ್\u200cಗೆ ಒಂದು ಬಾರಿಯ ಕೋಡ್ ಬೇಕ…)']
- contact sheets: ['qc\\sheet_gramsetu_master_16x9_01.jpg', 'qc\\sheet_gramsetu_master_16x9_02.jpg', 'qc\\sheet_gramsetu_master_16x9_03.jpg', 'qc\\sheet_gramsetu_master_16x9_04.jpg', 'qc\\phone390_gramsetu_master_16x9_01.jpg']

### gramsetu_square_1x1.mp4
- sped-up pieces (labelled on screen): ['fast_review (14.76x)', 'otp (2.0x)']
- Timbre/voice clips placed: 10; clips entering mid-way after a cut: []
- clips faded out early by a cut (end of a long reply): ['326f50c46827b384.wav at 28.26s (3.8s kept)', '91ad3c7a4ed3b90c.wav at 46.41s (1.78s kept)', '153ce55a9812e2eb.wav at 52.41s (2.55s kept)']
- render warnings: ['INFO history: dropped clip already playing before the cut (ಪೋರ್ಟಲ್\u200cಗೆ ಒಂದು ಬಾರಿಯ ಕೋಡ್ ಬೇಕ…)']
- contact sheets: ['qc\\sheet_gramsetu_square_1x1_01.jpg', 'qc\\sheet_gramsetu_square_1x1_02.jpg', 'qc\\sheet_gramsetu_square_1x1_03.jpg', 'qc\\sheet_gramsetu_square_1x1_04.jpg', 'qc\\phone390_gramsetu_square_1x1_01.jpg']

### gramsetu_teaser_45s.mp4
- sped-up pieces (labelled on screen): ['history_short (2.5x)']
- Timbre/voice clips placed: 4; clips entering mid-way after a cut: []
- clips faded out early by a cut (end of a long reply): ['326f50c46827b384.wav at 24.76s (3.8s kept)', '153ce55a9812e2eb.wav at 29.78s (2.55s kept)', 'd801869e53e504ad.wav at 37.32s (3.4s kept)']
- render warnings: []
- contact sheets: ['qc\\sheet_gramsetu_teaser_45s_01.jpg', 'qc\\sheet_gramsetu_teaser_45s_02.jpg', 'qc\\phone390_gramsetu_teaser_45s_01.jpg']

### gramsetu_vertical_9x16.mp4
- sped-up pieces (labelled on screen): ['history_short (2.5x)']
- Timbre/voice clips placed: 3; clips entering mid-way after a cut: []
- clips faded out early by a cut (end of a long reply): ['153ce55a9812e2eb.wav at 24.48s (2.55s kept)', 'd801869e53e504ad.wav at 32.02s (3.4s kept)']
- render warnings: []
- contact sheets: ['qc\\sheet_gramsetu_vertical_9x16_01.jpg', 'qc\\sheet_gramsetu_vertical_9x16_02.jpg', 'qc\\phone390_gramsetu_vertical_9x16_01.jpg']

### hook_variant_A.mp4
- sped-up pieces (labelled on screen): []
- Timbre/voice clips placed: 6; clips entering mid-way after a cut: []
- clips faded out early by a cut (end of a long reply): ['326f50c46827b384.wav at 24.76s (3.8s kept)', '153ce55a9812e2eb.wav at 35.78s (2.55s kept)']
- render warnings: ['INFO history: dropped clip already playing before the cut (ಪೋರ್ಟಲ್\u200cಗೆ ಒಂದು ಬಾರಿಯ ಕೋಡ್ ಬೇಕ…)']
- contact sheets: ['qc\\sheet_hook_variant_A_01.jpg', 'qc\\sheet_hook_variant_A_02.jpg', 'qc\\sheet_hook_variant_A_03.jpg', 'qc\\phone390_hook_variant_A_01.jpg']

### hook_variant_B.mp4
- sped-up pieces (labelled on screen): []
- Timbre/voice clips placed: 6; clips entering mid-way after a cut: []
- clips faded out early by a cut (end of a long reply): ['326f50c46827b384.wav at 24.76s (3.8s kept)', '153ce55a9812e2eb.wav at 35.78s (2.55s kept)']
- render warnings: ['INFO history: dropped clip already playing before the cut (ಪೋರ್ಟಲ್\u200cಗೆ ಒಂದು ಬಾರಿಯ ಕೋಡ್ ಬೇಕ…)']
- contact sheets: ['qc\\sheet_hook_variant_B_01.jpg', 'qc\\sheet_hook_variant_B_02.jpg', 'qc\\sheet_hook_variant_B_03.jpg', 'qc\\phone390_hook_variant_B_01.jpg']

### hook_variant_C.mp4
- sped-up pieces (labelled on screen): []
- Timbre/voice clips placed: 6; clips entering mid-way after a cut: []
- clips faded out early by a cut (end of a long reply): ['326f50c46827b384.wav at 24.76s (3.8s kept)', '153ce55a9812e2eb.wav at 35.78s (2.55s kept)']
- render warnings: ['INFO history: dropped clip already playing before the cut (ಪೋರ್ಟಲ್\u200cಗೆ ಒಂದು ಬಾರಿಯ ಕೋಡ್ ಬೇಕ…)']
- contact sheets: ['qc\\sheet_hook_variant_C_01.jpg', 'qc\\sheet_hook_variant_C_02.jpg', 'qc\\sheet_hook_variant_C_03.jpg', 'qc\\phone390_hook_variant_C_01.jpg']

## Secret scan

- files scanned: 56; configured keys checked: 1
- hits: none

## Files in final/ (MB)

- gramsetu_hook_20s_16x9.captions_en.srt: 0.0
- gramsetu_hook_20s_16x9.captions_kn.srt: 0.0
- gramsetu_hook_20s_16x9.mp4: 3.25
- gramsetu_master_16x9.captions_en.srt: 0.0
- gramsetu_master_16x9.captions_kn.srt: 0.0
- gramsetu_master_16x9.mp4: 12.71
- gramsetu_square_1x1.captions_en.srt: 0.0
- gramsetu_square_1x1.captions_kn.srt: 0.0
- gramsetu_square_1x1.mp4: 7.03
- gramsetu_teaser_45s.captions_en.srt: 0.0
- gramsetu_teaser_45s.captions_kn.srt: 0.0
- gramsetu_teaser_45s.mp4: 6.69
- gramsetu_vertical_9x16.captions_en.srt: 0.0
- gramsetu_vertical_9x16.captions_kn.srt: 0.0
- gramsetu_vertical_9x16.mp4: 3.5
- hook_variant_A.captions_en.srt: 0.0
- hook_variant_A.captions_kn.srt: 0.0
- hook_variant_A.mp4: 9.6
- hook_variant_B.captions_en.srt: 0.0
- hook_variant_B.captions_kn.srt: 0.0
- hook_variant_B.mp4: 9.6
- hook_variant_C.captions_en.srt: 0.0
- hook_variant_C.captions_kn.srt: 0.0
- hook_variant_C.mp4: 9.6
- readme_loop.gif: 1.16
- social_card_1200x627.png: 0.42
- thumbnail_1080x1350.png: 0.34
- thumbnail_1920x1080.png: 0.93
