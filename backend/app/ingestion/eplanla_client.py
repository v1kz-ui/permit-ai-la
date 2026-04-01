"""ePlanLA integration client (stub).

ePlanLA is the City of Los Angeles electronic plan-check submission
system. Once API access is granted, this client will allow PermitAI
to submit plan-check documents on behalf of homeowners and poll for
review status updates.
"""

import structlog

logger = structlog.get_logger()


class EPlanlaClient:
    """Stub client for the ePlanLA plan-check system.

    All methods raise ``NotImplementedError`` until the City provides
    API credentials and documentation.
    """

    async def submit_plan_check(
        self, project_id: str, documents: list[dict]
    ) -> str:
        """Submit documents to ePlanLA for electronic plan check.

        When implemented this method will:
        1. Authenticate with the ePlanLA API using city-issued credentials.
        2. Package the provided documents (S3 keys / URLs) into the
           required submission format.
        3. POST the submission to the ePlanLA intake endpoint.
        4. Return the ePlanLA tracking number for status polling.

        Args:
            project_id: PermitAI project UUID.
            documents: List of dicts with keys ``s3_key``, ``filename``,
                and ``document_type`` describing the files to submit.

        Returns:
            An ePlanLA tracking number string.

        Raises:
            NotImplementedError: Always, until API access is available.
        """
        raise NotImplementedError("ePlanLA integration pending API access")

    async def check_status(self, tracking_number: str) -> dict:
        """Check the review status of a previously submitted plan check.

        When implemented this method will:
        1. Query the ePlanLA status endpoint with the tracking number.
        2. Parse the response into a normalised status dict containing
           fields such as ``status``, ``reviewer``, ``comments``,
           ``estimated_completion_date``.

        Args:
            tracking_number: The tracking number returned by
                :meth:`submit_plan_check`.

        Returns:
            A dict with current review status details.

        Raises:
            NotImplementedError: Always, until API access is available.
        """
        raise NotImplementedError("ePlanLA integration pending API access")
