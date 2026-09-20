import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, Check, Info, Languages, Volume2 } from "lucide-react";
import { useEffect, useState } from "react";
import { SLOT_LABEL, speak, t } from "../i18n.js";
import { useApp } from "../store.jsx";

export function LangToggle({ className = "" }) {
  const { lang, toggleLang } = useApp();
  return (
    <button
      type="button"
      onClick={toggleLang}
      aria-label={lang === "hi" ? "Switch to English" : "हिन्दी में बदलें"}
      className={`btn-ghost min-h-[48px] shrink-0 px-4 py-2 text-[16px] ${className}`}
    >
      <Languages size={20} aria-hidden="true" />
      {t(lang, "language")}
    </button>
  );
}

export function SpeakerButton({ text, audioUrl, label, big = false }) {
  const { lang } = useApp();
  const [playing, setPlaying] = useState(false);

  const onPlay = () => {
    setPlaying(true);
    speak(text, lang, audioUrl);
    setTimeout(() => setPlaying(false), 2500);
  };

  return (
    <button
      type="button"
      onClick={onPlay}
      aria-label={label || t(lang, "listen")}
      className={`btn-ghost ${big ? "min-h-touch px-6 py-4 text-parent" : "min-h-[48px] px-4 py-2"}`}
    >
      <motion.span
        animate={playing ? { scale: [1, 1.18, 1] } : { scale: 1 }}
        transition={{ duration: 0.8, repeat: playing ? Infinity : 0 }}
        className="inline-flex"
      >
        <Volume2 size={big ? 28 : 20} aria-hidden="true" />
      </motion.span>
      {t(lang, "listen")}
    </button>
  );
}

export function SlotBadge({ slot, className = "" }) {
  const { lang } = useApp();
  const styles = {
    MORNING: "bg-slot-morning text-slot-morningInk",
    AFTERNOON: "bg-slot-afternoon text-slot-afternoonInk",
    NIGHT: "bg-slot-night text-slot-nightInk",
  };
  const icon = { MORNING: "☀", AFTERNOON: "◐", NIGHT: "☾" }[slot] || "•";
  return (
    <span className={`chip ${styles[slot] || "bg-black/5"} ${className}`}>
      <span aria-hidden="true">{icon}</span>
      {SLOT_LABEL[slot]?.[lang] || slot}
    </span>
  );
}

