import { AnimatePresence } from "framer-motion";
import { BellRing, Camera, HeartPulse, LayoutDashboard, User } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Toast } from "./components/ui.jsx";
import { t } from "./i18n.js";
import Dashboard from "./screens/Dashboard.jsx";
import Onboarding from "./screens/Onboarding.jsx";
import ParentToday from "./screens/ParentToday.jsx";
import ReminderTakeover from "./screens/ReminderTakeover.jsx";
import Review from "./screens/Review.jsx";
import Scan from "./screens/Scan.jsx";
import VisitCard from "./screens/VisitCard.jsx";
import { useApp } from "./store.jsx";

/* Two apps in one. The mode switch is the only thing they share, and the
 * parent never sees the caregiver's numbers. */
export default function App() {
  const { parentId, mode, setMode, lang, health } = useApp();
  const [screen, setScreen] = useState(parentId ? "dashboard" : "onboarding");
  const [scan, setScan] = useState(null);
  const [reminderSlot, setReminderSlot] = useState(null);
  const navRef = useRef(null);

  /* The bottom bar's height changes (the offline notice adds a line), and
     screens with their own sticky footer need to clear it. Publish it rather
     than guessing. */
  useEffect(() => {
    const el = navRef.current;
    if (!el || typeof ResizeObserver === "undefined") return undefined;
    const publish = () =>
      document.documentElement.style.setProperty("--nav-h", `${el.offsetHeight}px`);
    publish();
    const observer = new ResizeObserver(publish);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!parentId) {
      setScreen("onboarding");
      setMode("caregiver"); // Parent Mode has nothing to show without a parent
    }
  }, [parentId, setMode]);

  const caregiverScreens = {
    onboarding: <Onboarding onDone={(next) => setScreen(next || "scan")} />,
    scan: (
      <Scan
        onReviewReady={(result) => {
          setScan(result);
          setScreen("review");
        }}
      />
    ),
    review: scan ? (
      <Review scan={scan} onConfirmed={() => setScreen("dashboard")} />
    ) : (
      <Scan onReviewReady={(result) => (setScan(result), setScreen("review"))} />
    ),
    dashboard: <Dashboard onOpenVisitCard={() => setScreen("visitcard")} />,
    visitcard: <VisitCard onBack={() => setScreen("dashboard")} />,
  };

  return (
    <div className="min-h-full" style={{ paddingBottom: "var(--nav-h)" }}>
      {mode === "parent" ? (
        <ParentToday onOpenReminder={setReminderSlot} />
      ) : (
        caregiverScreens[screen] || caregiverScreens.dashboard
      )}

      <AnimatePresence>
        {reminderSlot && (
          <ReminderTakeover slot={reminderSlot} onClose={() => setReminderSlot(null)} />
        )}
      </AnimatePresence>

      <Toast />

      {/* Bottom bar. Parent Mode shows one tab, because the parent has one job. */}
      <nav
        ref={navRef}
        className="fixed inset-x-0 bottom-0 z-30 border-t border-black/5 bg-cream/95 backdrop-blur"
        aria-label="Main"
      >
        <div className="mx-auto flex max-w-2xl items-stretch gap-1 p-2">
          <NavButton
            active={mode === "parent"}
            onClick={() => setMode("parent")}
            icon={User}
            label={t(lang, "parentMode")}
          />
          <NavButton
            active={mode === "caregiver" && screen === "scan"}
            onClick={() => {
              setMode("caregiver");
              setScreen("scan");
            }}
            icon={Camera}
            label="Scan"
            disabled={!parentId}
          />
          <NavButton
            active={mode === "caregiver" && ["dashboard", "visitcard"].includes(screen)}
            onClick={() => {
              setMode("caregiver");
              setScreen("dashboard");
            }}
            icon={LayoutDashboard}
            label={t(lang, "caregiverMode")}
            disabled={!parentId}
          />
          <NavButton
            active={false}
            onClick={() => setReminderSlot("NIGHT")}
            icon={BellRing}
            label="Reminder"
            disabled={!parentId}
          />
        </div>
        {health && !health.bedrock && (
          <p className="pb-2 text-center text-[11px] text-ink-faint">
            offline mode · no AWS credentials configured
          </p>
        )}
      </nav>
    </div>
  );
}

function NavButton({ active, onClick, icon: Icon, label, disabled }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-current={active ? "page" : undefined}
      className={`flex min-h-[60px] min-w-0 flex-1 flex-col items-center justify-center gap-1
                  rounded-xl px-1 py-2 text-[11px] font-semibold transition-colors disabled:opacity-40
                  ${active ? "bg-teal text-white" : "text-ink-soft hover:bg-black/[.04]"}`}
    >
      <Icon size={22} aria-hidden="true" />
      <span className="w-full truncate text-center">{label}</span>
    </button>
  );
}
