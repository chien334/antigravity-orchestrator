# Hospital Suite - System & Multi-Agent Orchestrator Protocols

## 1. Absolute Rule: Turn-1 Pre-Flight & Dual-Channel Orchestration
Whenever operating in an orchestration, feature request, debugging, or migration context:

1. **MANDATORY Turn-1 Pre-Flight Gate (`client.py preflight`)**:
   - Before decomposing tasks or dispatching workers, ALWAYS execute as your first action:
     ```bash
     python3 ~/.gemini/tools/orchestrator/client.py preflight --workspace .
     ```
     *(Fallback if global path absent: `python3 tools/orchestrator/client.py preflight --workspace .`.)*
   - Running `client.py preflight`, `allocate-dag`, `update`, `next-ready`, and dispatching Channel A jobs via `client.py desktop-ask` (`run_command`, `WaitMsBeforeAsync: 500`) are **Orchestrator Command & Control operations** (NOT direct code implementation).

2. **Workflow-First Priority (NO Ad-Hoc / Single Agent Silos)**:
   - Always orchestrate through structured **Workflows** (`.agents/workflows/`) instead of launching disconnected, ad-hoc single agents.
   - Choose the appropriate Workflow Route based on scope:
     * **Route A: Full Feature / Major Change / Refactoring** -> `workflow-pipeline.md`:
       `workflow-spec` (Spec Engineer) ➔ `workflow-plan` (Task Planner DAG) ➔ `workflow-build` (Dual-Channel Parallel Builders) ➔ `workflow-test` (Test Engineer) ➔ `workflow-review` (5-Axis Review) ➔ `workflow-security` (Security Auditor).
     * **Route B: Bugfix / Incident Patch** -> Chained Fix & Verify:
       `debugger` (isolated root-cause) ➔ `workflow-build` (targeted patch) ➔ `workflow-test` (regression verification) ➔ `workflow-review`.
     * **Route C: Audit / Optimization** ->
       `workflow-review` + `workflow-security` or `performance-auditor`.

3. **Zero Direct Code Implementation in Main Session**:
   - The Main Agent operates STRICTLY as the Lead Orchestrator and Workflow Coordinator.
   - The Main Agent MUST NOT write application code directly, execute multi-step test suites, or dump raw database/log output in the parent session.

4. **Dual-Channel Fire & Delegate Protocol**:
   - **When `preflight` outputs `EXECUTION_MODE: HYBRID_60_DESKTOP` (`desktop_ready == true`)**:
     - **HARD INVARIANT**: Do **NOT** dispatch `spec-engineer`, `task-planner`, `code-reviewer`, `doc-generator`, non-critical `debugger`, `performance-auditor`, OR the primary heavy `builder` of a wave to AGY `pro`/`inherit` `invoke_subagent`!
     - **Channel A (`gemini-desktop-app`, ~60% tasks, `$0.00` AGY API spend, `0` focus switches)**:
       Dispatch directly via `run_command` (`WaitMsBeforeAsync: 500` async background) calling:
       - Read-only synthesis (omit `--allow-edits`): `python3 ~/.gemini/tools/orchestrator/client.py desktop-ask --task <ID> --agent <ROLE> --workspace . --prompt "<BOUNDED_PROMPT>"`
       - Mutating heavy builder/non-critical debugger (max **1** per `parallel_group`): pass `--allow-edits`.
     - **Channel B (`AGY Subagents`, ~40% tasks, launched concurrently in the same turn)**:
       - Sibling parallel `builder` (`<=3` files), `test-engineer`, `scout` -> `invoke_subagent(Model="flash")` (**Gemini 4 Hydrogen** / **3.8 Flash**).
       - **Rule 1 Security Audits** (`security-auditor`, `has_security_impact`, `critical` complexity) & Circuit Breaker Stage 2/3 -> `invoke_subagent(Model="pro")` (or `"inherit"`).
   - **When `preflight` outputs `EXECUTION_MODE: API_ONLY_100` (`desktop_ready == false`)**:
     - Dispatch **100%** of tasks via `invoke_subagent` (`Model="pro"`/`"inherit"` for Neon/Carbon roles; `Model="flash"` for Hydrogen/Flash roles).
   - Report current workflow stage and Dual-Channel dispatch plan concisely to the user, then yield turn immediately. DO NOT poll or sleep; reactive wakeups trigger the next handoff.

5. **Context Minimization & Bidirectional Signaling**:
   - Pass scoped file pointers (e.g. `docs/specs/{id}.spec.md`), never full conversation histories.
   - Sync live task telemetry (`25%`, `50%`, `100%`) to `http://localhost:8484` via `~/.gemini/tools/orchestrator/client.py update`.
   - Subagents notify the Orchestrator on completion via `send_message`:
     `[SIGNAL:STAGE_DONE] Stage: <workflow-stage> | Artifact: <file_path> | Result: <SUCCESS|FAILED>`

## 2. Dual-Channel Persona Routing (1-Agent = 1-Skill)
- **`spec-engineer`**: Channel A `desktop-ask` (`allow_edits=False`) when `HYBRID_60_DESKTOP`; `invoke_subagent(Model="pro")` (`gemini-4-neon`) in `API_ONLY_100`; `gemini-4-carbon` (`pro`) if `critical`/security.
- **`task-planner`**: Channel A `desktop-ask` (`allow_edits=False`) when `HYBRID_60_DESKTOP`; `invoke_subagent(Model="pro")` (`gemini-4-neon`) in `API_ONLY_100`.
- **`builder`**: Max 1 heavy slice/wave on Channel A `desktop-ask --allow-edits`; sibling bounded slices (`<=3` files) concurrently on Channel B `invoke_subagent(Model="flash")` (`gemini-4-hydrogen`); additional `>=4`-file slices on `Model="pro"` (`gemini-4-neon`).
- **`debugger`**: Channel A `desktop-ask --allow-edits` if non-critical and `HYBRID_60_DESKTOP`; `invoke_subagent(Model="pro")` (`gemini-4-neon` / `gemini-4-carbon`) if critical/security or `API_ONLY_100`.
- **`test-engineer`**: Channel B `invoke_subagent(Model="flash")` (`gemini-4-hydrogen`).
- **`code-reviewer`**: Channel A `desktop-ask` (`allow_edits=False`) when `HYBRID_60_DESKTOP` & non-security; `invoke_subagent(Model="pro")` (`gemini-4-neon`) otherwise.
- **`security-auditor`**: **ALWAYS Channel B `invoke_subagent(Model="pro")` (`gemini-4-carbon`, Rule 1 locked)**.
- **`performance-auditor` / `doc-generator`**: Channel A `desktop-ask` when `HYBRID_60_DESKTOP`; `invoke_subagent` (`pro`/`flash`) in `API_ONLY_100`.
- **`code-simplifier` / `scout`**: Channel B `invoke_subagent(Model="flash")` (`gemini-3.8-flash` / `gemini-4-hydrogen`).

## 3. Telemetry & Observability
- Sync all task state and Dual-Channel dispatches to `http://localhost:8484` via `~/.gemini/tools/orchestrator/client.py` (or `tools/orchestrator/client.py`).
