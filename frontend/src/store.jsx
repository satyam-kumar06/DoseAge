import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "./api.js";

const AppContext = createContext(null);
const SAVED = "dosewise.session";

function load() {
  try {
    return JSON.parse(localStorage.getItem(SAVED) || "{}");
  } catch {
    return {};
  }
}

export function AppProvider({ children }) {
  const saved = load();
  const [familyId, setFamilyId] = useState(saved.familyId || null);
  const [parentId, setParentId] = useState(saved.parentId || null);
  const [lang, setLang] = useState(saved.lang || "hi");
  const [mode, setMode] = useState(saved.mode || "caregiver");
  const [health, setHealth] = useState(null);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    localStorage.setItem(SAVED, JSON.stringify({ familyId, parentId, lang, mode }));
  }, [familyId, parentId, lang, mode]);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ ok: false }));
  }, []);

  const showToast = useCallback((message, action) => {
    setToast({ message, action, id: Date.now() });
  }, []);

  const clearToast = useCallback(() => setToast(null), []);

  const signOutDemo = useCallback(() => {
    setFamilyId(null);
    setParentId(null);
    localStorage.removeItem(SAVED);
  }, []);

  const value = useMemo(
    () => ({
      familyId,
      setFamilyId,
      parentId,
      setParentId,
      lang,
      setLang,
      toggleLang: () => setLang((l) => (l === "hi" ? "en" : "hi")),
      mode,
      setMode,
      health,
      toast,
      showToast,
      clearToast,
      signOutDemo,
    }),
    [familyId, parentId, lang, mode, health, toast, showToast, clearToast, signOutDemo]
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used inside AppProvider");
  return ctx;
}

/* Small polling hook, used by the scan screen while the pipeline runs. */
export function usePoll(fn, intervalMs, active) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!active) return undefined;
    let alive = true;
    const tick = () =>
      fn()
        .then((res) => alive && setData(res))
        .catch((err) => alive && setError(err));
    tick();
    const id = setInterval(tick, intervalMs);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [fn, intervalMs, active]);

  return { data, error };
}
