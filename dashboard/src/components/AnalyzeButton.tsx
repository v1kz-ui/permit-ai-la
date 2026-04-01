"use client";

import { useState } from "react";
import { api } from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

interface DepartmentTimelines {
  [dept: string]: number;
}

interface AnalysisResult {
  recommended_pathway?: string;
  pathway?: string;
  estimated_days?: number;
  timeline?: {
    total_days?: number;
    total_predicted_days?: number;
    phases?: Array<{ name: string; days: number }>;
    department_timelines?: DepartmentTimelines;
  };
  department_timelines?: DepartmentTimelines;
  bottlenecks?: Array<{ description?: string; department?: string }>;
  conflicts?: Array<{ description?: string; type?: string }>;
  address?: string;
  original_sqft?: number;
  proposed_sqft?: number;
}

// ─── Helper ───────────────────────────────────────────────────────────────────

function getCompletionDate(totalDays: number): string {
  const date = new Date();
  date.setDate(date.getDate() + totalDays);
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

// X-axis tick values: 0, 30, 60, ... up to maxDays rounded up to next 30
function buildTicks(maxDays: number): number[] {
  const ticks: number[] = [0];
  let t = 30;
  while (t <= maxDays + 30) {
    ticks.push(t);
    t += 30;
  }
  return ticks;
}

// ─── Gantt Chart ─────────────────────────────────────────────────────────────

function TimelineGantt({
  timeline,
  bottleneckDepts,
  totalDays,
}: {
  timeline: DepartmentTimelines;
  bottleneckDepts: Set<string>;
  totalDays: number;
}) {
  const entries = Object.entries(timeline);
  if (entries.length === 0) return null;

  const maxDays = Math.max(...entries.map(([, d]) => d), 1);
  const longestDept = entries.reduce((a, b) => (b[1] > a[1] ? b : a))[0];
  const ticks = buildTicks(maxDays);
  const axisMax = ticks[ticks.length - 1];

  return (
    <div className="mt-4">
      {/* Department rows */}
      <div className="space-y-2">
        {entries.map(([dept, days]) => {
          const isBottleneck = bottleneckDepts.has(dept);
          const isCritical = dept === longestDept;
          const widthPct = (days / axisMax) * 100;

          return (
            <div key={dept} className="flex items-center gap-3">
              {/* Label */}
              <div className="w-36 text-xs text-gray-700 truncate text-right shrink-0">
                {dept}
              </div>

              {/* Bar track */}
              <div className="flex-1 relative h-7 bg-gray-100 rounded overflow-hidden">
                <div
                  className={`h-full rounded flex items-center px-2 transition-all duration-500
                    ${isBottleneck ? "bg-red-400" : "bg-emerald-400"}`}
                  style={{ width: `${widthPct}%`, minWidth: "2px" }}
                >
                  {widthPct > 15 && (
                    <span className="text-xs text-white font-medium truncate">
                      {dept} · {days}d
                    </span>
                  )}
                </div>

                {/* badges outside bar when bar is short */}
                {widthPct <= 15 && (
                  <span
                    className="absolute left-1 top-1/2 -translate-y-1/2 text-xs text-gray-600 ml-1"
                    style={{ left: `${widthPct + 1}%` }}
                  >
                    {days}d
                  </span>
                )}
              </div>

              {/* Right badges */}
              <div className="flex items-center gap-1 w-28 shrink-0">
                {isCritical && (
                  <span className="text-xs bg-purple-100 text-purple-700 border border-purple-300 rounded-full px-2 py-0.5 whitespace-nowrap">
                    Critical Path
                  </span>
                )}
                {isBottleneck && (
                  <span className="flex items-center gap-1 text-xs text-red-600 font-medium whitespace-nowrap">
                    <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse inline-block" />
                    Bottleneck
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* X-axis */}
      <div className="flex mt-1 pl-[148px] pr-[116px]">
        <div className="flex-1 relative h-4">
          {ticks.map((tick) => (
            <span
              key={tick}
              className="absolute text-xs text-gray-400"
              style={{
                left: `${(tick / axisMax) * 100}%`,
                transform: "translateX(-50%)",
              }}
            >
              {tick}
            </span>
          ))}
        </div>
      </div>
      <p className="text-xs text-gray-400 pl-[148px] mt-0.5">Days</p>

      {/* Total duration */}
      <div className="mt-4 pt-3 border-t flex items-center justify-between text-sm">
        <span className="text-gray-600 font-medium">
          Total estimated duration:
          <span className="ml-2 font-bold text-gray-900">{totalDays} days</span>
        </span>
        <span className="text-gray-500">
          Estimated completion:{" "}
          <span className="font-semibold text-gray-700">
            {getCompletionDate(totalDays)}
          </span>
        </span>
      </div>
    </div>
  );
}

// ─── What-if Modal ────────────────────────────────────────────────────────────

function WhatIfModal({
  project,
  onClose,
}: {
  project: { address?: string; original_sqft?: number; proposed_sqft?: number };
  onClose: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [address, setAddress] = useState(project.address || "");
  const [origSqft, setOrigSqft] = useState(String(project.original_sqft || ""));
  const [propSqft, setPropSqft] = useState(String(project.proposed_sqft || ""));

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.pathfinder.whatIf({
        address,
        original_sqft: origSqft ? Number(origSqft) : undefined,
        proposed_sqft: propSqft ? Number(propSqft) : undefined,
      });
      setResult(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">What-if Scenario</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
          >
            ×
          </button>
        </div>

        <div className="space-y-3 mb-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Address</label>
            <input
              className="w-full border rounded px-3 py-2 text-sm"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="Project address"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Original Sq Ft
              </label>
              <input
                type="number"
                className="w-full border rounded px-3 py-2 text-sm"
                value={origSqft}
                onChange={(e) => setOrigSqft(e.target.value)}
                placeholder="e.g. 1200"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Proposed Sq Ft
              </label>
              <input
                type="number"
                className="w-full border rounded px-3 py-2 text-sm"
                value={propSqft}
                onChange={(e) => setPropSqft(e.target.value)}
                placeholder="e.g. 2400"
              />
            </div>
          </div>
        </div>

        {error && (
          <p className="text-red-600 text-sm mb-3 bg-red-50 p-2 rounded">
            {error}
          </p>
        )}

        {result && (
          <div className="mb-4 bg-gray-50 rounded p-3 text-sm space-y-1">
            <p>
              <span className="text-gray-500">Pathway:</span>{" "}
              <span className="font-medium capitalize">
                {result.recommended_pathway || result.pathway || "—"}
              </span>
            </p>
            <p>
              <span className="text-gray-500">Estimated Days:</span>{" "}
              <span className="font-medium">
                {result.estimated_days ||
                  result.timeline?.total_days ||
                  result.timeline?.total_predicted_days ||
                  "—"}
              </span>
            </p>
            {result.summary && (
              <p className="text-gray-600 mt-1">{result.summary}</p>
            )}
          </div>
        )}

        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm border rounded hover:bg-gray-50"
          >
            Close
          </button>
          <button
            onClick={run}
            disabled={loading || !address}
            className="px-4 py-2 text-sm bg-primary-600 text-white rounded hover:bg-primary-700 disabled:opacity-50"
          >
            {loading ? "Running…" : "Run Scenario"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function AnalyzeButton({
  projectId,
  project,
}: {
  projectId: string;
  project?: { address?: string; original_sqft?: number; proposed_sqft?: number };
}) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showWhatIf, setShowWhatIf] = useState(false);

  async function runAnalysis() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.pathfinder.analyze(projectId);
      setResult(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // Resolve department timelines from multiple possible shapes
  const deptTimelines: DepartmentTimelines =
    result?.timeline?.department_timelines ||
    result?.department_timelines ||
    {};

  const totalDays: number =
    result?.estimated_days ||
    result?.timeline?.total_days ||
    result?.timeline?.total_predicted_days ||
    0;

  const bottleneckDepts = new Set<string>(
    (result?.bottlenecks || [])
      .map((b) => b.department)
      .filter(Boolean) as string[]
  );

  const hasDeptTimelines = Object.keys(deptTimelines).length > 0;

  return (
    <div>
      <button
        onClick={runAnalysis}
        disabled={loading}
        className="px-4 py-2 bg-primary-600 text-white rounded hover:bg-primary-700 disabled:opacity-50 text-sm font-medium"
      >
        {loading ? "Analyzing…" : "Run PathfinderAI Analysis"}
      </button>

      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {error}
        </div>
      )}

      {result && (
        <div className="mt-4 space-y-4">
          {/* Summary */}
          <div className="bg-white rounded-lg shadow p-6">
            <h4 className="font-semibold mb-3">Analysis Results</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-gray-500">Recommended Pathway</p>
                <p className="font-medium capitalize">
                  {result.recommended_pathway || result.pathway || "—"}
                </p>
              </div>
              <div>
                <p className="text-gray-500">Estimated Timeline</p>
                <p className="font-medium">{totalDays || "—"} days</p>
              </div>
            </div>
          </div>

          {/* Bottlenecks */}
          {result.bottlenecks && result.bottlenecks.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h4 className="font-semibold mb-3">Bottlenecks</h4>
              <ul className="space-y-2">
                {result.bottlenecks.map((b, i) => (
                  <li
                    key={i}
                    className="text-sm border-l-4 border-red-400 pl-3 py-1"
                  >
                    {b.description || b.department || JSON.stringify(b)}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Conflicts */}
          {result.conflicts && result.conflicts.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h4 className="font-semibold mb-3">Conflicts</h4>
              <ul className="space-y-2">
                {result.conflicts.map((c, i) => (
                  <li
                    key={i}
                    className="text-sm border-l-4 border-yellow-400 pl-3 py-1"
                  >
                    {c.description || c.type || JSON.stringify(c)}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Timeline Gantt */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-1">
              <h4 className="font-semibold">Timeline Prediction</h4>
              <button
                onClick={() => setShowWhatIf(true)}
                className="text-xs px-3 py-1.5 border border-primary-500 text-primary-600 rounded hover:bg-primary-50 transition-colors"
              >
                What-if Scenarios
              </button>
            </div>

            {hasDeptTimelines ? (
              <TimelineGantt
                timeline={deptTimelines}
                bottleneckDepts={bottleneckDepts}
                totalDays={totalDays}
              />
            ) : result.timeline?.phases ? (
              // Fallback: phase-based bar chart
              <div className="space-y-2 mt-3">
                {result.timeline.phases.map((phase, i) => (
                  <div key={i} className="flex items-center gap-3 text-sm">
                    <span className="w-32 text-gray-600 truncate">{phase.name}</span>
                    <div className="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
                      <div
                        className="bg-primary-500 h-full rounded-full"
                        style={{
                          width: `${Math.min(
                            100,
                            ((phase.days || 0) / (result.timeline!.total_days || 1)) * 100
                          )}%`,
                        }}
                      />
                    </div>
                    <span className="w-16 text-right text-gray-500">{phase.days}d</span>
                  </div>
                ))}
                {totalDays > 0 && (
                  <p className="text-xs text-gray-500 pt-2">
                    Estimated completion: {getCompletionDate(totalDays)}
                  </p>
                )}
              </div>
            ) : (
              <p className="text-gray-400 text-sm mt-3">
                Timeline visualization placeholder — detailed phase data not available
              </p>
            )}
          </div>
        </div>
      )}

      {showWhatIf && (
        <WhatIfModal
          project={project || { address: result?.address }}
          onClose={() => setShowWhatIf(false)}
        />
      )}
    </div>
  );
}
