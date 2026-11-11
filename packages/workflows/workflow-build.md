---
name: workflow-build
description: Stage 3 Implementation Workflow - Execute code tasks defined in docs/plans/{feature_id}.plan.md concurrently using disjoint worker file scopes
---

# Stage 3: Parallel Software Implementation Workflow

## 1. Objective & Persona
- **Persona**: `builder` (or specialized `builder-fe`, `builder-be`, `builder-db`)
- **Model Engine**: ⚡ **Gemini 3.8 Flash** (`model: gemini-3.8-flash`, cost-efficient high-throughput)  
  *(Dynamically escalate to ✦ **Gemini 4 Carbon** with `reasoning_effort: high` if implementing security-sensitive cryptographic logic, core authorization tokens, or critical database schema migrations).*
- **Primary Skill**: `frontend-ui-engineering` / `api-and-interface-design` / `incremental-implementation`

---

## 2. Input Contract
- **Prerequisite**: Stage 2 Plan completed, and all tasks in `depends_on` are in `completed` status (evaluated via `GET /api/dag/ready` or `python3 packages/orchestrator/client.py next-ready`).
- **Input Slice**: Specific Task ID entry from `docs/plans/{feature_id}.plan.md`.
- **Target File Boundary**: Strictly constrained to the 1-3 files listed in the task definition (Decoupled File Scope Invariant).

---

## 3. Execution Steps
1. **Emit Start Telemetry**:
   ```bash
   python3 packages/orchestrator/client.py update \
     --task "{TASK_ID}" \
     --agent "builder" \
     --model "gemini-3.8-flash" \
     --group "{PARALLEL_GROUP}" \
     --status "running" \
     --progress 10 \
     --scope "{TARGET_FILES}" \
     --notes "Implementing component/logic according to plan"
   ```
2. **Minimal Blast-Radius Implementation**:
   - Write code strictly adhering to the architectural contracts defined in the plan.
   - Do not touch files assigned to parallel peers.
   - Run syntax and compile sanity checks locally (`python3 -m py_compile`, `tsc --noEmit`, etc.).
3. **Record Token Consumption & Progress**:
   - Update progress incrementally (e.g. 50%, 80%).
4. **Emit Completion Telemetry**:
   ```bash
   python3 packages/orchestrator/client.py update \
     --task "{TASK_ID}" \
     --agent "builder" \
     --model "gemini-3.8-flash" \
     --group "{PARALLEL_GROUP}" \
     --status "completed" \
     --progress 100 \
     --input-tokens {IN_TOK} \
     --output-tokens {OUT_TOK} \
     --cache-tokens {CACHE_TOK} \
     --scope "{TARGET_FILES}" \
     --notes "Implementation complete, passed syntax check"
   ```

---

## 4. Output Contract (Artifact Schema)
- **Source Code**: Modified and new files on disk.
- **Worker Completion Handoff**:
   ```markdown
   ### Worker Handoff: {TASK_ID}
   - **Status**: COMPLETED
   - **Files Modified**:
     * `path/to/file1.py`
     * `path/to/file2.ts`
   - **Syntax Verification**: `PASSED`
   ```

> **Handoff**: Once all parallel builders reach 100% and satisfy the Fan-In barrier synchronization, the Orchestrator triggers **Stage 4 (`workflow-test`)**.