/* Amber, never red: a duplicate is something to ask about, not an emergency. */
export function DuplicateBanner({ duplicates = [], compact = false }) {
  const { lang } = useApp();
  if (!duplicates.length) return null;

  return (
    <div className="space-y-3">
      {duplicates.map((dup) => (
        <motion.div
          key={dup.salt}
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
          className="rounded-2xl border border-warn/30 bg-warn/[.08] p-4"
          role="status"
        >
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 shrink-0 text-warn" size={compact ? 20 : 24} aria-hidden="true" />
            <div className="min-w-0">
              <p className="font-bold text-ink">{t(lang, "duplicateTitle")}</p>
              <p className="mt-1 text-ink-soft">{lang === "hi" ? dup.messageHi : dup.message}</p>
              {!compact && <SaltOverlap dup={dup} />}
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

/* The micro-interaction: two strips slide together, the shared salt sits in
   the overlap. It is the thing that lands in the first 30 seconds of the
   demo video, so it gets real motion. */
function SaltOverlap({ dup }) {
  /* When the overlap crosses two prescriptions, the left strip is the one
     already on the list and the right is the one just scanned. Naming which
     is which is the whole point: the caregiver needs to know the new sheet
     is the problem, not guess. */
  const cross = dup.existingBrands?.length > 0 && dup.newBrands?.length > 0;
  const left = cross ? dup.existingBrands[0] : dup.brands[0];
  const right = cross ? dup.newBrands[0] : dup.brands[1];

  return (
    <div className="mt-4 flex items-center justify-center gap-0 py-2" aria-hidden="true">
      <motion.div
        initial={{ x: -28, opacity: 0 }}
        animate={{ x: 12, opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.2, ease: [0.22, 0.61, 0.36, 1] }}
        className="rounded-xl bg-white px-3 py-2 text-center shadow-card"
      >
        <span className="block text-sm font-semibold">{left}</span>
        {cross && <span className="block text-[11px] text-ink-faint">already taking</span>}
      </motion.div>
      <motion.div
        initial={{ scale: 0.6, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.75 }}
        className="z-10 rounded-full bg-warn px-3 py-2 text-sm font-bold text-white shadow-lift"
      >
        {dup.salt}
      </motion.div>
      <motion.div
        initial={{ x: 28, opacity: 0 }}
        animate={{ x: -12, opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.2, ease: [0.22, 0.61, 0.36, 1] }}
        className="rounded-xl bg-white px-3 py-2 text-center shadow-card"
      >
        <span className="block text-sm font-semibold">{right}</span>
        {cross && <span className="block text-[11px] text-ink-faint">just scanned</span>}
      </motion.div>
    </div>
  );
}

export function Toast() {
  const { toast, clearToast } = useApp();

  useEffect(() => {
    if (!toast) return undefined;
    const id = setTimeout(clearToast, 5000); // five second Undo window
    return () => clearTimeout(id);
  }, [toast, clearToast]);

  return (
    <AnimatePresence>
      {toast && (
        <motion.div
          initial={{ y: 60, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 60, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-x-4 bottom-6 z-50 mx-auto flex max-w-md items-center
                     justify-between gap-4 rounded-2xl bg-ink px-5 py-4 text-white shadow-lift"
          role="status"
        >
          <span className="font-semibold">{toast.message}</span>
          {toast.action && (
            <button
              type="button"
              onClick={() => {
                toast.action.onClick();
                clearToast();
              }}
              className="shrink-0 rounded-xl bg-white/15 px-4 py-2 font-bold"
            >
              {toast.action.label}
            </button>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function AdherenceRing({ value = 0, size = 128, label }) {
  const stroke = 12;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const colour = value >= 80 ? "#16A34A" : value >= 50 ? "#D97706" : "#DC2626";

  return (
    <div className="flex items-center gap-4">
      <svg width={size} height={size} role="img" aria-label={`${value} percent adherence`}>
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#E9E3D9" strokeWidth={stroke} />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={colour}
          strokeWidth={stroke}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference * (1 - value / 100) }}
          transition={{ duration: 1.1, ease: [0.22, 0.61, 0.36, 1] }}
        />
        <text
          x="50%"
          y="50%"
          textAnchor="middle"
          dominantBaseline="central"
          className="fill-ink"
          style={{ fontSize: size / 4, fontWeight: 800 }}
        >
          {value}%
        </text>
      </svg>
      {label && <div className="text-ink-soft">{label}</div>}
    </div>
  );
}

export function CountUp({ value = 0, prefix = "", duration = 1200 }) {
  const [shown, setShown] = useState(0);

  useEffect(() => {
    const start = performance.now();
    let frame;
    const tick = (now) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setShown(Math.round(value * eased));
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value, duration]);

  return (
    <span>
      {prefix}
      {shown.toLocaleString("en-IN")}
    </span>
  );
}

export function Empty({ icon: Icon = Info, title, body, action }) {
  return (
    <div className="card flex flex-col items-center gap-3 p-8 text-center">
      <Icon className="text-ink-faint" size={32} aria-hidden="true" />
      <p className="text-lg font-bold">{title}</p>
      {body && <p className="text-ink-soft">{body}</p>}
      {action}
    </div>
  );
}

export function Spinner({ label = "Loading" }) {
  return (
    <div className="flex items-center justify-center gap-3 p-8 text-ink-soft" role="status">
      <motion.span
        animate={{ rotate: 360 }}
        transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
        className="block h-6 w-6 rounded-full border-[3px] border-teal/25 border-t-teal"
      />
      {label}
    </div>
  );
}

export function CheckBurst() {
  return (
    <motion.span
      initial={{ scale: 0, rotate: -30 }}
      animate={{ scale: 1, rotate: 0 }}
      transition={{ type: "spring", stiffness: 420, damping: 16 }}
      className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-ok text-white"
    >
      <Check size={36} strokeWidth={3} aria-hidden="true" />
    </motion.span>
  );
}

export function Disclaimer({ className = "" }) {
  const { lang } = useApp();
  return (
    <p className={`text-sm text-ink-faint ${className}`}>
      {lang === "hi"
        ? "DoseWise कोई दवा नहीं बदलता। यह सिर्फ़ ध्यान दिलाता है, फ़ैसला डॉक्टर का है।"
        : "DoseWise never changes a prescription. It flags things for a doctor or pharmacist to confirm."}
    </p>
  );
}
