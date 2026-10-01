import boto3
from botocore.client import Config

from app.core.config import settings

BUCKET = "exports"

_s3 = boto3.client(
    "s3",
    endpoint_url=settings.AWS_ENDPOINT_URL_S3,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION,
    config=Config(signature_version="s3v4"),
)


def upload_csv(file: bytes, file_path: str) -> str:
    _s3.put_object(
        Bucket=BUCKET,
        Key=file_path,
        Body=file,
        ContentType="text/csv",
    )
    return f"{settings.AWS_ENDPOINT_URL_S3}/{BUCKET}/{file_path}"
