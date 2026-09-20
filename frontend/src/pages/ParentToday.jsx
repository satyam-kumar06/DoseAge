import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router";
import { motion, AnimatePresence } from "framer-motion";
import Shell from "../components/Shell";
import BottomNav from "../components/BottomNav";
import SlotCard from "../components/SlotCard";
import TodayRing from "../components/TodayRing";
import EmptyState from "../components/EmptyState";
import { SpeakerIcon, CheckIcon, CameraIcon } from "../components/icons/Icons";
import { useDoseWise } from "../store/DoseWiseStore";
import { COLORS, SLOT_THEME } from "../constants/theme";
import { dayLabel } from "../lib/format";

export default function ParentToday() {
  const navigate = useNavigate();
  const {
    lang, setLang, slots, hasSchedule, nextSlot, doneCount,
    markSlotTaken, undoSlotTaken,
  } = useDoseWise();

  const [expandedId, setExpandedId] = useState(null);
  const [playingVoice, setPlayingVoice] = useState(false);

  // Keep the next pending dose open, without fighting a manual tap.
  useEffect(() => {
    setExpandedId((cur) => (cur === null ? nextSlot?.id ?? null : cur));
  }, [nextSlot]);

  function handleTaken(id) {
    markSlotTaken(id);
    // Leave the Shabash moment and its undo on screen before advancing.
    window.setTimeout(() => setExpandedId(null), 4200);
  }

  function handlePlayVoice() {
    // TODO(B): GET /parents/{id}/voice?slot=<next slot>, play the returned mp3.
    setPlayingVoice(true);
    window.setTimeout(() => setPlayingVoice(false), 1300);
  }

  const greeting = lang === "hi" ? "नमस्ते, मम्मी जी" : "Namaste, Mummy ji";

  return (
    <Shell bottomNav>
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-[32px] font-bold leading-tight m-0 tracking-tight" style={{ color: COLORS.ink }}>
            {greeting}
          </h1>
          <p className="text-[16px] mt-1 m-0" style={{ color: COLORS.inkMuted }}>{dayLabel(lang)}</p>
        </div>

        <div className="flex items-center gap-[10px] shrink-0">
          <button
            type="button"
            onClick={() => setLang(lang === "en" ? "hi" : "en")}
            className="h-14 px-4 rounded-full text-[16px] font-semibold border"
            style={{ background: COLORS.surface, borderColor: COLORS.line, color: COLORS.teal }}
          >
            {lang === "en" ? "हिं" : "EN"}
          </button>

          <motion.button
            type="button"
            onClick={handlePlayVoice}
            aria-label="Sun kar suniye"
            className="relative w-14 h-14 rounded-full flex items-center justify-center border"
            style={{ background: COLORS.surface, borderColor: COLORS.line }}
            whileTap={{ scale: 0.93 }}
          >
            {playingVoice && (
              <motion.span
                className="absolute inset-0 rounded-full"
                style={{ border: `2px solid ${COLORS.teal}` }}
                initial={{ scale: 1, opacity: 0.55 }}
                animate={{ scale: 1.65, opacity: 0 }}
                transition={{ duration: 1, repeat: Infinity, ease: "easeOut" }}
              />
            )}
            <SpeakerIcon />
          </motion.button>
        </div>
      </header>

      {!hasSchedule ? (
        <EmptyState
          icon={<CameraIcon color={COLORS.teal} size={32} />}
          title="Abhi koi dawai nahi"
          body="Pehli prescription scan kijiye. Uske baad har din ka schedule yahan dikhega."
          actionLabel="Prescription scan karein"
          onAction={() => navigate("/scan")}
        />
      ) : (
        <>
          <TodayRing done={doneCount} total={slots.length} nextSlot={nextSlot} />

          <div className="flex flex-col gap-[14px]">
            {slots.map((slot) => (
              <SlotCard
                key={slot.id}
                slot={slot}
                lang={lang}
                isExpanded={expandedId === slot.id}
                isNext={nextSlot?.id === slot.id}
                nextLabel={
                  nextSlot && nextSlot.id !== slot.id
                    ? `${SLOT_THEME[nextSlot.time_of_day].hindi} ${nextSlot.time} baje`
                    : null
                }
                onExpand={(id) => setExpandedId((cur) => (cur === id ? null : id))}
                onTaken={handleTaken}
                onUndo={undoSlotTaken}
              />
            ))}
          </div>

          <AnimatePresence>
            {!nextSlot && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="flex flex-col items-center gap-2 rounded-[20px] px-5 py-[26px]"
                style={{ background: COLORS.surface, boxShadow: "0 6px 20px rgba(41,37,36,0.06)" }}
              >
                <span className="w-16 h-16 rounded-full flex items-center justify-center" style={{ background: "rgba(22,163,74,0.12)" }}>
                  <CheckIcon color={COLORS.success} size={34} />
                </span>
                <h3 className="text-[24px] font-bold m-0 text-center" style={{ color: COLORS.ink }}>
                  Aaj ki saari dawai ho gayi
                </h3>
                <p className="text-[17px] m-0 text-center" style={{ color: COLORS.inkMuted }}>
                  Bahut badhiya. Kal subah 8 baje phir milte hain.
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </>
      )}

      <BottomNav />
    </Shell>
  );
}
