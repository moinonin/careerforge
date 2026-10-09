"""Artifact storage abstraction — LocalStorage (dev) and S3Storage (prod).

Selected via settings: if ``s3_endpoint_url`` (or AWS creds + bucket) are
configured, artifacts are uploaded to S3/MinIO; otherwise they stay on the
local filesystem under ``settings.generation_artifacts_dir``.

``save_file(path, key)`` returns a stored reference:
  - LocalStorage → absolute local filesystem path
  - S3Storage    → S3 object key stored as ``s3://<bucket>/<key>``

GenerationJob/StoredArtifact ``*_url`` columns hold that reference. The
download endpoints transparently handle both: local paths are read from
disk; ``s3://`` references are turned into presigned GET URLs (redirect).
"""

from __future__ import annotations

import os
from typing import Protocol

from backend.config import settings


class StorageBackend(Protocol):
    """Minimal artifact storage interface."""

    def save_file(self, local_path: str, key: str) -> str:
        """Persist *local_path* under *key*; return the stored reference."""
        ...

    def exists(self, ref: str) -> bool:
        """Return True if the artifact referenced by *ref* is retrievable."""
        ...

    def read_bytes(self, ref: str) -> bytes:
        """Read the artifact's bytes."""
        ...


class LocalStorage:
    """Store artifacts on the local filesystem (dev default)."""

    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def _path(self, key: str) -> str:
        return os.path.join(self.base_dir, key)

    def save_file(self, local_path: str, key: str) -> str:
        src = os.path.abspath(local_path)
        if not src.startswith(os.path.abspath(self.base_dir)):
            # Copy into the artifacts dir when the source lives elsewhere
            dest = self._path(key)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(src, "rb") as f_src, open(dest, "wb") as f_dst:
                f_dst.write(f_src.read())
            return dest
        return src

    def exists(self, ref: str) -> bool:
        return os.path.isfile(ref)

    def read_bytes(self, ref: str) -> bytes:
        with open(ref, "rb") as f:
            return f.read()


class S3Storage:
    """Store artifacts in S3/MinIO (production). References are s3:// URIs."""

    def __init__(self) -> None:
        import boto3

        self._bucket = settings.s3_bucket_name
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            region_name=settings.s3_region,
        )

    def save_file(self, local_path: str, key: str) -> str:
        self._client.upload_file(local_path, self._bucket, key)
        return f"s3://{self._bucket}/{key}"

    def exists(self, ref: str) -> bool:
        if not ref.startswith("s3://"):
            return os.path.isfile(ref)
        bucket, key = ref[5:].split("/", 1)
        try:
            self._client.head_object(Bucket=bucket, Key=key)
            return True
        except self._client.exceptions.ClientError:
            return False

    def read_bytes(self, ref: str) -> bytes:
        if not ref.startswith("s3://"):
            with open(ref, "rb") as f:
                return f.read()
        bucket, key = ref[5:].split("/", 1)
        obj = self._client.get_object(Bucket=bucket, Key=key)
        return obj["Body"].read()

    def presigned_url(self, ref: str, expires_in: int = 3600) -> str:
        """Return a presigned GET URL for an s3:// reference."""
        bucket, key = ref[5:].split("/", 1)
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )


_storage: StorageBackend | None = None


def get_storage() -> StorageBackend:
    """Return the configured storage backend (cached singleton)."""
    global _storage
    if _storage is None:
        if settings.s3_access_key_id and settings.s3_bucket_name:
            _storage = S3Storage()
        else:
            _storage = LocalStorage(settings.generation_artifacts_dir)
    return _storage


def reset_storage() -> None:
    """Drop the cached singleton (tests)."""
    global _storage
    _storage = None
