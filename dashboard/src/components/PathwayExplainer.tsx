"use client";
import { useState } from "react";

interface Props {
  pathway: string;
  isCoastal?: boolean;
  isHillside?: boolean;
  isVHFHSZ?: boolean;
  isHPOZ?: boolean;
  sqft?: number;
  pathwayConfidence?: number;
}

const PATHWAY_REASONS: Record<string, { description: string; keyFactors: string[] }> = {
  eo1: {
    description: "Emergency Order 1 — Expedited pathway for properties in fire-damaged zones, allowing faster rebuilding with streamlined clearances.",
    keyFactors: [
      "Property confirmed in LA fire damage zone",
      "Rebuilding to substantially similar footprint",
      "Eligible for expedited city department reviews",
    ],
  },
  eo8: {
    description: "Emergency Order 8 — Extended expedited pathway covering additional fire-damaged areas with modified requirements.",
    keyFactors: [
      "Property in expanded emergency zone",
      "May have additional environmental review requirements",
      "Streamlined but with conditional clearances",
    ],
  },
  standard: {
    description: "Standard building permit pathway — follows the regular LA DBS review process with full department clearances.",
    keyFactors: [
      "Property not in designated emergency zone",
      "Full plan check and department review required",
      "Standard processing timelines apply",
    ],
  },
  express: {
    description: "Express pathway — for smaller projects that qualify for over-the-counter or expedited plan check.",
    keyFactors: [
      "Project under size threshold for express processing",
      "Simplified plan review requirements",
      "Reduced number of department clearances",
    ],
  },
};

export default function PathwayExplainer({ pathway, isCoastal, isHillside, isVHFHSZ, isHPOZ, sqft, pathwayConfidence }: Props) {
  const [expanded, setExpanded] = useState(false);
  const info = PATHWAY_REASONS[pathway?.toLowerCase()] || PATHWAY_REASONS.standard;

  const overlays: string[] = [];
  if (isCoastal) overlays.push("Coastal Zone");
  if (isHillside) overlays.push("Hillside Area");
  if (isVHFHSZ) overlays.push("Very High Fire Hazard Severity Zone");
  if (isHPOZ) overlays.push("Historic Preservation Overlay Zone");

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden mb-6">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-slate-50 transition-colors text-left"
        aria-expanded={expanded}
        aria-controls="pathway-details"
      >
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm font-semibold text-slate-700">Why this pathway?</span>
        </div>
        <svg className={`w-4 h-4 text-slate-400 transition-transform ${expanded ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expanded && (
        <div id="pathway-details" className="px-5 pb-4 border-t border-slate-100 pt-3 space-y-3">
          <p className="text-sm text-slate-600">{info.description}</p>

          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Key Factors</h4>
            <ul className="space-y-1.5">
              {info.keyFactors.map((factor, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                  <svg className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                  {factor}
                </li>
              ))}
            </ul>
          </div>

          {overlays.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Zone Overlays</h4>
              <div className="flex flex-wrap gap-1.5">
                {overlays.map((o) => (
                  <span key={o} className="text-xs bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 rounded-full">{o}</span>
                ))}
              </div>
            </div>
          )}

          {sqft && (
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <span className="font-medium">Property size:</span> {sqft.toLocaleString()} sq ft
            </div>
          )}

          {pathwayConfidence != null && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">Pathway confidence:</span>
              <div className="flex-1 max-w-[120px] h-1.5 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${pathwayConfidence >= 0.8 ? "bg-emerald-500" : pathwayConfidence >= 0.5 ? "bg-amber-500" : "bg-red-500"}`}
                  style={{ width: `${Math.round(pathwayConfidence * 100)}%` }}
                />
              </div>
              <span className="text-xs font-medium text-slate-700">{Math.round(pathwayConfidence * 100)}%</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
