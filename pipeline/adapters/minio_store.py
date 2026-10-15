"""BlobStore adapter over MinIO (S3 API): a missing key becomes KeyError, other failures SnapshotError."""

import io
import os

import urllib3
from minio import Minio
from minio.error import MinioException, S3Error

from pipeline.core.errors import SnapshotError
from pipeline.core.ports import BlobStore


class MinioBlobStore(BlobStore):
    """Adapter: MinIO bucket behind the BlobStore port. Creates the bucket if missing."""

    def __init__(self, client: Minio, bucket: str = "snapshots"):
        self._client = client
        self._bucket = bucket
        self._call(self._ensure_bucket, bucket)

    @classmethod
    def from_env(cls) -> "MinioBlobStore":
        client = Minio(
            os.environ.get("MINIO_ENDPOINT", "localhost:9000"),
            access_key=os.environ.get("MINIO_ACCESS_KEY", ""),
            secret_key=os.environ.get("MINIO_SECRET_KEY", ""),
            secure=os.environ.get("MINIO_SECURE", "false").lower() == "true",
        )
        return cls(client, os.environ.get("MINIO_BUCKET", "snapshots"))

    def put(self, key: str, data: bytes) -> None:
        self._call(self._client.put_object, self._bucket, key, io.BytesIO(data), len(data))

    def get(self, key: str) -> bytes:
        try:
            response = self._client.get_object(self._bucket, key)
        except S3Error as exc:
            if exc.code == "NoSuchKey":
                raise KeyError(key) from exc
            raise SnapshotError("blob store error", code="BLOB_STORE_ERROR", context={"key": key}) from exc
        except (MinioException, urllib3.exceptions.HTTPError) as exc:
            raise SnapshotError("blob store unreachable", code="BLOB_STORE_ERROR", context={"key": key}) from exc
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete(self, key: str) -> None:
        self._call(self._client.remove_object, self._bucket, key)

    def _ensure_bucket(self, bucket: str) -> None:
        if not self._client.bucket_exists(bucket):
            self._client.make_bucket(bucket)

    @staticmethod
    def _call(fn, *args):
        try:
            return fn(*args)
        except (MinioException, urllib3.exceptions.HTTPError) as exc:
            raise SnapshotError(f"blob store error: {type(exc).__name__}", code="BLOB_STORE_ERROR") from exc
