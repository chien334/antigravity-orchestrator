---
name: workflow-plan
description: Stage 2 Planning Workflow - Ingest docs/specs/{feature_id}.spec.md, design architecture, schemas, and produce docs/plans/{feature_id}.plan.md with Gemini 4 Neon & Periodic Table Model DAG
---

# Stage 2: Architecture & Task DAG Planning Workflow

## 1. Objective & Persona
- **Persona**: `task-planner`
- **Model Engine**: ⚡✦ **Gemini 4 Neon** (`model: gemini-4-neon`, `reasoning_effort: medium | high`)  
  *Supersedes `gemini-4-argon` with Coding Agent Index #1 (`58.64`), Intelligence `61`, `~105 tok/s` (2x Argon speed), and 95% cache savings (`$0.15 / 1M` cache).*  
  *(Escalate to ✦ **Gemini 4 Carbon** if modeling critical cryptographic/security architecture or executing high-stakes `quality_first` planning).*  
  *(Optional `hybrid_desktop` Offload: Heavy read-only architecture synthesis or design trade-off second-opinions may be offloaded to `gemini-desktop-app` via `client.py desktop-ask` (`$0.00` AGY API spend) after `SecretRedactor` scrubbing, returning the `docs/reports/desktop_worker/{job_id}.md` pointer to `task-planner`.)*
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
     --model "gemini-4-neon" \
     --effort "medium" \
     --complexity "high" \
     --status "running" \
     --progress 20 \
     --scope "docs/specs/{feature_id}.spec.md" \
     --notes "Designing system contracts and Periodic Table SWE task DAG with Gemini 4 Neon"
   ```
2. **Architecture & Contract Modeling**: Define database schema, API signatures, and data contracts between modules.
3. **DAG Breakdown & Periodic Table Model Allocation**:
   - Split tasks into minimal blast-radius units.
   - Assign `parallel_group` to tasks that operate on disjoint files (Decoupled File Scope Invariant).
   - Tag prerequisite dependencies using `depends_on`.
   - Allocate models according to the Periodic Table SWE Fleet taxonomy:
     * **Tier 1 (`gemini-4-carbon`)**: Critical security, auth/authz, OWASP/CVE/migrations, and Circuit Breaker Stage 3 (`retry_count >= 3`, `effort: high`).
     * **Tier 1.5 / 2 (`gemini-4-neon`)**: Orchestration (`gemini-pro-orchestrator-neon`), non-security specs, architecture design, schema contracts, 5-axis reviews, debugging, multi-file builders (`>= 4` files), and CB Stage 2 (`retry_count == 2`, `effort: medium`/`high`/`xhigh`). *(Replaces `gemini-4-argon`, which remains legacy/fallback only).*
     * **Tier 3 (`gemini-4-hydrogen`)**: Bounded parallel code implementation (`<= 3` files), automated testing, and codebase scouting at 198 tok/sec (`effort: medium`/`high`/`xhigh`).
     * **Tier 4 (`gemini-3.8-flash`, `low`)**: Cost-first bulk scaffolding, doc formatting, text simplification, and active telemetry/linting (replaces absent `gemini-3.8-flash-lite` default).
     * **External Offload (`gemini-desktop-app`, `hybrid_desktop`)**: Heavy non-mutating synthesis/critique only (`read_only=True`, `file_count=0`, `has_security_impact=False`), drained sequentially via `desktop_jobs` while Stage 3 `gemini-4-hydrogen` builders execute file edits in parallel. Never assign file-writing or test-running tasks to `gemini-desktop-app`.
   - Define 3-Stage Fast-Retry Circuit Breaker thresholds (`retry == 1` Hydrogen `xhigh` ➔ `retry == 2` Neon `high`/`xhigh` ➔ `retry >= 3` Carbon `high`).
4. **Artifact Generation**: Produce `docs/plans/{feature_id}.plan.md`.
5. **Emit Completion Telemetry**:
   ```bash
   python3 packages/orchestrator/client.py update \
     --task "PLAN-{FEATURE}" \
     --agent "task-planner" \
     --model "gemini-4-neon" \
     --effort "medium" \
     --status "completed" \
     --progress 100 \
     --scope "docs/plans/{feature_id}.plan.md" \
     --notes "Plan DAG finalized with parallel worker slots, Neon/Hydrogen assignments, and 3-Stage Circuit Breaker"
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
| `BUILD-01` | `builder` | `gemini-4-hydrogen` | `BUILD-PARALLEL` | `PLAN-{FEATURE}` | `src/frontend/ViewA.tsx` (`<=3` files) |
| `BUILD-02` | `builder` | `gemini-4-hydrogen` | `BUILD-PARALLEL` | `PLAN-{FEATURE}` | `src/backend/ServiceB.py` (`<=3` files) |
| `BUILD-03` | `builder` | `gemini-4-neon` | `BUILD-PARALLEL` | `PLAN-{FEATURE}` | `src/core/{a,b,c,d}.py` (`>=4` files) |
| `TEST-01`  | `test-engineer` | `gemini-4-hydrogen` | - | `BUILD-01, BUILD-02, BUILD-03` | `tests/test_feature.py` |

## 3. 3-Stage Circuit Breaker Policy
- **Stage 1 (`retry_count == 1`)**: `gemini-4-hydrogen` (`xhigh` effort)
- **Stage 2 (`retry_count == 2`)**: `gemini-4-neon` (`high` / `xhigh` effort)
- **Stage 3 (`retry_count >= 3`)**: `gemini-4-carbon` (`high` effort)
```

> **Handoff**: The approved plan unblocks Stage 3 parallel builders evaluated via `GET /api/dag/ready`.
