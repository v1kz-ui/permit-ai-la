"""Database backup utilities for PostgreSQL with S3 storage."""

import datetime
from typing import Any

import structlog

from app.config import settings
from app.core.s3 import get_s3_client

logger = structlog.get_logger()

BACKUP_BUCKET = f"permitai-backups-{settings.ENVIRONMENT}"


class BackupService:
    """Service for managing PostgreSQL database backups via S3."""

    def __init__(self, bucket: str = BACKUP_BUCKET):
        self.bucket = bucket

    def create_backup(self) -> dict[str, str]:
        """Generate pg_dump command configuration for creating a backup.

        Returns a dict with the command, S3 destination, and timestamp.
        This does NOT execute the command; it is intended to be run by
        an operator or a scheduled CI/CD job.
        """
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        s3_key = f"backups/permitai_{timestamp}.sql.gz"

        # Parse database URL components for pg_dump
        db_url = settings.DATABASE_URL_SYNC
        command = (
            f"pg_dump '{db_url}' "
            f"--format=custom --compress=9 --no-owner --no-acl "
            f"| aws s3 cp - s3://{self.bucket}/{s3_key}"
        )

        return {
            "command": command,
            "s3_bucket": self.bucket,
            "s3_key": s3_key,
            "timestamp": timestamp,
            "note": "Run this command from a host with database network access and AWS credentials.",
        }

    def list_backups(self) -> list[dict[str, Any]]:
        """List available backups in the S3 bucket."""
        client = get_s3_client()
        try:
            response = client.list_objects_v2(
                Bucket=self.bucket,
                Prefix="backups/",
            )
        except Exception as exc:
            logger.warning("Failed to list backups", error=str(exc))
            return []

        objects = response.get("Contents", [])
        return [
            {
                "key": obj["Key"],
                "size_mb": round(obj["Size"] / 1024 / 1024, 2),
                "last_modified": obj["LastModified"].isoformat(),
            }
            for obj in sorted(objects, key=lambda o: o["LastModified"], reverse=True)
        ]

    def restore_backup(self, backup_key: str) -> dict[str, str]:
        """Generate pg_restore command configuration for restoring a backup.

        Args:
            backup_key: The S3 object key of the backup to restore.

        Returns a dict with the command and source info.
        """
        db_url = settings.DATABASE_URL_SYNC
        command = (
            f"aws s3 cp s3://{self.bucket}/{backup_key} - "
            f"| pg_restore --dbname='{db_url}' --no-owner --no-acl --clean --if-exists"
        )

        return {
            "command": command,
            "s3_bucket": self.bucket,
            "s3_key": backup_key,
            "note": "WARNING: This will overwrite existing data. Run from a host with DB access and AWS credentials.",
        }

    def cleanup_old_backups(self, retention_days: int = 30) -> list[dict[str, Any]]:
        """List S3 backup objects older than the retention period.

        Returns a list of objects that are candidates for deletion.
        Does NOT delete them automatically; the caller should confirm and delete.
        """
        client = get_s3_client()
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=retention_days)

        try:
            response = client.list_objects_v2(
                Bucket=self.bucket,
                Prefix="backups/",
            )
        except Exception as exc:
            logger.warning("Failed to list backups for cleanup", error=str(exc))
            return []

        objects = response.get("Contents", [])
        expired = []
        for obj in objects:
            last_modified = obj["LastModified"].replace(tzinfo=None)
            if last_modified < cutoff:
                expired.append({
                    "key": obj["Key"],
                    "size_mb": round(obj["Size"] / 1024 / 1024, 2),
                    "last_modified": obj["LastModified"].isoformat(),
                    "age_days": (datetime.datetime.utcnow() - last_modified).days,
                })

        return expired
