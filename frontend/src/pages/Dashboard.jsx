import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { motion } from "framer-motion";
import Shell from "../components/Shell";
import BottomNav from "../components/BottomNav";
import EmptyState from "../components/EmptyState";
import { AlertIcon, PillIcon, CameraIcon } from "../components/icons/Icons";
import { useDoseWise } from "../store/DoseWiseStore";
import { COLORS } from "../constants/theme";

const R = 48;
const C = 2 * Math.PI * R;

// Counts up to the monthly saving. One number, one moment.
function useCountUp(target, run) {
  const [n, setN] = useState(0);
  useEffect(() => {
    if (!run) return;
    let raf;
    const start = performance.now();
    const tick = (t) => {
      const p = Math.min((t - start) / 1400, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      setN(Math.round(target * eased));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, run]);
  return n;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { hasSchedule, alerts, markAlertRead, insights, slots, doneCount } = useDoseWise();
  const savings = useCountUp(insights.savings.monthlyTotal, hasSchedule);

  if (!hasSchedule) {
    return (
      <Shell bottomNav>
        <EmptyState
          icon={<CameraIcon color={COLORS.teal} size={32} />}
          title="Dashboard abhi khaali hai"
          body="Ek prescription scan karte hi adherence, refill aur savings yahan dikhne lagenge."
          actionLabel="Prescription scan karein"
          onAction={() => navigate("/scan")}
        />
        <BottomNav />
      </Shell>
    );
  }

  const week = insights.adherence7d;
  const weekTaken = week.reduce((s, d) => s + d.taken, 0);
  const weekTotal = week.reduce((s, d) => s + d.scheduled, 0);
  const pct = Math.round((weekTaken / weekTotal) * 100);

  return (
    <Shell bottomNav>
      <header>
        <h1 className="text-[30px] font-bold m-0 tracking-tight" style={{ color: COLORS.ink }}>
          {insights.parent.name}
        </h1>
        <p className="text-[17px] mt-1 m-0" style={{ color: COLORS.inkMuted }}>
          Aaj {doneCount} / {slots.length} doses li gayi
        </p>
      </header>

      {/* Weekly adherence */}
      <section
        className="rounded-[20px] p-5 flex items-center gap-5"
        style={{ background: COLORS.surface, boxShadow: "0 6px 20px rgba(41,37,36,0.06)" }}
      >
        <div className="relative w-[112px] h-[112px] shrink-0">
          <svg width="112" height="112" viewBox="0 0 112 112" style={{ transform: "rotate(-90deg)" }}>
            <circle cx="56" cy="56" r={R} fill="none" strokeWidth="11" stroke={COLORS.track} />
            <motion.circle
              cx="56" cy="56" r={R} fill="none" strokeWidth="11"
              stroke={COLORS.success} strokeLinecap="round" strokeDasharray={C}
              initial={{ strokeDashoffset: C }}
              animate={{ strokeDashoffset: C - (C * pct) / 100 }}
              transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1] }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-[28px] font-bold leading-none" style={{ color: COLORS.ink }}>{pct}%</span>
            <span className="text-[13px]" style={{ color: COLORS.inkMuted }}>7 din</span>
          </div>
        </div>

        <div className="flex-1 min-w-0">
          <h2 className="text-[19px] font-semibold m-0 mb-3" style={{ color: COLORS.ink }}>
            Is hafte
          </h2>
          <div className="flex gap-[6px]">
            {week.map((d) => {
              const full = d.taken === d.scheduled;
              const none = d.taken === 0;
              return (
                <div key={d.day} className="flex flex-col items-center gap-1 flex-1">
                  <span
                    className="w-full rounded-full"
                    style={{
                      height: 30,
                      background: none ? COLORS.track : full ? COLORS.success : COLORS.warning,
                      opacity: none ? 1 : 0.9,
                    }}
                    title={`${d.day}: ${d.taken}/${d.scheduled}`}
                  />
                  <span className="text-[11px]" style={{ color: COLORS.inkMuted }}>{d.day[0]}</span>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Alerts */}
      {alerts.length > 0 && (
        <section className="flex flex-col gap-2">
          <h2 className="text-[19px] font-semibold m-0" style={{ color: COLORS.ink }}>Alerts</h2>
          {alerts.map((a) => (
            <button
              key={a.id}
              type="button"
              onClick={() => markAlertRead(a.id)}
              className="flex items-start gap-3 rounded-[16px] p-4 text-left border-2 w-full"
              style={{
                background: a.read ? COLORS.surface : COLORS.warningBg,
                borderColor: a.read ? COLORS.line : COLORS.warning,
              }}
            >
              <AlertIcon color={a.read ? COLORS.inkMuted : COLORS.warning} />
              <span className="flex-1 min-w-0">
                <span className="block text-[17px] font-semibold" style={{ color: a.read ? COLORS.inkMuted : "#92400E" }}>
                  {a.medicines.join(" + ")}
                </span>
                <span className="block text-[15px] mt-[2px] leading-snug" style={{ color: a.read ? COLORS.inkMuted : "#78350F" }}>
                  Dono mein {a.salt} hai. Doctor se poochhein.
                </span>
              </span>
              <span className="text-[13px] shrink-0" style={{ color: COLORS.inkMuted }}>{a.at}</span>
            </button>
          ))}
        </section>
      )}

      {/* Refill radar */}
      <section className="flex flex-col gap-2">
        <h2 className="text-[19px] font-semibold m-0" style={{ color: COLORS.ink }}>Dawai khatam hone wali hai</h2>
        <div className="flex gap-2 flex-wrap">
          {insights.refills.map((r) => {
            const urgent = r.daysLeft <= 3;
            return (
              <span
                key={r.brand}
                className="flex items-center gap-2 rounded-full px-4 py-3 text-[16px] font-semibold border-2"
                style={{
                  background: urgent ? COLORS.warningBg : COLORS.surface,
                  borderColor: urgent ? COLORS.warning : COLORS.line,
                  color: urgent ? "#92400E" : COLORS.inkMuted,
                }}
              >
                <PillIcon size={20} color={urgent ? COLORS.warning : COLORS.inkMuted} />
                {r.brand}: {r.daysLeft} din bacha hai
              </span>
            );
          })}
        </div>
      </section>

      {/* Jan Aushadhi savings */}
      <section
        className="rounded-[20px] p-5"
        style={{ background: `linear-gradient(160deg,${COLORS.teal} 0%,${COLORS.tealDeep} 100%)`, boxShadow: "0 10px 28px rgba(15,118,110,.28)" }}
      >
        <p className="text-[16px] m-0 text-white/80">Jan Aushadhi generics se har mahine</p>
        <p className="text-[46px] font-bold m-0 text-white leading-tight tracking-tight">
          ₹{savings.toLocaleString("en-IN")}
        </p>
        <p className="text-[16px] m-0 text-white/80 mb-4">bach sakte hain</p>

        <div className="flex flex-col gap-2">
          {insights.savings.items.map((it) => (
            <div key={it.brand} className="flex items-center justify-between rounded-xl px-3 py-2" style={{ background: "rgba(255,255,255,0.12)" }}>
              <span className="text-[16px] text-white font-medium truncate">{it.brand}</span>
              <span className="text-[16px] text-white font-semibold shrink-0">₹{it.monthlySaving}</span>
            </div>
          ))}
        </div>

        <p className="text-[14px] mt-4 mb-0 text-white/75 leading-snug">
          {insights.savings.disclaimer}
        </p>
      </section>

      <button
        type="button"
        onClick={() => navigate("/visit-card")}
        className="w-full min-h-[64px] rounded-[16px] text-[19px] font-bold border-2 bg-transparent"
        style={{ borderColor: COLORS.teal, color: COLORS.teal }}
      >
        Doctor Visit Card banayein
      </button>

      <BottomNav />
    </Shell>
  );
}
