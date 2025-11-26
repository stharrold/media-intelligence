# Copyright (c) 2025 Harrold Holdings GmbH
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license information.

"""
Tests for the AudioProcessor class (GCP deployment).
"""

from unittest.mock import MagicMock, patch


class TestAudioProcessor:
    """Tests for the GCP AudioProcessor class."""

    @patch("src.audio_processor.StorageManager")
    @patch("src.audio_processor.SpeechClient")
    @patch("src.audio_processor.SituationClassifier")
    @patch("src.audio_processor.load_config")
    def test_initialization(self, mock_config, mock_classifier, mock_speech, mock_storage):
        """Test AudioProcessor initialization."""
        from src.audio_processor import AudioProcessor

        mock_config.return_value = {
            "project_id": "test-project",
            "input_bucket": "test-input",
            "output_bucket": "test-output",
        }

        processor = AudioProcessor()

        assert processor is not None
        mock_config.assert_called_once()

    @patch("src.audio_processor.StorageManager")
    @patch("src.audio_processor.SpeechClient")
    @patch("src.audio_processor.SituationClassifier")
    @patch("src.audio_processor.load_config")
    def test_initialization_with_custom_config(self, mock_config, mock_classifier, mock_speech, mock_storage):
        """Test AudioProcessor initialization with custom config."""
        from src.audio_processor import AudioProcessor

        custom_config = {
            "project_id": "custom-project",
            "input_bucket": "custom-input",
            "output_bucket": "custom-output",
            "enable_diarization": False,
            "enable_situation_detection": False,
        }
        mock_config.return_value = custom_config

        processor = AudioProcessor()

        assert processor.config == custom_config

    @patch("src.audio_processor.StorageManager")
    @patch("src.audio_processor.SpeechClient")
    @patch("src.audio_processor.SituationClassifier")
    @patch("src.audio_processor.load_config")
    @patch("src.audio_processor.is_supported_format")
    def test_process_file_unsupported_format(self, mock_supported, mock_config, mock_classifier, mock_speech, mock_storage):
        """Test processing rejects unsupported format."""
        from src.audio_processor import AudioProcessor

        mock_config.return_value = {
            "project_id": "test-project",
            "input_bucket": "test-input",
            "output_bucket": "test-output",
            "supported_formats": [".wav", ".mp3", ".flac"],
        }
        mock_supported.return_value = False

        processor = AudioProcessor()
        result = processor.process_file(gcs_uri="gs://bucket/file.txt", output_bucket="test-output")

        assert result.error is not None
        assert "Unsupported" in result.error or "unsupported" in result.error.lower()

    @patch("src.audio_processor.StorageManager")
    @patch("src.audio_processor.SpeechClient")
    @patch("src.audio_processor.SituationClassifier")
    @patch("src.audio_processor.load_config")
    @patch("src.audio_processor.is_supported_format")
    @patch("src.audio_processor.get_audio_duration")
    @patch("src.audio_processor.validate_audio_duration")
    def test_process_file_success(
        self,
        mock_validate,
        mock_duration,
        mock_supported,
        mock_config,
        mock_classifier_class,
        mock_speech_class,
        mock_storage_class,
    ):
        """Test successful file processing."""
        from src.audio_processor import AudioProcessor
        from src.situation_classifier import SituationPrediction, SituationResult
        from src.speech_client import TranscriptionResult, TranscriptSegment

        # Setup mocks
        mock_config.return_value = {
            "project_id": "test-project",
            "input_bucket": "test-input",
            "output_bucket": "test-output",
            "enable_diarization": True,
            "enable_situation_detection": True,
        }
        mock_supported.return_value = True
        mock_duration.return_value = 60.0
        mock_validate.return_value = True

        # Mock storage manager
        mock_storage = MagicMock()
        mock_storage.download_temp_file.return_value.__enter__ = MagicMock(return_value="/tmp/audio.wav")
        mock_storage.download_temp_file.return_value.__exit__ = MagicMock(return_value=False)
        mock_storage.upload_json.return_value = "gs://test-output/results/test.json"
        mock_storage.upload_text.return_value = "gs://test-output/transcripts/test.txt"
        mock_storage_class.return_value = mock_storage

        # Mock speech client
        mock_speech = MagicMock()
        mock_speech.transcribe_gcs.return_value = TranscriptionResult(
            segments=[
                TranscriptSegment(
                    text="Hello world",
                    start_time=0.0,
                    end_time=2.0,
                    confidence=0.95,
                    speaker_tag=0,
                )
            ],
            speaker_count=1,
            total_duration=60.0,
            language_code="en-US",
            model_used="long",
        )
        mock_speech_class.return_value = mock_speech

        # Mock situation classifier
        mock_classifier = MagicMock()
        mock_classifier.classify_audio.return_value = SituationResult(
            predictions=[
                SituationPrediction(
                    situation="meeting",
                    confidence=0.9,
                    start_time=0.0,
                    end_time=30.0,
                    all_scores={"meeting": 0.9},
                )
            ],
            overall_situation="meeting",
            overall_confidence=0.9,
            segment_duration=30.0,
        )
        mock_classifier_class.return_value = mock_classifier

        processor = AudioProcessor()
        result = processor.process_file(gcs_uri="gs://test-input/audio.wav", output_bucket="test-output")

        assert result.error is None
        assert result.duration == 60.0
        assert len(result.transcript_segments) == 1
        assert result.overall_situation == "meeting"


class TestProcessingResult:
    """Tests for ProcessingResult dataclass."""

    def test_to_dict(self):
        """Test ProcessingResult to_dict method."""
        from src.audio_processor import ProcessingResult
        from src.situation_classifier import SituationPrediction
        from src.speech_client import TranscriptSegment

        result = ProcessingResult(
            gcs_input_uri="gs://input/audio.wav",
            gcs_output_uri="gs://output/results.json",
            file_id="test_123",
            duration=60.0,
            transcript_segments=[
                TranscriptSegment(
                    text="Hello",
                    start_time=0.0,
                    end_time=1.0,
                    confidence=0.9,
                )
            ],
            situation_predictions=[
                SituationPrediction(
                    situation="meeting",
                    confidence=0.8,
                    start_time=0.0,
                    end_time=30.0,
                )
            ],
            speaker_count=1,
            overall_situation="meeting",
            overall_situation_confidence=0.8,
            processing_time=5.0,
            cost_estimate={},
            error=None,
        )

        result_dict = result.to_dict()

        assert result_dict["gcs_input_uri"] == "gs://input/audio.wav"
        assert result_dict["duration"] == 60.0
        assert result_dict["overall_situation"] == "meeting"
        assert len(result_dict["transcript_segments"]) == 1
        assert result_dict["error"] is None

    def test_to_dict_with_error(self):
        """Test ProcessingResult to_dict with error."""
        from src.audio_processor import ProcessingResult

        result = ProcessingResult(
            gcs_input_uri="gs://input/audio.wav",
            gcs_output_uri="",
            file_id="",
            duration=0.0,
            transcript_segments=[],
            situation_predictions=[],
            speaker_count=0,
            overall_situation="",
            overall_situation_confidence=0.0,
            processing_time=0.0,
            cost_estimate={},
            error="Processing failed",
        )

        result_dict = result.to_dict()

        assert result_dict["error"] == "Processing failed"
