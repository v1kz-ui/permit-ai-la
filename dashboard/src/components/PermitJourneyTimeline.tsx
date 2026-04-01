const PHASES = [
  { key: "application", label: "Application Filed" },
  { key: "clearances", label: "Dept. Clearances" },
  { key: "plan_review", label: "Plan Review" },
  { key: "inspection", label: "Inspections" },
  { key: "permit_issued", label: "Permit Issued" },
];

interface Props {
  currentPhase: string;
  completedPhases: string[];
}

export function derivePhase(clearances: any[]): string {
  if (!clearances.length) return "application";
  if (clearances.every((c: any) => c.status === "approved")) return "inspection";
  return "clearances";
}

export function deriveCompleted(clearances: any[]): string[] {
  const phases = ["application"];
  if (clearances.length && clearances.every((c: any) => c.status === "approved")) {
    phases.push("clearances", "plan_review");
  }
  return phases;
}

export default function PermitJourneyTimeline({ currentPhase, completedPhases }: Props) {
  const currentIndex = PHASES.findIndex((p) => p.key === currentPhase);

  return (
    <div className="card mb-6">
      <div className="flex items-center justify-between mb-5">
        <h3 className="font-semibold text-slate-800">Permit Journey</h3>
        {currentIndex >= 0 && (
          <span className="text-xs text-slate-400 bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-100">
            Step {currentIndex + 1} of {PHASES.length}
          </span>
        )}
      </div>

      <div className="flex items-start">
        {PHASES.map((phase, i) => {
          const isCompleted = completedPhases.includes(phase.key);
          const isCurrent = phase.key === currentPhase;

          return (
            <div key={phase.key} className="flex items-center flex-1">
              {i > 0 && (
                <div
                  className={`h-0.5 flex-1 -mt-5 ${
                    isCompleted ? "bg-emerald-400" : "bg-slate-200"
                  }`}
                />
              )}
              <div className="flex flex-col items-center">
                <div
                  className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold transition-all
                    ${
                      isCompleted
                        ? "bg-emerald-500 text-white shadow-sm"
                        : isCurrent
                        ? "bg-indigo-100 text-indigo-700 ring-2 ring-indigo-400 ring-offset-2"
                        : "bg-slate-100 text-slate-400"
                    }`}
                  aria-label={`${phase.label}: ${
                    isCompleted ? "completed" : isCurrent ? "current step" : "upcoming"
                  }`}
                >
                  {isCompleted ? (
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    i + 1
                  )}
                </div>
                <span
                  className={`text-xs mt-2 text-center max-w-[72px] leading-tight ${
                    isCurrent
                      ? "font-semibold text-indigo-700"
                      : isCompleted
                      ? "text-emerald-600 font-medium"
                      : "text-slate-400"
                  }`}
                >
                  {phase.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 pt-4 border-t border-slate-100">
        <div className="w-full bg-slate-100 rounded-full h-1.5">
          <div
            className="bg-indigo-500 h-1.5 rounded-full transition-all duration-700"
            style={{ width: `${((currentIndex + 1) / PHASES.length) * 100}%` }}
          />
        </div>
        <p className="text-xs text-slate-400 mt-2 text-center">
          {isCompleted(currentPhase, completedPhases)
            ? "All phases complete — permit ready"
            : `Currently in: ${PHASES.find((p) => p.key === currentPhase)?.label ?? "Review"}`}
        </p>
      </div>
    </div>
  );
}

function isCompleted(currentPhase: string, completedPhases: string[]): boolean {
  return currentPhase === "permit_issued" || completedPhases.includes("permit_issued");
}
