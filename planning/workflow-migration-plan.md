# Workflow Migration Plan: Applying stharrold-templates to media-intelligence

**Version:** 1.0.0
**Date:** 2025-11-25
**Source:** `.tmp/stharrold-templates` (Workflow v5.3.0)
**Target:** `media-intelligence` repository

---

## Executive Summary

This plan details how to apply the skill-based progressive disclosure workflow from `stharrold-templates` to the existing `media-intelligence` repository. Since media-intelligence is an **existing repository with content**, we will use the **Manual Selective Copy approach** (most control) rather than the automated `initialize_repository.py` script.

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Migration approach | Manual selective | Existing repo with content; avoid overwrites |
| Container runtime | Keep Docker + add Podman aliases | Existing Dockerfile works; dual support |
| Package manager | Migrate to uv | Required for workflow scripts |
| Branch structure | Add develop + contrib branches | Required for PR workflow |
| Quality gates | Adapt for existing tests | Keep ≥80% coverage target |

---

## Current State Analysis

### media-intelligence Repository

```
media-intelligence/
├── CLAUDE.md                    # Exists (no YAML frontmatter)
├── README.md, DEPLOYMENT.md     # Documentation exists
├── src/                         # 12 Python modules
├── tests/                       # 10 test files
├── terraform/                   # GCP infrastructure
├── requirements.txt             # pip-based dependencies
├── Dockerfile, Dockerfile.gcp   # Docker containers
├── compose.yaml                 # Docker Compose
├── build.sh, run.sh, test.sh    # Shell scripts
├── deploy.sh, test_gcp.sh       # GCP deployment
└── config.yaml, .env.example    # Configuration
```

**Existing strengths:**
- Comprehensive test suite
- Well-documented (CLAUDE.md, README, DEPLOYMENT.md)
- Working Docker setup
- GCP deployment pipeline

**Gaps to address:**
- No branch protection workflow (only `main` branch)
- No YAML frontmatter in CLAUDE.md
- No `.claude/skills/` system
- No pre-commit hooks
- pip-based (not uv)
- No quality gates automation

### stharrold-templates Workflow Components

```
stharrold-templates/
├── .claude/
│   ├── commands/workflow/       # 9 slash commands
│   └── skills/                  # 9 specialized skills
├── .agents/                     # Synced mirror (OpenAI spec)
├── CLAUDE.md                    # With YAML frontmatter
├── AGENTS.md                    # Synced from CLAUDE.md
├── WORKFLOW.md                  # Complete workflow guide
├── ARCHITECTURE.md              # System architecture
├── CONTRIBUTING.md              # Contribution guidelines
├── pyproject.toml               # uv-based config
├── .pre-commit-config.yaml      # Quality hooks
├── Containerfile                # Podman container
└── podman-compose.yml           # Container orchestration
```

---

## Migration Phases

### Phase 0: Prerequisites & Backup (30 minutes)

**Goal:** Ensure safe migration with rollback capability.

#### 0.1 Verify Prerequisites

```bash
# Required tools
git --version             # Must be installed
gh --version              # GitHub CLI for PRs
python3 --version         # 3.11+ required
pip install uv            # Or: curl -LsSf https://astral.sh/uv/install.sh | sh

# Optional (for full workflow)
podman --version          # 4.0+ for container workflow
```

#### 0.2 Create Backup Branch

```bash
cd /Users/stharrold/Documents/GitHub/media-intelligence

# Create backup of current state
git checkout main
git checkout -b backup/pre-workflow-migration-$(date +%Y%m%d)
git push origin backup/pre-workflow-migration-$(date +%Y%m%d)
```

#### 0.3 Commit Any Uncommitted Changes

```bash
git status
# If changes exist:
git add .
git commit -m "chore: checkpoint before workflow migration"
```

---

### Phase 1: Branch Structure Setup (15 minutes)

**Goal:** Establish git-flow + GitHub-flow hybrid branch structure.

