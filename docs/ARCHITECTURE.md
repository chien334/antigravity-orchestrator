# Architecture Specification: Multi-Agent Orchestrator

## 1. System Overview

The **Multi-Agent Orchestrator** coordinates autonomous subagents under a bounded, **1-Agent = 1-Skill** paradigm with zero context bloat, 4-tier dynamic model routing, condition-based parallel execution, and live SSE + SQLite telemetry.

```mermaid
graph TD
    Client[Antigravity CLI / User] -->|/orchestrator| Orchestrator[Fleet Orchestrator]
    
    subgraph Routing["Smart Routing & Scheduling"]
        Router[Smart Model Router\nPOST /api/router/recommend]
        ReadyQueue[DAG Ready-Queue Evaluator\nGET /api/dag/ready]
    end
    Orchestrator --> Router
    Orchestrator --> ReadyQueue

    subgraph Pipeline["6-Stage Artifact Handoff Pipeline"]
        Spec["Stage 1: spec-engineer<br/>✦ <strong>Gemini 4 Carbon</strong> (effort: high)<br/>docs/specs/*.spec.md"]
        Plan["Stage 2: task-planner<br/>✦ <strong>Gemini 4 Argon</strong> (effort: high)<br/>docs/plans/*.plan.md"]
        
        subgraph Stage3["Stage 3: Parallel Fan-Out (BUILD-PARALLEL)"]
            FE["Worker 1: Frontend UI<br/>⚡ Gemini 3.8 Flash"]
            BE["Worker 2: Backend Core<br/>⚡ Gemini 3.8 Flash"]
            DB["Worker 3: DB / Storage<br/>⚡ Gemini 3.8 Flash"]
        end

        Barrier[Barrier Synchronization\nFan-In]
        Test["Stage 4: test-engineer<br/>⚡ Gemini 3.8 Flash<br/>docs/reports/*.json"]
        Review["Stage 5: code-reviewer<br/>✦ <strong>Gemini 4 Argon</strong> (effort: high)<br/>docs/reviews/*.md"]
        Sec["Stage 6: security-auditor<br/>✦ <strong>Gemini 4 Carbon</strong> (effort: high)<br/>docs/security/*.md"]
        Audit["Mission Audit Exporter<br/>GET /api/audit/export"]
    end

    Orchestrator -->|Stage 1| Spec
    Spec -->|Pointer| Plan
    Plan --> ReadyQueue
    ReadyQueue -->|Unblocked Ready Set| FE & BE & DB
    FE & BE & DB --> Barrier
    Barrier --> Test
    Test --> Review
    Review --> Sec
    Sec --> Audit
    Audit --> Release[Production Release]

    subgraph Telemetry["Observability & Persistence Engine"]
        DB_Engine[(SQLite: orchestrator.db\nWAL Mode)]
        Analytics[Per-Model Financial Ledger\nGET /api/analytics/models]
        SSE[SSE Stream /events\n15s Ping Keepalive]
        Dashboard[Web Dashboard UI :8484\nTailwind + SVG DAG]
    end

    Orchestrator -.->|Record Tokens & Effort| DB_Engine
    FE & BE & DB -.->|Task Updates| DB_Engine
    DB_Engine --> Analytics
    DB_Engine -.-> SSE
    SSE -.-> Dashboard
```

---

## 2. Core Subsystems

### 2.1 State & Persistence Engine (SQLite 3)
- Thread-safe access via mutex-guarded standard library `sqlite3`.
- Active WAL (Write-Ahead Logging) mode and `synchronous=NORMAL` for concurrent non-blocking readers and writer.
- **Non-Destructive Schema Migration**:
  - Automatically adds `reasoning_effort TEXT DEFAULT NULL` to the `tasks` table if absent upon startup.
  - Generates index `idx_tasks_model` on `tasks(model)` for sub-millisecond per-model aggregation queries.
