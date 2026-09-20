/* Every call to the backend goes through here.
 * VITE_API_BASE points at the deployed HTTP API; with it unset the Vite dev
 * proxy forwards /api to the local Python server, so the app runs with no
 * AWS account at all.
 */
const BASE = import.meta.env.VITE_API_BASE || "/api";

async function request(method, path, body, query) {
  const url = new URL(`${BASE}${path}`, window.location.origin);
  if (query) {
    Object.entries(query).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
    });
  }

  const res = await fetch(url.toString().replace(window.location.origin, ""), {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });

  const text = await res.text();
  let payload;
  try {
    payload = text ? JSON.parse(text) : {};
  } catch {
    payload = { error: text };
  }
  if (!res.ok) {
    const err = new Error(payload.error || `request failed (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return payload;
}

export const api = {
  health: () => request("GET", "/health"),

  createFamily: (name, caregiver) => request("POST", "/families", { name, caregiver }),
  getFamily: (familyId) => request("GET", `/families/${familyId}`),
  addParent: (payload) => request("POST", "/parents", payload),
  getParent: (parentId) => request("GET", `/parents/${parentId}`),

  uploadUrl: (parentId, contentType = "image/jpeg") =>
    request("POST", "/scans/upload-url", { parentId, contentType }),
  startScan: (scanId, parentId, fixture) =>
    request("POST", `/scans/${scanId}/start`, { parentId, fixture }),
  /* On AWS the scan runs as a Step Functions execution, so starting it
     returns READING and we poll. Locally it runs inline and the first poll
     already comes back finished, so one code path covers both. */
  awaitScan: async (scanId, parentId, { timeoutMs = 120000, everyMs = 1500 } = {}) => {
    const deadline = Date.now() + timeoutMs;
    for (;;) {
      const scan = await api.getScan(scanId, parentId);
      if (scan.status === "NEEDS_REVIEW" || scan.status === "CONFIRMED") return scan;
      if (scan.status === "FAILED") throw new Error(scan.error || "could not read that prescription");
      if (Date.now() > deadline) throw new Error("the scan is taking longer than expected");
      await new Promise((r) => setTimeout(r, everyMs));
    }
  },
  getScan: (scanId, parentId) => request("GET", `/scans/${scanId}`, null, { parentId }),
  confirmMeds: (parentId, medicines, scanId) =>
    request("POST", "/meds/confirm", { parentId, medicines, scanId }),
  listMeds: (parentId) => request("GET", `/parents/${parentId}/meds`),

  today: (parentId, date) => request("GET", `/parents/${parentId}/today`, null, { date }),
  markTaken: (parentId, date, slot, medId) =>
    request("POST", `/doses/${parentId}/taken`, { date, slot, medId }),
  undoTaken: (parentId, date, slot, medId = null) =>
    request("POST", `/doses/${parentId}/undo`, { date, slot, medId }),
  voice: (parentId, slot, date) => request("GET", `/parents/${parentId}/voice`, null, { slot, date }),

  dashboard: (parentId, days = 7) =>
    request("GET", `/parents/${parentId}/dashboard`, null, { days }),
  alerts: (parentId) => request("GET", `/parents/${parentId}/alerts`),
  markAlertRead: (parentId, sk) => request("POST", `/parents/${parentId}/alerts/read`, { sk }),
  visitCard: (parentId) => request("POST", `/parents/${parentId}/visit-card`),
  checkRefills: (parentId) => request("POST", `/parents/${parentId}/refills/check`),

  // local-only conveniences, used by the demo controls
  seedDemo: (fixture) => request("POST", "/demo/seed", fixture ? { fixture } : {}),
  escalate: (parentId, slot, waitSeconds) =>
    request("POST", "/demo/escalate", { parentId, slot, waitSeconds }),
  runs: () => request("GET", "/demo/runs"),
  outbox: () => request("GET", "/outbox"),
};

/* Uploads go straight to S3 with a presigned PUT in production; the local
   server accepts the same PUT so the camera screen has one code path. */
export async function uploadImage(upload, blob) {
  const target = upload.url.startsWith("http") ? upload.url : `${BASE}${upload.url}`;
  await fetch(target, {
    method: upload.method || "PUT",
    headers: upload.headers,
    body: blob,
  });
  return upload.key;
}

export function fileUrl(path) {
  if (!path) return null;
  return path.startsWith("http") ? path : `${BASE}${path}`;
}
