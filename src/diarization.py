# Copyright (c) 2025 Harrold Holdings GmbH
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license information.

"""
Speaker diarization module using pyannote-audio.

Identifies and labels different speakers in audio recordings.
Requires a HuggingFace token with access to pyannote models.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import numpy as np

from .utils import TranscriptSegment

logger = logging.getLogger("media_intelligence.diarization")


@dataclass
class DiarizationConfig:
    """Configuration for speaker diarization."""
    pipeline: str = "pyannote/speaker-diarization-3.1"
    min_speakers: Optional[int] = None
    max_speakers: Optional[int] = None
    device: str = "cpu"


class SpeakerSegment:
    """Represents a speaker turn in the audio."""

    def __init__(self, start: float, end: float, speaker: str):
        self.start = start
        self.end = end
        self.speaker = speaker

    def __repr__(self) -> str:
        return f"SpeakerSegment({self.start:.2f}-{self.end:.2f}, {self.speaker})"


class Diarizer:
    """
    Speaker diarization using pyannote-audio.

    Identifies different speakers in audio and assigns speaker labels.
    Requires HuggingFace token for model access.

    Attributes:
        config: DiarizationConfig instance
        pipeline: Loaded pyannote pipeline
        hf_token: HuggingFace authentication token
    """

    def __init__(
        self,
        config: Optional[DiarizationConfig] = None,
        hf_token: Optional[str] = None
    ):
        """
        Initialize the diarizer.

        Args:
            config: DiarizationConfig instance. Uses defaults if not provided.
            hf_token: HuggingFace token. Falls back to HUGGINGFACE_TOKEN env var.

        Raises:
            ValueError: If no HuggingFace token provided or found
        """
        self.config = config or DiarizationConfig()
        self.hf_token = hf_token or os.environ.get("HUGGINGFACE_TOKEN")
        self.pipeline = None

        if not self.hf_token:
            raise ValueError(
                "HuggingFace token required for speaker diarization.\n"
                "Solution:\n"
                "1. Create account at https://huggingface.co\n"
                "2. Accept terms at https://huggingface.co/pyannote/speaker-diarization-3.1\n"
                "3. Generate token at https://huggingface.co/settings/tokens\n"
                "4. Set HUGGINGFACE_TOKEN environment variable or pass to constructor"
            )

        self._load_pipeline()

    def _load_pipeline(self) -> None:
        """Load the pyannote diarization pipeline."""
        from pyannote.audio import Pipeline
        import torch

        logger.info(f"Loading diarization pipeline: {self.config.pipeline}")

        self.pipeline = Pipeline.from_pretrained(
            self.config.pipeline,
            use_auth_token=self.hf_token
        )

        # Move to appropriate device
        if self.config.device == "cpu":
            self.pipeline.to(torch.device("cpu"))
        else:
            self.pipeline.to(torch.device(self.config.device))

        logger.info("Diarization pipeline loaded successfully")

    def diarize(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None,
    ) -> List[SpeakerSegment]:
        """
        Perform speaker diarization on audio.

        Args:
            audio: Audio data as numpy array
            sample_rate: Sample rate of audio
            min_speakers: Minimum number of speakers (None for auto)
            max_speakers: Maximum number of speakers (None for auto)

        Returns:
            List of SpeakerSegment objects

        Raises:
            RuntimeError: If pipeline not loaded
        """
        if self.pipeline is None:
            raise RuntimeError("Pipeline not loaded")

        import torch

        # Use config defaults if not specified
        min_speakers = min_speakers or self.config.min_speakers
        max_speakers = max_speakers or self.config.max_speakers

        logger.debug(
            f"Diarizing {len(audio)/sample_rate:.2f}s of audio "
            f"(min_speakers={min_speakers}, max_speakers={max_speakers})"
        )

        # Prepare audio tensor
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # Ensure audio is 1D
        if audio.ndim > 1:
            audio = audio.mean(axis=0)

        waveform = torch.from_numpy(audio).unsqueeze(0)

        # Create audio dict for pyannote
        audio_dict = {
            "waveform": waveform,
            "sample_rate": sample_rate
        }

        # Build kwargs for pipeline
        kwargs = {}
        if min_speakers is not None:
            kwargs["min_speakers"] = min_speakers
        if max_speakers is not None:
            kwargs["max_speakers"] = max_speakers

        # Run diarization
        diarization = self.pipeline(audio_dict, **kwargs)

        # Convert to SpeakerSegment list
        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append(SpeakerSegment(
                start=turn.start,
                end=turn.end,
                speaker=speaker
            ))

        # Sort by start time
        segments.sort(key=lambda x: x.start)

        logger.info(
            f"Diarization complete: {len(segments)} turns, "
            f"{len(set(s.speaker for s in segments))} speakers"
        )

        return segments

    def diarize_file(
        self,
        file_path: str,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None,
    ) -> List[SpeakerSegment]:
        """
        Diarize an audio file.

        Args:
            file_path: Path to audio file
            min_speakers: Minimum number of speakers
            max_speakers: Maximum number of speakers

        Returns:
            List of SpeakerSegment objects
        """
        from .utils import load_audio

        audio, sr = load_audio(file_path)
        return self.diarize(audio, sr, min_speakers, max_speakers)


def assign_speakers_to_segments(
    transcript_segments: List[TranscriptSegment],
    speaker_segments: List[SpeakerSegment],
    overlap_threshold: float = 0.5
) -> List[TranscriptSegment]:
    """
    Assign speaker labels to transcript segments based on diarization.

    Uses overlap-based assignment: a transcript segment is assigned the speaker
    with the most temporal overlap.

    Args:
        transcript_segments: List of transcript segments
        speaker_segments: List of speaker segments from diarization
        overlap_threshold: Minimum overlap ratio to assign speaker

    Returns:
        List of transcript segments with speaker labels assigned
    """
    if not speaker_segments:
        logger.warning("No speaker segments provided, skipping speaker assignment")
        return transcript_segments

    for t_seg in transcript_segments:
        best_speaker = None
        best_overlap = 0.0

        for s_seg in speaker_segments:
            # Calculate overlap
            overlap_start = max(t_seg.start, s_seg.start)
            overlap_end = min(t_seg.end, s_seg.end)
            overlap_duration = max(0, overlap_end - overlap_start)

            # Calculate overlap ratio relative to transcript segment duration
            t_duration = t_seg.end - t_seg.start
            if t_duration > 0:
                overlap_ratio = overlap_duration / t_duration
                if overlap_ratio > best_overlap:
                    best_overlap = overlap_ratio
                    best_speaker = s_seg.speaker

        if best_overlap >= overlap_threshold:
            t_seg.speaker = best_speaker
        else:
            t_seg.speaker = "UNKNOWN"

    # Count speakers
    speakers = set(s.speaker for s in transcript_segments if s.speaker and s.speaker != "UNKNOWN")
    logger.debug(f"Assigned {len(speakers)} unique speakers to transcript segments")

    return transcript_segments


def get_speaker_statistics(segments: List[TranscriptSegment]) -> Dict[str, float]:
    """
    Calculate speaking time statistics for each speaker.

    Args:
        segments: List of transcript segments with speaker labels

    Returns:
        Dict mapping speaker ID to total speaking time in seconds
    """
    stats: Dict[str, float] = {}

    for seg in segments:
        speaker = seg.speaker or "UNKNOWN"
        duration = seg.end - seg.start
        stats[speaker] = stats.get(speaker, 0.0) + duration

    return stats
