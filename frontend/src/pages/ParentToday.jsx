import { useState } from "react";
import {
  Volume2,
  Sun,
  CloudSun,
  Moon,
  Check,
} from "lucide-react";

import todayData from "../mocks/today.json";
import MedicineCard from "../components/MedicineCard";

function ParentToday() {
  const [taken, setTaken] = useState(false);

  const getSlotIcon = (slotName) => {
    if (slotName === "morning") {
      return <Sun size={28} />;
    }

    if (slotName === "afternoon") {
      return <CloudSun size={28} />;
    }

    return <Moon size={28} />;
  };

  return (
    <div className="min-h-screen bg-[#FAF7F2] px-5 py-8">
      
      {/* Greeting */}
      <div className="mx-auto max-w-2xl">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              Namaste {todayData.parent.name}
            </h1>

            <p className="mt-1 text-lg text-gray-600">
              Aaj ki dawai
            </p>
          </div>

          <button
            aria-label="Dawai sunaye"
            className="flex h-16 w-16 items-center justify-center rounded-full bg-[#0F766E] text-white"
          >
            <Volume2 size={30} />
          </button>
        </div>

        {/* Medicine slots */}
        <div className="mt-8 space-y-5">
          {todayData.slots.map((slot) => {
            const isMorning = slot.name === "morning";

            return (
              <div
                key={slot.name}
                className={`rounded-3xl p-5 shadow-sm ${
                  isMorning
                    ? "bg-[#FFF4C2]"
                    : slot.name === "afternoon"
                    ? "bg-[#FFE1C4]"
                    : "bg-[#E4E1FF]"
                }`}
              >
                {/* Slot header */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {getSlotIcon(slot.name)}

                    <div>
                      <h2 className="text-2xl font-bold capitalize">
                        {slot.name}
                      </h2>

                      <p className="text-lg text-gray-700">
                        {slot.time}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Medicines */}
                {slot.medicines.length === 0 ? (
                  <div className="mt-5 rounded-2xl bg-white/60 p-5">
                    <p className="text-lg text-gray-600">
                      No medicine
                    </p>
                  </div>
                ) : (
                  <div className="mt-5 space-y-4">
                    {slot.medicines.map((medicine) => (
                      <MedicineCard
                        key={medicine.id}
                        medicine={medicine}
                      />
                    ))}
                  </div>
                )}

                {/* Taken button only on morning for our demo */}
                {isMorning && slot.medicines.length > 0 && (
                  <div className="mt-5">
                    {!taken ? (
                      <button
                        onClick={() => setTaken(true)}
                        className="flex min-h-20 w-full items-center justify-center rounded-2xl bg-[#0F766E] text-2xl font-bold text-white shadow-md active:scale-[0.98]"
                      >
                        Le liya
                      </button>
                    ) : (
                      <div className="rounded-2xl bg-white p-6 text-center">
                        <div className="flex justify-center">
                          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-100 text-green-700">
                            <Check size={36} />
                          </div>
                        </div>

                        <h3 className="mt-4 text-2xl font-bold text-green-700">
                          Shabash!
                        </h3>

                        <p className="mt-2 text-lg text-gray-600">
                          Agli goli raat 9 baje.
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default ParentToday;