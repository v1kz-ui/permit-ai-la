interface Action {
  title: string;
  description: string;
  href: string;
  urgent?: boolean;
}

interface Props {
  clearances: any[];
  projectId: string;
}

export default function NextActions({ clearances, projectId }: Props) {
  const actions: Action[] = [];

  const bottlenecks = clearances.filter((c: any) => c.is_bottleneck);
  const notStarted = clearances.filter((c: any) => c.status === "not_started");
  const inReview = clearances.filter((c: any) => c.status === "in_review");
  const allApproved =
    clearances.length > 0 && clearances.every((c: any) => c.status === "approved");

  if (bottlenecks.length > 0) {
    actions.push({
      title: `${bottlenecks.length} clearance${bottlenecks.length > 1 ? "s" : ""} need${bottlenecks.length === 1 ? "s" : ""} attention`,
      description: `${bottlenecks[0].department}: ${bottlenecks[0].clearance_type} — flagged as delayed`,
      href: "/clearances",
      urgent: true,
    });
  }

  if (notStarted.length > 0) {
    actions.push({
      title: `${notStarted.length} clearance${notStarted.length > 1 ? "s" : ""} not yet started`,
      description: `${notStarted[0].department} is waiting for documents to begin review`,
      href: "/clearances",
    });
  }

  if (inReview.length > 0 && actions.length < 2) {
    actions.push({
      title: `${inReview.length} clearance${inReview.length > 1 ? "s" : ""} under review`,
      description: "These departments are actively processing — no action required",
      href: "/clearances",
    });
  }

  if (allApproved) {
    actions.push({
      title: "All clearances approved",
      description: "Permit is nearly ready — schedule the final inspection",
      href: "/clearances",
    });
  }

  if (actions.length === 0) return null;

  return (
    <div className="card border-l-4 border-l-indigo-500">
      <h3 className="font-semibold text-slate-800 mb-3">Recommended Actions</h3>
      <div className="space-y-2">
        {actions.slice(0, 2).map((action, i) => (
          <a
            key={i}
            href={action.href}
            className={`block p-3 rounded-lg transition-colors ${
              action.urgent
                ? "bg-red-50 hover:bg-red-100 border border-red-100"
                : "bg-slate-50 hover:bg-slate-100 border border-slate-100"
            }`}
            aria-label={`${action.title}: ${action.description}`}
          >
            <div className="flex items-start gap-2">
              {action.urgent && (
                <svg
                  className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5"
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
              )}
              <div>
                <p
                  className={`text-sm font-medium ${
                    action.urgent ? "text-red-800" : "text-slate-800"
                  }`}
                >
                  {action.title}
                </p>
                <p className="text-xs text-slate-500 mt-0.5">{action.description}</p>
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
