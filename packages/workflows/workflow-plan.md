---
name: workflow-plan
description: Stage 2 Planning Workflow - Ingest docs/specs/{feature_id}.spec.md, design architecture & Dual-Channel 60/40 DAG via Channel A Gemini.app Desktop (when HYBRID_60_DESKTOP) or Channel B Gemini 4 Neon fallback, producing docs/plans/{feature_id}.plan.md
---

# Stage 2: Architecture & Task DAG Planning Workflow

## 1. Objective & Persona
- **Persona**: `task-planner`
- **Dual-Channel Model & Dispatch Routing** (governed by Turn-1 `python3 ~/.gemini/tools/orchestrator/client.py preflight --workspace .`):
  - **When `EXECUTION_MODE: HYBRID_60_DESKTOP` (`desktop_ready == true`, Default)**:
    🖥️ **Channel A — `gemini-desktop-app`** (`$0.00` AGY API spend, `0` focus switches, `mode="task"`, `allow_edits=False` — omit `--allow-edits`).
    **HARD INVARIANT**: Do **NOT** dispatch `task-planner` to an AGY `pro`/`inherit` `invoke_subagent` when `desktop_ready == true`! Dispatch via `run_command` (`WaitMsBeforeAsync: 500`):
    ```bash
    python3 ~/.gemini/tools/orchestrator/client.py desktop-ask \
      --task "PLAN-{FEATURE}" \
      --agent task-planner \
      --workspace . \
      --output "docs/reports/desktop_worker/PLAN-{FEATURE}.md" \
      --prompt "Read docs/specs/{feature_id}.spec.md. Design system topology, schemas, interface signatures, and a Dual-Channel 60/40 Task DAG with disjoint file scopes (max 1 heavy builder per parallel_group on gemini-desktop-app) for docs/plans/{feature_id}.plan.md. Read-only synthesis only."
    ```
  - **When `EXECUTION_MODE: API_ONLY_100` (`desktop_ready == false`)**:
    ⚡✦ **Channel B — Gemini 4 Neon** (`invoke_subagent(Model="pro")` or `"inherit"`, `--model gemini-4-neon`, `reasoning_effort: medium | high`).  
    *(Escalate to ✦ **Gemini 4 Carbon** via `invoke_subagent(Model="pro")` if modeling critical cryptographic/security architecture or executing `quality_first` critical planning.)*
