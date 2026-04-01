"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import { api } from "@/lib/api";
import Link from "next/link";

const PATHWAY_TEXT: Record<string, string> = {
  standard: "bg-slate-100 text-slate-700",
  expedited: "bg-amber-100 text-amber-700",
  emergency: "bg-red-100 text-red-700",
  eo1: "bg-violet-100 text-violet-700",
  eo8: "bg-indigo-100 text-indigo-700",
};

const SCENARIO_COLORS = [
  { accent: "border-t-indigo-500", dot: "bg-indigo-500", text: "text-indigo-700", bg: "bg-indigo-50" },
  { accent: "border-t-violet-500", dot: "bg-violet-500", text: "text-violet-700", bg: "bg-violet-50" },
  { accent: "border-t-emerald-500", dot: "bg-emerald-500", text: "text-emerald-700", bg: "bg-emerald-50" },
];

interface ScenarioResult {
  pathway?: string;
  estimated_days?: number;
  constraints?: string[];
  recommendation?: string;
}

interface Scenario {
  label: string;
  description: string;
  sqft: number;
  result: ScenarioResult | null;
  loading: boolean;
  error: string | null;
}

export default function WhatIfPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;

  const [project, setProject] = useState<any>(null);
  const [projectLoading, setProjectLoading] = useState(true);
  const [originalSqft, setOriginalSqft] = useState(1000);
  const [proposedSqft, setProposedSqft] = useState(1200);
  const [running, setRunning] = useState(false);
  const [recommendation, setRecommendation] = useState<string | null>(null);
  const [touched, setTouched] = useState<{ original: boolean; proposed: boolean }>({ original: false, proposed: false });

  const originalSqftError = touched.original && originalSqft <= 0 ? "Must be greater than 0" : null;
  const proposedSqftError = touched.proposed && proposedSqft <= 0 ? "Must be greater than 0" : null;
  const hasValidationErrors = originalSqft <= 0 || proposedSqft <= 0;

  const [scenarios, setScenarios] = useState<Scenario[]>([
    { label: "Current Plan", description: "Proposed as entered", sqft: 1200, result: null, loading: false, error: null },
    { label: "EO1 Max (10%)", description: "10% increase over original", sqft: 1100, result: null, loading: false, error: null },
    { label: "EO8 Max (50%)", description: "50% increase over original", sqft: 1500, result: null, loading: false, error: null },
  ]);

  useEffect(() => {
    if (!projectId) return;
    api.projects.get(projectId)
      .then((p) => {
        setProject(p);
        const orig = p.original_sqft || p.sqft || 1000;
        const prop = p.proposed_sqft || p.sqft || 1200;
        setOriginalSqft(orig);
        setProposedSqft(prop);
        setScenarios([
          { label: "Current Plan", description: "Proposed as entered", sqft: prop, result: null, loading: false, error: null },
          { label: "EO1 Max (10%)", description: "10% increase over original", sqft: Math.round(orig * 1.1), result: null, loading: false, error: null },
          { label: "EO8 Max (50%)", description: "50% increase over original", sqft: Math.round(orig * 1.5), result: null, loading: false, error: null },
        ]);
      })
      .catch(() => {})
      .finally(() => setProjectLoading(false));
  }, [projectId]);

  const handleRunAnalysis = useCallback(async () => {
    if (!project?.address) return;
    const address = project.address;
    const eo1 = Math.round(originalSqft * 1.1);
    const eo8 = Math.round(originalSqft * 1.5);
    const sqfts = [proposedSqft, eo1, eo8];
    const labels = ["Current Plan", "EO1 Max (10%)", "EO8 Max (50%)"];
    const descs = ["Proposed as entered", "10% increase over original", "50% increase over original"];

    setRunning(true);
    setRecommendation(null);
    setScenarios(sqfts.map((sqft, i) => ({ label: labels[i], description: descs[i], sqft, result: null, loading: true, error: null })));

    const results = await Promise.allSettled(
      sqfts.map((sqft) => api.pathfinder.whatIf({ address, original_sqft: originalSqft, proposed_sqft: sqft }))
    );

    const finalScenarios: Scenario[] = sqfts.map((sqft, i) => ({
      label: labels[i],
      description: descs[i],
      sqft,
      result: results[i].status === "fulfilled" ? (results[i] as any).value : null,
      loading: false,
      error: results[i].status === "rejected" ? "Analysis failed" : null,
    }));

    setScenarios(finalScenarios);
    setRunning(false);
    const firstRec = finalScenarios.find((s) => s.result?.recommendation);
    if (firstRec?.result?.recommendation) setRecommendation(firstRec.result.recommendation);
  }, [project, originalSqft, proposedSqft]);

  const allDays = scenarios.map((s) => s.result?.estimated_days ?? 0).filter(Boolean) as number[];
  const maxDays = allDays.length > 0 ? Math.max(...allDays) : 1;

  return (
    <div className="flex h-full min-h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        {/* Header */}
        <div className="bg-white border-b border-slate-100 px-8 py-6">
          <Link href={`/projects/${projectId}`}
            className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-indigo-600 transition-colors mb-2">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
            Back to Project
          </Link>
          <h1 className="text-2xl font-bold text-slate-900">What-if Analysis</h1>
          {project && <p className="text-sm text-slate-500 mt-0.5">{project.address}</p>}
        </div>

        {projectLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-indigo-600 border-t-transparent" />
          </div>
        ) : (
          <div className="px-8 py-8 space-y-6">
            {/* Parameters */}
            <div className="card">
              <h3 className="font-semibold text-slate-800 mb-5">Project Parameters</h3>
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Original Sq Ft</label>
                  <input type="number" min={1} max={10000} value={originalSqft}
                    onChange={(e) => { setOriginalSqft(Number(e.target.value)); setTouched((t) => ({ ...t, original: true })); }}
                    onBlur={() => setTouched((t) => ({ ...t, original: true }))}
                    className={`input ${originalSqftError ? "!border-red-400 !ring-red-100" : ""}`} />
                  {originalSqftError && <p className="mt-1 text-xs text-red-600">{originalSqftError}</p>}
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Proposed Sq Ft</label>
                  <input type="number" min={1} max={10000} value={proposedSqft}
                    onChange={(e) => { setProposedSqft(Number(e.target.value)); setTouched((t) => ({ ...t, proposed: true })); }}
                    onBlur={() => setTouched((t) => ({ ...t, proposed: true }))}
                    className={`input ${proposedSqftError ? "!border-red-400 !ring-red-100" : ""}`} />
                  {proposedSqftError && <p className="mt-1 text-xs text-red-600">{proposedSqftError}</p>}
                </div>
              </div>
              <div className="mt-4 flex items-center gap-6 bg-indigo-50 border border-indigo-100 rounded-xl px-4 py-3 text-sm">
                <div>
                  <span className="text-slate-500">EO1 Max (10%): </span>
                  <span className="font-bold text-indigo-700">{Math.round(originalSqft * 1.1).toLocaleString()} sqft</span>
                </div>
                <div className="w-px h-4 bg-indigo-200" />
                <div>
                  <span className="text-slate-500">EO8 Max (50%): </span>
                  <span className="font-bold text-violet-700">{Math.round(originalSqft * 1.5).toLocaleString()} sqft</span>
                </div>
              </div>
            </div>

            <button onClick={handleRunAnalysis} disabled={running || !project?.address || hasValidationErrors} className="btn-primary">
              {running ? (
                <>
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Running Analysis…
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Run Analysis
                </>
              )}
            </button>

            {/* Scenario cards */}
            <div className="grid grid-cols-3 gap-5">
              {scenarios.map((scenario, i) => {
                const colors = SCENARIO_COLORS[i];
                const days = scenario.result?.estimated_days ?? null;
                const barPct = days && maxDays > 0 ? Math.min(100, Math.round((days / maxDays) * 100)) : 0;
                const pathwayKey = scenario.result?.pathway || "";

                return (
                  <div key={i} className={`card border-t-4 ${colors.accent} flex flex-col`}>
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`w-2 h-2 rounded-full ${colors.dot}`} />
                      <h4 className="font-bold text-slate-900">{scenario.label}</h4>
                    </div>
                    <p className="text-xs text-slate-500 mb-3">{scenario.description}</p>
                    <p className="text-sm font-medium text-slate-600 mb-4">
                      {scenario.sqft.toLocaleString()} sqft
                    </p>

                    {scenario.loading && (
                      <div className="flex items-center justify-center py-8">
                        <div className={`animate-spin rounded-full h-6 w-6 border-2 ${colors.dot.replace("bg-", "border-")} border-t-transparent`} />
                      </div>
                    )}
                    {scenario.error && !scenario.loading && (
                      <p className="text-sm text-red-500">{scenario.error}</p>
                    )}
                    {scenario.result && !scenario.loading && (
                      <div className="flex flex-col gap-4 flex-1">
                        {scenario.result.pathway && (
                          <span className={`self-start badge ${PATHWAY_TEXT[pathwayKey] || "bg-slate-100 text-slate-700"} font-semibold`}>
                            {scenario.result.pathway}
                          </span>
                        )}
                        {days !== null && (
                          <>
                            <div>
                              <span className={`text-5xl font-black ${colors.text}`}>{days}</span>
                              <span className="text-sm text-slate-500 ml-1.5">days est.</span>
                            </div>
                            <div>
                              <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                                <div className={`h-2 ${colors.dot} rounded-full transition-all duration-700`} style={{ width: `${barPct}%` }} />
                              </div>
                              <p className="text-xs text-slate-400 mt-1">Relative to longest scenario</p>
                            </div>
                          </>
                        )}
                        {scenario.result.constraints && scenario.result.constraints.length > 0 && (
                          <div>
                            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Key Constraints</p>
                            <ul className="space-y-1.5">
                              {scenario.result.constraints.slice(0, 4).map((c, ci) => (
                                <li key={ci} className="text-xs text-slate-600 flex items-start gap-2">
                                  <span className={`mt-1 w-1.5 h-1.5 rounded-full ${colors.dot} flex-shrink-0`} />
                                  {c}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Recommendation */}
            {recommendation && (
              <div className="card border border-emerald-200 bg-emerald-50/40 animate-in">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-xl bg-emerald-100 flex items-center justify-center flex-shrink-0">
                    <svg className="w-4 h-4 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div>
                    <h4 className="font-semibold text-emerald-800 mb-1">AI Recommendation</h4>
                    <p className="text-sm text-emerald-900 leading-relaxed">{recommendation}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
