"""Airflow DAG: ZIMAS Parcel Cache Refresh.

Runs daily at 03:00 UTC to refresh the full set of parcels for both
fire-affected communities — Pacific Palisades and Altadena — from the
LA GeoHub ArcGIS REST service.

The critical difference from the old stub:
  - Raw ArcGIS GeoJSON geometry is converted to PostGIS WKT via zimas_loader
  - Both Palisades AND Altadena are refreshed
  - Geometry-less parcels are stored (NULL geom) rather than dropped
  - Run stats (upserted / skipped / errors) posted as Airflow XComs
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from airflow import DAG
from airflow.decorators import task
from airflow.models import Variable
from airflow.utils.trigger_rule import TriggerRule

log = logging.getLogger(__name__)

default_args = {
    "owner": "permitai",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
    "execution_timeout": timedelta(hours=2),
}

# Community plan areas whose parcels we cache.
# Altadena is technically unincorporated LA County but the GeoHub service
# covers it under the same endpoint.
COMMUNITY_PLAN_AREAS = [
    "Palisades",
    "Altadena",
]


def _run_async(coro):
    """Run an async coroutine from a synchronous Airflow task."""
    return asyncio.run(coro)


with DAG(
    dag_id="zimas_cache_refresh",
    default_args=default_args,
    description="Daily refresh of Palisades + Altadena parcel data from ZIMAS / GeoHub",
    schedule="0 3 * * *",
    start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    tags=["ingestion", "zimas", "parcels"],
    max_active_runs=1,
    doc_md="""
## ZIMAS Cache Refresh

Fetches all parcels for **Pacific Palisades** and **Altadena** from the LA City
GeoHub ArcGIS REST API and upserts them into the `parcels` table with full
PostGIS geometry.

**Source:** https://geohub.lacity.org
**Schedule:** Daily at 03:00 UTC
**Coverage:** ~15,000 Palisades parcels + ~10,000 Altadena parcels
    """,
) as dag:

    @task()
    def fetch_palisades() -> list[dict]:
        """Fetch all parcels for Pacific Palisades."""
        from app.ingestion.zimas_client import ZimasClient

        async def _run():
            async with ZimasClient() as client:
                return await client.fetch_parcels_bulk("Palisades")

        results = _run_async(_run())
        log.info("Fetched %d Palisades parcel features", len(results))
        return results

    @task()
    def fetch_altadena() -> list[dict]:
        """Fetch all parcels for Altadena."""
        from app.ingestion.zimas_client import ZimasClient

        async def _run():
            async with ZimasClient() as client:
                return await client.fetch_parcels_bulk("Altadena")

        results = _run_async(_run())
        log.info("Fetched %d Altadena parcel features", len(results))
        return results

    @task()
    def upsert_palisades(features: list[dict]) -> dict:
        """Upsert Palisades parcel features into the parcels table."""
        from app.core.database import async_session_factory
        from app.ingestion.zimas_loader import upsert_parcels

        async def _run():
            async with async_session_factory() as session:
                upserted, skipped = await upsert_parcels(session, features)
                await session.commit()
                return {"community": "Palisades", "upserted": upserted, "skipped": skipped}

        result = _run_async(_run())
        log.info(
            "Palisades upsert complete: %d upserted, %d skipped",
            result["upserted"],
            result["skipped"],
        )
        return result

    @task()
    def upsert_altadena(features: list[dict]) -> dict:
        """Upsert Altadena parcel features into the parcels table."""
        from app.core.database import async_session_factory
        from app.ingestion.zimas_loader import upsert_parcels

        async def _run():
            async with async_session_factory() as session:
                upserted, skipped = await upsert_parcels(session, features)
                await session.commit()
                return {"community": "Altadena", "upserted": upserted, "skipped": skipped}

        result = _run_async(_run())
        log.info(
            "Altadena upsert complete: %d upserted, %d skipped",
            result["upserted"],
            result["skipped"],
        )
        return result

    @task(trigger_rule=TriggerRule.ALL_DONE)
    def summarize(palisades_result: dict, altadena_result: dict) -> dict:
        """Log a combined summary and push metrics to Airflow Variables."""
        total_upserted = palisades_result.get("upserted", 0) + altadena_result.get("upserted", 0)
        total_skipped = palisades_result.get("skipped", 0) + altadena_result.get("skipped", 0)

        summary = {
            "run_at": datetime.now(timezone.utc).isoformat(),
            "total_upserted": total_upserted,
            "total_skipped": total_skipped,
            "communities": [palisades_result, altadena_result],
        }

        # Persist last-run stats so the monitoring endpoint can read them
        try:
            Variable.set("zimas_last_sync_summary", str(summary))
        except Exception as exc:
            log.warning("Could not save Airflow Variable: %s", exc)

        log.info(
            "ZIMAS refresh complete: %d total upserted, %d skipped",
            total_upserted,
            total_skipped,
        )
        return summary

    # Wire the DAG: run both communities in parallel, then summarize
    pal_raw = fetch_palisades()
    alt_raw = fetch_altadena()
    pal_result = upsert_palisades(pal_raw)
    alt_result = upsert_altadena(alt_raw)
    summarize(pal_result, alt_result)
