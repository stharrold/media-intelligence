# Copyright (c) 2025 Harrold Holdings GmbH
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license information.

"""
Media Intelligence Pipeline

A containerized audio and video processing pipeline for extracting
structured intelligence from recorded media.

Supports both local CPU-only deployment and GCP cloud-native deployment.
"""

__version__ = "1.0.0"
__author__ = "Harrold Holdings GmbH"

# Local deployment imports (optional - may not be available in GCP mode)
try:
    from .process_audio import AudioProcessor
    from .transcription import Transcriber, WhisperConfig
    from .diarization import Diarizer, DiarizationConfig
    from .situation import SituationClassifier as LocalSituationClassifier, SituationConfig
except ImportError:
    pass

# GCP deployment imports (optional - may not be available in local mode)
try:
    from .audio_processor import AudioProcessor as GCPAudioProcessor, ProcessingResult
    from .speech_client import SpeechClient, TranscriptSegment, TranscriptionResult
    from .situation_classifier import SituationClassifier as GCPSituationClassifier, SituationPrediction, SituationResult
    from .storage_manager import StorageManager
except ImportError:
    pass
