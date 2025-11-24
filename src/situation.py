# Copyright (c) 2025 Harrold Holdings GmbH
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license information.

"""
Situation/scene classification module using AST (Audio Spectrogram Transformer).

Classifies audio scenes into practical situations like meeting, office, outdoor, etc.
Uses the MIT AST model fine-tuned on AudioSet.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import numpy as np

from .utils import SituationSegment

logger = logging.getLogger("media_intelligence.situation")


# Mapping from AudioSet labels to practical situations
SITUATION_MAPPING = {
    "airplane": [
        "Aircraft", "Fixed-wing aircraft", "Airplane", "Jet engine",
        "Propeller, airscrew", "Aircraft engine", "Light aircraft"
    ],
    "car": [
        "Vehicle", "Car", "Motor vehicle (road)", "Engine", "Traffic noise",
        "Road traffic", "Car horn", "Car alarm", "Idling", "Accelerating"
    ],
    "walking": [
        "Walk, footsteps", "Run", "Footsteps", "Gait", "Running",
        "Jogging", "Shuffling"
    ],
    "meeting": [
        "Speech", "Conversation", "Chatter", "Crowd", "Inside, public space",
        "Narration, monologue", "Discussion", "Debate"
    ],
    "office": [
        "Computer keyboard", "Typing", "Inside, small room", "Printer",
        "Mouse click", "Clicking", "Mechanical fan", "Air conditioning"
    ],
    "outdoor": [
        "Wind", "Rain", "Bird", "Outside, urban or manmade", "Outside, rural or natural",
        "Wind noise (microphone)", "Rustling leaves", "Rain on surface",
        "Thunder", "Thunderstorm", "Water", "Stream", "River"
    ],
    "restaurant": [
        "Dishes, pots, and pans", "Cutlery, silverware", "Restaurant",
        "Clinking", "Clanging", "Chopping (food)", "Sizzle", "Frying (food)"
    ],
    "quiet": [
        "Silence", "Inside, small room", "Quiet", "Ambient",
        "White noise", "Pink noise", "Room tone"
    ],
}

# Reverse mapping: AudioSet label -> situation
LABEL_TO_SITUATION: Dict[str, str] = {}
for situation, labels in SITUATION_MAPPING.items():
    for label in labels:
        LABEL_TO_SITUATION[label.lower()] = situation


@dataclass
class SituationConfig:
    """Configuration for situation classification."""
    model: str = "MIT/ast-finetuned-audioset-10-10-0.4593"
    segment_duration: float = 30.0
    confidence_threshold: float = 0.3
    device: str = "cpu"


class SituationClassifier:
    """
    Audio scene classification using AST (Audio Spectrogram Transformer).

    Classifies audio into practical situations like meeting, office, outdoor, etc.
    Uses AudioSet labels mapped to higher-level situation categories.

    Attributes:
        config: SituationConfig instance
        model: Loaded AST model
        feature_extractor: Audio feature extractor
    """

    def __init__(self, config: Optional[SituationConfig] = None):
        """
        Initialize the classifier.

        Args:
            config: SituationConfig instance. Uses defaults if not provided.
        """
        self.config = config or SituationConfig()
        self.model = None
        self.feature_extractor = None
        self.id2label = None
        self._load_model()

    def _load_model(self) -> None:
        """Load the AST model and feature extractor."""
        from transformers import AutoFeatureExtractor, ASTForAudioClassification
        import torch

        logger.info(f"Loading AST model: {self.config.model}")

        self.feature_extractor = AutoFeatureExtractor.from_pretrained(
            self.config.model
        )
        self.model = ASTForAudioClassification.from_pretrained(
            self.config.model
        )

        # Move to device
        device = torch.device(self.config.device)
        self.model.to(device)
        self.model.eval()

        # Get label mapping
        self.id2label = self.model.config.id2label

        logger.info(f"AST model loaded with {len(self.id2label)} classes")

    def classify_segment(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
    ) -> Tuple[str, float, List[Dict[str, float]]]:
        """
        Classify a single audio segment.

        Args:
            audio: Audio data as numpy array
            sample_rate: Sample rate of audio

        Returns:
            Tuple of (situation, confidence, top_predictions)
            - situation: Mapped situation category
            - confidence: Confidence score for top prediction
            - top_predictions: List of top AudioSet predictions with scores

        Raises:
            RuntimeError: If model not loaded
        """
        if self.model is None or self.feature_extractor is None:
            raise RuntimeError("Model not loaded")

        import torch

        # Ensure audio is float32
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # Ensure mono
        if audio.ndim > 1:
            audio = audio.mean(axis=0)

        # Extract features
        inputs = self.feature_extractor(
            audio,
            sampling_rate=sample_rate,
            return_tensors="pt",
            padding=True
        )

        # Move to device
        device = next(self.model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}

        # Run inference
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits

        # Get probabilities
        probs = torch.softmax(logits, dim=-1)[0]

        # Get top predictions
        top_k = 10
        top_probs, top_indices = torch.topk(probs, top_k)

        top_predictions = []
        for prob, idx in zip(top_probs.tolist(), top_indices.tolist()):
            label = self.id2label[idx]
            top_predictions.append({
                "label": label,
                "confidence": prob
            })

        # Map to situation
        situation = self._map_to_situation(top_predictions)
        confidence = top_predictions[0]["confidence"] if top_predictions else 0.0

        return situation, confidence, top_predictions

    def _map_to_situation(
        self,
        predictions: List[Dict[str, float]]
    ) -> str:
        """
        Map AudioSet predictions to a practical situation.

        Uses a voting mechanism based on the top predictions and their confidences.

        Args:
            predictions: List of prediction dicts with 'label' and 'confidence'

        Returns:
            Mapped situation category
        """
        # Accumulate scores for each situation
        situation_scores: Dict[str, float] = {}

        for pred in predictions:
            label = pred["label"].lower()
            confidence = pred["confidence"]

            # Check direct mapping
            if label in LABEL_TO_SITUATION:
                situation = LABEL_TO_SITUATION[label]
                situation_scores[situation] = situation_scores.get(situation, 0.0) + confidence

            # Check partial matches
            for sit_label, sit_name in LABEL_TO_SITUATION.items():
                if sit_label in label or label in sit_label:
                    situation_scores[sit_name] = situation_scores.get(sit_name, 0.0) + confidence * 0.5

        # Return situation with highest score, or "unknown" if no matches
        if not situation_scores:
            return "unknown"

        return max(situation_scores.items(), key=lambda x: x[1])[0]

    def classify_audio(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        segment_duration: Optional[float] = None,
    ) -> Tuple[List[SituationSegment], str]:
        """
        Classify full audio with sliding windows.

        Args:
            audio: Audio data as numpy array
            sample_rate: Sample rate of audio
            segment_duration: Duration of each segment (default from config)

        Returns:
            Tuple of (list of SituationSegments, overall_situation)
        """
        segment_duration = segment_duration or self.config.segment_duration
        segment_samples = int(segment_duration * sample_rate)

        duration = len(audio) / sample_rate
        segments = []

        # Process in windows
        start_sample = 0
        while start_sample < len(audio):
            end_sample = min(start_sample + segment_samples, len(audio))
            segment_audio = audio[start_sample:end_sample]

            # Skip very short segments
            if len(segment_audio) < sample_rate:  # Less than 1 second
                break

            start_time = start_sample / sample_rate
            end_time = end_sample / sample_rate

            situation, confidence, top_preds = self.classify_segment(
                segment_audio, sample_rate
            )

            segments.append(SituationSegment(
                start=start_time,
                end=end_time,
                situation=situation,
                confidence=confidence,
                top_predictions=top_preds[:5]  # Keep top 5
            ))

            start_sample = end_sample

        # Determine overall situation by voting
        overall_situation = self._determine_overall_situation(segments)

        logger.info(
            f"Situation classification complete: {len(segments)} segments, "
            f"overall={overall_situation}"
        )

        return segments, overall_situation

    def _determine_overall_situation(
        self,
        segments: List[SituationSegment]
    ) -> str:
        """
        Determine overall situation from segment classifications.

        Uses weighted voting based on segment duration and confidence.

        Args:
            segments: List of situation segments

        Returns:
            Overall situation category
        """
        if not segments:
            return "unknown"

        # Weighted voting
        situation_weights: Dict[str, float] = {}

        for seg in segments:
            duration = seg.end - seg.start
            weight = duration * seg.confidence
            situation_weights[seg.situation] = situation_weights.get(seg.situation, 0.0) + weight

        if not situation_weights:
            return "unknown"

        return max(situation_weights.items(), key=lambda x: x[1])[0]

    @staticmethod
    def get_available_situations() -> List[str]:
        """
        Get list of available situation categories.

        Returns:
            List of situation category names
        """
        return list(SITUATION_MAPPING.keys())

    @staticmethod
    def get_situation_labels(situation: str) -> List[str]:
        """
        Get AudioSet labels associated with a situation.

        Args:
            situation: Situation category name

        Returns:
            List of associated AudioSet labels
        """
        return SITUATION_MAPPING.get(situation, [])
