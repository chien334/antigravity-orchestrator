---
name: multi-agent-orchestrator
description: Multi-agent orchestration skill following the 1-Agent = 1-Skill paradigm (addyosmani/agent-skills). Coordinates specialized subagents across the software delivery lifecycle with real-time SSE telemetry, context minimization, 4-tier intelligent model routing (gemini-4-carbon), automated DAG scheduling, and audit exports.
---

# Multi-Agent Orchestrator Skill

## 1. Overview & Mission

The **Multi-Agent Orchestrator** coordinates autonomous subagents to deliver complex software projects with high velocity, zero state drift, and rigorous quality gates. 

Rooted in the **1-Agent = 1-Skill** paradigm popularized by Addy Osmani's agent design patterns, every agent in the fleet operates under a bounded scope, specialized persona, and strict context minimization protocol.

### Core Objectives
1. **Divide and Conquer**: Deconstruct monolithic tasks into discrete, verifiable slices with clear boundary contracts.
2. **Context Minimization**: Prevent token bloat by using pointer-based file references (`file:///...`) and scoped briefings.
3. **4-Tier Intelligent Model Routing**: Dynamically match task complexity to the optimal model tier—featuring **Gemini 4 Carbon** for frontier reasoning and security, **Gemini 4 Argon** for architecture and review, **Gemini 3.8 Flash** for high-throughput building, and **Gemini 3.8 Flash-Lite** for micro-tier telemetry.
4. **Automated DAG Scheduling**: Evaluate task dependencies (`depends_on`) automatically via a ready-queue evaluator for concurrent Fan-Out.
5. **Real-time Observability & Financial Analytics**: Stream subagent progress, telemetry, thoughts, and per-model token expenditure (USD & VND) via Server-Sent Events (SSE) and SQLite.
6. **Audit & Compliance Sign-off**: Export permanent post-mission execution reports in Markdown and structured JSON.

---

## 2. The 9 Specialized Personas (1-Agent = 1-Skill)

Each agent persona maps strictly to a single skill specialty. Agents never cross functional boundaries unless explicitly delegated.

```
+-----------------------------------------------------------------------------------+
|                           Multi-Agent Orchestrator                                |
|             (Task Dispatch, Smart Routing, DAG Ready Queue, SSE Telemetry)        |
+-----------------------------------------------------------------------------------+
                                          |
   +--------------------------------------+-----------------------------------+
   |                    |                 |                 |                 |
   v                    v                 v                 v                 v
[1. Spec]          [2. Plan]         [3. Build]        [4. Test]        [5. Review]
Product Spec       Architect         Software Builder  Test Spec        Code Review
Gemini 4 Carbon    Gemini 4 Argon    Gemini 3.8 Flash  Gemini 3.8 Flash Gemini 4 Argon
   |                    |                 |                 |                 |
   +--------------------+-----------------+-----------------+-----------------+
                                          |
                      +--------------------+--------------------+
                      |                                         |
                      v                                         v
               [6. Security]                              [7. Release]
               Security Specialist                        DevOps & Deployment
               Gemini 4 Carbon (Effort: high)             Gemini 3.8 Flash
```

| # | Persona | Primary Skill & Responsibility | Recommended Model & Effort | Output Artifact | Workflow Runbook |
|---|---------|--------------------------------|----------------------------|-----------------|------------------|
| 1 | **Multi-Agent Orchestrator** | Task scheduling, dependency resolution, SSE telemetry, context dispatch | ✦ **Gemini 4 Argon** (`medium`) | Orchestrator Plan, DAG | [`workflow-pipeline.md`](../../workflows/workflow-pipeline.md) |
| 2 | **Product / Spec Specialist** | Requirements discovery, user stories, acceptance criteria, edge-case matrix | ✦ **Gemini 4 Carbon** (`high`) | `docs/specs/{feature_id}.spec.md` | [`workflow-spec.md`](../../workflows/workflow-spec.md) |
| 3 | **Architect / Planner** | System design, contract definition, database schemas, component topology | ✦ **Gemini 4 Argon** (`medium`/`high`) | `docs/plans/{feature_id}.plan.md` | [`workflow-plan.md`](../../workflows/workflow-plan.md) |
| 4 | **Software Builder** | Code implementation, UI/API development, minimal blast radius edits | ⚡ **Gemini 3.8 Flash** (`None`) | Source Code Files on disk | [`workflow-build.md`](../../workflows/workflow-build.md) |
| 5 | **Test Specialist** | Test suites, mocks, unit tests, integration tests, assertions | ⚡ **Gemini 3.8 Flash** (`None`) | `docs/reports/test_report.json` | [`workflow-test.md`](../../workflows/workflow-test.md) |
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
                                      [Stage 3: Parallel Builders] ──▶ Disjoint Code Files (Gemini 3.8 Flash)
                                                                               │
                                                                               ▼
                                      [Stage 4: Tests] ◀── (Code + Spec AC) ──▶ docs/reports/test_report.json
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