#### 1.1 Create Branch Hierarchy

```bash
# From main branch
git checkout main
git pull origin main

# Create develop branch (integration)
git checkout -b develop
git push -u origin develop

# Create personal contrib branch
git checkout -b contrib/stharrold
git push -u origin contrib/stharrold

# Return to main for reference
git checkout main
```

#### 1.2 Configure Branch Protection (GitHub UI)

Navigate to: Repository Settings → Branches → Branch protection rules

**For `main` branch:**
- ✅ Require pull request before merging
- ✅ Require status checks to pass (after CI setup)
- ✅ Require conversation resolution before merging
- ✅ Do not allow bypassing the above settings

**For `develop` branch:**
- ✅ Require pull request before merging
- ✅ Require status checks to pass (after CI setup)

#### 1.3 Branch Structure Result

```
main (production, protected)
  ↑
develop (integration, protected)
  ↑
contrib/stharrold (active development)
  ↑
feature/* (isolated features via worktrees)
```

---

### Phase 2: Package Management Migration (30 minutes)

**Goal:** Migrate from requirements.txt to uv-based pyproject.toml.

#### 2.1 Create pyproject.toml

```toml
# pyproject.toml for media-intelligence
# Audio processing pipeline for extracting structured intelligence

[project]
name = "media-intelligence"
version = "1.0.0"
description = "Containerized audio processing system for extracting structured intelligence from recorded media"
requires-python = ">=3.11"
dependencies = [
    # Core ML/Audio
    "faster-whisper>=1.0.0",
    "pyannote-audio>=3.1.0",
    "torch>=2.0.0",
    "torchaudio>=2.0.0",
    "transformers>=4.35.0",

    # GCP
    "google-cloud-speech>=2.21.0",
    "google-cloud-storage>=2.10.0",
    "google-cloud-aiplatform>=1.35.0",

    # Utilities
    "pydantic>=2.0.0",
    "tenacity>=8.2.0",
    "python-dotenv>=1.0.0",
    "pyyaml>=6.0.0",
    "structlog>=23.1.0",

    # Workflow system dependencies
    "rich>=13.9.0",
    "click>=8.1.0",
    "httpx>=0.27.0",
    "duckdb>=1.4.2",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.ruff]
line-length = 170
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "B", "UP"]
ignore = ["E402"]

[tool.ruff.lint.per-file-ignores]
".claude/**/*.py" = ["N999", "B007", "B904", "B905"]
"tests/**/*.py" = ["N999"]

[tool.uv]
dev-dependencies = [
    "pre-commit>=4.5.0",
    "pytest>=8.4.2",
    "pytest-cov>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "ruff>=0.14.1",
    "mypy>=1.18.2",
]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["src*"]
exclude = ["tests*", ".claude*", "terraform*", "docs*"]
```

#### 2.2 Initialize uv Environment

```bash
git checkout contrib/stharrold

# Initialize uv from existing requirements
uv init --no-readme
uv add $(cat requirements.txt | grep -v '^#' | grep -v '^$' | tr '\n' ' ')

# Add dev dependencies
uv add --dev pytest pytest-cov pytest-asyncio ruff mypy pre-commit

# Sync environment
uv sync

# Verify
uv run pytest tests/ -v --tb=short
```

#### 2.3 Keep requirements.txt for Docker

```bash
# Generate requirements.txt from uv for Docker compatibility
uv pip compile pyproject.toml -o requirements.txt
```

---

### Phase 3: Skills System Installation (45 minutes)

**Goal:** Copy the 9-skill workflow system to media-intelligence.

#### 3.1 Copy Skills Directory

```bash
# From media-intelligence root
cp -r .tmp/stharrold-templates/.claude .

# Verify structure
ls -la .claude/skills/
# Should show: workflow-orchestrator, tech-stack-adapter, git-workflow-manager,
#              bmad-planner, speckit-author, quality-enforcer, workflow-utilities,
#              agentdb-state-manager, initialize-repository
```

