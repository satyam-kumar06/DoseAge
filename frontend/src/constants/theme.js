// One source of truth for the whole app. Review, Today, Dashboard and Visit Card
// all pull from here so the palette never drifts between screens.

export const SLOT_THEME = {
  Morning:   { hindi: "Subah",   time: "8:00",  bg: "#FDF4DF", bgExpanded: "#FAE8BE", accent: "#A9740A", ring: "rgba(169,116,10,0.28)", shadow: "rgba(169,116,10,0.16)" },
  Afternoon: { hindi: "Dopahar", time: "2:00",  bg: "#FDEEE2", bgExpanded: "#FAD9C0", accent: "#B9500C", ring: "rgba(185,80,12,0.28)",  shadow: "rgba(185,80,12,0.16)" },
  Night:     { hindi: "Raat",    time: "9:00",  bg: "#EBEAF8", bgExpanded: "#D9D7F2", accent: "#4338CA", ring: "rgba(67,56,202,0.28)",  shadow: "rgba(67,56,202,0.16)" },
};

export const SLOT_ORDER = ["Morning", "Afternoon", "Night"];

export const FOOD_LABEL = {
  before_food: { hi: "Khane se pehle", en: "Before food" },
  after_food:  { hi: "Khane ke baad",  en: "After food" },
};

export const COLORS = {
  bg: "#FAF7F2",
  bgGradient: "radial-gradient(120% 60% at 50% -10%, #FFF9EF 0%, #FAF7F2 55%)",
  surface: "#FFFFFF",
  ink: "#292524",
  inkMuted: "#7A716A",
  line: "rgba(41,37,36,0.10)",
  teal: "#0F766E",
  tealDeep: "#0B5A54",
  success: "#16A34A",
  warning: "#D97706",
  warningBg: "#FDF0D5",
  danger: "#DC2626",
  track: "#EDE7DE",
};

// Pill colours let a parent match "the yellow one" to the strip in their hand.
// Replaced by real photoUrl crops once the scan pipeline returns them.
export const PILL_COLORS = ["#EFBE3F", "#F09A56", "#6D6CC4", "#E07E4E", "#4FA3A0", "#C96A8E"];
