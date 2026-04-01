"""Airflow DAG: PCIS Clearance Scanner.

Runs 3x daily (8 AM, 2 PM, 8 PM UTC) to scrape clearance status from
the PCIS portal for all active permits and detect changes.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import structlog
from airflow import DAG
from airflow.decorators import task

logger = structlog.get_logger(__name__)

default_args = {
    "owner": "permitai",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id="pcis_clearance_scan",
    default_args=default_args,
    description="Scrape PCIS clearances for active permits 3x/day",
    schedule="0 8,14,20 * * *",
    start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    tags=["ingestion", "pcis", "clearances"],
    max_active_runs=1,
) as dag:

    @task()
    def get_active_permits() -> list[dict]:
        """Query the database for all active permits that need clearance scanning."""
        from sqlalchemy import select

        from app.core.database import async_session_factory
        from app.models.project import Project

        active_statuses = [
            "plan_check",
            "clearances_in_progress",
            "ready_for_issue",
        ]

        async def _run() -> list[dict]:
            async with async_session_factory() as session:
                stmt = (
                    select(
                        Project.id,
                        Project.ladbs_permit_number,
                    )
                    .where(Project.status.in_(active_statuses))
                    .where(Project.ladbs_permit_number.isnot(None))
                )
                rows = (await session.execute(stmt)).all()
                return [
                    {"project_id": str(r.id), "permit_number": r.ladbs_permit_number}
                    for r in rows
                ]

        return asyncio.run(_run())

    @task()
    def scrape_clearances(permits: list[dict]) -> list[dict]:
        """Scrape PCIS for each active permit and return detected changes."""
        from app.ingestion.pcis_scraper import ClearanceItem, PcisScraper

        async def _run() -> list[dict]:
            changes: list[dict] = []

            async with PcisScraper() as scraper:
                for permit in permits:
                    permit_number = permit["permit_number"]
                    project_id = permit["project_id"]

                    new_items = await scraper.scrape_clearances(permit_number)
                    if not new_items:
                        continue

                    # Build the change payload.  On the first scan for a
                    # permit we treat every item as "added".
                    changes.append(
                        {
                            "project_id": project_id,
                            "permit_number": permit_number,
                            "clearances": [
                                {
                                    "department": c.department,
                                    "clearance_type": c.clearance_type,
                                    "status": c.status,
                                    "case_number": c.case_number,
                                    "notes": c.notes,
                                }
                                for c in new_items
                            ],
                        }
                    )

            return changes

        return asyncio.run(_run())

    @task()
    def persist_changes(change_sets: list[dict]) -> int:
        """Write detected clearance changes back to the database."""
        from uuid import UUID

        from sqlalchemy import select
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        from app.core.database import async_session_factory
        from app.ingestion.pcis_scraper import ClearanceItem, PcisScraper
        from app.models.clearance import Clearance

        async def _run() -> int:
            updated = 0
            async with async_session_factory() as session:
                for cs in change_sets:
                    project_id = UUID(cs["project_id"])

                    # Fetch existing clearances for this project to detect changes.
                    existing_stmt = select(Clearance).where(
                        Clearance.project_id == project_id
                    )
                    existing_rows = (await session.execute(existing_stmt)).scalars().all()
                    existing_items = [
                        ClearanceItem(
                            department=c.department,
                            clearance_type=c.clearance_type,
                            status=c.status,
                            case_number=c.pcis_case_number,
                        )
                        for c in existing_rows
                    ]

                    new_items = [
                        ClearanceItem(**item) for item in cs["clearances"]
                    ]

                    diff = PcisScraper.detect_changes(new_items, existing_items)

                    # Process status changes.
                    for old_item, new_item in diff.status_changed:
                        for row in existing_rows:
                            if (
                                row.department == old_item.department
                                and row.clearance_type == old_item.clearance_type
                            ):
                                row.status = new_item.status
                                row.pcis_last_sync = datetime.now(timezone.utc)
                                updated += 1

                    # Process newly added clearances.
                    for item in diff.added:
                        new_clearance = Clearance(
                            project_id=project_id,
                            department=item.department,
                            clearance_type=item.clearance_type,
                            status=item.status,
                            pcis_case_number=item.case_number,
                            pcis_last_sync=datetime.now(timezone.utc),
                        )
                        session.add(new_clearance)
                        updated += 1

                await session.commit()
            return updated

        return asyncio.run(_run())

    active = get_active_permits()
    scraped = scrape_clearances(active)
    persist_changes(scraped)
