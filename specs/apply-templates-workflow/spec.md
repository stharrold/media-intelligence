# Specification: Apply Templates Workflow

**Type:** feature
**Slug:** apply-templates-workflow
**Date:** 2025-11-28
**Author:** stharrold

## Overview

Apply the skill-based progressive disclosure workflow system (v5.3) from `stharrold-templates` to the existing `media-intelligence` repository. This migration enables structured feature development, automated quality gates, and consistent branch management using the 7-step workflow (specify → plan → tasks → implement → integrate → release → backmerge).

## Implementation Context

<!-- Generated from planning/apply-templates-workflow/ -->

**Planning Reference:** See `planning/apply-templates-workflow/` for complete planning documents (requirements.md, architecture.md, epics.md).

**Migration Approach:** Manual selective copy (most control for existing repo with content)

**Key Decisions:**
- **Container runtime:** Keep Docker + add Podman aliases (existing Dockerfile works; dual support)
- **Package manager:** Already migrated to uv (pyproject.toml exists)
- **Branch structure:** Already created (develop + contrib/stharrold branches exist)
- **Quality gates:** Adapt for existing tests (≥40% coverage current, target: 80%)

## Requirements Reference

See: `planning/apply-templates-workflow/requirements.md` for functional requirements

### What Already Exists (Pre-Migration State)

- `.claude/` directory with 9 skills (workflow-orchestrator, tech-stack-adapter, git-workflow-manager, bmad-planner, speckit-author, quality-enforcer, workflow-utilities, agentdb-state-manager, initialize-repository)
- `.claude/commands/workflow/` with 9 slash commands
- Branch structure: main → develop → contrib/stharrold → feature/*
- `pyproject.toml` with uv-based config
- `Containerfile.dev` and `podman-compose.yml` for development
- Quality gates script at `.claude/skills/quality-enforcer/scripts/run_quality_gates.py`
- Pre-commit hooks configured in `.pre-commit-config.yaml`

### What Needs to Be Completed

1. **Verify all quality gates pass** (5 gates)
2. **Test workflow commands** (/1_specify through /7_backmerge)
3. **Validate AgentDB state tracking**
4. **Create first feature using the workflow** (this feature itself)

## Detailed Specification

### Component 1: Quality Gates Verification

**Script:** `.claude/skills/quality-enforcer/scripts/run_quality_gates.py`

**Purpose:** Validate all 5 quality gates pass before any PR

**Quality Gates:**
| Gate | Requirement | Current Status |
|------|-------------|----------------|
| 1. Coverage | ≥40% test coverage | Needs verification |
| 2. Tests | All pytest tests pass | Needs verification |
| 3. Build | Build succeeds | Needs verification |
| 4. Linting | `ruff check .` clean | Needs verification |
| 5. AI Config Sync | CLAUDE.md → AGENTS.md synced | Needs verification |

**Verification:**
```bash
podman-compose run --rm dev uv run python .claude/skills/quality-enforcer/scripts/run_quality_gates.py
```

### Component 2: Workflow Commands

**Location:** `.claude/commands/workflow/`

**Commands:**
| Command | Purpose | Dependencies |
|---------|---------|--------------|
| `/1_specify` | Create feature branch and specification | None |
| `/2_plan` | Generate specifications from planning | /1_specify |
| `/3_tasks` | Validate task list from plan.md | /2_plan |
| `/4_implement` | Execute tasks + run quality gates | /3_tasks |
| `/5_integrate` | Create PRs, cleanup worktree | /4_implement |
| `/6_release` | Create release (develop→main) | /5_integrate |
| `/7_backmerge` | Sync release to develop and contrib | /6_release |

### Component 3: AgentDB State Tracking

**Location:** `.claude/skills/agentdb-state-manager/`

**Purpose:** Track workflow state transitions and sync events

**Scripts:**
- `scripts/init_database.py` - Initialize DuckDB database
- `scripts/record_sync.py` - Record workflow transitions
- `scripts/query_workflow_state.py` - Query current state

**Usage:**
```bash
# Initialize database
podman-compose run --rm dev uv run python .claude/skills/agentdb-state-manager/scripts/init_database.py

# Record transition
podman-compose run --rm dev uv run python .claude/skills/agentdb-state-manager/scripts/record_sync.py \
  --sync-type workflow_transition --pattern phase_2_plan

# Query state
podman-compose run --rm dev uv run python .claude/skills/agentdb-state-manager/scripts/query_workflow_state.py --format json
```

## Testing Requirements

### Unit Tests

Existing tests in `tests/` should continue to pass:
- `test_transcription.py`, `test_diarization.py`, `test_situation.py` - Local pipeline
- `test_speech_client.py`, `test_situation_classifier.py`, `test_storage_manager.py`, `test_audio_processor.py` - GCP
- `test_integration.py`, `test_gcp_integration.py` - End-to-end

### Workflow Tests

Validate the workflow system works:
1. Run quality gates script
2. Execute `/1_specify` through `/5_integrate` for a test feature
3. Verify AgentDB records state transitions
4. Confirm PR workflow (feature → contrib → develop → main)

## Quality Gates

- [x] Test coverage ≥40% (current minimum, target 80% tracked in issue #9)
- [ ] All tests passing
- [ ] Build succeeds (`podman-compose build`)
- [ ] Linting clean (`podman-compose run --rm dev uv run ruff check .`)
- [ ] AI Config synced (`CLAUDE.md → AGENTS.md`)

## Dependencies

**Already in pyproject.toml:**
- `rich>=13.9.0` - Console formatting
- `click>=8.1.0` - CLI framework
- `duckdb>=1.4.2` - AgentDB state storage
- `pytest>=8.4.2` - Testing
- `pytest-cov>=7.0.0` - Coverage
- `ruff>=0.14.1` - Linting
- `pre-commit>=4.5.0` - Git hooks

## Implementation Notes

### Key Considerations

1. **This feature is self-referential** - We're using the workflow to validate the workflow
2. **Existing content preserved** - No overwrites of existing `src/` or `tests/` code
3. **Containerized execution** - All commands run via `podman-compose run --rm dev uv run <command>`

### Critical Guidelines

- **One way to run:** Always use `podman-compose run --rm dev uv run <command>`
- **End on editable branch:** Workflows must end on `contrib/*` (never `develop` or `main`)
- **Quality gates must pass** before creating any PR
- **Follow PR workflow sequence:** feature → contrib → develop → main

## References

- `planning/apply-templates-workflow/` - Planning documents (requirements, architecture, epics)
- `.claude/skills/` - 9 workflow skills
- `CLAUDE.md` - Project context and workflow overview