- **Primary Skill**: `planning-and-task-breakdown` & `api-and-interface-design` *(+ `gemini-desktop-worker` when Channel A Desktop is active)*

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
   # Use --model gemini-desktop-app in HYBRID_60_DESKTOP mode, or --model gemini-4-neon in API_ONLY_100 mode
   python3 ~/.gemini/tools/orchestrator/client.py update \
     --task "PLAN-{FEATURE}" \
     --agent "task-planner" \
     --model "gemini-desktop-app" \
     --complexity "high" \
     --status "running" \
     --progress 20 \
     --scope "docs/specs/{feature_id}.spec.md" \
     --notes "Designing system contracts and Dual-Channel 60/40 Task DAG"
   ```
2. **Architecture & Contract Modeling**: Define database schema, API signatures, and data contracts between modules.
3. **DAG Breakdown & Dual-Channel 60/40 Model Allocation**:
   - Split tasks into minimal blast-radius units.
   - Assign `parallel_group` to tasks that operate on disjoint files (Decoupled File Scope Invariant).
   - Tag prerequisite dependencies using `depends_on`.
   - Allocate models with `python3 ~/.gemini/tools/orchestrator/client.py allocate-dag --target-desktop-share 0.60 --apply`:
     * 🖥️ **Channel A (`gemini-desktop-app`, ~60% share when `desktop_ready == true`)**: Sequential heavy stages (`spec-engineer`, `task-planner`, `code-reviewer`, `doc-generator`, non-critical `debugger`, `performance-auditor`) with `allow_edits=False`, PLUS **at most 1 primary heavy `builder` per `parallel_group`** with `allow_edits=True` (`--allow-edits`) on strictly disjoint files (ensuring `Gemini.app`'s single-window FIFO lock never blocks concurrent siblings).
     * ✦ **Tier 1 (`gemini-4-carbon`, `Model="pro"`)**: Rule 1 security audits (`security-auditor`), auth/authz, OWASP/CVE/migrations, and Circuit Breaker Stage 3 (`retry_count >= 3`, `effort: high`). Never offloaded to Desktop.
     * ⚡✦ **Tier 1.5 / 2 (`gemini-4-neon`, `Model="pro"`/`"inherit"`)**: `API_ONLY_100` fallback / Desktop spillover for specs, plans, 5-axis reviews, debugging, multi-file builders (`>= 4` files), and CB Stage 2 (`retry_count == 2`).
     * ⚡ **Tier 3 (`gemini-4-hydrogen`, `Model="flash"`)**: Sibling bounded parallel builders (`<= 3` files), `test-engineer`, and `scout` at 198 tok/sec (`effort: medium`/`high`/`xhigh`).
     * ⚡ **Tier 4 (`gemini-3.8-flash`, `Model="flash"`)**: Cost-first bulk scaffolding, simplification, and micro-telemetry (`API_ONLY_100` fallback).
   - Define 3-Stage Fast-Retry Circuit Breaker thresholds (`retry == 1` Hydrogen `xhigh` ➔ `retry == 2` Neon `high`/`xhigh` ➔ `retry >= 3` Carbon `high`).
4. **Artifact Generation**: Produce `docs/plans/{feature_id}.plan.md`.
5. **Emit Completion Telemetry**:
   ```bash
   python3 ~/.gemini/tools/orchestrator/client.py update \
     --task "PLAN-{FEATURE}" \
     --agent "task-planner" \
     --model "gemini-desktop-app" \
     --status "completed" \
     --progress 100 \
     --scope "docs/plans/{feature_id}.plan.md" \
     --notes "Plan DAG finalized with Dual-Channel 60/40 allocation, disjoint worker slices, and 3-Stage Circuit Breaker"
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

## 2. Disjoint File Scope Allocation (Dual-Channel 60/40)
| Task ID | Persona | Channel & Model (`HYBRID_60_DESKTOP`) | `API_ONLY_100` Fallback | Parallel Group | Depends On | Disjoint Target Files |
|---|---|---|---|---|---|---|
| `BUILD-01` | `builder` | 🖥️ Ch-A: `gemini-desktop-app` (`--allow-edits`) | `gemini-4-neon` (`pro`) | `BUILD-PARALLEL` | `PLAN-{FEATURE}` | `src/core/{a,b,c,d}.py` (`>=4` files) |
| `BUILD-02` | `builder` | ⚡ Ch-B: `gemini-4-hydrogen` (`flash`) | `gemini-4-hydrogen` (`flash`) | `BUILD-PARALLEL` | `PLAN-{FEATURE}` | `src/frontend/ViewA.tsx` (`<=3` files) |
| `BUILD-03` | `builder` | ⚡ Ch-B: `gemini-4-hydrogen` (`flash`) | `gemini-4-hydrogen` (`flash`) | `BUILD-PARALLEL` | `PLAN-{FEATURE}` | `src/backend/ServiceB.py` (`<=3` files) |
| `TEST-01`  | `test-engineer` | ⚡ Ch-B: `gemini-4-hydrogen` (`flash`) | `gemini-4-hydrogen` (`flash`) | - | `BUILD-01, BUILD-02, BUILD-03` | `tests/test_feature.py` |

## 3. 3-Stage Circuit Breaker Policy
- **Stage 1 (`retry_count == 1`)**: `gemini-4-hydrogen` (`flash`, `xhigh` effort)
- **Stage 2 (`retry_count == 2`)**: `gemini-4-neon` (`pro`, `high` / `xhigh` effort)
- **Stage 3 (`retry_count >= 3`)**: `gemini-4-carbon` (`pro`, `high` effort)
```

> **Handoff**: The approved plan unblocks Stage 3 concurrent Dual-Channel builders evaluated via `python3 ~/.gemini/tools/orchestrator/client.py next-ready`.
