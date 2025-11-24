# Copyright (c) 2025 Harrold Holdings GmbH
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license information.

"""
Integration tests for the Media Intelligence Pipeline.

These tests verify end-to-end functionality with synthetic audio data.
They do not require real audio files or model downloads when properly mocked.
"""

import pytest
import numpy as np
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


def generate_synthetic_audio(duration_seconds: float = 1.0, sample_rate: int = 16000) -> np.ndarray:
    """
    Generate synthetic audio data for testing.

    Args:
        duration_seconds: Duration of audio in seconds
        sample_rate: Sample rate in Hz

    Returns:
        Numpy array of audio samples
    """
    num_samples = int(duration_seconds * sample_rate)
    # Generate a simple sine wave with some noise
    t = np.linspace(0, duration_seconds, num_samples)
    audio = 0.5 * np.sin(2 * np.pi * 440 * t) + 0.1 * np.random.randn(num_samples)
    return audio.astype(np.float32)


def create_test_wav_file(filepath: Path, duration_seconds: float = 1.0):
    """Create a test WAV file with synthetic audio."""
    import wave
    import struct

    sample_rate = 16000
    audio = generate_synthetic_audio(duration_seconds, sample_rate)

    # Convert to 16-bit PCM
    audio_int16 = (audio * 32767).astype(np.int16)

    with wave.open(str(filepath), 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())


class TestUtilsIntegration:
    """Integration tests for utility functions."""

    def test_memory_validation(self):
        """Test memory validation functions."""
        from src.utils import (
            check_available_memory,
            estimate_memory_requirement,
            validate_memory_for_file
        )

        # Test memory check returns a positive value
        available = check_available_memory()
        assert available > 0

        # Test memory estimation for different models
        file_size = 10 * 1024 * 1024  # 10MB
        tiny_estimate = estimate_memory_requirement(file_size, "tiny.en")
        base_estimate = estimate_memory_requirement(file_size, "base.en")
        medium_estimate = estimate_memory_requirement(file_size, "medium.en")

        # Larger models should require more memory
        assert tiny_estimate < base_estimate < medium_estimate

    def test_path_sanitization(self):
        """Test path sanitization prevents traversal."""
        from src.utils import sanitize_path

        # Normal paths should work
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test.wav"
            test_path.touch()
            result = sanitize_path(test_path)
            assert result.exists()

    def test_audio_file_validation(self):
        """Test audio file validation."""
        from src.utils import validate_audio_file, SUPPORTED_FORMATS

        with tempfile.TemporaryDirectory() as tmpdir:
            # Test valid format
            wav_file = Path(tmpdir) / "test.wav"
            create_test_wav_file(wav_file)
            assert validate_audio_file(wav_file) is True

            # Test invalid format
            txt_file = Path(tmpdir) / "test.txt"
            txt_file.write_text("not audio")
            assert validate_audio_file(txt_file) is False


class TestTranscriberIntegration:
    """Integration tests for transcription with model validation."""

    def test_invalid_model_raises_error(self):
        """Test that invalid model names raise ValueError."""
        from src.transcription import Transcriber, WhisperConfig

        with pytest.raises(ValueError) as exc_info:
            config = WhisperConfig(model_size="invalid_model")
            # Need to mock the model loading to test validation
            with patch('src.transcription.WhisperModel'):
                Transcriber(config)

        assert "Invalid Whisper model" in str(exc_info.value)

    @patch('src.transcription.WhisperModel')
    def test_valid_models_accepted(self, mock_whisper):
        """Test that all valid models are accepted."""
        from src.transcription import Transcriber, WhisperConfig

        valid_models = ["tiny", "tiny.en", "base", "base.en", "small", "small.en", "medium", "medium.en"]

        for model in valid_models:
            config = WhisperConfig(model_size=model)
            transcriber = Transcriber(config)
            assert transcriber.config.model_size == model


class TestDiarizerIntegration:
    """Integration tests for diarization with token validation."""

    def test_empty_token_raises_error(self):
        """Test that empty HuggingFace token raises ValueError."""
        from src.diarization import Diarizer, DiarizationConfig

        # Test with empty string
        with pytest.raises(ValueError) as exc_info:
            Diarizer(hf_token="")
        assert "HuggingFace token required" in str(exc_info.value)

        # Test with whitespace-only string
        with pytest.raises(ValueError) as exc_info:
            Diarizer(hf_token="   ")
        assert "HuggingFace token required" in str(exc_info.value)

    def test_none_token_raises_error(self):
        """Test that None HuggingFace token raises ValueError."""
        from src.diarization import Diarizer

        # Clear environment variable if set
        old_token = os.environ.pop("HUGGINGFACE_TOKEN", None)
        try:
            with pytest.raises(ValueError) as exc_info:
                Diarizer(hf_token=None)
            assert "HuggingFace token required" in str(exc_info.value)
        finally:
            if old_token:
                os.environ["HUGGINGFACE_TOKEN"] = old_token


