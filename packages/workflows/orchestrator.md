---
name: orchestrator
description: Multi-Agent Orchestrator - coordinate subagents, plan, Gemini 4 Neon SWE Fleet & Periodic Table parallel execution, 3-Stage Fast-Retry Circuit Breaker, and real-time dashboard
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
   - **"Fast Hands, Deep Brain"**: Hydrogen scouts & bounded parallel builders (`<= 3` files) operate at 198 tok/s, while **Gemini 4 Neon** (`gemini-pro-orchestrator-neon`, Coding Agent Index #1 `58.64`, ~105 tok/s) orchestrates, plans, specs, reviews, and handles complex multi-file builds (`>= 4` files), and **Gemini 4 Carbon** locks down Stage 6 security & critical invariants.

3. **Periodic Table Intelligent Model Routing (Neon SWE Fleet)**:
   - ✦ **Tier 1: Frontier Security & Escalation (`gemini-4-carbon`, `reasoning_effort: high | medium`)**: Rule 1 security audits (OWASP/auth/crypto/CVE/migration), `critical` complexity specs, and Circuit Breaker Stage 3 (`retry_count >= 3`). Rates: $2.00 / 1M in, $10.00 / 1M out, $0.50 / 1M cache *(doubles to $4/$20 on Dec 1, 2026)*.
   - ⚡✦ **Tier 1.5 / 2: SWE Frontier & Orchestrator Brain (`gemini-4-neon`, `gemini-pro-orchestrator-neon`, `reasoning_effort: low | medium | high | xhigh`)**: Element #10 — Coding Agent Index #1 (`58.64`), Intelligence `61` (`xhigh`), `~105 tok/s` (2x Carbon/Argon speed), ~32% lower cost/task vs Carbon. Replaces `gemini-4-argon` across `orchestrator`, `task-planner`, and `code-reviewer`, and takes over non-security `spec-engineer`, `debugger`, `performance-auditor`, multi-file `builder` (`>= 4` files), and Circuit Breaker Stage 2 (`retry_count == 2`). Rates: $3.00 / 1M in, $15.00 / 1M out, $0.15 / 1M cache (95% cache savings).
   - ✦ **Tier 2b: Legacy Deep Reasoning (`gemini-4-argon`, `reasoning_effort: medium | high`)**: Superseded by `gemini-4-neon` in default SWE routing; retained for historical ledger compatibility & legacy fallback. Rates: $1.25 / 1M in, $5.00 / 1M out, $0.3125 / 1M cache *($2/$10 → $4/$20 Dec 1, 2026)*.
   - ⚡ **Tier 3: High-Throughput Workhorse (`gemini-4-hydrogen`, `reasoning_effort: low | medium | high | xhigh`)**: Ultra-fast workhorse (198 tok/s, ~2x faster than Neon without ~40s deep-thinking TTFT) for bounded parallel `builder` slices (`<= 3` files), `test-engineer`, `scout`, and UI iteration (~24% quota saved when paired with `Orchestrator (Neon)`). Rates: $1.50 / 1M in, $7.50 / 1M out, $0.075 / 1M cache (95% cache savings).
   - ⚡ **Tier 4: Cost-Efficient & Active Micro-Tier (`gemini-3.8-flash`, `reasoning_effort: low | medium | high`)**: Cost-first parallel scaffolding, `code-simplifier` (`low`), `doc-generator`, and active telemetry/linting default (replaces absent `gemini-3.8-flash-lite` default). Live rates: $0.75 / 1M in, $3.75 / 1M out, $0.075 / 1M cache. *(Legacy `gemini-3.8-flash-lite` is deprecated/DB-alias only).*
   - 🖥️ **External Heavy-Analysis Offload Tier (`gemini-desktop-app` via `gemini-desktop-worker`)**: Local cross-platform Gemini Desktop App bridge (`macos_ax` / `windows_uia` / `linux_pwa` / `mock`) for `$0.00` AGY API spend on heavy **read-only** synthesis (`spec-engineer`, `task-planner`, `code-reviewer`, read-only `debugger`/`scout`) under `--budget-mode hybrid_desktop` or `offload_heavy_to_desktop`. Pre-flight `SecretRedactor` scrubs credentials, Clipboard Save/Restore protects user clipboard (`<= 300ms`), and outputs write to `docs/reports/desktop_worker/{job_id}.md` pointers. *(Rule 1 Security Guardrail & Stage 3 file-editing builders NEVER offload to Desktop).*

4. **3-Stage Fast-Retry & Escalation Circuit Breaker**:
   - **Stage 1 (`retry_count == 1`)**: Hydrogen builders & testers perform 1 fast self-healing turn (`effort: xhigh`).
   - **Stage 2 (`retry_count == 2`)**: Auto-escalate to **Gemini 4 Neon** (`high`, or `xhigh` if `complexity == "high"`).
   - **Stage 3 (`retry_count >= 3`)** or security impact: Trip hard directly to **Gemini 4 Carbon** (`high` effort) for final frontier root-cause diagnosis.

5. **Condition-Based DAG Scheduling & Parallel Fan-Out**:
   - Group independent tasks using `parallel_group` (e.g., `BUILD-PARALLEL`) and specify prerequisites with `depends_on`.
   - Discover ready unblocked tasks automatically via `GET /api/dag/ready` or CLI `python3 packages/orchestrator/client.py next-ready`.
   - Dispatch workers concurrently in the same turn when dependencies are satisfied.
   - Enforce the **Decoupled File Scope Invariant**: builder workers must operate on strictly disjoint files.

6. **Token Telemetry & CLI Subcommands**:
   - Query smart recommendations (including `hybrid_desktop` / `offload_heavy_to_desktop`):
     `python3 packages/orchestrator/client.py recommend --agent <AGENT> --complexity <low|medium|high|critical> [--budget-mode <balanced|speed_first|quality_first|cost_saving|hybrid_desktop|offload_heavy_to_desktop>] [--desktop-available] [--read-only] [--retry-count <N>] [--security-impact]`
   - Check Gemini Desktop App readiness & dispatch bounded read-only analysis (`$0.00` API spend):
     `python3 packages/orchestrator/client.py desktop-doctor --format text`
     `python3 packages/orchestrator/client.py desktop-ask --task <TASK_ID> --prompt-file <PATH> --driver auto`
     `python3 packages/orchestrator/client.py desktop-jobs --limit 20` / `desktop-cancel --job-id <JOB_ID>`
   - Discover runnable unblocked DAG tasks:
     `python3 packages/orchestrator/client.py next-ready`
   - Inspect registered models and pricing:
     `python3 packages/orchestrator/client.py models`
   - Record `input_tokens`, `output_tokens`, `cache_tokens`, and `--reasoning-effort` (`low|medium|high|xhigh`) after every turn:
     `python3 packages/orchestrator/client.py update --task <TASK_ID> --agent <AGENT> --status <running|completed> --progress <N> --model <MODEL> --reasoning-effort <EFFORT>`
   - Export post-mission audit reports:
     `python3 packages/orchestrator/client.py export --format markdown --out mission_audit_report.md`
