---
name: workflow-build
description: Stage 3 Implementation Workflow - Execute Dual-Channel parallel build slices from docs/plans/{feature_id}.plan.md concurrently across Channel A Gemini.app Desktop (max 1 heavy slice/wave with --allow-edits) and Channel B Gemini 4 Hydrogen/Neon on disjoint files
---

# Stage 3: Parallel Software Implementation Workflow

## 1. Objective & Persona
- **Persona**: `builder` (or specialized `builder-fe`, `builder-be`, `builder-db`, `ui-builder`)
- **Dual-Channel Model & Dispatch Routing** (governed by Turn-1 `preflight` & `allocate-dag`):
  - **Primary Heavy Builder Slice when `EXECUTION_MODE: HYBRID_60_DESKTOP` (`desktop_ready == true`, Max 1 per `parallel_group`)**:
    🖥️ **Channel A — `gemini-desktop-app`** (`$0.00` AGY API spend, `0` focus switches, `mode="task"`, `allow_edits=True`).
    **HARD INVARIANT**: When `desktop_ready == true`, dispatch the primary heavy builder slice (`file_count >= 4` or `complexity == "high"`, max **1** per `parallel_group`) via `run_command` (`WaitMsBeforeAsync: 500`):
    ```bash
    python3 ~/.gemini/tools/orchestrator/client.py desktop-ask \
      --task "{TASK_ID}" \
      --agent builder \
      --workspace . \
      --allow-edits \
      --prompt "Implement {TASK_ID} per docs/plans/{feature_id}.plan.md. Scope is strictly limited to {TARGET_FILES}. Run local syntax/compile checks and report exact modified files and check results."
    ```
  - **Sibling Bounded Parallel Slices (`file_count <= 3`, Concurrent in Same Turn)**:
    ⚡ **Channel B — Gemini 4 Hydrogen** (`invoke_subagent(Model="flash")`, `--model gemini-4-hydrogen`, `reasoning_effort: medium | high | xhigh`, `198 tok/s`).
  - **Additional Multi-File Slices (`file_count >= 4` spillover or `API_ONLY_100` mode)**:
    ⚡✦ **Channel B — Gemini 4 Neon** (`invoke_subagent(Model="pro")` or `"inherit"`, `--model gemini-4-neon`, `reasoning_effort: medium | high | xhigh`).
  - *(Security-sensitive builders touching auth/crypto/migrations stay strictly on Channel B `Model="pro"` **Gemini 4 Carbon**; `cost_saving` bounded slices fall back to **Gemini 3.8 Flash** `Model="flash"`.)*
  - *(**3-Stage Circuit Breaker Escalation**: Retries NEVER offload to Desktop. `retry == 1` runs on Channel B Hydrogen `Model="flash"` (`xhigh`); `retry == 2` escalates to Channel B Neon `Model="pro"`; `retry >= 3` or security impact trips hard to Channel B Carbon `Model="pro"`.)*
- **Primary Skill**: `frontend-ui-engineering` / `api-and-interface-design` / `incremental-implementation`

---

## 2. Input Contract
- **Prerequisite**: Stage 2 Plan completed, and all tasks in `depends_on` are in `completed` status (evaluated via `GET /api/dag/ready` or `python3 ~/.gemini/tools/orchestrator/client.py next-ready`).
- **Input Slice**: Specific Task ID entry from `docs/plans/{feature_id}.plan.md`.
- **Target File Boundary**: Strictly disjoint file sets per worker across Channel A and Channel B (Decoupled File Scope Invariant).

---

## 3. Execution Steps
1. **Emit Start Telemetry**:
   ```bash
   # Use --model gemini-desktop-app for Channel A primary slice, gemini-4-hydrogen for <=3f Channel B, or gemini-4-neon for >=4f Channel B
   python3 ~/.gemini/tools/orchestrator/client.py update \
     --task "{TASK_ID}" \
     --agent "builder" \
     --model "gemini-4-hydrogen" \
     --reasoning-effort "high" \
     --group "{PARALLEL_GROUP}" \
     --status "running" \
     --progress 10 \
     --scope "{TARGET_FILES}" \
     --notes "Implementing disjoint file slice"
   ```
2. **Minimal Blast-Radius Implementation**:
   - Write code strictly adhering to the architectural contracts defined in the plan.
   - Do not touch files assigned to parallel peers (across either Channel A or Channel B).
   - Run syntax and compile sanity checks locally (`python3 -m py_compile`, `tsc --noEmit`, etc.).
3. **3-Stage Fast-Retry & Circuit Breaker Handling (Channel B API Only)**:
   - **Stage 1 (`retry_count == 1`)**: `invoke_subagent(Model="flash")` on `gemini-4-hydrogen` (`--reasoning-effort xhigh`).
   - **Stage 2 (`retry_count == 2`)**: `invoke_subagent(Model="pro")` on `gemini-4-neon` (`--reasoning-effort high`).
   - **Stage 3 (`retry_count >= 3` or security impact)**: `invoke_subagent(Model="pro")` on `gemini-4-carbon` (`--reasoning-effort high`).
4. **Record Token Consumption & Progress**:
   - Update progress incrementally (e.g. 50%, 80%).
5. **Emit Completion Telemetry**:
   ```bash
   python3 ~/.gemini/tools/orchestrator/client.py update \
     --task "{TASK_ID}" \
     --agent "builder" \
     --model "gemini-4-hydrogen" \
     --reasoning-effort "high" \
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
   - **Channel / Model**: Channel A (`gemini-desktop-app`) | Channel B (`gemini-4-hydrogen` / `gemini-4-neon`)
   - **Files Modified**:
     * `path/to/file1.py`
     * `path/to/file2.ts`
   - **Syntax Verification**: `PASSED`
   ```

> **Handoff**: Once Channel A and Channel B parallel builders reach 100% and satisfy the Fan-In barrier synchronization, the Orchestrator triggers **Stage 4 (`workflow-test`)**.
