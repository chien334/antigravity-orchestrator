---
name: workflow-build
description: Stage 3 Implementation Workflow - Execute code tasks defined in docs/plans/{feature_id}.plan.md concurrently using Gemini 4 Hydrogen (<=3 files, 198 tok/s) or Gemini 4 Neon (>=4 files, ~105 tok/s) on disjoint worker file scopes
---

# Stage 3: Parallel Software Implementation Workflow

## 1. Objective & Persona
- **Persona**: `builder` (or specialized `builder-fe`, `builder-be`, `builder-db`, `ui-builder`)
- **Model Engine**:
  - **Bounded Parallel Slices (`file_count <= 3`, Default)**: ⚡ **Gemini 4 Hydrogen** (`model: gemini-4-hydrogen`, `reasoning_effort: medium | high | xhigh`)  
    *High-throughput agentic workhorse generating code at 198 tokens/second (~2x faster than Neon without ~40s deep-thinking TTFT) with 95% cache savings ($0.075 / 1M cache tokens).*
  - **Multi-File / Complex Refactors (`file_count >= 4` or `complexity == "high"`, or `quality_first` `medium`)**: ⚡✦ **Gemini 4 Neon** (`model: gemini-4-neon`, `reasoning_effort: medium | high | xhigh`)  
    *SWE Frontier (#1 Coding Agent `58.64`, CursorBench `65.4%`) preventing cross-file contract drift on larger refactors.*
  *(Fallback to ⚡ **Gemini 3.8 Flash** (`low`) in `cost_saving` mode).*  
  *(**3-Stage Circuit Breaker Escalation**: If an implementation attempt fails, allow 1 fast self-healing turn on Hydrogen with `effort: xhigh` (`retry_count == 1`). If still failing at `retry_count == 2`, escalate to ⚡✦ **Gemini 4 Neon** (`effort: high`, or `xhigh` if `complexity == "high"`). If failures persist at `retry_count >= 3` or if modifying security-sensitive cryptographic logic/core auth, trip the circuit breaker hard to ✦ **Gemini 4 Carbon** with `reasoning_effort: high`).*
- **Primary Skill**: `frontend-ui-engineering` / `api-and-interface-design` / `incremental-implementation`

---

## 2. Input Contract
- **Prerequisite**: Stage 2 Plan completed, and all tasks in `depends_on` are in `completed` status (evaluated via `GET /api/dag/ready` or `python3 packages/orchestrator/client.py next-ready`).
- **Input Slice**: Specific Task ID entry from `docs/plans/{feature_id}.plan.md`.
- **Target File Boundary**: Bounded parallel slices target 1–3 disjoint files on `gemini-4-hydrogen`; multi-file refactors touching `>= 4` files route to `gemini-4-neon` (Decoupled File Scope Invariant).

---

## 3. Execution Steps
1. **Emit Start Telemetry**:
   ```bash
   # Use --model gemini-4-hydrogen for <=3 files, or --model gemini-4-neon for >=4 files / high complexity
   python3 packages/orchestrator/client.py update \
     --task "{TASK_ID}" \
     --agent "builder" \
     --model "gemini-4-hydrogen" \
     --reasoning-effort "high" \
     --group "{PARALLEL_GROUP}" \
     --status "running" \
     --progress 10 \
     --scope "{TARGET_FILES}" \
     --notes "Implementing component/logic at 198 tok/sec with Gemini 4 Hydrogen"
   ```
2. **Minimal Blast-Radius Implementation**:
   - Write code strictly adhering to the architectural contracts defined in the plan.
   - Do not touch files assigned to parallel peers.
   - Run syntax and compile sanity checks locally (`python3 -m py_compile`, `tsc --noEmit`, etc.).
3. **3-Stage Fast-Retry & Circuit Breaker Handling**:
   - **Stage 1 (`retry_count == 1`)**: Execute **1 fast self-correction turn** on `gemini-4-hydrogen` (`--reasoning-effort xhigh`).
   - **Stage 2 (`retry_count == 2`)**: Escalate to **Gemini 4 Neon** (`--model gemini-4-neon --reasoning-effort high`, or `xhigh` if `complexity == "high"`).
   - **Stage 3 (`retry_count >= 3` or security impact)**: Announce circuit breaker hard trip and escalate to **Gemini 4 Carbon** (`--model gemini-4-carbon --reasoning-effort high`).
4. **Record Token Consumption & Progress**:
   - Update progress incrementally (e.g. 50%, 80%).
5. **Emit Completion Telemetry**:
   ```bash
   python3 packages/orchestrator/client.py update \
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
   - **Model**: `gemini-4-hydrogen` (effort: high)
   - **Files Modified**:
     * `path/to/file1.py`
     * `path/to/file2.ts`
   - **Syntax Verification**: `PASSED`
   ```

> **Handoff**: Once all parallel builders reach 100% and satisfy the Fan-In barrier synchronization, the Orchestrator triggers **Stage 4 (`workflow-test`)**.
