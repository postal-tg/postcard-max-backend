from uuid import uuid4

import boto3
from botocore.client import Config

from postcard_backend.core.config import Settings


class ObjectStorage:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint_url,
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
            region_name=settings.storage_region,
            use_ssl=settings.storage_use_ssl,
            config=Config(signature_version="s3v4"),
        )

    def ensure_bucket(self) -> None:
        existing = [item["Name"] for item in self.client.list_buckets().get("Buckets", [])]
        if self.settings.storage_bucket not in existing:
            self.client.create_bucket(Bucket=self.settings.storage_bucket)

    def upload_bytes(self, content: bytes, content_type: str, prefix: str = "generated") -> tuple[str, str]:
        key = f"{prefix}/{uuid4().hex}.png"
        self.client.put_object(
            Bucket=self.settings.storage_bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )
        public_url = f"{self.settings.storage_public_base_url}/{self.settings.storage_bucket}/{key}"
        return key, public_url

    def download_bytes(self, key: str) -> tuple[bytes, str]:
        response = self.client.get_object(Bucket=self.settings.storage_bucket, Key=key)
        content = response["Body"].read()
        content_type = response.get("ContentType", "application/octet-stream")
        return content, content_type
