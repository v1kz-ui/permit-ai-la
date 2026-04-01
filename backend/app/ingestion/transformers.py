"""Data transformation functions for LADBS permit records."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

import structlog

logger = structlog.get_logger(__name__)

# ------------------------------------------------------------------ #
# Street-suffix standardization map (USPS Publication 28)
# ------------------------------------------------------------------ #
_SUFFIX_MAP: dict[str, str] = {
    "AVENUE": "AVE",
    "AV": "AVE",
    "BOULEVARD": "BLVD",
    "CIRCLE": "CIR",
    "COURT": "CT",
    "DRIVE": "DR",
    "HIGHWAY": "HWY",
    "LANE": "LN",
    "PLACE": "PL",
    "ROAD": "RD",
    "STREET": "ST",
    "STR": "ST",
    "TERRACE": "TER",
    "TRAIL": "TRL",
    "WAY": "WAY",
}

# Regex to strip secondary-unit designators (Unit, Apt, #, Ste, etc.)
_UNIT_RE = re.compile(
    r"\s*[,#]?\s*(?:UNIT|APT|APARTMENT|STE|SUITE|BLDG|BUILDING|FL|FLOOR|RM|ROOM|SP|SPACE)\s*[#.]?\s*\S+\s*$",
    re.IGNORECASE,
)

# ------------------------------------------------------------------ #
# Permit-status mapping (Socrata -> internal canonical value)
# ------------------------------------------------------------------ #
_STATUS_MAP: dict[str, str] = {
    "CofO Issued": "final",
    "Issued": "issued",
    "Permit Finaled": "final",
    "Ready to Issue": "ready_for_issue",
    "Plan Check": "plan_check",
    "Application Submitted": "intake",
    "PC - Corrections Issued": "plan_check",
    "PC - Submitted for Recheck": "plan_check",
    "PC - Approved": "ready_for_issue",
    "Clearances In Process": "clearances_in_progress",
    "Expired": "closed",
    "Voided": "closed",
}


# ------------------------------------------------------------------ #
# Public API
# ------------------------------------------------------------------ #


def normalize_address(raw: str) -> str:
    """Uppercase, strip unit/apt info, and standardize street suffixes."""
    addr = raw.strip().upper()

    # Remove unit / apartment designator
    addr = _UNIT_RE.sub("", addr).strip()

    # Standardize suffixes
    tokens = addr.split()
    if tokens:
        last = tokens[-1].rstrip(".,")
        replacement = _SUFFIX_MAP.get(last)
        if replacement:
            tokens[-1] = replacement
    addr = " ".join(tokens)

    # Collapse whitespace
    addr = re.sub(r"\s+", " ", addr)
    return addr


def map_permit_status(socrata_status: str) -> str:
    """Map a Socrata permit-status string to an internal status enum value.

    Falls back to ``"intake"`` for unknown statuses.
    """
    return _STATUS_MAP.get(socrata_status, "intake")


def parse_socrata_date(ts: str) -> datetime | None:
    """Parse a Socrata floating-timestamp string into an aware UTC datetime.

    Socrata floating timestamps look like ``2024-01-15T00:00:00.000``
    (no timezone).  We treat them as UTC.
    """
    if not ts:
        return None
    try:
        # Try the full ISO format first (with optional fractional seconds)
        ts_clean = ts.strip()
        dt = datetime.fromisoformat(ts_clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        logger.warning("transformers.date_parse_failed", raw=ts)
        return None


def tag_fire_rebuild(
    permit_type: str,
    address: str,
    fire_zone_addresses: set[str],
) -> bool:
    """Return ``True`` if the permit looks like a fire-rebuild.

    Criteria:
    1. The normalized address is in the known fire-zone address set, **and**
    2. The permit type contains a rebuild/repair keyword.
    """
    rebuild_keywords = {"REBUILD", "REPAIR", "FIRE DAMAGE", "RESTORATION", "RECONSTRUCT"}
    upper_type = (permit_type or "").upper()
    if not any(kw in upper_type for kw in rebuild_keywords):
        return False

    normalized = normalize_address(address)
    return normalized in fire_zone_addresses


def deduplicate_key(record: dict) -> str:
    """Return a stable deduplication key for a permit record.

    Uses the permit number when present; otherwise falls back to a
    SHA-256 hash of address + permit type + date.
    """
    permit_number = record.get("permit_nbr") or record.get("permit_number")
    if permit_number:
        return str(permit_number).strip()

    # Fallback composite key
    parts = "|".join(
        str(record.get(f, ""))
        for f in ("address", "permit_type", "issue_date")
    )
    return hashlib.sha256(parts.encode()).hexdigest()[:24]
