"""Tests for the Speech-to-Text client."""

from dataclasses import dataclass
from unittest.mock import Mock, patch

import pytest

from src.speech_client import SpeechClient, TranscriptionResult, TranscriptSegment


@pytest.fixture
def mock_speech_response():
    """Create a mock Speech-to-Text response."""

    @dataclass
    class MockWord:
        word: str
        start_offset: Mock
        end_offset: Mock
        confidence: float
        speaker_label: str

    @dataclass
    class MockAlternative:
        transcript: str
        confidence: float
        words: list

    @dataclass
    class MockResult:
        alternatives: list
        language_code: str

    @dataclass
    class MockTranscript:
        results: list

    @dataclass
    class MockFileResults:
        transcript: MockTranscript

    # Create mock time offsets
    def make_offset(seconds):
        offset = Mock()
        offset.total_seconds.return_value = seconds
        return offset

    # Create mock words
    words = [
        MockWord(
            word="Hello",
            start_offset=make_offset(0.0),
            end_offset=make_offset(0.5),
            confidence=0.95,
            speaker_label="1",
        ),
        MockWord(
            word="world",
            start_offset=make_offset(0.5),
            end_offset=make_offset(1.0),
            confidence=0.92,
            speaker_label="1",
        ),
        MockWord(
            word="how",
            start_offset=make_offset(1.5),
            end_offset=make_offset(1.8),
            confidence=0.88,
            speaker_label="2",
        ),
        MockWord(
            word="are",
            start_offset=make_offset(1.8),
            end_offset=make_offset(2.0),
            confidence=0.90,
            speaker_label="2",
        ),
        MockWord(
            word="you",
            start_offset=make_offset(2.0),
            end_offset=make_offset(2.3),
            confidence=0.93,
            speaker_label="2",
        ),
    ]

    result = MockResult(
        alternatives=[
            MockAlternative(
                transcript="Hello world how are you",
                confidence=0.91,
                words=words,
            )
        ],
        language_code="en-US",
    )

    transcript = MockTranscript(results=[result])
    file_results = MockFileResults(transcript=transcript)

    return {"gs://test-bucket/test.wav": file_results}


