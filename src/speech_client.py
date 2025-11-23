"""
Google Cloud Speech-to-Text V2 client for the Media Intelligence Pipeline.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any

from google.api_core import exceptions
from google.cloud.speech_v2 import SpeechClient as GoogleSpeechClient
from google.cloud.speech_v2.types import cloud_speech
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


@dataclass
class TranscriptSegment:
    """A segment of transcribed audio."""

    start_time: float  # Seconds
    end_time: float  # Seconds
    text: str  # Transcript text
    speaker_tag: int | None = None  # Speaker ID (0-5)
    confidence: float = 0.0  # 0.0-1.0
    language_code: str = "en-US"  # Auto-detected or specified
    words: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "text": self.text,
            "speaker_tag": self.speaker_tag,
            "confidence": self.confidence,
            "language_code": self.language_code,
            "words": self.words,
        }


@dataclass
class TranscriptionResult:
    """Result of audio transcription."""

    segments: list[TranscriptSegment]
    speaker_count: int
    total_duration: float
    language_code: str
    model_used: str
    raw_response: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "segments": [s.to_dict() for s in self.segments],
            "speaker_count": self.speaker_count,
            "total_duration": self.total_duration,
            "language_code": self.language_code,
            "model_used": self.model_used,
        }

    def get_full_transcript(self, include_speakers: bool = True) -> str:
        """
        Get the full transcript as a string.

        Args:
            include_speakers: Whether to include speaker labels.

        Returns:
            Full transcript text.
        """
        lines = []
        current_speaker = None

        for segment in self.segments:
            if include_speakers and segment.speaker_tag is not None:
                if segment.speaker_tag != current_speaker:
                    current_speaker = segment.speaker_tag
                    lines.append(f"\n[Speaker {current_speaker + 1}]")
            lines.append(segment.text)

        return " ".join(lines).strip()


class SpeechClient:
    """Client for Google Cloud Speech-to-Text V2 API."""

    def __init__(
        self,
        project_id: str | None = None,
        location: str = "global",
        client: GoogleSpeechClient | None = None,
    ):
        """
        Initialize the Speech Client.

        Args:
            project_id: GCP project ID. If None, uses PROJECT_ID env var.
            location: GCP location for the recognizer. Default is "global".
            client: Optional pre-configured Speech client (for testing).
        """
        self.project_id = project_id or os.getenv("PROJECT_ID")
        self.location = location
        self._client = client

        if not self.project_id:
            raise ValueError("PROJECT_ID must be set")

    @property
    def client(self) -> GoogleSpeechClient:
        """Lazy initialization of Speech client."""
        if self._client is None:
            self._client = GoogleSpeechClient()
        return self._client

    def _get_recognizer_path(self) -> str:
        """Get the recognizer resource path."""
        return f"projects/{self.project_id}/locations/{self.location}/recognizers/_"

    def _build_config(
        self,
        language_code: str = "en-US",
        model: str = "long",
        enable_diarization: bool = True,
        min_speaker_count: int = 2,
        max_speaker_count: int = 6,
        **kwargs: Any,
    ) -> cloud_speech.RecognitionConfig:
        """
        Build recognition configuration.

        Args:
            language_code: Language code for transcription.
            model: Model to use (long, short, telephony, video).
            enable_diarization: Whether to enable speaker diarization.
            min_speaker_count: Minimum number of speakers.
            max_speaker_count: Maximum number of speakers.
            **kwargs: Additional configuration options.

        Returns:
            RecognitionConfig object.
        """
        # Build diarization config if enabled
        diarization_config = None
        if enable_diarization:
            diarization_config = cloud_speech.SpeakerDiarizationConfig(
                min_speaker_count=min_speaker_count,
                max_speaker_count=max_speaker_count,
            )

        # Build features config
        features = cloud_speech.RecognitionFeatures(
            enable_automatic_punctuation=kwargs.get("enable_automatic_punctuation", True),
            enable_word_time_offsets=kwargs.get("enable_word_time_offsets", True),
            enable_word_confidence=kwargs.get("enable_word_confidence", True),
            enable_spoken_punctuation=kwargs.get("enable_spoken_punctuation", False),
            enable_spoken_emojis=kwargs.get("enable_spoken_emojis", False),
            diarization_config=diarization_config,
        )

        # Build recognition config
        config = cloud_speech.RecognitionConfig(
            auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
            language_codes=[language_code],
            model=model,
            features=features,
        )

        return config

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (exceptions.ServiceUnavailable, exceptions.TooManyRequests)
        ),
    )
    def transcribe_gcs(
        self,
        gcs_uri: str,
        language_code: str = "en-US",
        model: str = "long",
        enable_diarization: bool = True,
        min_speaker_count: int = 2,
        max_speaker_count: int = 6,
        **kwargs: Any,
    ) -> TranscriptionResult:
        """
        Transcribe an audio file from Google Cloud Storage.

        Args:
            gcs_uri: GCS URI of the audio file (gs://bucket/path/to/file).
            language_code: Language code for transcription.
            model: Model to use (long, short, telephony, video).
            enable_diarization: Whether to enable speaker diarization.
            min_speaker_count: Minimum number of speakers.
            max_speaker_count: Maximum number of speakers.
            **kwargs: Additional configuration options.

        Returns:
            TranscriptionResult with segments and metadata.
        """
        logger.info(f"Starting transcription for {gcs_uri}")
        logger.info(f"Model: {model}, Language: {language_code}, Diarization: {enable_diarization}")

        # Build configuration
        config = self._build_config(
            language_code=language_code,
            model=model,
            enable_diarization=enable_diarization,
            min_speaker_count=min_speaker_count,
            max_speaker_count=max_speaker_count,
            **kwargs,
        )

        # Build request
        request = cloud_speech.BatchRecognizeRequest(
            recognizer=self._get_recognizer_path(),
            config=config,
            files=[
                cloud_speech.BatchRecognizeFileMetadata(uri=gcs_uri),
            ],
            recognition_output_config=cloud_speech.RecognitionOutputConfig(
                inline_response_config=cloud_speech.InlineOutputConfig(),
            ),
        )

        # Execute batch recognition (long-running operation)
        operation = self.client.batch_recognize(request=request)
        logger.info(f"Waiting for transcription operation to complete...")

        response = operation.result(timeout=3600)  # 1 hour timeout

        # Parse results
        return self._parse_batch_response(
            response,
            gcs_uri,
            model,
            language_code,
            enable_diarization,
        )

    def _parse_batch_response(
        self,
        response: cloud_speech.BatchRecognizeResponse,
        gcs_uri: str,
        model: str,
        language_code: str,
        enable_diarization: bool,
    ) -> TranscriptionResult:
        """
        Parse batch recognition response into TranscriptionResult.

        Args:
            response: The batch recognition response.
            gcs_uri: Original GCS URI.
            model: Model used.
            language_code: Language code used.
            enable_diarization: Whether diarization was enabled.

        Returns:
            TranscriptionResult object.
        """
        segments: list[TranscriptSegment] = []
        speaker_tags_seen: set[int] = set()
        total_duration = 0.0

        # Get results for the file
        file_results = response.results.get(gcs_uri)

        if file_results is None:
            logger.warning(f"No results found for {gcs_uri}")
            return TranscriptionResult(
                segments=[],
                speaker_count=0,
                total_duration=0.0,
                language_code=language_code,
                model_used=model,
                raw_response=response,
            )

        transcript = file_results.transcript

        for result in transcript.results:
            if not result.alternatives:
                continue

            alternative = result.alternatives[0]

            # Extract word-level information with speaker tags
            words_data = []
            segment_speaker_tag = None
            segment_start = None
            segment_end = None

            for word_info in alternative.words:
                word_start = word_info.start_offset.total_seconds()
                word_end = word_info.end_offset.total_seconds()

                if segment_start is None:
                    segment_start = word_start
                segment_end = word_end

                if word_end > total_duration:
                    total_duration = word_end

                # Get speaker tag if available
                if enable_diarization and word_info.speaker_label:
                    try:
                        speaker_tag = int(word_info.speaker_label)
                        speaker_tags_seen.add(speaker_tag)
                        if segment_speaker_tag is None:
                            segment_speaker_tag = speaker_tag
                    except ValueError:
                        pass

                words_data.append({
                    "word": word_info.word,
                    "start_time": word_start,
                    "end_time": word_end,
                    "confidence": word_info.confidence,
                    "speaker_tag": segment_speaker_tag,
                })

            # Create segment
            segment = TranscriptSegment(
                start_time=segment_start or 0.0,
                end_time=segment_end or 0.0,
                text=alternative.transcript.strip(),
                speaker_tag=segment_speaker_tag,
                confidence=alternative.confidence,
                language_code=result.language_code or language_code,
                words=words_data,
            )

            if segment.text:
                segments.append(segment)

        # Calculate speaker count
        speaker_count = len(speaker_tags_seen) if speaker_tags_seen else 0

        logger.info(
            f"Transcription complete: {len(segments)} segments, "
            f"{speaker_count} speakers, {total_duration:.1f}s duration"
        )

        return TranscriptionResult(
            segments=segments,
            speaker_count=speaker_count,
            total_duration=total_duration,
            language_code=language_code,
            model_used=model,
            raw_response=response,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (exceptions.ServiceUnavailable, exceptions.TooManyRequests)
        ),
    )
    def transcribe_streaming(
        self,
        audio_generator,
        language_code: str = "en-US",
        model: str = "short",
        enable_diarization: bool = False,
        **kwargs: Any,
    ):
        """
        Transcribe audio from a streaming source.

        Args:
            audio_generator: Generator yielding audio chunks.
            language_code: Language code for transcription.
            model: Model to use (short recommended for streaming).
            enable_diarization: Whether to enable speaker diarization.
            **kwargs: Additional configuration options.

        Yields:
            TranscriptSegment for each recognized segment.
        """
        logger.info("Starting streaming transcription")

        config = self._build_config(
            language_code=language_code,
            model=model,
            enable_diarization=enable_diarization,
            **kwargs,
        )

        def request_generator():
            # First request contains config
            yield cloud_speech.StreamingRecognizeRequest(
                recognizer=self._get_recognizer_path(),
                streaming_config=cloud_speech.StreamingRecognitionConfig(
                    config=config,
                    streaming_features=cloud_speech.StreamingRecognitionFeatures(
                        interim_results=True,
                    ),
                ),
            )

            # Subsequent requests contain audio
            for chunk in audio_generator:
                yield cloud_speech.StreamingRecognizeRequest(audio=chunk)

        responses = self.client.streaming_recognize(requests=request_generator())

        for response in responses:
            for result in response.results:
                if not result.alternatives:
                    continue

                alternative = result.alternatives[0]

                # Only yield final results
                if result.is_final:
                    yield TranscriptSegment(
                        start_time=0.0,  # Streaming doesn't provide precise timing
                        end_time=0.0,
                        text=alternative.transcript.strip(),
                        confidence=alternative.confidence,
                        language_code=language_code,
                    )
