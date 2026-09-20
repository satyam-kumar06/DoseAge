import React from "react";
import { COLORS } from "../constants/theme";

// An empty screen is an invitation to act, never a dead end.
export default function EmptyState({ icon, title, body, actionLabel, onAction }) {
  return (
    <div
      className="flex flex-col items-center text-center gap-2 rounded-[20px] px-6 py-9"
      style={{ background: COLORS.surface, boxShadow: "0 6px 20px rgba(41,37,36,0.06)" }}
    >
      <span
        className="w-16 h-16 rounded-full flex items-center justify-center mb-1"
        style={{ background: "rgba(15,118,110,0.10)" }}
      >
        {icon}
      </span>
      <h3 className="text-[22px] font-bold m-0" style={{ color: COLORS.ink }}>{title}</h3>
      <p className="text-[17px] m-0 leading-snug" style={{ color: COLORS.inkMuted }}>{body}</p>
      {actionLabel && (
        <button
          type="button"
          onClick={onAction}
          className="mt-4 w-full min-h-[64px] rounded-[16px] text-white text-[20px] font-bold border-0"
          style={{ background: `linear-gradient(180deg,${COLORS.teal} 0%,${COLORS.tealDeep} 100%)`, boxShadow: "0 8px 20px rgba(15,118,110,.28)" }}
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
