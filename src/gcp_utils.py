"""
Utility functions for the Media Intelligence Pipeline.
"""

import math
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def load_config(config_path: str | None = None) -> dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to config file. If None, looks for config.yaml
                    in the project root.

    Returns:
        Configuration dictionary.
    """
    if config_path is None:
        # Look for config.yaml in project root
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config.yaml"

    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Override with environment variables
    env_overrides = {
        "project_id": os.getenv("PROJECT_ID"),
        "region": os.getenv("REGION"),
        "input_bucket": os.getenv("INPUT_BUCKET"),
        "output_bucket": os.getenv("OUTPUT_BUCKET"),
        "vertex_ai_endpoint_id": os.getenv("VERTEX_AI_ENDPOINT_ID"),
    }

    for key, value in env_overrides.items():
        if value is not None:
            config[key] = value

    return config


def generate_file_id() -> str:
    """
    Generate a unique file ID for output files.

    Returns:
        Unique file ID string.
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    return f"{timestamp}_{unique_id}"


def get_audio_duration(file_path: str) -> float:
    """
    Get the duration of an audio file in seconds.

    Args:
        file_path: Path to the audio file.

    Returns:
        Duration in seconds.
    """
    try:
        import librosa

        duration = librosa.get_duration(path=file_path)
        return duration
    except Exception:
        # Fallback using soundfile
        import soundfile as sf

        with sf.SoundFile(file_path) as f:
            return len(f) / f.samplerate


def estimate_cost(
    audio_duration_seconds: float,
    config: dict[str, Any] | None = None,
    enable_diarization: bool = True,
    enable_situation_detection: bool = True,
) -> dict[str, float]:
    """
    Estimate GCP costs for processing an audio file.

    Speech-to-Text V2 Enhanced (as of Nov 2024):
    - $0.009/15 seconds for enhanced models with diarization
    - $0.006/15 seconds for standard models

    Vertex AI AutoML Prediction:
    - $0.30/1000 predictions

    Cloud Storage:
    - $0.020/GB/month (standard)

    Args:
        audio_duration_seconds: Duration of audio in seconds.
        config: Configuration dictionary with cost overrides.
        enable_diarization: Whether diarization is enabled.
        enable_situation_detection: Whether situation detection is enabled.

    Returns:
        Dictionary with cost breakdown.
    """
    if config is None:
        config = {}

    cost_config = config.get("cost", {})

    # Speech-to-Text cost
    blocks_15s = math.ceil(audio_duration_seconds / 15)

    if enable_diarization:
        speech_rate = cost_config.get("speech_enhanced_per_15s", 0.009)
    else:
        speech_rate = cost_config.get("speech_standard_per_15s", 0.006)

    speech_cost = blocks_15s * speech_rate

    # Vertex AI cost (30s segments)
    vertex_cost = 0.0
    if enable_situation_detection:
        segment_duration = config.get("processing", {}).get("segment_duration", 30)
        num_predictions = math.ceil(audio_duration_seconds / segment_duration)
        vertex_rate = cost_config.get("vertex_per_1000_predictions", 0.30)
        vertex_cost = num_predictions * vertex_rate / 1000

    # Storage cost (negligible for small files)
    storage_cost = 0.001

    total_cost = speech_cost + vertex_cost + storage_cost

    return {
        "speech_to_text": round(speech_cost, 4),
        "situation_classification": round(vertex_cost, 4),
        "storage": round(storage_cost, 4),
        "total": round(total_cost, 4),
    }


def format_timestamp(seconds: float) -> str:
    """
    Format seconds as HH:MM:SS.mmm timestamp.

    Args:
        seconds: Time in seconds.

    Returns:
        Formatted timestamp string.
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def parse_gcs_uri(gcs_uri: str) -> tuple[str, str]:
    """
    Parse a GCS URI into bucket and blob path.

    Args:
        gcs_uri: GCS URI (gs://bucket/path/to/file).

    Returns:
        Tuple of (bucket_name, blob_path).

    Raises:
        ValueError: If URI is not a valid GCS URI.
    """
    if not gcs_uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI: {gcs_uri}")

    uri_without_prefix = gcs_uri[5:]
    parts = uri_without_prefix.split("/", 1)

    if len(parts) != 2:
        raise ValueError(f"Invalid GCS URI: {gcs_uri}")

    return parts[0], parts[1]


def get_file_extension(file_path: str) -> str:
    """
    Get the file extension from a file path or GCS URI.

    Args:
        file_path: Local file path or GCS URI.

    Returns:
        File extension without the dot (lowercase).
    """
    if file_path.startswith("gs://"):
        file_path = file_path.split("/")[-1]

    return Path(file_path).suffix.lower().lstrip(".")


def is_supported_format(file_path: str, supported_formats: list[str] | None = None) -> bool:
    """
    Check if a file format is supported.

    Args:
        file_path: Local file path or GCS URI.
        supported_formats: List of supported formats. If None, uses defaults.

    Returns:
        True if format is supported.
    """
    if supported_formats is None:
        supported_formats = ["wav", "mp3", "m4a", "flac", "opus", "ogg", "aac"]

    extension = get_file_extension(file_path)
    return extension in supported_formats


def validate_audio_duration(
    duration_seconds: float,
    max_duration_minutes: float = 480,
) -> None:
    """
    Validate that audio duration is within limits.

    Args:
        duration_seconds: Duration of audio in seconds.
        max_duration_minutes: Maximum allowed duration in minutes.

    Raises:
        ValueError: If duration exceeds maximum.
    """
    max_seconds = max_duration_minutes * 60

    if duration_seconds > max_seconds:
        raise ValueError(
            f"Audio duration ({duration_seconds / 60:.1f} minutes) exceeds "
            f"maximum allowed duration ({max_duration_minutes} minutes)"
        )


def get_situation_color(situation: str) -> str:
    """
    Get a color for a situation label (for CLI output).

    Args:
        situation: Situation label.

    Returns:
        Color name for rich library.
    """
    colors = {
        "airplane": "blue",
        "car": "yellow",
        "walking": "green",
        "meeting": "magenta",
        "office": "cyan",
        "outdoor": "bright_green",
        "restaurant": "red",
        "quiet": "white",
    }
    return colors.get(situation.lower(), "white")
