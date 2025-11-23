"""
Media Intelligence Pipeline for GCP.

A cloud-native media processing pipeline using Google Cloud Platform
managed services for transcription, diarization, and situation detection.
"""

__version__ = "1.0.0"
__author__ = "Media Intelligence Team"

from .audio_processor import AudioProcessor, ProcessingResult
from .speech_client import SpeechClient, TranscriptSegment, TranscriptionResult
from .situation_classifier import SituationClassifier, SituationPrediction, SituationResult
from .storage_manager import StorageManager
from .utils import load_config, estimate_cost, get_audio_duration

__all__ = [
    "AudioProcessor",
    "ProcessingResult",
    "SpeechClient",
    "TranscriptSegment",
    "TranscriptionResult",
    "SituationClassifier",
    "SituationPrediction",
    "SituationResult",
    "StorageManager",
    "load_config",
    "estimate_cost",
    "get_audio_duration",
]
