import React, { createContext, useContext, useMemo, useState, useCallback } from "react";
import scanResult from "../mocks/scan_result.json";
import insights from "../mocks/insights.json";
import { SLOT_ORDER, SLOT_THEME, PILL_COLORS } from "../constants/theme";
import { nowLabel } from "../lib/format";

// ---------------------------------------------------------------------------
// This is the ONLY file that fakes the backend. Every screen reads from here.
// When B's API is live, replace the body of runScan / confirmMedicines /
// markSlotTaken with fetch calls. No screen has to change.
// ---------------------------------------------------------------------------

const Ctx = createContext(null);
export const useDoseWise = () => useContext(Ctx);

function buildDosesFromMeds(meds) {
  // Group confirmed medicines into the three time-of-day slots.
  return SLOT_ORDER.map((slotName) => {
    const inSlot = meds.filter((m) => m.slots.includes(slotName));
    return {
      id: `${slotName.toLowerCase()}_slot`,
      time_of_day: slotName,
      time: SLOT_THEME[slotName].time,
      status: "PENDING",
      takenAt: null,
      medicines: inSlot.map((m, i) => ({
        medId: m.id,
        brand: m.brand,
        salts: m.salts,
        instructions: m.food,
        count: 1,
        photoUrl: null,
        colorHint: PILL_COLORS[(meds.indexOf(m) + i) % PILL_COLORS.length],
      })),
    };
  }).filter((slot) => slot.medicines.length > 0);
}

export function DoseWiseProvider({ children }) {
  const [lang, setLang] = useState("en");
  const [mode, setMode] = useState(null);         // "parent" | "caregiver"
  const [scan, setScan] = useState(null);         // extraction result under review
  const [scanStage, setScanStage] = useState("idle"); // idle | uploading | reading | done
  const [meds, setMeds] = useState([]);           // confirmed medicines
  const [slots, setSlots] = useState([]);         // today's doses
  const [alerts, setAlerts] = useState([]);
  const [previewUrl, setPreviewUrl] = useState(null);

  // --- Scan ---------------------------------------------------------------
  // Fakes the S3 upload + Step Functions pipeline with realistic timing so the
  // loading states are actually exercised. TODO(B): POST /scans/upload-url,
  // PUT to S3, then poll GET /scans/{id}.
  const runScan = useCallback((file) => {
    if (file) setPreviewUrl(URL.createObjectURL(file));
    setScanStage("uploading");
    setScan(null);
    window.setTimeout(() => setScanStage("reading"), 900);
    window.setTimeout(() => {
      setScan(JSON.parse(JSON.stringify(scanResult)));
      setScanStage("done");
    }, 3200);
  }, []);

  const resetScan = useCallback(() => {
    setScan(null);
    setScanStage("idle");
    setPreviewUrl(null);
  }, []);

  const updateScanMedicine = useCallback((id, patch) => {
    setScan((prev) => ({
      ...prev,
      medicines: prev.medicines.map((m) => (m.id === id ? { ...m, ...patch } : m)),
    }));
  }, []);

  const removeScanMedicine = useCallback((id) => {
    setScan((prev) => ({ ...prev, medicines: prev.medicines.filter((m) => m.id !== id) }));
  }, []);

  // --- Confirm ------------------------------------------------------------
  // TODO(B): POST /meds/confirm. Server creates DOSE items + EventBridge rules.
  const confirmMedicines = useCallback(() => {
    if (!scan) return;
    setMeds(scan.medicines);
    setSlots(buildDosesFromMeds(scan.medicines));
    setAlerts(
      scan.alerts.map((a, i) => ({ ...a, id: `alert_${i}`, read: false, at: nowLabel() }))
    );
  }, [scan]);

  // --- Today --------------------------------------------------------------
  // TODO(B): POST /doses/{id}/taken (idempotent).
  const markSlotTaken = useCallback((slotId) => {
    setSlots((prev) =>
      prev.map((s) => (s.id === slotId ? { ...s, status: "TAKEN", takenAt: nowLabel() } : s))
    );
  }, []);

  const undoSlotTaken = useCallback((slotId) => {
    setSlots((prev) =>
      prev.map((s) => (s.id === slotId ? { ...s, status: "PENDING", takenAt: null } : s))
    );
  }, []);

  const markAlertRead = useCallback((id) => {
    setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, read: true } : a)));
  }, []);

  // Loads the same data judges will see, without needing to scan first.
  const loadDemoData = useCallback(() => {
    const demo = JSON.parse(JSON.stringify(scanResult));
    setMeds(demo.medicines);
    const built = buildDosesFromMeds(demo.medicines);
    if (built[0]) {
      built[0].status = "TAKEN";
      built[0].takenAt = "8:12";
    }
    setSlots(built);
    setAlerts(demo.alerts.map((a, i) => ({ ...a, id: `alert_${i}`, read: false, at: "9:04" })));
  }, []);

  const hasSchedule = slots.length > 0;
  const nextSlot = useMemo(() => slots.find((s) => s.status === "PENDING"), [slots]);
  const doneCount = slots.filter((s) => s.status === "TAKEN").length;

  const value = {
    lang, setLang, mode, setMode,
    scan, scanStage, previewUrl, runScan, resetScan, updateScanMedicine, removeScanMedicine,
    meds, confirmMedicines,
    slots, hasSchedule, nextSlot, doneCount, markSlotTaken, undoSlotTaken,
    alerts, markAlertRead,
    insights,
    loadDemoData,
  };

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
