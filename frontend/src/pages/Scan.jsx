import React, { useRef, useEffect } from "react";
import { useNavigate } from "react-router";
import { motion, AnimatePresence } from "framer-motion";
import Shell from "../components/Shell";
import BottomNav from "../components/BottomNav";
import { CameraIcon } from "../components/icons/Icons";
import { useDoseWise } from "../store/DoseWiseStore";
import { COLORS } from "../constants/theme";

const STAGES = {
  uploading: "Photo bhej rahe hain...",
  reading: "Doctor ki handwriting padh rahe hain...",
};

export default function Scan() {
  const navigate = useNavigate();
  const inputRef = useRef(null);
  const { runScan, scanStage, previewUrl, resetScan } = useDoseWise();

  // As soon as the pipeline finishes, hand the caregiver to the review screen.
  useEffect(() => {
    if (scanStage === "done") {
      const t = window.setTimeout(() => navigate("/review"), 600);
      return () => window.clearTimeout(t);
    }
  }, [scanStage, navigate]);

  const busy = scanStage === "uploading" || scanStage === "reading";

  return (
    <Shell bottomNav>
      <header>
        <h1 className="text-[30px] font-bold m-0 tracking-tight" style={{ color: COLORS.ink }}>
          Prescription scan karein
        </h1>
        <p className="text-[17px] mt-2 m-0 leading-snug" style={{ color: COLORS.inkMuted }}>
          Parchi ko seedha rakhein aur poori frame ke andar laayein. Printed ya handwritten,
          dono chalega.
        </p>
      </header>

      {/* Capture area with guide frame */}
      <div
        className="relative rounded-[22px] overflow-hidden flex items-center justify-center"
        style={{ aspectRatio: "3 / 4", background: previewUrl ? "#000" : "#EFEAE1", border: `2px dashed ${busy ? COLORS.teal : COLORS.line}` }}
      >
        {previewUrl ? (
          <img src={previewUrl} alt="Aapki prescription" className="w-full h-full object-contain" />
        ) : (
          <div className="flex flex-col items-center gap-3 px-8 text-center">
            <CameraIcon color={COLORS.inkMuted} size={46} />
            <p className="text-[17px] m-0" style={{ color: COLORS.inkMuted }}>
              Abhi tak koi photo nahi
            </p>
          </div>
        )}

        {/* Corner guide marks */}
        {!previewUrl && (
          <>
            {[
              "top-5 left-5 border-t-4 border-l-4 rounded-tl-lg",
              "top-5 right-5 border-t-4 border-r-4 rounded-tr-lg",
              "bottom-5 left-5 border-b-4 border-l-4 rounded-bl-lg",
              "bottom-5 right-5 border-b-4 border-r-4 rounded-br-lg",
            ].map((cls) => (
              <span key={cls} className={`absolute w-10 h-10 ${cls}`} style={{ borderColor: COLORS.teal, opacity: 0.45 }} />
            ))}
          </>
        )}

        {/* Scanning sweep: one deliberate motion, only while the pipeline runs */}
        <AnimatePresence>
          {busy && (
            <motion.div
              className="absolute inset-0"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              style={{ background: "rgba(15,118,110,0.18)" }}
            >
              <motion.span
                className="absolute left-0 right-0 h-[3px]"
                style={{ background: "linear-gradient(90deg, transparent, #0F766E, transparent)", boxShadow: "0 0 18px #0F766E" }}
                initial={{ top: "8%" }}
                animate={{ top: ["8%", "92%", "8%"] }}
                transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Status line */}
      <AnimatePresence mode="wait">
        {busy && (
          <motion.div
            key={scanStage}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            className="flex items-center justify-center gap-3 rounded-[16px] px-4 py-4"
            style={{ background: COLORS.surface, boxShadow: "0 6px 20px rgba(41,37,36,0.06)" }}
            aria-live="polite"
          >
            <motion.span
              className="w-5 h-5 rounded-full border-[3px]"
              style={{ borderColor: COLORS.track, borderTopColor: COLORS.teal }}
              animate={{ rotate: 360 }}
              transition={{ duration: 0.9, repeat: Infinity, ease: "linear" }}
            />
            <span className="text-[18px] font-semibold" style={{ color: COLORS.ink }}>
              {STAGES[scanStage]}
            </span>
          </motion.div>
        )}

        {scanStage === "done" && (
          <motion.div
            key="done"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center text-[18px] font-semibold"
            style={{ color: COLORS.success }}
          >
            Padh liya. Ab aap check kar lijiye.
          </motion.div>
        )}
      </AnimatePresence>

      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) runScan(file);
        }}
      />

      <div className="flex flex-col gap-3">
        <button
          type="button"
          disabled={busy}
          onClick={() => inputRef.current?.click()}
          className="w-full min-h-[72px] rounded-[18px] text-white text-[24px] font-bold flex items-center justify-center gap-3 border-0"
          style={{
            background: `linear-gradient(180deg,${COLORS.teal} 0%,${COLORS.tealDeep} 100%)`,
            boxShadow: "0 8px 20px rgba(15,118,110,.30)",
            opacity: busy ? 0.55 : 1,
          }}
        >
          <CameraIcon color="#fff" size={28} />
          {previewUrl ? "Dobara photo lo" : "Photo lo"}
        </button>

        {/* Lets you rehearse the demo without a real prescription in hand */}
        <button
          type="button"
          disabled={busy}
          onClick={() => runScan(null)}
          className="w-full min-h-[56px] rounded-[16px] text-[18px] font-semibold border-2 bg-transparent"
          style={{ borderColor: COLORS.line, color: COLORS.inkMuted }}
        >
          Sample prescription use karein
        </button>

        {previewUrl && !busy && (
          <button
            type="button"
            onClick={resetScan}
            className="text-[16px] font-semibold underline bg-transparent border-0 mx-auto"
            style={{ color: COLORS.inkMuted }}
          >
            Photo hatao
          </button>
        )}
      </div>

      <BottomNav />
    </Shell>
  );
}
