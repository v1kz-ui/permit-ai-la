"""PCIS (Plan Check & Inspection System) clearance scraper.

This is a *fallback* data source used when the LADBS API does not expose
clearance-level detail.  The scraper POSTs to the public PermitLA / IPARS
portal and parses the HTML response with BeautifulSoup.
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
import structlog
from bs4 import BeautifulSoup

logger = structlog.get_logger(__name__)

PCIS_URL = "https://www.permitla.org/ipars"
MIN_REQUEST_INTERVAL = 3.0  # seconds between requests

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


@dataclass
class ClearanceItem:
    """A single clearance row scraped from PCIS."""

    department: str
    clearance_type: str
    status: str
    case_number: str | None = None
    notes: str | None = None


@dataclass
class ChangeResult:
    """Describes the differences between two clearance snapshots."""

    added: list[ClearanceItem] = field(default_factory=list)
    removed: list[ClearanceItem] = field(default_factory=list)
    status_changed: list[tuple[ClearanceItem, ClearanceItem]] = field(default_factory=list)


class PcisScraper:
    """Rate-limited scraper for the PCIS clearance portal."""

    def __init__(self, timeout: float = 30.0) -> None:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
        )
        self._last_request_time: float = 0.0

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> PcisScraper:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def scrape_clearances(self, permit_number: str) -> list[ClearanceItem]:
        """POST to the PCIS portal and return parsed clearance rows."""
        await self._enforce_rate_limit()

        headers = {
            "User-Agent": random.choice(_USER_AGENTS),
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": PCIS_URL,
        }
        form_data = {
            "permitNumber": permit_number,
            "action": "search",
        }

        try:
            response = await self._client.post(
                PCIS_URL,
                data=form_data,
                headers=headers,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error(
                "pcis.request_failed",
                permit_number=permit_number,
                error=str(exc),
            )
            return []

        self._last_request_time = time.monotonic()
        return self._parse_clearances(response.text, permit_number)

    @staticmethod
    def detect_changes(
        new_clearances: list[ClearanceItem],
        existing_clearances: list[ClearanceItem],
    ) -> ChangeResult:
        """Compare two clearance lists and return the diff."""

        def _key(c: ClearanceItem) -> str:
            return f"{c.department}|{c.clearance_type}"

        new_map = {_key(c): c for c in new_clearances}
        old_map = {_key(c): c for c in existing_clearances}

        result = ChangeResult()

        for k, item in new_map.items():
            if k not in old_map:
                result.added.append(item)
            elif old_map[k].status != item.status:
                result.status_changed.append((old_map[k], item))

        for k, item in old_map.items():
            if k not in new_map:
                result.removed.append(item)

        return result

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    async def _enforce_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < MIN_REQUEST_INTERVAL:
            wait = MIN_REQUEST_INTERVAL - elapsed
            logger.debug("pcis.rate_limit_wait", wait_seconds=round(wait, 2))
            await asyncio.sleep(wait)

    @staticmethod
    def _parse_clearances(html: str, permit_number: str) -> list[ClearanceItem]:
        """Extract clearance rows from the HTML response."""
        soup = BeautifulSoup(html, "html.parser")
        items: list[ClearanceItem] = []

        # The clearance table is typically the first <table> with class
        # "clearance-table" or a table inside a div#clearanceResults.
        table = (
            soup.find("table", class_="clearance-table")
            or soup.select_one("#clearanceResults table")
            or soup.find("table")
        )

        if table is None:
            logger.warning("pcis.no_table_found", permit_number=permit_number)
            return items

        rows = table.find_all("tr")[1:]  # skip header row
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 3:
                continue
            items.append(
                ClearanceItem(
                    department=cells[0].get_text(strip=True),
                    clearance_type=cells[1].get_text(strip=True),
                    status=cells[2].get_text(strip=True),
                    case_number=cells[3].get_text(strip=True) if len(cells) > 3 else None,
                    notes=cells[4].get_text(strip=True) if len(cells) > 4 else None,
                )
            )

        logger.info(
            "pcis.parsed",
            permit_number=permit_number,
            clearance_count=len(items),
        )
        return items
