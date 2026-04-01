import { unstable_cache } from "next/cache";
import Sidebar from "@/components/Sidebar";
import StatusBadge from "@/components/StatusBadge";
import ProjectsFilters from "@/components/ProjectsFilters";
import Pagination from "@/components/Pagination";
import { api } from "@/lib/api";
import { MOCK_PROJECTS } from "@/lib/mockData";
import Link from "next/link";

export default async function ProjectsPage({
  searchParams,
}: {
  searchParams: { status?: string; pathway?: string; page?: string };
}) {
  const page = Number(searchParams.page) || 1;
  const status = searchParams.status || "";
  const pathway = searchParams.pathway || "";

  const fetchProjects = unstable_cache(
    async () => {
      try {
        const result = await api.staff.projects({
          status: status || undefined,
          pathway: pathway || undefined,
          page,
          size: 20,
        });
        return (!result.items || result.items.length === 0) ? MOCK_PROJECTS as typeof result : result;
      } catch {
        return MOCK_PROJECTS as any;
      }
    },
    [`projects-${status}-${pathway}-${page}`],
    { revalidate: 30 }
  );

  const data = await fetchProjects();

  const pathwayColors: Record<string, string> = {
    standard: "bg-slate-100 text-slate-700",
    eo1: "bg-indigo-100 text-indigo-700",
    eo8: "bg-violet-100 text-violet-700",
    coastal: "bg-cyan-100 text-cyan-700",
    hillside: "bg-amber-100 text-amber-700",
  };

  return (
    <div className="flex h-full min-h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        {/* Header */}
        <div className="bg-white border-b border-slate-100 px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">Projects</h1>
              <p className="text-sm text-slate-500 mt-0.5">
                {data.total > 0 ? `${data.total} rebuild projects` : "Fire rebuild permit tracking"}
              </p>
            </div>
            <Link href="/projects/new" className="btn-primary">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              New Project
            </Link>
          </div>
        </div>

        <div className="px-8 py-6 space-y-5">
          {/* Filters */}
          <div className="card !p-4">
            <ProjectsFilters />
          </div>

          {/* Table */}
          <div className="card !p-0 overflow-hidden overflow-x-auto">
            <table className="table-base">
              <thead>
                <tr>
                  <th>Address</th>
                  <th>Pathway</th>
                  <th>Status</th>
                  <th>Predicted Days</th>
                  <th>Overlays</th>
                  <th>Created</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {data.items.length === 0 && (
                  <tr>
                    <td colSpan={7}>
                      <div className="flex flex-col items-center justify-center py-16 text-slate-400">
                        <svg className="w-10 h-10 mb-3 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                        </svg>
                        <p className="font-medium text-slate-500">No projects found</p>
                        <p className="text-sm mt-1">Try adjusting your filters or create a new project</p>
                      </div>
                    </td>
                  </tr>
                )}
                {data.items.map((project: any) => (
                  <tr key={project.id}>
                    <td>
                      <Link
                        href={`/projects/${project.id}`}
                        className="font-medium text-indigo-600 hover:text-indigo-700 hover:underline"
                      >
                        {project.address}
                      </Link>
                    </td>
                    <td>
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${pathwayColors[project.pathway] || "bg-slate-100 text-slate-700"}`}>
                        {project.pathway?.toUpperCase() || "—"}
                      </span>
                    </td>
                    <td>
                      <StatusBadge status={project.status} />
                    </td>
                    <td>
                      {project.predicted_days != null ? (
                        <span className="font-semibold text-slate-700">{project.predicted_days}d</span>
                      ) : "—"}
                    </td>
                    <td>
                      <div className="flex items-center gap-1.5">
                        {project.is_coastal && (
                          <span className="badge bg-cyan-100 text-cyan-700">Coastal</span>
                        )}
                        {project.is_hillside && (
                          <span className="badge bg-amber-100 text-amber-700">Hillside</span>
                        )}
                        {!project.is_coastal && !project.is_hillside && (
                          <span className="text-slate-400 text-xs">None</span>
                        )}
                      </div>
                    </td>
                    <td className="text-slate-500">
                      {project.created_at
                        ? new Date(project.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
                        : "—"}
                    </td>
                    <td>
                      <Link href={`/projects/${project.id}`} className="text-slate-400 hover:text-indigo-600 transition-colors">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                        </svg>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <Pagination
            currentPage={data.page}
            totalPages={data.pages}
            basePath="/projects"
          />
        </div>
      </main>
    </div>
  );
}
