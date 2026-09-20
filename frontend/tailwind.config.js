/** DoseWise design system. Values come straight from the build plan, so a
 *  screen can be checked against the spec by reading this file. */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        teal: { DEFAULT: "#0F766E", deep: "#0B5A54", soft: "#E6F2F0" },
        cream: "#FAF7F2",
        ink: { DEFAULT: "#14201C", soft: "#4B5A55", faint: "#7C8A85" },
        ok: "#16A34A",
        warn: "#D97706",
        danger: "#DC2626",
        slot: {
          morning: "#FDF3D0",
          morningInk: "#7A5B10",
          afternoon: "#FDE4CE",
          afternoonInk: "#8A4B14",
          night: "#DDE2F5",
          nightInk: "#2F3A73",
        },
      },
      fontFamily: {
        sans: ["Noto Sans", "system-ui", "sans-serif"],
        deva: ["Noto Sans Devanagari", "Noto Sans", "sans-serif"],
      },
      fontSize: {
        // parent scale: nothing under 22px on a parent screen
        parent: ["22px", { lineHeight: "1.45" }],
        "parent-lg": ["32px", { lineHeight: "1.25", fontWeight: "700" }],
        "parent-xl": ["44px", { lineHeight: "1.15", fontWeight: "800" }],
      },
      borderRadius: { xl: "16px", "2xl": "20px", "3xl": "28px" },
      spacing: { 18: "4.5rem", 22: "5.5rem" },
      minHeight: { touch: "64px" },
      boxShadow: {
        card: "0 1px 2px rgba(20,32,28,.06), 0 8px 24px rgba(20,32,28,.06)",
        lift: "0 12px 32px rgba(15,118,110,.18)",
      },
      transitionTimingFunction: { gentle: "cubic-bezier(.22,.61,.36,1)" },
    },
  },
  plugins: [],
};
