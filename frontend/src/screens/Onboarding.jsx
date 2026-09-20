import { motion } from "framer-motion";
import { ArrowRight, HeartPulse, Sparkles } from "lucide-react";
import { useState } from "react";
import { api } from "../api.js";
import { Disclaimer } from "../components/ui.jsx";
import { useApp } from "../store.jsx";

/* Sixty seconds, three fields, then straight to the camera. No long forms:
 * every extra field is a caregiver who never finishes signing up. */
export default function Onboarding({ onDone }) {
  const { setFamilyId, setParentId, showToast, health } = useApp();
  const [form, setForm] = useState({
    parentName: "",
    parentPhone: "",
    language: "hi",
    caregiverName: "",
    caregiverPhone: "",
  });
  const [busy, setBusy] = useState(false);

  const set = (key) => (event) => setForm({ ...form, [key]: event.target.value });

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    try {
      const family = await api.createFamily(`${form.parentName || "My"} family`, {
        name: form.caregiverName,
        phone: form.caregiverPhone,
      });
      const parent = await api.addParent({
        familyId: family.familyId,
        name: form.parentName,
        phone: form.parentPhone,
        language: form.language,
      });
      setFamilyId(family.familyId);
      setParentId(parent.parentId);
      onDone?.();
    } catch (err) {
      showToast(err.message);
    } finally {
      setBusy(false);
    }
  };

  const seed = async () => {
    setBusy(true);
    try {
      const demo = await api.seedDemo();
      setFamilyId(demo.familyId);
      setParentId(demo.parentId);
      showToast(`Demo family ready: ${demo.medicines} medicines, ${demo.duplicates.length} duplicate flagged`);
      onDone?.("dashboard");
    } catch (err) {
      showToast(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-md px-5 pb-16 pt-10">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <div className="mb-8 text-center">
          <HeartPulse className="mx-auto text-teal" size={44} aria-hidden="true" />
          <h1 className="mt-3 text-3xl font-extrabold">DoseWise</h1>
          <p className="mt-2 text-ink-soft">
            Your parents take 7 pills a day from 3 doctors. DoseWise makes sure none of them is a mistake.
          </p>
        </div>

        <form onSubmit={submit} className="card space-y-4 p-6">
          <div>
            <label className="label" htmlFor="parentName">
              Parent's name
            </label>
            <input
              id="parentName"
              className="input mt-1"
              value={form.parentName}
              onChange={set("parentName")}
              placeholder="Kamla Devi"
              required
            />
          </div>

          <div>
            <label className="label" htmlFor="parentPhone">
              Parent's phone
            </label>
            <input
              id="parentPhone"
              className="input mt-1"
              value={form.parentPhone}
              onChange={set("parentPhone")}
              placeholder="+91"
              inputMode="tel"
            />
          </div>

          <div>
            <span className="label">Reminder language</span>
            <div className="mt-2 flex gap-3">
              {[
                { id: "hi", label: "हिन्दी" },
                { id: "en", label: "English" },
              ].map((option) => (
                <button
                  key={option.id}
                  type="button"
                  onClick={() => setForm({ ...form, language: option.id })}
                  className={`btn min-h-[56px] flex-1 px-4 ${
                    form.language === option.id ? "btn-primary" : "btn-ghost"
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          <hr className="border-black/5" />

          <div>
            <label className="label" htmlFor="caregiverName">
              Your name
            </label>
            <input
              id="caregiverName"
              className="input mt-1"
              value={form.caregiverName}
              onChange={set("caregiverName")}
              placeholder="You"
            />
          </div>

          <div>
            <label className="label" htmlFor="caregiverPhone">
              Your phone, for missed dose alerts
            </label>
            <input
              id="caregiverPhone"
              className="input mt-1"
              value={form.caregiverPhone}
              onChange={set("caregiverPhone")}
              placeholder="+91"
              inputMode="tel"
            />
          </div>

          <button type="submit" disabled={busy} className="btn-primary min-h-touch w-full px-6 py-4 text-lg">
            Scan first prescription
            <ArrowRight size={22} aria-hidden="true" />
          </button>
        </form>

        {/* Local only: /demo/seed lives in the dev server, not the API Lambda,
            so the button hides itself once we are pointed at real AWS. */}
        {health?.backend !== "aws" && (
          <button type="button" onClick={seed} disabled={busy} className="btn-ghost mt-4 min-h-[56px] w-full px-6">
            <Sparkles size={20} aria-hidden="true" />
            Load the demo family
          </button>
        )}

        <Disclaimer className="mt-6 text-center" />
      </motion.div>
    </div>
  );
}
