---
name: multi-agent-orchestrator
description: Multi-agent orchestration skill following the 1-Agent = 1-Skill paradigm (addyosmani/agent-skills). Coordinates specialized subagents across the software delivery lifecycle with real-time SSE telemetry, context minimization, 5-Tier Periodic Table intelligent model routing (gemini-4-carbon, gemini-4-argon, gemini-4-hydrogen with xhigh effort & 198 tok/s velocity, gemini-3.8-flash, gemini-3.8-flash-lite), automated DAG scheduling, and audit exports.
---

# Multi-Agent Orchestrator Skill

## 1. Overview & Mission

The **Multi-Agent Orchestrator** coordinates autonomous subagents to deliver complex software projects with high velocity, zero state drift, and rigorous quality gates. 

Rooted in the **1-Agent = 1-Skill** paradigm popularized by Addy Osmani's agent design patterns, every agent in the fleet operates under a bounded scope, specialized persona, and strict context minimization protocol.

### Core Objectives
1. **Divide and Conquer**: Deconstruct monolithic tasks into discrete, verifiable slices with clear boundary contracts.
2. **Context Minimization**: Prevent token bloat by using pointer-based file references (`file:///...`) and scoped briefings.
3. **5-Tier Periodic Table Intelligent Model Routing**: Dynamically match task complexity to the optimal model tier:
   - ✦ **Tier 1 (Frontier Reasoning)**: `gemini-4-carbon` ($2.00 / $10.00 / $0.50) — Cybersecurity audits, formal invariants, deep root-cause debugging.
   - ✦ **Tier 2 (Deep Reasoning)**: `gemini-4-argon` ($1.25 / $5.00 / $0.3125) — Macro Task DAG scheduling, system architecture, 5-axis code audits.
   - ✦ **Tier 3 (High-Throughput Workhorse)**: `gemini-4-hydrogen` ($1.50 / $7.50 / $0.075) — Parallel software builders, test fixture suites, codebase reconnaissance, rapid UI iteration (198 tok/s, 2.5x speed, `xhigh` effort).
   - ⚡ **Tier 4 (Cost-Efficient Builder / Bulk)**: `gemini-3.8-flash` ($0.075 / $0.30 / $0.01875) — Bulk code scaffolding, cost-first implementations, text simplification.
   - ⚡ **Tier 5 (Ultra-Fast Telemetry)**: `gemini-3.8-flash-lite` ($0.0375 / $0.15 / $0.01) — Micro-telemetry heartbeats, ping monitors, linting.
4. **"Fast Hands, Deep Brain" Topologies**: Accelerate end-to-end execution through Scout-Then-Architect (Hydrogen scouts feed compact pointers to Argon), Fan-Out Builders with Dual Quality Gates (Hydrogen builders + Argon review + Carbon security), and Fast-Retry Circuit Breakers with `--retry-count`.
5. **Automated DAG Scheduling**: Evaluate task dependencies (`depends_on`) automatically via a ready-queue evaluator for concurrent Fan-Out.
6. **Real-time Observability & Financial Analytics**: Stream subagent progress, telemetry, thoughts, and per-model token expenditure (USD & VND) via Server-Sent Events (SSE) and SQLite.
7. **Audit & Compliance Sign-off**: Export permanent post-mission execution reports in Markdown and structured JSON.

---

## 2. The 9 Specialized Personas (1-Agent = 1-Skill)

Each agent persona maps strictly to a single skill specialty. Agents never cross functional boundaries unless explicitly delegated.