#### 3.2 Copy Slash Commands

```bash
# Commands are already in .claude/commands/workflow/
ls -la .claude/commands/workflow/
# Should show: 1_specify.md through 7_backmerge.md, all.md, CLAUDE.md
```

#### 3.3 Adapt Skills for media-intelligence

**Modify `.claude/skills/tech-stack-adapter/`** to recognize:
- Docker (existing) + Podman (optional)
- Both `requirements.txt` and `pyproject.toml`
- Existing test structure in `tests/`

**No changes needed for:**
- workflow-orchestrator (generic)
- git-workflow-manager (generic)
- bmad-planner (generic)
- speckit-author (generic)
- quality-enforcer (paths configurable)
- workflow-utilities (generic)
- agentdb-state-manager (generic)
- initialize-repository (meta-skill, not used in this repo)

#### 3.4 Create Workflow Directories

```bash
mkdir -p planning
mkdir -p specs
mkdir -p ARCHIVED

# Create directory CLAUDE.md files
cat > planning/CLAUDE.md << 'EOF'
---
type: claude-context
directory: planning
purpose: BMAD planning documents for features
parent: ../CLAUDE.md
sibling_readme: README.md
children:
  - ARCHIVED/CLAUDE.md
---

# Claude Code Context: planning

Planning documents created by `/1_specify` (BMAD planner).

## Contents

Feature planning directories with:
- `requirements.md` - Feature requirements
- `architecture.md` - Technical architecture
- `epics.md` - User stories and epics

## Related

- **Parent**: [media-intelligence](../CLAUDE.md)
EOF

cat > specs/CLAUDE.md << 'EOF'
---
type: claude-context
directory: specs
purpose: SpecKit specifications for features
parent: ../CLAUDE.md
sibling_readme: README.md
children:
  - ARCHIVED/CLAUDE.md
---

# Claude Code Context: specs

Detailed specifications created by `/2_plan` (SpecKit author).

## Contents

Feature specification directories with:
- `spec.md` - Detailed specification
- `plan.md` - Implementation task breakdown

## Related

- **Parent**: [media-intelligence](../CLAUDE.md)
EOF
```

---

### Phase 4: Quality Infrastructure (30 minutes)

**Goal:** Set up pre-commit hooks and quality gates.

#### 4.1 Create Pre-commit Configuration

```bash
cat > .pre-commit-config.yaml << 'EOF'
# Pre-commit hooks for repository consistency
# Install: uv run pre-commit install
# Run manually: uv run pre-commit run --all-files

repos:
  # Standard hooks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
        args: ['--maxkb=500']
      - id: check-merge-conflict
      - id: detect-private-key

  # Ruff for Python linting and formatting
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  # Local hooks for repository-specific checks
  - repo: local
    hooks:
      # Sync AI configuration files (CLAUDE.md → AGENTS.md, .agents/)
      - id: sync-ai-config
        name: Sync AI configuration (CLAUDE.md → AGENTS.md, .agents/)
        entry: python .claude/skills/workflow-utilities/scripts/sync_ai_config.py sync
        language: python
        files: ^(CLAUDE\.md|\.claude/)
        pass_filenames: false
        stages: [pre-commit]

      # Check CLAUDE.md frontmatter
      - id: claude-md-frontmatter
        name: Check CLAUDE.md has YAML frontmatter
        entry: python .claude/skills/workflow-utilities/scripts/check_claude_md_frontmatter.py
        language: python
        files: CLAUDE\.md$
        pass_filenames: false
EOF
```

#### 4.2 Install Pre-commit Hooks

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

#### 4.3 Adapt Quality Gates Script

The quality gates are in `.claude/skills/quality-enforcer/scripts/run_quality_gates.py`.

