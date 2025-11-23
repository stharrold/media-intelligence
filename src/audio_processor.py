"""
Main audio processing orchestrator for the Media Intelligence Pipeline.
"""

import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .situation_classifier import SituationClassifier, SituationPrediction, SituationResult
from .speech_client import SpeechClient, TranscriptSegment, TranscriptionResult
from .storage_manager import StorageManager
from .utils import (
    estimate_cost,
    format_timestamp,
    generate_file_id,
    get_audio_duration,
    get_file_extension,
    is_supported_format,
    load_config,
    parse_gcs_uri,
    validate_audio_duration,
)

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of complete audio processing."""

    gcs_input_uri: str
    gcs_output_uri: str
    file_id: str
    duration: float
    transcript_segments: list[TranscriptSegment]
    situation_predictions: list[SituationPrediction]
    speaker_count: int
    overall_situation: str
    overall_situation_confidence: float
    processing_time: float
    cost_estimate: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)
    transcript_uri: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "gcs_input_uri": self.gcs_input_uri,
            "gcs_output_uri": self.gcs_output_uri,
            "file_id": self.file_id,
            "duration": self.duration,
            "transcript_segments": [s.to_dict() for s in self.transcript_segments],
            "situation_predictions": [p.to_dict() for p in self.situation_predictions],
            "speaker_count": self.speaker_count,
            "overall_situation": self.overall_situation,
            "overall_situation_confidence": self.overall_situation_confidence,
            "processing_time": self.processing_time,
            "cost_estimate": self.cost_estimate,
            "metadata": self.metadata,
            "transcript_uri": self.transcript_uri,
            "error": self.error,
        }

    def get_transcript_text(
        self,
        include_speakers: bool = True,
        include_timestamps: bool = True,
    ) -> str:
        """
        Generate formatted transcript text.

        Args:
            include_speakers: Include speaker labels.
            include_timestamps: Include timestamps.

        Returns:
            Formatted transcript string.
        """
        lines = []
        current_speaker = None

        for segment in self.transcript_segments:
            parts = []

            # Add timestamp
            if include_timestamps:
                ts = format_timestamp(segment.start_time)
                parts.append(f"[{ts}]")

            # Add speaker label
            if include_speakers and segment.speaker_tag is not None:
                if segment.speaker_tag != current_speaker:
                    current_speaker = segment.speaker_tag
                    parts.append(f"Speaker {current_speaker + 1}:")

            # Add text
            parts.append(segment.text)

            lines.append(" ".join(parts))

        return "\n".join(lines)


class AudioProcessor:
    """
    Main orchestrator for audio processing pipeline.

    Coordinates transcription, diarization, and situation classification.
    """

    def __init__(
        self,
        speech_client: SpeechClient | None = None,
        situation_classifier: SituationClassifier | None = None,
        storage_manager: StorageManager | None = None,
        config: dict[str, Any] | None = None,
    ):
        """
        Initialize the Audio Processor.

        Args:
            speech_client: Optional pre-configured SpeechClient.
            situation_classifier: Optional pre-configured SituationClassifier.
            storage_manager: Optional pre-configured StorageManager.
            config: Optional configuration dictionary.
        """
        self.config = config or load_config()

        # Initialize components lazily
        self._speech_client = speech_client
        self._situation_classifier = situation_classifier
        self._storage_manager = storage_manager

    @property
    def speech_client(self) -> SpeechClient:
        """Lazy initialization of Speech client."""
        if self._speech_client is None:
            self._speech_client = SpeechClient()
        return self._speech_client

    @property
    def situation_classifier(self) -> SituationClassifier:
        """Lazy initialization of Situation classifier."""
        if self._situation_classifier is None:
            self._situation_classifier = SituationClassifier()
        return self._situation_classifier

    @property
    def storage_manager(self) -> StorageManager:
        """Lazy initialization of Storage manager."""
        if self._storage_manager is None:
            self._storage_manager = StorageManager()
        return self._storage_manager

    def process_file(
        self,
        gcs_uri: str,
        output_bucket: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> ProcessingResult:
        """
        Process an audio file from GCS.

        Args:
            gcs_uri: GCS URI of the input audio file.
            output_bucket: Bucket for output files. If None, uses configured bucket.
            config: Optional processing configuration overrides.

        Returns:
            ProcessingResult with all analysis results.
        """
        start_time = time.time()
        file_id = generate_file_id()

        # Merge configuration
        processing_config = self._merge_config(config)

        logger.info(f"Processing {gcs_uri} (file_id: {file_id})")

        try:
            # Validate input
            self._validate_input(gcs_uri, processing_config)

            # Get audio duration
            duration = self._get_duration(gcs_uri)

            # Validate duration
            max_duration = processing_config.get("processing", {}).get(
                "max_duration_minutes", 480
            )
            validate_audio_duration(duration, max_duration)

            # Run transcription
            transcription_result = self._transcribe(gcs_uri, processing_config)

            # Run situation classification
            situation_result = self._classify_situations(
                gcs_uri, duration, processing_config
            )

            # Calculate cost estimate
            cost = estimate_cost(
                duration,
                self.config,
                enable_diarization=processing_config.get("speech", {})
                .get("diarization", {})
                .get("enabled", True),
                enable_situation_detection=processing_config.get("situation", {}).get(
                    "enabled", True
                ),
            )

            # Build result
            processing_time = time.time() - start_time

            result = ProcessingResult(
                gcs_input_uri=gcs_uri,
                gcs_output_uri="",  # Will be set after saving
                file_id=file_id,
                duration=duration,
                transcript_segments=transcription_result.segments,
                situation_predictions=situation_result.predictions,
                speaker_count=transcription_result.speaker_count,
                overall_situation=situation_result.overall_situation,
                overall_situation_confidence=situation_result.overall_confidence,
                processing_time=processing_time,
                cost_estimate=cost,
                metadata=self._build_metadata(
                    gcs_uri,
                    transcription_result,
                    situation_result,
                    processing_config,
                ),
            )

            # Save outputs
            result = self._save_outputs(result, output_bucket, processing_config)

            logger.info(
                f"Processing complete for {gcs_uri}: "
                f"{len(result.transcript_segments)} segments, "
                f"{result.speaker_count} speakers, "
                f"{result.overall_situation} situation, "
                f"{processing_time:.2f}s processing time"
            )

            return result

        except Exception as e:
            logger.error(f"Processing failed for {gcs_uri}: {e}", exc_info=True)

            # Return error result
            return ProcessingResult(
                gcs_input_uri=gcs_uri,
                gcs_output_uri="",
                file_id=file_id,
                duration=0.0,
                transcript_segments=[],
                situation_predictions=[],
                speaker_count=0,
                overall_situation="unknown",
                overall_situation_confidence=0.0,
                processing_time=time.time() - start_time,
                cost_estimate={},
                error=str(e),
            )

    def _merge_config(self, overrides: dict[str, Any] | None) -> dict[str, Any]:
        """Merge override configuration with defaults."""
        if overrides is None:
            return self.config

        merged = self.config.copy()

        # Simple shallow merge for common overrides
        if "language_code" in overrides:
            merged.setdefault("speech", {})["language_codes"] = [overrides["language_code"]]

        if "model" in overrides:
            merged.setdefault("speech", {})["model"] = overrides["model"]

        if "min_speakers" in overrides:
            merged.setdefault("speech", {}).setdefault("diarization", {})[
                "min_speaker_count"
            ] = overrides["min_speakers"]

        if "max_speakers" in overrides:
            merged.setdefault("speech", {}).setdefault("diarization", {})[
                "max_speaker_count"
            ] = overrides["max_speakers"]

        return merged

    def _validate_input(self, gcs_uri: str, config: dict[str, Any]) -> None:
        """Validate input file."""
        # Check format
        supported = config.get("supported_formats", [])
        if supported and not is_supported_format(gcs_uri, supported):
            ext = get_file_extension(gcs_uri)
            raise ValueError(f"Unsupported audio format: {ext}")

        # Check file exists
        if not self.storage_manager.file_exists(gcs_uri):
            raise FileNotFoundError(f"File not found: {gcs_uri}")

    def _get_duration(self, gcs_uri: str) -> float:
        """Get audio duration, downloading if necessary."""
        with tempfile.NamedTemporaryFile(
            suffix=f".{get_file_extension(gcs_uri)}", delete=True
        ) as tmp:
            local_path = self.storage_manager.download_file(gcs_uri, tmp.name)
            return get_audio_duration(local_path)

    def _transcribe(
        self, gcs_uri: str, config: dict[str, Any]
    ) -> TranscriptionResult:
        """Run transcription."""
        speech_config = config.get("speech", {})
        diarization_config = speech_config.get("diarization", {})

        return self.speech_client.transcribe_gcs(
            gcs_uri=gcs_uri,
            language_code=speech_config.get("language_codes", ["en-US"])[0],
            model=speech_config.get("model", "long"),
            enable_diarization=diarization_config.get("enabled", True),
            min_speaker_count=diarization_config.get("min_speaker_count", 2),
            max_speaker_count=diarization_config.get("max_speaker_count", 6),
        )

    def _classify_situations(
        self, gcs_uri: str, duration: float, config: dict[str, Any]
    ) -> SituationResult:
        """Run situation classification."""
        situation_config = config.get("situation", {})

        if not situation_config.get("enabled", True):
            # Return empty result if disabled
            return SituationResult(
                predictions=[],
                overall_situation="unknown",
                overall_confidence=0.0,
                segment_duration=30.0,
            )

        segment_duration = config.get("processing", {}).get("segment_duration", 30)

        return self.situation_classifier.classify_audio(
            gcs_uri=gcs_uri,
            segment_duration=segment_duration,
            total_duration=duration,
            storage_manager=self.storage_manager,
        )

    def _build_metadata(
        self,
        gcs_uri: str,
        transcription_result: TranscriptionResult,
        situation_result: SituationResult,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Build metadata dictionary."""
        return {
            "input_file": gcs_uri,
            "processed_at": datetime.utcnow().isoformat(),
            "model_used": transcription_result.model_used,
            "language_code": transcription_result.language_code,
            "diarization_enabled": config.get("speech", {})
            .get("diarization", {})
            .get("enabled", True),
            "situation_classification_enabled": config.get("situation", {}).get(
                "enabled", True
            ),
            "segment_duration": situation_result.segment_duration,
        }

    def _save_outputs(
        self,
        result: ProcessingResult,
        output_bucket: str | None,
        config: dict[str, Any],
    ) -> ProcessingResult:
        """Save output files to GCS."""
        if output_bucket is None:
            output_bucket = self.storage_manager.output_bucket

        output_config = config.get("output", {})
        storage_config = config.get("storage", {})

        # Save JSON result
        if output_config.get("json", {}).get("enabled", True):
            json_path = f"{storage_config.get('results_prefix', 'results/')}{result.file_id}.json"
            result.gcs_output_uri = self.storage_manager.upload_json(
                result.to_dict(),
                bucket_name=output_bucket,
                blob_path=json_path,
            )

        # Save plain text transcript
        if output_config.get("txt", {}).get("enabled", True):
            txt_config = output_config.get("txt", {})
            transcript_text = result.get_transcript_text(
                include_speakers=txt_config.get("include_speaker_labels", True),
                include_timestamps=txt_config.get("include_timestamps", True),
            )
            txt_path = f"{storage_config.get('transcripts_prefix', 'transcripts/')}{result.file_id}.txt"
            result.transcript_uri = self.storage_manager.upload_text(
                transcript_text,
                bucket_name=output_bucket,
                blob_path=txt_path,
            )

        return result

    def process_batch(
        self,
        gcs_uris: list[str],
        output_bucket: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> list[ProcessingResult]:
        """
        Process multiple audio files.

        Args:
            gcs_uris: List of GCS URIs to process.
            output_bucket: Bucket for output files.
            config: Optional processing configuration.

        Returns:
            List of ProcessingResult objects.
        """
        results = []

        for gcs_uri in gcs_uris:
            result = self.process_file(gcs_uri, output_bucket, config)
            results.append(result)

        return results
