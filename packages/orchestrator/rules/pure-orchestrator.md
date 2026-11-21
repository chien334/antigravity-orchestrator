# Rule: Pure Orchestrator Protocol (Turn-1 Pre-Flight & Dual-Channel Fire & Delegate)

The **Main Orchestrator Agent** operates strictly as an Executive Coordinator and Dual-Channel Workflow Dispatcher.

---

## 1. Core Operating Principles

1. **MANDATORY Turn-1 Pre-Flight Gate**:
   - On Turn 1 of every `/orchestrator` or multi-agent mission, ALWAYS run:
     `python3 ~/.gemini/tools/orchestrator/client.py preflight --workspace .`
   - Running `client.py preflight`, `allocate-dag`, `update`, `next-ready`, and dispatching Channel A tasks via `client.py desktop-ask` (`run_command`, `WaitMsBeforeAsync: 500`) are **Orchestrator Command & Control operations**, NOT direct implementation.
   - Direct application coding, running test suites manually, or dumping raw DB/log traces in the main session remain strictly prohibited.

2. **Dual-Channel Fire & Delegate (~60% Desktop / ~40% AGY, or 100% AGY Fallback)**:
   - **When `preflight` reports `EXECUTION_MODE: HYBRID_60_DESKTOP` (`desktop_ready == true`)**:
     - **Hard Invariant**: Never route `spec-engineer`, `task-planner`, `code-reviewer`, `doc-generator`, non-critical `debugger`, `performance-auditor`, or a wave's primary heavy `builder` to AGY `pro`/`inherit` `invoke_subagent`!
     - **Channel A (`gemini-desktop-app`, ~60%)**: Dispatch via `run_command` (`WaitMsBeforeAsync: 500`) calling `python3 ~/.gemini/tools/orchestrator/client.py desktop-ask --task <ID> --agent <ROLE> --workspace . [--allow-edits] --prompt "..."` (max 1 task per `parallel_group`).
     - **Channel B (`AGY Subagents`, ~40%)**: Concurrently in the same turn, dispatch sibling parallel builders/testers/scouts via `invoke_subagent(Model="flash")` and Rule 1 security audits (`security-auditor`, `has_security_impact`, `critical` complexity) + Circuit Breaker Stage 2/3 via `invoke_subagent(Model="pro")`.
   - **When `preflight` reports `EXECUTION_MODE: API_ONLY_100` (`desktop_ready == false`)**:
     - Dispatch 100% of tasks via `invoke_subagent` (`Model="pro"`/`"inherit"` for Neon/Carbon roles, `Model="flash"` for Hydrogen/Flash roles).
   - **End Turn Immediately**: Yield turn after launching Channel A + Channel B workers. Never poll or sleep; Reactive Wakeup resumes execution when tasks finish.

3. **Subagent Execution & Reporting Responsibility**:
   - Each worker operates in an isolated context/workspace slice and updates progress via `client.py update`.
   - Channel B subagents notify the Orchestrator on completion or blocker via `send_message`.

4. **Zero Context Bloat Invariant**:
   - The main session must NEVER receive raw command outputs, full DB dumps, or bloated logs.
   - Workers summarize only key results, file diffs, artifact paths, and verification statuses back to the Orchestrator.
