import React, { useState, useEffect } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { SunriseIcon, SunHighIcon, MoonStarsIcon, CheckIcon } from "./icons/Icons";
import PillSwatch from "./PillSwatch";
import { SLOT_THEME, FOOD_LABEL, COLORS } from "../constants/theme";

const ICONS = { Morning: SunriseIcon, Afternoon: SunHighIcon, Night: MoonStarsIcon };

export default function SlotCard({ slot, isExpanded, isNext, nextLabel, lang, onExpand, onTaken, onUndo }) {
  const theme = SLOT_THEME[slot.time_of_day];
  const Icon = ICONS[slot.time_of_day];
  const reduceMotion = useReducedMotion();
  const [phase, setPhase] = useState("idle"); // idle | confirming | done

  const isTaken = slot.status === "TAKEN";
  const goli = slot.medicines.reduce((n, m) => n + m.count, 0);

  // If the store says this slot is pending again (undo, or a fresh day),
  // the button must return to its resting state.
  useEffect(() => {
    if (!isTaken) setPhase("idle");
  }, [isTaken]);

  function handleTaken() {
    if (phase !== "idle") return;
    setPhase("confirming");
    if (typeof navigator !== "undefined" && navigator.vibrate) navigator.vibrate(100);
    window.setTimeout(() => {
      setPhase("done");
      onTaken?.(slot.id);
    }, 560);
  }

  const baseShadow = `0 2px 10px ${theme.shadow}`;
  const breathe = isNext && !isExpanded && !reduceMotion;

  return (
    <motion.section
      layout
      className="w-full rounded-[20px] overflow-hidden"
      style={{ background: isExpanded ? theme.bgExpanded : theme.bg, opacity: isTaken ? 0.72 : 1 }}
      animate={
        breathe
          ? { boxShadow: [baseShadow, `${baseShadow}, 0 0 0 4px ${theme.ring}`, baseShadow] }
          : { boxShadow: isExpanded ? `0 10px 28px ${theme.shadow}` : baseShadow }
      }
      transition={
        breathe
          ? { boxShadow: { duration: 2.8, repeat: Infinity, ease: "easeInOut" }, layout: { duration: 0.42, ease: [0.22, 1, 0.36, 1] } }
          : { layout: { duration: 0.42, ease: [0.22, 1, 0.36, 1] } }
      }
      aria-label={`${slot.time_of_day}, ${theme.hindi}`}
    >
      <button
        type="button"
        onClick={() => onExpand(slot.id)}
        className="w-full flex items-center gap-[14px] text-left p-[18px] min-h-[76px]"
        aria-expanded={isExpanded}
      >
        <span className="w-14 h-14 rounded-2xl shrink-0 flex items-center justify-center bg-white/70">
          <Icon color={theme.accent} size={34} />
        </span>

        <span className="flex-1 min-w-0">
          <span className="block text-[24px] font-bold leading-tight" style={{ color: COLORS.ink }}>
            {slot.time_of_day}
            <span className="ml-2 text-[17px] font-medium" style={{ color: theme.accent }}>
              {theme.hindi}
            </span>
          </span>
          <span className="block text-[16px] mt-[3px]" style={{ color: COLORS.inkMuted }}>
            {isTaken ? `${slot.takenAt} baje li` : `${goli} goli`}
          </span>
        </span>

        {isTaken ? (
          <span
            className="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
            style={{ background: COLORS.success, boxShadow: "0 2px 8px rgba(22,163,74,.35)" }}
          >
            <CheckIcon size={22} />
          </span>
        ) : (
          <span
            className="text-[16px] font-semibold rounded-full px-3 py-[6px] shrink-0 bg-white/80"
            style={{ color: theme.accent }}
          >
            {slot.time}
          </span>
        )}
      </button>

      <AnimatePresence initial={false}>
        {isExpanded && !isTaken && (
          <motion.div
            key="body"
            initial={reduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
            animate={reduceMotion ? { opacity: 1 } : { height: "auto", opacity: 1 }}
            exit={reduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
            transition={{ duration: 0.38, ease: [0.22, 1, 0.36, 1] }}
            className="px-[18px] pb-5"
          >
            <ul className="flex flex-col gap-[10px] mb-[18px] list-none p-0 m-0">
              {slot.medicines.map((med, i) => (
                <li key={i} className="flex items-center gap-[14px] bg-white/80 rounded-2xl px-4 py-[14px]">
                  <PillSwatch colorHint={med.colorHint} photoUrl={med.photoUrl} />
                  <div className="min-w-0">
                    <p className="text-[21px] font-semibold m-0 truncate" style={{ color: COLORS.ink }}>
                      {med.brand}
                    </p>
                    <p className="text-[16px] m-0" style={{ color: COLORS.inkMuted }}>
                      {FOOD_LABEL[med.instructions]?.[lang === "hi" ? "hi" : "hi"] ?? ""}
                    </p>
                  </div>
                  <span
                    className="ml-auto text-[17px] font-semibold rounded-xl px-3 py-[6px] shrink-0 bg-white/90"
                    style={{ color: theme.accent }}
                  >
                    {med.count} goli
                  </span>
                </li>
              ))}
            </ul>

            {phase === "done" ? (
              <div className="flex flex-col items-center gap-[3px] pt-1" aria-live="polite">
                <p className="text-[24px] font-bold m-0" style={{ color: COLORS.success }}>
                  Shabash!
                </p>
                <p className="text-[17px] m-0" style={{ color: COLORS.inkMuted }}>
                  {nextLabel ? `Agli goli ${nextLabel}.` : "Aaj ki saari dawai ho gayi."}
                </p>
                <button
                  type="button"
                  onClick={() => { setPhase("idle"); onUndo?.(slot.id); }}
                  className="mt-[10px] w-full min-h-[52px] rounded-[14px] text-[18px] font-semibold border-2 bg-transparent"
                  style={{ borderColor: "rgba(41,37,36,0.18)", color: COLORS.inkMuted }}
                >
                  Galti se daba diya? Wapas karo
                </button>
              </div>
            ) : (
              <motion.button
                type="button"
                onClick={handleTaken}
                disabled={phase === "confirming"}
                className="relative w-full min-h-[72px] rounded-[18px] text-white text-[26px] font-bold flex items-center justify-center overflow-hidden border-0"
                style={{
                  background:
                    phase === "confirming"
                      ? `linear-gradient(180deg,#18A55C 0%,${COLORS.success} 100%)`
                      : `linear-gradient(180deg,${COLORS.teal} 0%,${COLORS.tealDeep} 100%)`,
                  boxShadow: "0 8px 20px rgba(15,118,110,.32)",
                }}
                whileTap={reduceMotion ? {} : { scale: 0.985, y: 2 }}
              >
                <AnimatePresence>
                  {phase === "confirming" && !reduceMotion && (
                    <motion.span
                      className="absolute inset-0 rounded-[18px]"
                      initial={{ boxShadow: `0 0 0 0px ${theme.ring}`, opacity: 1 }}
                      animate={{ boxShadow: `0 0 0 26px ${theme.ring}`, opacity: 0 }}
                      transition={{ duration: 0.65, ease: "easeOut" }}
                    />
                  )}
                </AnimatePresence>

                <AnimatePresence mode="wait" initial={false}>
                  {phase === "idle" ? (
                    <motion.span key="label" exit={{ opacity: 0, scale: 0.7 }}>
                      Le liya
                    </motion.span>
                  ) : (
                    <motion.span
                      key="check"
                      initial={{ scale: 0.3, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      transition={{ type: "spring", stiffness: 420, damping: 15 }}
                    >
                      <CheckIcon size={32} />
                    </motion.span>
                  )}
                </AnimatePresence>
              </motion.button>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.section>
  );
}
