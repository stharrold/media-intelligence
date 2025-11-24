# Copyright (c) 2025 Harrold Holdings GmbH
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license information.

"""
Tests for the situation classification module.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock


class TestSituationConfig:
    """Tests for SituationConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        from src.situation import SituationConfig

        config = SituationConfig()
        assert config.model == "MIT/ast-finetuned-audioset-10-10-0.4593"
        assert config.segment_duration == 30.0
        assert config.confidence_threshold == 0.3
        assert config.device == "cpu"

    def test_custom_values(self):
        """Test custom configuration values."""
        from src.situation import SituationConfig

        config = SituationConfig(
            segment_duration=15.0,
            confidence_threshold=0.5,
            device="cuda"
        )
        assert config.segment_duration == 15.0
        assert config.confidence_threshold == 0.5
        assert config.device == "cuda"


class TestSituationMapping:
    """Tests for situation mapping constants."""

    def test_situation_mapping_exists(self):
        """Test that situation mapping is properly defined."""
        from src.situation import SITUATION_MAPPING

        expected_situations = [
            "airplane", "car", "walking", "meeting",
            "office", "outdoor", "restaurant", "quiet"
        ]

        for situation in expected_situations:
            assert situation in SITUATION_MAPPING
            assert len(SITUATION_MAPPING[situation]) > 0

    def test_label_to_situation_mapping(self):
        """Test reverse mapping from labels to situations."""
        from src.situation import LABEL_TO_SITUATION

        # Test some known mappings
        assert LABEL_TO_SITUATION.get("aircraft") == "airplane"
        assert LABEL_TO_SITUATION.get("vehicle") == "car"
        assert LABEL_TO_SITUATION.get("speech") == "meeting"


class TestSituationSegment:
    """Tests for SituationSegment dataclass."""

    def test_creation(self):
        """Test segment creation."""
        from src.utils import SituationSegment

        segment = SituationSegment(
            start=0.0,
            end=30.0,
            situation="meeting",
            confidence=0.95,
            top_predictions=[{"label": "Speech", "confidence": 0.95}]
        )
        assert segment.start == 0.0
        assert segment.end == 30.0
        assert segment.situation == "meeting"
        assert segment.confidence == 0.95
        assert len(segment.top_predictions) == 1

    def test_to_dict(self):
        """Test conversion to dictionary."""
        from src.utils import SituationSegment

        segment = SituationSegment(
            start=0.0,
            end=30.0,
            situation="office",
            confidence=0.8,
            top_predictions=[]
        )
        d = segment.to_dict()
        assert d["situation"] == "office"
        assert d["confidence"] == 0.8


class TestSituationClassifier:
    """Tests for the SituationClassifier class."""

    @patch('src.situation.AutoFeatureExtractor')
    @patch('src.situation.ASTForAudioClassification')
    def test_initialization(self, mock_ast, mock_extractor):
        """Test classifier initialization."""
        from src.situation import SituationClassifier, SituationConfig

        mock_ast.from_pretrained.return_value = Mock()
        mock_ast.from_pretrained.return_value.config.id2label = {0: "Speech"}
        mock_extractor.from_pretrained.return_value = Mock()

        config = SituationConfig()
        classifier = SituationClassifier(config)

        mock_ast.from_pretrained.assert_called_once()
        mock_extractor.from_pretrained.assert_called_once()

    def test_get_available_situations(self):
        """Test available situations list."""
        from src.situation import SituationClassifier

        situations = SituationClassifier.get_available_situations()
        assert "airplane" in situations
        assert "meeting" in situations
        assert "office" in situations
        assert "outdoor" in situations

    def test_get_situation_labels(self):
        """Test getting labels for a situation."""
        from src.situation import SituationClassifier

        labels = SituationClassifier.get_situation_labels("meeting")
        assert "Speech" in labels
        assert "Conversation" in labels

        empty_labels = SituationClassifier.get_situation_labels("nonexistent")
        assert empty_labels == []


class TestMapToSituation:
    """Tests for situation mapping logic."""

    @patch('src.situation.AutoFeatureExtractor')
    @patch('src.situation.ASTForAudioClassification')
    def test_map_speech_to_meeting(self, mock_ast, mock_extractor):
        """Test that speech predictions map to meeting."""
        from src.situation import SituationClassifier

        mock_ast.from_pretrained.return_value = Mock()
        mock_ast.from_pretrained.return_value.config.id2label = {0: "Speech"}
        mock_extractor.from_pretrained.return_value = Mock()

        classifier = SituationClassifier()

        predictions = [
            {"label": "Speech", "confidence": 0.9},
            {"label": "Conversation", "confidence": 0.8},
        ]

        situation = classifier._map_to_situation(predictions)
        assert situation == "meeting"

    @patch('src.situation.AutoFeatureExtractor')
    @patch('src.situation.ASTForAudioClassification')
    def test_map_vehicle_to_car(self, mock_ast, mock_extractor):
        """Test that vehicle predictions map to car."""
        from src.situation import SituationClassifier

        mock_ast.from_pretrained.return_value = Mock()
        mock_ast.from_pretrained.return_value.config.id2label = {0: "Vehicle"}
        mock_extractor.from_pretrained.return_value = Mock()

        classifier = SituationClassifier()

        predictions = [
            {"label": "Vehicle", "confidence": 0.85},
            {"label": "Engine", "confidence": 0.7},
        ]

        situation = classifier._map_to_situation(predictions)
        assert situation == "car"

    @patch('src.situation.AutoFeatureExtractor')
    @patch('src.situation.ASTForAudioClassification')
    def test_map_unknown_labels(self, mock_ast, mock_extractor):
        """Test mapping of unknown labels."""
        from src.situation import SituationClassifier

        mock_ast.from_pretrained.return_value = Mock()
        mock_ast.from_pretrained.return_value.config.id2label = {}
        mock_extractor.from_pretrained.return_value = Mock()

        classifier = SituationClassifier()

        predictions = [
            {"label": "Unknown_Label_XYZ", "confidence": 0.9},
        ]

        situation = classifier._map_to_situation(predictions)
        assert situation == "unknown"


class TestDetermineOverallSituation:
    """Tests for overall situation determination."""

    @patch('src.situation.AutoFeatureExtractor')
    @patch('src.situation.ASTForAudioClassification')
    def test_weighted_voting(self, mock_ast, mock_extractor):
        """Test weighted voting for overall situation."""
        from src.situation import SituationClassifier
        from src.utils import SituationSegment

        mock_ast.from_pretrained.return_value = Mock()
        mock_ast.from_pretrained.return_value.config.id2label = {}
        mock_extractor.from_pretrained.return_value = Mock()

        classifier = SituationClassifier()

        segments = [
            SituationSegment(0, 30, "meeting", 0.9, []),
            SituationSegment(30, 60, "meeting", 0.8, []),
            SituationSegment(60, 90, "office", 0.7, []),
        ]

        overall = classifier._determine_overall_situation(segments)
        # Meeting should win due to higher combined weight
        assert overall == "meeting"

    @patch('src.situation.AutoFeatureExtractor')
    @patch('src.situation.ASTForAudioClassification')
    def test_empty_segments(self, mock_ast, mock_extractor):
        """Test with empty segments list."""
        from src.situation import SituationClassifier

        mock_ast.from_pretrained.return_value = Mock()
        mock_ast.from_pretrained.return_value.config.id2label = {}
        mock_extractor.from_pretrained.return_value = Mock()

        classifier = SituationClassifier()
        overall = classifier._determine_overall_situation([])
        assert overall == "unknown"
