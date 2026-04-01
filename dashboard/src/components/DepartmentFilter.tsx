"use client";

import { useRouter, useSearchParams } from "next/navigation";

const departments = [
  { value: "", label: "All Departments" },
  { value: "LADBS", label: "LADBS" },
  { value: "LAFD", label: "LAFD" },
  { value: "LADWP", label: "LADWP" },
  { value: "Public Works", label: "Public Works" },
  { value: "Planning", label: "Planning" },
  { value: "Coastal Commission", label: "Coastal Commission" },
  { value: "Transportation", label: "Transportation" },
];

export default function DepartmentFilter({ basePath }: { basePath: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();

  function onChange(value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) {
      params.set("department", value);
    } else {
      params.delete("department");
    }
    router.push(`${basePath}?${params.toString()}`);
  }

  return (
    <select
      className="select w-auto"
      value={searchParams.get("department") || ""}
      onChange={(e) => onChange(e.target.value)}
    >
      {departments.map((d) => (
        <option key={d.value} value={d.value}>
          {d.label}
        </option>
      ))}
    </select>
  );
}
