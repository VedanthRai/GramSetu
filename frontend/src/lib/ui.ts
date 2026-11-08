// Interface chrome strings (pending native review). Assistant speech comes from the server templates.
import type { LangCode } from "./api";

type Key =
  | "speak" | "stop" | "send" | "edit" | "listening" | "transcribing" | "thinking" | "executing" | "speaking" | "ready"
  | "approveStart" | "approveFinal" | "cancel" | "looksRight" | "typeInstead" | "upload" | "replay" | "newTask"
  | "secureCode" | "submitCode" | "doneInBrowser" | "tapToSpeak" | "secondsLeft";

const T: Record<Key, Record<LangCode, string>> = {
  speak: { "en-IN": "Speak", "hi-IN": "बोलिए", "kn-IN": "ಮಾತನಾಡಿ", "ta-IN": "பேசுங்கள்" },
  stop: { "en-IN": "Stop", "hi-IN": "रोकें", "kn-IN": "ನಿಲ್ಲಿಸಿ", "ta-IN": "நிறுத்து" },
  send: { "en-IN": "Use this", "hi-IN": "यही भेजें", "kn-IN": "ಇದನ್ನು ಕಳುಹಿಸಿ", "ta-IN": "இதை அனுப்பு" },
  edit: { "en-IN": "Edit", "hi-IN": "बदलें", "kn-IN": "ತಿದ್ದಿ", "ta-IN": "திருத்து" },
  listening: { "en-IN": "Listening…", "hi-IN": "सुन रहा हूँ…", "kn-IN": "ಕೇಳುತ್ತಿದ್ದೇನೆ…", "ta-IN": "கேட்கிறேன்…" },
  transcribing: { "en-IN": "Transcribing with Prisma…", "hi-IN": "Prisma लिख रहा है…", "kn-IN": "Prisma ಬರೆಯುತ್ತಿದೆ…", "ta-IN": "Prisma எழுதுகிறது…" },
  thinking: { "en-IN": "Understanding…", "hi-IN": "समझ रहा हूँ…", "kn-IN": "ಅರ್ಥಮಾಡಿಕೊಳ್ಳುತ್ತಿದ್ದೇನೆ…", "ta-IN": "புரிந்துகொள்கிறேன்…" },
  executing: { "en-IN": "Working on the portal…", "hi-IN": "पोर्टल पर काम हो रहा है…", "kn-IN": "ಪೋರ್ಟಲ್‌ನಲ್ಲಿ ಕೆಲಸ ನಡೆಯುತ್ತಿದೆ…", "ta-IN": "போர்ட்டலில் வேலை நடக்கிறது…" },
  speaking: { "en-IN": "Speaking (Timbre)…", "hi-IN": "बोल रहा हूँ (Timbre)…", "kn-IN": "ಮಾತನಾಡುತ್ತಿದ್ದೇನೆ (Timbre)…", "ta-IN": "பேசுகிறேன் (Timbre)…" },
  ready: { "en-IN": "Tap and speak", "hi-IN": "दबाइए और बोलिए", "kn-IN": "ಒತ್ತಿ ಮಾತನಾಡಿ", "ta-IN": "அழுத்திப் பேசுங்கள்" },
  approveStart: { "en-IN": "Approve and start", "hi-IN": "अनुमति दें और शुरू करें", "kn-IN": "ಅನುಮತಿಸಿ ಮತ್ತು ಪ್ರಾರಂಭಿಸಿ", "ta-IN": "அனுமதித்துத் தொடங்கு" },
  approveFinal: { "en-IN": "Approve final step", "hi-IN": "अंतिम कदम की अनुमति दें", "kn-IN": "ಅಂತಿಮ ಹಂತಕ್ಕೆ ಅನುಮತಿಸಿ", "ta-IN": "இறுதிப் படிக்கு அனுமதி" },
  cancel: { "en-IN": "Cancel", "hi-IN": "रद्द करें", "kn-IN": "ರದ್ದುಮಾಡಿ", "ta-IN": "ரத்து செய்" },
  looksRight: { "en-IN": "Looks right", "hi-IN": "सही है", "kn-IN": "ಸರಿಯಾಗಿದೆ", "ta-IN": "சரியாக உள்ளது" },
  typeInstead: { "en-IN": "Type instead", "hi-IN": "टाइप करें", "kn-IN": "ಟೈಪ್ ಮಾಡಿ", "ta-IN": "தட்டச்சு செய்" },
  upload: { "en-IN": "Upload audio", "hi-IN": "ऑडियो अपलोड", "kn-IN": "ಆಡಿಯೊ ಅಪ್‌ಲೋಡ್", "ta-IN": "ஆடியோ பதிவேற்று" },
  replay: { "en-IN": "Replay", "hi-IN": "फिर से सुनें", "kn-IN": "ಮತ್ತೆ ಕೇಳಿ", "ta-IN": "மீண்டும் கேள்" },
  newTask: { "en-IN": "New task", "hi-IN": "नया काम", "kn-IN": "ಹೊಸ ಕೆಲಸ", "ta-IN": "புதிய பணி" },
  secureCode: { "en-IN": "One-time code (only you type this)", "hi-IN": "एक बार का कोड (सिर्फ आप टाइप करें)", "kn-IN": "ಒಂದು ಬಾರಿಯ ಕೋಡ್ (ನೀವು ಮಾತ್ರ ಟೈಪ್ ಮಾಡಿ)", "ta-IN": "ஒருமுறைக் குறியீடு (நீங்கள் மட்டும் தட்டச்சு செய்யுங்கள்)" },
  submitCode: { "en-IN": "Enter code on portal", "hi-IN": "पोर्टल पर कोड डालें", "kn-IN": "ಪೋರ್ಟಲ್‌ನಲ್ಲಿ ಕೋಡ್ ನಮೂದಿಸಿ", "ta-IN": "போர்ட்டலில் குறியீட்டை உள்ளிடு" },
  doneInBrowser: { "en-IN": "I did it in the browser window", "hi-IN": "मैंने ब्राउज़र में कर दिया", "kn-IN": "ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಮಾಡಿದ್ದೇನೆ", "ta-IN": "உலாவியில் செய்துவிட்டேன்" },
  tapToSpeak: { "en-IN": "Tap to stop", "hi-IN": "रोकने के लिए दबाएँ", "kn-IN": "ನಿಲ್ಲಿಸಲು ಒತ್ತಿ", "ta-IN": "நிறுத்த அழுத்து" },
  secondsLeft: { "en-IN": "s left", "hi-IN": " सेकंड बाकी", "kn-IN": " ಸೆಕೆಂಡ್ ಉಳಿದಿದೆ", "ta-IN": " வினாடி மீதம்" },
};

export function ui(key: Key, lang: LangCode): string {
  return T[key][lang] ?? T[key]["en-IN"];
}

export const STATE_LABEL: Record<string, string> = {
  IDLE: "Ready", AWAITING_MIC_PERMISSION: "Waiting for microphone permission", LISTENING: "Listening",
  TRANSCRIBING: "Transcribing", INTERPRETING: "Understanding", NEEDS_CLARIFICATION: "Needs one more detail",
  PREVIEWING_TASK: "Review the summary", AWAITING_CONSENT: "Waiting for your approval", EXECUTING: "Working on the demo portal",
  AWAITING_USER_ACTION: "Your action needed", PAUSED_FOR_CONFIRMATION: "Final approval needed", VERIFYING: "Verifying",
  COMPLETED: "Completed — verified", FAILED: "Stopped — not completed", CANCELLED: "Cancelled",
};

export const INTENT_LABEL: Record<string, string> = {
  scheme_application: "Scheme application (PM-KISAN-style demo)",
  clinic_appointment: "Doctor's appointment (demo clinic)",
  cancel_appointment: "Cancel a demo booking",
};
