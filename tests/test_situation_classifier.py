"""Tests for the Situation Classifier."""

from unittest.mock import Mock, patch

import pytest

from src.situation_classifier import (
    SITUATION_LABELS,
    MockSituationClassifier,
    SituationClassifier,
    SituationPrediction,
    SituationResult,
)


@pytest.fixture
def mock_classifier():
    """Create a mock situation classifier."""
    return MockSituationClassifier()


@pytest.fixture
def classifier_with_endpoint():
    """Create a classifier with mocked Vertex AI endpoint."""
    with patch("src.situation_classifier.aiplatform") as _mock_aiplatform:  # noqa: F841
        classifier = SituationClassifier(
            project_id="test-project",
            endpoint_id="test-endpoint",
            location="us-central1",
        )

        # Mock endpoint
        mock_endpoint = Mock()
        mock_prediction = Mock()
        mock_prediction.predictions = [{"confidences": {"meeting": 0.8, "office": 0.15, "quiet": 0.05}}]
        mock_endpoint.predict.return_value = mock_prediction

        classifier._endpoint = mock_endpoint
        return classifier


class TestSituationClassifier:
    """Tests for SituationClassifier class."""

    def test_init_with_project_id(self):
        """Test initialization with project ID."""
        classifier = SituationClassifier(
            project_id="test-project",
            endpoint_id="test-endpoint",
        )
        assert classifier.project_id == "test-project"
        assert classifier.endpoint_id == "test-endpoint"
        assert classifier.labels == SITUATION_LABELS

    def test_init_with_custom_labels(self):
        """Test initialization with custom labels."""
        custom_labels = ["indoor", "outdoor", "vehicle"]
        classifier = SituationClassifier(
            project_id="test-project",
            labels=custom_labels,
        )
        assert classifier.labels == custom_labels

    def test_mock_classify(self, mock_classifier):
        """Test mock classification."""
        result = mock_classifier.classify_audio(
            gcs_uri="gs://test-bucket/test.wav",
            segment_duration=30.0,
            total_duration=90.0,
        )

        assert isinstance(result, SituationResult)
        assert len(result.predictions) == 3  # 90s / 30s = 3 segments
        assert result.overall_situation in SITUATION_LABELS

    def test_mock_classify_single_segment(self, mock_classifier):
        """Test mock classification with single segment."""
        result = mock_classifier.classify_audio(
            gcs_uri="gs://test-bucket/short.wav",
            segment_duration=30.0,
            total_duration=15.0,  # Less than segment duration
        )

        assert len(result.predictions) == 1

    def test_aggregate_predictions_empty(self, mock_classifier):
        """Test aggregation with empty predictions."""
        situation, confidence = mock_classifier._aggregate_predictions([])
        assert situation == "unknown"
        assert confidence == 0.0

    def test_aggregate_predictions_single(self, mock_classifier):
        """Test aggregation with single prediction."""
        predictions = [
            SituationPrediction(
                situation="meeting",
                confidence=0.9,
                start_time=0.0,
                end_time=30.0,
            )
        ]
        situation, confidence = mock_classifier._aggregate_predictions(predictions)
        assert situation == "meeting"
        assert confidence == 1.0  # Only one prediction, so 100% for that situation

    def test_aggregate_predictions_multiple(self, mock_classifier):
        """Test aggregation with multiple predictions."""
        predictions = [
            SituationPrediction(
                situation="meeting",
                confidence=0.9,
                start_time=0.0,
                end_time=30.0,
            ),
            SituationPrediction(
                situation="meeting",
                confidence=0.8,
                start_time=30.0,
                end_time=60.0,
            ),
            SituationPrediction(
                situation="office",
                confidence=0.7,
                start_time=60.0,
                end_time=90.0,
            ),
        ]
        situation, confidence = mock_classifier._aggregate_predictions(predictions)
        assert situation == "meeting"
        # Confidence should be weighted average

    def test_classify_with_endpoint(self, classifier_with_endpoint):
        """Test classification with real endpoint (mocked)."""
        result = classifier_with_endpoint._predict_segment(
            gcs_uri="gs://test-bucket/test.wav",
            start_time=0.0,
            end_time=30.0,
        )

        assert isinstance(result, SituationPrediction)
        assert result.situation == "meeting"
        assert result.confidence == 0.8


class TestSituationPrediction:
    """Tests for SituationPrediction dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        prediction = SituationPrediction(
            situation="meeting",
            confidence=0.85,
            start_time=0.0,
            end_time=30.0,
            all_scores={"meeting": 0.85, "office": 0.10, "quiet": 0.05},
        )

        result = prediction.to_dict()

        assert result["situation"] == "meeting"
        assert result["confidence"] == 0.85
        assert result["start_time"] == 0.0
        assert result["end_time"] == 30.0
        assert "meeting" in result["all_scores"]


class TestSituationResult:
    """Tests for SituationResult dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        predictions = [
            SituationPrediction(
                situation="meeting",
                confidence=0.9,
                start_time=0.0,
                end_time=30.0,
            )
        ]

        result = SituationResult(
            predictions=predictions,
            overall_situation="meeting",
            overall_confidence=0.9,
            segment_duration=30.0,
        )

        data = result.to_dict()

        assert data["overall_situation"] == "meeting"
        assert data["overall_confidence"] == 0.9
        assert data["segment_duration"] == 30.0
        assert len(data["predictions"]) == 1


class TestSituationLabels:
    """Tests for situation labels."""

    def test_default_labels(self):
        """Test default situation labels."""
        expected = [
            "airplane",
            "car",
            "walking",
            "meeting",
            "office",
            "outdoor",
            "restaurant",
            "quiet",
        ]
        assert SITUATION_LABELS == expected

    def test_all_labels_lowercase(self):
        """Test all labels are lowercase."""
        for label in SITUATION_LABELS:
            assert label == label.lower()
