# Architecture: Apply Templates Workflow

**Feature**: Apply workflow templates from stharrold-templates to media-intelligence
**GitHub Issue**: #11
**Date**: 2025-11-28

## Overview

This document describes the architectural approach for integrating workflow templates from `stharrold-templates` into the `media-intelligence` repository.

## Current State

### Existing media-intelligence Structure
```
media-intelligence/
├── CLAUDE.md                    # AI context (exists, comprehensive)
├── AGENTS.md                    # Cross-tool compatibility (exists)
├── README.md                    # Project documentation (exists)
├── .claude/
│   ├── commands/                # Workflow slash commands (exists)
│   └── skills/                  # 9 skills system (exists)
├── src/                         # Source code (exists)
├── tests/                       # Test suite (exists)
├── terraform/                   # GCP infrastructure (exists)
└── docs/                        # Documentation (minimal)
```

### Template Source Structure
```
.tmp/stharrold-templates/
├── WORKFLOW.md                  # Workflow documentation v5.3.0
├── ARCHITECTURE.md              # Architecture analysis
├── CONTRIBUTING.md              # Contribution guidelines
├── CHANGELOG.md                 # Version history format
├── azure-pipelines.yml          # CI/CD pipeline
├── docs/                        # Reference documentation
│   └── reference/               # Workflow phase docs
├── validate_documentation.sh    # Master validation script
├── test_*.sh                    # Individual validation tests
└── planning/                    # Planning templates
    └── specs/                   # Specification templates
```

## Target State

### Integrated Structure
```
media-intelligence/
├── CLAUDE.md                    # (enhanced with workflow details)
├── AGENTS.md                    # (synced from CLAUDE.md)
├── WORKFLOW.md                  # NEW: Workflow documentation
├── ARCHITECTURE.md              # NEW: Architecture analysis
├── CONTRIBUTING.md              # NEW: Contribution guidelines
├── CHANGELOG.md                 # (enhanced format)
├── azure-pipelines.yml          # NEW: Azure DevOps CI/CD
├── validate_documentation.sh    # NEW: Documentation validation
├── test_*.sh                    # NEW: Validation scripts
├── docs/
│   └── reference/               # NEW: Workflow phase documentation
│       ├── workflow-planning.md
│       ├── workflow-integration.md
│       ├── workflow-hotfix.md
│       └── workflow-operations.md
├── planning/                    # Planning artifacts
└── specs/                       # Specification artifacts
```

## Integration Strategy

### Phase 1: Documentation Templates
1. Copy and adapt WORKFLOW.md for media-intelligence context
2. Copy and adapt ARCHITECTURE.md for media-intelligence specifics
3. Create CONTRIBUTING.md with media-intelligence guidelines
4. Update CHANGELOG.md format

### Phase 2: Validation Infrastructure
1. Copy validation scripts to repository root
2. Adapt scripts for media-intelligence directory structure
3. Integrate with quality-enforcer (optional gate 6)

### Phase 3: Reference Documentation
1. Create docs/reference/ directory
2. Adapt workflow phase documentation for media-intelligence
3. Ensure all files ≤30KB

### Phase 4: CI/CD Integration
1. Copy azure-pipelines.yml
2. Adapt for media-intelligence build process
3. Test pipeline execution

## Design Decisions

### DD-1: Preserve Existing Functionality
- Do not modify src/, tests/, or terraform/
- Keep existing CLAUDE.md sections, add workflow sections
- Maintain current quality gates (5 gates)

### DD-2: File Adaptation vs Direct Copy
- WORKFLOW.md: Adapt (change project-specific references)
- ARCHITECTURE.md: Adapt (update for media-intelligence context)
- CONTRIBUTING.md: Adapt (repository-specific)
- Validation scripts: Copy with minimal changes
- azure-pipelines.yml: Adapt (adjust build commands)

### DD-3: Documentation Size Limits
- All docs/reference/ files: ≤20KB
- All root documentation: ≤30KB
- Use modular structure with cross-references

### DD-4: Validation Integration
- Validation scripts remain optional (not blocking quality gates)
- Run via `./validate_documentation.sh` for documentation PRs
- Quality gates remain: coverage, tests, build, lint, sync

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Conflicting documentation | Medium | Review and merge carefully |
| Breaking existing workflow | High | Run quality gates after each change |
| File size bloat | Low | Monitor ≤30KB limits |
| Missing cross-references | Low | Run validation scripts |

## Dependencies

- Existing skills system (no changes)
- Existing quality gates (no changes)
- podman-compose development workflow (no changes)