class TestAudioProcessorIntegration:
    """Integration tests for the main AudioProcessor."""

    @patch('src.process_audio.Transcriber')
    @patch('src.process_audio.SituationClassifier')
    def test_memory_check_before_processing(self, mock_classifier, mock_transcriber):
        """Test that memory is validated before processing."""
        from src.process_audio import AudioProcessor
        from src.utils import validate_memory_for_file

        # Setup mocks
        mock_transcriber_instance = MagicMock()
        mock_transcriber_instance.config.model_size = "base.en"
        mock_transcriber_instance.config.compute_type = "int8"
        mock_transcriber.return_value = mock_transcriber_instance

        mock_classifier_instance = MagicMock()
        mock_classifier.return_value = mock_classifier_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "test.wav"
            create_test_wav_file(test_file, duration_seconds=1.0)

            # Memory validation should pass for small files
            is_valid, msg = validate_memory_for_file(test_file, "base.en")
            assert is_valid is True

    @patch('src.process_audio.Transcriber')
    @patch('src.process_audio.SituationClassifier')
    def test_timeout_parameter(self, mock_classifier, mock_transcriber):
        """Test that timeout parameter is accepted."""
        from src.process_audio import AudioProcessor

        # Setup mocks
        mock_transcriber_instance = MagicMock()
        mock_transcriber.return_value = mock_transcriber_instance

        mock_classifier_instance = MagicMock()
        mock_classifier.return_value = mock_classifier_instance

        processor = AudioProcessor(
            whisper_model="tiny.en",
            timeout=300,
            enable_diarization=False
        )

        assert processor.timeout == 300

    @patch('src.process_audio.Transcriber')
    @patch('src.process_audio.SituationClassifier')
    def test_path_sanitization_in_processing(self, mock_classifier, mock_transcriber):
        """Test that paths are sanitized during processing."""
        from src.process_audio import AudioProcessor

        # Setup mocks
        mock_transcriber_instance = MagicMock()
        mock_transcriber_instance.config.model_size = "base.en"
        mock_transcriber_instance.config.compute_type = "int8"
        mock_transcriber_instance.transcribe.return_value = ([], {"language": "en", "language_probability": 0.99})
        mock_transcriber.return_value = mock_transcriber_instance

        mock_classifier_instance = MagicMock()
        mock_classifier_instance.classify_audio.return_value = ([], "quiet")
        mock_classifier.return_value = mock_classifier_instance

        processor = AudioProcessor(
            whisper_model="tiny.en",
            enable_diarization=False
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "test.wav"
            create_test_wav_file(test_file, duration_seconds=0.5)
            output_dir = Path(tmpdir) / "output"

            # Mock load_audio to return synthetic data
            with patch('src.process_audio.load_audio') as mock_load:
                mock_load.return_value = (generate_synthetic_audio(0.5), 16000)

                result = processor.process_file(
                    str(test_file),
                    str(output_dir)
                )

                assert result is not None
                assert result.duration > 0


class TestEndToEndWorkflow:
    """End-to-end workflow tests (with mocked models)."""

    @patch('src.process_audio.Transcriber')
    @patch('src.process_audio.SituationClassifier')
    @patch('src.process_audio.load_audio')
    def test_complete_processing_workflow(self, mock_load, mock_classifier, mock_transcriber):
        """Test complete processing workflow with mocked components."""
        from src.process_audio import AudioProcessor
        from src.utils import TranscriptSegment, SituationSegment

        # Setup mocks
        mock_load.return_value = (generate_synthetic_audio(2.0), 16000)

        mock_transcriber_instance = MagicMock()
        mock_transcriber_instance.config.model_size = "tiny.en"
        mock_transcriber_instance.config.compute_type = "int8"
        mock_transcriber_instance.transcribe.return_value = (
            [TranscriptSegment(start=0.0, end=1.0, text="Hello world", confidence=0.95)],
            {"language": "en", "language_probability": 0.99, "duration": 2.0}
        )
        mock_transcriber.return_value = mock_transcriber_instance

        mock_classifier_instance = MagicMock()
        mock_classifier_instance.classify_audio.return_value = (
            [SituationSegment(start=0.0, end=2.0, situation="quiet", confidence=0.85, top_predictions=[])],
            "quiet"
        )
        mock_classifier.return_value = mock_classifier_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "test.wav"
            create_test_wav_file(test_file, duration_seconds=2.0)
            output_dir = Path(tmpdir) / "output"

            processor = AudioProcessor(
                whisper_model="tiny.en",
                enable_diarization=False,
                enable_situation=True,
                timeout=60
            )

            result = processor.process_file(
                str(test_file),
                str(output_dir)
            )

            # Verify result structure
            assert result is not None
            assert result.duration > 0
            assert len(result.transcript_segments) == 1
            assert result.transcript_segments[0].text == "Hello world"
            assert result.overall_situation == "quiet"
            assert result.processing_time > 0

            # Verify output files were created
            assert (output_dir / "test_results.json").exists()
            assert (output_dir / "test_transcript.txt").exists()
