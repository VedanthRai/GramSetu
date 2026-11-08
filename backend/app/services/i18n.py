"""User-facing message templates. The same string is displayed AND spoken (Timbre), so meaning never drifts.

Translations were written by the build engineer and are marked PENDING NATIVE REVIEW (see docs/demo-script.md).
"""
from __future__ import annotations

NATIVE_REVIEW_STATUS = "pending native review"

M: dict[str, dict[str, str]] = {
    "greeting": {
        "en-IN": "Namaste. Tell me what you need — a scheme application or a doctor's appointment.",
        "hi-IN": "नमस्ते। बताइए आपको क्या चाहिए — योजना का आवेदन या डॉक्टर की अपॉइंटमेंट।",
        "kn-IN": "ನಮಸ್ಕಾರ. ನಿಮಗೆ ಏನು ಬೇಕು ಎಂದು ಹೇಳಿ — ಯೋಜನೆಯ ಅರ್ಜಿ ಅಥವಾ ವೈದ್ಯರ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್.",
        "ta-IN": "வணக்கம். உங்களுக்கு என்ன வேண்டும் என்று சொல்லுங்கள் — திட்ட விண்ணப்பம் அல்லது மருத்துவர் சந்திப்பு.",
    },
    "ask.full_name": {
        "en-IN": "What is the applicant's full name?",
        "hi-IN": "आवेदक का पूरा नाम क्या है?",
        "kn-IN": "ಅರ್ಜಿದಾರರ ಪೂರ್ಣ ಹೆಸರು ಏನು?",
        "ta-IN": "விண்ணப்பதாரரின் முழுப் பெயர் என்ன?",
    },
    "ask.state": {
        "en-IN": "Which state is your land in?",
        "hi-IN": "आपकी जमीन किस राज्य में है?",
        "kn-IN": "ನಿಮ್ಮ ಜಮೀನು ಯಾವ ರಾಜ್ಯದಲ್ಲಿದೆ?",
        "ta-IN": "உங்கள் நிலம் எந்த மாநிலத்தில் உள்ளது?",
    },
    "ask.district": {
        "en-IN": "Which district?",
        "hi-IN": "कौन सा जिला?",
        "kn-IN": "ಯಾವ ಜಿಲ್ಲೆ?",
        "ta-IN": "எந்த மாவட்டம்?",
    },
    "ask.district_ambiguous": {
        "en-IN": "{place} has more than one district: {options}. Which one?",
        "hi-IN": "{place} नाम के एक से ज़्यादा जिले हैं: {options}। कौन सा?",
        "kn-IN": "{place} ಹೆಸರಿನಲ್ಲಿ ಒಂದಕ್ಕಿಂತ ಹೆಚ್ಚು ಜಿಲ್ಲೆಗಳಿವೆ: {options}. ಯಾವುದು?",
        "ta-IN": "{place} என்ற பெயரில் ஒன்றுக்கு மேற்பட்ட மாவட்டங்கள் உள்ளன: {options}. எது?",
    },
    "ask.village": {
        "en-IN": "What is the name of your village?",
        "hi-IN": "आपके गाँव का नाम क्या है?",
        "kn-IN": "ನಿಮ್ಮ ಗ್ರಾಮದ ಹೆಸರು ಏನು?",
        "ta-IN": "உங்கள் கிராமத்தின் பெயர் என்ன?",
    },
    "ask.land_area_acres": {
        "en-IN": "How many acres of land do you hold?",
        "hi-IN": "आपके पास कितने एकड़ जमीन है?",
        "kn-IN": "ನಿಮ್ಮ ಬಳಿ ಎಷ್ಟು ಎಕರೆ ಜಮೀನು ಇದೆ?",
        "ta-IN": "உங்களிடம் எத்தனை ஏக்கர் நிலம் உள்ளது?",
    },
    "ask.ownership": {
        "en-IN": "Is the land in your own name, or do you farm it as a tenant?",
        "hi-IN": "क्या जमीन आपके अपने नाम पर है, या आप किराए पर खेती करते हैं?",
        "kn-IN": "ಜಮೀನು ನಿಮ್ಮ ಸ್ವಂತ ಹೆಸರಿನಲ್ಲಿದೆಯೇ, ಅಥವಾ ಗೇಣಿಗೆ ಸಾಗುವಳಿ ಮಾಡುತ್ತೀರಾ?",
        "ta-IN": "நிலம் உங்கள் சொந்தப் பெயரில் உள்ளதா, அல்லது குத்தகைக்கு விவசாயம் செய்கிறீர்களா?",
    },
    "ask.bank_account_linked": {
        "en-IN": "Do you have a bank account in your name? Yes or no.",
        "hi-IN": "क्या आपके नाम पर बैंक खाता है? हाँ या नहीं।",
        "kn-IN": "ನಿಮ್ಮ ಹೆಸರಿನಲ್ಲಿ ಬ್ಯಾಂಕ್ ಖಾತೆ ಇದೆಯೇ? ಹೌದು ಅಥವಾ ಇಲ್ಲ.",
        "ta-IN": "உங்கள் பெயரில் வங்கிக் கணக்கு உள்ளதா? ஆம் அல்லது இல்லை.",
    },
    "ask.mobile": {
        "en-IN": "Which mobile number should the demo portal send the verification code to? You can type it.",
        "hi-IN": "डेमो पोर्टल किस मोबाइल नंबर पर सत्यापन कोड भेजे? आप इसे टाइप कर सकते हैं।",
        "kn-IN": "ಡೆಮೊ ಪೋರ್ಟಲ್ ಯಾವ ಮೊಬೈಲ್ ಸಂಖ್ಯೆಗೆ ಪರಿಶೀಲನಾ ಕೋಡ್ ಕಳುಹಿಸಬೇಕು? ನೀವು ಟೈಪ್ ಮಾಡಬಹುದು.",
        "ta-IN": "டெமோ போர்ட்டல் எந்த மொபைல் எண்ணுக்கு சரிபார்ப்புக் குறியீட்டை அனுப்ப வேண்டும்? நீங்கள் தட்டச்சு செய்யலாம்.",
    },
    "ask.department": {
        "en-IN": "Which department? General medicine, children's doctor, bones and joints, or ear-nose-throat.",
        "hi-IN": "कौन सा विभाग? सामान्य चिकित्सा, बच्चों के डॉक्टर, हड्डी, या कान-नाक-गला।",
        "kn-IN": "ಯಾವ ವಿಭಾಗ? ಸಾಮಾನ್ಯ ವೈದ್ಯಕೀಯ, ಮಕ್ಕಳ ವೈದ್ಯರು, ಮೂಳೆ, ಅಥವಾ ಕಿವಿ-ಮೂಗು-ಗಂಟಲು.",
        "ta-IN": "எந்தப் பிரிவு? பொது மருத்துவம், குழந்தை மருத்துவர், எலும்பு, அல்லது காது-மூக்கு-தொண்டை.",
    },
    "ask.location": {
        "en-IN": "Which clinic location? Bengaluru, Mysuru, Chennai or Lucknow.",
        "hi-IN": "कौन सा क्लिनिक? बेंगलुरु, मैसूरु, चेन्नई या लखनऊ।",
        "kn-IN": "ಯಾವ ಕ್ಲಿನಿಕ್? ಬೆಂಗಳೂರು, ಮೈಸೂರು, ಚೆನ್ನೈ ಅಥವಾ ಲಕ್ನೋ.",
        "ta-IN": "எந்த மருத்துவமனை? பெங்களூரு, மைசூரு, சென்னை அல்லது லக்னோ.",
    },
    "ask.appointment_date": {
        "en-IN": "Which day would you like the appointment?",
        "hi-IN": "आपको किस दिन अपॉइंटमेंट चाहिए?",
        "kn-IN": "ಯಾವ ದಿನ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಬೇಕು?",
        "ta-IN": "எந்த நாளில் சந்திப்பு வேண்டும்?",
    },
    "ask.slot_time": {
        "en-IN": "These times are free on {date}: {options}. Which one?",
        "hi-IN": "{date} को ये समय खाली हैं: {options}। कौन सा चाहिए?",
        "kn-IN": "{date} ರಂದು ಈ ಸಮಯಗಳು ಲಭ್ಯವಿವೆ: {options}. ಯಾವುದು ಬೇಕು?",
        "ta-IN": "{date} அன்று இந்த நேரங்கள் காலியாக உள்ளன: {options}. எது வேண்டும்?",
    },
    "ask.no_slots": {
        "en-IN": "There are no free {period} slots on {date}. Please choose another day or time of day.",
        "hi-IN": "{date} को {period} कोई समय खाली नहीं है। कृपया दूसरा दिन या समय चुनें।",
        "kn-IN": "{date} ರಂದು {period} ಯಾವುದೇ ಸಮಯ ಲಭ್ಯವಿಲ್ಲ. ದಯವಿಟ್ಟು ಬೇರೆ ದಿನ ಅಥವಾ ಸಮಯ ಆಯ್ಕೆಮಾಡಿ.",
        "ta-IN": "{date} அன்று {period} நேரம் காலியாக இல்லை. வேறு நாள் அல்லது நேரத்தைத் தேர்ந்தெடுக்கவும்.",
    },
    "ask.patient_name": {
        "en-IN": "What is the patient's name?",
        "hi-IN": "मरीज़ का नाम क्या है?",
        "kn-IN": "ರೋಗಿಯ ಹೆಸರು ಏನು?",
        "ta-IN": "நோயாளியின் பெயர் என்ன?",
    },
    "ask.booking_reference": {
        "en-IN": "Please tell me the demo booking reference you want to cancel.",
        "hi-IN": "कृपया वह डेमो बुकिंग संदर्भ बताइए जिसे रद्द करना है।",
        "kn-IN": "ರದ್ದುಮಾಡಬೇಕಾದ ಡೆಮೊ ಬುಕಿಂಗ್ ಉಲ್ಲೇಖವನ್ನು ಹೇಳಿ.",
        "ta-IN": "ரத்து செய்ய வேண்டிய டெமோ முன்பதிவு குறிப்பைச் சொல்லுங்கள்.",
    },
    "scheme.guidance": {
        "en-IN": "From the official PM-KISAN website: the scheme gives income support of 6,000 rupees per year in three equal instalments to land-holding farmer families, and eKYC is mandatory. Eligibility is decided by the State government; I cannot confirm that you are eligible. The required document list is not yet verified. I can help you fill the demo form.",
        "hi-IN": "आधिकारिक पीएम-किसान वेबसाइट के अनुसार: यह योजना भूमिधारक किसान परिवारों को साल में 6,000 रुपये तीन बराबर किस्तों में देती है, और ई-केवाईसी अनिवार्य है। पात्रता राज्य सरकार तय करती है; मैं यह पुष्टि नहीं कर सकता कि आप पात्र हैं। ज़रूरी दस्तावेज़ों की सूची अभी सत्यापित नहीं है। मैं डेमो फॉर्म भरने में मदद कर सकता हूँ।",
        "kn-IN": "ಅಧಿಕೃತ ಪಿಎಂ-ಕಿಸಾನ್ ವೆಬ್‌ಸೈಟ್ ಪ್ರಕಾರ: ಈ ಯೋಜನೆ ಜಮೀನು ಹೊಂದಿರುವ ರೈತ ಕುಟುಂಬಗಳಿಗೆ ವರ್ಷಕ್ಕೆ 6,000 ರೂಪಾಯಿಗಳನ್ನು ಮೂರು ಸಮಾನ ಕಂತುಗಳಲ್ಲಿ ನೀಡುತ್ತದೆ, ಮತ್ತು ಇ-ಕೆವೈಸಿ ಕಡ್ಡಾಯ. ಅರ್ಹತೆಯನ್ನು ರಾಜ್ಯ ಸರ್ಕಾರ ನಿರ್ಧರಿಸುತ್ತದೆ; ನೀವು ಅರ್ಹರು ಎಂದು ನಾನು ಖಚಿತಪಡಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ. ಅಗತ್ಯ ದಾಖಲೆಗಳ ಪಟ್ಟಿ ಇನ್ನೂ ಪರಿಶೀಲಿಸಲಾಗಿಲ್ಲ. ಡೆಮೊ ಫಾರ್ಮ್ ತುಂಬಲು ನಾನು ಸಹಾಯ ಮಾಡಬಲ್ಲೆ.",
        "ta-IN": "அதிகாரப்பூர்வ பிஎம்-கிசான் இணையதளத்தின்படி: இந்தத் திட்டம் நிலம் வைத்திருக்கும் விவசாயக் குடும்பங்களுக்கு ஆண்டுக்கு 6,000 ரூபாயை மூன்று சம தவணைகளில் வழங்குகிறது, மேலும் இ-கேஒய்சி கட்டாயம். தகுதியை மாநில அரசு தீர்மானிக்கிறது; நீங்கள் தகுதியானவர் என்று என்னால் உறுதிப்படுத்த முடியாது. தேவையான ஆவணப் பட்டியல் இன்னும் சரிபார்க்கப்படவில்லை. டெமோ படிவத்தை நிரப்ப நான் உதவ முடியும்.",
    },
    "review.intro": {
        "en-IN": "Please check. GramSetu will enter this on the {portal}:",
        "hi-IN": "कृपया जाँच लें। GramSetu {portal} पर यह जानकारी भरेगा:",
        "kn-IN": "ದಯವಿಟ್ಟು ಪರಿಶೀಲಿಸಿ. GramSetu {portal} ನಲ್ಲಿ ಈ ಮಾಹಿತಿಯನ್ನು ತುಂಬುತ್ತದೆ:",
        "ta-IN": "தயவுசெய்து சரிபாருங்கள். GramSetu {portal} இல் இதை நிரப்பும்:",
    },
    "review.ask": {
        "en-IN": "Is this correct? Say yes to continue, or tell me what to change.",
        "hi-IN": "क्या यह सही है? आगे बढ़ने के लिए हाँ कहें, या बताइए क्या बदलना है।",
        "kn-IN": "ಇದು ಸರಿಯೇ? ಮುಂದುವರಿಯಲು ಹೌದು ಎನ್ನಿ, ಅಥವಾ ಏನು ಬದಲಾಯಿಸಬೇಕು ಎಂದು ಹೇಳಿ.",
        "ta-IN": "இது சரியா? தொடர ஆம் என்று சொல்லுங்கள், அல்லது என்ன மாற்ற வேண்டும் என்று சொல்லுங்கள்.",
    },
    "consent.ask": {
        "en-IN": "Shall I open the demo portal and fill this in? I will stop and ask you again before the final submit.",
        "hi-IN": "क्या मैं डेमो पोर्टल खोलकर यह भर दूँ? अंतिम सबमिट से पहले मैं आपसे फिर पूछूँगा।",
        "kn-IN": "ನಾನು ಡೆಮೊ ಪೋರ್ಟಲ್ ತೆರೆದು ಇದನ್ನು ತುಂಬಲೇ? ಅಂತಿಮ ಸಲ್ಲಿಕೆಯ ಮೊದಲು ನಾನು ಮತ್ತೆ ಕೇಳುತ್ತೇನೆ.",
        "ta-IN": "டெமோ போர்ட்டலைத் திறந்து இதை நிரப்பட்டுமா? இறுதிச் சமர்ப்பிப்புக்கு முன் மீண்டும் கேட்பேன்.",
    },
    "correction.applied": {
        "en-IN": "Changed {field} to {value}.",
        "hi-IN": "{field} बदलकर {value} कर दिया।",
        "kn-IN": "{field} ಅನ್ನು {value} ಎಂದು ಬದಲಾಯಿಸಲಾಗಿದೆ.",
        "ta-IN": "{field} ஐ {value} என மாற்றினேன்.",
    },
    "exec.started": {
        "en-IN": "Opening the demo portal now. You can watch every step in Mission Control.",
        "hi-IN": "अब डेमो पोर्टल खोल रहा हूँ। हर कदम आप मिशन कंट्रोल में देख सकते हैं।",
        "kn-IN": "ಈಗ ಡೆಮೊ ಪೋರ್ಟಲ್ ತೆರೆಯುತ್ತಿದ್ದೇನೆ. ಪ್ರತಿ ಹಂತವನ್ನು ಮಿಷನ್ ಕಂಟ್ರೋಲ್‌ನಲ್ಲಿ ನೋಡಬಹುದು.",
        "ta-IN": "இப்போது டெமோ போர்ட்டலைத் திறக்கிறேன். ஒவ்வொரு படியையும் மிஷன் கண்ட்ரோலில் பார்க்கலாம்.",
    },
    "exec.recovered": {
        "en-IN": "The portal rejected a value. I corrected the format and it was accepted.",
        "hi-IN": "पोर्टल ने एक मान अस्वीकार किया। मैंने प्रारूप ठीक किया और वह स्वीकार हो गया।",
        "kn-IN": "ಪೋರ್ಟಲ್ ಒಂದು ಮೌಲ್ಯವನ್ನು ತಿರಸ್ಕರಿಸಿತು. ನಾನು ಸ್ವರೂಪವನ್ನು ಸರಿಪಡಿಸಿದೆ ಮತ್ತು ಅದು ಸ್ವೀಕರಿಸಲ್ಪಟ್ಟಿತು.",
        "ta-IN": "போர்ட்டல் ஒரு மதிப்பை நிராகரித்தது. நான் வடிவத்தைச் சரிசெய்தேன், அது ஏற்கப்பட்டது.",
    },
    "otp.needed": {
        "en-IN": "The portal needs a one-time code. Type it yourself in the secure box. Never say it aloud and never share it with anyone. I will not read, store or send it.",
        "hi-IN": "पोर्टल को एक बार का कोड चाहिए। इसे सुरक्षित बॉक्स में खुद टाइप करें। इसे कभी बोलकर न बताएँ और किसी से साझा न करें। मैं इसे न पढ़ूँगा, न रखूँगा, न भेजूँगा।",
        "kn-IN": "ಪೋರ್ಟಲ್‌ಗೆ ಒಂದು ಬಾರಿಯ ಕೋಡ್ ಬೇಕು. ಅದನ್ನು ಸುರಕ್ಷಿತ ಪೆಟ್ಟಿಗೆಯಲ್ಲಿ ನೀವೇ ಟೈಪ್ ಮಾಡಿ. ಅದನ್ನು ಎಂದಿಗೂ ಜೋರಾಗಿ ಹೇಳಬೇಡಿ, ಯಾರೊಂದಿಗೂ ಹಂಚಿಕೊಳ್ಳಬೇಡಿ. ನಾನು ಅದನ್ನು ಓದುವುದಿಲ್ಲ, ಉಳಿಸುವುದಿಲ್ಲ, ಕಳುಹಿಸುವುದಿಲ್ಲ.",
        "ta-IN": "போர்ட்டலுக்கு ஒருமுறைக் குறியீடு தேவை. அதைப் பாதுகாப்புப் பெட்டியில் நீங்களே தட்டச்சு செய்யுங்கள். அதை ஒருபோதும் சத்தமாகச் சொல்லாதீர்கள், யாரிடமும் பகிராதீர்கள். நான் அதைப் படிக்கவோ, சேமிக்கவோ, அனுப்பவோ மாட்டேன்.",
    },
    "final.ask": {
        "en-IN": "Everything is filled. Final step: {action}. This creates a demo record. Do you approve?",
        "hi-IN": "सब भर दिया गया है। अंतिम कदम: {action}। इससे एक डेमो रिकॉर्ड बनेगा। क्या आप अनुमति देते हैं?",
        "kn-IN": "ಎಲ್ಲವನ್ನೂ ತುಂಬಲಾಗಿದೆ. ಅಂತಿಮ ಹಂತ: {action}. ಇದು ಡೆಮೊ ದಾಖಲೆಯನ್ನು ರಚಿಸುತ್ತದೆ. ನೀವು ಅನುಮತಿಸುತ್ತೀರಾ?",
        "ta-IN": "அனைத்தும் நிரப்பப்பட்டுள்ளன. இறுதிப் படி: {action}. இது ஒரு டெமோ பதிவை உருவாக்கும். நீங்கள் அனுமதிக்கிறீர்களா?",
    },
    "action.submit_application": {
        "en-IN": "submit the demo application", "hi-IN": "डेमो आवेदन जमा करना",
        "kn-IN": "ಡೆಮೊ ಅರ್ಜಿ ಸಲ್ಲಿಸುವುದು", "ta-IN": "டெமோ விண்ணப்பத்தைச் சமர்ப்பித்தல்",
    },
    "action.confirm_booking": {
        "en-IN": "confirm the demo booking", "hi-IN": "डेमो बुकिंग की पुष्टि करना",
        "kn-IN": "ಡೆಮೊ ಬುಕಿಂಗ್ ದೃಢೀಕರಿಸುವುದು", "ta-IN": "டெமோ முன்பதிவை உறுதிப்படுத்துதல்",
    },
    "action.cancel_booking": {
        "en-IN": "cancel the demo booking", "hi-IN": "डेमो बुकिंग रद्द करना",
        "kn-IN": "ಡೆಮೊ ಬುಕಿಂಗ್ ರದ್ದುಮಾಡುವುದು", "ta-IN": "டெமோ முன்பதிவை ரத்து செய்தல்",
    },
    "done.application": {
        "en-IN": "Done. The demo portal stored your application. Demo reference: {ref}. This is a demo record, not an official application.",
        "hi-IN": "हो गया। डेमो पोर्टल ने आपका आवेदन सहेज लिया। डेमो संदर्भ: {ref}। यह एक डेमो रिकॉर्ड है, आधिकारिक आवेदन नहीं।",
        "kn-IN": "ಆಯಿತು. ಡೆಮೊ ಪೋರ್ಟಲ್ ನಿಮ್ಮ ಅರ್ಜಿಯನ್ನು ಉಳಿಸಿದೆ. ಡೆಮೊ ಉಲ್ಲೇಖ: {ref}. ಇದು ಡೆಮೊ ದಾಖಲೆ, ಅಧಿಕೃತ ಅರ್ಜಿ ಅಲ್ಲ.",
        "ta-IN": "முடிந்தது. டெமோ போர்ட்டல் உங்கள் விண்ணப்பத்தைச் சேமித்தது. டெமோ குறிப்பு: {ref}. இது டெமோ பதிவு, அதிகாரப்பூர்வ விண்ணப்பம் அல்ல.",
    },
    "done.booking": {
        "en-IN": "Done. Your demo appointment is booked with {doctor} on {date} at {time}. Demo reference: {ref}.",
        "hi-IN": "हो गया। आपकी डेमो अपॉइंटमेंट {doctor} के साथ {date} को {time} बजे बुक हो गई। डेमो संदर्भ: {ref}।",
        "kn-IN": "ಆಯಿತು. ನಿಮ್ಮ ಡೆಮೊ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ {doctor} ಅವರೊಂದಿಗೆ {date} ರಂದು {time} ಕ್ಕೆ ಬುಕ್ ಆಗಿದೆ. ಡೆಮೊ ಉಲ್ಲೇಖ: {ref}.",
        "ta-IN": "முடிந்தது. உங்கள் டெமோ சந்திப்பு {doctor} உடன் {date} அன்று {time} மணிக்கு முன்பதிவு ஆனது. டெமோ குறிப்பு: {ref}.",
    },
    "done.cancelled": {
        "en-IN": "The demo booking {ref} is cancelled. The slot is free again.",
        "hi-IN": "डेमो बुकिंग {ref} रद्द हो गई। वह समय फिर से खाली है।",
        "kn-IN": "ಡೆಮೊ ಬುಕಿಂಗ್ {ref} ರದ್ದಾಗಿದೆ. ಆ ಸಮಯ ಮತ್ತೆ ಲಭ್ಯವಿದೆ.",
        "ta-IN": "டெமோ முன்பதிவு {ref} ரத்து செய்யப்பட்டது. அந்த நேரம் மீண்டும் காலியாக உள்ளது.",
    },
    "fail.unverified": {
        "en-IN": "I could not confirm that this worked. Nothing is marked complete. {detail}",
        "hi-IN": "मैं पुष्टि नहीं कर सका कि यह सफल हुआ। कुछ भी पूरा नहीं माना गया। {detail}",
        "kn-IN": "ಇದು ಯಶಸ್ವಿಯಾಯಿತು ಎಂದು ನಾನು ಖಚಿತಪಡಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ. ಯಾವುದನ್ನೂ ಪೂರ್ಣ ಎಂದು ಗುರುತಿಸಿಲ್ಲ. {detail}",
        "ta-IN": "இது வெற்றியடைந்ததா என்று என்னால் உறுதிப்படுத்த முடியவில்லை. எதுவும் முடிந்ததாகக் குறிக்கப்படவில்லை. {detail}",
    },
    "emergency": {
        "en-IN": "This may be an emergency. Please call 112 now, or go to the nearest hospital. I am an AI assistant and cannot give medical advice. I have stopped the booking.",
        "hi-IN": "यह आपातकाल हो सकता है। कृपया अभी 112 पर कॉल करें, या नज़दीकी अस्पताल जाएँ। मैं एक एआई सहायक हूँ और चिकित्सा सलाह नहीं दे सकता। मैंने बुकिंग रोक दी है।",
        "kn-IN": "ಇದು ತುರ್ತು ಪರಿಸ್ಥಿತಿ ಇರಬಹುದು. ದಯವಿಟ್ಟು ಈಗಲೇ 112 ಗೆ ಕರೆ ಮಾಡಿ, ಅಥವಾ ಹತ್ತಿರದ ಆಸ್ಪತ್ರೆಗೆ ಹೋಗಿ. ನಾನು ಎಐ ಸಹಾಯಕ, ವೈದ್ಯಕೀಯ ಸಲಹೆ ನೀಡಲಾರೆ. ನಾನು ಬುಕಿಂಗ್ ನಿಲ್ಲಿಸಿದ್ದೇನೆ.",
        "ta-IN": "இது அவசரநிலையாக இருக்கலாம். உடனே 112 ஐ அழையுங்கள், அல்லது அருகிலுள்ள மருத்துவமனைக்குச் செல்லுங்கள். நான் ஒரு AI உதவியாளர், மருத்துவ ஆலோசனை வழங்க முடியாது. முன்பதிவை நிறுத்திவிட்டேன்.",
    },
    "scam": {
        "en-IN": "Careful. Never share an OTP, PIN, password or bank details with anyone — not even someone who says they are from the government or a bank. Real government offices do not ask for these on the phone. I have not used what you said.",
        "hi-IN": "सावधान। ओटीपी, पिन, पासवर्ड या बैंक विवरण कभी किसी को न बताएँ — उसे भी नहीं जो खुद को सरकारी या बैंक कर्मचारी बताए। असली सरकारी दफ्तर फ़ोन पर ये नहीं माँगते। आपकी कही बात का मैंने उपयोग नहीं किया।",
        "kn-IN": "ಎಚ್ಚರಿಕೆ. ಒಟಿಪಿ, ಪಿನ್, ಪಾಸ್‌ವರ್ಡ್ ಅಥವಾ ಬ್ಯಾಂಕ್ ವಿವರಗಳನ್ನು ಯಾರಿಗೂ ಹೇಳಬೇಡಿ — ಸರ್ಕಾರ ಅಥವಾ ಬ್ಯಾಂಕ್‌ನಿಂದ ಬಂದವರೆಂದು ಹೇಳುವವರಿಗೂ ಸಹ. ನಿಜವಾದ ಸರ್ಕಾರಿ ಕಚೇರಿಗಳು ಫೋನ್‌ನಲ್ಲಿ ಇವನ್ನು ಕೇಳುವುದಿಲ್ಲ. ನೀವು ಹೇಳಿದ್ದನ್ನು ನಾನು ಬಳಸಿಲ್ಲ.",
        "ta-IN": "கவனம். ஓடிபி, பின், கடவுச்சொல் அல்லது வங்கி விவரங்களை யாரிடமும் பகிராதீர்கள் — அரசு அல்லது வங்கியிலிருந்து பேசுவதாகச் சொல்பவரிடமும் கூட. உண்மையான அரசு அலுவலகங்கள் தொலைபேசியில் இவற்றைக் கேட்பதில்லை. நீங்கள் சொன்னதை நான் பயன்படுத்தவில்லை.",
    },
    "unsupported": {
        "en-IN": "I can help with two demo services: a PM-KISAN-style scheme application, and a doctor's appointment at the demo clinic. Which one?",
        "hi-IN": "मैं दो डेमो सेवाओं में मदद कर सकता हूँ: पीएम-किसान जैसी योजना का आवेदन, और डेमो क्लिनिक में डॉक्टर की अपॉइंटमेंट। कौन सी?",
        "kn-IN": "ನಾನು ಎರಡು ಡೆಮೊ ಸೇವೆಗಳಲ್ಲಿ ಸಹಾಯ ಮಾಡಬಲ್ಲೆ: ಪಿಎಂ-ಕಿಸಾನ್ ರೀತಿಯ ಯೋಜನೆಯ ಅರ್ಜಿ, ಮತ್ತು ಡೆಮೊ ಕ್ಲಿನಿಕ್‌ನಲ್ಲಿ ವೈದ್ಯರ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್. ಯಾವುದು?",
        "ta-IN": "இரண்டு டெமோ சேவைகளில் உதவ முடியும்: பிஎம்-கிசான் போன்ற திட்ட விண்ணப்பம், மற்றும் டெமோ மருத்துவமனையில் மருத்துவர் சந்திப்பு. எது?",
    },
    "medical_boundary": {
        "en-IN": "I am an AI assistant. I can book an appointment, but I cannot diagnose or suggest treatment or medicines.",
        "hi-IN": "मैं एक एआई सहायक हूँ। मैं अपॉइंटमेंट बुक कर सकता हूँ, लेकिन बीमारी की पहचान, इलाज या दवा की सलाह नहीं दे सकता।",
        "kn-IN": "ನಾನು ಎಐ ಸಹಾಯಕ. ನಾನು ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಬುಕ್ ಮಾಡಬಲ್ಲೆ, ಆದರೆ ರೋಗ ಪತ್ತೆ, ಚಿಕಿತ್ಸೆ ಅಥವಾ ಔಷಧಿ ಸಲಹೆ ನೀಡಲಾರೆ.",
        "ta-IN": "நான் ஒரு AI உதவியாளர். சந்திப்பை முன்பதிவு செய்ய முடியும், ஆனால் நோயறிதல், சிகிச்சை அல்லது மருந்து ஆலோசனை வழங்க முடியாது.",
    },
    "rephrase": {
        "en-IN": "Sorry, I did not understand that. Could you say it another way?",
        "hi-IN": "माफ़ कीजिए, मैं समझ नहीं पाया। क्या आप दूसरे तरीके से कह सकते हैं?",
        "kn-IN": "ಕ್ಷಮಿಸಿ, ನನಗೆ ಅರ್ಥವಾಗಲಿಲ್ಲ. ಬೇರೆ ರೀತಿಯಲ್ಲಿ ಹೇಳಬಹುದೇ?",
        "ta-IN": "மன்னிக்கவும், புரியவில்லை. வேறு விதமாகச் சொல்ல முடியுமா?",
    },
    "cancelled": {
        "en-IN": "Stopped. {detail}",
        "hi-IN": "रोक दिया। {detail}",
        "kn-IN": "ನಿಲ್ಲಿಸಲಾಗಿದೆ. {detail}",
        "ta-IN": "நிறுத்தப்பட்டது. {detail}",
    },
}

