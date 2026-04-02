"use client";

import { useRouter, useSearchParams } from "next/navigation";

const departments = [
  { value: "", label: "All Departments" },
  { value: "ladbs", label: "LADBS" },
  { value: "dcp", label: "City Planning (DCP)" },
  { value: "boe", label: "Bureau of Engineering" },
  { value: "lafd", label: "Fire Department (LAFD)" },
  { value: "ladwp", label: "Water & Power (LADWP)" },
  { value: "lasan", label: "Sanitation (LASAN)" },
  { value: "lahd", label: "Housing (LAHD)" },
  { value: "dot", label: "Transportation (DOT)" },
  { value: "cultural_affairs", label: "Cultural Affairs" },
  { value: "urban_forestry", label: "Urban Forestry" },
  { value: "la_county", label: "LA County" },
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
