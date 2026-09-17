import {
  Sun,
  CloudSun,
  Moon,
  Utensils,
  AlertTriangle,
} from "lucide-react";

function MedicineCard({ medicine }) {
  const getSlotIcon = (slot) => {
    if (slot === "morning") return <Sun size={22} />;
    if (slot === "afternoon") return <CloudSun size={22} />;
    return <Moon size={22} />;
  };

  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm">
      {/* Medicine visual */}
      <div className="flex items-center gap-4">
        <div className="flex h-24 w-24 shrink-0 items-center justify-center rounded-2xl bg-gray-100 text-4xl">
          💊
        </div>

        <div>
          <h3 className="text-2xl font-bold text-gray-900">
            {medicine.brand}
          </h3>

          <p className="mt-1 text-lg text-gray-500">
            {medicine.salts.join(", ")}
          </p>

          <span className="mt-2 inline-block rounded-lg bg-gray-100 px-3 py-1 text-base font-semibold">
            {medicine.strength}
          </span>
        </div>
      </div>

      {/* Timing */}
      <div className="mt-5 flex flex-wrap gap-2">
        {medicine.slots.map((slot) => (
          <div
            key={slot}
            className="flex items-center gap-2 rounded-xl bg-gray-100 px-4 py-2 text-base font-semibold capitalize"
          >
            {getSlotIcon(slot)}
            {slot}
          </div>
        ))}
      </div>

      {/* Food */}
      {medicine.food !== "none" && (
        <div className="mt-3 flex items-center gap-2 text-lg text-gray-700">
          <Utensils size={22} />

          {medicine.food === "after"
            ? "Khane ke baad"
            : "Khane se pehle"}
        </div>
      )}

      {/* Confidence warning */}
      {medicine.confidence < 0.7 && (
        <div className="mt-4 flex items-center gap-2 rounded-xl bg-amber-50 p-3 text-[#D97706]">
          <AlertTriangle size={22} />

          <span className="font-semibold">
            Please check this medicine
          </span>
        </div>
      )}
    </div>
  );
}

export default MedicineCard;