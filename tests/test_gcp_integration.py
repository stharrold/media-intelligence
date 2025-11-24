"""Integration tests for the Media Intelligence Pipeline.

These tests require GCP credentials and actual GCP resources.
Run with: pytest tests/test_integration.py -v --integration
"""

import json
import os
import uuid

import pytest

# Skip all tests if not running integration tests
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS", "").lower() != "true",
    reason="Integration tests disabled. Set RUN_INTEGRATION_TESTS=true to enable.",
)


@pytest.fixture(scope="module")
def project_id():
    """Get GCP project ID from environment."""
    project_id = os.getenv("PROJECT_ID")
    if not project_id:
        pytest.skip("PROJECT_ID environment variable not set")
    return project_id


@pytest.fixture(scope="module")
def test_bucket(project_id):
    """Create a temporary test bucket."""
    from google.cloud import storage

    client = storage.Client(project=project_id)
    bucket_name = f"{project_id}-test-{uuid.uuid4().hex[:8]}"

    bucket = client.create_bucket(bucket_name, location="us-central1")

    yield bucket

    # Cleanup
    try:
        bucket.delete(force=True)
    except Exception as e:
        print(f"Warning: Failed to delete test bucket: {e}")


@pytest.fixture
def sample_audio_uri(test_bucket):
    """Upload a sample audio file and return its GCS URI."""
    # Check if there's a sample file
    sample_path = os.path.join(os.path.dirname(__file__), "fixtures", "sample.wav")

    if os.path.exists(sample_path):
        blob = test_bucket.blob("test/sample.wav")
        blob.upload_from_filename(sample_path)
        return f"gs://{test_bucket.name}/test/sample.wav"

    pytest.skip("Sample audio file not found at tests/fixtures/sample.wav")


class TestStorageManagerIntegration:
    """Integration tests for StorageManager."""

    def test_upload_and_download_json(self, test_bucket, project_id):
        """Test uploading and downloading JSON."""
        from src.storage_manager import StorageManager

        manager = StorageManager(
            project_id=project_id,
            output_bucket=test_bucket.name,
        )

        test_data = {"test": "data", "number": 42}
        blob_path = f"test/{uuid.uuid4().hex}.json"

        # Upload
        uri = manager.upload_json(test_data, blob_path=blob_path)
        assert uri == f"gs://{test_bucket.name}/{blob_path}"

        # Download
        downloaded = manager.read_json(uri)
        assert downloaded == test_data

    def test_upload_and_download_text(self, test_bucket, project_id):
        """Test uploading and downloading text."""
        from src.storage_manager import StorageManager

        manager = StorageManager(
            project_id=project_id,
            output_bucket=test_bucket.name,
        )

        test_text = "Hello, World!\nThis is a test."
        blob_path = f"test/{uuid.uuid4().hex}.txt"

        # Upload
        uri = manager.upload_text(test_text, blob_path=blob_path)
        assert uri == f"gs://{test_bucket.name}/{blob_path}"

        # Download
        downloaded = manager.read_text(uri)
        assert downloaded == test_text

    def test_file_exists(self, test_bucket, project_id):
        """Test checking file existence."""
        from src.storage_manager import StorageManager

        manager = StorageManager(
            project_id=project_id,
            output_bucket=test_bucket.name,
        )

        # Create a file
        blob_path = f"test/{uuid.uuid4().hex}.txt"
        uri = manager.upload_text("test", blob_path=blob_path)

        # Check exists
        assert manager.file_exists(uri) is True
        assert manager.file_exists(f"gs://{test_bucket.name}/nonexistent.txt") is False


class TestSpeechClientIntegration:
    """Integration tests for SpeechClient."""

    @pytest.mark.slow
    def test_transcribe_gcs(self, sample_audio_uri, project_id):
        """Test transcription from GCS."""
        from src.speech_client import SpeechClient

        client = SpeechClient(project_id=project_id)

        result = client.transcribe_gcs(
            gcs_uri=sample_audio_uri,
            language_code="en-US",
            model="long",
            enable_diarization=True,
        )

        assert result is not None
        assert len(result.segments) > 0
        assert result.total_duration > 0


class TestAudioProcessorIntegration:
    """Integration tests for AudioProcessor."""

    @pytest.mark.slow
    def test_process_file(self, sample_audio_uri, test_bucket, project_id):
        """Test full file processing."""
        from src.audio_processor import AudioProcessor

        processor = AudioProcessor()

        result = processor.process_file(
            gcs_uri=sample_audio_uri,
            output_bucket=test_bucket.name,
        )

        # Check result
        assert result.error is None
        assert result.duration > 0
        assert len(result.transcript_segments) > 0
        assert result.gcs_output_uri != ""
        assert result.transcript_uri is not None

        # Verify output files exist
        from src.storage_manager import StorageManager

        manager = StorageManager(project_id=project_id)
        assert manager.file_exists(result.gcs_output_uri)
        assert manager.file_exists(result.transcript_uri)

        # Verify JSON output structure
        json_data = manager.read_json(result.gcs_output_uri)
        assert "file_id" in json_data
        assert "transcript_segments" in json_data
        assert "speaker_count" in json_data


class TestCloudRunIntegration:
    """Integration tests for Cloud Run endpoints."""

    @pytest.fixture
    def cloud_run_url(self):
        """Get Cloud Run URL from environment."""
        url = os.getenv("CLOUD_RUN_URL")
        if not url:
            pytest.skip("CLOUD_RUN_URL environment variable not set")
        return url

    def test_health_endpoint(self, cloud_run_url):
        """Test health check endpoint."""
        import requests

        response = requests.get(f"{cloud_run_url}/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"

    def test_ready_endpoint(self, cloud_run_url):
        """Test readiness endpoint."""
        import requests

        response = requests.get(f"{cloud_run_url}/ready")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ready"

    @pytest.mark.slow
    def test_process_endpoint(self, cloud_run_url, sample_audio_uri, test_bucket):
        """Test process endpoint."""
        import requests

        response = requests.post(
            f"{cloud_run_url}/process",
            json={
                "gcs_uri": sample_audio_uri,
                "output_bucket": test_bucket.name,
            },
        )

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert "file_id" in data
        assert "result_uri" in data


class TestUtilsIntegration:
    """Integration tests for utility functions."""

    def test_load_config(self):
        """Test loading configuration file."""
        from src.utils import load_config

        config = load_config()

        assert "processing" in config
        assert "speech" in config
        assert "situation" in config

    def test_estimate_cost(self):
        """Test cost estimation."""
        from src.utils import estimate_cost

        # 5 minutes of audio
        cost = estimate_cost(300, enable_diarization=True, enable_situation_detection=True)

        assert "total" in cost
        assert cost["total"] > 0
        assert "speech_to_text" in cost
        assert "situation_classification" in cost


# Fixtures directory marker
@pytest.fixture(scope="session", autouse=True)
def create_fixtures_dir():
    """Create fixtures directory if it doesn't exist."""
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    os.makedirs(fixtures_dir, exist_ok=True)