FIELD_LABELS: dict[str, dict[str, str]] = {
    "full_name": {"en-IN": "Applicant name", "hi-IN": "आवेदक का नाम", "kn-IN": "ಅರ್ಜಿದಾರರ ಹೆಸರು", "ta-IN": "விண்ணப்பதாரர் பெயர்"},
    "state": {"en-IN": "State", "hi-IN": "राज्य", "kn-IN": "ರಾಜ್ಯ", "ta-IN": "மாநிலம்"},
    "district": {"en-IN": "District", "hi-IN": "जिला", "kn-IN": "ಜಿಲ್ಲೆ", "ta-IN": "மாவட்டம்"},
    "village": {"en-IN": "Village", "hi-IN": "गाँव", "kn-IN": "ಗ್ರಾಮ", "ta-IN": "கிராமம்"},
    "land_area_acres": {"en-IN": "Land (acres)", "hi-IN": "जमीन (एकड़)", "kn-IN": "ಜಮೀನು (ಎಕರೆ)", "ta-IN": "நிலம் (ஏக்கர்)"},
    "ownership": {"en-IN": "Ownership", "hi-IN": "स्वामित्व", "kn-IN": "ಮಾಲೀಕತ್ವ", "ta-IN": "உரிமை"},
    "bank_account_linked": {"en-IN": "Bank account", "hi-IN": "बैंक खाता", "kn-IN": "ಬ್ಯಾಂಕ್ ಖಾತೆ", "ta-IN": "வங்கிக் கணக்கு"},
    "mobile": {"en-IN": "Mobile (demo)", "hi-IN": "मोबाइल (डेमो)", "kn-IN": "ಮೊಬೈಲ್ (ಡೆಮೊ)", "ta-IN": "மொபைல் (டெமோ)"},
    "department": {"en-IN": "Department", "hi-IN": "विभाग", "kn-IN": "ವಿಭಾಗ", "ta-IN": "பிரிவு"},
    "location": {"en-IN": "Clinic", "hi-IN": "क्लिनिक", "kn-IN": "ಕ್ಲಿನಿಕ್", "ta-IN": "மருத்துவமனை"},
    "appointment_date": {"en-IN": "Date", "hi-IN": "तारीख", "kn-IN": "ದಿನಾಂಕ", "ta-IN": "தேதி"},
    "time_preference": {"en-IN": "Time of day", "hi-IN": "समय", "kn-IN": "ಸಮಯ", "ta-IN": "நேரம்"},
    "slot_time": {"en-IN": "Time slot", "hi-IN": "समय स्लॉट", "kn-IN": "ಸಮಯದ ಸ್ಲಾಟ್", "ta-IN": "நேர இடம்"},
    "doctor": {"en-IN": "Doctor", "hi-IN": "डॉक्टर", "kn-IN": "ವೈದ್ಯರು", "ta-IN": "மருத்துவர்"},
    "patient_name": {"en-IN": "Patient name", "hi-IN": "मरीज़ का नाम", "kn-IN": "ರೋಗಿಯ ಹೆಸರು", "ta-IN": "நோயாளி பெயர்"},
    "booking_reference": {"en-IN": "Booking reference", "hi-IN": "बुकिंग संदर्भ", "kn-IN": "ಬುಕಿಂಗ್ ಉಲ್ಲೇಖ", "ta-IN": "முன்பதிவு குறிப்பு"},
}

