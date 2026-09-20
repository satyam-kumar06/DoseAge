import React from "react";
import { motion } from "framer-motion";
import { AlertIcon } from "./icons/Icons";
import { COLORS } from "../constants/theme";

// The moment that wins the room. Two pills slide together and overlap, the
// shared salt fades in between them.
export default function DuplicateBanner({ alert }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className="rounded-[20px] p-[18px]"
      style={{ background: COLORS.warningBg, border: `2px solid ${COLORS.warning}` }}
      role="alert"
    >
      <div className="flex items-center gap-3 mb-3">
        <AlertIcon />
        <span className="text-[19px] font-bold" style={{ color: "#92400E" }}>
          Ek hi salt, do dawai
        </span>
      </div>

      <div className="flex items-center justify-center h-[70px] relative mb-3">
        <motion.span
          className="absolute rounded-[14px]"
          style={{ width: 54, height: 54, background: "#EFBE3F", boxShadow: "inset 0 -3px 0 rgba(0,0,0,.08)" }}
          initial={{ x: -70 }}
          animate={{ x: -22 }}
          transition={{ delay: 0.35, duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        />
        <motion.span
          className="absolute rounded-[14px]"
          style={{ width: 54, height: 54, background: "#F09A56", boxShadow: "inset 0 -3px 0 rgba(0,0,0,.08)" }}
          initial={{ x: 70 }}
          animate={{ x: 22 }}
          transition={{ delay: 0.35, duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        />
        <motion.span
          className="relative z-10 text-[15px] font-bold px-3 py-1 rounded-full"
          style={{ background: "#fff", color: "#92400E" }}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 1.0, duration: 0.4 }}
        >
          {alert.salt}
        </motion.span>
      </div>

      <p className="text-[17px] leading-snug m-0" style={{ color: "#78350F" }}>
        <strong>{alert.medicines[0]}</strong> aur <strong>{alert.medicines[1]}</strong> dono mein{" "}
        {alert.salt} hai. Dono lene se pehle doctor se poochhein.
      </p>
    </motion.div>
  );
}
