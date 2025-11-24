# Copyright (c) 2025 Harrold Holdings GmbH
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license information.

"""
Tests for the transcription module.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock


class TestWhisperConfig:
    """Tests for WhisperConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        from src.transcription import WhisperConfig

        config = WhisperConfig()
        assert config.model_size == "base.en"
        assert config.device == "cpu"
        assert config.compute_type == "int8"
        assert config.beam_size == 5
        assert config.language == "en"
        assert config.word_timestamps is True
        assert config.vad_filter is True

    def test_custom_values(self):
        """Test custom configuration values."""
        from src.transcription import WhisperConfig

        config = WhisperConfig(
            model_size="small.en",
            device="cuda",
            compute_type="float16",
            beam_size=3,
            language="de"
        )
        assert config.model_size == "small.en"
        assert config.device == "cuda"
        assert config.compute_type == "float16"
        assert config.beam_size == 3
        assert config.language == "de"


class TestTranscriber:
    """Tests for the Transcriber class."""

    @patch('src.transcription.WhisperModel')
    def test_initialization(self, mock_whisper_model):
        """Test transcriber initialization."""
        from src.transcription import Transcriber, WhisperConfig

        config = WhisperConfig(model_size="tiny.en")
        transcriber = Transcriber(config)

        mock_whisper_model.assert_called_once()
        assert transcriber.model is not None

    @patch('src.transcription.WhisperModel')
    def test_get_available_models(self, mock_whisper_model):
        """Test available models list."""
        from src.transcription import Transcriber

        models = Transcriber.get_available_models()
        assert "tiny" in models
        assert "tiny.en" in models
        assert "base" in models
        assert "base.en" in models
        assert "small" in models
        assert "medium" in models

    @patch('src.transcription.WhisperModel')
    def test_get_model_info(self, mock_whisper_model):
        """Test model info retrieval."""
        from src.transcription import Transcriber

        info = Transcriber.get_model_info("base.en")
        assert "params" in info
        assert "vram" in info
        assert "speed" in info

    @patch('src.transcription.WhisperModel')
    def test_transcribe_empty_audio(self, mock_whisper_model):
        """Test transcription with empty audio."""
        from src.transcription import Transcriber, WhisperConfig

        config = WhisperConfig()
        transcriber = Transcriber(config)

        # Empty audio should return empty segments
        segments, metadata = transcriber.transcribe(np.array([]), 16000)
        assert segments == []
        assert metadata["language"] is None

    @patch('src.transcription.WhisperModel')
    def test_transcribe_returns_segments(self, mock_whisper_model):
        """Test that transcription returns proper segments."""
        from src.transcription import Transcriber, WhisperConfig

        # Mock the transcribe method
        mock_segment = Mock()
        mock_segment.start = 0.0
        mock_segment.end = 2.5
        mock_segment.text = " Hello world"
        mock_segment.avg_logprob = -0.3

        mock_info = Mock()
        mock_info.language = "en"
        mock_info.language_probability = 0.98
        mock_info.duration = 2.5

        mock_whisper_model.return_value.transcribe.return_value = (
            iter([mock_segment]),
            mock_info
        )

        config = WhisperConfig()
        transcriber = Transcriber(config)

        audio = np.random.randn(16000 * 3).astype(np.float32)  # 3 seconds
        segments, metadata = transcriber.transcribe(audio, 16000)

        assert len(segments) == 1
        assert segments[0].text == "Hello world"
        assert segments[0].start == 0.0
        assert segments[0].end == 2.5
        assert metadata["language"] == "en"


class TestTranscriptSegment:
    """Tests for TranscriptSegment dataclass."""

    def test_creation(self):
        """Test segment creation."""
        from src.utils import TranscriptSegment

        segment = TranscriptSegment(
            start=0.0,
            end=5.0,
            text="Hello world",
            speaker="SPEAKER_00",
            confidence=0.95
        )
        assert segment.start == 0.0
        assert segment.end == 5.0
        assert segment.text == "Hello world"
        assert segment.speaker == "SPEAKER_00"
        assert segment.confidence == 0.95

    def test_to_dict(self):
        """Test conversion to dictionary."""
        from src.utils import TranscriptSegment

        segment = TranscriptSegment(
            start=0.0,
            end=5.0,
            text="Hello world"
        )
        d = segment.to_dict()
        assert d["start"] == 0.0
        assert d["end"] == 5.0
        assert d["text"] == "Hello world"