VALUE_LABELS: dict[str, dict[str, str]] = {
    "karnataka": {"en-IN": "Karnataka", "hi-IN": "कर्नाटक", "kn-IN": "ಕರ್ನಾಟಕ", "ta-IN": "கர்நாடகா"},
    "uttar_pradesh": {"en-IN": "Uttar Pradesh", "hi-IN": "उत्तर प्रदेश", "kn-IN": "ಉತ್ತರ ಪ್ರದೇಶ", "ta-IN": "உத்தரப் பிரதேசம்"},
    "tamil_nadu": {"en-IN": "Tamil Nadu", "hi-IN": "तमिलनाडु", "kn-IN": "ತಮಿಳುನಾಡು", "ta-IN": "தமிழ்நாடு"},
    "maharashtra": {"en-IN": "Maharashtra", "hi-IN": "महाराष्ट्र", "kn-IN": "ಮಹಾರಾಷ್ಟ್ರ", "ta-IN": "மகாராஷ்டிரா"},
    "bengaluru_urban": {"en-IN": "Bengaluru Urban", "hi-IN": "बेंगलुरु शहरी", "kn-IN": "ಬೆಂಗಳೂರು ನಗರ", "ta-IN": "பெங்களூரு நகர்ப்புறம்"},
    "bengaluru_rural": {"en-IN": "Bengaluru Rural", "hi-IN": "बेंगलुरु ग्रामीण", "kn-IN": "ಬೆಂಗಳೂರು ಗ್ರಾಮಾಂತರ", "ta-IN": "பெங்களூரு ஊரகம்"},
    "mysuru": {"en-IN": "Mysuru", "hi-IN": "मैसूरु", "kn-IN": "ಮೈಸೂರು", "ta-IN": "மைசூரு"},
    "belagavi": {"en-IN": "Belagavi", "hi-IN": "बेलगावी", "kn-IN": "ಬೆಳಗಾವಿ", "ta-IN": "பெலகாவி"},
    "lucknow": {"en-IN": "Lucknow", "hi-IN": "लखनऊ", "kn-IN": "ಲಕ್ನೋ", "ta-IN": "லக்னோ"},
    "varanasi": {"en-IN": "Varanasi", "hi-IN": "वाराणसी", "kn-IN": "ವಾರಾಣಸಿ", "ta-IN": "வாரணாசி"},
    "kanpur_nagar": {"en-IN": "Kanpur Nagar", "hi-IN": "कानपुर नगर", "kn-IN": "ಕಾನ್ಪುರ ನಗರ", "ta-IN": "கான்பூர் நகர்"},
    "kanpur_dehat": {"en-IN": "Kanpur Dehat", "hi-IN": "कानपुर देहात", "kn-IN": "ಕಾನ್ಪುರ ದೇಹಾತ್", "ta-IN": "கான்பூர் தேஹாத்"},
    "chennai": {"en-IN": "Chennai", "hi-IN": "चेन्नई", "kn-IN": "ಚೆನ್ನೈ", "ta-IN": "சென்னை"},
    "coimbatore": {"en-IN": "Coimbatore", "hi-IN": "कोयंबटूर", "kn-IN": "ಕೊಯಮತ್ತೂರು", "ta-IN": "கோயம்புத்தூர்"},
    "madurai": {"en-IN": "Madurai", "hi-IN": "मदुरै", "kn-IN": "ಮಧುರೈ", "ta-IN": "மதுரை"},
    "pune": {"en-IN": "Pune", "hi-IN": "पुणे", "kn-IN": "ಪುಣೆ", "ta-IN": "புனே"},
    "nashik": {"en-IN": "Nashik", "hi-IN": "नासिक", "kn-IN": "ನಾಸಿಕ್", "ta-IN": "நாசிக்"},
    "owner": {"en-IN": "Own name", "hi-IN": "अपने नाम पर", "kn-IN": "ಸ್ವಂತ ಹೆಸರಿನಲ್ಲಿ", "ta-IN": "சொந்தப் பெயரில்"},
    "tenant": {"en-IN": "Tenant", "hi-IN": "किरायेदार", "kn-IN": "ಗೇಣಿದಾರ", "ta-IN": "குத்தகைதாரர்"},
    "yes": {"en-IN": "Yes", "hi-IN": "हाँ", "kn-IN": "ಹೌದು", "ta-IN": "ஆம்"},
    "no": {"en-IN": "No", "hi-IN": "नहीं", "kn-IN": "ಇಲ್ಲ", "ta-IN": "இல்லை"},
    "general_medicine": {"en-IN": "General medicine", "hi-IN": "सामान्य चिकित्सा", "kn-IN": "ಸಾಮಾನ್ಯ ವೈದ್ಯಕೀಯ", "ta-IN": "பொது மருத்துவம்"},
    "pediatrics": {"en-IN": "Children's doctor", "hi-IN": "बच्चों के डॉक्टर", "kn-IN": "ಮಕ್ಕಳ ವೈದ್ಯರು", "ta-IN": "குழந்தை மருத்துவம்"},
    "orthopedics": {"en-IN": "Bones and joints", "hi-IN": "हड्डी रोग", "kn-IN": "ಮೂಳೆ ಚಿಕಿತ್ಸೆ", "ta-IN": "எலும்பு மருத்துவம்"},
    "ent": {"en-IN": "Ear, nose, throat", "hi-IN": "कान-नाक-गला", "kn-IN": "ಕಿವಿ-ಮೂಗು-ಗಂಟಲು", "ta-IN": "காது-மூக்கு-தொண்டை"},
    "bengaluru": {"en-IN": "Bengaluru", "hi-IN": "बेंगलुरु", "kn-IN": "ಬೆಂಗಳೂರು", "ta-IN": "பெங்களூரு"},
    "morning": {"en-IN": "morning", "hi-IN": "सुबह", "kn-IN": "ಬೆಳಿಗ್ಗೆ", "ta-IN": "காலை"},
    "afternoon": {"en-IN": "afternoon", "hi-IN": "दोपहर", "kn-IN": "ಮಧ್ಯಾಹ್ನ", "ta-IN": "மதியம்"},
    "evening": {"en-IN": "evening", "hi-IN": "शाम", "kn-IN": "ಸಂಜೆ", "ta-IN": "மாலை"},
    "any": {"en-IN": "any time", "hi-IN": "कोई भी समय", "kn-IN": "ಯಾವುದೇ ಸಮಯ", "ta-IN": "எந்த நேரமும்"},
}

