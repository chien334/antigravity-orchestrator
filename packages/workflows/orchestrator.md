---
name: orchestrator
description: Dual-Channel Multi-Agent Orchestrator - Turn-1 preflight auto-routing ~60% workload to Gemini.app Desktop ($0.00 API spend) and ~40% to AGY Periodic Table parallel workers (or 100% AGY fallback), 3-Stage Circuit Breaker, and real-time SSE dashboard
---

# Dual-Channel Multi-Agent Orchestrator

Start full-session Multi-Agent Orchestrator mode:

1. **MANDATORY Turn-1 Pre-Flight Gate (Execute FIRST)**:
   - Before decomposing tasks or calling `invoke_subagent`, ALWAYS run:
     ```bash
     python3 ~/.gemini/tools/orchestrator/client.py preflight --workspace .
     ```
     *(If `~/.gemini/tools/orchestrator/client.py` is absent, use `tools/orchestrator/client.py` or `packages/orchestrator/client.py`.)*
   - `preflight` checks/auto-starts the `:8484` Orchestrator Dashboard (`http://localhost:8484`), probes live Gemini Desktop App readiness (`desktop_share.desktop_ready`: installed + Accessibility granted + screen unlocked), allocates pending DAG tasks (`target_share=0.60`), and outputs `EXECUTION_MODE: HYBRID_60_DESKTOP` or `EXECUTION_MODE: API_ONLY_100`.
   - SQLite persistence is active at `tools/orchestrator/orchestrator.db` (or `packages/orchestrator/orchestrator.db`).

2. **Dual-Channel Fire & Delegate Protocol (Command & Control vs. Implementation)**:
   - **Zero Direct Code Implementation**: The Orchestrator NEVER writes application code, executes test suites directly, or dumps raw DB/log diagnostics in the main session.
   - **Orchestrator Command & Control Exception**: Running `client.py preflight`, `client.py allocate-dag`, `client.py update`, `client.py next-ready`, and dispatching Channel A tasks via `client.py desktop-ask` (`run_command` with `WaitMsBeforeAsync: 500`) **ARE required Orchestrator dispatch operations** — execute them directly!
   - **Case A — When `preflight` reports `EXECUTION_MODE: HYBRID_60_DESKTOP` (`desktop_ready == true`)**:
     - **HARD INVARIANT (~60% Gemini Desktop App Share)**: Do **NOT** send `spec-engineer`, `task-planner`, `code-reviewer`, `doc-generator`, non-critical `debugger`, `performance-auditor`, OR the primary heavy `builder` of a wave to an AGY `pro` / `inherit` `invoke_subagent`!
     - **Channel A (`gemini-desktop-app` — ~60% tasks, `$0.00` AGY API spend, `0` focus switches)**:
       Dispatch directly via `run_command` (`WaitMsBeforeAsync: 500` async background task):
       - Read-only synthesis (`spec-engineer`, `task-planner`, `code-reviewer`, `performance-auditor`, `doc-generator` critique — omit `--allow-edits`):
         `python3 ~/.gemini/tools/orchestrator/client.py desktop-ask --task <TASK_ID> --agent <ROLE> --workspace . --prompt "<BOUNDED_PROMPT>"`
       - Mutating heavy `builder` or non-critical `debugger` (max **1** per `parallel_group` — pass `--allow-edits`):
         `python3 ~/.gemini/tools/orchestrator/client.py desktop-ask --task <TASK_ID> --agent builder --workspace . --allow-edits --prompt "<BOUNDED_PROMPT>"`
       - *(Optional wrapper alternative: a thin `invoke_subagent(Model="flash_lite")` wrapper that ONLY invokes `client.py desktop-ask` and NEVER solves the task itself.)*
       - **Parallel-Group Mutex Invariant**: Dispatch **at most 1** task per `parallel_group` to `desktop-ask` so `Gemini.app`'s single-window FIFO lock NEVER serializes sibling workers.
     - **Channel B (`AGY Subagents` — ~40% tasks, concurrent in the same turn)**:
       - Sibling parallel `builder` (`<=3` files), `test-engineer`, `scout` -> `invoke_subagent(Model="flash")` (**Gemini 4 Hydrogen** `198 tok/s` / **3.8 Flash**).
       - **Rule 1 Security Audits** (`security-auditor`, `has_security_impact=True`, `critical` complexity), Circuit Breaker Stage 2/3, and busy-queue Neon spillover -> `invoke_subagent(Model="pro")` (or `"inherit"`).
   - **Case B — When `preflight` reports `EXECUTION_MODE: API_ONLY_100` (`desktop_ready == false`)**:
     - Automatically and seamlessly dispatch **100%** of tasks via `invoke_subagent`:
       - `Model="pro"` (or `"inherit"`) for `gemini-4-carbon` / `gemini-4-neon` roles (`security-auditor`, `spec-engineer`, `task-planner`, `code-reviewer`, `debugger`, multi-file `builder >=4` files).
       - `Model="flash"` for `gemini-4-hydrogen` / `gemini-3.8-flash` roles (bounded `builder <=3` files, `test-engineer`, `scout`, `code-simplifier`, `doc-generator`).
   - **Reactive Yield**: End your turn immediately after dispatching Channel A (`run_command`, `WaitMsBeforeAsync=500`) + Channel B (`invoke_subagent`) workers. Never poll or sleep.

