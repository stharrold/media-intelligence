# Copyright (c) 2025 Harrold Holdings GmbH
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license information.

"""
Tests for the StorageManager class.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestStorageManager:
    """Tests for StorageManager class."""

    @patch("src.storage_manager.storage.Client")
    def test_initialization(self, mock_storage_client):
        """Test StorageManager initialization."""
        from src.storage_manager import StorageManager

        manager = StorageManager(
            project_id="test-project",
            input_bucket="test-input",
            output_bucket="test-output",
        )

        assert manager.project_id == "test-project"
        assert manager.input_bucket_name == "test-input"
        assert manager.output_bucket_name == "test-output"

    @patch("src.storage_manager.storage.Client")
    def test_initialization_from_env(self, mock_storage_client):
        """Test StorageManager initialization from environment variables."""
        from src.storage_manager import StorageManager
        import os

        with patch.dict(os.environ, {
            "PROJECT_ID": "env-project",
            "INPUT_BUCKET": "env-input",
            "OUTPUT_BUCKET": "env-output",
        }):
            manager = StorageManager()

            assert manager.project_id == "env-project"
            assert manager.input_bucket_name == "env-input"
            assert manager.output_bucket_name == "env-output"

    @patch("src.storage_manager.storage.Client")
    def test_download_file(self, mock_storage_client):
        """Test file download from GCS."""
        from src.storage_manager import StorageManager

        # Setup mock
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_storage_client.return_value = mock_client
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        manager = StorageManager(
            project_id="test-project",
            input_bucket="test-input",
            output_bucket="test-output",
        )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            result = manager.download_file("gs://test-input/audio.wav", tmp.name)

            mock_client.bucket.assert_called_with("test-input")
            mock_bucket.blob.assert_called_with("audio.wav")
            mock_blob.download_to_filename.assert_called_once()
            assert result == tmp.name

    @patch("src.storage_manager.storage.Client")
    def test_upload_file(self, mock_storage_client):
        """Test file upload to GCS."""
        from src.storage_manager import StorageManager

        # Setup mock
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_storage_client.return_value = mock_client
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        manager = StorageManager(
            project_id="test-project",
            input_bucket="test-input",
            output_bucket="test-output",
        )

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp.write(b'{"test": "data"}')
            tmp.flush()

            result = manager.upload_file(tmp.name, "results/test.json")

            mock_client.bucket.assert_called_with("test-output")
            mock_bucket.blob.assert_called_with("results/test.json")
            mock_blob.upload_from_filename.assert_called_once()
            assert result.startswith("gs://test-output/")

    @patch("src.storage_manager.storage.Client")
    def test_upload_json(self, mock_storage_client):
        """Test JSON upload to GCS."""
        from src.storage_manager import StorageManager

        # Setup mock
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_storage_client.return_value = mock_client
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        manager = StorageManager(
            project_id="test-project",
            input_bucket="test-input",
            output_bucket="test-output",
        )

        data = {"transcript": "Hello world", "duration": 10.5}
        result = manager.upload_json(data, "results/test.json")

        mock_blob.upload_from_string.assert_called_once()
        call_args = mock_blob.upload_from_string.call_args
        uploaded_data = json.loads(call_args[0][0])
        assert uploaded_data == data
        assert result.startswith("gs://test-output/")

    @patch("src.storage_manager.storage.Client")
    def test_upload_text(self, mock_storage_client):
        """Test text upload to GCS."""
        from src.storage_manager import StorageManager

        # Setup mock
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_storage_client.return_value = mock_client
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        manager = StorageManager(
            project_id="test-project",
            input_bucket="test-input",
            output_bucket="test-output",
        )

        text = "This is a transcript.\nWith multiple lines."
        result = manager.upload_text(text, "transcripts/test.txt")

        mock_blob.upload_from_string.assert_called_once()
        call_args = mock_blob.upload_from_string.call_args
        assert call_args[0][0] == text
        assert result.startswith("gs://test-output/")

    @patch("src.storage_manager.storage.Client")
    def test_file_exists(self, mock_storage_client):
        """Test checking if file exists in GCS."""
        from src.storage_manager import StorageManager

        # Setup mock
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_storage_client.return_value = mock_client
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_blob.exists.return_value = True

        manager = StorageManager(
            project_id="test-project",
            input_bucket="test-input",
            output_bucket="test-output",
        )

        result = manager.file_exists("gs://test-input/audio.wav")

        assert result is True
        mock_blob.exists.assert_called_once()

    @patch("src.storage_manager.storage.Client")
    def test_list_files(self, mock_storage_client):
        """Test listing files in GCS bucket."""
        from src.storage_manager import StorageManager

        # Setup mock
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob1 = MagicMock()
        mock_blob1.name = "audio1.wav"
        mock_blob2 = MagicMock()
        mock_blob2.name = "audio2.wav"
        mock_storage_client.return_value = mock_client
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.list_blobs.return_value = [mock_blob1, mock_blob2]

        manager = StorageManager(
            project_id="test-project",
            input_bucket="test-input",
            output_bucket="test-output",
        )

        result = manager.list_files(prefix="")

        assert len(result) == 2
        assert "audio1.wav" in result
        assert "audio2.wav" in result

    @patch("src.storage_manager.storage.Client")
    def test_delete_file(self, mock_storage_client):
        """Test deleting file from GCS."""
        from src.storage_manager import StorageManager

        # Setup mock
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_storage_client.return_value = mock_client
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        manager = StorageManager(
            project_id="test-project",
            input_bucket="test-input",
            output_bucket="test-output",
        )

        manager.delete_file("gs://test-output/results/test.json")

        mock_blob.delete.assert_called_once()


class TestGCSURIParsing:
    """Tests for GCS URI parsing."""

    @patch("src.storage_manager.storage.Client")
    def test_parse_valid_uri(self, mock_storage_client):
        """Test parsing valid GCS URIs."""
        from src.storage_manager import StorageManager

        manager = StorageManager(
            project_id="test-project",
            input_bucket="test-input",
            output_bucket="test-output",
        )

        # Test basic URI
        bucket, path = manager._parse_gcs_uri("gs://my-bucket/path/to/file.wav")
        assert bucket == "my-bucket"
        assert path == "path/to/file.wav"

        # Test URI with single path segment
        bucket, path = manager._parse_gcs_uri("gs://bucket/file.json")
        assert bucket == "bucket"
        assert path == "file.json"

    @patch("src.storage_manager.storage.Client")
    def test_parse_invalid_uri(self, mock_storage_client):
        """Test parsing invalid GCS URIs raises error."""
        from src.storage_manager import StorageManager

        manager = StorageManager(
            project_id="test-project",
            input_bucket="test-input",
            output_bucket="test-output",
        )

        with pytest.raises(ValueError):
            manager._parse_gcs_uri("not-a-gcs-uri")

        with pytest.raises(ValueError):
            manager._parse_gcs_uri("s3://wrong-protocol/file.wav")