```
+-----------------------------------------------------------------------------------+
|                           Multi-Agent Orchestrator                                |
|        (Task Dispatch, 5-Tier Smart Routing, DAG Ready Queue, SSE Telemetry)      |
+-----------------------------------------------------------------------------------+
                                          |
   +--------------------------------------+-----------------------------------+
   |                    |                 |                 |                 |
   v                    v                 v                 v                 v
[1. Spec]          [2. Plan]         [3. Build]        [4. Test]        [5. Review]
Product Spec       Architect         Software Builder  Test Spec        Code Review
Gemini 4 Carbon    Gemini 4 Argon    Gemini 4 Hydrogen Gemini 4 Hydrogen Gemini 4 Argon
(effort: high)     (effort: high)    (198 tok/sec)     (effort: medium) (effort: high)
   |                    |                 |                 |                 |
   +--------------------+-----------------+-----------------+-----------------+
                                          |
                       +--------------------+--------------------+
                       |                                         |
                       v                                         v
                [6. Security]                              [7. Release]
                Security Specialist                        DevOps & Deployment
                Gemini 4 Carbon (Effort: high)             Gemini 4 Hydrogen / Argon
```

| # | Persona | Primary Skill & Responsibility | Recommended Model & Effort | Output Artifact | Workflow Runbook |
|---|---------|--------------------------------|----------------------------|-----------------|------------------|
| 1 | **Multi-Agent Orchestrator** | Task scheduling, dependency resolution, SSE telemetry, context dispatch | ✦ **Gemini 4 Argon** (`medium`) | Orchestrator Plan, DAG | [`workflow-pipeline.md`](../../workflows/workflow-pipeline.md) |
| 2 | **Product / Spec Specialist** | Requirements discovery, user stories, acceptance criteria, edge-case matrix | ✦ **Gemini 4 Carbon** (`high`) | `docs/specs/{feature_id}.spec.md` | [`workflow-spec.md`](../../workflows/workflow-spec.md) |
| 3 | **Architect / Planner** | System design, contract definition, database schemas, component topology | ✦ **Gemini 4 Argon** (`medium`/`high`) | `docs/plans/{feature_id}.plan.md` | [`workflow-plan.md`](../../workflows/workflow-plan.md) |
| 4 | **Software Builder** | Code implementation, UI/API development, minimal blast radius edits | ✦ **Gemini 4 Hydrogen** (`medium`/`high`/`xhigh`) | Source Code Files on disk | [`workflow-build.md`](../../workflows/workflow-build.md) |
| 5 | **Test Specialist** | Test suites, mocks, unit tests, integration tests, assertions | ✦ **Gemini 4 Hydrogen** (`medium`/`high`) | `docs/reports/test_report.json` | [`workflow-test.md`](../../workflows/workflow-test.md) |
| 6 | **Code Reviewer** | 5-axis code quality inspection, anti-pattern detection, invariants | ✦ **Gemini 4 Argon** (`high`) | `docs/reviews/review_signoff.md` | [`workflow-review.md`](../../workflows/workflow-review.md) |
| 7 | **Security Specialist** | Threat modeling, OWASP verification, secret scanning, RBAC checks | ✦ **Gemini 4 Carbon** (`high`) | `docs/security/security_audit.md` | [`workflow-security.md`](../../workflows/workflow-security.md) |
| 8 | **Root-Cause Debugger** | Deep failure isolation, complex multi-component diagnostics | ✦ **Gemini 4 Carbon** (`high`) | Diagnostic Report & Fix Plan | - |
| 9 | **Observability / Telemetry** | Instrumentation, heartbeat logging, quick formatting, dead code linting | ⚡ **Gemini 3.8 Flash-Lite** (`None`) | Telemetry Logs & Metrics | - |

---

## 3. Handoff Pipeline & Artifact Data Contracts (Output(N) ➔ Input(N+1))

Every stage delivers an explicit, structured file artifact that serves as the strictly bounded input for the next stage. Raw conversation histories are never passed directly to subagents; instead, only the target artifact path is provided:

```
[User Request]
       │
       ▼
[Stage 1: Spec] ──▶ docs/specs/{feature_id}.spec.md (Gemini 4 Carbon, effort: high)
                           │
                           ▼
                   [Stage 2: Plan] ──▶ docs/plans/{feature_id}.plan.md (Gemini 4 Argon)
                                               │
                                               ▼
                                      [GET /api/dag/ready] ──▶ Evaluates Unblocked Tasks
                                               │
                                               ▼
                                      [Stage 3: Parallel Builders] ──▶ Disjoint Code Files (Gemini 4 Hydrogen, 198 tok/s)
                                                                               │
                                                                               ▼
                                      [Stage 4: Tests] ◀── (Code + Spec AC) ──▶ docs/reports/test_report.json (Gemini 4 Hydrogen)
                                               │
                                               ▼
                                      [Stage 5: Review] ──▶ docs/reviews/review_signoff.md (Gemini 4 Argon)
                                                                      │
                                                                      ▼
                                                              [Stage 6: Security] ──▶ docs/security/security_audit.md (Gemini 4 Carbon, effort: high)
                                                                                              │
                                                                                              ▼
                                                                                      [Audit Export & Release]
```

