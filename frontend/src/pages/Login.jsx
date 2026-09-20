import React, { useState } from "react";
import { useNavigate } from "react-router";
import { motion } from "framer-motion";
import Shell from "../components/Shell";
import { PillIcon } from "../components/icons/Icons";
import { useDoseWise } from "../store/DoseWiseStore";
import { COLORS } from "../constants/theme";

// TODO(B): swap the fake sign-in for Cognito (Amplify UI or hosted UI).
export default function Login() {
  const navigate = useNavigate();
  const { setMode, loadDemoData } = useDoseWise();
  const [email, setEmail] = useState("");

  function enter(mode) {
    setMode(mode);
    navigate(mode === "parent" ? "/today" : "/scan");
  }

  function enterDemo() {
    loadDemoData();
    setMode("caregiver");
    navigate("/dashboard");
  }

  return (
    <Shell>
      <div className="flex flex-col items-center text-center pt-10 pb-2">
        <motion.span
          className="w-[72px] h-[72px] rounded-[22px] flex items-center justify-center mb-5"
          style={{ background: COLORS.teal, boxShadow: "0 10px 28px rgba(15,118,110,.32)" }}
          initial={{ scale: 0.7, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 300, damping: 18 }}
        >
          <PillIcon color="#fff" size={38} />
        </motion.span>
        <h1 className="text-[34px] font-bold m-0 tracking-tight" style={{ color: COLORS.ink }}>DoseWise</h1>
        <p className="text-[18px] mt-2 mb-0 leading-snug max-w-[300px]" style={{ color: COLORS.inkMuted }}>
          Teen doctor, saat goli. Koi galti nahi.
        </p>
      </div>

      <div className="flex flex-col gap-3">
        <label className="text-[16px] font-semibold" style={{ color: COLORS.ink }}>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="aap@example.com"
            className="mt-2 w-full min-h-[64px] rounded-[16px] px-4 text-[20px] border-2 bg-white"
            style={{ borderColor: COLORS.line, color: COLORS.ink }}
          />
        </label>

        <button
          type="button"
          onClick={() => enter("caregiver")}
          className="w-full min-h-[64px] rounded-[16px] text-white text-[21px] font-bold border-0"
          style={{ background: `linear-gradient(180deg,${COLORS.teal} 0%,${COLORS.tealDeep} 100%)`, boxShadow: "0 8px 20px rgba(15,118,110,.28)" }}
        >
          Main family member hoon
        </button>

        <button
          type="button"
          onClick={() => enter("parent")}
          className="w-full min-h-[64px] rounded-[16px] text-[21px] font-bold border-2 bg-transparent"
          style={{ borderColor: COLORS.teal, color: COLORS.teal }}
        >
          Main parent hoon
        </button>
      </div>

      <button
        type="button"
        onClick={enterDemo}
        className="mx-auto text-[16px] font-semibold underline bg-transparent border-0"
        style={{ color: COLORS.inkMuted }}
      >
        Judges: demo data ke saath khol lijiye
      </button>

      <p className="text-[14px] text-center leading-snug mt-2 mb-0" style={{ color: COLORS.inkMuted }}>
        DoseWise kabhi prescription nahi badalta. Yeh sirf doctor ya pharmacist ke liye
        cheezein flag karta hai.
      </p>
    </Shell>
  );
}