**5 Quality Gates:**
| Gate | Description | media-intelligence Adaptation |
|------|-------------|------------------------------|
| 1. Coverage | ≥80% test coverage | Use existing `pytest --cov=src` |
| 2. Tests | All pytest tests pass | Use existing `pytest tests/` |
| 3. Build | Build succeeds | `uv build` or existing `./build.sh` |
| 4. Linting | `ruff check .` clean | Add ruff to workflow |
| 5. AI Config Sync | CLAUDE.md synced | New requirement |

---

### Phase 5: Documentation Updates (45 minutes)

**Goal:** Add YAML frontmatter and create documentation hierarchy.

#### 5.1 Update Root CLAUDE.md

Replace the current CLAUDE.md with YAML frontmatter version:

```markdown
---
type: claude-context
directory: .
purpose: Containerized audio processing system for extracting structured intelligence from recorded media
parent: null
sibling_readme: README.md
children:
  - .claude/CLAUDE.md
  - src/CLAUDE.md
  - tests/CLAUDE.md
  - terraform/CLAUDE.md
  - planning/CLAUDE.md
  - specs/CLAUDE.md
---

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Media Intelligence Pipeline: A containerized audio processing system for extracting structured intelligence from recorded media. Supports two deployment modes:

- **Local**: CPU-only containerized pipeline (air-gapped deployment ready)
- **GCP**: Cloud-native pipeline using Google Cloud managed services

## Essential Commands

```bash
# Build and test (containerized - preferred)
./build.sh              # Build container image
./run.sh <audio.wav>    # Process audio file
./test.sh               # Run validation tests

# Development (uv-based)
uv run pytest tests/    # Run unit tests
uv run ruff check .     # Lint code
uv run ruff check --fix # Auto-fix linting issues

# Quality gates (before PR)
uv run python .claude/skills/quality-enforcer/scripts/run_quality_gates.py

