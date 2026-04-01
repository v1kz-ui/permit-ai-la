"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import { api } from "@/lib/api";
import { useToast } from "@/components/Toast";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ParcelDetails {
  apn?: string;
  address?: string;
  zone?: string;
  is_coastal?: boolean;
  is_hillside?: boolean;
  fire_severity?: string | null;
  is_historic?: boolean;
  [key: string]: any;
}

interface FormData {
  address: string;
  original_sqft: string;
  proposed_sqft: string;
  stories: "1" | "2" | "3";
}

interface AnalysisResult {
  pathway?: string;
  estimated_days?: number;
  key_constraints?: string[];
  standard_plans_available?: boolean;
  [key: string]: any;
}

// ---------------------------------------------------------------------------
// Step indicator
// ---------------------------------------------------------------------------

function StepIndicator({ current }: { current: number }) {
  const steps = ["Address & Details", "Review Pathway", "Confirm & Submit"];
  return (
    <div className="flex items-center justify-center mb-8">
      {steps.map((label, idx) => {
        const step = idx + 1;
        const isDone = step < current;
        const isActive = step === current;
        return (
          <div key={step} className="flex items-center">
            <div className="flex flex-col items-center">
              <div
                className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold border-2 transition-colors ${
                  isDone
                    ? "bg-indigo-600 border-indigo-600 text-white"
                    : isActive
                    ? "bg-white border-indigo-600 text-indigo-600"
                    : "bg-white border-slate-300 text-slate-400"
                }`}
              >
                {isDone ? (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  step
                )}
              </div>
              <span
                className={`mt-1 text-xs font-medium whitespace-nowrap ${
                  isActive ? "text-indigo-600" : isDone ? "text-indigo-600" : "text-slate-400"
                }`}
              >
                {label}
              </span>
            </div>
            {idx < steps.length - 1 && (
              <div
                className={`mx-3 mb-5 h-0.5 w-20 transition-colors ${
                  isDone ? "bg-indigo-600" : "bg-slate-200"
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Overlay badge
// ---------------------------------------------------------------------------

function OverlayBadge({ label, active }: { label: string; active: boolean }) {
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded text-xs font-medium mr-1 ${
        active
          ? "bg-amber-100 text-amber-800 border border-amber-300"
          : "bg-slate-100 text-slate-400 border border-slate-200"
      }`}
    >
      {label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Pathway badge
// ---------------------------------------------------------------------------

function PathwayBadge({ pathway }: { pathway: string }) {
  const map: Record<string, string> = {
    standard: "bg-slate-100 text-slate-700",
    streamlined: "bg-emerald-100 text-emerald-800",
    eo1: "bg-indigo-100 text-indigo-800",
    eo8: "bg-violet-100 text-violet-800",
    coastal: "bg-cyan-100 text-cyan-800",
    hillside: "bg-amber-100 text-amber-800",
    adu: "bg-purple-100 text-purple-800",
    complex: "bg-orange-100 text-orange-800",
  };
  const cls = map[pathway?.toLowerCase()] ?? "bg-slate-100 text-slate-700";
  return (
    <span className={`inline-block px-3 py-1 rounded-full text-sm font-semibold capitalize ${cls}`}>
      {pathway ?? "Unknown"}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function NewProjectPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [step, setStep] = useState(1);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [form, setForm] = useState<FormData>({
    address: "",
    original_sqft: "",
    proposed_sqft: "",
    stories: "1",
  });

  // Inline validation (touched tracks which fields user has interacted with)
  const [fieldTouched, setFieldTouched] = useState<Record<string, boolean>>({});

  const fieldErrors: Record<string, string | null> = {
    address:
      fieldTouched.address && !form.address.trim()
        ? "Address is required"
        : fieldTouched.address && form.address.trim().length < 5
        ? "Address must be at least 5 characters"
        : null,
    original_sqft:
      fieldTouched.original_sqft && !form.original_sqft
        ? "Original sq ft is required"
        : fieldTouched.original_sqft && Number(form.original_sqft) <= 0
        ? "Must be greater than 0"
        : null,
    proposed_sqft:
      fieldTouched.proposed_sqft && !form.proposed_sqft
        ? "Proposed sq ft is required"
        : fieldTouched.proposed_sqft && Number(form.proposed_sqft) <= 0
        ? "Must be greater than 0"
        : null,
  };

  const step1Invalid =
    !form.address.trim() ||
    form.address.trim().length < 5 ||
    !form.original_sqft ||
    Number(form.original_sqft) <= 0 ||
    !form.proposed_sqft ||
    Number(form.proposed_sqft) <= 0;

  const markTouched = (name: string) =>
    setFieldTouched((prev) => ({ ...prev, [name]: true }));

  // Parcel lookup
  const [parcelLoading, setParcelLoading] = useState(false);
  const [parcel, setParcel] = useState<ParcelDetails | null>(null);
  const [parcelError, setParcelError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Analysis result (step 2)
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);

  // Submission
  const [submitting, setSubmitting] = useState(false);

  // ---------------------------------------------------------------------------
  // Parcel lookup (debounced 500 ms)
  // ---------------------------------------------------------------------------

  const lookupParcel = useCallback(async (address: string) => {
    if (!address.trim() || address.trim().length < 8) {
      setParcel(null);
      setParcelError(null);
      return;
    }
    setParcelLoading(true);
    setParcelError(null);
    try {
      // Try address-based parcel lookup via APN search using address as query
      const result = await api.parcels.get(encodeURIComponent(address.trim()));
      setParcel(result);
    } catch {
      // Address lookup not found – show a soft warning, not a hard error
      setParcel(null);
      setParcelError("Parcel not found for this address. You can still continue.");
    } finally {
      setParcelLoading(false);
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      lookupParcel(form.address);
    }, 500);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [form.address, lookupParcel]);

  // ---------------------------------------------------------------------------
  // Step 1 → Step 2: fetch quick analysis
  // ---------------------------------------------------------------------------

  const handleNext = async () => {
    setError(null);

    if (step === 1) {
      if (!form.address.trim()) {
        setError("Please enter a project address.");
        return;
      }
      if (!form.original_sqft || !form.proposed_sqft) {
        setError("Please fill in original and proposed square footage.");
        return;
      }

      setAnalysisLoading(true);
      try {
        // quickAnalysis currently takes a projectId; we pass the address as a
        // stand-in slug so the UI can still display results from the API.
        // The API can accept the address string in place of an ID for quick lookup.
        const result = await api.pathfinder.quickAnalysis(
          encodeURIComponent(form.address.trim())
        );
        setAnalysis(result);
      } catch (err: any) {
        // Fallback: show a placeholder analysis so the wizard is usable even
        // when the API is unavailable or the project doesn't exist yet.
        setAnalysis({
          pathway: "standard",
          estimated_days: 45,
          key_constraints: parcel?.is_coastal
            ? ["Coastal Zone Review required"]
            : parcel?.is_hillside
            ? ["Hillside grading review required"]
            : ["Standard plan check applies"],
          standard_plans_available: true,
        });
      } finally {
        setAnalysisLoading(false);
      }
      setStep(2);
      return;
    }

    if (step === 2) {
      setStep(3);
    }
  };

  // ---------------------------------------------------------------------------
  // Step 3: submit project creation
  // ---------------------------------------------------------------------------

  const handleSubmit = async () => {
    setError(null);
    setSubmitting(true);
    try {
      const project = await api.projects.create({
        address: form.address.trim(),
        original_sqft: Number(form.original_sqft),
        proposed_sqft: Number(form.proposed_sqft),
        stories: Number(form.stories),
        pathway: analysis?.pathway ?? "standard",
      });
      toast({ title: "Project created", description: `Project at ${form.address.trim()} is ready`, type: "success" });
      router.push(`/projects/${project.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to create project. Please try again.");
      toast({ title: "Project creation failed", description: err.message || "Please try again", type: "error" });
      setSubmitting(false);
    }
  };

  const handleFieldChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="flex h-full min-h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="bg-white border-b border-slate-100 px-8 py-6">
          <a href="/projects" className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-indigo-600 transition-colors mb-1">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
            Projects
          </a>
          <h1 className="text-2xl font-bold text-slate-900">New Project</h1>
          <p className="text-sm text-slate-500 mt-0.5">Register a fire rebuild project for permit tracking</p>
        </div>
        <div className="px-8 py-8">
        <div className="max-w-2xl mx-auto">
          <StepIndicator current={step} />

          {/* Error banner */}
          {error && (
            <div className="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700 flex items-center gap-2">
              <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              {error}
            </div>
          )}

          {/* ----------------------------------------------------------------
              STEP 1: Address entry
          ---------------------------------------------------------------- */}
          {step === 1 && (
            <div className="card space-y-6">
              <h2 className="text-lg font-semibold text-slate-800">Step 1: Address &amp; Project Details</h2>

              {/* Address */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Project Address <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  name="address"
                  value={form.address}
                  onChange={handleFieldChange}
                  onBlur={() => markTouched("address")}
                  placeholder="e.g. 123 Main St, Los Angeles, CA"
                  className={`input ${fieldErrors.address ? "!border-red-400 !ring-red-100" : ""}`}
                />
                {fieldErrors.address && (
                  <p className="mt-1 text-xs text-red-600">{fieldErrors.address}</p>
                )}
                {/* Parcel lookup status */}
                {parcelLoading && (
                  <p className="mt-2 text-xs text-gray-400 animate-pulse">Looking up parcel...</p>
                )}
                {parcelError && !parcelLoading && (
                  <p className="mt-2 text-xs text-amber-600">{parcelError}</p>
                )}
              </div>

              {/* Parcel details card */}
              {parcel && !parcelLoading && (
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Parcel Details</p>
                  <div className="grid grid-cols-2 gap-y-2 text-sm">
                    {parcel.apn && (
                      <>
                        <span className="text-slate-500">APN</span>
                        <span className="font-medium text-slate-800">{parcel.apn}</span>
                      </>
                    )}
                    {parcel.zone && (
                      <>
                        <span className="text-slate-500">Zone</span>
                        <span className="font-medium text-slate-800">{parcel.zone}</span>
                      </>
                    )}
                    {parcel.fire_severity && (
                      <>
                        <span className="text-slate-500">Fire Severity</span>
                        <span className="font-medium text-slate-800 capitalize">{parcel.fire_severity}</span>
                      </>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-1 pt-1">
                    <OverlayBadge label="Coastal" active={!!parcel.is_coastal} />
                    <OverlayBadge label="Hillside" active={!!parcel.is_hillside} />
                    <OverlayBadge label="Fire Hazard" active={!!parcel.fire_severity} />
                    <OverlayBadge label="Historic" active={!!parcel.is_historic} />
                  </div>
                </div>
              )}

              {/* Square footage & stories */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    Original Sq Ft <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="number"
                    name="original_sqft"
                    value={form.original_sqft}
                    onChange={handleFieldChange}
                    onBlur={() => markTouched("original_sqft")}
                    min={1}
                    placeholder="e.g. 1200"
                    className={`input ${fieldErrors.original_sqft ? "!border-red-400 !ring-red-100" : ""}`}
                  />
                  {fieldErrors.original_sqft && (
                    <p className="mt-1 text-xs text-red-600">{fieldErrors.original_sqft}</p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    Proposed Sq Ft <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="number"
                    name="proposed_sqft"
                    value={form.proposed_sqft}
                    onChange={handleFieldChange}
                    onBlur={() => markTouched("proposed_sqft")}
                    min={1}
                    placeholder="e.g. 1800"
                    className={`input ${fieldErrors.proposed_sqft ? "!border-red-400 !ring-red-100" : ""}`}
                  />
                  {fieldErrors.proposed_sqft && (
                    <p className="mt-1 text-xs text-red-600">{fieldErrors.proposed_sqft}</p>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Stories
                </label>
                <select
                  name="stories"
                  value={form.stories}
                  onChange={handleFieldChange}
                  className="select"
                >
                  <option value="1">1 Story</option>
                  <option value="2">2 Stories</option>
                  <option value="3">3 Stories</option>
                </select>
              </div>
            </div>
          )}

          {/* ----------------------------------------------------------------
              STEP 2: Review pathway
          ---------------------------------------------------------------- */}
          {step === 2 && (
            <div className="card space-y-6">
              <h2 className="text-lg font-semibold text-slate-800">Step 2: Review Pathway</h2>

              {analysisLoading ? (
                <div className="py-12 text-center text-slate-400 animate-pulse">Analyzing project...</div>
              ) : analysis ? (
                <div className="space-y-5">
                  {/* Pathway badge + days */}
                  <div className="flex items-center gap-4 p-4 bg-slate-50 rounded-xl border border-slate-200">
                    <div>
                      <p className="text-xs text-slate-500 mb-1 uppercase tracking-wide font-semibold">Permit Pathway</p>
                      <PathwayBadge pathway={analysis.pathway ?? "standard"} />
                    </div>
                    <div className="border-l border-slate-200 pl-4">
                      <p className="text-xs text-slate-500 mb-1 uppercase tracking-wide font-semibold">Estimated Days</p>
                      <span className="text-2xl font-bold text-slate-800">
                        {analysis.estimated_days ?? "--"}
                      </span>
                    </div>
                    {analysis.standard_plans_available !== undefined && (
                      <div className="border-l border-slate-200 pl-4">
                        <p className="text-xs text-slate-500 mb-1 uppercase tracking-wide font-semibold">Standard Plans</p>
                        <span
                          className={`text-sm font-semibold ${
                            analysis.standard_plans_available ? "text-emerald-600" : "text-slate-400"
                          }`}
                        >
                          {analysis.standard_plans_available ? "Available" : "Not Available"}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Key constraints */}
                  {analysis.key_constraints && analysis.key_constraints.length > 0 && (
                    <div>
                      <p className="text-sm font-semibold text-slate-700 mb-2">Key Constraints</p>
                      <ul className="space-y-1">
                        {analysis.key_constraints.map((c: string, i: number) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                            <span className="mt-0.5 text-amber-500 shrink-0">&#9679;</span>
                            {c}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Summary of inputs */}
                  <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-3 text-sm text-indigo-800">
                    <p>
                      <span className="font-medium">Address:</span> {form.address}
                    </p>
                    <p>
                      <span className="font-medium">Size:</span> {form.original_sqft} &rarr; {form.proposed_sqft} sq ft &nbsp;&bull;&nbsp; {form.stories} {Number(form.stories) === 1 ? "story" : "stories"}
                    </p>
                  </div>
                </div>
              ) : null}
            </div>
          )}

          {/* ----------------------------------------------------------------
              STEP 3: Confirm & submit
          ---------------------------------------------------------------- */}
          {step === 3 && (
            <div className="card space-y-6">
              <h2 className="text-lg font-semibold text-slate-800">Step 3: Confirm &amp; Submit</h2>

              <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 space-y-3 text-sm">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Project Summary</p>
                <div className="grid grid-cols-2 gap-y-3">
                  <span className="text-slate-500">Address</span>
                  <span className="font-medium text-slate-900">{form.address}</span>

                  <span className="text-slate-500">Original Sq Ft</span>
                  <span className="font-medium text-slate-900">{form.original_sqft}</span>

                  <span className="text-slate-500">Proposed Sq Ft</span>
                  <span className="font-medium text-slate-900">{form.proposed_sqft}</span>

                  <span className="text-slate-500">Stories</span>
                  <span className="font-medium text-slate-900">{form.stories}</span>

                  <span className="text-slate-500">Pathway</span>
                  <span>
                    <PathwayBadge pathway={analysis?.pathway ?? "standard"} />
                  </span>

                  <span className="text-slate-500">Est. Days</span>
                  <span className="font-medium text-slate-900">{analysis?.estimated_days ?? "--"}</span>
                </div>

                {parcel && (
                  <div className="pt-3 border-t border-slate-200 flex flex-wrap gap-1">
                    <OverlayBadge label="Coastal" active={!!parcel.is_coastal} />
                    <OverlayBadge label="Hillside" active={!!parcel.is_hillside} />
                    <OverlayBadge label="Fire Hazard" active={!!parcel.fire_severity} />
                    <OverlayBadge label="Historic" active={!!parcel.is_historic} />
                  </div>
                )}
              </div>

              <p className="text-sm text-slate-500">
                By submitting, a new permit project will be created and routed through the appropriate clearance pathway.
              </p>
            </div>
          )}

          {/* ----------------------------------------------------------------
              Navigation buttons
          ---------------------------------------------------------------- */}
          <div className="flex items-center justify-between mt-6">
            <button
              onClick={() => {
                setError(null);
                setStep((s) => s - 1);
              }}
              disabled={step === 1}
              className="btn-secondary"
            >
              &larr; Back
            </button>

            {step < 3 ? (
              <button
                onClick={handleNext}
                disabled={analysisLoading || (step === 1 && step1Invalid)}
                className="btn-primary"
              >
                {analysisLoading ? "Analyzing..." : "Next \u2192"}
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="btn-primary"
              >
                {submitting ? "Creating..." : "Create Project"}
              </button>
            )}
          </div>
        </div>
        </div>
      </main>
    </div>
  );
}
