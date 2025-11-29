---
type: claude-context
directory: .
purpose: Containerized audio processing system for extracting structured intelligence from recorded media
---

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Media Intelligence Pipeline: A containerized audio processing system for extracting structured intelligence from recorded media. Supports two deployment modes:

- **Local**: CPU-only containerized pipeline (air-gapped deployment ready)
- **GCP**: Cloud-native pipeline using Google Cloud managed services

**Key Principle**: All development uses `podman-compose run --rm dev uv run <command>`. One way to run everything.

## Essential Commands

```bash
# Build container (once)
podman-compose build

# Run any command (containerized - preferred)
podman-compose run --rm dev uv run <command>

# Common operations
podman-compose run --rm dev uv run pytest tests/                      # Run all tests
podman-compose run --rm dev uv run pytest tests/test_utils.py -v      # Single file
podman-compose run --rm dev uv run pytest tests/ -v -k "test_init"    # By name pattern
podman-compose run --rm dev uv run pytest tests/ --cov=src            # With coverage
podman-compose run --rm dev uv run ruff check .                       # Lint
podman-compose run --rm dev uv run ruff check --fix .                 # Auto-fix

# Build and run production container
./build.sh              # Build container image
./run.sh <audio.wav>    # Process audio file
./test.sh               # Run validation tests

# GCP Deployment
./deploy.sh --project PROJECT_ID --region REGION
./test_gcp.sh
```

## Workflow System

This repository uses a **skill-based workflow system** (v5.3) located in `.claude/skills/`.

### Slash Commands

| Command | Purpose |
|---------|---------|
| `/workflow:all` | Orchestrate full workflow with auto-detection |
| `/workflow:1_specify` | Create feature branch and specification |
| `/workflow:2_plan` | Generate detailed specs via speckit-author |
| `/workflow:3_tasks` | Validate task list from plan.md |
| `/workflow:4_implement` | Execute tasks + run quality gates |
| `/workflow:5_integrate` | Create PRs, cleanup worktree |
| `/workflow:6_release` | Create release (develop→main) |
| `/workflow:7_backmerge` | Sync release to develop and contrib |

### Branch Structure

```
main (production) ← develop (integration) ← contrib/stharrold (active) ← feature/*
```

**PR Flow**: feature → contrib → develop → main

### Quality Gates (5 gates, all must pass before PR)

```bash
podman-compose run --rm dev uv run python .claude/skills/quality-enforcer/scripts/run_quality_gates.py
```

| Gate | Description |
|------|-------------|
| 1. Coverage | ≥40% test coverage on `src/` (target: 80%, tracked in issue #9) |
| 2. Tests | All pytest tests pass |
| 3. Build | Build succeeds |
| 4. Linting | `ruff check .` clean |
| 5. AI Config Sync | CLAUDE.md → AGENTS.md synced |

### Pre-commit Hooks

```bash
# Install hooks (one-time)
uv run pre-commit install

# Run manually on all files
uv run pre-commit run --all-files
```

## Container Files

| File | Purpose |
|------|---------|
| `Containerfile` | Production container (multi-stage build) |
| `Containerfile.dev` | Development container with uv |
| `Containerfile.gcp` | Cloud Run optimized container |
| `podman-compose.yml` | Container orchestration |

## Architecture

### Local Pipeline (`src/`)
- `process_audio.py` - Main CLI and orchestration
- `transcription.py` - faster-whisper wrapper (Whisper INT8)
- `diarization.py` - pyannote-audio 3.1 speaker diarization
- `situation.py` - AST AudioSet classifier
- `key_manager.py` - Secure key storage (OS keyring for local, GCP Secret Manager for cloud)
- `utils.py` - Shared utilities, data classes

### GCP Pipeline (`src/`)
- `main.py` - Cloud Run/Functions entry points
- `audio_processor.py` - GCP orchestrator
- `speech_client.py` - Cloud Speech-to-Text V2
- `situation_classifier.py` - Vertex AI AutoML
- `storage_manager.py` - GCS operations
- `gcp_utils.py` - GCP-specific utilities

### Infrastructure (`terraform/`)
- `main.tf` - GCP resources (Cloud Run, GCS, Pub/Sub)
- `iam.tf` - Service accounts and permissions
- `variables.tf` / `outputs.tf` - Configuration

### Skills System (9 skills in `.claude/skills/`)

| Skill | Purpose |
|-------|---------|
| workflow-orchestrator | Main coordinator, templates |
| git-workflow-manager | Worktrees, PRs, semantic versioning |
| quality-enforcer | Quality gates (5 gates) |
| bmad-planner | Requirements + architecture |
| speckit-author | Specifications |
| tech-stack-adapter | Python/uv/Podman detection |
| workflow-utilities | Archive, directory structure |
| agentdb-state-manager | Workflow state tracking (DuckDB) |
| initialize-repository | Bootstrap new repos |

### AgentDB (Workflow State)

> **Note**: AgentDB requires DuckDB which may not be available in all container environments. These commands are optional for workflow state tracking.

```bash
# Initialize database (start of session)
podman-compose run --rm dev uv run python .claude/skills/agentdb-state-manager/scripts/init_database.py

# Record workflow transition
podman-compose run --rm dev uv run python .claude/skills/agentdb-state-manager/scripts/record_sync.py \
  --sync-type workflow_transition --pattern phase_1_specify

# Query current workflow state
podman-compose run --rm dev uv run python .claude/skills/agentdb-state-manager/scripts/query_workflow_state.py --format json
```

## Key Patterns

- **Dataclasses**: `TranscriptSegment`, `SituationSegment`, `ProcessingResult`
- **Lazy initialization**: GCP clients use `@property` pattern
- **Retry logic**: `tenacity` for transient errors
- **Context managers**: `download_temp_file()` for cleanup
- **Testing**: pytest-mock (`mocker` fixture) for clean mocking
- **Line length**: 170 chars (configured in pyproject.toml for ruff)

## Configuration

- `.env` - Environment variables (HuggingFace token, GCP settings)
- `config.yaml` - Advanced processing options
- Precedence: defaults → config.yaml → .env → CLI args

## Testing

Tests are in `tests/` with mocked external dependencies:
- `test_transcription.py`, `test_diarization.py`, `test_situation.py` - Local
- `test_speech_client.py`, `test_situation_classifier.py`, `test_storage_manager.py`, `test_audio_processor.py` - GCP
- `test_integration.py`, `test_gcp_integration.py` - End-to-end

```bash
# Run tests
podman-compose run --rm dev uv run pytest tests/
podman-compose run --rm dev uv run pytest tests/ --cov=src --cov-report=term
```

## AI Config Sync

CLAUDE.md automatically syncs to:
- `AGENTS.md` (cross-tool compatibility)
- `.github/copilot-instructions.md` (GitHub Copilot)
- `.agents/` (mirrored skills)

```bash
# Manual sync
podman-compose run --rm dev uv run python .claude/skills/workflow-utilities/scripts/sync_ai_config.py sync

# Verify sync
podman-compose run --rm dev uv run python .claude/skills/workflow-utilities/scripts/sync_ai_config.py verify
```

## Critical Guidelines

- **One way to run**: Always use `podman-compose run --rm dev uv run <command>`
- **End on editable branch**: All workflows must end on `contrib/*` (never `develop` or `main`)
- **ALWAYS prefer editing existing files** over creating new ones
- **Follow PR workflow sequence**: feature → contrib → develop → main
- **Quality gates must pass** before creating any PR
