import { AnimatePresence, motion } from "framer-motion";
import { Check, Clock } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import PillArt from "../components/PillArt.jsx";
import { CheckBurst, DuplicateBanner, Empty, LangToggle, SlotBadge, Spinner, SpeakerButton } from "../components/ui.jsx";
import { FOOD_LABEL, SLOT_LABEL, speak, t } from "../i18n.js";
import { useApp } from "../store.jsx";

/* Parent Mode, Today.
 *
 * One screen, one job. The next due slot is expanded and shows pill pictures
 * with a count; everything else is collapsed. There is exactly one primary
 * action on the page, and it is enormous.
 */
export default function ParentToday({ onOpenReminder }) {
  const { parentId, lang, showToast, signOutDemo } = useApp();
  const [day, setDay] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [celebrating, setCelebrating] = useState(null);

  const refresh = useCallback(async () => {
    if (!parentId) return;
    try {
      setDay(await api.today(parentId));
      setError(null);
    } catch (err) {
      /* A saved parentId from another backend (or a reset database) 404s
         here. Spinning forever is the worst possible answer, so say what
         happened and offer the way out. */
      if (err.status === 404) signOutDemo();
      else setError(err);
    }
  }, [parentId, signOutDemo]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (!parentId) return <Empty title={t(lang, "nothingToday")} />;
  if (error)
    return (
      <Empty
        title={lang === "hi" ? "अभी जानकारी नहीं मिल पाई" : "Could not load today"}
        body={error.message}
        action={
          <button type="button" onClick={refresh} className="btn-primary min-h-[56px] px-6">
            {lang === "hi" ? "फिर कोशिश करें" : "Try again"}
          </button>
        }
      />
    );
  if (!day) return <Spinner />;

  /* One card per salt. The backend already collapses repeats, but a parent
     must never be shown the same warning twice, so the screen is the second
     line of defence against older data. */
  const duplicateAlerts = Object.values(
    (day.alerts || [])
      .filter((a) => a.alertType === "DUPLICATE")
      .reduce((seen, a) => {
        const salt = a.salt || a.message;
        if (!seen[salt]) {
          seen[salt] = {
            salt: a.salt || "",
            brands: a.brands || [],
            message: a.message,
            messageHi: a.messageHi,
          };
        }
        return seen;
      }, {})
  );

  const nextSlot = day.slots.find((s) => s.slot === day.nextSlot) || null;
  const others = day.slots.filter((s) => s !== nextSlot);
  const allDone = day.slots.length > 0 && day.slots.every((s) => s.status !== "PENDING");

  const markTaken = async (slot, medId = null) => {
    setBusy(true);
    try {
      const res = await api.markTaken(parentId, day.date, slot, medId);
      if (!medId) setCelebrating(slot);
      if (navigator.vibrate) navigator.vibrate(30);
      speak(res.praise.spoken, lang);
      showToast(t(lang, "doneToast"), {
        label: t(lang, "undo"),
        onClick: async () => {
          await api.undoTaken(parentId, day.date, slot, medId);
          refresh();
        },
      });
      setTimeout(() => setCelebrating(null), 1800);
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="parent-scope mx-auto w-full max-w-lg px-5 pb-28 pt-6">
      <header className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-parent-lg font-extrabold leading-tight">
            {t(lang, "namaste", day.parentName)}
          </h1>
          <p className="mt-1 text-ink-soft">{t(lang, "today")}</p>
        </div>
        <LangToggle />
      </header>

      {duplicateAlerts.length > 0 && (
        <div className="mb-6">
          <DuplicateBanner duplicates={duplicateAlerts} compact />
        </div>
      )}

      {allDone && (
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          className="card mb-6 flex flex-col items-center gap-4 p-8 text-center"
        >
          <CheckBurst />
          <p className="text-parent font-bold">{t(lang, "allDone")}</p>
        </motion.div>
      )}

      {!day.slots.length && <Empty title={t(lang, "nothingToday")} />}

      {nextSlot && (
        <NextSlotCard
          slot={nextSlot}
          lang={lang}
          busy={busy}
          celebrating={celebrating === nextSlot.slot}
          onTaken={() => markTaken(nextSlot.slot)}
          onTakeOne={(medId) => markTaken(nextSlot.slot, medId)}
          onRemind={() => onOpenReminder?.(nextSlot.slot)}
          parentName={day.parentName}
          parentId={parentId}
        />
      )}

      <div className="mt-6 space-y-3">
        {others.map((slot) => (
          <CollapsedSlot key={slot.slot} slot={slot} lang={lang} onTaken={() => markTaken(slot.slot)} />
        ))}
      </div>
    </div>
  );
}

function NextSlotCard({ slot, lang, busy, celebrating, onTaken, onTakeOne, onRemind, parentName, parentId }) {
  const [voice, setVoice] = useState(null);

  useEffect(() => {
    api
      .voice(parentId, slot.slot)
      .then(setVoice)
      .catch(() => setVoice(null));
  }, [parentId, slot.slot]);

  return (
    <motion.section
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="card overflow-hidden p-6"
      aria-labelledby={`slot-${slot.slot}`}
    >
      <div className="flex items-center justify-between gap-3">
        <h2 id={`slot-${slot.slot}`} className="flex items-center gap-3 text-parent-lg">
          <SlotBadge slot={slot.slot} />
        </h2>
        <span className="flex items-center gap-2 text-ink-soft">
          <Clock size={22} aria-hidden="true" />
          {slot.time}
        </span>
      </div>

      <p className="mt-4 text-parent-xl text-teal">{t(lang, "pills", slot.pillCount)}</p>

      {/* One row per medicine, each its own tick. Some parents take the
          strip one pill at a time, and marking the whole slot when only two of
          four went down is a lie the dashboard would then repeat. The big
          button below still finishes everything at once. */}
      <ul className="mt-5 space-y-3">
        {slot.doses.map((dose) => {
          const taken = dose.status === "TAKEN";
          return (
            <li key={dose.medId}>
              <button
                type="button"
                onClick={() => !taken && onTakeOne(dose.medId)}
                disabled={busy || taken}
                aria-pressed={taken}
                aria-label={`${dose.brand}${taken ? ", " + t(lang, "takenShort") : ""}`}
                className={`flex min-h-touch w-full items-center gap-4 rounded-2xl p-2 text-left
                            transition-colors disabled:opacity-100
                            ${taken ? "bg-ok/10" : "hover:bg-black/[.03] active:bg-black/[.05]"}`}
              >
                <PillArt brand={dose.brand} form={dose.form} photoUrl={dose.photoUrl} size={72} />
                <div className="min-w-0 flex-1">
                  <p className={`truncate text-parent font-bold ${taken ? "text-ink-soft line-through" : ""}`}>
                    {dose.brand}
                  </p>
                  <p className="text-ink-soft">
                    {dose.strength} · {FOOD_LABEL[dose.food]?.[lang] || ""}
                  </p>
                </div>
                <span
                  aria-hidden="true"
                  className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full border-2
                              ${taken ? "border-ok bg-ok text-white" : "border-black/15 text-transparent"}`}
                >
                  <Check size={26} strokeWidth={3} />
                </span>
              </button>
            </li>
          );
        })}
      </ul>

      <div className="mt-6 flex flex-col gap-3">
        <AnimatePresence mode="wait">
          {celebrating ? (
            <motion.div
              key="done"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="flex min-h-touch items-center justify-center gap-3 rounded-2xl bg-ok/10 py-5 text-parent-lg text-ok"
            >
              <CheckBurst />
              {t(lang, "takenShort")}
            </motion.div>
          ) : (
            <motion.button
              key="take"
              type="button"
              onClick={onTaken}
              disabled={busy}
              className="btn-parent"
              whileTap={{ scale: 0.97 }}
            >
              <Check size={34} strokeWidth={3} aria-hidden="true" />
              {t(lang, "taken")}
            </motion.button>
          )}
        </AnimatePresence>

        <div className="flex gap-3">
          <SpeakerButton text={voice?.spoken || voice?.caption || ""} audioUrl={voice?.url} big />
          <button type="button" onClick={onRemind} className="btn-ghost min-h-touch flex-1 px-4 text-parent">
            {t(lang, "later")}
          </button>
        </div>
      </div>
    </motion.section>
  );
}

function CollapsedSlot({ slot, lang, onTaken }) {
  const done = slot.status === "TAKEN";
  const missed = slot.status === "MISSED";

  return (
    <div
      className={`card flex flex-wrap items-center justify-between gap-3 p-4 ${
        missed ? "border-warn/40 bg-warn/[.06]" : ""
      }`}
    >
      <div className="flex min-w-0 flex-wrap items-center gap-3">
        <SlotBadge slot={slot.slot} />
        <span className="text-ink-soft">{t(lang, "pills", slot.pillCount)}</span>
      </div>

      {done ? (
        <span className="chip bg-ok/10 text-ok">
          <Check size={18} aria-hidden="true" />
          {t(lang, "takenShort")}
        </span>
      ) : missed ? (
        <span className="chip bg-warn/15 text-warn">{t(lang, "missed")}</span>
      ) : (
        <button type="button" onClick={onTaken} className="btn-ghost min-h-[56px] px-5 text-lg">
          {t(lang, "taken")}
        </button>
      )}
    </div>
  );
}

export { SLOT_LABEL };