---

## 4. 5-Tier Intelligent Model Routing Matrix

To maximize precision, throughput, and financial economy, tasks are dynamically routed across five discrete model tiers:

| Tier | Engine Model | Canonical ID | Input / 1M | Output / 1M | Cache Read / 1M | Tunable Reasoning Effort | Role Specialization & Rationale |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Tier 1: Frontier** | **Gemini 4 Carbon** | `gemini-4-carbon` | **$2.00** | **$10.00** | **$0.50** | `low`, `medium`, `high` | • `security-auditor`: Deep vulnerability modeling, OWASP scans, secret audits.<br>• `spec-engineer`: Formal specification proofs, edge-case discovery.<br>• `debugger`: Complex multi-component root-cause isolation.<br>• Core cryptographic, financial, and authentication logic. |
| **Tier 2: Deep Reasoning** | **Gemini 4 Argon** | `gemini-4-argon` | **$1.25** | **$5.00** | **$0.3125** | `low`, `medium`, `high` | • `task-planner`: Architecture modeling, dependency graphs, sequencing.<br>• `code-reviewer`: 5-axis rigorous review (correctness, architecture, maintainability, performance, error handling).<br>• `orchestrator`: Fleet dispatch and synthesis coordination. |
| **Tier 3: High-Throughput Workhorse** | **Gemini 4 Hydrogen** | `gemini-4-hydrogen` | **$1.50** | **$7.50** | **$0.075** | `low`, `medium`, `high`, `xhigh` | • `builder`: Parallel disjoint feature implementation, CRUD, UI components at 198 tok/s (2.5x speed).<br>• `test-engineer`: Unit/integration test suites, assertion gates, test fixtures.<br>• `scout`: Codebase reconnaissance and symbol pointer discovery.<br>• 95% cache read savings ($0.075 / 1M tokens). |
| **Tier 4: Cost-Efficient Builder / Bulk** | **Gemini 3.8 Flash** | `gemini-3.8-flash` | **$0.075** | **$0.30** | **$0.01875** | `None` | • `code-simplifier`: Text formatting, doc generation, low-complexity scaffolding.<br>• Fallback for bulk execution in `cost_saving` mode. |
| **Tier 5: Ultra-Fast Micro-Tier** | **Gemini 3.8 Flash-Lite** | `gemini-3.8-flash-lite` | **$0.0375** | **$0.15** | **$0.01** | `None` | • `observability-and-instrumentation`: Heartbeats, quick linting, documentation formatting.<br>• Near-zero latency execution. |

### Tunable Reasoning Effort Guidelines (`--reasoning-effort` / `--effort`)
- **`xhigh`** (Exclusively supported on `gemini-4-hydrogen`): Maximum depth thinking for challenging algorithmic edge cases, self-healing test fixes, and complex logic implementation without sacrificing 198 tok/s velocity. *(Clamped to `high` on Carbon/Argon).*
- **`high`**: Activates deep multi-pass reasoning, autonomous verification loops, and vulnerability fuzzing. Use for `security-auditor` on critical tasks, formal PRD specifications, and high-complexity debugging.
- **`medium`** (Default): Balanced deep reasoning for architecture design, 5-axis code reviews, and cross-module contracts.
- **`low`**: Light reasoning check for quick architectural clarifications and sanity checks.

---

## 5. "Fast Hands, Deep Brain" Advanced Topologies

To maximize fleet velocity while preserving mathematical correctness and security invariants, the orchestrator applies four advanced multi-agent topologies:

