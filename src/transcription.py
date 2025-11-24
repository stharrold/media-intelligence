# Copyright (c) 2025 Harrold Holdings GmbH
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license information.

"""
Transcription module using faster-whisper.

Provides speech-to-text functionality with support for multiple languages,
word-level timestamps, and voice activity detection filtering.
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple, Iterator, Any
from dataclasses import dataclass

import numpy as np

from .utils import TranscriptSegment

logger = logging.getLogger("media_intelligence.transcription")


@dataclass
class WhisperConfig:
    """Configuration for Whisper transcription."""
    model_size: str = "base.en"
    device: str = "cpu"
    compute_type: str = "int8"
    beam_size: int = 5
    language: Optional[str] = "en"
    word_timestamps: bool = True
    vad_filter: bool = True
    vad_min_silence_duration_ms: int = 500


class Transcriber:
    """
    Speech-to-text transcription using faster-whisper.

    Provides efficient transcription with INT8 quantization for CPU deployment.
    Supports multiple Whisper model sizes and languages.

    Attributes:
        config: WhisperConfig instance
        model: Loaded faster-whisper model
    """

    # Valid Whisper model sizes
    VALID_MODELS = {
        "tiny", "tiny.en", "base", "base.en", "small", "small.en",
        "medium", "medium.en", "large-v2", "large-v3"
    }

    def __init__(self, config: Optional[WhisperConfig] = None):
        """
        Initialize the transcriber.

        Args:
            config: WhisperConfig instance. Uses defaults if not provided.

        Raises:
            ValueError: If model_size is not a valid Whisper model
        """
        self.config = config or WhisperConfig()
        self.model = None

        # Validate model name at initialization
        if self.config.model_size not in self.VALID_MODELS:
            raise ValueError(
                f"Invalid Whisper model: '{self.config.model_size}'. "
                f"Valid models: {', '.join(sorted(self.VALID_MODELS))}"
            )

        self._load_model()

    def _load_model(self) -> None:
        """Load the faster-whisper model."""
        from faster_whisper import WhisperModel

        logger.info(
            f"Loading Whisper model: {self.config.model_size} "
            f"(device={self.config.device}, compute_type={self.config.compute_type})"
        )

        self.model = WhisperModel(
            self.config.model_size,
            device=self.config.device,
            compute_type=self.config.compute_type,
            cpu_threads=4,
        )

        logger.info("Whisper model loaded successfully")

    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        language: Optional[str] = None,
        beam_size: Optional[int] = None,
    ) -> Tuple[List[TranscriptSegment], dict]:
        """
        Transcribe audio to text.

        Args:
            audio: Audio data as numpy array (16kHz mono expected)
            sample_rate: Sample rate of audio (should be 16000)
            language: Language code (None for auto-detection)
            beam_size: Beam size for decoding (None uses config default)

        Returns:
            Tuple of (list of TranscriptSegments, metadata dict)

        Raises:
            RuntimeError: If model not loaded
            ValueError: If audio format invalid
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")

        if len(audio) == 0:
            logger.warning("Empty audio provided")
            return [], {"language": None, "language_probability": 0.0}

        # Use config defaults if not specified
        language = language or self.config.language
        beam_size = beam_size or self.config.beam_size

        # Auto-detect language if set to None or "auto"
        if language == "auto":
            language = None

        logger.debug(
            f"Transcribing {len(audio)/sample_rate:.2f}s of audio "
            f"(language={language}, beam_size={beam_size})"
        )

        # Run transcription
        segments_gen, info = self.model.transcribe(
            audio,
            language=language,
            beam_size=beam_size,
            word_timestamps=self.config.word_timestamps,
            vad_filter=self.config.vad_filter,
            vad_parameters=dict(
                min_silence_duration_ms=self.config.vad_min_silence_duration_ms
            ),
        )

        # Convert generator to list of segments
        segments = []
        for seg in segments_gen:
            transcript_segment = TranscriptSegment(
                start=seg.start,
                end=seg.end,
                text=seg.text.strip(),
                confidence=seg.avg_logprob if hasattr(seg, "avg_logprob") else 0.0,
            )
            segments.append(transcript_segment)
            logger.debug(f"Segment: [{seg.start:.2f}s-{seg.end:.2f}s] {seg.text.strip()}")

        metadata = {
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": info.duration,
        }

        logger.info(
            f"Transcription complete: {len(segments)} segments, "
            f"language={info.language} (prob={info.language_probability:.2f})"
        )

        return segments, metadata

    def transcribe_file(
        self,
        file_path: str,
        language: Optional[str] = None,
        beam_size: Optional[int] = None,
    ) -> Tuple[List[TranscriptSegment], dict]:
        """
        Transcribe an audio file.

        Args:
            file_path: Path to audio file
            language: Language code (None for auto-detection)
            beam_size: Beam size for decoding

        Returns:
            Tuple of (list of TranscriptSegments, metadata dict)
        """
        from .utils import load_audio

        audio, sr = load_audio(file_path)
        return self.transcribe(audio, sr, language, beam_size)

    @staticmethod
    def get_available_models() -> List[str]:
        """
        Get list of available Whisper model sizes.

        Returns:
            List of model size names
        """
        return [
            "tiny",
            "tiny.en",
            "base",
            "base.en",
            "small",
            "small.en",
            "medium",
            "medium.en",
            "large-v2",
            "large-v3",
        ]

    @staticmethod
    def get_model_info(model_size: str) -> dict:
        """
        Get information about a Whisper model.

        Args:
            model_size: Model size name

        Returns:
            Dict with model parameters and memory requirements
        """
        model_info = {
            "tiny": {"params": "39M", "vram": "~1GB", "speed": "~32x"},
            "tiny.en": {"params": "39M", "vram": "~1GB", "speed": "~32x"},
            "base": {"params": "74M", "vram": "~1GB", "speed": "~16x"},
            "base.en": {"params": "74M", "vram": "~1GB", "speed": "~16x"},
            "small": {"params": "244M", "vram": "~2GB", "speed": "~6x"},
            "small.en": {"params": "244M", "vram": "~2GB", "speed": "~6x"},
            "medium": {"params": "769M", "vram": "~5GB", "speed": "~2x"},
            "medium.en": {"params": "769M", "vram": "~5GB", "speed": "~2x"},
            "large-v2": {"params": "1550M", "vram": "~10GB", "speed": "~1x"},
            "large-v3": {"params": "1550M", "vram": "~10GB", "speed": "~1x"},
        }
        return model_info.get(model_size, {"params": "unknown", "vram": "unknown", "speed": "unknown"})