# GCP deployment
./deploy.sh --project PROJECT_ID --region REGION
./test_gcp.sh
```

## Workflow System

This repository uses a **skill-based workflow system** (v5.3) located in `.claude/skills/`.

### Slash Commands

| Command | Purpose |
|---------|---------|
| `/workflow/all` | Orchestrate full workflow with auto-detection |
| `/1_specify` | Create feature branch and specification |
| `/2_plan` | Generate detailed specs via speckit-author |
| `/3_tasks` | Validate task list from plan.md |
| `/4_implement` | Execute tasks + run quality gates |
| `/5_integrate` | Create PRs, cleanup worktree |
| `/6_release` | Create release (develop→main) |
| `/7_backmerge` | Sync release to develop and contrib |

### Branch Structure

```
main (production) ← develop (integration) ← contrib/stharrold (active) ← feature/*
```

### Quality Gates (5 gates, all must pass before PR)

| Gate | Description |
|------|-------------|
| 1. Coverage | ≥80% test coverage |
| 2. Tests | All pytest tests pass |
| 3. Build | Build succeeds |
| 4. Linting | `ruff check .` clean |
| 5. AI Config Sync | CLAUDE.md → AGENTS.md synced |

## Architecture

### Local Pipeline (`src/`)
- `process_audio.py` - Main CLI and orchestration
- `transcription.py` - faster-whisper wrapper (Whisper INT8)
- `diarization.py` - pyannote-audio 3.1 speaker diarization
- `situation.py` - AST AudioSet classifier
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

## Key Patterns

- **Dataclasses**: `TranscriptSegment`, `SituationSegment`, `ProcessingResult`
- **Lazy initialization**: GCP clients use `@property` pattern
- **Retry logic**: `tenacity` for transient errors
- **Context managers**: `download_temp_file()` for cleanup

## Configuration

- `.env` - Environment variables (HuggingFace token, GCP settings)
- `config.yaml` - Advanced processing options
- Precedence: defaults → config.yaml → .env → CLI args

## Testing

Tests are in `tests/` with mocked external dependencies:
- `test_transcription.py`, `test_diarization.py`, `test_situation.py` - Local
- `test_speech_client.py`, `test_situation_classifier.py`, `test_storage_manager.py`, `test_audio_processor.py` - GCP
- `test_integration.py`, `test_gcp_integration.py` - End-to-end

Run tests:
```bash
uv run pytest tests/           # All tests
uv run pytest tests/ -v -k test_transcription  # Single test
uv run pytest tests/ --cov=src --cov-report=term  # With coverage
```

## Critical Guidelines

- **ALWAYS prefer editing existing files** over creating new ones
- **End on editable branch**: All workflows must end on `contrib/*` (never `develop` or `main`)
- **Quality gates must pass** before creating any PR
- **Follow PR workflow sequence**: feature → contrib → develop → main
```

#### 5.2 Copy Workflow Documentation

```bash
# Copy workflow documentation
cp .tmp/stharrold-templates/WORKFLOW.md .
cp .tmp/stharrold-templates/CONTRIBUTING.md .
cp .tmp/stharrold-templates/ARCHITECTURE.md .

# These files are tech-agnostic and work as-is
```

#### 5.3 Create Directory CLAUDE.md Files

Create CLAUDE.md with YAML frontmatter in each major directory:
- `src/CLAUDE.md`
- `tests/CLAUDE.md`
- `terraform/CLAUDE.md`
- `docs/CLAUDE.md`

---

### Phase 6: AI Config Sync Setup (20 minutes)

**Goal:** Enable automatic sync to AGENTS.md and .agents/.

#### 6.1 Create .agents Directory

```bash
mkdir -p .agents
mkdir -p .github
```

#### 6.2 Create AGENTS.md

```bash
# Initial sync will create this
uv run python .claude/skills/workflow-utilities/scripts/sync_ai_config.py sync
```

#### 6.3 Create GitHub Copilot Instructions

```bash
# sync_ai_config.py creates this automatically
# Located at .github/copilot-instructions.md
```

#### 6.4 Verify Sync

```bash
uv run python .claude/skills/workflow-utilities/scripts/sync_ai_config.py verify
```

---

### Phase 7: Container Integration (Optional, 20 minutes)

**Goal:** Add Podman support while keeping Docker.

#### 7.1 Create Containerfile (Podman-compatible)

```dockerfile
# Containerfile - Podman-compatible container for media-intelligence
# Also works with Docker: docker build -f Containerfile -t media-intelligence .

FROM python:3.11-slim

LABEL maintainer="stharrold"
LABEL description="Media Intelligence Pipeline with uv + Python 3.11"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install uv
ENV UV_VERSION=0.5.5
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy dependency files first (for layer caching)
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN uv sync --frozen 2>/dev/null || uv sync

# Copy project files
COPY . .

CMD ["bash"]
```

#### 7.2 Create podman-compose.yml

```yaml
# podman-compose.yml - Development environment
# Usage: podman-compose run --rm dev <command>

services:
  dev:
    build:
      context: .
      dockerfile: Containerfile
    image: media-intelligence:latest
    container_name: media-intelligence-dev
    working_dir: /app
    volumes:
      - .:/app:Z
    stdin_open: true
    tty: true
    command: bash
```

#### 7.3 Keep Existing Docker Setup

The existing `Dockerfile` and `compose.yaml` continue to work for production deployments.

---

## Implementation Checklist

### Phase 0: Prerequisites & Backup
- [ ] Verify git, gh, python3, uv installed
- [ ] Create backup branch
- [ ] Commit any uncommitted changes

### Phase 1: Branch Structure
- [ ] Create `develop` branch from `main`
- [ ] Create `contrib/stharrold` branch from `develop`
- [ ] Configure branch protection rules in GitHub

### Phase 2: Package Management
- [ ] Create `pyproject.toml` with all dependencies
- [ ] Initialize uv environment
- [ ] Verify tests pass with `uv run pytest`
- [ ] Generate `requirements.txt` for Docker compatibility

### Phase 3: Skills System
- [ ] Copy `.claude/` directory from templates
- [ ] Verify 9 skills present
- [ ] Create `planning/`, `specs/`, `ARCHIVED/` directories
- [ ] Create directory CLAUDE.md files

### Phase 4: Quality Infrastructure
- [ ] Create `.pre-commit-config.yaml`
- [ ] Install pre-commit hooks
- [ ] Run pre-commit on all files
- [ ] Verify quality gates script works

### Phase 5: Documentation
- [ ] Update root `CLAUDE.md` with YAML frontmatter
- [ ] Copy `WORKFLOW.md`, `CONTRIBUTING.md`, `ARCHITECTURE.md`
- [ ] Create CLAUDE.md in `src/`, `tests/`, `terraform/`, `docs/`

### Phase 6: AI Config Sync
- [ ] Create `.agents/` directory
- [ ] Run initial sync to create `AGENTS.md`
- [ ] Create `.github/copilot-instructions.md`
- [ ] Verify sync working

### Phase 7: Container Integration (Optional)
- [ ] Create `Containerfile` for Podman
- [ ] Create `podman-compose.yml`
- [ ] Test container builds

---

## Post-Migration Workflow

After migration, the daily workflow becomes:

### Starting a New Feature

```bash
# 1. Ensure on contrib branch
git checkout contrib/stharrold

# 2. Use /1_specify to create feature specification
# Or manually:
uv run python .claude/skills/bmad-planner/scripts/create_planning.py my-feature stharrold

# 3. Create feature worktree
uv run python .claude/skills/git-workflow-manager/scripts/create_worktree.py \
  feature my-feature contrib/stharrold

# 4. Navigate to worktree and implement
cd ../media-intelligence_feature_my-feature

# 5. Run quality gates
uv run python .claude/skills/quality-enforcer/scripts/run_quality_gates.py

# 6. Create PR to contrib
uv run python .claude/skills/git-workflow-manager/scripts/pr_workflow.py finish-feature
```

### Creating a Release

```bash
# From contrib branch
uv run python .claude/skills/git-workflow-manager/scripts/release_workflow.py full
```

---

## Rollback Procedure

If migration causes issues:

```bash
# Return to backup branch
git checkout backup/pre-workflow-migration-YYYYMMDD

# Or reset main to before migration
git checkout main
git reset --hard origin/main

# Delete workflow artifacts
rm -rf .claude/ .agents/ planning/ specs/ ARCHIVED/
rm -f WORKFLOW.md CONTRIBUTING.md ARCHITECTURE.md AGENTS.md
rm -f pyproject.toml .pre-commit-config.yaml Containerfile podman-compose.yml
```

---

## Estimated Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 0: Prerequisites | 30 min | None |
| Phase 1: Branch Structure | 15 min | Phase 0 |
| Phase 2: Package Management | 30 min | Phase 1 |
| Phase 3: Skills System | 45 min | Phase 2 |
| Phase 4: Quality Infrastructure | 30 min | Phase 3 |
| Phase 5: Documentation | 45 min | Phase 3 |
| Phase 6: AI Config Sync | 20 min | Phase 5 |
| Phase 7: Container Integration | 20 min | Phase 2 (optional) |
| **Total** | **~4 hours** | |

---

## Success Criteria

Migration is successful when:

1. ✅ Branch structure exists: main → develop → contrib/stharrold
2. ✅ `uv run pytest tests/` passes (≥80% coverage)
3. ✅ `uv run pre-commit run --all-files` passes
4. ✅ Quality gates script runs without errors
5. ✅ Slash commands (`/1_specify`, etc.) are available
6. ✅ CLAUDE.md has YAML frontmatter
7. ✅ AGENTS.md syncs correctly from CLAUDE.md
8. ✅ Can create feature worktree and PR workflow
