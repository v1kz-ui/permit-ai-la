"use client";
import { useState } from "react";

const JARGON_DEFINITIONS: Record<string, string> = {
  "EO1": "Emergency Order 1 — expedited like-for-like rebuild pathway for fire-damaged properties",
  "EO8": "Emergency Order 8 — expanded rebuild pathway allowing up to 10% more square footage",
  "VHFHSZ": "Very High Fire Hazard Severity Zone — areas requiring additional fire safety measures",
  "VHFSZ": "Very High Fire Hazard Severity Zone — areas requiring additional fire safety measures",
  "HPOZ": "Historic Preservation Overlay Zone — areas with additional historic review requirements",
  "LADBS": "Los Angeles Dept. of Building and Safety — issues building permits and inspections",
  "DCP": "Dept. of City Planning — handles zoning, land use, and environmental review",
  "LAFD": "Los Angeles Fire Department — reviews fire and life safety compliance",
  "LADWP": "LA Dept. of Water and Power — reviews water and electrical service connections",
  "LASAN": "LA Sanitation — reviews sewer connections and waste management",
  "DOT": "Dept. of Transportation — reviews driveway access and traffic impact",
  "BOE": "Bureau of Engineering — reviews grading, drainage, and public works",
  "APN": "Assessor Parcel Number — unique ID for every property parcel in LA County",
  "CofO": "Certificate of Occupancy — final approval that a building is safe to inhabit",
  "PCIS": "Plan Check and Inspection System — LADBS's permit tracking database",
};

interface Props {
  term: string;
  children?: React.ReactNode;
}

export default function JargonTip({ term, children }: Props) {
  const [open, setOpen] = useState(false);
  const definition = JARGON_DEFINITIONS[term] || term;

  return (
    <span className="relative inline-flex items-center">
      <button
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onClick={() => setOpen(!open)}
        className="inline-flex items-center gap-0.5 border-b border-dashed border-slate-400 cursor-help text-inherit font-inherit"
        aria-label={`${term}: ${definition}`}
      >
        {children || term}
        <svg className="w-3 h-3 text-slate-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </button>
      {open && (
        <span className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 bg-slate-900 text-white text-xs rounded-lg px-3 py-2 shadow-xl pointer-events-none" role="tooltip">
          <strong className="text-amber-300">{term}</strong>: {definition}
          <span className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-900" />
        </span>
      )}
    </span>
  );
}