- Persistent tables:
  * `tasks`: Stores `task_id`, `agent_type`, `model`, `reasoning_effort`, `complexity`, `status`, `progress`, `scope`, `notes`, `conv_id`, `depends_on`, `parallel_group`, `input_tokens`, `output_tokens`, `cache_tokens`, `total_tokens`, `created_at`, `updated_at`.
  * `logs`: Time-series event stream capped at 1000 items with levels (`info`, `warn`, `error`, `thought`).

### 2.2 4-Tier Intelligent Model Routing Subsystem (`MODEL_REGISTRY`)
The runtime matches task requirements against four distinct capability and financial tiers:

| Tier | Canonical Name | Target Personas | Pricing (In / Out / Cache per 1M) | Supported Reasoning Efforts | Rationale |
|---|---|---|---|:---:|---|
| **Frontier** | `gemini-4-carbon` | `security-auditor`, `spec-engineer`, `debugger` | **$2.00 / $10.00 / $0.50** | `low`, `medium`, `high` | Google Frontier model for deep multi-pass reasoning, autonomous verification loops, and vulnerability fuzzing. |
| **Deep Reasoning** | `gemini-4-argon` | `task-planner`, `code-reviewer`, `orchestrator` | **$1.25 / $5.00 / $0.3125** | `low`, `medium`, `high` | High-velocity deep reasoning for architectural topology, DAG scheduling, and 5-axis code reviews. |
| **Cost-Efficient** | `gemini-3.8-flash` | `builder`, `test-engineer`, `code-simplifier` | **$0.075 / $0.30 / $0.01875** | `None` | Ultra-fast parallel code generation and unit testing (>70% cost savings). |
| **Ultra-Fast** | `gemini-3.8-flash-lite` | `observability-and-instrumentation` | **$0.0375 / $0.15 / $0.01** | `None` | Micro-tier for telemetry heartbeats, linting, and doc formatting. |

- **Smart Model Recommender (`recommend_model`)**:
  - Evaluates persona, complexity (`low`, `medium`, `high`, `critical`), security impact, and budget mode (`balanced` vs `quality_first`).
  - Returns recommended model, reasoning effort, tier, rationale, and automatic fallback.

### 2.3 Condition-Based DAG Ready-Queue Evaluator
- Evaluates task prerequisite relationships via `depends_on`.
- Endpoint `GET /api/dag/ready` identifies all `pending` tasks whose prerequisite tasks are all `completed`.
- Automatically sets `can_fan_out = True` when two or more tasks are ready to run concurrently, identifying the target `fan_out_group`.
- Ensures the **Decoupled File Scope Invariant**: parallel builder workers must only edit non-overlapping file sets.

### 2.4 Per-Model Financial Analytics & Token Telemetry
- Measures:
  * Prompt Tokens (`input_tokens`)
  * Completion Tokens (`output_tokens`)
  * Antigravity Cache Read Tokens (`cache_tokens`)
  * Total Token Footprint
  * Cache Hit Rate Percentage (`cache_tokens / (input_tokens + cache_tokens) * 100`)
- Financial Calculation:
  * Converts token usage to actual USD cost based on `MODEL_REGISTRY` rates.
  * Calculates cache savings: `baseline_cost_without_cache - actual_cost`.
  * Multiplies by the fixed exchange rate `USD_TO_VND_RATE = 25400.0` for local currency reporting.
- Endpoint `GET /api/analytics/models` provides per-model breakdowns and global mission summaries.

### 2.5 Mission Audit Exporter
- Endpoint `GET /api/audit/export?format=markdown|json` and CLI `client.py export`.
- Compiles the full execution transcript:
  1. Per-Model Consumption & Financial Ledger table.
  2. Complete Task Execution Matrix with status, reasoning efforts, progress, and file scopes.
  3. Verification and compliance signatures.

---

## 3. Reliability & Zero-Dependency Guarantees
- Strictly uses standard library Python 3.10+: `sqlite3`, `http.server`, `urllib`, `json`, `argparse`, `threading`, `time`.
- No external Python package managers or pip installations required (`requirements.txt` is empty/stdlib-only).
- Web Dashboard is rendered as a standalone vanilla HTML/JS single-page application with embedded SVG graphs and responsive Tailwind CSS.
