"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, Suspense } from "react";

const statuses = [
  { value: "", label: "All Statuses" },
  { value: "intake", label: "Intake" },
  { value: "in_review", label: "In Review" },
  { value: "approved", label: "Approved" },
  { value: "issued", label: "Issued" },
  { value: "denied", label: "Denied" },
];

const pathways = [
  { value: "", label: "All Pathways" },
  { value: "standard", label: "Standard" },
  { value: "eo1", label: "EO1" },
  { value: "eo8", label: "EO8" },
  { value: "coastal", label: "Coastal" },
  { value: "hillside", label: "Hillside" },
];

function FiltersInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const updateFilter = useCallback(
    (key: string, value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
      params.delete("page");
      router.push(`/projects?${params.toString()}`);
    },
    [router, searchParams]
  );

  const clearFilters = useCallback(() => {
    router.push("/projects");
  }, [router]);

  const hasActiveFilters = searchParams.get("status") || searchParams.get("pathway");

  return (
    <div className="flex items-center gap-3 flex-wrap">
      <select
        className="select w-auto"
        value={searchParams.get("status") || ""}
        onChange={(e) => updateFilter("status", e.target.value)}
      >
        {statuses.map((s) => (
          <option key={s.value} value={s.value}>{s.label}</option>
        ))}
      </select>
      <select
        className="select w-auto"
        value={searchParams.get("pathway") || ""}
        onChange={(e) => updateFilter("pathway", e.target.value)}
      >
        {pathways.map((p) => (
          <option key={p.value} value={p.value}>{p.label}</option>
        ))}
      </select>
      {hasActiveFilters && (
        <button
          onClick={clearFilters}
          className="text-xs text-slate-500 hover:text-red-600 transition-colors flex items-center gap-1"
        >
          &#10005; Clear
        </button>
      )}
    </div>
  );
}

export default function ProjectsFilters() {
  return (
    <Suspense fallback={<div className="flex gap-3"><div className="h-10 w-36 bg-slate-100 rounded-xl animate-pulse" /><div className="h-10 w-36 bg-slate-100 rounded-xl animate-pulse" /></div>}>
      <FiltersInner />
    </Suspense>
  );
}
