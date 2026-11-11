---
name: workflow-plan
description: Stage 2 Planning Workflow - Ingest docs/specs/{feature_id}.spec.md, design architecture, schemas, and produce docs/plans/{feature_id}.plan.md with 4-Tier Model DAG
---

# Stage 2: Architecture & Task DAG Planning Workflow

## 1. Objective & Persona
- **Persona**: `task-planner`
- **Model Engine**: ✦ **Gemini 4 Argon** (`model: gemini-4-argon`, `reasoning_effort: high` / `medium`)  
  *(Escalate to ✦ **Gemini 4 Carbon** if executing in `quality_first` mode or modeling critical cryptographic/security architecture).*
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
   python3 packages/orchestrator/client.py update \
     --task "PLAN-{FEATURE}" \
     --agent "task-planner" \
     --model "gemini-4-argon" \
     --effort "high" \
     --complexity "high" \
     --status "running" \
     --progress 20 \
     --scope "docs/specs/{feature_id}.spec.md" \
     --notes "Designing system contracts and 4-tier task DAG"
   ```
2. **Architecture & Contract Modeling**: Define database schema, API signatures, and data contracts between modules.
3. **DAG Breakdown & 4-Tier Model Allocation**:
   - Split tasks into minimal blast-radius units.
   - Assign `parallel_group` to tasks that operate on disjoint files (Decoupled File Scope Invariant).
   - Tag prerequisite dependencies using `depends_on`.
   - Allocate models according to the 4-tier taxonomy:
     * **Tier 1 (`gemini-4-carbon`)**: Critical security, auth/authz, complex cryptographic models (`effort: high`).
     * **Tier 2 (`gemini-4-argon`)**: Architecture design, schema contracts, reviews (`effort: medium`).
     * **Tier 3 (`gemini-3.8-flash`)**: Parallel code implementation and unit testing (>70% cost savings).
     * **Tier 4 (`gemini-3.8-flash-lite`)**: Micro-tier telemetry, docs, and linting.
4. **Artifact Generation**: Produce `docs/plans/{feature_id}.plan.md`.
5. **Emit Completion Telemetry**:
   ```bash
   python3 packages/orchestrator/client.py update \
     --task "PLAN-{FEATURE}" \
     --agent "task-planner" \
     --model "gemini-4-argon" \
     --effort "high" \
     --status "completed" \
     --progress 100 \
     --scope "docs/plans/{feature_id}.plan.md" \
     --notes "Plan DAG finalized with parallel worker slots and 4-tier model assignments"
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
- File boundary allocations (strictly disjoint for parallel builders).

## 2. Directed Acyclic Graph (DAG) & Task Matrix

| Task ID | Description | Target Files | Model | Reasoning Effort | Complexity | Depends On | Parallel Group |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **BUILD-01** | Backend Schema & DB Migration | `backend/models/...` | ⚡ Flash | - | `medium` | `[]` | `BUILD-PARALLEL` |
| **BUILD-02** | Frontend Component & UI | `frontend/src/...` | ⚡ Flash | - | `medium` | `[]` | `BUILD-PARALLEL` |
| **BUILD-03** | REST API Route Handler | `backend/api/...` | ⚡ Flash | - | `medium` | `["BUILD-01"]` | `BUILD-PARALLEL` |
| **TEST-01** | Unit & Integration Test Suite | `tests/...` | ⚡ Flash | - | `medium` | `["BUILD-02", "BUILD-03"]` | - |
| **REVIEW-01** | 5-Axis Code Review | All modified files | ✦ Argon | `high` | `high` | `["TEST-01"]` | - |
| **SEC-01** | Security & OWASP Audit | All modified files | ✦ Carbon | `high` | `critical` | `["REVIEW-01"]` | - |

## 3. Barrier Synchronization Criteria
- Conditions required before advancing to Testing and Code Review.
```

> **Handoff**: The Orchestrator queries `python3 packages/orchestrator/client.py next-ready` (or `GET /api/dag/ready`) to evaluate unblocked tasks in `docs/plans/{feature_id}.plan.md` and dispatches workers to **Stage 3 (`workflow-build`)**.
