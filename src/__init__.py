# Copyright (c) 2025 Harrold Holdings GmbH
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license information.

"""
Media Intelligence Pipeline

A containerized audio and video processing pipeline for extracting
structured intelligence from recorded media.

Supports both local CPU-only deployment and GCP cloud-native deployment.
"""

__version__ = "0.1.0"
__author__ = "Harrold Holdings GmbH"

# Local deployment imports (optional - may not be available in GCP mode)
try:
    from .diarization import DiarizationConfig, Diarizer  # noqa: F401
    from .process_audio import AudioProcessor  # noqa: F401
    from .situation import SituationClassifier as LocalSituationClassifier  # noqa: F401
    from .situation import SituationConfig  # noqa: F401
    from .transcription import Transcriber, WhisperConfig  # noqa: F401
except ImportError:
    pass

# GCP deployment imports (optional - may not be available in local mode)
try:
    from .audio_processor import AudioProcessor as GCPAudioProcessor  # noqa: F401
    from .audio_processor import ProcessingResult  # noqa: F401
    from .situation_classifier import SituationClassifier as GCPSituationClassifier  # noqa: F401
    from .situation_classifier import SituationPrediction, SituationResult  # noqa: F401
    from .speech_client import SpeechClient, TranscriptionResult, TranscriptSegment  # noqa: F401
    from .storage_manager import StorageManager  # noqa: F401
except ImportError:
    pass
