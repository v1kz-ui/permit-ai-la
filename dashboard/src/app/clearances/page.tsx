"use client";

import { useEffect, useState, useCallback, Suspense } from "react";
import {
  DndContext,
  DragEndEvent,
  DragOverEvent,
  DragStartEvent,
  DragOverlay,
  closestCorners,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import Sidebar from "@/components/Sidebar";
import DepartmentFilter from "@/components/DepartmentFilter";
import DataSourceBanner from "@/components/DataSourceBanner";
import UndoToast from "@/components/UndoToast";
import { SkeletonKanban } from "@/components/Skeleton";
import { api } from "@/lib/api";
import { MOCK_KANBAN } from "@/lib/mockData";
import { useToast } from "@/components/Toast";

// ─── Types ────────────────────────────────────────────────────────────────────

type KanbanKey = "not_started" | "in_review" | "approved" | "conditional" | "denied";

interface KanbanCard {
  id: string;
  address?: string;
  project_address?: string;
  department?: string;
  clearance_type?: string;
  predicted_days?: number | null;
  is_bottleneck?: boolean;
  status?: string;
}

type KanbanData = Record<KanbanKey, KanbanCard[]>;

// ─── Column config ────────────────────────────────────────────────────────────

const columnConfig: { key: KanbanKey; label: string; headerColor: string; dot: string }[] = [
  { key: "not_started",  label: "Not Started",  headerColor: "bg-slate-100",  dot: "bg-slate-400" },
  { key: "in_review",    label: "In Review",    headerColor: "bg-blue-100",   dot: "bg-blue-500"  },
  { key: "approved",     label: "Approved",     headerColor: "bg-emerald-100",dot: "bg-emerald-500" },
  { key: "conditional",  label: "Conditional",  headerColor: "bg-amber-100",  dot: "bg-amber-500" },
  { key: "denied",       label: "Denied",       headerColor: "bg-red-100",    dot: "bg-red-500"   },
];


// ─── Draggable Card ───────────────────────────────────────────────────────────

function KanbanCardItem({
  card,
  isDragging,
}: {
  card: KanbanCard;
  isDragging?: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({
    id: card.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`bg-white rounded-xl shadow-sm border p-3 text-sm cursor-grab active:cursor-grabbing select-none transition-shadow hover:shadow-md
        ${card.is_bottleneck
          ? "border-red-300 bg-red-50/60 border-l-4 border-l-red-500"
          : "border-slate-200"
        }`}
    >
      <p className="font-medium text-xs truncate mb-1">
        {card.address || card.project_address || "—"}
      </p>
      <p className="text-xs text-slate-500 mb-0.5">{card.department || "—"}</p>
      <p className="text-xs text-slate-400 mb-2">{card.clearance_type || "—"}</p>
      <div className="flex items-center justify-between gap-2">
        {card.predicted_days != null && (
          <span className="text-xs bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-full px-2 py-0.5 font-medium">
            {card.predicted_days}d
          </span>
        )}
        {card.is_bottleneck && (
          <span className="flex items-center gap-1 text-xs text-red-600 font-semibold">
            <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse inline-block" />
            Bottleneck
          </span>
        )}
      </div>
    </div>
  );
}

// Ghost card shown in DragOverlay
function GhostCard({ card }: { card: KanbanCard }) {
  return (
    <div
      className={`bg-white rounded shadow-lg p-3 text-sm rotate-2 opacity-90 w-[220px]
        ${card.is_bottleneck ? "border-l-4 border-red-500 bg-red-50" : "border border-blue-300"}`}
    >
      <p className="font-medium text-xs truncate mb-1">
        {card.address || card.project_address || "—"}
      </p>
      <p className="text-xs text-gray-500">{card.department || "—"}</p>
      <p className="text-xs text-gray-400">{card.clearance_type || "—"}</p>
    </div>
  );
}

// ─── Droppable Column ─────────────────────────────────────────────────────────

function KanbanColumn({
  col,
  cards,
  activeId,
}: {
  col: (typeof columnConfig)[number];
  cards: KanbanCard[];
  activeId: string | null;
}) {
  return (
    <div className="flex-1 min-w-[220px] bg-slate-50 rounded-2xl border border-slate-200">
      <div className={`${col.headerColor} px-4 py-3 rounded-t-2xl flex items-center justify-between border-b border-slate-200`}>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${col.dot}`} />
          <h3 className="font-semibold text-sm text-slate-700">{col.label}</h3>
        </div>
        <span className="text-xs font-semibold bg-white/80 text-slate-600 rounded-full px-2.5 py-0.5 border border-slate-200">
          {cards.length}
        </span>
      </div>
      <div
        data-column-id={col.key}
        className="p-2.5 space-y-2 max-h-[calc(100vh-220px)] overflow-y-auto scrollbar-thin min-h-[80px]"
      >
        <SortableContext
          items={cards.map((c) => c.id)}
          strategy={verticalListSortingStrategy}
        >
          {cards.length === 0 && (
            <p className="text-xs text-slate-400 text-center py-6">Drop items here</p>
          )}
          {cards.map((card) => (
            <KanbanCardItem
              key={card.id}
              card={card}
              isDragging={activeId === card.id}
            />
          ))}
        </SortableContext>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ClearancesPage() {
  const { toast } = useToast();
  const [kanban, setKanban] = useState<KanbanData>({
    not_started: [],
    in_review: [],
    approved: [],
    conditional: [],
    denied: [],
  });
  const [loading, setLoading] = useState(true);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [dataSource, setDataSource] = useState<"live" | "mock">("live");
  const [pendingMove, setPendingMove] = useState<{
    cardId: string;
    toCol: KanbanKey;
    toLabel: string;
    prevKanban: KanbanData;
  } | null>(null);
  // Snapshot of kanban at drag-start, used for undo rollback
  const dragStartKanbanRef = { current: kanban as KanbanData };

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  );

  // ── Load data ──
  useEffect(() => {
    api.staff
      .kanban()
      .then((data) => {
        const hasData = Object.values(data).some((col: any) => Array.isArray(col) && col.length > 0);
        if (hasData) {
          setKanban(data as KanbanData);
          setDataSource("live");
        } else {
          setKanban(MOCK_KANBAN as KanbanData);
          setDataSource("mock");
        }
      })
      .catch(() => {
        setKanban(MOCK_KANBAN as KanbanData);
        setDataSource("mock");
      })
      .finally(() => setLoading(false));
  }, []);

  // ── Helpers ──
  const findColumnForCard = useCallback(
    (cardId: string): KanbanKey | null => {
      for (const col of columnConfig) {
        if (kanban[col.key].some((c) => c.id === cardId)) return col.key;
      }
      return null;
    },
    [kanban]
  );

  const getActiveCard = useCallback((): KanbanCard | null => {
    if (!activeId) return null;
    for (const col of columnConfig) {
      const found = kanban[col.key].find((c) => c.id === activeId);
      if (found) return found;
    }
    return null;
  }, [activeId, kanban]);

  // ── Undo handlers ──
  const handleUndoExpire = useCallback(() => {
    if (!pendingMove) return;
    api.clearances
      .updateStatus(pendingMove.cardId, pendingMove.toCol)
      .then(() => toast({ title: "Clearance updated", description: `Moved to ${pendingMove.toLabel}`, type: "success" }))
      .catch(() => {
        api.staff.kanban().then((data) => setKanban(data as KanbanData)).catch(() => {});
        toast({ title: "Move failed", description: "Could not update status", type: "error" });
      });
    setPendingMove(null);
  }, [pendingMove, toast]);

  const handleUndo = useCallback(() => {
    if (!pendingMove) return;
    setKanban(pendingMove.prevKanban);
    setPendingMove(null);
    toast({ title: "Move undone", type: "info" });
  }, [pendingMove, toast]);

  // ── Drag handlers ──
  function handleDragStart(event: DragStartEvent) {
    setActiveId(String(event.active.id));
    dragStartKanbanRef.current = kanban;
  }

  function handleDragOver(event: DragOverEvent) {
    const { active, over } = event;
    if (!over) return;

    const activeColKey = findColumnForCard(String(active.id));
    // over could be a card or a column data-id
    let overColKey: KanbanKey | null = null;

    // Check if over is a column key
    if (columnConfig.some((c) => c.key === over.id)) {
      overColKey = over.id as KanbanKey;
    } else {
      overColKey = findColumnForCard(String(over.id));
    }

    if (!activeColKey || !overColKey || activeColKey === overColKey) return;

    setKanban((prev) => {
      const card = prev[activeColKey].find((c) => c.id === String(active.id));
      if (!card) return prev;
      return {
        ...prev,
        [activeColKey]: prev[activeColKey].filter((c) => c.id !== String(active.id)),
        [overColKey]: [...prev[overColKey], { ...card, status: overColKey }],
      };
    });
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    setActiveId(null);
    if (!over) return;

    // Determine destination column
    let destColKey: KanbanKey | null = null;
    if (columnConfig.some((c) => c.key === over.id)) {
      destColKey = over.id as KanbanKey;
    } else {
      destColKey = findColumnForCard(String(over.id));
    }

    if (!destColKey) return;

    const cardId = String(active.id);
    const destLabel = columnConfig.find((c) => c.key === destColKey)?.label ?? destColKey;

    // Queue a pending move — user has 5s to undo before the API call fires
    setPendingMove({
      cardId,
      toCol: destColKey,
      toLabel: destLabel,
      prevKanban: dragStartKanbanRef.current,
    });
  }

  // ─── Render ───
  return (
    <div className="flex h-full min-h-screen">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="bg-white border-b border-slate-100 px-8 py-6 flex items-center justify-between flex-shrink-0">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Clearances Board</h1>
            <p className="text-sm text-slate-500 mt-0.5">Drag and drop cards to update clearance status</p>
          </div>
          <Suspense fallback={<div className="w-40 h-10 bg-slate-100 rounded-xl animate-pulse" />}>
            <DepartmentFilter basePath="/clearances" />
          </Suspense>
        </div>

        {dataSource === "mock" && <DataSourceBanner source="mock" />}

        <div className="flex-1 overflow-x-auto p-6 pb-4">
        {loading ? (
          <SkeletonKanban />
        ) : (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCorners}
            onDragStart={handleDragStart}
            onDragOver={handleDragOver}
            onDragEnd={handleDragEnd}
          >
            <div className="flex gap-4 min-w-[1100px]">
              {columnConfig.map((col) => (
                <KanbanColumn
                  key={col.key}
                  col={col}
                  cards={kanban[col.key] || []}
                  activeId={activeId}
                />
              ))}
            </div>

            <DragOverlay>
              {activeId && getActiveCard() ? (
                <GhostCard card={getActiveCard()!} />
              ) : null}
            </DragOverlay>
          </DndContext>
        )}
        </div>
      </main>

      {pendingMove && (
        <UndoToast
          message={`Moved to ${pendingMove.toLabel}`}
          onUndo={handleUndo}
          onExpire={handleUndoExpire}
        />
      )}
    </div>
  );
}
