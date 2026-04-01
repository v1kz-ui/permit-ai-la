"use client";

export function SkeletonCard({ className = "" }: { className?: string }) {
  return (
    <div className={`card animate-pulse ${className}`}>
      <div className="w-10 h-10 rounded-xl bg-slate-200 mb-4" />
      <div className="h-3 bg-slate-200 rounded w-24 mb-2" />
      <div className="h-7 bg-slate-200 rounded w-16" />
    </div>
  );
}

export function SkeletonTable({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="card !p-0 overflow-hidden animate-pulse">
      <div className="bg-slate-50 px-5 py-3 border-b border-slate-100 flex gap-8">
        {Array.from({ length: cols }).map((_, i) => (
          <div key={i} className="h-3 bg-slate-200 rounded w-20" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="px-5 py-4 border-b border-slate-50 flex gap-8">
          {Array.from({ length: cols }).map((_, j) => (
            <div key={j} className="h-4 bg-slate-100 rounded" style={{ width: `${60 + Math.random() * 60}px` }} />
          ))}
        </div>
      ))}
    </div>
  );
}

export function SkeletonChart({ height = 200 }: { height?: number }) {
  return (
    <div className="card animate-pulse">
      <div className="h-4 bg-slate-200 rounded w-40 mb-4" />
      <div className="bg-slate-100 rounded-xl" style={{ height }} />
    </div>
  );
}

export function SkeletonKanban() {
  return (
    <div className="flex gap-5 animate-pulse">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="min-w-[220px] flex-1">
          <div className="h-4 bg-slate-200 rounded w-24 mb-3" />
          {Array.from({ length: 2 + i % 2 }).map((_, j) => (
            <div key={j} className="bg-white rounded-xl border border-slate-200 p-4 mb-3">
              <div className="h-4 bg-slate-100 rounded w-full mb-2" />
              <div className="h-3 bg-slate-100 rounded w-2/3 mb-2" />
              <div className="h-5 bg-slate-100 rounded w-12" />
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
