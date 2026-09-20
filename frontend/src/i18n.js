/* Hindi and English strings. Every parent-facing string exists in both, and
 * the toggle sits on every screen. Hindi is Devanagari for reading and has a
 * Roman twin where a caregiver might need to read it aloud.
 */
export const STRINGS = {
  hi: {
    appName: "DoseWise",
    tagline: "कोई गोली गलती नहीं",
    namaste: (name) => (name ? `नमस्ते ${name} जी` : "नमस्ते"),
    today: "आज की दवा",
    morning: "सुबह",
    afternoon: "दोपहर",
    night: "रात",
    taken: "ले लिया",
    takenShort: "लिया",
    later: "10 मिनट बाद",
    pills: (n) => `${n} गोली`,
    beforeFood: "खाने से पहले",
    afterFood: "खाने के बाद",
    anyFood: "कभी भी",
    listen: "सुनें",
    allDone: "आज की सारी दवा हो गई",
    nothingToday: "आज कोई दवा नहीं है",
    undo: "वापस लें",
    undone: "वापस ले लिया",
    doneToast: "शाबाश!",
    duplicateTitle: "एक ही दवा दो नाम से",
    askDoctor: "डॉक्टर से पूछें",
    missed: "छूट गई",
    pending: "बाकी है",
    language: "English",
    parentMode: "माता-पिता",
    caregiverMode: "परिवार",
    reminderTitle: "दवा का समय",
  },
  en: {
    appName: "DoseWise",
    tagline: "No pill is a mistake",
    namaste: (name) => (name ? `Hello ${name}` : "Hello"),
    today: "Today's medicine",
    morning: "Morning",
    afternoon: "Afternoon",
    night: "Night",
    taken: "Taken",
    takenShort: "Taken",
    later: "In 10 minutes",
    pills: (n) => `${n} ${n === 1 ? "pill" : "pills"}`,
    beforeFood: "Before food",
    afterFood: "After food",
    anyFood: "Any time",
    listen: "Listen",
    allDone: "All of today's medicine is done",
    nothingToday: "No medicine scheduled today",
    undo: "Undo",
    undone: "Undone",
    doneToast: "Well done!",
    duplicateTitle: "Same medicine, two names",
    askDoctor: "Ask your doctor",
    missed: "Missed",
    pending: "Pending",
    language: "हिन्दी",
    parentMode: "Parent",
    caregiverMode: "Family",
    reminderTitle: "Medicine time",
  },
};

export const SLOT_LABEL = {
  MORNING: { hi: "सुबह", en: "Morning" },
  AFTERNOON: { hi: "दोपहर", en: "Afternoon" },
  NIGHT: { hi: "रात", en: "Night" },
};

export const FOOD_LABEL = {
  before: { hi: "खाने से पहले", en: "Before food" },
  after: { hi: "खाने के बाद", en: "After food" },
  any: { hi: "कभी भी", en: "Any time" },
};

export function t(lang, key, ...args) {
  const table = STRINGS[lang] || STRINGS.hi;
  const value = table[key] ?? STRINGS.en[key] ?? key;
  return typeof value === "function" ? value(...args) : value;
}

/* One voice at a time, and never a silent failure.
 *
 * Two things went wrong before this: every call made a fresh Audio with no way
 * to stop the last one (React re-invokes effects in development, so the
 * reminder spoke over itself), and a blocked autoplay fell back to browser
 * speech synthesis that had no Hindi voice installed, which reads Devanagari
 * aloud in an English voice. Both are now visible to the caller instead of
 * happening quietly.
 */
let currentAudio = null;

export function stopSpeaking() {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio.currentTime = 0;
    currentAudio = null;
  }
  if (typeof window !== "undefined" && window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
}

/** Does this browser actually have a voice for the language? */
export function hasVoiceFor(lang = "hi") {
  if (typeof window === "undefined" || !window.speechSynthesis) return false;
  const want = lang === "hi" ? "hi" : "en";
  return window.speechSynthesis.getVoices().some((v) => (v.lang || "").toLowerCase().startsWith(want));
}

/** Returns {engine, ok, blocked, voiceAvailable} so the UI can react. */
export async function speak(text, lang = "hi", audioUrl = null) {
  stopSpeaking();

  if (audioUrl) {
    const audio = new Audio(audioUrl);
    currentAudio = audio;
    try {
      await audio.play();
      return { ok: true, engine: "polly", blocked: false };
    } catch {
      /* Autoplay policy: a browser will not speak until the person has tapped
         something. Not an error, but the UI must ask for that tap. */
      currentAudio = null;
      return { ok: false, engine: "polly", blocked: true, audioUrl };
    }
  }

  return speakLocally(text, lang);
}

function speakLocally(text, lang) {
  if (typeof window === "undefined" || !window.speechSynthesis) {
    return { ok: false, engine: "none", blocked: false, voiceAvailable: false };
  }
  const synth = window.speechSynthesis;
  synth.cancel();

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang === "hi" ? "hi-IN" : "en-IN";
  const match = synth
    .getVoices()
    .find((v) => (v.lang || "").toLowerCase().startsWith(lang === "hi" ? "hi" : "en"));
  if (match) utterance.voice = match;
  utterance.rate = 0.9;
  synth.speak(utterance);

  return { ok: true, engine: "browser", blocked: false, voiceAvailable: Boolean(match) };
}
