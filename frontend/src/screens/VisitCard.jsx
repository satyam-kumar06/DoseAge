import { ArrowLeft, Copy, Download, Printer } from "lucide-react";
import { useEffect, useState } from "react";
import { api, fileUrl } from "../api.js";
import { Spinner } from "../components/ui.jsx";
import { useApp } from "../store.jsx";

/* A clean printable preview with a share button. The link is short lived on
 * purpose: a medicine list is not something to leave lying on the internet. */
export default function VisitCard({ onBack }) {
  const { parentId, showToast } = useApp();
  const [card, setCard] = useState(null);

  useEffect(() => {
    if (!parentId) return;
    api
      .visitCard(parentId)
      .then(setCard)
      .catch((err) => showToast(err.message));
  }, [parentId, showToast]);

  if (!card) return <Spinner label="Building the card" />;

  const link = fileUrl(card.url);

  return (
    <div className="mx-auto w-full max-w-3xl px-5 pb-16 pt-8">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <button type="button" onClick={onBack} className="btn-ghost min-h-[48px] px-4">
          <ArrowLeft size={18} aria-hidden="true" />
          Back
        </button>
        <a href={link} target="_blank" rel="noreferrer" className="btn-primary min-h-[48px] px-4">
          <Download size={18} aria-hidden="true" />
          Download PDF
        </a>
        <button
          type="button"
          onClick={() => {
            navigator.clipboard?.writeText(new URL(link, window.location.origin).toString());
            showToast("Link copied. It expires in 24 hours.");
          }}
          className="btn-ghost min-h-[48px] px-4"
        >
          <Copy size={18} aria-hidden="true" />
          Copy share link
        </button>
        <button type="button" onClick={() => window.print()} className="btn-ghost min-h-[48px] px-4">
          <Printer size={18} aria-hidden="true" />
          Print
        </button>
      </div>

      <div className="card overflow-hidden">
        <iframe
          title="Doctor visit card"
          srcDoc={card.html}
          className="h-[70vh] w-full border-0 bg-white"
        />
      </div>
    </div>
  );
}
