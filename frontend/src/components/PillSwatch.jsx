import React from "react";

// Stand-in for the real pill-strip crop. Swap for <img src={photoUrl}/> once
// the scan pipeline returns cropped photos.
export default function PillSwatch({ colorHint, photoUrl, size = 52 }) {
  if (photoUrl) {
    return (
      <img
        src={photoUrl}
        alt=""
        className="rounded-[14px] shrink-0 object-cover"
        style={{ width: size, height: size }}
      />
    );
  }
  return (
    <div
      className="rounded-[14px] shrink-0 flex items-center justify-center"
      style={{ width: size, height: size, background: colorHint, boxShadow: "inset 0 -3px 0 rgba(0,0,0,0.08)" }}
      aria-hidden="true"
    >
      <span className="rounded-full bg-white/85" style={{ width: size * 0.42, height: size * 0.23 }} />
    </div>
  );
}
