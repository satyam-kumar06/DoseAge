import { motion } from "framer-motion";
import { AlertCircle, Check, Pencil, Quote } from "lucide-react";
import { useState } from "react";
import { api } from "../api.js";
import PillArt from "../components/PillArt.jsx";
import { Disclaimer, DuplicateBanner, SlotBadge } from "../components/ui.jsx";
import { useApp } from "../store.jsx";

/* The human check screen.
 *
 * Every extracted field is shown next to the exact line it came from, so the
 * caregiver can see what the AI read rather than trusting it. Nothing is
 * saved until "Confirm all" is pressed: this screen is the safety story.
 */
const SLOTS = ["MORNING", "AFTERNOON", "NIGHT"];

export default function Review({ scan, onConfirmed }) {
  const { parentId, showToast } = useApp();
  const [meds, setMeds] = useState(scan.medicines || []);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(null);

  const update = (medId, changes) =>
    setMeds((list) => list.map((m) => (m.medId === medId ? { ...m, ...changes } : m)));

  const remove = (medId) => setMeds((list) => list.filter((m) => m.medId !== medId));

  const confirm = async () => {
    setBusy(true);
    try {
      const res = await api.confirmMeds(parentId, meds, scan.scanId);
      showToast(`${res.medicines.length} medicines saved, ${res.dosesCreated} doses scheduled`);
      onConfirmed(res);
    } catch (err) {
      showToast(err.message);
    } finally {
      setBusy(false);
    }
  };

  const lowConfidence = meds.filter((m) => m.lowConfidence).length;
  /* A prescription that never wrote "1-0-1" leaves us with no timing. Saving
     it anyway produced a medicine that silently never appeared on the parent's
     day. Ask instead, and do not let Confirm past it. */
  const needsTiming = meds.filter((m) => !m.asNeeded && !(m.slots || []).length);

  return (
    <div className="mx-auto w-full max-w-2xl px-5 pb-40 pt-8">
      <header className="mb-5">
        <h1 className="text-2xl font-extrabold">Check what we read</h1>
        <p className="mt-1 text-ink-soft">
          Nothing is saved until you confirm. {scan.doctorName && `From ${scan.doctorName}. `}
          {lowConfidence > 0 && `${lowConfidence} line${lowConfidence > 1 ? "s" : ""} need a look.`}
        </p>
      </header>

      {scan.duplicates?.length > 0 && (
        <div className="mb-6">
          <DuplicateBanner duplicates={scan.duplicates} />
        </div>
      )}

      <div className="space-y-4">
        {meds.map((med) => (
          <MedCard
            key={med.medId}
            med={med}
            editing={editing === med.medId}
            onEdit={() => setEditing(editing === med.medId ? null : med.medId)}
            onChange={(changes) => update(med.medId, changes)}
            onRemove={() => remove(med.medId)}
          />
        ))}
      </div>

      {scan.unreadableLines?.length > 0 && (
        <div className="card mt-6 p-5">
          <p className="flex items-center gap-2 font-bold">
            <AlertCircle size={20} className="text-warn" aria-hidden="true" />
            Lines we could not read
          </p>
          <ul className="mt-2 space-y-1 text-ink-soft">
            {scan.unreadableLines.map((line) => (
              <li key={line} className="font-mono text-sm">
                {line}
              </li>
            ))}
          </ul>
          <p className="mt-3 text-sm text-ink-faint">
            These were left out on purpose. Add them by hand if they are medicines.
          </p>
        </div>
      )}

      <Disclaimer className="mt-6" />

      {/* Above the bottom bar, never behind it: this button is the only way
          forward from the review screen. */}
      <div
        className="fixed inset-x-0 z-40 border-t border-black/5 bg-cream/95 p-4 backdrop-blur"
        style={{ bottom: "var(--nav-h)" }}
      >
        <div className="mx-auto flex max-w-2xl items-center gap-3">
          <button
            type="button"
            onClick={confirm}
            disabled={busy || !meds.length || needsTiming.length > 0}
            className="btn-primary min-h-touch flex-1 px-6 py-4 text-lg"
          >
            <Check size={24} aria-hidden="true" />
            {needsTiming.length
              ? `Set timing for ${needsTiming.length} medicine${needsTiming.length > 1 ? "s" : ""}`
              : `Confirm all ${meds.length}`}
          </button>
        </div>
      </div>
    </div>
  );
}

