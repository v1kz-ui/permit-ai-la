"use client";
import { useEffect, useState } from "react";

interface Props {
  show: boolean;
  message?: string;
}

export default function CelebrationBanner({ show, message = "All clearances approved!" }: Props) {
  const [visible, setVisible] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (show && !dismissed) {
      setVisible(true);
    }
  }, [show, dismissed]);

  if (!visible) return null;

  return (
    <div className="relative overflow-hidden bg-gradient-to-r from-emerald-50 via-teal-50 to-emerald-50 border border-emerald-200 rounded-xl p-5 mb-6 animate-in">
      {/* CSS confetti dots */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {Array.from({ length: 20 }).map((_, i) => (
          <span
            key={i}
            className="absolute w-2 h-2 rounded-full opacity-60 animate-bounce"
            style={{
              left: `${5 + (i * 4.7) % 90}%`,
              top: `${10 + (i * 7.3) % 70}%`,
              backgroundColor: ['#10b981', '#6366f1', '#f59e0b', '#ec4899', '#3b82f6'][i % 5],
              animationDelay: `${i * 0.15}s`,
              animationDuration: `${1.2 + (i % 3) * 0.4}s`,
            }}
          />
        ))}
      </div>

      <div className="relative flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 bg-emerald-100 rounded-full">
            <svg className="w-6 h-6 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h3 className="font-semibold text-emerald-800 text-sm">{message}</h3>
            <p className="text-xs text-emerald-600 mt-0.5">
              This project is ready to proceed to the next phase.
            </p>
          </div>
        </div>
        <button
          onClick={() => { setVisible(false); setDismissed(true); }}
          className="text-emerald-400 hover:text-emerald-600 transition-colors p-1"
          aria-label="Dismiss celebration"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}
