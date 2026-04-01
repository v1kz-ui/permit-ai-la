"use client";
import { useEffect, useState } from "react";

interface Props {
  message: string;
  onUndo: () => void;
  onExpire: () => void;
  duration?: number;
}

export default function UndoToast({ message, onUndo, onExpire, duration = 5000 }: Props) {
  const [remaining, setRemaining] = useState(duration);

  useEffect(() => {
    const interval = setInterval(() => {
      setRemaining((r) => {
        if (r <= 100) {
          onExpire();
          return 0;
        }
        return r - 100;
      });
    }, 100);
    return () => clearInterval(interval);
  }, [onExpire, duration]);

  const seconds = Math.ceil(remaining / 1000);

  return (
    <div
      className="fixed bottom-6 right-6 z-50 bg-slate-900 text-white rounded-xl shadow-2xl px-5 py-4 flex items-center gap-4"
      role="alert"
      aria-live="assertive"
    >
      <p className="text-sm">{message}</p>
      <button
        onClick={onUndo}
        className="text-sm font-bold text-amber-400 hover:text-amber-300 transition-colors whitespace-nowrap"
        aria-label={`Undo this action, ${seconds} seconds remaining`}
      >
        Undo ({seconds}s)
      </button>
      <div
        className="absolute bottom-0 left-0 h-0.5 bg-amber-400 rounded-b-xl transition-all duration-100"
        style={{ width: `${(remaining / duration) * 100}%` }}
        aria-hidden="true"
      />
    </div>
  );
}
