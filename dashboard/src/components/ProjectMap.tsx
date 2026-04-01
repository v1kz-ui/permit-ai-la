"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

// Status → colour mapping matches StatusBadge colours
const STATUS_COLORS: Record<string, string> = {
  intake:                "#6b7280",  // gray
  in_review:             "#3b82f6",  // blue
  plan_check:            "#8b5cf6",  // purple
  clearances_in_progress:"#f59e0b", // amber
  ready_for_issue:       "#10b981",  // green
  issued:                "#059669",  // dark green
  inspection:            "#0ea5e9",  // sky
  final:                 "#1e3a5f",  // dark navy
  closed:                "#9ca3af",  // light gray
};

const BOTTLENECK_COLOR = "#ef4444"; // red

interface ProjectFeature {
  id: string;
  address: string;
  status: string;
  pathway: string | null;
  predicted_total_days: number | null;
  has_bottleneck: boolean;
  lng: number;
  lat: number;
}

interface TooltipState {
  x: number;
  y: number;
  feature: ProjectFeature;
}

interface ProjectMapProps {
  height?: number;
  className?: string;
}

// Mock project pins for the static placeholder
const MOCK_PINS = [
  { x: 22, y: 38, label: "14823 Sunset Blvd", status: "bottleneck", color: "#ef4444" },
  { x: 31, y: 44, label: "2104 Altadena Dr", status: "in_review", color: "#8b5cf6" },
  { x: 18, y: 52, label: "756 Castellammare Dr", status: "clearances", color: "#f59e0b" },
  { x: 40, y: 30, label: "4490 Via Marisol", status: "plan_check", color: "#8b5cf6" },
  { x: 28, y: 60, label: "1833 Marquez Ave", status: "issued", color: "#059669" },
  { x: 55, y: 42, label: "312 Topanga Cyn", status: "in_review", color: "#3b82f6" },
  { x: 65, y: 55, label: "8821 Wonderland Ave", status: "issued", color: "#059669" },
  { x: 72, y: 35, label: "5002 Zaca Mesa Rd", status: "intake", color: "#6b7280" },
  { x: 48, y: 65, label: "901 Chautauqua Blvd", status: "final", color: "#1e3a5f" },
  { x: 38, y: 75, label: "1247 Palisades Dr", status: "bottleneck", color: "#ef4444" },
  { x: 62, y: 20, label: "3380 Altadena Ave", status: "clearances", color: "#f59e0b" },
  { x: 80, y: 48, label: "7755 Mulholland Dr", status: "in_review", color: "#3b82f6" },
];

