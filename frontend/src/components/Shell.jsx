import React from "react";
import { COLORS } from "../constants/theme";

// Every screen sits in the same 430px column on the warm background, so the
// app feels like one product whether you're in parent or caregiver mode.
export default function Shell({ children, pad = true, bottomNav = false }) {
  return (
    <div
      className="min-h-screen w-full flex justify-center"
      style={{ background: COLORS.bgGradient, fontFamily: "'Noto Sans','Noto Sans Devanagari',sans-serif" }}
    >
      <div
        className={`w-full max-w-[430px] flex flex-col gap-[22px] ${pad ? "px-[18px] pt-[26px]" : ""}`}
        style={{ paddingBottom: bottomNav ? 110 : 48 }}
      >
        {children}
      </div>
    </div>
  );
}
