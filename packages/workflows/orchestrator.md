---
name: orchestrator
description: Multi-Agent Orchestrator - coordinate subagents, plan, 5-Tier Periodic Table parallel execution, Fast-Retry Circuit Breaker, and real-time dashboard
---

# Multi-Agent Orchestrator

Start full-session Multi-Agent Orchestrator mode:

1. **Dashboard & Telemetry**:
   - Ensure the Orchestrator Dashboard is running at `http://localhost:8484` (`python3 packages/orchestrator/server.py --port 8484`).
   - SQLite persistence is active at `packages/orchestrator/orchestrator.db` (or `tools/orchestrator/orchestrator.db` in deployed projects).

2. **Core Operational Principles**:
   - **Zero Direct Heavy Implementation**: The Orchestrator NEVER writes code, runs diagnostic shell scripts directly, or queries databases in the parent session.
   - **Fire & Delegate**: Break work into 1-Agent = 1-Skill tasks, dispatch subagents immediately via `invoke_subagent`, and end turn.
   - **Context Minimization**: Subagents run in isolated sandboxes and only report concise findings back. Zero context pollution.
   - **"Fast Hands, Deep Brain"**: Hydrogen scouts & parallel builders operate at 198 tok/s, while Argon architects and Carbon secures.

3. **5-Tier Periodic Table Intelligent Model Routing**:
   - ✦ **Tier 1: Frontier Reasoning (`gemini-4-carbon`, `reasoning_effort: high | medium`)**: Mission-critical security audits, deep vulnerability modeling, formal architectural specifications, and complex root-cause debugging. Rates: $2.00 / 1M in, $10.00 / 1M out, $0.50 / 1M cache.
   - ✦ **Tier 2: Deep Reasoning (`gemini-4-argon`, `reasoning_effort: medium | high`)**: High-velocity deep reasoning for architecture design, task DAG scheduling, 5-axis code reviews, and cross-module contracts. Rates: $1.25 / 1M in, $5.00 / 1M out, $0.3125 / 1M cache.
   - ✦ **Tier 3: High-Throughput Workhorse (`gemini-4-hydrogen`, `reasoning_effort: low | medium | high | xhigh`)**: Ultra-fast workhorse for parallel code builders, automated test suites, codebase scouting, and UI iteration (198 tok/s, 2.5x speed). Rates: $1.50 / 1M in, $7.50 / 1M out, $0.075 / 1M cache (95% cache savings).
   - ⚡ **Tier 4: Cost-Efficient Builder / Bulk (`gemini-3.8-flash`)**: Cost-first parallel implementations, scaffolding, and doc formatting. Rates: $0.075 / 1M in, $0.30 / 1M out, $0.01875 / 1M cache.
   - ⚡ **Tier 5: Ultra-Fast Micro-Tier (`gemini-3.8-flash-lite`)**: Low-latency micro-tier for telemetry heartbeats, quick formatting, and linting. Rates: $0.0375 / 1M in, $0.15 / 1M out, $0.01 / 1M cache.

4. **Fast-Retry & Escalation Circuit Breaker**:
   - Hydrogen builders & testers perform 1 fast self-healing turn on failure (`effort: xhigh`).
   - If `retry_count >= 2` or security impact is present, auto-escalate directly to **Gemini 4 Carbon** (`high` effort) for deep root cause diagnosis.

5. **Condition-Based DAG Scheduling & Parallel Fan-Out**:
   - Group independent tasks using `parallel_group` (e.g., `BUILD-PARALLEL`) and specify prerequisites with `depends_on`.
   - Discover ready unblocked tasks automatically via `GET /api/dag/ready` or CLI `python3 packages/orchestrator/client.py next-ready`.
   - Dispatch workers concurrently in the same turn when dependencies are satisfied.
   - Enforce the **Decoupled File Scope Invariant**: builder workers must operate on strictly disjoint files.

6. **Token Telemetry & CLI Subcommands**:
   - Query smart recommendations:
     `python3 packages/orchestrator/client.py recommend --agent <AGENT> --complexity <low|medium|high|critical> [--budget-mode <balanced|speed_first|quality_first|cost_saving>] [--retry-count <N>] [--security-impact]`
   - Discover runnable unblocked DAG tasks:
     `python3 packages/orchestrator/client.py next-ready`
   - Inspect registered models and pricing:
     `python3 packages/orchestrator/client.py models`
   - Record `input_tokens`, `output_tokens`, `cache_tokens`, and `--reasoning-effort` (`low|medium|high|xhigh`) after every turn:
     `python3 packages/orchestrator/client.py update --task <TASK_ID> --agent <AGENT> --status <running|completed> --progress <N> --model <MODEL> --reasoning-effort <EFFORT>`
   - Export post-mission audit reports:
     `python3 packages/orchestrator/client.py export --format markdown --out mission_audit_report.md`