### Topology A: Scout-Then-Architect (Token Minimization)
1. **Parallel Fast Scouting**: The orchestrator dispatches 2 to 4 `gemini-4-hydrogen` scouts (`effort: low`).
2. **Compact URI Pointers**: Scouts search the codebase using ripgrep and AST tools, returning strictly compact URI pointers (`file:///path/to/file#L10-L25`) and summary cards without dumping raw code files into the chat context.
3. **Deep Synthesis**: `gemini-4-argon` receives the consolidated pointer summary (< 4,000 tokens), avoiding context bloat, and crafts the master architecture specification and task DAG.
4. **Efficiency Impact**: Cuts scout phase time from 3 minutes to 45 seconds and slashes prompt context tokens fed to Tier 2 by **80%**.

### Topology B: Fan-Out Hydrogen Builders + Dual Quality Gate
1. **Contract Locking**: `gemini-4-argon` designs the feature specification and locks disjoint file contracts.
2. **Massive Parallel Implementation**: Up to 8 `gemini-4-hydrogen` workers (`group: BUILD-PARALLEL`, `effort: medium`/`high`) implement assigned file slices concurrently at 198 tokens/second.
3. **High-Speed Test Execution**: A `gemini-4-hydrogen` test engineer executes unit/integration test suites against spec acceptance criteria.
4. **Dual Quality Gate**:
   - `gemini-4-argon` performs the 5-axis code quality and architecture review.
   - `gemini-4-carbon` (`effort: high`) executes the final OWASP security audit before production release.

### Topology C: Fast-Retry & Escalation Circuit Breaker
```
            [Hydrogen Builder / Fixer]
                       │
                 Executes Task
                       │
                    Result?
                  /        \
               PASS        FAIL
               /              \
       [Next DAG Stage]     Retry Count < 1?
                            /            \
                         YES              NO (or Security Impact)
                         /                  \
               Fast Self-Fix Retry       ESCALATE TO CIRCUIT BREAKER
               (Hydrogen, effort: xhigh)              │
                                                      ▼
                                           [Gemini 4 Carbon]
                                           Reasoning Effort: HIGH
                                           Deep Root-Cause Diagnosis
```
1. **Attempt 0 (`retry_count: 0`)**: Task executes on `gemini-4-hydrogen` (`effort: medium` or `high`).
2. **Attempt 1 (`retry_count: 1`)**: Fast self-healing retry turn on `gemini-4-hydrogen` with elevated effort (`effort: xhigh`).
3. **Attempt 2+ (`retry_count >= 2`)**: Trip circuit breaker! The task is automatically escalated to **Gemini 4 Carbon** (`reasoning_effort: high`) for deep root-cause diagnosis.
4. **Zero-Downgrade Security Guardrail**: If failure logs match security terms (`auth`, `rbac`, `secret`, `leak`, `overflow`, `crypto`), circuit breaker trips immediately to Carbon without intermediate retries.

### Topology D: Smart Router Budget Modes
- **`balanced` (Default)**: Builders & Testers on Hydrogen, Specs & Reviews on Argon, Security on Carbon.
- **`speed_first` / `latency_sensitive`**: All standard development, build, test, and documentation tasks assigned to `gemini-4-hydrogen` (with `xhigh` effort for reviews). Security strictly remains on Carbon.
- **`quality_first`**: Builders on Argon, Specs/Reviews/Security on Carbon.
- **`cost_saving` / `cost_first`**: Builders on Gemini 3.8 Flash, Telemetry on Flash-Lite, Security on Carbon.