3. **Periodic Table Intelligent Model Routing (Neon SWE Fleet + Conditional 60% Desktop Peer)**:
   - 🖥️ **Conditional 60% Peer Model (`gemini-desktop-app` via `client.py desktop-ask`)**: Active whenever `preflight` reports `desktop_ready == true` (`$0.00` AGY API spend, `0` focus switches, `mode="task"`, `background=True`, `allow_edits=True/False`). Dispatched via `run_command(WaitMsBeforeAsync=500)`.
   - ✦ **Tier 1: Frontier Security & Escalation (`gemini-4-carbon`, `Model="pro"`, `reasoning_effort: high | medium`)**: Rule 1 security audits (OWASP/auth/crypto/CVE/migration), `critical` complexity specs, and Circuit Breaker Stage 3 (`retry_count >= 3`). Rates: $2.00 / 1M in, $10.00 / 1M out, $0.50 / 1M cache.
   - ⚡✦ **Tier 1.5 / 2: SWE Frontier & Orchestrator Brain (`gemini-4-neon`, `gemini-pro-orchestrator-neon`, `Model="pro"`/`"inherit"`, `reasoning_effort: low | medium | high | xhigh`)**: Coding Agent Index #1 (`58.64`), `~105 tok/s`, 95% cache savings ($3.00 / $15.00 / $0.15). Takes over non-security `spec-engineer`, `task-planner`, `code-reviewer`, `debugger`, `performance-auditor`, multi-file `builder` (`>= 4` files) in `API_ONLY_100` mode or Desktop queue spillover, and CB Stage 2 (`retry_count == 2`).
   - ⚡ **Tier 3: High-Throughput Workhorse (`gemini-4-hydrogen`, `Model="flash"`, `198 tok/s`)**: Bounded parallel `builder` slices (`<= 3` files), `test-engineer`, `scout`, and UI iteration ($1.50 / $7.50 / $0.075).
   - ⚡ **Tier 4: Cost-Efficient Micro-Tier (`gemini-3.8-flash`, `Model="flash"`, `low`)**: Cost-first scaffolding, `code-simplifier`, `doc-generator` ($0.75 / $3.75 / $0.075). *(Legacy `gemini-4-argon` and `gemini-3.8-flash-lite` are deprecated/DB-alias only).*

4. **3-Stage Fast-Retry & Escalation Circuit Breaker (Channel B API Only)**:
   - **Stage 1 (`retry_count == 1`)**: Hydrogen `invoke_subagent(Model="flash")` performs 1 fast self-healing turn (`effort: xhigh`).
   - **Stage 2 (`retry_count == 2`)**: Escalate to **Gemini 4 Neon** (`invoke_subagent(Model="pro")`, `high`/`xhigh`).
   - **Stage 3 (`retry_count >= 3`)** or security impact: Trip hard directly to **Gemini 4 Carbon** (`invoke_subagent(Model="pro")`, `high` effort).

5. **Condition-Based DAG Scheduling & Parallel Fan-Out**:
   - Group independent tasks using `parallel_group` (e.g., `BUILD-PARALLEL`) and prerequisites with `depends_on`.
   - Discover ready unblocked tasks via `python3 ~/.gemini/tools/orchestrator/client.py next-ready`.
   - Enforce the **Decoupled File Scope Invariant**: parallel workers across Channel A and Channel B must operate on strictly disjoint files.

6. **Token Telemetry & Turnkey CLI Subcommands**:
   - **Turn-1 Mandatory Pre-Flight Gate**:
     `python3 ~/.gemini/tools/orchestrator/client.py preflight --workspace .`
     `python3 ~/.gemini/tools/orchestrator/client.py preflight --tasks-json tasks.json --apply`
     `python3 ~/.gemini/tools/orchestrator/client.py preflight --no-desktop` *(force `API_ONLY_100`)*
   - **DAG Allocation & Ready Queue**:
     `python3 ~/.gemini/tools/orchestrator/client.py allocate-dag --target-desktop-share 0.60 --apply`
     `python3 ~/.gemini/tools/orchestrator/client.py next-ready`
   - **Channel A Desktop Dispatch (`run_command`, `WaitMsBeforeAsync: 500`)**:
     `python3 ~/.gemini/tools/orchestrator/client.py desktop-ask --task <TASK_ID> --agent <ROLE> --workspace . [--allow-edits] --prompt "..."`
     `python3 ~/.gemini/tools/orchestrator/client.py desktop-jobs --limit 20` / `desktop-cancel --job-id <JOB_ID>`
   - **Smart Router & Model Registry**:
     `python3 ~/.gemini/tools/orchestrator/client.py recommend --agent <AGENT> --complexity <low|medium|high|critical> [--budget-mode ...] [--desktop-available] [--read-only] [--retry-count <N>] [--security-impact]`
     `python3 ~/.gemini/tools/orchestrator/client.py models`
   - **Telemetry & Audit Export**:
     `python3 ~/.gemini/tools/orchestrator/client.py update --task <TASK_ID> --agent <AGENT> --status <running|completed> --progress <N> --model <MODEL> --reasoning-effort <EFFORT>`
     `python3 ~/.gemini/tools/orchestrator/client.py export --format markdown --out docs/reports/mission_audit_report.md`
