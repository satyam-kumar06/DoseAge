import React from "react";
import { useNavigate } from "react-router";
import Shell from "../components/Shell";
import BottomNav from "../components/BottomNav";
import EmptyState from "../components/EmptyState";
import { ShareIcon, FileIcon, CameraIcon } from "../components/icons/Icons";
import { useDoseWise } from "../store/DoseWiseStore";
import { COLORS, SLOT_THEME, FOOD_LABEL } from "../constants/theme";
import { dayLabel } from "../lib/format";

// One page a doctor or pharmacist can read in 20 seconds.
export default function VisitCard() {
  const navigate = useNavigate();
  const { meds, alerts, insights, hasSchedule } = useDoseWise();

  if (!hasSchedule) {
    return (
      <Shell bottomNav>
        <EmptyState
          icon={<CameraIcon color={COLORS.teal} size={32} />}
          title="Visit card ke liye dawai chahiye"
          body="Prescription scan karke confirm kijiye, phir yahan ek page ka summary ban jayega."
          actionLabel="Prescription scan karein"
          onAction={() => navigate("/scan")}
        />
        <BottomNav />
      </Shell>
    );
  }

  const week = insights.adherence7d;
  const pct = Math.round(
    (week.reduce((s, d) => s + d.taken, 0) / week.reduce((s, d) => s + d.scheduled, 0)) * 100
  );

  async function handleShare() {
    // TODO(B): POST /parents/{id}/visit-card, share the returned 24h S3 link.
    const text = `DoseWise: ${insights.parent.name} ki medicine summary`;
    if (navigator.share) {
      try { await navigator.share({ title: "DoseWise Visit Card", text }); } catch { /* user cancelled */ }
    } else {
      window.print();
    }
  }

  return (
    <Shell bottomNav>
      <header>
        <h1 className="text-[30px] font-bold m-0 tracking-tight" style={{ color: COLORS.ink }}>
          Doctor Visit Card
        </h1>
        <p className="text-[17px] mt-2 m-0 leading-snug" style={{ color: COLORS.inkMuted }}>
          Yeh page kisi bhi doctor ya pharmacist ko dikha dijiye.
        </p>
      </header>

      {/* The printable page itself */}
      <article
        className="rounded-[20px] overflow-hidden"
        style={{ background: COLORS.surface, boxShadow: "0 6px 24px rgba(41,37,36,0.08)", border: `1px solid ${COLORS.line}` }}
      >
        <div className="px-5 py-4" style={{ borderBottom: `1px solid ${COLORS.line}` }}>
          <p className="text-[22px] font-bold m-0" style={{ color: COLORS.ink }}>{insights.parent.name}</p>
          <p className="text-[15px] m-0 mt-[2px]" style={{ color: COLORS.inkMuted }}>
            {insights.parent.age} saal · {dayLabel("en")}
          </p>
        </div>

        <div className="px-5 py-4 flex flex-col gap-4">
          <div>
            <h2 className="text-[15px] font-bold m-0 mb-3" style={{ color: COLORS.inkMuted }}>
              Abhi chalu dawaiyan
            </h2>
            <div className="flex flex-col gap-3">
              {meds.map((m) => (
                <div key={m.id} style={{ borderLeft: `3px solid ${COLORS.teal}`, paddingLeft: 12 }}>
                  <p className="text-[18px] font-semibold m-0" style={{ color: COLORS.ink }}>
                    {m.brand} {m.strength}
                  </p>
                  <p className="text-[15px] m-0" style={{ color: COLORS.inkMuted }}>
                    {m.salts.join(" + ")} · {m.frequency_code} · {FOOD_LABEL[m.food].en}
                  </p>
                  <p className="text-[15px] m-0" style={{ color: COLORS.inkMuted }}>
                    {m.slots.map((s) => `${s} ${SLOT_THEME[s].time}`).join(", ")}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div style={{ borderTop: `1px solid ${COLORS.line}`, paddingTop: 14 }}>
            <h2 className="text-[15px] font-bold m-0 mb-2" style={{ color: COLORS.inkMuted }}>
              Adherence, pichhle 7 din
            </h2>
            <p className="text-[24px] font-bold m-0" style={{ color: pct >= 80 ? COLORS.success : COLORS.warning }}>
              {pct}%
            </p>
          </div>

          {alerts.length > 0 && (
            <div style={{ borderTop: `1px solid ${COLORS.line}`, paddingTop: 14 }}>
              <h2 className="text-[15px] font-bold m-0 mb-2" style={{ color: COLORS.inkMuted }}>
                Flagged: same salt
              </h2>
              {alerts.map((a) => (
                <p key={a.id} className="text-[16px] m-0" style={{ color: "#92400E" }}>
                  {a.medicines.join(" + ")} — both contain {a.salt}
                </p>
              ))}
            </div>
          )}

          <p className="text-[13px] m-0 leading-snug" style={{ color: COLORS.inkMuted, borderTop: `1px solid ${COLORS.line}`, paddingTop: 14 }}>
            DoseWise flags medicines that share a salt. It never changes a prescription and
            never gives medical advice. Please confirm everything with the treating doctor.
          </p>
        </div>
      </article>

      <div className="flex flex-col gap-3">
        <button
          type="button"
          onClick={handleShare}
          className="w-full min-h-[64px] rounded-[16px] text-white text-[20px] font-bold flex items-center justify-center gap-3 border-0"
          style={{ background: `linear-gradient(180deg,${COLORS.teal} 0%,${COLORS.tealDeep} 100%)`, boxShadow: "0 8px 20px rgba(15,118,110,.28)" }}
        >
          <ShareIcon color="#fff" />
          Share karein
        </button>
        <button
          type="button"
          onClick={() => window.print()}
          className="w-full min-h-[56px] rounded-[16px] text-[18px] font-semibold flex items-center justify-center gap-2 border-2 bg-transparent"
          style={{ borderColor: COLORS.line, color: COLORS.inkMuted }}
        >
          <FileIcon size={22} />
          PDF download karein
        </button>
      </div>

      <BottomNav />
    </Shell>
  );
}
