import logging
import uuid
from typing import AsyncGenerator

import aioboto3
from botocore.config import Config as BotoConfig

from backend.config import get_settings

logger = logging.getLogger(__name__)

class FileService:
    def __init__(self):
        self.settings = get_settings()
        self.session = aioboto3.Session()

    def _client_kwargs(self) -> dict:
        kwargs = {
            "region_name": self.settings.aws_region,
            "aws_access_key_id": self.settings.aws_access_key_id,
            "aws_secret_access_key": self.settings.aws_secret_access_key,
        }
        if self.settings.s3_endpoint_url:
            kwargs["endpoint_url"] = self.settings.s3_endpoint_url
            kwargs["config"] = BotoConfig(s3={"addressing_style": "path"})
        return kwargs
    
    def generate_s3_key(self, location_slug: str, filename: str) -> str:
        """Generate a unique S3 key for an upload."""
        unique_id = uuid.uuid4().hex[:12]
        return f"uploads/{location_slug}/{unique_id}/{filename}"
    
    async def upload_file(
            self, s3_key: str, file_data: bytes, content_type: str
    ) -> None:
        """Upload file bytes to S3."""
        async with self.session.client("s3", **self._client_kwargs()) as s3:
            await s3.put_object(
                Bucket=self.settings.s3_bucket,
                Key=s3_key,
                Body=file_data,
                ContentType=content_type,
            )
    
    async def stream_file(self, s3_key: str) -> AsyncGenerator[bytes, None]:
        """Stream file from S3 in chunks for proxy delivery."""
        async with self.session.client("s3", **self._client_kwargs()) as s3:
            response = await s3.get_object(
                Bucket=self.settings.s3_bucket,
                Key=s3_key,
            )
            async with response["Body"] as stream:
                while chunk := await stream.read(64 * 1024):
                    yield chunk
    
    async def delete_file(self, s3_key: str) -> None:
        """Delete a file from S3 (for hard cleanup if ever needed)."""
        async with self.session.clinet("s3", **self._client_kwargs()) as s3:
            await s3.delete_object(
                Bucket=self.settings.s3_bucket,
                Key=s3_key,
            )
    
async def ensure_bucket_exists(self) -> None:
    """Create bucket if it doesn't exist. 
    Works with MinIO locally. On R2, bucket should already exist
    (created through the dashboard), so this just verifies.
    """
    async with self.session.client("s3", **self._client_kwargs()) as s3:
        try:
            await s3.head_bucket(Bucket=self.settings.s3_bucket)
        except Exception:
            try:
                await s3.create_bucket(Bucket=self.settings.s3_bucket)
            except Exception as e:
                # R2 may reject create_bucket via API — that's fine 
                # if the bucket was created through the dashboard
                logger.warning(f"Could not create bucket: {e}")

file_service = FileService()