// Single source of truth for slot colors + copy.
// Promote to named Tailwind colors in tailwind.config.js when the Review and
// Dashboard screens start reusing them.

export const SLOT_THEME = {
  Morning: {
    hindi: "Subah",
    bg: "#FDF4DF",
    bgExpanded: "#FAE8BE",
    accent: "#A9740A",
    ring: "rgba(169,116,10,0.28)",
    shadow: "rgba(169,116,10,0.16)",
  },
  Afternoon: {
    hindi: "Dopahar",
    bg: "#FDEEE2",
    bgExpanded: "#FAD9C0",
    accent: "#B9500C",
    ring: "rgba(185,80,12,0.28)",
    shadow: "rgba(185,80,12,0.16)",
  },
  Night: {
    hindi: "Raat",
    bg: "#EBEAF8",
    bgExpanded: "#D9D7F2",
    accent: "#4338CA",
    ring: "rgba(67,56,202,0.28)",
    shadow: "rgba(67,56,202,0.16)",
  },
};

export const FOOD_LABEL = {
  before_food: "Khane se pehle",
  after_food: "Khane ke baad",
};

export const COLORS = {
  bg: "#FAF7F2",
  surface: "#FFFFFF",
  ink: "#292524",
  inkMuted: "#7A716A",
  teal: "#0F766E",
  tealDeep: "#0B5A54",
  success: "#16A34A",
  track: "#EDE7DE",
};
