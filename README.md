# Media Intelligence Pipeline

A containerized audio and video processing pipeline for extracting structured intelligence from recorded media. Designed for air-gapped, CPU-only deployment in enterprise environments.

## Features

- [x] **Speech-to-Text Transcription** - Using faster-whisper (4x faster than OpenAI Whisper)
- [x] **Speaker Diarization** - Identify and label speakers using pyannote-audio 3.1
- [x] **Situation Detection** - Classify audio scenes (airplane, car, meeting, office, outdoor, etc.)
- [x] **Batch Processing** - Process individual files or entire directories
- [x] **Multiple Output Formats** - JSON (structured), TXT (human-readable), situation reports
- [x] **CPU-Only Deployment** - No GPU required (air-gapped deployment ready)
- [x] **Containerized** - Podman/Docker with resource limits

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/stharrold/media-intelligence.git
cd media-intelligence

# 2. Build the container
./build.sh

# 3. Add your HuggingFace token to .env (optional, for speaker diarization)
echo "HUGGINGFACE_TOKEN=hf_your_token" >> .env

# 4. Place audio files in data/input/
cp your_audio.wav data/input/

# 5. Process!
./run.sh your_audio.wav
```

Results will be saved to `data/output/`.

## Performance Benchmarks

| Model | Audio Duration | Processing Time | RTF | Memory |
|-------|---------------|-----------------|-----|--------|
| tiny.en | 60s | ~8s | 0.13 | ~2GB |
| base.en | 60s | ~15s | 0.25 | ~4GB |
| small.en | 60s | ~30s | 0.50 | ~6GB |
| medium.en | 60s | ~60s | 1.00 | ~8GB |

*RTF = Real-Time Factor (lower is faster)*
*Benchmarks on 4-core CPU*

## Architecture

```
Input Audio (WAV/MP3/M4A/FLAC/OGG/OPUS)
    |
    +-> Preprocessing (librosa)
    |   - Load & convert to 16kHz mono
    |   - Normalize audio
    |
    +----------+---------------+-----------+
    |          |               |           |
    v          v               v           v
faster-    pyannote       AST Audio    (Future)
whisper    diarization    Classifier   Video
base.en    3.1            AudioSet     Processing
int8
    |          |               |           |
    +----------+---------------+-----------+
               |
               v
    Merge & Attribution Engine
               |
               v
    Output Generation
    - JSON (complete structured data)
    - TXT (human-readable transcript with speakers)
    - Situations (scene classification report)
```

## Usage Examples

### Process a Single File

```bash
# Basic usage
./run.sh meeting.wav

# Specify model
./run.sh meeting.wav -m small.en

# Disable diarization (faster)
./run.sh meeting.wav --no-diarization

# Auto-detect language
./run.sh foreign_audio.wav -l auto
```

### Process Multiple Files

```bash
# Process all files in data/input/
./run.sh .

# Or specify a subdirectory
cp *.wav data/input/meetings/
./run.sh meetings/
```

### Advanced Options

```bash
# Full options
./run.sh recording.wav \
    -m base.en \           # Model: tiny, base, small, medium
    -l en \                # Language code (or 'auto')
    --no-diarization \     # Disable speaker identification
    --no-situation \       # Disable scene classification
    -v                     # Verbose output
```

### Python API

```python
from src.process_audio import AudioProcessor

# Initialize processor
processor = AudioProcessor(
    whisper_model="base.en",
    device="cpu",
    compute_type="int8",
    hf_token="hf_your_token"  # Optional
)

# Process a file
result = processor.process_file(
    "recording.wav",
    output_dir="output/",
    language="en"
)

# Access results
print(f"Duration: {result.duration:.2f}s")
print(f"Speakers: {result.metadata['num_speakers']}")
print(f"Situation: {result.overall_situation}")

for segment in result.transcript_segments:
    print(f"[{segment.start:.2f}s] {segment.speaker}: {segment.text}")
```

## Output Formats

### JSON Output (`*_results.json`)

```json
{
  "file_path": "/data/input/meeting.wav",
  "duration": 180.5,
  "overall_situation": "meeting",
  "processing_time": 36.2,
  "metadata": {
    "language": "en",
    "language_probability": 0.98,
    "num_speakers": 3
  },
  "transcript": [
    {
      "start": 0.0,
      "end": 3.5,
      "text": "Good morning everyone, let's begin.",
      "speaker": "SPEAKER_00",
      "confidence": 0.87
    }
  ],
  "situations": [
    {
      "start": 0.0,
      "end": 30.0,
      "situation": "meeting",
      "confidence": 0.92,
      "top_predictions": [
        {"label": "Speech", "confidence": 0.924},
        {"label": "Conversation", "confidence": 0.856}
      ]
    }
  ]
}
```

### Text Transcript (`*_transcript.txt`)

```
Transcript: meeting.wav
Duration: 180.50s
Overall Situation: meeting
================================================================================

[0.00s - 3.50s] SPEAKER_00: Good morning everyone, let's begin.
[3.50s - 8.20s] SPEAKER_01: Thanks for joining. First item on the agenda...
```

### Situation Report (`*_situations.txt`)

```
Situation Analysis: meeting.wav
================================================================================

