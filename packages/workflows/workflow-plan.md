---
name: workflow-plan
description: Stage 2 Planning Workflow - Ingest docs/specs/{feature_id}.spec.md, design architecture, schemas, and produce docs/plans/{feature_id}.plan.md with parallel DAG
---

# Stage 2: Architecture & Task DAG Planning Workflow

## 1. Objective & Persona
- **Persona**: `task-planner`
- **Model Engine**: ✦ **Gemini 4 Argon** (`model: gemini-4-argon`, `reasoning_effort: high`)
- **Primary Skill**: `planning-and-task-breakdown` & `api-and-interface-design`

---

## 2. Input Contract
- **Prerequisite**: Stage 1 must be completed.
- **Input Artifact**: `docs/specs/{feature_id}.spec.md`
- **Context Provided**:
  * Pointers to existing code, database schemas, and configuration.
  * Acceptance criteria from the spec.

---

## 3. Execution Steps
1. **Emit Start Telemetry**:
   ```bash
   python3 tools/orchestrator/client.py update \
     --task "PLAN-{FEATURE}" \
     --agent "task-planner" \
     --model "gemini-4-argon" \
     --complexity "high" \
     --status "running" \
     --progress 20 \
     --scope "docs/specs/{feature_id}.spec.md" \
     --notes "Designing system contracts and task DAG"
   ```
2. **Architecture & Contract Modeling**: Define database schema, API signatures, and data contracts between modules.
3. **DAG Breakdown & Concurrency Grouping**:
   - Split tasks into minimal blast-radius units.
   - Assign `parallel_group` to tasks that operate on disjoint files.
   - Tag prerequisite dependencies using `depends_on`.
   - Assign appropriate engine: `gemini-4-argon` for architecture/security; `gemini-3.8-flash` for implementation/tests.
4. **Artifact Generation**: Produce `docs/plans/{feature_id}.plan.md`.
5. **Emit Completion Telemetry**:
   ```bash
   python3 tools/orchestrator/client.py update \
     --task "PLAN-{FEATURE}" \
     --agent "task-planner" \
     --model "gemini-4-argon" \
     --status "completed" \
     --progress 100 \
     --scope "docs/plans/{feature_id}.plan.md" \
     --notes "Plan DAG finalized with parallel worker slots"
   ```

---

## 4. Output Contract (Artifact Schema)
Save to: `docs/plans/{feature_id}.plan.md`

```markdown
# Architecture & Implementation Plan: {Feature Name}

- **Feature ID**: {feature_id}
- **Source Spec**: docs/specs/{feature_id}.spec.md
- **Architect**: task-planner (Gemini 4 Argon)
- **Status**: APPROVED

## 1. Technical Architecture & Schemas
- Interface contracts, data models, or SQL migrations.
- File boundary allocations.

## 2. Directed Acyclic Graph (DAG) & Task Matrix

| Task ID | Description | Target Files | Model | Complexity | Depends On | Parallel Group |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **BUILD-01** | Backend Schema & DB Migration | `backend/models/...` | ⚡ Flash | `medium` | `[]` | `PARALLEL-CORE` |
| **BUILD-02** | Frontend Component & UI | `frontend/src/...` | ⚡ Flash | `medium` | `[]` | `PARALLEL-CORE` |
| **BUILD-03** | REST API Route Handler | `backend/api/...` | ⚡ Flash | `medium` | `["BUILD-01"]` | `PARALLEL-API` |
| **TEST-01** | Unit & Integration Test Suite | `tests/...` | ⚡ Flash | `low` | `["BUILD-02", "BUILD-03"]` | - |

## 3. Barrier Synchronization Criteria
- Conditions required before advancing to Testing and Code Review.
```

> **Handoff**: The Orchestrator parses the task table in `docs/plans/{feature_id}.plan.md` and dispatches workers to **Stage 3 (`workflow-build`)**.
