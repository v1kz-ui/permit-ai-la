---
sidebar_position: 3
title: Frontend (Dashboard)
---

# Frontend Architecture

The staff dashboard is a Next.js 14 application using the App Router.

## Tech Stack

- **Next.js 14** with App Router (file-based routing)
- **React 18** with server and client components
- **Tailwind CSS** for styling
- **Recharts** for charts and visualizations
- **Mapbox GL** for interactive maps
- **dnd-kit** for drag-and-drop (Kanban board)

## Page Routes

| Route | Page | Description |
|-------|------|-------------|
| `/` | Dashboard Home | KPI cards, pipeline chart, map, bottlenecks |
| `/projects` | Projects List | Filterable table with pagination |
| `/projects/new` | New Project | Multi-step wizard with parcel lookup |
| `/projects/[id]` | Project Detail | Clearances, timeline, documents, AI analysis |
| `/projects/[id]/what-if` | What-If Analysis | Scenario comparison (EO1/EO8/Standard) |
| `/clearances` | Kanban Board | Drag-and-drop clearance status management |
| `/inspections` | Inspections | Scheduling, pass rates, failure tracking |
| `/inspections/routing` | Inspector Routing | Geographic clustering for inspectors |
| `/analytics` | Analytics | Trends, equity metrics, department performance |
| `/compliance` | Compliance | Rule validation and sequence checking |
| `/impact` | Impact Dashboard | Public-facing outcomes and metrics |
| `/chat` | AI Chat | Conversational assistant with project context |
| `/admin` | Admin Panel | System health, user management, cache |
| `/admin/audit` | Audit Log | Full change history with JSON diffs |

## Key Components

### Layout
- **Sidebar** -- Navigation with grouped sections (Operations, Intelligence, Public, Admin), mobile hamburger menu, skip-to-content link

### Data Display
- **TrendChart** -- Recharts line/area chart for time-series metrics
- **DepartmentChart** -- Bar chart with color-coded bottleneck status
- **ProjectMap** -- Mapbox GL map with project location markers
- **PermitJourneyTimeline** -- 5-phase visual timeline (Application > Clearances > Plan Review > Inspections > Permit Issued)
- **StatusBadge** -- Color-coded status indicators

### Interactive
- **DocumentUpload** -- Drag-and-drop file upload with preview and progress bars
- **PathwayExplainer** -- Educational card explaining EO1/EO8/Standard requirements
- **CelebrationBanner** -- Confetti animation when all clearances approved
- **UndoToast** -- 5-second undo window for Kanban card moves
- **JargonTip** -- Hover tooltips explaining LA permit terminology

### Helpers
- **DepartmentFilter** -- Dropdown filter for all 10+ departments
- **Pagination** -- Page-based navigation for tables
- **Skeleton** -- Loading placeholders (cards, charts, kanban)
- **DataSourceBanner** -- Indicator showing live API vs mock data fallback

## API Client

The API client in `dashboard/src/lib/api.ts` provides typed methods for all endpoints with automatic error handling and mock data fallback when the backend is unavailable. Data is revalidated every 30 seconds.

## Accessibility

- ARIA labels and roles throughout
- Skip-to-content navigation link
- Keyboard-navigable controls
- WCAG color contrast compliance
- Screen reader support with `role` and `aria-live` attributes
