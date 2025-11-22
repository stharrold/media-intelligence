# Quick Start Guide

Get started with Media Intelligence in 5 minutes.

## Prerequisites

- **Container Runtime**: Podman (recommended) or Docker
- **Memory**: 4GB+ RAM available
- **Disk**: 5GB+ free space for models

## Step 1: Clone and Build

```bash
git clone https://github.com/stharrold/media-intelligence.git
cd media-intelligence
./build.sh
```

Build takes 3-5 minutes on first run (downloads models).

## Step 2: Configure HuggingFace Token (Optional)

Speaker diarization requires a HuggingFace token.

### Get Your Token

1. Create account: https://huggingface.co/join
2. Accept pyannote terms: https://huggingface.co/pyannote/speaker-diarization-3.1
3. Generate token: https://huggingface.co/settings/tokens (select "Read" access)

### Add to Configuration

```bash
# Edit .env file
echo "HUGGINGFACE_TOKEN=hf_your_token_here" >> .env
```

**Note**: Skip this step if you don't need speaker identification.

## Step 3: Add Audio Files

Place your audio files in the `data/input/` directory:

```bash
cp ~/my_recording.wav data/input/
```

Supported formats: WAV, MP3, M4A, FLAC, OGG, OPUS

## Step 4: Process Audio

```bash
./run.sh my_recording.wav
```

## Step 5: View Results

```bash
# Check output directory
ls data/output/

# View transcript
cat data/output/my_recording_transcript.txt

# View JSON results
cat data/output/my_recording_results.json
```

## Example Commands

```bash
# Basic transcription
./run.sh meeting.wav

# Faster processing (smaller model)
./run.sh meeting.wav -m tiny.en

# Without speaker diarization
./run.sh meeting.wav --no-diarization

# Auto-detect language
./run.sh foreign_audio.wav -l auto

# Process all files in directory
./run.sh .

# Verbose output
./run.sh meeting.wav -v
```

## Sample Output

### Terminal Output

```
Media Intelligence Pipeline
Audio transcription, diarization, and situation detection

Processing: meeting.wav
Duration: 45.20s

Step 1/4: Transcribing audio...
  Found 12 segments

Step 2/4: Identifying speakers...
  Found 2 speakers

Step 3/4: Detecting situations...
  Overall situation: meeting

Step 4/4: Saving outputs...
  JSON: data/output/meeting_results.json
  Transcript: data/output/meeting_transcript.txt
  Situations: data/output/meeting_situations.txt

✓ Processing complete

╔═══════════════════╤══════════╗
║ Metric            │ Value    ║
╟───────────────────┼──────────╢
║ Duration          │ 45.20s   ║
║ Processing Time   │ 12.30s   ║
║ RTF               │ 0.272    ║
║ Segments          │ 12       ║
║ Speakers          │ 2        ║
║ Overall Situation │ meeting  ║
╚═══════════════════╧══════════╝
```

### Transcript Output

```
Transcript: meeting.wav
Duration: 45.20s
Overall Situation: meeting
================================================================================

[0.00s - 2.50s] SPEAKER_00: Hello everyone, thanks for joining.
[2.80s - 6.20s] SPEAKER_01: Thanks for having us. Let's get started.
[6.50s - 12.00s] SPEAKER_00: First, I want to discuss the quarterly results.
```

## Common Issues

### "No HuggingFace token"

```
⚠ Speaker diarization disabled: No HuggingFace token provided.
```

**Solution**: Add token to `.env` or use `--no-diarization`

### "Input not found"

```
Error: Input not found: data/input/file.wav
```

**Solution**: Ensure file is in `data/input/` directory

### Out of Memory

**Solution**: Use a smaller model:
```bash
./run.sh file.wav -m tiny.en
```

### Slow Processing

**Solutions**:
- Use `.en` models for English audio (e.g., `base.en` instead of `base`)
- Use smaller model (`tiny.en` or `base.en`)
- Disable diarization: `--no-diarization`

## Model Comparison

| Model | Speed | Quality | Memory | Best For |
|-------|-------|---------|--------|----------|
| tiny.en | Fastest | Good | ~2GB | Quick previews, testing |
| base.en | Fast | Better | ~4GB | **Recommended default** |
| small.en | Medium | High | ~6GB | Accuracy-focused |
| medium.en | Slow | Highest | ~8GB | Critical accuracy needs |

## Next Steps

- Read the full [README.md](README.md) for advanced usage
- Customize settings in `config.example.yaml`
- See [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for technical details

## Getting Help

- Check troubleshooting in [README.md](README.md#troubleshooting)
- Run `./run.sh --help` for CLI options
- Run `./test.sh` to validate your installation
