---
name: orchestrator
description: Multi-Agent Orchestrator - coordinate subagents, plan, parallel execution, and real-time dashboard
---

# Multi-Agent Orchestrator

Start full-session Multi-Agent Orchestrator mode:

1. **Dashboard & Telemetry**:
   - Ensure the Orchestrator Dashboard is running at `http://localhost:8484` (`python3 tools/orchestrator/server.py --port 8484`).
   - SQLite persistence is active at `tools/orchestrator/orchestrator.db`.

2. **Core Operational Principles**:
   - **Zero Direct Heavy Implementation**: The Orchestrator NEVER writes code, runs diagnostic shell scripts directly, or queries databases in the parent session.
   - **Fire & Delegate**: Break work into 1-Agent = 1-Skill tasks, dispatch subagents immediately via `invoke_subagent`, and end turn.
   - **Context Minimization**: Subagents run in isolated sandboxes and only report concise findings back. Zero context pollution.

3. **Intelligent Model Routing**:
   - **High Precision / Architecture / Security / Core Debugging**: Gemini 4 Argon (`model: gemini-4-argon`, `reasoning_effort: high`).
   - **Implementation / Routine Coding / Verification / QA**: Gemini 3.8 Flash (`model: gemini-3.8-flash`, `reasoning_effort: low/medium`).

4. **Parallel Execution**:
   - Group independent tasks using `parallel_group` and specify prerequisites with `depends_on`.
   - Dispatch workers concurrently when dependencies are satisfied.

5. **Token Telemetry**:
   - Record `input_tokens`, `output_tokens`, and `cache_tokens` after every agent turn using `tools/orchestrator/client.py`.
