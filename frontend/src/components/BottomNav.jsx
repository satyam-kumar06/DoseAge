import React from "react";
import { useNavigate, useLocation } from "react-router";
import { HomeIcon, CameraIcon, ChartIcon, FileIcon } from "./icons/Icons";
import { COLORS } from "../constants/theme";

const TABS = [
  { path: "/today", label: "Aaj", Icon: HomeIcon },
  { path: "/scan", label: "Scan", Icon: CameraIcon },
  { path: "/dashboard", label: "Family", Icon: ChartIcon },
  { path: "/visit-card", label: "Doctor", Icon: FileIcon },
];

export default function BottomNav() {
  const navigate = useNavigate();
  const { pathname } = useLocation();

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 flex justify-center pointer-events-none"
      style={{ paddingBottom: "max(14px, env(safe-area-inset-bottom))" }}
    >
      <div
        className="pointer-events-auto flex items-center gap-1 rounded-[22px] px-2 py-2 mx-4"
        style={{ background: COLORS.surface, boxShadow: "0 8px 30px rgba(41,37,36,0.14)", border: `1px solid ${COLORS.line}` }}
      >
        {TABS.map(({ path, label, Icon }) => {
          const active = pathname === path;
          return (
            <button
              key={path}
              type="button"
              onClick={() => navigate(path)}
              className="flex flex-col items-center gap-[2px] rounded-2xl px-4 py-2 min-w-[74px]"
              style={{ background: active ? "rgba(15,118,110,0.10)" : "transparent" }}
              aria-current={active ? "page" : undefined}
            >
              <Icon size={24} color={active ? COLORS.teal : COLORS.inkMuted} />
              <span className="text-[13px] font-semibold" style={{ color: active ? COLORS.teal : COLORS.inkMuted }}>
                {label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
