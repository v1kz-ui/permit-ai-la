import boto3
from botocore.config import Config

from app.config import settings

_s3_client = None


def get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            region_name=settings.AWS_REGION,
            config=Config(
                retries={"max_attempts": 3, "mode": "adaptive"},
                signature_version="s3v4",
            ),
        )
    return _s3_client


def generate_presigned_upload_url(
    bucket: str, key: str, content_type: str, expires_in: int = 3600
) -> str:
    client = get_s3_client()
    return client.generate_presigned_url(
        "put_object",
        Params={"Bucket": bucket, "Key": key, "ContentType": content_type},
        ExpiresIn=expires_in,
    )


def generate_presigned_download_url(bucket: str, key: str, expires_in: int = 3600) -> str:
    client = get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )
