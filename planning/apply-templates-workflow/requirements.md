# Requirements: Apply Templates Workflow

**Feature**: Apply workflow templates from stharrold-templates to media-intelligence
**GitHub Issue**: #11
**Date**: 2025-11-28

## Functional Requirements

### FR-1: Documentation Templates
- [ ] Integrate WORKFLOW.md (v5.3.0) adapted for media-intelligence context
- [ ] Integrate ARCHITECTURE.md with media-intelligence specifics
- [ ] Integrate CONTRIBUTING.md with repository-specific guidelines
- [ ] Update CHANGELOG.md format for consistency

### FR-2: Validation Scripts
- [ ] Integrate `validate_documentation.sh` master script
- [ ] Integrate `test_file_size.sh` (30KB limit)
- [ ] Integrate `test_cross_references.sh` (internal links)
- [ ] Integrate `test_content_duplication.sh` (detect duplicates)
- [ ] Integrate `test_command_syntax.sh` (validate bash commands)
- [ ] Integrate `test_yaml_structure.sh` (check frontmatter)

### FR-3: Reference Documentation Structure
- [ ] Create `docs/reference/` directory hierarchy
- [ ] Create workflow phase documentation (workflow-planning.md, workflow-integration.md, workflow-hotfix.md, workflow-operations.md)
- [ ] Ensure documentation ≤30KB per file for AI context optimization

### FR-4: CI/CD Pipeline
- [ ] Integrate `azure-pipelines.yml` for Azure DevOps compatibility
- [ ] Ensure pipeline runs same podman-compose commands as local

## Non-Functional Requirements

### NFR-1: Compatibility
- Preserve existing media-intelligence functionality
- Maintain compatibility with current GCP deployment
- Keep existing test coverage (≥40%)

### NFR-2: Documentation Standards
- All files ≤30KB for AI context optimization
- YAML frontmatter on all CLAUDE.md and README.md files
- Cross-references between related documentation

### NFR-3: Workflow Consistency
- Follow existing branch structure: feature → contrib → develop → main
- Use existing quality gates (5 gates)
- Maintain containerized development pattern

## User Stories

### US-1: Developer Documentation
As a developer, I want comprehensive workflow documentation so that I can follow consistent development practices.

### US-2: CI/CD Pipeline
As a developer, I want automated validation scripts so that documentation quality is maintained.

### US-3: Cross-Platform Support
As a developer, I want Azure DevOps pipeline support so that I can use either GitHub Actions or Azure Pipelines.

## Acceptance Criteria

1. All validation scripts pass on existing documentation
2. WORKFLOW.md accurately reflects media-intelligence workflow
3. Quality gates continue to pass (≥40% coverage, tests, lint, build, sync)
4. No breaking changes to existing functionality
5. Documentation follows ≤30KB file size standard