[0.0s - 30.0s] MEETING (confidence: 0.924)
  Top predictions:
    - Speech: 0.924
    - Conversation: 0.856
    - Inside, public space: 0.732
```

## Situation Categories

The classifier detects these scene types:

| Situation | Example Sounds |
|-----------|---------------|
| airplane | Aircraft noise, jet engine, cabin sounds |
| car | Engine, traffic, road noise |
| walking | Footsteps, running, gait sounds |
| meeting | Speech, conversation, crowd chatter |
| office | Keyboard typing, mouse clicks, printer |
| outdoor | Wind, rain, birds, urban/rural ambient |
| restaurant | Dishes, cutlery, cooking sounds |
| quiet | Silence, ambient room tone |

## Configuration

### Environment Variables (`.env`)

```bash
# HuggingFace token for speaker diarization
HUGGINGFACE_TOKEN=hf_your_token_here

# Processing settings
OMP_NUM_THREADS=4
MKL_NUM_THREADS=4

# Default model
DEFAULT_MODEL=base.en
```

### Advanced Configuration (`config.yaml`)

See `config.example.yaml` for all available options including:
- Model selection and parameters
- Diarization settings
- Output format preferences
- Resource limits

### Configuration Precedence

Settings are applied in the following order (later sources override earlier ones):

1. **Default values** - Built-in defaults in the code
2. **config.yaml** - Advanced configuration file (if present)
3. **Environment variables (.env)** - Loaded via python-dotenv
4. **Command-line arguments** - Highest priority, always override other settings

For example, if `DEFAULT_MODEL=base.en` is set in `.env` but you run `./run.sh audio.wav -m tiny.en`, the `tiny.en` model will be used.

## Troubleshooting

### "HuggingFace token required for speaker diarization"

1. Create account at https://huggingface.co
2. Accept terms at https://huggingface.co/pyannote/speaker-diarization-3.1
3. Generate token at https://huggingface.co/settings/tokens
4. Add to `.env`: `HUGGINGFACE_TOKEN=hf_your_token`

Alternatively, use `--no-diarization` to skip speaker identification.

### Out of Memory

- Use a smaller model: `./run.sh audio.wav -m tiny.en`
- Increase container memory limit in `compose.yaml`
- Process shorter audio files

### Slow Processing

- Use INT8 quantization (default)
- Use `.en` models for English audio
- Reduce beam size in config
- Use smaller model

### Unsupported Audio Format

Convert to WAV:
```bash
ffmpeg -i input.mp4 -ac 1 -ar 16000 output.wav
```

### Container Build Fails

- Ensure podman/docker is installed
- Check available disk space (>5GB needed)
- Try building with `--no-cache`: `podman build --no-cache -t media-intelligence .`

## Testing

```bash
# Run validation tests
./test.sh

# Run unit tests (requires pytest)
pytest tests/ -v

# Test with sample file
./run.sh sample.wav -m tiny.en --no-diarization
```

## Directory Structure

```
media-intelligence/
├── LICENSE                     # Apache 2.0
├── README.md                   # This file
├── QUICKSTART.md              # 5-minute guide
├── IMPLEMENTATION_SUMMARY.md  # Technical design
├── Dockerfile                 # Container build
├── compose.yaml               # Podman/Docker Compose
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
├── config.example.yaml       # Advanced config
├── build.sh                  # Build script
├── run.sh                    # Run script
├── test.sh                   # Test script
├── src/
│   ├── __init__.py
│   ├── process_audio.py      # Main pipeline
│   ├── transcription.py      # Whisper wrapper
│   ├── diarization.py        # Pyannote wrapper
│   ├── situation.py          # AST classifier
│   └── utils.py              # Utilities
├── tests/
│   ├── test_transcription.py
│   ├── test_diarization.py
│   └── test_situation.py
├── data/
│   ├── input/                # Input audio files
│   └── output/               # Processing results
├── cache/                    # Model cache
└── models/                   # Optional model storage
```

## Dependencies

### Core Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| faster-whisper | 1.0.3 | Speech-to-text |
| pyannote.audio | 3.1.1 | Speaker diarization |
| transformers | 4.36.2 | AST classifier |
| torch | 2.1.2 | ML backend |
| librosa | 0.10.1 | Audio processing |

### System Requirements

- Python 3.11+
- 4GB+ RAM (8GB recommended)
- 4+ CPU cores
- 5GB+ disk space (for models)

## License

Copyright (c) 2025 Harrold Holdings GmbH

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

## References

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - CTranslate2 Whisper implementation
- [pyannote-audio](https://github.com/pyannote/pyannote-audio) - Speaker diarization toolkit
- [AST](https://github.com/YuanGongND/ast) - Audio Spectrogram Transformer
- [Whisper](https://github.com/openai/whisper) - OpenAI speech recognition

## Contributing

Contributions welcome! Please read the contributing guidelines and submit pull requests.

## Roadmap

- [ ] Video processing (scene detection, object recognition)
- [ ] Real-time streaming mode
- [ ] Custom model fine-tuning
- [ ] Multi-language support improvements
- [ ] GPU acceleration option