@pytest.fixture
def speech_client():
    """Create a SpeechClient with mocked Google client."""
    with patch("src.speech_client.GoogleSpeechClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        client = SpeechClient(project_id="test-project")
        client._client = mock_client
        return client


@pytest.mark.skip(reason="Requires google-cloud-speech - GCP dependency not available (issue #TBD)")
class TestSpeechClient:
    """Tests for SpeechClient class."""

    def test_init_with_project_id(self):
        """Test initialization with project ID."""
        with patch("src.speech_client.GoogleSpeechClient"):
            client = SpeechClient(project_id="test-project")
            assert client.project_id == "test-project"
            assert client.location == "global"

    def test_init_without_project_id_raises_error(self):
        """Test initialization without project ID raises error."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="PROJECT_ID must be set"):
                SpeechClient(project_id=None)

    def test_get_recognizer_path(self, speech_client):
        """Test recognizer path generation."""
        path = speech_client._get_recognizer_path()
        assert path == "projects/test-project/locations/global/recognizers/_"

    def test_build_config_default(self, speech_client):
        """Test building default recognition config."""
        config = speech_client._build_config()

        assert config.model == "long"
        assert "en-US" in config.language_codes
        assert config.features.enable_automatic_punctuation is True
        assert config.features.enable_word_time_offsets is True
        assert config.features.diarization_config is not None
        assert config.features.diarization_config.min_speaker_count == 2
        assert config.features.diarization_config.max_speaker_count == 6

    def test_build_config_custom(self, speech_client):
        """Test building custom recognition config."""
        config = speech_client._build_config(
            language_code="fr-FR",
            model="short",
            enable_diarization=False,
            min_speaker_count=1,
            max_speaker_count=10,
        )

        assert config.model == "short"
        assert "fr-FR" in config.language_codes
        assert config.features.diarization_config is None

    def test_transcribe_gcs_success(self, speech_client, mock_speech_response):
        """Test successful transcription from GCS."""
        # Setup mock response
        mock_operation = Mock()
        mock_response = Mock()
        mock_response.results = mock_speech_response
        mock_operation.result.return_value = mock_response

        speech_client._client.batch_recognize.return_value = mock_operation

        # Call transcribe
        result = speech_client.transcribe_gcs(
            gcs_uri="gs://test-bucket/test.wav",
            language_code="en-US",
            model="long",
        )

        # Verify result
        assert isinstance(result, TranscriptionResult)
        assert len(result.segments) == 1
        assert result.segments[0].text == "Hello world how are you"
        assert result.segments[0].confidence == 0.91
        assert result.model_used == "long"
        assert result.language_code == "en-US"

    def test_transcribe_gcs_empty_response(self, speech_client):
        """Test handling of empty response."""
        mock_operation = Mock()
        mock_response = Mock()
        mock_response.results = {}
        mock_operation.result.return_value = mock_response

        speech_client._client.batch_recognize.return_value = mock_operation

        result = speech_client.transcribe_gcs(
            gcs_uri="gs://test-bucket/test.wav",
        )

        assert len(result.segments) == 0
        assert result.speaker_count == 0


class TestTranscriptSegment:
    """Tests for TranscriptSegment dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        segment = TranscriptSegment(
            start_time=0.0,
            end_time=5.0,
            text="Hello world",
            speaker_tag=1,
            confidence=0.95,
            language_code="en-US",
            words=[{"word": "Hello", "start_time": 0.0}],
        )

        result = segment.to_dict()

        assert result["start_time"] == 0.0
        assert result["end_time"] == 5.0
        assert result["text"] == "Hello world"
        assert result["speaker_tag"] == 1
        assert result["confidence"] == 0.95


class TestTranscriptionResult:
    """Tests for TranscriptionResult dataclass."""

    def test_get_full_transcript_with_speakers(self):
        """Test full transcript generation with speaker labels."""
        segments = [
            TranscriptSegment(
                start_time=0.0,
                end_time=2.0,
                text="Hello.",
                speaker_tag=0,
                confidence=0.9,
                language_code="en-US",
            ),
            TranscriptSegment(
                start_time=2.0,
                end_time=4.0,
                text="Hi there.",
                speaker_tag=1,
                confidence=0.85,
                language_code="en-US",
            ),
            TranscriptSegment(
                start_time=4.0,
                end_time=6.0,
                text="How are you?",
                speaker_tag=0,
                confidence=0.88,
                language_code="en-US",
            ),
        ]

        result = TranscriptionResult(
            segments=segments,
            speaker_count=2,
            total_duration=6.0,
            language_code="en-US",
            model_used="long",
        )

        transcript = result.get_full_transcript(include_speakers=True)

        assert "[Speaker 1]" in transcript
        assert "[Speaker 2]" in transcript
        assert "Hello." in transcript
        assert "Hi there." in transcript

    def test_get_full_transcript_without_speakers(self):
        """Test full transcript generation without speaker labels."""
        segments = [
            TranscriptSegment(
                start_time=0.0,
                end_time=2.0,
                text="Hello.",
                speaker_tag=0,
                confidence=0.9,
                language_code="en-US",
            ),
        ]

        result = TranscriptionResult(
            segments=segments,
            speaker_count=1,
            total_duration=2.0,
            language_code="en-US",
            model_used="long",
        )

        transcript = result.get_full_transcript(include_speakers=False)

        assert "[Speaker" not in transcript
        assert "Hello." in transcript

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = TranscriptionResult(
            segments=[],
            speaker_count=2,
            total_duration=60.0,
            language_code="en-US",
            model_used="long",
        )

        data = result.to_dict()

        assert data["speaker_count"] == 2
        assert data["total_duration"] == 60.0
        assert data["language_code"] == "en-US"
        assert data["model_used"] == "long"
