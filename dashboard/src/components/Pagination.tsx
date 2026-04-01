"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

function PaginationInner({
  currentPage,
  totalPages,
  basePath,
}: {
  currentPage: number;
  totalPages: number;
  basePath: string;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();

  function goToPage(page: number) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("page", String(page));
    router.push(`${basePath}?${params.toString()}`);
  }

  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center gap-2 mt-4">
      <button
        onClick={() => goToPage(currentPage - 1)}
        disabled={currentPage <= 1}
        className="btn-secondary !py-1.5 !px-3 text-xs disabled:opacity-40"
      >
        Previous
      </button>
      <span className="text-sm text-slate-500">
        Page {currentPage} of {totalPages}
      </span>
      <button
        onClick={() => goToPage(currentPage + 1)}
        disabled={currentPage >= totalPages}
        className="btn-secondary !py-1.5 !px-3 text-xs disabled:opacity-40"
      >
        Next
      </button>
    </div>
  );
}

export default function Pagination(props: {
  currentPage: number;
  totalPages: number;
  basePath: string;
}) {
  return (
    <Suspense fallback={null}>
      <PaginationInner {...props} />
    </Suspense>
  );
}
