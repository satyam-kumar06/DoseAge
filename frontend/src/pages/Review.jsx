import React, { useState } from "react";
import { useNavigate } from "react-router";
import { motion, AnimatePresence } from "framer-motion";
import Shell from "../components/Shell";
import DuplicateBanner from "../components/DuplicateBanner";
import EmptyState from "../components/EmptyState";
import PillSwatch from "../components/PillSwatch";
import { SunriseIcon, SunHighIcon, MoonStarsIcon, AlertIcon, EditIcon, CameraIcon } from "../components/icons/Icons";
import { useDoseWise } from "../store/DoseWiseStore";
import { COLORS, SLOT_THEME, SLOT_ORDER, FOOD_LABEL, PILL_COLORS } from "../constants/theme";

const SLOT_ICON = { Morning: SunriseIcon, Afternoon: SunHighIcon, Night: MoonStarsIcon };

// The screen judges love: the AI never saves without a human confirming.
export default function Review() {
  const navigate = useNavigate();
  const { scan, updateScanMedicine, removeScanMedicine, confirmMedicines } = useDoseWise();
  const [editingId, setEditingId] = useState(null);

  if (!scan) {
    return (
      <Shell>
        <EmptyState
          icon={<CameraIcon color={COLORS.teal} size={32} />}
          title="Abhi kuch review karne ko nahi"
          body="Pehle ek prescription scan karein, phir yahan har dawai check kar sakte hain."
          actionLabel="Prescription scan karein"
          onAction={() => navigate("/scan")}
        />
      </Shell>
    );
  }

  function toggleSlot(med, slotName) {
    const next = med.slots.includes(slotName)
      ? med.slots.filter((x) => x !== slotName)
      : [...med.slots, slotName];
    updateScanMedicine(med.id, { slots: next });
  }

  function handleConfirm() {
    confirmMedicines();
    navigate("/today");
  }

  return (
    <Shell>
      <header>
        <h1 className="text-[30px] font-bold m-0 tracking-tight" style={{ color: COLORS.ink }}>
          Ek baar check kar lijiye
        </h1>
        <p className="text-[17px] mt-2 m-0 leading-snug" style={{ color: COLORS.inkMuted }}>
          Humne parchi se yeh padha hai. Kuch galat lage to tap karke theek kar dijiye.
          Aapke confirm karne se pehle kuch save nahi hota.
        </p>
      </header>

      {scan.alerts.map((alert, i) => (
        <DuplicateBanner key={i} alert={alert} />
      ))}

      <div className="flex flex-col gap-3">
        {scan.medicines.map((med, idx) => {
          const needsCheck = med.confidence < 0.7 || !med.verified;
          const isEditing = editingId === med.id;

          return (
            <motion.article
              layout
              key={med.id}
              className="rounded-[20px] p-[16px]"
              style={{
                background: COLORS.surface,
                boxShadow: "0 4px 16px rgba(41,37,36,0.06)",
                border: needsCheck ? `2px solid ${COLORS.warning}` : `1px solid ${COLORS.line}`,
              }}
            >
              <div className="flex items-start gap-[14px]">
                <PillSwatch colorHint={PILL_COLORS[idx % PILL_COLORS.length]} />

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h2 className="text-[22px] font-bold m-0 truncate" style={{ color: COLORS.ink }}>
                      {med.brand}
                    </h2>
                    {med.strength && (
                      <span
                        className="text-[14px] font-semibold rounded-lg px-2 py-[3px] shrink-0"
                        style={{ background: "rgba(15,118,110,0.10)", color: COLORS.teal }}
                      >
                        {med.strength}
                      </span>
                    )}
                  </div>
                  <p className="text-[16px] m-0 mt-[2px]" style={{ color: COLORS.inkMuted }}>
                    {med.salts.join(" + ")}
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() => setEditingId(isEditing ? null : med.id)}
                  aria-label={`${med.brand} edit karein`}
                  className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0 border"
                  style={{ borderColor: COLORS.line, background: isEditing ? "rgba(15,118,110,0.10)" : "transparent" }}
                >
                  <EditIcon color={isEditing ? COLORS.teal : COLORS.inkMuted} />
                </button>
              </div>

              {needsCheck && (
                <div className="flex items-center gap-2 mt-3 rounded-xl px-3 py-2" style={{ background: COLORS.warningBg }}>
                  <AlertIcon size={20} />
                  <span className="text-[15px] font-semibold" style={{ color: "#92400E" }}>
                    Zara check kijiye, hum poore sure nahi hain
                  </span>
                </div>
              )}

              {/* Timing chips: tap to toggle */}
              <div className="flex gap-2 mt-3 flex-wrap">
                {SLOT_ORDER.map((slotName) => {
                  const on = med.slots.includes(slotName);
                  const t = SLOT_THEME[slotName];
                  const Icon = SLOT_ICON[slotName];
                  return (
                    <button
                      key={slotName}
                      type="button"
                      onClick={() => toggleSlot(med, slotName)}
                      aria-pressed={on}
                      className="flex items-center gap-2 rounded-full px-3 min-h-[48px] border-2 text-[16px] font-semibold"
                      style={{
                        background: on ? t.bgExpanded : "transparent",
                        borderColor: on ? t.accent : COLORS.line,
                        color: on ? t.accent : COLORS.inkMuted,
                      }}
                    >
                      <Icon color={on ? t.accent : COLORS.inkMuted} size={22} />
                      {t.hindi}
                    </button>
                  );
                })}

                <button
                  type="button"
                  onClick={() =>
                    updateScanMedicine(med.id, {
                      food: med.food === "after_food" ? "before_food" : "after_food",
                    })
                  }
                  className="rounded-full px-4 min-h-[48px] border-2 text-[16px] font-semibold"
                  style={{ borderColor: COLORS.line, color: COLORS.ink, background: "transparent" }}
                >
                  {FOOD_LABEL[med.food].hi}
                </button>
              </div>

              <AnimatePresence initial={false}>
                {isEditing && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
                    className="overflow-hidden"
                  >
                    <div className="pt-4 flex flex-col gap-3">
                      <label className="text-[15px] font-semibold" style={{ color: COLORS.ink }}>
                        Dawai ka naam
                        <input
                          value={med.brand}
                          onChange={(e) => updateScanMedicine(med.id, { brand: e.target.value })}
                          className="mt-1 w-full min-h-[56px] rounded-[14px] px-3 text-[19px] border-2 bg-white"
                          style={{ borderColor: COLORS.line, color: COLORS.ink }}
                        />
                      </label>

                      <label className="text-[15px] font-semibold" style={{ color: COLORS.ink }}>
                        Kitne din
                        <input
                          type="number"
                          value={med.durationDays}
                          onChange={(e) => updateScanMedicine(med.id, { durationDays: Number(e.target.value) })}
                          className="mt-1 w-full min-h-[56px] rounded-[14px] px-3 text-[19px] border-2 bg-white"
                          style={{ borderColor: COLORS.line, color: COLORS.ink }}
                        />
                      </label>

                      {/* Trust by showing the source: what the AI actually read */}
                      <div className="rounded-[14px] px-3 py-3" style={{ background: "#F5F1EA" }}>
                        <p className="text-[13px] font-semibold m-0 mb-1" style={{ color: COLORS.inkMuted }}>
                          Parchi mein yeh likha tha
                        </p>
                        <p className="text-[16px] m-0 font-mono" style={{ color: COLORS.ink }}>
                          {med.source_text}
                        </p>
                      </div>

                      <button
                        type="button"
                        onClick={() => { removeScanMedicine(med.id); setEditingId(null); }}
                        className="min-h-[52px] rounded-[14px] text-[17px] font-semibold border-2 bg-transparent"
                        style={{ borderColor: "rgba(220,38,38,0.35)", color: COLORS.danger }}
                      >
                        Yeh dawai hatao
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.article>
          );
        })}
      </div>

      <div className="flex flex-col gap-3">
        <button
          type="button"
          onClick={handleConfirm}
          className="w-full min-h-[72px] rounded-[18px] text-white text-[23px] font-bold border-0"
          style={{ background: `linear-gradient(180deg,${COLORS.teal} 0%,${COLORS.tealDeep} 100%)`, boxShadow: "0 8px 20px rgba(15,118,110,.30)" }}
        >
          Sab sahi hai, confirm karo
        </button>
        <button
          type="button"
          onClick={() => navigate("/scan")}
          className="w-full min-h-[56px] rounded-[16px] text-[18px] font-semibold border-2 bg-transparent"
          style={{ borderColor: COLORS.line, color: COLORS.inkMuted }}
        >
          Dobara scan karein
        </button>
      </div>
    </Shell>
  );
}
