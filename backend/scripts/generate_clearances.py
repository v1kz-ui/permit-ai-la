"""Generate realistic clearances for existing projects based on their zone flags and status.

Every permit project needs clearances from various city departments.
This script creates them based on each project's characteristics:
  - All projects: LADBS, DCP
  - Fire severity zone: LAFD
  - Coastal zone: DCP (coastal review)
  - Has water/sewer: LADWP, LASAN
  - Street work: DOT, BOE

Clearance status mirrors the project status progression.

Usage:
    cd backend
    python scripts/generate_clearances.py
"""
from __future__ import annotations
import asyncio
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://permitai:permitai@localhost:5432/permitai"
engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Department clearance templates
CLEARANCE_TEMPLATES = {
    "ladbs": [
        {"type": "Building Plan Check", "days": (14, 45)},
        {"type": "Structural Review", "days": (7, 30)},
    ],
    "dcp": [
        {"type": "Zoning Verification", "days": (5, 21)},
    ],
    "lafd": [
        {"type": "Fire Life Safety Review", "days": (7, 28)},
        {"type": "Brush Clearance Verification", "days": (3, 14)},
    ],
    "ladwp": [
        {"type": "Water Service Clearance", "days": (10, 35)},
    ],
    "lasan": [
        {"type": "Sewer Connection Review", "days": (7, 21)},
    ],
    "dot": [
        {"type": "Driveway/Access Review", "days": (5, 14)},
    ],
    "boe": [
        {"type": "Grading Plan Review", "days": (10, 30)},
    ],
    "lahd": [
        {"type": "Housing Compliance Review", "days": (5, 14)},
    ],
    "cultural_affairs": [
        {"type": "Cultural Resource Review", "days": (10, 30)},
    ],
    "urban_forestry": [
        {"type": "Tree Removal Permit", "days": (7, 21)},
    ],
}

# Status progression probabilities based on project status
STATUS_WEIGHTS = {
    "intake": {"not_started": 0.7, "in_review": 0.25, "approved": 0.05},
    "in_review": {"not_started": 0.1, "in_review": 0.5, "approved": 0.3, "conditional": 0.1},
    "approved": {"in_review": 0.1, "approved": 0.8, "conditional": 0.1},
    "issued": {"approved": 0.85, "conditional": 0.1, "in_review": 0.05},
    "inspection": {"approved": 0.9, "conditional": 0.1},
    "final": {"approved": 0.95, "conditional": 0.05},
    "closed": {"approved": 1.0},
}


def pick_status(project_status: str) -> str:
    weights = STATUS_WEIGHTS.get(project_status, STATUS_WEIGHTS["intake"])
    statuses = list(weights.keys())
    probs = list(weights.values())
    return random.choices(statuses, weights=probs, k=1)[0]


def pick_departments(project: dict) -> list[tuple[str, str, tuple[int, int]]]:
    """Determine which clearances a project needs."""
    depts = []

    # Everyone needs LADBS + DCP
    depts.append(("ladbs", "Building Plan Check", (14, 45)))
    depts.append(("dcp", "Zoning Verification", (5, 21)))

    # Fire zone → LAFD
    if project.get("is_very_high_fire_severity"):
        depts.append(("lafd", "Fire Life Safety Review", (7, 28)))
        depts.append(("lafd", "Brush Clearance Verification", (3, 14)))

    # Coastal → extra DCP review
    if project.get("is_coastal_zone"):
        depts.append(("dcp", "Coastal Development Review", (14, 45)))

    # Most projects need utilities
    if random.random() < 0.7:
        depts.append(("ladwp", "Water Service Clearance", (10, 35)))
    if random.random() < 0.5:
        depts.append(("lasan", "Sewer Connection Review", (7, 21)))

    # Some need DOT/BOE
    if random.random() < 0.3:
        depts.append(("dot", "Driveway/Access Review", (5, 14)))
    if random.random() < 0.2:
        depts.append(("boe", "Grading Plan Review", (10, 30)))

    # Historic properties → Cultural Affairs
    if project.get("is_historic"):
        depts.append(("cultural_affairs", "Cultural Resource Review", (10, 30)))

    # Some fire-damaged lots need tree work
    if random.random() < 0.25:
        depts.append(("urban_forestry", "Tree Removal Permit", (7, 21)))

    return depts


