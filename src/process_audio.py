#!/usr/bin/env python3
# Copyright (c) 2025 Harrold Holdings GmbH
# Licensed under the Apache License, Version 2.0
# See LICENSE file in the project root for full license information.

"""
Media Intelligence Pipeline - Main Audio Processing Module

Provides end-to-end audio processing including:
- Speech-to-text transcription (faster-whisper)
- Speaker diarization (pyannote-audio)
- Situation/scene classification (AST)

Usage:
    python -m src.process_audio input.wav -o output/
    python -m src.process_audio input_directory/ -o output/
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from .diarization import DiarizationConfig, Diarizer
from .situation import SituationClassifier, SituationConfig
from .transcription import Transcriber, WhisperConfig
from .utils import (
    SUPPORTED_FORMATS,
    ProcessingResult,
    console,
    find_audio_files,
    load_audio,
    print_error,
    print_results_table,
    print_step,
    print_success,
    print_warning,
    sanitize_path,
    save_json_output,
    save_situations_output,
    save_transcript_output,
    setup_logging,
    validate_memory_for_file,
)

# Load environment variables
load_dotenv()

logger = logging.getLogger("media_intelligence")


class AudioProcessor:
    """
    Main audio processing pipeline.

    Orchestrates transcription, diarization, and situation classification
    to produce comprehensive audio analysis.

    Attributes:
        transcriber: Whisper transcription instance
        diarizer: Pyannote diarization instance (optional)
        classifier: AST situation classifier instance
        config: Processing configuration
    """

    def __init__(
        self,
        whisper_model: str = "base.en",
        device: str = "cpu",
        compute_type: str = "int8",
        num_workers: int = 4,
        hf_token: str | None = None,
        enable_diarization: bool = True,
        enable_situation: bool = True,
        timeout: int | None = None,
    ):
        """
        Initialize the audio processor.

        Args:
            whisper_model: Whisper model size (tiny, base, small, medium, etc.)
            device: Processing device (cpu or cuda)
            compute_type: Compute type (int8, float16, float32)
            num_workers: Number of CPU workers
            hf_token: HuggingFace token for pyannote (optional)
            enable_diarization: Enable speaker diarization
            enable_situation: Enable situation classification
            timeout: Processing timeout in seconds (None for no limit)
        """
        self.timeout = timeout
        self.device = device
        self.num_workers = num_workers
        self.hf_token = hf_token or os.environ.get("HUGGINGFACE_TOKEN")
        self.enable_diarization = enable_diarization
        self.whisper_model = whisper_model
        self.enable_situation = enable_situation

        # Set thread limits
        os.environ["OMP_NUM_THREADS"] = str(num_workers)
        os.environ["MKL_NUM_THREADS"] = str(num_workers)

        # Initialize transcriber
        logger.info("Initializing transcription model...")
        whisper_config = WhisperConfig(
            model_size=whisper_model,
            device=device,
            compute_type=compute_type,
        )
        self.transcriber = Transcriber(whisper_config)

        # Initialize diarizer (optional)
        self.diarizer = None
        if enable_diarization and self.hf_token:
            logger.info("Initializing diarization model...")
            try:
                diarization_config = DiarizationConfig(device=device)
                self.diarizer = Diarizer(diarization_config, self.hf_token)
            except Exception as e:
                logger.warning(f"Failed to initialize diarization: {e}")
                print_warning(f"Diarization disabled: {e}")
        elif enable_diarization and not self.hf_token:
            print_warning("Speaker diarization disabled: No HuggingFace token provided.\n" "Set HUGGINGFACE_TOKEN environment variable to enable.")

        # Initialize situation classifier (optional)
        self.classifier = None
        if enable_situation:
            logger.info("Initializing situation classifier...")
            try:
                situation_config = SituationConfig(device=device)
                self.classifier = SituationClassifier(situation_config)
            except Exception as e:
                logger.warning(f"Failed to initialize situation classifier: {e}")
                print_warning(f"Situation classification disabled: {e}")

    def process_file(
        self,
        audio_path: str,
        output_dir: str,
        language: str = "en",
        beam_size: int = 5,
    ) -> ProcessingResult:
        """
        Process a single audio file.

        Args:
            audio_path: Path to audio file
            output_dir: Directory for output files
            language: Language code for transcription
            beam_size: Beam size for Whisper decoding

        Returns:
            ProcessingResult with complete analysis

        Raises:
            FileNotFoundError: If audio file not found
            ValueError: If audio format not supported
        """
        # Sanitize paths to prevent path traversal
        audio_path = sanitize_path(audio_path)
        output_dir = sanitize_path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if audio_path.suffix.lower() not in SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {audio_path.suffix}. " f"Supported: {', '.join(SUPPORTED_FORMATS)}")

        # Validate memory requirements
        mem_valid, mem_msg = validate_memory_for_file(audio_path, self.whisper_model)
        if not mem_valid:
            raise MemoryError(mem_msg)
        if mem_msg:  # Warning message
            print_warning(mem_msg)

        start_time = time.time()
        filename = audio_path.stem

        # Helper function to check timeout
        def check_timeout():
            if self.timeout and (time.time() - start_time) > self.timeout:
                raise TimeoutError(f"Processing timeout after {self.timeout}s. " f"Consider using a smaller model or shorter audio files.")

        console.print(f"\nProcessing: [bold]{audio_path.name}[/bold]")

        # Load audio
        audio, sr = load_audio(audio_path)
        duration = len(audio) / sr
        console.print(f"Duration: {duration:.2f}s")

        # Step 1: Transcription
        total_steps = 2 + (1 if self.diarizer else 0) + (1 if self.classifier else 0)
        current_step = 1

        print_step(current_step, total_steps, "Transcribing audio...")
        transcript_segments, trans_metadata = self.transcriber.transcribe(audio, sr, language=language, beam_size=beam_size)
        console.print(f"  Found {len(transcript_segments)} segments")
        check_timeout()

        # Step 2: Diarization (optional)
        speaker_segments = []
        num_speakers = 0
        if self.diarizer:
            current_step += 1
            print_step(current_step, total_steps, "Identifying speakers...")
            try:
                from .diarization import assign_speakers_to_segments as assign_speakers

                speaker_segments = self.diarizer.diarize(audio, sr)
                transcript_segments = assign_speakers(transcript_segments, speaker_segments)
                num_speakers = len(set(s.speaker for s in speaker_segments))
                console.print(f"  Found {num_speakers} speakers")
                check_timeout()
            except Exception as e:
                logger.error(f"Diarization failed: {e}")
                print_warning(f"Diarization failed: {e}")

        # Step 3: Situation classification (optional)
        situation_segments = []
        overall_situation = "unknown"
        if self.classifier:
            current_step += 1
            print_step(current_step, total_steps, "Detecting situations...")
            try:
                situation_segments, overall_situation = self.classifier.classify_audio(audio, sr)
                console.print(f"  Overall situation: {overall_situation}")
                check_timeout()
            except Exception as e:
                logger.error(f"Situation classification failed: {e}")
                print_warning(f"Situation classification failed: {e}")

        # Calculate processing time
        processing_time = time.time() - start_time

        # Build result
        result = ProcessingResult(
            file_path=str(audio_path.absolute()),
            duration=duration,
            transcript_segments=transcript_segments,
            situation_segments=situation_segments,
            overall_situation=overall_situation,
            processing_time=processing_time,
            metadata={
                "language": trans_metadata.get("language", language),
                "language_probability": trans_metadata.get("language_probability", 1.0),
                "num_speakers": num_speakers,
                "model": self.transcriber.config.model_size,
                "compute_type": self.transcriber.config.compute_type,
            },
        )

        # Step N: Save outputs
        current_step += 1
        print_step(current_step, total_steps, "Saving outputs...")

        # Save JSON
        json_path = output_dir / f"{filename}_results.json"
        save_json_output(result, json_path)
        console.print(f"  JSON: {json_path}")

        # Save transcript
        txt_path = output_dir / f"{filename}_transcript.txt"
        save_transcript_output(result, txt_path)
        console.print(f"  Transcript: {txt_path}")

        # Save situations
        if situation_segments:
            sit_path = output_dir / f"{filename}_situations.txt"
            save_situations_output(result, sit_path)
            console.print(f"  Situations: {sit_path}")

        print_success("Processing complete")
        print_results_table(result)

        return result

    def process_directory(
        self,
        input_dir: str,
        output_dir: str,
        language: str = "en",
        beam_size: int = 5,
    ) -> list[ProcessingResult]:
        """
        Process all audio files in a directory.

        Args:
            input_dir: Directory containing audio files
            output_dir: Directory for output files
            language: Language code for transcription
            beam_size: Beam size for Whisper decoding

        Returns:
            List of ProcessingResult objects
        """
        input_dir = Path(input_dir)
        audio_files = find_audio_files(input_dir)

        if not audio_files:
            print_warning(f"No audio files found in {input_dir}")
            return []

        console.print(f"\nFound {len(audio_files)} audio files")

        results = []
        for i, audio_path in enumerate(audio_files, 1):
            console.print(f"\n[bold]File {i}/{len(audio_files)}[/bold]")
            try:
                result = self.process_file(str(audio_path), output_dir, language, beam_size)
                results.append(result)
            except Exception as e:
                print_error(f"Failed to process {audio_path.name}: {e}")
                logger.exception(f"Failed to process {audio_path}")

        # Print summary
        console.print("\n[bold]Batch Processing Complete[/bold]")
        console.print(f"Processed: {len(results)}/{len(audio_files)} files")

        return results


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Media Intelligence Pipeline - Audio Processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Process single file:
    python -m src.process_audio recording.wav -o output/

  Process directory:
    python -m src.process_audio recordings/ -o output/

  Use smaller model for faster processing:
    python -m src.process_audio recording.wav -m tiny.en

  Disable diarization:
    python -m src.process_audio recording.wav --no-diarization
        """,
    )

    parser.add_argument("input", help="Input audio file or directory")
    parser.add_argument("-o", "--output", default="/data/output", help="Output directory (default: /data/output)")
    parser.add_argument(
        "-m",
        "--model",
        default="base.en",
        choices=["tiny", "tiny.en", "base", "base.en", "small", "small.en", "medium", "medium.en"],
        help="Whisper model size (default: base.en)",
    )
    parser.add_argument("-d", "--device", default="cpu", choices=["cpu", "cuda"], help="Processing device (default: cpu)")
    parser.add_argument("-c", "--compute-type", default="int8", choices=["int8", "float16", "float32"], help="Compute type (default: int8)")
    parser.add_argument("--hf-token", help="HuggingFace token for pyannote (or set HUGGINGFACE_TOKEN env var)")
    parser.add_argument("-w", "--workers", type=int, default=4, help="Number of CPU workers (default: 4)")
    parser.add_argument("-l", "--language", default="en", help="Language code (default: en, use 'auto' for detection)")
    parser.add_argument("-b", "--beam-size", type=int, default=5, help="Beam size for decoding (default: 5)")
    parser.add_argument("--no-diarization", action="store_true", help="Disable speaker diarization")
    parser.add_argument("--no-situation", action="store_true", help="Disable situation classification")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--log-file", help="Write logs to file")
    parser.add_argument("--timeout", type=int, default=None, help="Processing timeout in seconds (default: no limit)")

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(log_level, args.log_file)

    # Print banner
    console.print("[bold blue]Media Intelligence Pipeline[/bold blue]")
    console.print("Audio transcription, diarization, and situation detection\n")

    try:
        # Initialize processor
        processor = AudioProcessor(
            whisper_model=args.model,
            device=args.device,
            compute_type=args.compute_type,
            num_workers=args.workers,
            hf_token=args.hf_token,
            enable_diarization=not args.no_diarization,
            enable_situation=not args.no_situation,
            timeout=args.timeout,
        )

        input_path = Path(args.input)

        if input_path.is_file():
            # Process single file
            processor.process_file(str(input_path), args.output, args.language, args.beam_size)
        elif input_path.is_dir():
            # Process directory
            processor.process_directory(str(input_path), args.output, args.language, args.beam_size)
        else:
            print_error(f"Input not found: {args.input}")
            return 1

        return 0

    except KeyboardInterrupt:
        console.print("\n[yellow]Processing interrupted by user[/yellow]")
        return 130
    except Exception as e:
        print_error(f"Processing failed: {e}")
        logger.exception("Processing failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