function StaticMapPlaceholder({ height, isLoading }: { height: number; isLoading?: boolean }) {
  const [hovered, setHovered] = useState<number | null>(null);

  return (
    <div className="relative w-full overflow-hidden" style={{ height }}>
      {/* Gradient background simulating a map */}
      <div className="absolute inset-0" style={{
        background: "linear-gradient(160deg, #dbeafe 0%, #ede9fe 30%, #d1fae5 60%, #e0f2fe 100%)",
      }} />

      {/* Road-like lines */}
      <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
        {/* Pacific Coast Highway */}
        <path d="M0,70 Q20,65 40,68 Q60,71 100,65" stroke="#c7d2fe" strokeWidth="0.8" fill="none" opacity="0.8" />
        {/* Sunset Blvd */}
        <path d="M5,45 Q25,42 50,40 Q75,38 100,42" stroke="#bfdbfe" strokeWidth="0.6" fill="none" opacity="0.7" />
        {/* Topanga Canyon */}
        <path d="M30,10 Q32,35 35,55 Q38,75 36,95" stroke="#c7d2fe" strokeWidth="0.5" fill="none" opacity="0.6" />
        {/* Mulholland */}
        <path d="M0,30 Q20,28 45,25 Q70,22 100,30" stroke="#ddd6fe" strokeWidth="0.5" fill="none" opacity="0.6" />
        {/* Side streets */}
        <path d="M60,10 Q62,30 65,50 Q67,70 64,90" stroke="#e2e8f0" strokeWidth="0.4" fill="none" opacity="0.5" />
        <path d="M78,15 Q79,40 80,60 Q81,80 79,95" stroke="#e2e8f0" strokeWidth="0.4" fill="none" opacity="0.5" />
        <path d="M0,55 Q30,53 50,55 Q75,57 100,52" stroke="#e2e8f0" strokeWidth="0.4" fill="none" opacity="0.4" />

        {/* Zone overlays */}
        <ellipse cx="25" cy="50" rx="18" ry="22" fill="#fde68a" fillOpacity="0.18" />
        <ellipse cx="62" cy="42" rx="22" ry="20" fill="#c7d2fe" fillOpacity="0.18" />

        {/* Zone labels */}
        <text x="15" y="87" fontSize="2.8" fill="#92400e" opacity="0.7" fontFamily="sans-serif" fontWeight="600">Pacific Palisades</text>
        <text x="52" y="87" fontSize="2.8" fill="#4338ca" opacity="0.7" fontFamily="sans-serif" fontWeight="600">Altadena</text>
      </svg>

      {/* Project pins */}
      {MOCK_PINS.map((pin, i) => (
        <div
          key={i}
          className="absolute cursor-pointer transition-transform duration-150"
          style={{
            left: `${pin.x}%`,
            top: `${pin.y}%`,
            transform: `translate(-50%, -50%) scale(${hovered === i ? 1.6 : 1})`,
            zIndex: hovered === i ? 20 : 10,
          }}
          onMouseEnter={() => setHovered(i)}
          onMouseLeave={() => setHovered(null)}
        >
          <div
            className="rounded-full border-2 border-white shadow-md"
            style={{
              width: 12,
              height: 12,
              backgroundColor: pin.color,
              boxShadow: hovered === i ? `0 0 0 3px ${pin.color}40` : "0 1px 4px rgba(0,0,0,0.25)",
            }}
          />
          {/* Tooltip */}
          {hovered === i && (
            <div
              className="absolute z-30 bg-white rounded-xl shadow-xl border border-slate-100 px-3 py-2 text-xs whitespace-nowrap pointer-events-none"
              style={{
                bottom: "calc(100% + 6px)",
                left: "50%",
                transform: "translateX(-50%)",
                minWidth: 140,
              }}
            >
              <p className="font-semibold text-slate-800 truncate max-w-[180px]">{pin.label}</p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: pin.color }} />
                <span className="text-slate-500 capitalize">{pin.status.replace(/_/g, " ")}</span>
              </div>
            </div>
          )}
        </div>
      ))}

      {/* Legend */}
      <div className="absolute bottom-3 left-3 bg-white/90 backdrop-blur-sm rounded-xl px-3 py-2.5 shadow-sm border border-slate-100 text-xs">
        <p className="font-semibold text-slate-700 mb-1.5 text-[11px] uppercase tracking-wide">Status</p>
        {[
          ["In Review", "#3b82f6"],
          ["Clearances", "#f59e0b"],
          ["Issued", "#059669"],
          ["Bottleneck", "#ef4444"],
        ].map(([label, color]) => (
          <div key={label} className="flex items-center gap-1.5 mb-1 last:mb-0">
            <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
            <span className="text-slate-600">{label}</span>
          </div>
        ))}
        <p className="text-slate-400 mt-1.5 text-[10px]">{MOCK_PINS.length} projects shown</p>
      </div>

      {/* Zone pill labels */}
      <div className="absolute top-3 right-3 flex flex-col gap-1.5">
        <span className="text-[11px] font-semibold bg-amber-100/90 text-amber-800 px-2.5 py-1 rounded-full border border-amber-200 shadow-sm backdrop-blur-sm">
          🔥 Pacific Palisades
        </span>
        <span className="text-[11px] font-semibold bg-indigo-100/90 text-indigo-800 px-2.5 py-1 rounded-full border border-indigo-200 shadow-sm backdrop-blur-sm">
          🔥 Altadena
        </span>
      </div>

      {/* Loading overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-white/40 backdrop-blur-[1px] flex items-center justify-center">
          <div className="flex items-center gap-2 bg-white rounded-xl px-4 py-2.5 shadow-sm border border-slate-100">
            <div className="w-4 h-4 border-2 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
            <span className="text-sm text-slate-600 font-medium">Loading map…</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ProjectMap({ height = 320, className = "" }: ProjectMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const [features, setFeatures] = useState<ProjectFeature[]>([]);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);

  // Fetch project map data from API
  useEffect(() => {
    api.parcels.mapData()
      .then((geojson) => {
        const parsed: ProjectFeature[] = geojson.features.map((f) => ({
          id: f.properties.id,
          address: f.properties.address,
          status: f.properties.status,
          pathway: f.properties.pathway,
          predicted_total_days: f.properties.predicted_total_days,
          has_bottleneck: f.properties.has_bottleneck,
          lng: f.geometry.coordinates[0],
          lat: f.geometry.coordinates[1],
        }));
        setFeatures(parsed);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  // Initialize Mapbox map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;
    if (!token) {
      setError("Mapbox token not configured (NEXT_PUBLIC_MAPBOX_TOKEN)");
      return;
    }

    // Dynamic import to avoid SSR issues
    import("mapbox-gl").then((mapboxgl) => {
      mapboxgl.default.accessToken = token;

      const map = new mapboxgl.default.Map({
        container: mapContainerRef.current!,
        style: "mapbox://styles/mapbox/light-v11",
        center: [-118.52, 34.04],  // Pacific Palisades
        zoom: 11,
        attributionControl: false,
      });

      map.addControl(new mapboxgl.default.NavigationControl(), "top-right");
      map.addControl(
        new mapboxgl.default.AttributionControl({ compact: true }),
        "bottom-right"
      );

      map.on("load", () => {
        setMapLoaded(true);
      });

      mapRef.current = map;
    });

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  // Add project markers once map is loaded and features are fetched
  useEffect(() => {
    if (!mapLoaded || !mapRef.current || features.length === 0) return;

    import("mapbox-gl").then((mapboxgl) => {
      const map = mapRef.current;

      // Remove existing markers
      const existingMarkers = document.querySelectorAll(".project-marker");
      existingMarkers.forEach((m) => m.remove());

      features.forEach((feature) => {
        const color = feature.has_bottleneck
          ? BOTTLENECK_COLOR
          : (STATUS_COLORS[feature.status] ?? "#6b7280");

        // Create custom marker element
        const el = document.createElement("div");
        el.className = "project-marker";
        el.style.cssText = `
          width: 14px;
          height: 14px;
          border-radius: 50%;
          background-color: ${color};
          border: 2px solid white;
          box-shadow: 0 2px 4px rgba(0,0,0,0.3);
          cursor: pointer;
          transition: transform 0.15s ease;
        `;

        el.addEventListener("mouseenter", (e) => {
          el.style.transform = "scale(1.5)";
          const rect = (e.target as HTMLElement).getBoundingClientRect();
          const containerRect = mapContainerRef.current!.getBoundingClientRect();
          setTooltip({
            x: rect.left - containerRect.left + 8,
            y: rect.top - containerRect.top - 8,
            feature,
          });
        });

        el.addEventListener("mouseleave", () => {
          el.style.transform = "scale(1)";
          setTooltip(null);
        });

        el.addEventListener("click", () => {
          window.location.href = `/projects/${feature.id}`;
        });

        new mapboxgl.default.Marker({ element: el })
          .setLngLat([feature.lng, feature.lat])
          .addTo(map);
      });
    });
  }, [mapLoaded, features]);

  if (loading) {
    return (
      <div className={`relative overflow-hidden rounded-2xl ${className}`} style={{ height }}>
        <StaticMapPlaceholder height={height} isLoading />
      </div>
    );
  }

  if (error) {
    return (
      <div className={`relative overflow-hidden rounded-2xl ${className}`} style={{ height }}>
        <StaticMapPlaceholder height={height} />
      </div>
    );
  }

  return (
    <div className={`relative rounded-lg overflow-hidden ${className}`} style={{ height }}>
      <div ref={mapContainerRef} style={{ width: "100%", height: "100%" }} />

      {/* Tooltip */}
      {tooltip && (
        <div
          className="absolute z-10 bg-white shadow-lg rounded-lg p-3 text-sm pointer-events-none"
          style={{
            left: Math.min(tooltip.x, (mapContainerRef.current?.offsetWidth ?? 400) - 200),
            top: Math.max(0, tooltip.y - 80),
            maxWidth: 220,
          }}
        >
          <p className="font-semibold text-gray-800 truncate">{tooltip.feature.address}</p>
          <div className="flex items-center gap-2 mt-1">
            <span
              className="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0"
              style={{
                backgroundColor: tooltip.feature.has_bottleneck
                  ? BOTTLENECK_COLOR
                  : (STATUS_COLORS[tooltip.feature.status] ?? "#6b7280"),
              }}
            />
            <span className="text-gray-600 capitalize">
              {tooltip.feature.status.replace(/_/g, " ")}
              {tooltip.feature.has_bottleneck && " · Bottleneck"}
            </span>
          </div>
          {tooltip.feature.pathway && (
            <p className="text-xs text-gray-500 mt-0.5">
              {tooltip.feature.pathway.replace(/_/g, " ")}
            </p>
          )}
          {tooltip.feature.predicted_total_days != null && (
            <p className="text-xs text-gray-500">
              ~{tooltip.feature.predicted_total_days} days
            </p>
          )}
        </div>
      )}

      {/* Legend */}
      <div className="absolute bottom-8 left-2 bg-white bg-opacity-90 rounded-lg p-2 text-xs shadow">
        <p className="font-semibold text-gray-700 mb-1.5">Status</p>
        {[
          ["Active", "#3b82f6"],
          ["Issued", "#059669"],
          ["Bottleneck", "#ef4444"],
        ].map(([label, color]) => (
          <div key={label} className="flex items-center gap-1.5 mb-1">
            <span
              className="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0"
              style={{ backgroundColor: color }}
            />
            <span className="text-gray-600">{label}</span>
          </div>
        ))}
        <p className="text-gray-400 mt-1">{features.length} projects</p>
      </div>
    </div>
  );
}
