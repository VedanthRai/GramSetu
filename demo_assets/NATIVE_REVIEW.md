# Native-language review sheet

Every non-English line in the demo video is **[pending native review]**. Please ask a native Kannada speaker (and a
Hindi speaker for the clinic line) to tick each box, or write a corrected line next to it. After editing
`demo_assets/sentences.json`, rebuild everything with one command:

```bash
bash scripts/build_video.sh        # or: make video
```

All of these voices are AI-generated with Gnani Timbre (model `timbre-v2.5`). The user's lines are spoken by the
Timbre voice **Kavin** (Kannada) or **Deepak** (Hindi); GramSetu's replies use **Saanvi** (Kannada); narration uses **Pranav** (English).

## A. The user's lines (demo_assets/sentences.json)

| # | Lang | Native script | English meaning | Natural, everyday spoken style? | Pronunciation OK in the Timbre audio? |
|---|---|---|---|---|---|
| 1 | kn-IN | ನಮಸ್ಕಾರ. ನಾನು ರೈತ, ನನ್ನ ಹೆಸರು ರಮೇಶ್ ಕುಮಾರ್. ಬೆಂಗಳೂರು ಕಡೆ, ಊರು ಹಾರೋಹಳ್ಳಿ. ಎರಡು ಎಕರೆ ಜಮೀನು ಇದೆ, ನನ್ನ ಹೆಸರಲ್ಲೇ. ಬ್ಯಾಂಕ್ ಖಾತೆನೂ ಇದೆ. ಪಿಎಂ ಕಿಸಾನ್ ಡೆಮೊ ಫಾರ್ಮ್ ತುಂಬೋಕೆ ಸಹಾಯ ಮಾಡಿ. | Hello. I'm a farmer, my name is Ramesh Kumar. From the Bengaluru side, village Harohalli. I have two acres of land, in my own name. I have a bank account too. Please help me fill the PM-KISAN demo form. | [ ] [pending native review] | [ ] [pending native review] |
| 2 | kn-IN | ಬೆಂಗಳೂರು ಗ್ರಾಮಾಂತರ. | Bengaluru Rural. | [ ] [pending native review] | [ ] [pending native review] |
| 3 | kn-IN | ಹೌದು, ಎಲ್ಲಾ ಸರಿ ಇದೆ. | Yes, everything is correct. | [ ] [pending native review] | [ ] [pending native review] |
| 4 | hi-IN | मुझे कल सुबह डॉक्टर को दिखाना है। | I need to see a doctor tomorrow morning. | [ ] [pending native review] | [ ] [pending native review] |

Audio files to listen to: `demo_assets/generated/kn_request.wav`, `kn_district.wav`, `kn_confirm.wav`, `hi_clinic.wav`.

## B. GramSetu's spoken replies that appear in the video (from `backend/app/services/i18n.py`, Kannada)

These are the app's own templates; the English captions in the video are the app's en-IN version of the same template.

| Reply | Kannada (as spoken by Timbre voice Saanvi) | English template | OK? |
|---|---|---|---|
| greeting | ನಮಸ್ಕಾರ. ನಿಮಗೆ ಏನು ಬೇಕು ಎಂದು ಹೇಳಿ — ಯೋಜನೆಯ ಅರ್ಜಿ ಅಥವಾ ವೈದ್ಯರ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್. | Namaste. Tell me what you need — a scheme application or a doctor's appointment. | [ ] [pending native review] |
| district question | ಬೆಂಗಳೂರು ಹೆಸರಿನಲ್ಲಿ ಒಂದಕ್ಕಿಂತ ಹೆಚ್ಚು ಜಿಲ್ಲೆಗಳಿವೆ: ಬೆಂಗಳೂರು ನಗರ, ಬೆಂಗಳೂರು ಗ್ರಾಮಾಂತರ. ಯಾವುದು? | Bengaluru has more than one district: Bengaluru Urban, Bengaluru Rural. Which one? | [ ] [pending native review] |
| mobile question | ಡೆಮೊ ಪೋರ್ಟಲ್ ಯಾವ ಮೊಬೈಲ್ ಸಂಖ್ಯೆಗೆ ಪರಿಶೀಲನಾ ಕೋಡ್ ಕಳುಹಿಸಬೇಕು? ನೀವು ಟೈಪ್ ಮಾಡಬಹುದು. | Which mobile number should the demo portal send the verification code to? You can type it. | [ ] [pending native review] |
| consent | ನಾನು ಡೆಮೊ ಪೋರ್ಟಲ್ ತೆರೆದು ಇದನ್ನು ತುಂಬಲೇ? ಅಂತಿಮ ಸಲ್ಲಿಕೆಯ ಮೊದಲು ನಾನು ಮತ್ತೆ ಕೇಳುತ್ತೇನೆ. | Shall I open the demo portal and fill this in? I will stop and ask you again before the final submit. | [ ] [pending native review] |
| OTP prompt, final approval, recovery note, receipt, PM-KISAN guidance, review summary | see `backend/app/services/i18n.py` (`otp.*`, `final.*`, `recovered`, `done.scheme`, `scheme.guidance`, `review.*`) | same file, `en-IN` | [ ] [pending native review] |

## C. On-screen text written for the video

All captions, labels and cards in the edit are English except the native-script captions, which reproduce the lines
above exactly (user lines from `sentences.json`, GramSetu lines as spoken). Nothing else needs language review.

Reviewer name: ____________________  Date: ____________