## 4. 4-Tier Intelligent Model Routing Matrix

To maximize precision while keeping operational costs optimal, tasks are dynamically routed across four discrete model tiers:

| Tier | Engine Model | Canonical ID | Input / 1M | Output / 1M | Cache Read / 1M | Tunable Reasoning Effort | Role Specialization & Rationale |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Tier 1: Frontier** | **Gemini 4 Carbon** | `gemini-4-carbon` | **$2.00** | **$10.00** | **$0.50** | `low`, `medium`, `high` | • `security-auditor`: Deep vulnerability modeling, OWASP scans, secret audits.<br>• `spec-engineer`: Formal specification proofs, edge-case discovery.<br>• `debugger`: Complex multi-component root-cause isolation.<br>• Core cryptographic, financial, and authentication logic. |
| **Tier 2: Deep Reasoning** | **Gemini 4 Argon** | `gemini-4-argon` | **$1.25** | **$5.00** | **$0.3125** | `low`, `medium`, `high` | • `task-planner`: Architecture modeling, dependency graphs, sequencing.<br>• `code-reviewer`: 5-axis rigorous review (correctness, architecture, security).<br>• `orchestrator`: Fleet dispatch and synthesis coordination. |
| **Tier 3: Cost-Efficient** | **Gemini 3.8 Flash** | `gemini-3.8-flash` | **$0.075** | **$0.30** | **$0.01875** | `None` | • `builder`: Parallel feature implementation, CRUD, UI components.<br>• `test-engineer`: Unit test suites, mocks, assertion gates.<br>• Saves >70% in token expenditure compared to frontier models. |
| **Tier 4: Ultra-Fast Micro-Tier** | **Gemini 3.8 Flash-Lite** | `gemini-3.8-flash-lite` | **$0.0375** | **$0.15** | **$0.01** | `None` | • `observability-and-instrumentation`: Heartbeats, quick linting, documentation formatting.<br>• Near-zero latency execution. |

### Tunable Reasoning Effort Guidelines (`--reasoning-effort` / `--effort`)
`gemini-4-carbon` and `gemini-4-argon` support tunable thinking depth:
- **`high`**: Activates deep multi-pass reasoning, autonomous verification loops, and vulnerability fuzzing. Use for `security-auditor` on critical tasks, formal PRD specifications, and high-complexity debugging.
- **`medium`** (Default): Balanced deep reasoning for architecture design, 5-axis code reviews, and cross-module contracts.
- **`low`**: Light reasoning check for quick architectural clarifications and sanity checks.

### Smart Router API & CLI
Query the smart router before assigning subagents:
```bash
# Query CLI
python3 packages/orchestrator/client.py recommend \
  --agent security-auditor \
  --complexity critical \
  --security-impact

# REST API: POST /api/router/recommend
# Request Body:
# {
#   "agent_type": "security-auditor",
#   "complexity": "critical",
#   "has_security_impact": true,
#   "budget_mode": "balanced"
# }
# Response:
# {
#   "status": "ok",
#   "recommendation": {
#     "model": "gemini-4-carbon",
#     "reasoning_effort": "high",
#     "tier": "frontier",
#     "rationale": "Critical-tier security audit...",
#     "estimated_cost_tier": "$$$$",
#     "fallback_model": "gemini-4-argon"
#   }
# }
```

---

## 5. Parallel Worker Execution & Automated DAG Ready-Queue

The Orchestrator implements a **Condition-Based Directed Acyclic Graph (DAG)** with automated Fan-Out and Fan-In:

```
                  ┌──▶ [Parallel Worker 1: Frontend UI] (Flash) ──┐
                  │                                                │
[Plan (Argon)] ───┼──▶ [Parallel Worker 2: Backend API] (Flash) ──┼──▶ [Barrier Sync & Fan-In]
                  │                                                │
                  └──▶ [Parallel Worker 3: Data Access] (Flash) ───┘
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

## 6. Context Minimization Protocol

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

## 7. Real-Time Telemetry & Per-Model Financial Analytics

Hospital Suite includes a zero-dependency, real-time Python dashboard powered by SSE (Server-Sent Events) and SQLite.

### Starting the Server
```bash
# Start server on default port 8484
python3 packages/orchestrator/server.py --port 8484