function MedCard({ med, editing, onEdit, onChange, onRemove }) {
  const toggleSlot = (slot) => {
    const slots = med.slots?.includes(slot)
      ? med.slots.filter((s) => s !== slot)
      : [...(med.slots || []), slot];
    onChange({ slots });
  };

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={`card p-5 ${med.lowConfidence ? "border-warn/40 bg-warn/[.04]" : ""}`}
    >
      <div className="flex items-start gap-4">
        <PillArt brand={med.brand} form={med.form} size={64} />

        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h2 className="truncate text-lg font-bold">{med.brand}</h2>
              <p className="text-ink-soft">
                {med.salts?.length ? med.salts.join(" + ") : "salt not matched"}
                {med.strength ? ` · ${med.strength}` : ""}
              </p>
            </div>
            <button type="button" onClick={onEdit} className="btn-ghost min-h-[44px] px-3 py-2 text-sm">
              <Pencil size={16} aria-hidden="true" />
              {editing ? "Done" : "Edit"}
            </button>
          </div>

          {!med.asNeeded && !(med.slots || []).length && (
            <div className="mt-3 rounded-xl border border-warn/40 bg-warn/[.07] p-3">
              <p className="flex items-center gap-2 font-bold text-ink">
                <AlertCircle size={18} className="text-warn" aria-hidden="true" />
                When should this be taken?
              </p>
              <p className="mt-1 text-sm text-ink-soft">
                The prescription did not say. Pick the times, or mark it as only when needed.
              </p>

              <div className="mt-3 flex gap-2">
                {SLOTS.map((slot) => (
                  <button
                    key={slot}
                    type="button"
                    onClick={() => toggleSlot(slot)}
                    className="btn-ghost min-h-[52px] flex-1 px-2 text-sm"
                  >
                    {slot[0] + slot.slice(1).toLowerCase()}
                  </button>
                ))}
              </div>

              <div className="mt-3 flex items-end gap-3">
                <label className="block flex-1">
                  <span className="label">How many at a time</span>
                  <select
                    className="input mt-1"
                    value={med.countPerDose || 1}
                    onChange={(e) => onChange({ countPerDose: Number(e.target.value) })}
                  >
                    {[1, 2, 3, 4].map((n) => (
                      <option key={n} value={n}>
                        {n}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  type="button"
                  onClick={() => onChange({ asNeeded: true, slots: [] })}
                  className="btn-ghost min-h-[52px] px-4 text-sm"
                >
                  Only when needed
                </button>
              </div>
            </div>
          )}

          <div className="mt-3 flex flex-wrap items-center gap-2">
            {(med.slots || []).map((slot) => (
              <SlotBadge key={slot} slot={slot} />
            ))}
            <span className="chip bg-black/5 text-ink-soft">{med.food} food</span>
            {med.durationDays > 0 && (
              <span className="chip bg-black/5 text-ink-soft">{med.durationDays} days</span>
            )}
            {med.lowConfidence && (
              <span className="chip bg-warn/15 text-warn">
                <AlertCircle size={14} aria-hidden="true" />
                Please check
              </span>
            )}
            {!med.saltMatched && (
              <span className="chip bg-black/5 text-ink-soft">unverified salt</span>
            )}
            {med.asNeeded && (
              <button
                type="button"
                onClick={() => onChange({ asNeeded: false })}
                className="chip bg-teal-soft text-teal-deep"
              >
                only when needed · change
              </button>
            )}
            {(med.slots || []).length > 0 && (med.countPerDose || 1) > 1 && (
              <span className="chip bg-black/5 text-ink-soft">{med.countPerDose} at a time</span>
            )}
          </div>

          {/* Trust by showing the source. */}
          {med.sourceText && (
            <p className="mt-3 flex items-start gap-2 rounded-xl bg-black/[.03] p-3 font-mono text-sm text-ink-soft">
              <Quote size={14} className="mt-1 shrink-0" aria-hidden="true" />
              {med.sourceText}
            </p>
          )}

          {editing && (
            <div className="mt-4 space-y-3 border-t border-black/5 pt-4">
              <div className="grid grid-cols-2 gap-3">
                <label className="block">
                  <span className="label">Brand</span>
                  <input
                    className="input mt-1"
                    value={med.brand}
                    onChange={(e) => onChange({ brand: e.target.value })}
                  />
                </label>
                <label className="block">
                  <span className="label">Strength</span>
                  <input
                    className="input mt-1"
                    value={med.strength || ""}
                    onChange={(e) => onChange({ strength: e.target.value })}
                  />
                </label>
              </div>

              <label className="block">
                <span className="label">Salt, if we could not match it</span>
                <input
                  className="input mt-1"
                  value={(med.salts || []).join(", ")}
                  onChange={(e) =>
                    onChange({
                      salts: e.target.value
                        .split(",")
                        .map((s) => s.trim())
                        .filter(Boolean),
                      saltsManual: true,
                    })
                  }
                  placeholder="Paracetamol"
                />
              </label>

              <div>
                <span className="label">Timing</span>
                <div className="mt-2 flex gap-2">
                  {SLOTS.map((slot) => (
                    <button
                      key={slot}
                      type="button"
                      onClick={() => toggleSlot(slot)}
                      className={`btn min-h-[52px] flex-1 px-3 text-sm ${
                        med.slots?.includes(slot) ? "btn-primary" : "btn-ghost"
                      }`}
                    >
                      {slot[0] + slot.slice(1).toLowerCase()}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <label className="block">
                  <span className="label">Food</span>
                  <select
                    className="input mt-1"
                    value={med.food}
                    onChange={(e) => onChange({ food: e.target.value })}
                  >
                    <option value="before">Before food</option>
                    <option value="after">After food</option>
                    <option value="any">Any time</option>
                  </select>
                </label>
                <label className="block">
                  <span className="label">Days</span>
                  <input
                    type="number"
                    min="0"
                    className="input mt-1"
                    value={med.durationDays || 0}
                    onChange={(e) => onChange({ durationDays: Number(e.target.value) })}
                  />
                </label>
              </div>

              <button type="button" onClick={onRemove} className="btn-ghost min-h-[48px] w-full text-danger">
                Remove this medicine
              </button>
            </div>
          )}
        </div>
      </div>
    </motion.article>
  );
}
