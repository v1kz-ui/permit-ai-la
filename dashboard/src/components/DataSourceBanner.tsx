"use client";

interface Props {
  source: "live" | "mock";
  timestamp?: number;
}

export default function DataSourceBanner({ source, timestamp }: Props) {
  if (source === "live") return null;

  const timeStr = timestamp
    ? new Date(timestamp).toLocaleTimeString("en-US", {
        hour: "numeric",
        minute: "2-digit",
      })
    : null;

  return (
    <div
      className="bg-amber-50 border-b border-amber-200 px-6 py-3 flex items-center gap-3 text-sm"
      role="alert"
      aria-live="polite"
    >
      <svg
        className="w-4 h-4 text-amber-500 flex-shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
      <p className="text-amber-800">
        <strong>Showing cached data</strong> — live connection unavailable
        {timeStr ? `. Last attempted at ${timeStr}` : ""}.{" "}
        <span className="font-normal">Data shown may not reflect current status.</span>
      </p>
    </div>
  );
}
