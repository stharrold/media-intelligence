# Copyright (c) 2025 Harrold Holdings GmbH
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license information.

"""
Tests for the diarization module.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock


class TestDiarizationConfig:
    """Tests for DiarizationConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        from src.diarization import DiarizationConfig

        config = DiarizationConfig()
        assert config.pipeline == "pyannote/speaker-diarization-3.1"
        assert config.min_speakers is None
        assert config.max_speakers is None
        assert config.device == "cpu"

    def test_custom_values(self):
        """Test custom configuration values."""
        from src.diarization import DiarizationConfig

        config = DiarizationConfig(
            min_speakers=2,
            max_speakers=5,
            device="cuda"
        )
        assert config.min_speakers == 2
        assert config.max_speakers == 5
        assert config.device == "cuda"


class TestSpeakerSegment:
    """Tests for SpeakerSegment class."""

    def test_creation(self):
        """Test speaker segment creation."""
        from src.diarization import SpeakerSegment

        segment = SpeakerSegment(
            start=0.0,
            end=5.0,
            speaker="SPEAKER_00"
        )
        assert segment.start == 0.0
        assert segment.end == 5.0
        assert segment.speaker == "SPEAKER_00"

    def test_repr(self):
        """Test string representation."""
        from src.diarization import SpeakerSegment

        segment = SpeakerSegment(1.5, 3.5, "SPEAKER_01")
        repr_str = repr(segment)
        assert "1.50" in repr_str
        assert "3.50" in repr_str
        assert "SPEAKER_01" in repr_str


class TestDiarizer:
    """Tests for the Diarizer class."""

    def test_initialization_without_token_raises(self):
        """Test that initialization without token raises ValueError."""
        from src.diarization import Diarizer

        with patch.dict('os.environ', {'HUGGINGFACE_TOKEN': ''}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                Diarizer(hf_token=None)
            assert "HuggingFace token required" in str(exc_info.value)

    @patch('src.diarization.Pipeline')
    def test_initialization_with_token(self, mock_pipeline):
        """Test initialization with valid token."""
        from src.diarization import Diarizer

        mock_pipeline.from_pretrained.return_value = Mock()

        diarizer = Diarizer(hf_token="hf_test_token")
        assert diarizer.hf_token == "hf_test_token"
        mock_pipeline.from_pretrained.assert_called_once()


class TestAssignSpeakersToSegments:
    """Tests for speaker assignment function."""

    def test_empty_speaker_segments(self):
        """Test with no speaker segments."""
        from src.diarization import assign_speakers_to_segments
        from src.utils import TranscriptSegment

        transcript_segments = [
            TranscriptSegment(0.0, 2.0, "Hello"),
            TranscriptSegment(2.0, 4.0, "World")
        ]

        result = assign_speakers_to_segments(transcript_segments, [])
        assert len(result) == 2
        # Speaker should not be assigned

    def test_speaker_assignment(self):
        """Test correct speaker assignment based on overlap."""
        from src.diarization import assign_speakers_to_segments, SpeakerSegment
        from src.utils import TranscriptSegment

        transcript_segments = [
            TranscriptSegment(0.0, 2.0, "Hello"),
            TranscriptSegment(2.0, 4.0, "World")
        ]

        speaker_segments = [
            SpeakerSegment(0.0, 2.5, "SPEAKER_00"),
            SpeakerSegment(2.5, 5.0, "SPEAKER_01")
        ]

        result = assign_speakers_to_segments(transcript_segments, speaker_segments)

        assert result[0].speaker == "SPEAKER_00"
        # Second segment should be assigned to SPEAKER_00 or SPEAKER_01 based on overlap

    def test_overlap_threshold(self):
        """Test overlap threshold behavior."""
        from src.diarization import assign_speakers_to_segments, SpeakerSegment
        from src.utils import TranscriptSegment

        # Transcript segment with minimal overlap
        transcript_segments = [
            TranscriptSegment(0.0, 10.0, "Long sentence")
        ]

        # Speaker only covers small portion
        speaker_segments = [
            SpeakerSegment(0.0, 1.0, "SPEAKER_00")  # Only 10% overlap
        ]

        result = assign_speakers_to_segments(
            transcript_segments,
            speaker_segments,
            overlap_threshold=0.5  # Require 50% overlap
        )

        assert result[0].speaker == "UNKNOWN"


class TestGetSpeakerStatistics:
    """Tests for speaker statistics function."""

    def test_speaker_statistics(self):
        """Test speaking time calculation."""
        from src.diarization import get_speaker_statistics
        from src.utils import TranscriptSegment

        segments = [
            TranscriptSegment(0.0, 5.0, "Hello", speaker="SPEAKER_00"),
            TranscriptSegment(5.0, 10.0, "World", speaker="SPEAKER_01"),
            TranscriptSegment(10.0, 15.0, "Test", speaker="SPEAKER_00"),
        ]

        stats = get_speaker_statistics(segments)

        assert stats["SPEAKER_00"] == 10.0  # 5 + 5 seconds
        assert stats["SPEAKER_01"] == 5.0

    def test_unknown_speaker(self):
        """Test handling of unknown speakers."""
        from src.diarization import get_speaker_statistics
        from src.utils import TranscriptSegment

        segments = [
            TranscriptSegment(0.0, 5.0, "Hello", speaker=None),
        ]

        stats = get_speaker_statistics(segments)
        assert "UNKNOWN" in stats
