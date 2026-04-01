"""Airflow DAG: LADBS Permit Poller.

Polls the Socrata Open Data API every 15 minutes for new/updated permit
records, transforms them, and upserts into the PermitAI database.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from airflow import DAG
from airflow.decorators import task
from airflow.models import Variable

default_args = {
    "owner": "permitai",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}

# Palisades-area ZIP codes for focused polling.
PALISADES_ZIP_CODES = ["90272", "90049", "90402"]


def _get_last_success_ts() -> datetime:
    raw = Variable.get("ladbs_permit_poller_last_success_ts", default_var=None)
    if raw:
        return datetime.fromisoformat(raw)
    # Default: look back 1 hour on first run.
    return datetime.now(timezone.utc) - timedelta(hours=1)


def _set_last_success_ts(ts: datetime) -> None:
    Variable.set("ladbs_permit_poller_last_success_ts", ts.isoformat())


with DAG(
    dag_id="ladbs_permit_poller",
    default_args=default_args,
    description="Poll LADBS Socrata API for new/updated permits every 15 min",
    schedule="*/15 * * * *",
    start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    tags=["ingestion", "ladbs", "permits"],
    max_active_runs=1,
) as dag:

    @task()
    def extract(**context) -> list[dict]:
        """Fetch raw permit records from the Socrata API."""
        from app.ingestion.socrata_client import SocrataClient

        since = _get_last_success_ts()

        async def _run() -> list[dict]:
            async with SocrataClient() as client:
                return await client.fetch_permits(
                    since=since,
                    zip_codes=PALISADES_ZIP_CODES,
                )

        records = asyncio.run(_run())
        context["ti"].xcom_push(key="record_count", value=len(records))
        return records

    @task()
    def transform(raw_records: list[dict]) -> list[dict]:
        """Normalise, map statuses, de-duplicate."""
        from app.ingestion.transformers import (
            deduplicate_key,
            map_permit_status,
            normalize_address,
            parse_socrata_date,
        )

        seen_keys: set[str] = set()
        transformed: list[dict] = []

        for rec in raw_records:
            key = deduplicate_key(rec)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            transformed.append(
                {
                    "ladbs_permit_number": key,
                    "address": normalize_address(rec.get("address", "")),
                    "status": map_permit_status(rec.get("status", "")),
                    "description": rec.get("permit_type_descr") or rec.get("work_description"),
                    "application_date": parse_socrata_date(
                        rec.get("application_date", "")
                    ),
                    "issued_date": parse_socrata_date(rec.get("issue_date", "")),
                }
            )

        return transformed

    @task()
    def load(records: list[dict]) -> int:
        """Upsert transformed records into the database."""
        from app.core.database import async_session_factory
        from app.core.s3 import get_s3_client
        from app.ingestion.loaders import dead_letter, upsert_permits

        s3 = get_s3_client()

        async def _run() -> int:
            failed: list[dict] = []
            async with async_session_factory() as session:
                try:
                    count = await upsert_permits(session, records)
                    await session.commit()
                except Exception as exc:
                    await session.rollback()
                    # Attempt individual inserts so we can isolate bad rows.
                    count = 0
                    for rec in records:
                        try:
                            async with async_session_factory() as s2:
                                count += await upsert_permits(s2, [rec])
                                await s2.commit()
                        except Exception as inner_exc:
                            failed.append(rec)
                            await dead_letter(rec, str(inner_exc), s3)

            # Persist last-success timestamp on any successful load.
            if count > 0:
                _set_last_success_ts(datetime.now(timezone.utc))

            return count

        return asyncio.run(_run())

    raw = extract()
    clean = transform(raw)
    load(clean)
