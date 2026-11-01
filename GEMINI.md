# Hospital Suite - System & Multi-Agent Orchestrator Protocols

## 1. Absolute Rule: Workflow-First & Pure Orchestration
Whenever operating in an orchestration, feature request, debugging, or migration context:

1. **Workflow-First Priority (NO Ad-Hoc / Single Agent Silos)**:
   - Always orchestrate through structured **Workflows** (`.agents/workflows/`) instead of launching disconnected, ad-hoc single agents.
   - Workflows enforce end-to-end quality gates, artifact handoffs (file pointers like `.spec.md`, `.plan.md`, `test_report.json`), and clean boundaries.
   - Choose the appropriate Workflow Route based on scope:
     * **Route A: Full Feature / Major Change / Refactoring** -> `workflow-pipeline.md`:
       `workflow-spec` (Spec Engineer) ➔ `workflow-plan` (Task Planner DAG) ➔ `workflow-build` (Parallel Builders) ➔ `workflow-test` (Test Engineer) ➔ `workflow-review` (5-Axis Review) ➔ `workflow-security` (Security Auditor).
     * **Route B: Bugfix / Incident Patch** -> Chained Fix & Verify:
       `debugger` (isolated root-cause) ➔ `workflow-build` (targeted patch) ➔ `workflow-test` (regression verification) ➔ `workflow-review`.
     * **Route C: Audit / Optimization** ->
       `workflow-review` + `workflow-security` or `performance-auditor`.

2. **Zero Direct Heavy Implementation in Main Session**:
   - The Main Agent operates STRICTLY as the Lead Orchestrator and Workflow Coordinator.
   - The Main Agent MUST NOT write implementation code directly, run multi-step terminal investigations, execute raw database dumps, or run test suites in the parent session.
   - All tasks within the active workflow MUST be delegated to specialized background subagents via `invoke_subagent`.

3. **Immediate Dispatch-and-Release (Fire & Delegate)**:
   - When a workflow stage is triggered:
     1. Pass scoped file pointers (e.g. `docs/specs/{id}.spec.md`), never full conversational history.
     2. Register/update task in Orchestrator Dashboard (`http://localhost:8484` via `tools/orchestrator/client.py`).
     3. Dispatch subagent(s) immediately using `invoke_subagent`.
     4. Report current workflow stage and dispatch plan concisely to the user, then yield turn. DO NOT poll or sleep.
   - Reactive wakeups will automatically notify the Orchestrator when a workflow stage completes, triggering the next handoff.

4. **Context Minimization & Anti-Bloat Invariant**:
   - NEVER dump massive raw logs, full SQL table schemas, or raw outputs into the main conversation.
   - Subagents run in their own isolated context/worktree. They must return ONLY high-level summaries, root causes, file diffs, and verification statuses.
   - Artifacts are saved to disk (`docs/specs/`, `docs/plans/`, `docs/reports/`) so subsequent stages can read them directly without bloating conversation tokens.

5. **Bidirectional Signaling Protocol (Tín hiệu Subagent ➔ Orchestrator)**:
   - **Progress & Heartbeat Signal (SSE Live Stream)**: Trong quá trình xử lý, subagent phát tín hiệu tiến độ thời gian thực (25%, 50%, 75%, 100%) lên Orchestrator Dashboard (`http://localhost:8484`) qua:
     `python3 tools/orchestrator/client.py update <TASK_ID> --status <running|completed|failed> --progress <N> --notes "<Message>"`
   - **Reactive Wakeup Signal (`send_message`)**: Khi một Stage hoàn thành hoặc gặp blocker, subagent **BẮT BUỘC** phát tín hiệu trực tiếp về Orchestrator qua công cụ `send_message`:
     `[SIGNAL:STAGE_DONE] Stage: <workflow-stage> | Artifact: <file_path> | Result: <SUCCESS|FAILED>`
   - Tín hiệu này kích hoạt cơ chế **Reactive Wakeup**, tự động đánh thức Orchestrator ngay lập tức để chuyển tiếp sang Stage tiếp theo trong Workflow mà không cần polling hay chờ đợi thủ công.

## 2. Specialized Subagent Routing (1-Agent = 1-Skill)
- **`spec-engineer`** (Model: `pro`): Requirements clarification, boundary definition, PRDs (`workflow-spec`).
- **`task-planner`** (Model: `pro`): Architecture, dependency graphs (DAG), execution plans (`workflow-plan`).
- **`builder`** (Model: `flash`): Code implementation, feature development, DB migrations, bug fixes (`workflow-build`).
- **`debugger`** (Model: `pro`): Root-cause isolation, diagnostic script execution, SQL error diagnosis.
- **`test-engineer`** (Model: `flash`): Unit/integration/API testing, test suite execution (`workflow-test`).
- **`code-reviewer`** (Model: `pro`): 5-axis rigorous review (correctness, architecture, security, performance, readability) (`workflow-review`).
- **`security-auditor`** (Model: `pro`): OWASP scanning, auth/authz vulnerability checks, secret exposure audits (`workflow-security`).
- **`performance-auditor`** (Model: `flash`): CWV, profiling, DB index and query optimization.
- **`code-simplifier`** (Model: `flash`): Refactoring, dead code cleanup, complexity reduction.

## 3. Telemetry & Observability
- All subagents and orchestrator actions must sync state to the local Orchestrator Dashboard (`http://localhost:8484`) via `tools/orchestrator/client.py`.
