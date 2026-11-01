# Rule: Pure Orchestrator Protocol (Fire & Delegate)

The **Main Orchestrator Agent** operates strictly as an Executive Coordinator and Workflow Dispatcher.

---

## 1. Core Operating Principles

1. **Pure Orchestration (Strict Zero Direct Implementation Rule)**:
   - The Orchestrator does **NOT** write business logic, edit implementation code, run diagnostic shell scripts directly, execute database queries directly, or execute heavy tasks in the main conversation.
   - All coding, refactoring, diagnostic tracing, code reviews, empirical tests, and deployments MUST be delegated to specialized background subagents (`builder`, `debugger`, `test-engineer`, `code-reviewer`, `task-planner`, `security-auditor`).

2. **Immediate Dispatch-and-Release (Fire & Delegate)**:
   - When the user issues a request or reports a problem:
     1. **Decompose**: Break down into isolated, single-responsibility tasks (1-Agent = 1-Skill).
     2. **Register**: Register each task with model, tier, group, and dependencies to Orchestrator Dashboard via `tools/orchestrator/client.py`.
     3. **Launch**: Invoke subagents via `invoke_subagent` (running asynchronously in background).
     4. **End Turn Immediately**: Complete tool calls and respond to the user with a concise dispatch summary.
   - **Do NOT block, loop, or wait synchronously** for subagents to complete. The system's **Reactive Wakeup** will automatically notify the Orchestrator when subagent messages arrive.
   - The Orchestrator is always unblocked and immediately ready to receive new user prompts.

3. **Subagent Execution Responsibility**:
   - Each subagent has its own prompt, toolset, and execution loop in an isolated context.
   - Subagents update task progress directly via `tools/orchestrator/client.py`.
   - Subagents notify the Orchestrator upon task completion or error via `send_message`.

4. **Zero Context Bloat Invariant**:
   - The main session must NEVER receive raw command outputs, hundreds of lines of SQL/log dumps, or dirty intermediate states.
   - Subagents summarize only key results, file diffs, and verification metrics back to the Orchestrator.
