"use client";

import { useState } from "react";
import Sidebar from "@/components/Sidebar";
import { api } from "@/lib/api";
import { MOCK_PROJECTS } from "@/lib/mockData";
import { useToast } from "@/components/Toast";

const QUICK_PROJECTS = MOCK_PROJECTS.items.slice(0, 5);

interface ComplianceResult {
  rule: string;
  passed: boolean;
  message: string;
  severity: string;
}

interface ComplianceReport {
  project_id: string;
  pathway: string;
  passed: boolean;
  results: ComplianceResult[];
  warnings: string[];
  blocking_issues: string[];
}

interface SequenceResult {
  rule: string;
  passed: boolean;
  message: string;
  severity: string;
}

export default function CompliancePage() {
  const { toast } = useToast();
  const [projectSearch, setProjectSearch] = useState("");
  const [report, setReport] = useState<ComplianceReport | null>(null);
  const [sequence, setSequence] = useState<SequenceResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCheck(projectId?: string) {
    const id = projectId ?? projectSearch;
    if (!id) return;
    setLoading(true);
    setError(null);
    setReport(null);
    setSequence(null);
    try {
      const [complianceData, seqData] = await Promise.all([
        api.compliance.check(id),
        api.compliance.validateSequence(id),
      ]);
      setReport(complianceData);
      setSequence(seqData);
      toast({
        title: complianceData.passed ? "Compliance check passed" : "Compliance issues found",
        description: `${complianceData.results.length} rules checked`,
        type: "info",
      });
    } catch (e: any) {
      setError(e.message || "Failed to run compliance check");
      toast({ title: "Compliance check failed", description: e.message || "Could not complete check", type: "error" });
    } finally {
      setLoading(false);
    }
  }

  const passedCount = report?.results.filter((r) => r.passed).length ?? 0;
  const failedCount = report?.results.filter((r) => !r.passed).length ?? 0;

  return (
    <div className="flex h-full min-h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        {/* Header */}
        <div className="bg-white border-b border-slate-100 px-8 py-6">
          <h1 className="text-2xl font-bold text-slate-900">Compliance Checker</h1>
          <p className="text-sm text-slate-500 mt-0.5">Validate project pathway rules and clearance sequencing</p>
        </div>

        <div className="px-8 py-8 space-y-6 max-w-4xl">
          {/* Search */}
          <div className="card">
            <h3 className="font-semibold text-slate-800 mb-4">Select Project</h3>
            <div className="flex gap-3">
              <input
                type="text"
                value={projectSearch}
                onChange={(e) => setProjectSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCheck()}
                placeholder="Enter project ID or address..."
                className="input flex-1"
              />
              <button
                onClick={() => handleCheck()}
                disabled={loading || !projectSearch}
                className="btn-primary min-w-[160px]"
              >
                {loading ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Checking...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                    Run Check
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Quick project picker */}
          {!report && !loading && (
            <div className="card">
              <h3 className="font-semibold text-slate-800 mb-3">Quick Select</h3>
              <p className="text-xs text-slate-500 mb-4">Or choose from recent projects:</p>
              <div className="space-y-2">
                {QUICK_PROJECTS.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => { setProjectSearch(p.id); handleCheck(p.id); }}
                    className={`w-full flex items-center justify-between px-4 py-3 rounded-xl border text-sm transition-all text-left group
                      ${projectSearch === p.id
                        ? "border-indigo-400 bg-indigo-50 text-indigo-800"
                        : "border-slate-200 hover:border-indigo-300 hover:bg-slate-50 text-slate-700"
                      }`}
                  >
                    <div>
                      <p className="font-medium truncate">{p.address}</p>
                      <p className="text-xs text-slate-400 mt-0.5">ID: {p.id}</p>
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ml-3 flex-shrink-0 ${
                      p.pathway === "eo1" ? "bg-indigo-100 text-indigo-700" :
                      p.pathway === "eo8" ? "bg-violet-100 text-violet-700" :
                      p.pathway === "coastal" ? "bg-cyan-100 text-cyan-700" :
                      p.pathway === "hillside" ? "bg-amber-100 text-amber-700" :
                      "bg-slate-100 text-slate-600"
                    }`}>
                      {p.pathway?.toUpperCase()}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
              <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          {report && (
            <div className="space-y-5 animate-in">
              {/* Summary card */}
              <div className={`card border-2 ${report.passed ? "border-emerald-400 bg-emerald-50/40" : "border-red-400 bg-red-50/40"}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 rounded-2xl flex items-center justify-center text-xl ${report.passed ? "bg-emerald-100" : "bg-red-100"}`}>
                      {report.passed ? "✅" : "❌"}
                    </div>
                    <div>
                      <p className={`text-lg font-bold ${report.passed ? "text-emerald-800" : "text-red-800"}`}>
                        {report.passed ? "Compliance Check Passed" : "Compliance Check Failed"}
                      </p>
                      <p className="text-sm text-slate-600 mt-0.5">
                        Pathway: <span className="font-semibold">{report.pathway}</span> · {report.results.length} rules checked
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-center">
                      <p className="text-2xl font-bold text-emerald-600">{passedCount}</p>
                      <p className="text-xs text-slate-500">Passed</p>
                    </div>
                    <div className="w-px h-10 bg-slate-200" />
                    <div className="text-center">
                      <p className="text-2xl font-bold text-red-600">{failedCount}</p>
                      <p className="text-xs text-slate-500">Failed</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Blocking issues */}
              {report.blocking_issues.length > 0 && (
                <div className="card border border-red-200 bg-red-50/40">
                  <h4 className="font-semibold text-red-800 mb-3 flex items-center gap-2">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                    </svg>
                    Blocking Issues
                  </h4>
                  <ul className="space-y-2">
                    {report.blocking_issues.map((issue, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-red-700">
                        <span className="text-red-400 mt-0.5">•</span>
                        {issue}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Warnings */}
              {report.warnings.length > 0 && (
                <div className="card border border-amber-200 bg-amber-50/40">
                  <h4 className="font-semibold text-amber-800 mb-3 flex items-center gap-2">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    Warnings
                  </h4>
                  <ul className="space-y-2">
                    {report.warnings.map((w, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-amber-700">
                        <span className="text-amber-400 mt-0.5">•</span>
                        {w}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Rule results */}
              <div className="card">
                <h4 className="font-semibold text-slate-800 mb-4">Rule Results</h4>
                <div className="space-y-2">
                  {report.results.map((r, i) => (
                    <div
                      key={i}
                      className={`flex items-center gap-3 p-3.5 rounded-xl border ${
                        r.passed
                          ? "border-emerald-100 bg-emerald-50/40"
                          : r.severity === "blocking"
                            ? "border-red-200 bg-red-50/40"
                            : "border-amber-100 bg-amber-50/40"
                      }`}
                    >
                      <span className={`w-14 text-center px-2 py-0.5 rounded-full text-xs font-bold flex-shrink-0 ${
                        r.passed ? "bg-emerald-200 text-emerald-800" : "bg-red-200 text-red-800"
                      }`}>
                        {r.passed ? "PASS" : "FAIL"}
                      </span>
                      <span className="text-sm font-medium text-slate-800 w-40 flex-shrink-0">{r.rule}</span>
                      <span className="text-sm text-slate-600 flex-1">{r.message}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${
                        r.severity === "blocking"
                          ? "bg-red-100 text-red-700"
                          : r.severity === "warning"
                            ? "bg-amber-100 text-amber-700"
                            : "bg-slate-100 text-slate-600"
                      }`}>
                        {r.severity}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Sequence */}
              {sequence && (
                <div className={`card border ${sequence.passed ? "border-emerald-200 bg-emerald-50/40" : "border-amber-200 bg-amber-50/40"}`}>
                  <h4 className="font-semibold text-slate-800 mb-3">Clearance Sequence Validation</h4>
                  <div className="flex items-center gap-3">
                    <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                      sequence.passed ? "bg-emerald-200 text-emerald-800" : "bg-amber-200 text-amber-800"
                    }`}>
                      {sequence.passed ? "VALID" : "ISSUES"}
                    </span>
                    <span className="text-sm text-slate-600">{sequence.message}</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
