import { motion } from "framer-motion";
import { Check, Clock } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import PillArt from "../components/PillArt.jsx";
import { CheckBurst } from "../components/ui.jsx";
import { Volume2 } from "lucide-react";
import { FOOD_LABEL, hasVoiceFor, speak, stopSpeaking, t } from "../i18n.js";
import { useApp } from "../store.jsx";

/* At dose time the app takes the whole screen: the pill picture, the Hindi
 * voice, and two buttons. Nothing else is on the page, because a 70 year old
 * holding a phone at 9 PM should not have to find anything.
 */
export default function ReminderTakeover({ slot, onClose }) {
  const { parentId, lang, showToast } = useApp();
  const [day, setDay] = useState(null);
  const [voice, setVoice] = useState(null);
  const [done, setDone] = useState(false);
  const [needsTap, setNeedsTap] = useState(false);
  const [noHindiVoice, setNoHindiVoice] = useState(false);
  const started = useRef(false);

  useEffect(() => {
    if (!parentId) return undefined;
    /* React invokes effects twice in development. Without this guard the
       reminder speaks over itself, which is what "double voice" was. */
    if (started.current) return undefined;
    started.current = true;

    api.today(parentId).then(setDay);
    api
      .voice(parentId, slot)
      .then(async (res) => {
        setVoice(res);
        const result = await speak(res.spoken, lang, res.url);
        /* A browser will not play audio until the person has tapped
           something. That is a rule, not a failure: ask for the tap. */
        setNeedsTap(Boolean(result.blocked));
        setNoHindiVoice(result.engine === "browser" && result.voiceAvailable === false);
      })
      .catch(() => setVoice(null));

    return () => stopSpeaking();
  }, [parentId, slot, lang]);

  const playNow = async () => {
    const result = await speak(voice?.spoken || "", lang, voice?.url);
    setNeedsTap(Boolean(result.blocked));
    setNoHindiVoice(result.engine === "browser" && result.voiceAvailable === false);
  };

  const slotData = day?.slots.find((s) => s.slot === slot);

  const take = async () => {
    stopSpeaking();
    const res = await api.markTaken(parentId, day.date, slot);
    setDone(true);
    if (navigator.vibrate) navigator.vibrate(30);
    speak(res.praise.spoken, lang);
    setTimeout(onClose, 1800);
  };

  const snooze = () => {
    stopSpeaking();
    showToast(lang === "hi" ? "10 मिनट बाद फिर याद दिलाएँगे" : "We will remind you in 10 minutes");
    onClose();
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="parent-scope fixed inset-0 z-40 flex flex-col bg-cream px-6 py-8"
      role="dialog"
      aria-modal="true"
      aria-label={t(lang, "reminderTitle")}
    >
      <div className="mx-auto flex w-full max-w-lg flex-1 flex-col items-center justify-center gap-6 text-center">
        {done ? (
          <>
            <CheckBurst />
            <p className="text-parent-xl text-ok">{t(lang, "doneToast")}</p>
          </>
        ) : (
          <>
            <p className="flex items-center gap-3 text-parent text-ink-soft">
              <Clock size={26} aria-hidden="true" />
              {t(lang, "reminderTitle")} · {slotData?.time || ""}
            </p>

            <div className="flex flex-wrap items-center justify-center gap-4">
              {(slotData?.doses || []).map((dose) => (
                <div key={dose.medId} className="flex flex-col items-center gap-2">
                  <PillArt brand={dose.brand} form={dose.form} photoUrl={dose.photoUrl} size={128} />
                  <p className="text-parent font-bold">{dose.brand}</p>
                  <p className="text-ink-soft">{FOOD_LABEL[dose.food]?.[lang]}</p>
                </div>
              ))}
            </div>

            {voice?.caption && (
              <p className="text-parent font-semibold text-teal">{voice.caption}</p>
            )}

            <button
              type="button"
              onClick={playNow}
              className={`btn min-h-touch w-full px-6 py-5 text-parent ${
                needsTap ? "btn-primary animate-pulse" : "btn-ghost"
              }`}
            >
              <Volume2 size={28} aria-hidden="true" />
              {needsTap
                ? lang === "hi"
                  ? "सुनने के लिए दबाएँ"
                  : "Tap to hear it"
                : t(lang, "listen")}
            </button>

            {noHindiVoice && lang === "hi" && (
              <p className="text-sm text-ink-faint">
                इस फ़ोन में हिन्दी आवाज़ नहीं है — ऊपर लिखा हुआ पढ़ें।
                <br />
                This phone has no Hindi voice installed; the line above is the same message.
              </p>
            )}
          </>
        )}
      </div>

      {!done && (
        <div className="mx-auto w-full max-w-lg space-y-3">
          <motion.button type="button" onClick={take} className="btn-parent" whileTap={{ scale: 0.97 }}>
            <Check size={34} strokeWidth={3} aria-hidden="true" />
            {t(lang, "taken")}
          </motion.button>
          <button type="button" onClick={snooze} className="btn-ghost min-h-touch w-full px-6 py-5 text-parent">
            {t(lang, "later")}
          </button>
        </div>
      )}
    </motion.div>
  );
}
