import { motion } from "framer-motion";
import { AlertCircle, Bell, FileDown, IndianRupee, Package, Pill, Play, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, fileUrl } from "../api.js";
import {
  AdherenceRing,
  CountUp,
  Disclaimer,
  DuplicateBanner,
  Empty,
  Spinner,
} from "../components/ui.jsx";
import { useApp } from "../store.jsx";

/* Caregiver Mode. Calm and informative: one ring, one timeline, three cards.
 * A missed dose is amber here too, because a child scrolling this at work
 * does not need a red screen to care. */
export default function Dashboard({ onOpenVisitCard }) {
  const { parentId, health, showToast, signOutDemo } = useApp();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!parentId) return;
    try {
      setData(await api.dashboard(parentId, 7));
      setError(null);
    } catch (err) {
      if (err.status === 404) signOutDemo();
      else setError(err);
    }
  }, [parentId, signOutDemo]);

  useEffect(() => {
    load();
  }, [load]);

  if (!parentId) return <Empty title="No parent yet" body="Add a parent to see their week." />;
  if (error)
    return (
      <Empty
        title="Could not load the dashboard"
        body={error.message}
        action={
          <button type="button" onClick={load} className="btn-primary min-h-[56px] px-6">
            Try again
          </button>
        }
      />
    );
  if (!data) return <Spinner label="Loading the week" />;

  const runEscalation = async () => {
    setBusy(true);
    try {
      const pending = data.timeline.find((d) => d.pending > 0);
      const slot = "NIGHT";
      await api.escalate(parentId, slot, 5);
      showToast("Escalation running: reminder, wait, nudge, family alert");
      setTimeout(load, 14000);
    } catch (err) {
      showToast(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-2xl px-5 pb-20 pt-8">
      <header className="mb-6 flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold">{data.parentName}</h1>
          <p className="text-ink-soft">Last 7 days</p>
        </div>
        <button type="button" onClick={load} className="btn-ghost min-h-[48px] px-4">
          <RefreshCw size={18} aria-hidden="true" />
          Refresh
        </button>
      </header>

      {data.duplicates?.length > 0 && (
        <div className="mb-6">
          <DuplicateBanner duplicates={data.duplicates} />
        </div>
      )}

      <section className="card p-6">
        <div className="flex flex-wrap items-center justify-between gap-6">
          <AdherenceRing
            value={data.adherence}
            label={
              <div>
                <p className="text-lg font-bold text-ink">{data.takenCount} taken</p>
                <p className="text-ink-soft">
                  {data.missedCount} missed · {data.pendingCount} still to come
                </p>
              </div>
            }
          />
        </div>

        <div className="mt-6 grid grid-cols-7 gap-2">
          {data.timeline.map((day) => {
            const total = day.total || 1;
            const takenPct = (day.taken / total) * 100;
            const missedPct = (day.missed / total) * 100;
            return (
              <div key={day.date} className="text-center">
                <div className="mx-auto flex h-24 w-full max-w-[38px] flex-col-reverse overflow-hidden rounded-xl bg-black/[.05]">
                  <motion.div
                    initial={{ height: 0 }}
                    animate={{ height: `${takenPct}%` }}
                    transition={{ duration: 0.6 }}
                    className="w-full bg-ok"
                  />
                  <motion.div
                    initial={{ height: 0 }}
                    animate={{ height: `${missedPct}%` }}
                    transition={{ duration: 0.6, delay: 0.1 }}
                    className="w-full bg-warn"
                  />
                </div>
                <p className="mt-2 text-xs text-ink-soft">{day.weekday}</p>
              </div>
            );
          })}
        </div>
      </section>

      <MedicinesCard medicines={data.medicines} />

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <SavingsCard savings={data.savings} />
        <RefillCard refills={data.refills} />
      </div>

      <AlertsCard alerts={data.alerts} />

      <section className="card mt-6 space-y-3 p-6">
        <h2 className="text-lg font-bold">Doctor Visit Card</h2>
        <p className="text-ink-soft">
          One page: medicines, salts, timings, adherence, flagged duplicates. The link expires in 24 hours.
        </p>
        <button type="button" onClick={onOpenVisitCard} className="btn-primary min-h-touch w-full px-6 py-4">
          <FileDown size={22} aria-hidden="true" />
          Generate the card
        </button>
      </section>

      {health && !health.sms && (
        <section className="card mt-6 space-y-3 p-6">
          <h2 className="text-lg font-bold">Try the escalation</h2>
          <p className="text-ink-soft">
            Runs the real workflow with 5 second waits: reminder, check, nudge, check, family alert, mark
            missed. With no AWS account the SMS lands in the local outbox instead of a phone.
          </p>
          <div className="flex gap-3">
            <button type="button" onClick={runEscalation} disabled={busy} className="btn-primary min-h-[56px] flex-1 px-4">
              <Play size={18} aria-hidden="true" />
              Run it
            </button>
            <button
              type="button"
              onClick={async () => {
                const box = await api.outbox();
                showToast(`${box.messages.length} messages in the outbox`);
              }}
              className="btn-ghost min-h-[56px] flex-1 px-4"
            >
              <Bell size={18} aria-hidden="true" />
              See messages
            </button>
          </div>
        </section>
      )}

      <Disclaimer className="mt-6" />
    </div>
  );
}

/* The salt behind each brand, shown plainly.
   This is the thing DoseWise actually knows that a pill box does not, and
   until it was on screen there was no way to tell a failed match from a
   working one. An unmatched medicine says so rather than going quiet. */
function MedicinesCard({ medicines = [] }) {
  if (!medicines.length) return null;
  const unmatched = medicines.filter((m) => !m.salts?.length).length;

  return (
    <section className="card mt-6 p-6">
      <h2 className="flex items-center gap-2 text-lg font-bold">
        <Pill size={20} className="text-teal" aria-hidden="true" />
        Medicines and salts
      </h2>
      <p className="mt-1 text-sm text-ink-soft">
        {medicines.length} active
        {unmatched > 0 && ` · ${unmatched} without a matched salt`}
      </p>

      <ul className="mt-4 space-y-3">
        {medicines.map((med) => (
          <li key={med.medId} className="flex items-start justify-between gap-3 border-b border-black/5 pb-3 last:border-0 last:pb-0">
            <div className="min-w-0">
              <p className="font-semibold">
                {med.brand}
                {med.strength ? <span className="text-ink-faint"> · {med.strength}</span> : null}
              </p>
              {med.salts?.length ? (
                <p className="text-sm text-teal-deep">{med.salts.join(" + ")}</p>
              ) : (
                <p className="flex items-center gap-1.5 text-sm text-warn">
                  <AlertCircle size={14} aria-hidden="true" />
                  salt not matched — add it on the review screen
                </p>
              )}
            </div>
            <div className="shrink-0 text-right text-sm text-ink-faint">
              <div>{(med.slots || []).map((s) => s[0]).join(" ") || "-"}</div>
              <div>{med.frequencyCode || ""}</div>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function SavingsCard({ savings }) {
  if (!savings || !savings.items?.length) {
    return <Empty icon={IndianRupee} title="No generic match yet" body="Add medicines to see savings." />;
  }
  return (
    <section className="card p-6">
      <h2 className="flex items-center gap-2 text-lg font-bold">
        <IndianRupee size={20} className="text-teal" aria-hidden="true" />
        Jan Aushadhi Saver
      </h2>
      <p className="mt-3 text-4xl font-extrabold text-teal">
        <CountUp value={Math.round(savings.monthlyTotal)} prefix="₹" />
      </p>
      <p className="text-ink-soft">could be saved every month</p>

      <ul className="mt-4 space-y-2">
        {savings.items.slice(0, 4).map((item) => (
          <li key={item.medId} className="flex items-baseline justify-between gap-3 text-sm">
            <span className="min-w-0">
              <strong>{item.brand}</strong>
              <div className="text-ink-faint">
                ask for: <span className="text-ink-soft">{item.generic}</span>
              </div>
              <div className="text-xs text-ink-faint">{item.salts?.join(" + ")}</div>
            </span>
            <span className="shrink-0 font-semibold text-ok">₹{Math.round(item.monthlySaving)}</span>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-xs text-ink-faint">{savings.disclaimer}</p>
    </section>
  );
}

function RefillCard({ refills }) {
  if (!refills?.length) {
    return <Empty icon={Package} title="Refill Radar" body="No strip sizes recorded yet." />;
  }
  return (
    <section className="card p-6">
      <h2 className="flex items-center gap-2 text-lg font-bold">
        <Package size={20} className="text-teal" aria-hidden="true" />
        Refill Radar
      </h2>
      <ul className="mt-4 space-y-3">
        {refills.slice(0, 5).map((refill) => (
          <li key={refill.medId} className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate font-semibold">{refill.brand}</p>
              <p className="text-sm text-ink-faint">runs out {refill.runsOutOn}</p>
            </div>
            <span className={`chip shrink-0 ${refill.warn ? "bg-warn/15 text-warn" : "bg-black/5 text-ink-soft"}`}>
              {refill.daysLeft} days
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function AlertsCard({ alerts }) {
  if (!alerts?.length) return null;
  const tone = {
    DUPLICATE: "bg-warn/10 text-warn",
    MISSED: "bg-warn/10 text-warn",
    REFILL: "bg-teal-soft text-teal-deep",
  };
  return (
    <section className="card mt-6 p-6">
      <h2 className="flex items-center gap-2 text-lg font-bold">
        <Bell size={20} className="text-teal" aria-hidden="true" />
        Alerts
      </h2>
      <ul className="mt-4 space-y-3">
        {alerts.slice(0, 8).map((alert) => (
          <li key={alert.SK} className="flex items-start gap-3">
            <span className={`chip shrink-0 ${tone[alert.alertType] || "bg-black/5"}`}>
              {alert.alertType.toLowerCase()}
            </span>
            <div className="min-w-0">
              <p className="text-ink">{alert.message}</p>
              <p className="text-xs text-ink-faint">{new Date(alert.createdAt).toLocaleString("en-IN")}</p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
