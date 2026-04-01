"""LADBS Open Data (Socrata) client for permit record ingestion."""

from __future__ import annotations

import asyncio
from datetime import datetime

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

SOCRATA_BASE_URL = "https://data.lacity.org/resource"
DEFAULT_PAGE_SIZE = 1000
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 2
RATE_LIMIT_SLEEP_SECONDS = 60


class SocrataClient:
    """Async client for the LA City Socrata Open Data API (LADBS permits)."""

    def __init__(
        self,
        app_token: str | None = None,
        dataset_id: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._app_token = app_token or settings.SOCRATA_APP_TOKEN
        self._dataset_id = dataset_id or settings.SOCRATA_DATASET_ID
        self._base_url = f"{SOCRATA_BASE_URL}/{self._dataset_id}.json"
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={"Accept": "application/json"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> SocrataClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #

    async def fetch_permits(
        self,
        since: datetime,
        zip_codes: list[str] | None = None,
    ) -> list[dict]:
        """Fetch all permit records updated after *since*.

        Paginates through the Socrata API using ``$offset`` / ``$limit``
        until fewer than ``DEFAULT_PAGE_SIZE`` records are returned.
        """
        all_records: list[dict] = []
        offset = 0

        while True:
            params = self._build_params(since, zip_codes, offset)
            data = await self._request_with_retry(params)

            if data is None:
                # Exhausted retries on a non-recoverable error; stop paging.
                logger.warning(
                    "socrata.page_failed",
                    offset=offset,
                    msg="Stopping pagination after unrecoverable error",
                )
                break

            all_records.extend(data)
            logger.info(
                "socrata.page_fetched",
                offset=offset,
                page_size=len(data),
                total_so_far=len(all_records),
            )

            if len(data) < DEFAULT_PAGE_SIZE:
                break
            offset += DEFAULT_PAGE_SIZE

        return all_records

    # --------------------------------------------------------------------- #
    # Internals
    # --------------------------------------------------------------------- #

    def _build_params(
        self,
        since: datetime,
        zip_codes: list[str] | None,
        offset: int,
    ) -> dict[str, str]:
        where_clauses: list[str] = [
            f":updated_at > '{since.isoformat()}'",
        ]
        if zip_codes:
            quoted = ", ".join(f"'{z}'" for z in zip_codes)
            where_clauses.append(f"zip_code IN ({quoted})")

        params: dict[str, str] = {
            "$where": " AND ".join(where_clauses),
            "$order": ":updated_at ASC",
            "$limit": str(DEFAULT_PAGE_SIZE),
            "$offset": str(offset),
        }
        if self._app_token:
            params["$$app_token"] = self._app_token

        return params

    async def _request_with_retry(self, params: dict[str, str]) -> list[dict] | None:
        """Issue a GET request with exponential backoff and special 429 handling."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await self._client.get(self._base_url, params=params)

                if response.status_code == 200:
                    return response.json()

                if response.status_code == 429:
                    logger.warning(
                        "socrata.rate_limited",
                        attempt=attempt,
                        sleep_seconds=RATE_LIMIT_SLEEP_SECONDS,
                    )
                    await asyncio.sleep(RATE_LIMIT_SLEEP_SECONDS)
                    continue

                if response.status_code in {500, 503}:
                    backoff = BACKOFF_BASE_SECONDS ** attempt
                    logger.warning(
                        "socrata.server_error",
                        status=response.status_code,
                        attempt=attempt,
                        backoff=backoff,
                    )
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(backoff)
                        continue
                    # Final attempt exhausted -- skip this page.
                    logger.error(
                        "socrata.server_error_exhausted",
                        status=response.status_code,
                    )
                    return None

                # Unexpected status code
                logger.error(
                    "socrata.unexpected_status",
                    status=response.status_code,
                    body=response.text[:500],
                )
                return None

            except httpx.HTTPError as exc:
                backoff = BACKOFF_BASE_SECONDS ** attempt
                logger.warning(
                    "socrata.http_error",
                    error=str(exc),
                    attempt=attempt,
                    backoff=backoff,
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(backoff)
                    continue
                logger.error("socrata.http_error_exhausted", error=str(exc))
                return None

        return None
