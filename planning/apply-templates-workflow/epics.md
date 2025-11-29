# Epics: Apply Templates Workflow

**Feature**: Apply workflow templates from stharrold-templates to media-intelligence
**GitHub Issue**: #11
**Date**: 2025-11-28

## Epic 1: Documentation Templates

**Goal**: Integrate core documentation templates adapted for media-intelligence

### Tasks
- [ ] E1.1: Copy and adapt WORKFLOW.md
  - Update project name references
  - Adjust skill descriptions for media-intelligence
  - Update command examples
- [ ] E1.2: Copy and adapt ARCHITECTURE.md
  - Update system architecture sections
  - Include media-intelligence pipeline details
  - Add GCP deployment context
- [ ] E1.3: Create CONTRIBUTING.md
  - Adapt from template
  - Include media-intelligence specific guidelines
  - Reference existing quality gates
- [ ] E1.4: Update CHANGELOG.md format
  - Ensure consistent versioning format
  - Add template integration entry

**Acceptance**: All documentation files pass validation, ≤30KB each

---

## Epic 2: Validation Scripts

**Goal**: Integrate documentation validation infrastructure

### Tasks
- [ ] E2.1: Copy validation scripts to root
  - validate_documentation.sh
  - test_file_size.sh
  - test_cross_references.sh
  - test_content_duplication.sh
  - test_command_syntax.sh
  - test_yaml_structure.sh
- [ ] E2.2: Adapt scripts for media-intelligence
  - Update directory paths
  - Adjust file patterns
  - Test execution
- [ ] E2.3: Document validation usage in CLAUDE.md
  - Add validation commands section
  - Include in development workflow

**Acceptance**: `./validate_documentation.sh` runs successfully

---

## Epic 3: Reference Documentation

**Goal**: Create detailed workflow phase documentation

### Tasks
- [ ] E3.1: Create docs/reference/ directory structure
  - CLAUDE.md for directory
  - README.md for directory
  - ARCHIVED/ subdirectory
- [ ] E3.2: Create workflow-planning.md
  - Phases 0-3 documentation
  - Adapted for media-intelligence
- [ ] E3.3: Create workflow-integration.md
  - Phases 4-5 documentation
  - PR workflow details
- [ ] E3.4: Create workflow-hotfix.md
  - Phase 6 documentation
  - Emergency fix procedures
- [ ] E3.5: Create workflow-operations.md
  - Maintenance procedures
  - Troubleshooting guide

**Acceptance**: All files ≤20KB, cross-references valid

---

## Epic 4: CI/CD Integration

**Goal**: Add Azure DevOps pipeline support

### Tasks
- [ ] E4.1: Copy azure-pipelines.yml
  - Adapt for media-intelligence build
  - Include podman-compose setup
- [ ] E4.2: Configure pipeline stages
  - Build stage
  - Test stage
  - Lint stage
  - Quality gates stage
- [ ] E4.3: Test pipeline (if Azure DevOps available)
  - Verify all stages pass
  - Document any issues

**Acceptance**: Pipeline YAML is valid, stages defined correctly

---

## Priority Order

1. **Epic 1** (Documentation Templates) - Foundation for other epics
2. **Epic 2** (Validation Scripts) - Quality assurance
3. **Epic 3** (Reference Documentation) - Detailed guidance
4. **Epic 4** (CI/CD Integration) - Optional, enhances automation

## Estimated Scope

- **Total tasks**: 15
- **Files to create/modify**: ~15
- **Quality gates**: Must pass after each epic
