import { AnimatePresence, motion } from "framer-motion";
import { Camera, FileText, Image as ImageIcon, RefreshCw } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api, uploadImage } from "../api.js";
import { Disclaimer } from "../components/ui.jsx";
import { useApp } from "../store.jsx";

/* Camera with a guide frame, then a friendly progress state, then cards.
 * The waiting copy names what is happening ("reading the doctor's
 * handwriting") because a silent spinner on a medical app feels like a bug.
 */
const STEPS = [
  "Uploading the photo",
  "Reading the printed text",
  "Reading the doctor's handwriting",
  "Matching brands to salts",
  "Checking for duplicate salts",
];

export default function Scan({ onReviewReady }) {
  const { parentId, health, showToast } = useApp();
  const [preview, setPreview] = useState(null);
  const [step, setStep] = useState(-1);
  const [fixture, setFixture] = useState("family_demo");
  const fileInput = useRef(null);
  const timers = useRef([]);

  useEffect(() => () => timers.current.forEach(clearTimeout), []);

  const runProgress = () => {
    timers.current.forEach(clearTimeout);
    timers.current = STEPS.map((_, index) =>
      setTimeout(() => setStep(index), index * 700)
    );
  };

  const handleFile = async (file) => {
    if (!parentId) return showToast("Add a parent first");
    setPreview(URL.createObjectURL(file));
    setStep(0);
    runProgress();

    try {
      const { scanId, upload } = await api.uploadUrl(parentId, file.type || "image/jpeg");
      await uploadImage(upload, file);
      await api.startScan(scanId, parentId, fixture);
      const result = await api.awaitScan(scanId, parentId);
      timers.current.forEach(clearTimeout);
      setStep(STEPS.length);
      onReviewReady(result);
    } catch (err) {
      timers.current.forEach(clearTimeout);
      setStep(-1);
      showToast(err.message);
    }
  };

  const scanWithoutPhoto = async () => {
    if (!parentId) return showToast("Add a parent first");
    setStep(0);
    runProgress();
    try {
      const { scanId, upload } = await api.uploadUrl(parentId);
      await uploadImage(upload, new Blob(["placeholder"], { type: "image/jpeg" }));
      await api.startScan(scanId, parentId, fixture);
      const result = await api.awaitScan(scanId, parentId);
      timers.current.forEach(clearTimeout);
      setStep(STEPS.length);
      onReviewReady(result);
    } catch (err) {
      timers.current.forEach(clearTimeout);
      setStep(-1);
      showToast(err.message);
    }
  };

  const busy = step >= 0 && step < STEPS.length;

  return (
    <div className="mx-auto w-full max-w-md px-5 pb-16 pt-8">
      <h1 className="text-2xl font-extrabold">Scan a prescription</h1>
      <p className="mt-1 text-ink-soft">Printed or handwritten. One page at a time.</p>

      <div className="card mt-6 overflow-hidden">
        <div className="relative aspect-[3/4] bg-ink/[.04]">
          {preview ? (
            <img src={preview} alt="prescription preview" className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-3 text-ink-faint">
              <FileText size={44} aria-hidden="true" />
              <p className="px-8 text-center">Fit the whole page inside the frame</p>
            </div>
          )}

          {/* guide frame */}
          <div className="pointer-events-none absolute inset-6 rounded-2xl border-[3px] border-dashed border-teal/50" />

          <AnimatePresence>
            {busy && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-cream/90 px-8 text-center"
              >
                <motion.span
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1.2, repeat: Infinity, ease: "linear" }}
                  className="block h-9 w-9 rounded-full border-4 border-teal/25 border-t-teal"
                />
                <p className="text-lg font-bold">{STEPS[Math.min(step, STEPS.length - 1)]}…</p>
                <ol className="w-full space-y-1 text-left text-sm text-ink-faint">
                  {STEPS.map((label, index) => (
                    <li key={label} className={index <= step ? "text-teal" : ""}>
                      {index < step ? "✓" : index === step ? "→" : "·"} {label}
                    </li>
                  ))}
                </ol>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="space-y-3 p-5">
          <input
            ref={fileInput}
            type="file"
            accept="image/*"
            capture="environment"
            className="sr-only"
            onChange={(event) => event.target.files?.[0] && handleFile(event.target.files[0])}
          />
          <button
            type="button"
            onClick={() => fileInput.current?.click()}
            disabled={busy}
            className="btn-primary min-h-touch w-full px-6 py-4 text-lg"
          >
            <Camera size={24} aria-hidden="true" />
            Take a photo
          </button>
          <button
            type="button"
            onClick={() => fileInput.current?.click()}
            disabled={busy}
            className="btn-ghost min-h-[56px] w-full px-6"
          >
            <ImageIcon size={20} aria-hidden="true" />
            Choose from gallery
          </button>

          {health && !health.bedrock && (
            <div className="rounded-xl bg-teal-soft p-4 text-sm">
              <p className="font-semibold text-teal-deep">Offline mode</p>
              <p className="mt-1 text-ink-soft">
                No AWS credentials are configured, so the reading step replays a saved prescription.
                Everything after it is the real pipeline.
              </p>
              <label className="label mt-3 block" htmlFor="fixture">
                Sample prescription
              </label>
              <select
                id="fixture"
                className="input mt-1"
                value={fixture}
                onChange={(event) => setFixture(event.target.value)}
              >
                {(health.fixtures || ["family_demo"]).map((name) => (
                  <option key={name} value={name}>
                    {name.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={scanWithoutPhoto}
                disabled={busy}
                className="btn-ghost mt-3 min-h-[52px] w-full px-4"
              >
                <RefreshCw size={18} aria-hidden="true" />
                Run the pipeline without a photo
              </button>
            </div>
          )}
        </div>
      </div>

      <Disclaimer className="mt-6" />
    </div>
  );
}