# Or customize port via environment variable
ORCHESTRATOR_PORT=9000 python3 packages/orchestrator/server.py
```

### Dashboard Features (`GET http://localhost:8484/`)
- **Obsidian Emerald Carbon Badges & Reasoning Pills**: Visual indicators for `gemini-4-carbon` and pulsing badges for `reasoning_effort: high`.
- **Per-Model Financial Ledger**: Dedicated breakdown of token consumption (prompt, completion, cache read), USD spend, VND spend (25,400 VND/USD), and cache savings for Carbon, Argon, Flash, and Flash-Lite.
- **Interactive SVG DAG Visualizer**: Graphical dependency graph displaying task nodes, active glowing pulse rings, and dependency arrows.
- **Smart Router Interactive Sandbox**: Test model routing recommendations directly from the Web UI.
- **One-Click Audit Exporter**: Button to instantly download signed Markdown audit post-mortems.

### REST API Endpoints
- `GET /`: Dashboard Web UI.
- `GET /events`: Server-Sent Events stream (`text/event-stream`).
- `GET /api/state`: Full JSON snapshot of tasks, logs, and metrics.
- `GET /api/models`: Model registry metadata and pricing rates.
- `POST /api/router/recommend`: Smart model and reasoning effort recommendation.
- `GET /api/dag/ready`: Evaluate DAG dependencies and return ready unblocked tasks.
- `GET /api/analytics/models`: Per-model token consumption and financial breakdown.
- `GET /api/audit/export?format=markdown|json`: Export signed mission audit report.
- `POST /api/tasks`: Upsert task status with `reasoning_effort`, tokens, and dependencies.
- `POST /api/logs`: Append log entry.
- `POST /api/reset`: Reset all task and log states.

---

## 8. Subagent Reporting Protocol & CLI Usage

Subagents report their execution lifecycle via the `client.py` CLI or Python SDK.

### CLI Usage Guide

```bash
# 1. Announce task start with model and reasoning effort
python3 packages/orchestrator/client.py update \
  --task TASK-01 \
  --agent security-auditor \
  --status running \
  --progress 15 \
  --model gemini-4-carbon \
  --reasoning-effort high \
  --complexity critical \
  --group SEC-AUDIT \
  --depends-on TASK-00 \
  --scope "Deep OWASP & Vulnerability Scan" \
  --notes "Initiating multi-pass reasoning loop"

# 2. Emit telemetry logs
python3 packages/orchestrator/client.py log \
  --task TASK-01 \
  --agent security-auditor \
  --level info \
  --message "Verified authorization boundary contracts; zero leaks detected"

# 3. Discover next ready unblocked tasks
python3 packages/orchestrator/client.py next-ready

# 4. Mark task completed with token estimates
python3 packages/orchestrator/client.py update \
  --task TASK-01 \
  --agent security-auditor \
  --status completed \
  --progress 100 \
  --input-tokens 45000 \
  --output-tokens 3200 \
  --cache-tokens 95000 \
  --notes "Security audit passed with 100% compliance"

# 5. Export mission audit report
python3 packages/orchestrator/client.py export --format markdown --out mission_audit_report.md
```

### Python SDK Usage

```python
from packages.orchestrator.client import OrchestratorClient

client = OrchestratorClient(base_url="http://localhost:8484")

# Query Smart Router
rec = client.recommend(agent_type="security-auditor", complexity="critical", security_impact=True)
print(f"Recommended model: {rec['recommendation']['model']}, effort: {rec['recommendation']['reasoning_effort']}")

# Announce task start
client.update_task(
    task_id="TASK-01",
    agent_type="security-auditor",
    status="running",
    progress=20,
    model="gemini-4-carbon",
    reasoning_effort="high",
    complexity="critical",
    scope="Core cryptography & token validation",
    notes="Analyzing secret signing logic"
)

# Stream log or thought
client.log(
    task_id="TASK-01",
    agent_type="security-auditor",
    level="thought",
    message="Simulating boundary replay conditions"
)

# Query ready queue
ready = client.next_ready()
print(f"Can fan out: {ready['can_fan_out']}, ready count: {len(ready['ready_tasks'])}")

# Complete task
client.update_task(
    task_id="TASK-01",
    agent_type="security-auditor",
    status="completed",
    progress=100,
    input_tokens=25000,
    output_tokens=1800,
    cache_tokens=60000,
    notes="Zero vulnerabilities found"
)
```