PORTAL_NAMES = {
    "demo_scheme": {"en-IN": "demo scheme portal", "hi-IN": "डेमो योजना पोर्टल",
                    "kn-IN": "ಡೆಮೊ ಯೋಜನಾ ಪೋರ್ಟಲ್", "ta-IN": "டெமோ திட்ட போர்ட்டல்"},
    "demo_clinic_cancel": {"en-IN": "demo clinic portal", "hi-IN": "डेमो क्लिनिक पोर्टल",
                           "kn-IN": "ಡೆಮೊ ಕ್ಲಿನಿಕ್ ಪೋರ್ಟಲ್", "ta-IN": "டெமோ மருத்துவமனை போர்ட்டல்"},
    "demo_clinic": {"en-IN": "demo clinic portal", "hi-IN": "डेमो क्लिनिक पोर्टल",
                    "kn-IN": "ಡೆಮೊ ಕ್ಲಿನಿಕ್ ಪೋರ್ಟಲ್", "ta-IN": "டெமோ மருத்துவமனை போர்ட்டல்"},
}

MONTHS = {
    "hi-IN": ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"],
    "kn-IN": ["ಜನವರಿ", "ಫೆಬ್ರವರಿ", "ಮಾರ್ಚ್", "ಏಪ್ರಿಲ್", "ಮೇ", "ಜೂನ್", "ಜುಲೈ", "ಆಗಸ್ಟ್", "ಸೆಪ್ಟೆಂಬರ್", "ಅಕ್ಟೋಬರ್", "ನವೆಂಬರ್", "ಡಿಸೆಂಬರ್"],
    "ta-IN": ["ஜனவரி", "பிப்ரவரி", "மார்ச்", "ஏப்ரல்", "மே", "ஜூன்", "ஜூலை", "ஆகஸ்ட்", "செப்டம்பர்", "அக்டோபர்", "நவம்பர்", "டிசம்பர்"],
    "en-IN": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
}


def t(key: str, lang: str, **kw: str) -> str:
    table = M[key]
    text = table.get(lang) or table["en-IN"]
    return text.format(**kw) if kw else text


def label(field: str, lang: str) -> str:
    return FIELD_LABELS.get(field, {}).get(lang) or FIELD_LABELS.get(field, {}).get("en-IN") or field


def value_label(value: str, lang: str) -> str:
    v = VALUE_LABELS.get(value)
    return (v.get(lang) or v["en-IN"]) if v else value


def format_date(iso: str, lang: str) -> str:
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{d} {MONTHS.get(lang, MONTHS['en-IN'])[m - 1]}"