async def main():
    print("=" * 60)
    print("Generating clearances for existing projects...")
    print("=" * 60)

    # Check existing clearances
    async with async_session() as session:
        r = await session.execute(text("SELECT COUNT(*) FROM clearances"))
        existing = r.scalar()
        if existing > 0:
            print(f"  Already have {existing} clearances. Skipping generation.")
            print("  (Drop clearances table contents first if you want to regenerate)")
            await engine.dispose()
            return

    # Fetch all projects
    async with async_session() as session:
        result = await session.execute(text("""
            SELECT id, status, pathway, is_coastal_zone, is_very_high_fire_severity,
                   is_hillside, is_historic, created_at
            FROM projects
            ORDER BY created_at DESC
        """))
        projects = [dict(zip(
            ["id", "status", "pathway", "is_coastal_zone", "is_very_high_fire_severity",
             "is_hillside", "is_historic", "created_at"],
            row
        )) for row in result.fetchall()]

    print(f"  {len(projects)} projects to process")

    # Generate clearances in batches
    batch_size = 500
    total_clearances = 0
    total_bottlenecks = 0
    errors = 0
    now = datetime.now(timezone.utc)

    for batch_start in range(0, len(projects), batch_size):
        batch = projects[batch_start: batch_start + batch_size]
        rows = []

        for proj in batch:
            departments = pick_departments(proj)

            for dept, clearance_type, day_range in departments:
                status = pick_status(proj["status"])
                predicted_days = random.randint(*day_range)

                # Determine dates
                created = proj["created_at"] or now - timedelta(days=random.randint(1, 90))
                submitted = None
                completed = None

                if status != "not_started":
                    submitted = created + timedelta(days=random.randint(1, 7))
                if status in ("approved", "conditional", "denied"):
                    completed = submitted + timedelta(days=predicted_days) if submitted else None

                # 15% chance of bottleneck for in_review items
                is_bottleneck = status == "in_review" and random.random() < 0.15
                if is_bottleneck:
                    total_bottlenecks += 1

                rows.append({
                    "id": str(uuid.uuid4()),
                    "project_id": str(proj["id"]),
                    "department": dept,
                    "clearance_type": clearance_type,
                    "status": status,
                    "is_bottleneck": is_bottleneck,
                    "predicted_days": predicted_days,
                    "submitted_date": submitted,
                    "completed_date": completed,
                })

        # Batch insert
        async with async_session() as session:
            try:
                async with session.begin():
                    for row in rows:
                        await session.execute(
                            text("""
                                INSERT INTO clearances (
                                    id, project_id, department, clearance_type, status,
                                    is_bottleneck, predicted_days, submitted_date, completed_date,
                                    created_at, updated_at
                                ) VALUES (
                                    :id, :project_id, :department, :clearance_type, :status,
                                    :is_bottleneck, :predicted_days, :submitted_date, :completed_date,
                                    NOW(), NOW()
                                )
                            """),
                            row,
                        )
                    total_clearances += len(rows)
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"  [!] Batch error: {str(e)[:200]}")
                # Try one by one
                for row in rows:
                    async with async_session() as s2:
                        try:
                            async with s2.begin():
                                await s2.execute(
                                    text("""
                                        INSERT INTO clearances (
                                            id, project_id, department, clearance_type, status,
                                            is_bottleneck, predicted_days, submitted_date, completed_date,
                                            created_at, updated_at
                                        ) VALUES (
                                            :id, :project_id, :department, :clearance_type, :status,
                                            :is_bottleneck, :predicted_days, :submitted_date, :completed_date,
                                            NOW(), NOW()
                                        )
                                    """),
                                    row,
                                )
                            total_clearances += 1
                        except Exception:
                            pass

        if (batch_start // batch_size) % 20 == 0:
            print(f"  ... {total_clearances:,} clearances generated ({batch_start + len(batch):,}/{len(projects):,} projects)")

    # Also generate some inspections for issued/final projects
    print(f"\nGenerating inspections for issued/final projects...")
    async with async_session() as session:
        result = await session.execute(text("""
            SELECT id, status, created_at FROM projects
            WHERE status IN ('issued', 'final', 'inspection')
            ORDER BY created_at DESC
        """))
        issued_projects = result.fetchall()

    insp_count = 0
    insp_types = ["Foundation", "Framing", "Electrical Rough", "Plumbing Rough",
                  "Mechanical Rough", "Insulation", "Drywall", "Final"]

    for proj_id, proj_status, created_at in issued_projects:
        # Each issued project gets 2-6 inspections
        num_inspections = random.randint(2, 6)
        base_date = (created_at or now) + timedelta(days=random.randint(30, 120))

        for i in range(num_inspections):
            insp_type = insp_types[min(i, len(insp_types) - 1)]

            if proj_status == "final" or (proj_status == "issued" and random.random() < 0.7):
                status = random.choices(["passed", "failed"], weights=[0.82, 0.18], k=1)[0]
            else:
                status = "scheduled"

            scheduled = base_date + timedelta(days=i * random.randint(7, 21))
            completed = scheduled if status in ("passed", "failed") else None

            failure_reasons = None
            if status == "failed":
                reasons = [
                    "Framing not per approved plans",
                    "Missing fire blocking",
                    "Incorrect nail spacing",
                    "GFCI not installed in wet area",
                    "Insulation R-value below requirement",
                    "Smoke detector not in required location",
                ]
                failure_reasons = [random.choice(reasons)]

            row = {
                "id": str(uuid.uuid4()),
                "project_id": str(proj_id),
                "inspection_type": insp_type,
                "status": status,
                "scheduled_date": scheduled,
                "completed_date": completed,
                "inspector_name": random.choice(["J. Rodriguez", "M. Chen", "K. Williams", "S. Patel", "R. Thompson"]),
                "notes": f"{'FAILED: ' + failure_reasons[0] if failure_reasons else 'Passed - all items satisfactory'}",
            }

            async with async_session() as session:
                try:
                    async with session.begin():
                        await session.execute(
                            text("""
                                INSERT INTO inspections (
                                    id, project_id, inspection_type, status,
                                    scheduled_date, completed_date, inspector_name,
                                    notes, created_at, updated_at
                                ) VALUES (
                                    :id, :project_id, :inspection_type, :status,
                                    :scheduled_date, :completed_date, :inspector_name,
                                    :notes, NOW(), NOW()
                                )
                            """),
                            row,
                        )
                    insp_count += 1
                except Exception:
                    pass

        if insp_count % 5000 == 0 and insp_count > 0:
            print(f"  ... {insp_count:,} inspections generated")

    # Final summary
    async with async_session() as session:
        for tbl in ["projects", "parcels", "clearances", "inspections", "audit_log"]:
            r = await session.execute(text(f"SELECT COUNT(*) FROM {tbl}"))
            print(f"  {tbl}: {r.scalar():,}")

        r = await session.execute(text("""
            SELECT department, status, COUNT(*) FROM clearances
            GROUP BY department, status ORDER BY department, status
        """))
        print("\n  Clearances by department/status:")
        for dept, status, cnt in r.fetchall():
            print(f"    {dept}/{status}: {cnt:,}")

        r = await session.execute(text("SELECT COUNT(*) FROM clearances WHERE is_bottleneck"))
        print(f"\n  Bottlenecks: {r.scalar():,}")

        r = await session.execute(text("""
            SELECT status, COUNT(*) FROM inspections GROUP BY status ORDER BY COUNT(*) DESC
        """))
        print("\n  Inspections by status:")
        for status, cnt in r.fetchall():
            print(f"    {status}: {cnt:,}")

    print(f"\n{'='*60}")
    print(f"DONE: {total_clearances:,} clearances, {insp_count:,} inspections")
    print(f"{'='*60}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
