import React from "react";
import { motion } from "framer-motion";
import { COLORS, SLOT_THEME } from "../constants/theme";

const R = 36;
const C = 2 * Math.PI * R;

// Hero of the parent screen: where today stands, and what is next.
export default function TodayRing({ done, total, nextSlot }) {
  const offset = total ? C - (C * done) / total : C;
  const theme = nextSlot ? SLOT_THEME[nextSlot.time_of_day] : null;
  const goli = nextSlot ? nextSlot.medicines.reduce((n, m) => n + m.count, 0) : 0;

  return (
    <div
      className="flex items-center gap-[18px] rounded-[20px] px-5 py-[18px]"
      style={{ background: COLORS.surface, boxShadow: "0 6px 20px rgba(41,37,36,0.06)" }}
    >
      <div className="relative w-[84px] h-[84px] shrink-0">
        <svg width="84" height="84" viewBox="0 0 84 84" style={{ transform: "rotate(-90deg)" }}>
          <circle cx="42" cy="42" r={R} fill="none" strokeWidth="9" stroke={COLORS.track} />
          <motion.circle
            cx="42" cy="42" r={R} fill="none" strokeWidth="9"
            stroke={COLORS.teal} strokeLinecap="round" strokeDasharray={C}
            initial={{ strokeDashoffset: C }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-[24px] font-bold leading-none" style={{ color: COLORS.ink }}>{done}/{total}</span>
          <span className="text-[13px]" style={{ color: COLORS.inkMuted }}>aaj</span>
        </div>
      </div>

      <div className="min-w-0">
        <h2 className="text-[22px] font-semibold m-0" style={{ color: COLORS.ink }}>
          {nextSlot ? "Agli goli" : "Sab ho gaya"}
        </h2>
        <p className="text-[17px] m-0" style={{ color: COLORS.inkMuted }}>
          {nextSlot ? (
            <>
              <strong className="font-semibold" style={{ color: COLORS.teal }}>
                {theme.hindi} {nextSlot.time}
              </strong>{" "}· {goli} goli
            </>
          ) : (
            <strong className="font-semibold" style={{ color: COLORS.teal }}>Aaj ki dawai poori</strong>
          )}
        </p>
      </div>
    </div>
  );
}