### Smart Router API & CLI
Query the smart router before assigning subagents:
```bash
# Query CLI with budget mode and retry count
python3 packages/orchestrator/client.py recommend \
  --agent builder \
  --complexity medium \
  --budget-mode speed_first \
  --retry-count 1

# Security task always routes to Carbon regardless of budget mode
python3 packages/orchestrator/client.py recommend \
  --agent security-auditor \
  --complexity critical \
  --security-impact

# REST API: POST /api/router/recommend
# Request Body:
# {
#   "agent_type": "builder",
#   "complexity": "medium",
#   "has_security_impact": false,
#   "budget_mode": "speed_first",
#   "retry_count": 0
# }
# Response:
# {
#   "status": "ok",
#   "recommendation": {
#     "model": "gemini-4-hydrogen",
#     "reasoning_effort": "high",
#     "tier": "high_throughput",
#     "rationale": "Parallel code implementation... dispatched to Gemini 4 Hydrogen for 2.5x speed and 198 tok/s throughput.",
#     "estimated_cost_tier": "$$$",
#     "fallback_model": "gemini-3.8-flash"
#   }
# }
```

---

## 6. Parallel Worker Execution & Automated DAG Ready-Queue

The Orchestrator implements a **Condition-Based Directed Acyclic Graph (DAG)** with automated Fan-Out and Fan-In:

```
                  ┌──▶ [Parallel Worker 1: Frontend UI] (Hydrogen, 198 tok/s) ──┐
                  │                                                             │
[Plan (Argon)] ───┼──▶ [Parallel Worker 2: Backend API] (Hydrogen, 198 tok/s) ──┼──▶ [Barrier Sync & Fan-In]
                  │                                                             │
                  └──▶ [Parallel Worker 3: Data Access] (Hydrogen, 198 tok/s) ──┘
```

### Core Concurrency Invariants:
1. **Dependency Invariant (`depends_on`)**:
   - A task enters the `READY` state only when all tasks listed in `depends_on` have reached `status == "completed"`.
2. **Automated Ready-Queue Discovery**:
   - Instead of manual inspection, query `GET /api/dag/ready` or run `python3 packages/orchestrator/client.py next-ready`.
   - The endpoint automatically separates runnable unblocked tasks from blocked tasks and flags `can_fan_out: true` when multiple tasks can run concurrently.
3. **Decoupled File Scope Invariant**:
   - Parallel builder workers MUST operate on strictly disjoint, non-overlapping file paths (e.g., `packages/orchestrator/models.py` vs `dashboard.py` vs `client.py`).
4. **Barrier Synchronization (Fan-In)**:
   - When all subagents in a parallel group reach 100%, the Orchestrator synthesizes outputs, validates cross-cutting contracts, and advances to the next stage.

---

## 7. Context Minimization Protocol

Context window exhaustion is the primary source of hallucinations and drift in LLM agent swarms. The Orchestrator enforces:

1. **Pointers Over Copies**:
   - Never copy entire files into prompts.
   - Reference files using exact absolute paths and line numbers:
     `[models.py](file:///path/to/packages/orchestrator/models.py#L10-L60)`.
2. **Strictly Bounded Slices**:
   - Limit each subagent assignment to a maximum of 1-3 target files and 1 discrete objective.
3. **Structured Handoff Summaries**:
   - When a subagent completes a task, it reports:
     - Exact files modified or created.
     - Verification command and output.
     - Brief 2-3 sentence execution summary.
4. **No Sprawl**:
   - Subagents must not introduce speculative abstractions or modify unassigned files outside their scope.

---

## 8. Real-Time Telemetry & Per-Model Financial Analytics

Hospital Suite includes a zero-dependency, real-time Python dashboard powered by SSE (Server-Sent Events) and SQLite.

### Starting the Server
```bash
# Start server on default port 8484
python3 packages/orchestrator/server.py --port 8484

# Or customize port via environment variable
ORCHESTRATOR_PORT=9000 python3 packages/orchestrator/server.py
```

### Dashboard Features (`GET http://localhost:8484/`)
- **Obsidian Emerald Carbon & Electric Cyan Hydrogen Badges**: Visual indicators for `gemini-4-carbon`, `gemini-4-argon`, and electric cyan `#06b6d4` for `gemini-4-hydrogen` with pulsing reasoning pills (including `xhigh`).
- **5-Tier Financial Ledger**: Dedicated breakdown of token consumption (prompt, completion, cache read), USD spend, VND spend (25,400 VND/USD), and 95% cache savings across Carbon, Argon, Hydrogen, Flash, and Flash-Lite.
- **Interactive SVG DAG Visualizer**: Graphical dependency graph displaying task nodes, active glowing pulse rings, and dependency arrows.
- **Smart Router Interactive Sandbox**: Test model routing recommendations with `speed_first` mode and simulate the Fast-Retry Circuit Breaker with `retry_count >= 2`.
- **One-Click Audit Exporter**: Button to instantly download signed Markdown audit post-mortems.

