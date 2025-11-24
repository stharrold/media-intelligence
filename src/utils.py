# Copyright (c) 2025 Harrold Holdings GmbH
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license information.

"""
Shared utilities for the Media Intelligence Pipeline.

Provides common functions for audio loading, file handling, logging,
and output generation.
"""

import logging
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
import json

import numpy as np
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel

# Initialize rich console
console = Console()

# Supported audio formats
SUPPORTED_FORMATS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".opus"}


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """
    Configure logging for the pipeline.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional path to log file

    Returns:
        Configured logger instance
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Configure root logger
    logger = logging.getLogger("media_intelligence")
    logger.setLevel(log_level)

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler (only for DEBUG/INFO)
    if log_level <= logging.INFO:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def load_audio(
    file_path: Union[str, Path],
    target_sr: int = 16000,
    mono: bool = True
) -> Tuple[np.ndarray, int]:
    """
    Load and preprocess audio file.

    Args:
        file_path: Path to audio file
        target_sr: Target sample rate (default 16kHz for Whisper)
        mono: Convert to mono (default True)

    Returns:
        Tuple of (audio_array, sample_rate)

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format not supported
    """
    import librosa

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    if file_path.suffix.lower() not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported audio format: {file_path.suffix}. "
            f"Supported formats: {', '.join(SUPPORTED_FORMATS)}"
        )

    # Load audio with librosa
    audio, sr = librosa.load(
        str(file_path),
        sr=target_sr,
        mono=mono
    )

    return audio, sr


def get_audio_duration(file_path: Union[str, Path]) -> float:
    """
    Get duration of audio file in seconds.

    Args:
        file_path: Path to audio file

    Returns:
        Duration in seconds
    """
    import librosa

    duration = librosa.get_duration(path=str(file_path))
    return duration


def validate_audio_file(file_path: Union[str, Path]) -> bool:
    """
    Validate that a file is a supported audio format.

    Args:
        file_path: Path to file

    Returns:
        True if valid audio file, False otherwise
    """
    file_path = Path(file_path)
    return (
        file_path.exists() and
        file_path.is_file() and
        file_path.suffix.lower() in SUPPORTED_FORMATS
    )


def find_audio_files(directory: Union[str, Path]) -> List[Path]:
    """
    Find all audio files in a directory.

    Args:
        directory: Directory to search

    Returns:
        List of audio file paths
    """
    directory = Path(directory)
    audio_files = []

    for format_ext in SUPPORTED_FORMATS:
        audio_files.extend(directory.glob(f"*{format_ext}"))
        audio_files.extend(directory.glob(f"*{format_ext.upper()}"))

    return sorted(audio_files)


def sanitize_path(path: Union[str, Path]) -> Path:
    """
    Sanitize and validate a file path.

    Prevents path traversal attacks and ensures path is within expected bounds.

    Args:
        path: Path to sanitize

    Returns:
        Sanitized Path object

    Raises:
        ValueError: If path is invalid or attempts traversal
    """
    path = Path(path).resolve()

    # Check for path traversal attempts
    if ".." in str(path):
        raise ValueError(f"Invalid path (traversal detected): {path}")

    return path


@dataclass
class TranscriptSegment:
    """Represents a segment of transcribed audio."""
    start: float
    end: float
    text: str
    speaker: Optional[str] = None
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SituationSegment:
    """Represents a classified situation/scene segment."""
    start: float
    end: float
    situation: str
    confidence: float
    top_predictions: List[Dict[str, float]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ProcessingResult:
    """Complete processing result for an audio file."""
    file_path: str
    duration: float
    transcript_segments: List[TranscriptSegment]
    situation_segments: List[SituationSegment]
    overall_situation: str
    processing_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "file_path": self.file_path,
            "duration": self.duration,
            "overall_situation": self.overall_situation,
            "processing_time": self.processing_time,
            "metadata": self.metadata,
            "transcript": [seg.to_dict() for seg in self.transcript_segments],
            "situations": [seg.to_dict() for seg in self.situation_segments],
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def save_json_output(
    result: ProcessingResult,
    output_path: Union[str, Path]
) -> Path:
    """
    Save processing result as JSON.

    Args:
        result: ProcessingResult to save
        output_path: Output file path

    Returns:
        Path to saved file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result.to_json())

    return output_path


def save_transcript_output(
    result: ProcessingResult,
    output_path: Union[str, Path]
) -> Path:
    """
    Save human-readable transcript.

    Args:
        result: ProcessingResult to save
        output_path: Output file path

    Returns:
        Path to saved file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    filename = Path(result.file_path).name

    lines = [
        f"Transcript: {filename}",
        f"Duration: {result.duration:.2f}s",
        f"Overall Situation: {result.overall_situation}",
        "=" * 80,
        "",
    ]

    for segment in result.transcript_segments:
        speaker = segment.speaker or "UNKNOWN"
        lines.append(
            f"[{segment.start:.2f}s - {segment.end:.2f}s] {speaker}: {segment.text}"
        )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return output_path


def save_situations_output(
    result: ProcessingResult,
    output_path: Union[str, Path]
) -> Path:
    """
    Save situation analysis report.

    Args:
        result: ProcessingResult to save
        output_path: Output file path

    Returns:
        Path to saved file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    filename = Path(result.file_path).name

    lines = [
        f"Situation Analysis: {filename}",
        "=" * 80,
        "",
    ]

    for segment in result.situation_segments:
        lines.append(
            f"[{segment.start:.1f}s - {segment.end:.1f}s] "
            f"{segment.situation.upper()} (confidence: {segment.confidence:.3f})"
        )
        lines.append("  Top predictions:")
        for pred in segment.top_predictions[:3]:
            lines.append(f"    - {pred['label']}: {pred['confidence']:.3f}")
        lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return output_path


def print_step(step: int, total: int, message: str) -> None:
    """Print a processing step with formatting."""
    console.print(f"[bold blue]Step {step}/{total}: {message}[/bold blue]")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[bold green]✓ {message}[/bold green]")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[bold red]✗ {message}[/bold red]")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[bold yellow]⚠ {message}[/bold yellow]")


def print_results_table(result: ProcessingResult) -> None:
    """Print a summary table of processing results."""
    table = Table(title="Processing Results", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="dim")
    table.add_column("Value")

    # Calculate RTF (Real-Time Factor)
    rtf = result.processing_time / result.duration if result.duration > 0 else 0

    table.add_row("Duration", f"{result.duration:.2f}s")
    table.add_row("Processing Time", f"{result.processing_time:.2f}s")
    table.add_row("RTF", f"{rtf:.3f}")
    table.add_row("Segments", str(len(result.transcript_segments)))
    table.add_row(
        "Speakers",
        str(result.metadata.get("num_speakers", "N/A"))
    )
    table.add_row("Overall Situation", result.overall_situation)

    console.print(table)


def create_progress() -> Progress:
    """Create a rich progress bar."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    )


def format_timestamp(seconds: float) -> str:
    """
    Format seconds as HH:MM:SS.mmm timestamp.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def get_file_info(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Get metadata about an audio file.

    Args:
        file_path: Path to audio file

    Returns:
        Dictionary with file information
    """
    file_path = Path(file_path)
    stat = file_path.stat()

    return {
        "name": file_path.name,
        "path": str(file_path.absolute()),
        "size_bytes": stat.st_size,
        "size_mb": stat.st_size / (1024 * 1024),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "format": file_path.suffix.lower(),
    }
