import React from "react";

// One icon family for the whole app: 2.6 stroke, round caps, 15% fill washes.
const s = { fill: "none", strokeWidth: 2.6, strokeLinecap: "round", strokeLinejoin: "round" };

export function SunriseIcon({ color = "currentColor", size = 34 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden="true">
      <circle cx="20" cy="24" r="7" fill={color} opacity=".18" />
      <path d="M13 24a7 7 0 0 1 14 0" stroke={color} {...s} />
      <line x1="20" y1="9" x2="20" y2="13.5" stroke={color} {...s} />
      <line x1="9" y1="24" x2="5.5" y2="24" stroke={color} {...s} />
      <line x1="34.5" y1="24" x2="31" y2="24" stroke={color} {...s} />
      <line x1="11" y1="15" x2="13.6" y2="17.6" stroke={color} {...s} />
      <line x1="29" y1="15" x2="26.4" y2="17.6" stroke={color} {...s} />
      <line x1="11" y1="31" x2="29" y2="31" stroke={color} {...s} opacity=".45" />
    </svg>
  );
}

export function SunHighIcon({ color = "currentColor", size = 34 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden="true">
      <circle cx="20" cy="20" r="8" fill={color} opacity=".18" />
      <circle cx="20" cy="20" r="8" stroke={color} {...s} />
      {[[20,3.5,20,8],[20,32,20,36.5],[3.5,20,8,20],[32,20,36.5,20],[8.2,8.2,11.3,11.3],[31.8,8.2,28.7,11.3],[8.2,31.8,11.3,28.7],[31.8,31.8,28.7,28.7]].map((l, i) => (
        <line key={i} x1={l[0]} y1={l[1]} x2={l[2]} y2={l[3]} stroke={color} {...s} />
      ))}
    </svg>
  );
}

export function MoonStarsIcon({ color = "currentColor", size = 34 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden="true">
      <path d="M25 8a13 13 0 1 0 8 20.5A11 11 0 0 1 25 8Z" fill={color} opacity=".18" stroke={color} {...s} />
      <path d="M31 9l1.5 3.4L36 13.9l-3.5 1.5L31 18.8l-1.5-3.4L26 13.9l3.5-1.5L31 9Z" fill={color} />
    </svg>
  );
}

export function SpeakerIcon({ color = "#0F766E", size = 26 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 26 26" aria-hidden="true">
      <path d="M6 10v6h4l5 4V6l-5 4H6Z" fill={color} />
      <path d="M18 9.5a5 5 0 0 1 0 7" stroke={color} {...s} />
      <path d="M21 6.5a9.5 9.5 0 0 1 0 13" stroke={color} {...s} opacity=".55" />
    </svg>
  );
}

export function CameraIcon({ color = "currentColor", size = 30 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <path d="M4 11h5l2.5-3.5h9L23 11h5v15H4V11Z" stroke={color} {...s} />
      <circle cx="16" cy="18" r="5.5" stroke={color} {...s} />
      <circle cx="16" cy="18" r="5.5" fill={color} opacity=".15" />
    </svg>
  );
}

export function CheckIcon({ color = "#fff", size = 24 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 13l4 4L19 7" stroke={color} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </svg>
  );
}

export function AlertIcon({ color = "#D97706", size = 26 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 26 26" aria-hidden="true">
      <path d="M13 3.5 24 22H2L13 3.5Z" fill={color} opacity=".18" stroke={color} {...s} />
      <line x1="13" y1="10" x2="13" y2="15.5" stroke={color} {...s} />
      <circle cx="13" cy="18.8" r="1.4" fill={color} />
    </svg>
  );
}

export function PillIcon({ color = "currentColor", size = 26 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 26 26" aria-hidden="true">
      <rect x="2.5" y="8" width="21" height="10" rx="5" stroke={color} {...s} />
      <path d="M13 8v10" stroke={color} {...s} />
      <rect x="2.5" y="8" width="10.5" height="10" rx="5" fill={color} opacity=".18" />
    </svg>
  );
}

export function HomeIcon({ color = "currentColor", size = 26 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 26 26" aria-hidden="true">
      <path d="M4 11.5 13 4l9 7.5V22H4V11.5Z" stroke={color} {...s} />
      <path d="M10 22v-6h6v6" stroke={color} {...s} />
    </svg>
  );
}

export function ChartIcon({ color = "currentColor", size = 26 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 26 26" aria-hidden="true">
      <line x1="4" y1="22" x2="22" y2="22" stroke={color} {...s} />
      <rect x="6" y="13" width="4" height="7" rx="1.4" fill={color} opacity=".25" stroke={color} {...s} />
      <rect x="12.5" y="8" width="4" height="12" rx="1.4" fill={color} opacity=".25" stroke={color} {...s} />
      <rect x="19" y="4.5" width="4" height="15.5" rx="1.4" fill={color} opacity=".25" stroke={color} {...s} />
    </svg>
  );
}

export function FileIcon({ color = "currentColor", size = 26 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 26 26" aria-hidden="true">
      <path d="M6 3h9l5 5v15H6V3Z" stroke={color} {...s} />
      <path d="M15 3v5h5" stroke={color} {...s} />
      <line x1="9.5" y1="13" x2="16.5" y2="13" stroke={color} {...s} />
      <line x1="9.5" y1="17" x2="16.5" y2="17" stroke={color} {...s} />
    </svg>
  );
}

export function ShareIcon({ color = "currentColor", size = 24 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 3v12" stroke={color} {...s} />
      <path d="M8 7l4-4 4 4" stroke={color} {...s} />
      <path d="M5 13v7h14v-7" stroke={color} {...s} />
    </svg>
  );
}

export function BackIcon({ color = "currentColor", size = 24 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M15 5l-7 7 7 7" stroke={color} {...s} />
    </svg>
  );
}

export function EditIcon({ color = "currentColor", size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 20h4l10-10-4-4L4 16v4Z" stroke={color} {...s} />
      <path d="M14 6l4 4" stroke={color} {...s} />
    </svg>
  );
}
