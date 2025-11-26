"""
Vertex AI AutoML situation classifier for the Media Intelligence Pipeline.
"""

import logging
import os
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from google.api_core import exceptions
from google.cloud import aiplatform
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# Default situation labels
SITUATION_LABELS = [
    "airplane",
    "car",
    "walking",
    "meeting",
    "office",
    "outdoor",
    "restaurant",
    "quiet",
]


@dataclass
class SituationPrediction:
    """A prediction for a segment of audio."""

    situation: str  # Classified situation
    confidence: float  # 0.0-1.0
    start_time: float  # Segment start time in seconds
    end_time: float  # Segment end time in seconds
    all_scores: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "situation": self.situation,
            "confidence": self.confidence,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "all_scores": self.all_scores,
        }


@dataclass
class SituationResult:
    """Result of situation classification."""

    predictions: list[SituationPrediction]
    overall_situation: str
    overall_confidence: float
    segment_duration: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "predictions": [p.to_dict() for p in self.predictions],
            "overall_situation": self.overall_situation,
            "overall_confidence": self.overall_confidence,
            "segment_duration": self.segment_duration,
        }


class SituationClassifier:
    """
    Classifier for detecting acoustic situations in audio.

    Uses Vertex AI AutoML or a pre-trained model to classify
    audio segments into situation categories.
    """

    def __init__(
        self,
        project_id: str | None = None,
        endpoint_id: str | None = None,
        location: str = "us-central1",
        labels: list[str] | None = None,
    ):
        """
        Initialize the Situation Classifier.

        Args:
            project_id: GCP project ID. If None, uses PROJECT_ID env var.
            endpoint_id: Vertex AI endpoint ID. If None, uses VERTEX_AI_ENDPOINT_ID env var.
            location: GCP location for Vertex AI.
            labels: List of situation labels. If None, uses defaults.
        """
        self.project_id = project_id or os.getenv("PROJECT_ID")
        self.endpoint_id = endpoint_id or os.getenv("VERTEX_AI_ENDPOINT_ID")
        self.location = location or os.getenv("VERTEX_AI_LOCATION", "us-central1")
        self.labels = labels or SITUATION_LABELS

        self._endpoint = None
        self._initialized = False

    def _initialize(self) -> None:
        """Initialize Vertex AI SDK."""
        if self._initialized:
            return

        aiplatform.init(
            project=self.project_id,
            location=self.location,
        )
        self._initialized = True

    @property
    def endpoint(self):
        """Lazy initialization of Vertex AI endpoint."""
        if self._endpoint is None and self.endpoint_id:
            self._initialize()
            self._endpoint = aiplatform.Endpoint(endpoint_name=f"projects/{self.project_id}/locations/{self.location}/endpoints/{self.endpoint_id}")
        return self._endpoint

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((exceptions.ServiceUnavailable, exceptions.TooManyRequests)),
    )
    def classify_audio(
        self,
        gcs_uri: str,
        segment_duration: float = 30.0,
        total_duration: float | None = None,
        storage_manager=None,
    ) -> SituationResult:
        """
        Classify acoustic situations in an audio file.

        Args:
            gcs_uri: GCS URI of the audio file.
            segment_duration: Duration of each segment to classify (seconds).
            total_duration: Total duration of audio (if known).
            storage_manager: Optional StorageManager for downloading files.

        Returns:
            SituationResult with predictions for each segment.
        """
        logger.info(f"Classifying situations in {gcs_uri}")

        # If no endpoint is configured, use mock classification
        if not self.endpoint_id:
            logger.warning("No Vertex AI endpoint configured, using mock classification")
            return self._mock_classify(gcs_uri, segment_duration, total_duration)

        predictions = []

        # Calculate number of segments
        if total_duration is None:
            total_duration = self._get_audio_duration(gcs_uri, storage_manager)

        num_segments = max(1, int(total_duration / segment_duration))

        for i in range(num_segments):
            start_time = i * segment_duration
            end_time = min((i + 1) * segment_duration, total_duration)

            # Get prediction from Vertex AI
            prediction = self._predict_segment(gcs_uri, start_time, end_time)
            predictions.append(prediction)

        # Calculate overall situation
        overall_situation, overall_confidence = self._aggregate_predictions(predictions)

        logger.info(f"Classification complete: {len(predictions)} segments, " f"overall situation: {overall_situation} ({overall_confidence:.2f})")

        return SituationResult(
            predictions=predictions,
            overall_situation=overall_situation,
            overall_confidence=overall_confidence,
            segment_duration=segment_duration,
        )

    def _predict_segment(
        self,
        gcs_uri: str,
        start_time: float,
        end_time: float,
    ) -> SituationPrediction:
        """
        Get prediction for a single audio segment.

        Args:
            gcs_uri: GCS URI of the audio file.
            start_time: Segment start time.
            end_time: Segment end time.

        Returns:
            SituationPrediction for the segment.
        """
        try:
            # Prepare instance for prediction
            instance = {
                "gcs_uri": gcs_uri,
                "start_time": start_time,
                "end_time": end_time,
            }

            # Call Vertex AI endpoint
            response = self.endpoint.predict(instances=[instance])

            # Parse prediction
            prediction = response.predictions[0]

            # Handle different response formats
            if isinstance(prediction, dict):
                scores = prediction.get("confidences", prediction.get("scores", {}))
                if isinstance(scores, list):
                    scores = dict(zip(self.labels, scores, strict=True))
            else:
                scores = {self.labels[0]: 1.0}

            # Get top prediction
            if scores:
                top_label = max(scores, key=scores.get)
                top_confidence = scores[top_label]
            else:
                top_label = "unknown"
                top_confidence = 0.0

            return SituationPrediction(
                situation=top_label,
                confidence=top_confidence,
                start_time=start_time,
                end_time=end_time,
                all_scores=scores,
            )

        except Exception as e:
            logger.warning(f"Prediction failed for segment {start_time}-{end_time}: {e}")
            return SituationPrediction(
                situation="unknown",
                confidence=0.0,
                start_time=start_time,
                end_time=end_time,
            )

    def _mock_classify(
        self,
        gcs_uri: str,
        segment_duration: float,
        total_duration: float | None,
    ) -> SituationResult:
        """
        Generate mock classification results for testing.

        Args:
            gcs_uri: GCS URI of the audio file.
            segment_duration: Duration of each segment.
            total_duration: Total duration of audio.

        Returns:
            SituationResult with mock predictions.
        """
        # Default duration if not provided
        if total_duration is None:
            total_duration = 60.0

        predictions = []
        num_segments = max(1, int(total_duration / segment_duration))

        # Generate mock predictions with seeded random for deterministic tests
        import hashlib
        import random

        # Seed based on GCS URI for deterministic results in tests
        seed = int(hashlib.md5(gcs_uri.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)

        for i in range(num_segments):
            start_time = i * segment_duration
            end_time = min((i + 1) * segment_duration, total_duration)

            # Deterministic situation for mock based on seed
            situation = rng.choice(self.labels)
            confidence = rng.uniform(0.6, 0.95)

            predictions.append(
                SituationPrediction(
                    situation=situation,
                    confidence=confidence,
                    start_time=start_time,
                    end_time=end_time,
                    all_scores={situation: confidence},
                )
            )

        overall_situation, overall_confidence = self._aggregate_predictions(predictions)

        return SituationResult(
            predictions=predictions,
            overall_situation=overall_situation,
            overall_confidence=overall_confidence,
            segment_duration=segment_duration,
        )

    def _aggregate_predictions(
        self,
        predictions: list[SituationPrediction],
    ) -> tuple[str, float]:
        """
        Aggregate segment predictions into overall situation.

        Uses weighted voting based on confidence scores.

        Args:
            predictions: List of segment predictions.

        Returns:
            Tuple of (overall_situation, confidence).
        """
        if not predictions:
            return "unknown", 0.0

        # Weighted voting
        weighted_counts: Counter[str] = Counter()

        for pred in predictions:
            # Weight by confidence
            weighted_counts[pred.situation] += pred.confidence

        if not weighted_counts:
            return "unknown", 0.0

        # Get top situation
        overall_situation = weighted_counts.most_common(1)[0][0]

        # Calculate confidence as weighted average
        total_weight = sum(weighted_counts.values())
        overall_confidence = weighted_counts[overall_situation] / total_weight

        return overall_situation, overall_confidence

    def _get_audio_duration(
        self,
        gcs_uri: str,
        storage_manager=None,
    ) -> float:
        """
        Get duration of audio file.

        Args:
            gcs_uri: GCS URI of the audio file.
            storage_manager: Optional StorageManager for downloading.

        Returns:
            Duration in seconds.
        """
        if storage_manager is None:
            from .storage_manager import StorageManager

            storage_manager = StorageManager()

        # Download file temporarily
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            local_path = storage_manager.download_file(gcs_uri, tmp.name)

            try:
                import librosa

                duration = librosa.get_duration(filename=local_path)
                return duration
            except Exception:
                # Fallback: assume 60 seconds
                logger.warning(f"Could not determine duration for {gcs_uri}, assuming 60s")
                return 60.0


class MockSituationClassifier(SituationClassifier):
    """
    Mock classifier for testing without Vertex AI.

    Generates deterministic predictions based on filename.
    """

    def __init__(self, labels: list[str] | None = None):
        """Initialize mock classifier."""
        super().__init__(
            project_id="mock-project",
            endpoint_id=None,
            labels=labels,
        )

    def classify_audio(
        self,
        gcs_uri: str,
        segment_duration: float = 30.0,
        total_duration: float | None = None,
        storage_manager=None,
    ) -> SituationResult:
        """Generate mock predictions."""
        return self._mock_classify(gcs_uri, segment_duration, total_duration)
