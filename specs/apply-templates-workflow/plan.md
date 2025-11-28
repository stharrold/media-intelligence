# Implementation Plan: Apply Templates Workflow

**Type:** feature
**Slug:** apply-templates-workflow
**Date:** 2025-11-28

## Task Breakdown

### Phase 1: Verification and Validation

#### Task impl_001: Run Quality Gates

**Priority:** High

**Files:**
- `.claude/skills/quality-enforcer/scripts/run_quality_gates.py`

**Description:**
Verify all 5 quality gates pass for the current codebase state.

**Steps:**
1. Run the quality gates script
2. Document any failures
3. Fix any issues found

**Acceptance Criteria:**
- [ ] Coverage gate passes (≥40%)
- [ ] All tests pass
- [ ] Build succeeds
- [ ] Linting clean
- [ ] AI Config sync verified

**Verification:**
```bash
podman-compose run --rm dev uv run python .claude/skills/quality-enforcer/scripts/run_quality_gates.py
```

**Dependencies:**
- None

---

#### Task impl_002: Initialize AgentDB

**Priority:** High

**Files:**
- `.claude/skills/agentdb-state-manager/scripts/init_database.py`
- `.claude/skills/agentdb-state-manager/agentdb.duckdb`

**Description:**
Initialize the AgentDB DuckDB database for workflow state tracking.

**Steps:**
1. Run database initialization script
2. Verify database file created
3. Test state query

**Acceptance Criteria:**
- [ ] Database file exists at `.claude/skills/agentdb-state-manager/agentdb.duckdb`
- [ ] Query script returns valid JSON

**Verification:**
```bash
podman-compose run --rm dev uv run python .claude/skills/agentdb-state-manager/scripts/init_database.py
podman-compose run --rm dev uv run python .claude/skills/agentdb-state-manager/scripts/query_workflow_state.py --format json
```

**Dependencies:**
- None

---

### Phase 2: Specification Creation

#### Task impl_003: Create Feature Specifications

**Priority:** High

**Files:**
- `specs/apply-templates-workflow/spec.md`
- `specs/apply-templates-workflow/plan.md`
- `specs/apply-templates-workflow/CLAUDE.md`
- `specs/apply-templates-workflow/README.md`

**Description:**
Create the specification documents for this feature (self-referential - this task creates the files you're reading).

**Steps:**
1. Create `specs/apply-templates-workflow/` directory
2. Generate spec.md from planning/workflow-migration-plan.md
3. Generate plan.md with task breakdown
4. Create CLAUDE.md and README.md

**Acceptance Criteria:**
- [ ] spec.md exists with complete specification
- [ ] plan.md exists with task breakdown
- [ ] CLAUDE.md provides AI context
- [ ] README.md provides human-readable overview

**Verification:**
```bash
ls -la specs/apply-templates-workflow/
```

**Dependencies:**
- impl_001 (quality gates should pass first)

---

#### Task impl_004: Record Workflow State

**Priority:** Medium

**Files:**
- `.claude/skills/agentdb-state-manager/scripts/record_sync.py`

**Description:**
Record the /2_plan phase transition in AgentDB.

**Steps:**
1. Run record_sync script with phase_2_plan pattern
2. Verify state recorded
3. Query state to confirm

**Acceptance Criteria:**
- [ ] Workflow transition recorded
- [ ] State query shows phase_2_plan

**Verification:**
```bash
podman-compose run --rm dev uv run python .claude/skills/agentdb-state-manager/scripts/record_sync.py \
  --sync-type workflow_transition --pattern phase_2_plan \
  --source "planning/workflow-migration-plan.md" --target "specs/apply-templates-workflow"
podman-compose run --rm dev uv run python .claude/skills/agentdb-state-manager/scripts/query_workflow_state.py --format json
```

**Dependencies:**
- impl_002 (database must be initialized)
- impl_003 (specs must be created)

---

### Phase 3: Commit and Finalize

#### Task impl_005: Commit Specifications

**Priority:** High

**Files:**
- `specs/apply-templates-workflow/*`

**Description:**
Commit the specification files to the feature branch.

**Steps:**
1. Add specs directory to git
2. Create commit with descriptive message
3. Verify commit

**Acceptance Criteria:**
- [ ] All spec files committed
- [ ] Commit message follows convention

**Verification:**
```bash
git status
git log -1 --oneline
```

**Dependencies:**
- impl_003, impl_004

---

## Task Dependencies Graph

```
impl_001 (quality gates) ─┐
                          ├─> impl_003 (create specs) ─> impl_005 (commit)
impl_002 (init db) ───────┴─> impl_004 (record state) ─┘
```

## Critical Path

1. impl_001 - Run quality gates
2. impl_002 - Initialize AgentDB
3. impl_003 - Create specifications
4. impl_004 - Record workflow state
5. impl_005 - Commit specifications

## Parallel Work Opportunities

- impl_001 and impl_002 can run in parallel
- impl_003 depends on impl_001 passing
- impl_004 depends on both impl_002 and impl_003

## Quality Checklist

Before considering this phase complete:

- [ ] All tasks marked as complete
- [ ] Quality gates pass
- [ ] AgentDB initialized and recording
- [ ] Specifications created and committed
- [ ] Ready to proceed to /3_tasks

## Next Steps After Plan Completion

1. Run `/3_tasks` to validate task list
2. Run `/4_implement` to execute remaining tasks
3. Run `/5_integrate` to create PR to contrib branch
4. Continue through /6_release and /7_backmerge for full release

## Notes

### Implementation Tips

- This is a self-referential feature - we're using the workflow to validate the workflow itself
- Most of the heavy lifting (skills, commands, config) was done in preparation
- This phase focuses on validation and documentation

### Common Pitfalls

- Don't skip quality gates verification - they catch issues early
- Remember to initialize AgentDB before trying to record state
- Always run commands via `podman-compose run --rm dev uv run <command>`

### Resources

- `planning/workflow-migration-plan.md` - Complete migration plan
- `WORKFLOW.md` - Workflow system documentation
- `.claude/skills/*/CLAUDE.md` - Skill-specific context
