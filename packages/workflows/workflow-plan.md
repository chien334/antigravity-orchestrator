---
name: workflow-plan
description: Stage 2 Planning Workflow - Ingest docs/specs/{feature_id}.spec.md, design architecture, schemas, and produce docs/plans/{feature_id}.plan.md with 5-Tier Model DAG
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
  * Pointers to existing code, database schemas, and configuration (gathered via fast `gemini-4-hydrogen` scouts under the Scout-Then-Architect topology).
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
     --notes "Designing system contracts and 5-Tier Periodic Table task DAG"
   ```
2. **Architecture & Contract Modeling**: Define database schema, API signatures, and data contracts between modules.
3. **DAG Breakdown & 5-Tier Model Allocation**:
   - Split tasks into minimal blast-radius units.
   - Assign `parallel_group` to tasks that operate on disjoint files (Decoupled File Scope Invariant).
   - Tag prerequisite dependencies using `depends_on`.
   - Allocate models according to the 5-Tier Periodic Table taxonomy:
     * **Tier 1 (`gemini-4-carbon`)**: Critical security, auth/authz, complex cryptographic models (`effort: high`).
     * **Tier 2 (`gemini-4-argon`)**: Architecture design, schema contracts, reviews (`effort: medium`/`high`).
     * **Tier 3 (`gemini-4-hydrogen`)**: Parallel code implementation, automated testing, and codebase scouting at 198 tok/sec (`effort: medium`/`high`/`xhigh`).
     * **Tier 4 (`gemini-3.8-flash`)**: Cost-first bulk scaffolding, doc formatting, and text simplification.
     * **Tier 5 (`gemini-3.8-flash-lite`)**: Micro-tier telemetry, docs, and linting.
   - Define Fast-Retry Circuit Breaker thresholds (`retry_count >= 2` escalates to Carbon).
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
     --notes "Plan DAG finalized with parallel worker slots, 5-tier model assignments, and Circuit Breaker policies"
   ```

---

## 4. Output Contract (Artifact Schema)
Save to: `docs/plans/{feature_id}.plan.md`

```markdown
# Architectural Plan: {Feature Name}

## 1. System Topology & Contracts
- **Module Boundaries**: ...
- **Database Schema Changes**: ...
- **Interface Signatures**: ...

## 2. Disjoint File Scope Allocation
| Task ID | Persona | Assigned Model | Parallel Group | Depends On | Disjoint Target Files |
|---|---|---|---|---|---|
| `BUILD-01` | `builder` | `gemini-4-hydrogen` | `BUILD-PARALLEL` | `PLAN-{FEATURE}` | `src/frontend/ViewA.tsx` |
| `BUILD-02` | `builder` | `gemini-4-hydrogen` | `BUILD-PARALLEL` | `PLAN-{FEATURE}` | `src/backend/ServiceB.py` |
| `TEST-01`  | `test-engineer` | `gemini-4-hydrogen` | - | `BUILD-01, BUILD-02` | `tests/test_feature.py` |

## 3. Circuit Breaker Policy
- **Max Self-Retries**: 1 on `gemini-4-hydrogen` (`xhigh` effort)
- **Escalation Target**: `gemini-4-carbon` (`high` effort)
```

> **Handoff**: The approved plan unblocks Stage 3 parallel builders evaluated via `GET /api/dag/ready`.
