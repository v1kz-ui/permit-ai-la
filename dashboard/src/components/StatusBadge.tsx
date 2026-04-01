import clsx from "clsx";

const statusStyles: Record<string, string> = {
  not_started: "bg-slate-100 text-slate-600 border border-slate-200",
  in_review: "bg-blue-100 text-blue-700 border border-blue-200",
  approved: "bg-emerald-100 text-emerald-700 border border-emerald-200",
  conditional: "bg-amber-100 text-amber-700 border border-amber-200",
  denied: "bg-red-100 text-red-700 border border-red-200",
  bottleneck: "bg-red-50 text-red-700 border border-red-300 font-semibold",
  pending: "bg-amber-100 text-amber-700 border border-amber-200",
  active: "bg-emerald-100 text-emerald-700 border border-emerald-200",
  closed: "bg-slate-100 text-slate-500 border border-slate-200",
  final: "bg-violet-100 text-violet-700 border border-violet-200",
  scheduled: "bg-blue-100 text-blue-700 border border-blue-200",
  completed_pass: "bg-emerald-100 text-emerald-700 border border-emerald-200",
  completed_fail: "bg-red-100 text-red-700 border border-red-200",
  cancelled: "bg-slate-100 text-slate-500 border border-slate-200",
};

const statusLabels: Record<string, string> = {
  not_started: "Not Started",
  in_review: "In Review",
  approved: "Approved",
  conditional: "Conditional",
  denied: "Denied",
  bottleneck: "⚠ Bottleneck",
  pending: "Pending",
  active: "Active",
  closed: "Closed",
  final: "Final",
  scheduled: "Scheduled",
  completed_pass: "Pass",
  completed_fail: "Fail",
  cancelled: "Cancelled",
};

export default function StatusBadge({ status }: { status: string }) {
  const label = statusLabels[status] || status.replace(/_/g, " ");
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
        statusStyles[status] || "bg-slate-100 text-slate-600 border border-slate-200"
      )}
    >
      {label}
    </span>
  );
}