### REST API Endpoints
- `GET /`: Dashboard Web UI.
- `GET /events`: Server-Sent Events stream (`text/event-stream`).
- `GET /api/state`: Full JSON snapshot of tasks, logs, and metrics.
- `GET /api/models`: Model registry metadata and pricing rates for all 5 tiers.
- `POST /api/router/recommend`: Smart model and reasoning effort recommendation (supporting `budget_mode` and `retry_count`).
- `GET /api/dag/ready`: Evaluate DAG dependencies and return ready unblocked tasks.
- `GET /api/analytics/models`: 5-tier per-model token consumption and financial breakdown.
- `GET /api/audit/export?format=markdown|json`: Export signed mission audit report.
- `POST /api/tasks`: Upsert task status with `reasoning_effort` (`xhigh`), tokens, and dependencies.
- `POST /api/logs`: Append log entry.
- `POST /api/reset`: Reset all task and log states.

---

## 9. Subagent Reporting Protocol & CLI Usage

Subagents report their execution lifecycle via the `client.py` CLI or Python SDK.

### CLI Usage Guide

```bash
# 1. Announce task start with model and reasoning effort (including xhigh on Hydrogen)
python3 packages/orchestrator/client.py update \
  --task TASK-01 \
  --agent builder \
  --status running \
  --progress 15 \
  --model gemini-4-hydrogen \
  --reasoning-effort high \
  --complexity medium \
  --group BUILD-PARALLEL \
  --depends-on TASK-00 \
  --scope "Frontend component implementation" \
  --notes "Initiating parallel build on disjoint file slice"

# 2. Emit telemetry logs
python3 packages/orchestrator/client.py log \
  --task TASK-01 \
  --agent builder \
  --level info \
  --message "Component rendered and passed local type checks"

# 3. Discover next ready unblocked tasks
python3 packages/orchestrator/client.py next-ready

# 4. Mark task completed with token estimates
python3 packages/orchestrator/client.py update \
  --task TASK-01 \
  --agent builder \
  --status completed \
  --progress 100 \
  --input-tokens 24000 \
  --output-tokens 1800 \
  --cache-tokens 65000 \
  --notes "Implementation complete, passed syntax check"

# 5. Export mission audit report
python3 packages/orchestrator/client.py export --format markdown --out mission_audit_report.md
```

### Python SDK Usage

```python
from packages.orchestrator.client import OrchestratorClient

client = OrchestratorClient(base_url="http://localhost:8484")

# Query Smart Router with speed_first budget mode
rec = client.recommend(
    agent_type="builder",
    complexity="medium",
    budget_mode="speed_first",
    retry_count=0
)
print(f"Recommended model: {rec['recommendation']['model']}, effort: {rec['recommendation']['reasoning_effort']}")

# Announce task start on Gemini 4 Hydrogen
client.update_task(
    task_id="TASK-01",
    agent_type="builder",
    status="running",
    progress=20,
    model="gemini-4-hydrogen",
    reasoning_effort="high",
    complexity="medium",
    scope="Core UI component implementation",
    notes="Building with 198 tok/sec velocity"
)

# Stream log or thought
client.log(
    task_id="TASK-01",
    agent_type="builder",
    level="thought",
    message="Rendering UI virtual DOM diff"
)

# Query ready queue
ready = client.next_ready()
print(f"Can fan out: {ready['can_fan_out']}, ready count: {len(ready['ready_tasks'])}")

# Complete task
client.update_task(
    task_id="TASK-01",
    agent_type="builder",
    status="completed",
    progress=100,
    input_tokens=15000,
    output_tokens=1200,
    cache_tokens=45000,
    notes="Zero syntax errors detected"
)
```
