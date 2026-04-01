"""FIMS (Fire Inspection Management System) integration client (stub).

FIMS is the Los Angeles Fire Department's system for managing fire
inspections and clearances. Once API access is granted, this client
will allow PermitAI to check fire-clearance status and request
inspections on behalf of homeowners.
"""

import structlog

logger = structlog.get_logger()


class FimsClient:
    """Stub client for the LAFD FIMS system.

    All methods raise ``NotImplementedError`` until the department
    provides API credentials and documentation.
    """

    async def get_fire_clearance_status(self, address: str) -> dict:
        """Look up the fire-clearance status for a given address.

        When implemented this method will:
        1. Authenticate with the FIMS API.
        2. Query clearance records by normalised address.
        3. Return a dict with fields such as ``clearance_status``,
           ``inspection_date``, ``inspector``, ``conditions``,
           and ``expiration_date``.

        Args:
            address: Property street address to look up.

        Returns:
            A dict containing fire-clearance information.

        Raises:
            NotImplementedError: Always, until API access is available.
        """
        raise NotImplementedError("FIMS integration pending API access")

    async def submit_fire_inspection_request(self, project_id: str) -> str:
        """Submit a fire inspection request for a project.

        When implemented this method will:
        1. Authenticate with the FIMS API.
        2. Create an inspection request linked to the project's
           address and permit number.
        3. Return the FIMS request ID for tracking.

        Args:
            project_id: PermitAI project UUID.

        Returns:
            A FIMS request ID string.

        Raises:
            NotImplementedError: Always, until API access is available.
        """
        raise NotImplementedError("FIMS integration pending API access")
