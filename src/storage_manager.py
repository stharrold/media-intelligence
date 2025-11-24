"""
Google Cloud Storage operations for the Media Intelligence Pipeline.
"""

import json
import logging
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from google.cloud import storage
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .gcp_utils import generate_file_id, parse_gcs_uri

logger = logging.getLogger(__name__)


class StorageManager:
    """Manager for Google Cloud Storage operations."""

    def __init__(
        self,
        project_id: str | None = None,
        input_bucket: str | None = None,
        output_bucket: str | None = None,
    ):
        """
        Initialize the Storage Manager.

        Args:
            project_id: GCP project ID. If None, uses PROJECT_ID env var.
            input_bucket: Name of input bucket. If None, uses INPUT_BUCKET env var.
            output_bucket: Name of output bucket. If None, uses OUTPUT_BUCKET env var.
        """
        self.project_id = project_id or os.getenv("PROJECT_ID")
        self.input_bucket = input_bucket or os.getenv("INPUT_BUCKET")
        self.output_bucket = output_bucket or os.getenv("OUTPUT_BUCKET")

        self._client: storage.Client | None = None

    @property
    def client(self) -> storage.Client:
        """Lazy initialization of Storage client."""
        if self._client is None:
            self._client = storage.Client(project=self.project_id)
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    )
    def download_file(
        self,
        gcs_uri: str,
        local_path: str | None = None,
    ) -> str:
        """
        Download a file from GCS to local storage.

        Args:
            gcs_uri: GCS URI (gs://bucket/path/to/file).
            local_path: Local path to save file. If None, uses temp directory.

        Returns:
            Local path to downloaded file.
        """
        bucket_name, blob_path = parse_gcs_uri(gcs_uri)

        if local_path is None:
            # Create temp file with same extension
            ext = Path(blob_path).suffix
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            local_path = temp_file.name
            temp_file.close()

        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        logger.info(f"Downloading {gcs_uri} to {local_path}")
        blob.download_to_filename(local_path)

        return local_path

    @contextmanager
    def download_temp_file(self, gcs_uri: str) -> Generator[str, None, None]:
        """
        Context manager for downloading a file to a temp location with automatic cleanup.

        Args:
            gcs_uri: GCS URI (gs://bucket/path/to/file).

        Yields:
            Local path to downloaded file.

        Example:
            with storage_manager.download_temp_file("gs://bucket/audio.wav") as local_path:
                process_audio(local_path)
            # File is automatically cleaned up after the block
        """
        local_path = self.download_file(gcs_uri)
        try:
            yield local_path
        finally:
            # Clean up temp file
            try:
                if os.path.exists(local_path):
                    os.remove(local_path)
                    logger.debug(f"Cleaned up temp file: {local_path}")
            except OSError as e:
                logger.warning(f"Failed to clean up temp file {local_path}: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    )
    def upload_file(
        self,
        local_path: str,
        bucket_name: str | None = None,
        blob_path: str | None = None,
        content_type: str | None = None,
    ) -> str:
        """
        Upload a file to GCS.

        Args:
            local_path: Local path to file.
            bucket_name: Target bucket name. If None, uses output_bucket.
            blob_path: Path in bucket. If None, uses filename.
            content_type: MIME type. If None, auto-detected.

        Returns:
            GCS URI of uploaded file.
        """
        if bucket_name is None:
            bucket_name = self.output_bucket

        if blob_path is None:
            blob_path = Path(local_path).name

        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        logger.info(f"Uploading {local_path} to gs://{bucket_name}/{blob_path}")
        blob.upload_from_filename(local_path, content_type=content_type)

        return f"gs://{bucket_name}/{blob_path}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    )
    def upload_json(
        self,
        data: dict[str, Any],
        bucket_name: str | None = None,
        blob_path: str | None = None,
    ) -> str:
        """
        Upload JSON data to GCS.

        Args:
            data: Dictionary to serialize as JSON.
            bucket_name: Target bucket name. If None, uses output_bucket.
            blob_path: Path in bucket. If None, generates unique path.

        Returns:
            GCS URI of uploaded file.
        """
        if bucket_name is None:
            bucket_name = self.output_bucket

        if blob_path is None:
            file_id = generate_file_id()
            blob_path = f"results/{file_id}.json"

        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        json_str = json.dumps(data, indent=2, default=str)

        logger.info(f"Uploading JSON to gs://{bucket_name}/{blob_path}")
        blob.upload_from_string(json_str, content_type="application/json")

        return f"gs://{bucket_name}/{blob_path}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    )
    def upload_text(
        self,
        text: str,
        bucket_name: str | None = None,
        blob_path: str | None = None,
    ) -> str:
        """
        Upload text data to GCS.

        Args:
            text: Text content to upload.
            bucket_name: Target bucket name. If None, uses output_bucket.
            blob_path: Path in bucket. If None, generates unique path.

        Returns:
            GCS URI of uploaded file.
        """
        if bucket_name is None:
            bucket_name = self.output_bucket

        if blob_path is None:
            file_id = generate_file_id()
            blob_path = f"transcripts/{file_id}.txt"

        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        logger.info(f"Uploading text to gs://{bucket_name}/{blob_path}")
        blob.upload_from_string(text, content_type="text/plain")

        return f"gs://{bucket_name}/{blob_path}"

    def read_json(self, gcs_uri: str) -> dict[str, Any]:
        """
        Read JSON data from GCS.

        Args:
            gcs_uri: GCS URI (gs://bucket/path/to/file.json).

        Returns:
            Parsed JSON data.
        """
        bucket_name, blob_path = parse_gcs_uri(gcs_uri)
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        content = blob.download_as_string()
        return json.loads(content)

    def read_text(self, gcs_uri: str) -> str:
        """
        Read text data from GCS.

        Args:
            gcs_uri: GCS URI (gs://bucket/path/to/file.txt).

        Returns:
            Text content.
        """
        bucket_name, blob_path = parse_gcs_uri(gcs_uri)
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        return blob.download_as_string().decode("utf-8")

    def file_exists(self, gcs_uri: str) -> bool:
        """
        Check if a file exists in GCS.

        Args:
            gcs_uri: GCS URI (gs://bucket/path/to/file).

        Returns:
            True if file exists.
        """
        bucket_name, blob_path = parse_gcs_uri(gcs_uri)
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        return blob.exists()

    def delete_file(self, gcs_uri: str) -> None:
        """
        Delete a file from GCS.

        Args:
            gcs_uri: GCS URI (gs://bucket/path/to/file).
        """
        bucket_name, blob_path = parse_gcs_uri(gcs_uri)
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        logger.info(f"Deleting {gcs_uri}")
        blob.delete()

    def list_files(
        self,
        bucket_name: str | None = None,
        prefix: str = "",
        max_results: int | None = None,
    ) -> list[str]:
        """
        List files in a GCS bucket.

        Args:
            bucket_name: Bucket to list. If None, uses input_bucket.
            prefix: Filter to files starting with this prefix.
            max_results: Maximum number of results.

        Returns:
            List of GCS URIs.
        """
        if bucket_name is None:
            bucket_name = self.input_bucket

        bucket = self.client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix, max_results=max_results)

        return [f"gs://{bucket_name}/{blob.name}" for blob in blobs]

    def get_file_metadata(self, gcs_uri: str) -> dict[str, Any]:
        """
        Get metadata for a file in GCS.

        Args:
            gcs_uri: GCS URI (gs://bucket/path/to/file).

        Returns:
            Dictionary with file metadata.
        """
        bucket_name, blob_path = parse_gcs_uri(gcs_uri)
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        blob.reload()

        return {
            "name": blob.name,
            "bucket": blob.bucket.name,
            "size": blob.size,
            "content_type": blob.content_type,
            "created": blob.time_created.isoformat() if blob.time_created else None,
            "updated": blob.updated.isoformat() if blob.updated else None,
            "md5_hash": blob.md5_hash,
            "gcs_uri": gcs_uri,
        }

    def copy_file(
        self,
        source_uri: str,
        dest_bucket: str,
        dest_path: str | None = None,
    ) -> str:
        """
        Copy a file within GCS.

        Args:
            source_uri: Source GCS URI.
            dest_bucket: Destination bucket name.
            dest_path: Destination path. If None, uses source filename.

        Returns:
            GCS URI of copied file.
        """
        source_bucket_name, source_blob_path = parse_gcs_uri(source_uri)

        if dest_path is None:
            dest_path = Path(source_blob_path).name

        source_bucket = self.client.bucket(source_bucket_name)
        source_blob = source_bucket.blob(source_blob_path)

        dest_bucket_obj = self.client.bucket(dest_bucket)

        logger.info(f"Copying {source_uri} to gs://{dest_bucket}/{dest_path}")
        source_bucket.copy_blob(source_blob, dest_bucket_obj, dest_path)

        return f"gs://{dest_bucket}/{dest_path}"
