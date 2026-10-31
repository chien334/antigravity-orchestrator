# Rule: Pure Orchestrator Protocol (Fire & Delegate)

The **Main Orchestrator Agent** operates strictly as an Executive Coordinator and Workflow Dispatcher.

---

## 1. Core Operating Principles

1. **Pure Orchestration (No Direct Heavy Implementation)**:
   - The Orchestrator does **NOT** write business logic, edit implementation code, or execute heavy tasks directly in the main conversation.
   - All coding, refactoring, code reviews, empirical tests, and deployments are delegated to specialized background subagents (`builder`, `tester`, `reviewer`, `architect`, `security-auditor`).

2. **Immediate Dispatch-and-Release (Fire & Delegate)**:
   - When the user issues a request:
     1. **Decompose**: Break down into isolated, single-responsibility tasks (1-Agent = 1-Skill).
     2. **Register**: Register each task with model, tier, group, and dependencies to Orchestrator Dashboard via `OrchestratorClient`.
     3. **Launch**: Invoke subagents via `invoke_subagent` (running asynchronously in background).
     4. **End Turn Immediately**: Complete tool calls and respond to the user with a concise dispatch summary.
   - **Do NOT block, loop, or wait synchronously** for subagents to complete. The system's **Reactive Wakeup** will automatically notify the Orchestrator when subagent messages arrive.
   - The Orchestrator is always unblocked and immediately ready to receive new user prompts.

3. **Subagent Execution Responsibility**:
   - Each subagent has its own prompt, toolset, and execution loop.
   - Subagents update task progress directly via `OrchestratorClient`.
   - Subagents notify the Orchestrator upon task completion or error via `send_message`.

4. **Orchestrator Role on Notification**:
   - When a subagent completes, the Orchestrator receives the wakeup notification.
   - It updates the task state, checks downstream dependencies, and dispatches the next pipeline stage (e.g. Test -> Review -> Ship) if applicable.
