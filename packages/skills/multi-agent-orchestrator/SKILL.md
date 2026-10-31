---
name: multi-agent-orchestrator
description: Multi-agent orchestration skill following the 1-Agent = 1-Skill paradigm (addyosmani/agent-skills). Coordinates specialized subagents across the software delivery lifecycle with real-time SSE telemetry, context minimization, and structured task reporting.
---

# Multi-Agent Orchestrator Skill

## 1. Overview & Mission

The **Multi-Agent Orchestrator** coordinates autonomous subagents to deliver complex software projects with high velocity, zero state drift, and rigorous quality gates. 

Rooted in the **1-Agent = 1-Skill** paradigm popularized by Addy Osmani's agent design patterns, every agent in the fleet operates under a bounded scope, specialized persona, and strict context minimization protocol.

### Core Objectives
1. **Divide and Conquer**: Deconstruct monolithic tasks into discrete, verifiable slices with clear boundary contracts.
2. **Context Minimization**: Prevent token bloat by using pointer-based file references and scoped briefings.
3. **Real-time Observability**: Stream subagent progress, telemetry, and thoughts via Server-Sent Events (SSE) to a live dark-mode dashboard.
4. **Resilient Feedback Loops**: Enforce verification gates (lint, build, unit tests, security scans) before advancing pipeline stages.

---

## 2. The 9 Specialized Personas (1-Agent = 1-Skill)

Each agent persona maps strictly to a single skill specialty. Agents never cross functional boundaries unless explicitly delegated.

```
+-----------------------------------------------------------------------------------+
|                           Multi-Agent Orchestrator                                |
|                  (Task Dispatch, Telemetry, Dependency DAG)                       |
+-----------------------------------------------------------------------------------+
                                          |
   +--------------------------------------+-----------------------------------+
   |                    |                 |                 |                 |
   v                    v                 v                 v                 v
[1. Spec]          [2. Plan]         [3. Build]        [4. Test]        [5. Review]
Product Spec       Architect         Software Builder  Test Spec        Code Review
   |                    |                 |                 |                 |
   +--------------------+-----------------+-----------------+-----------------+
                                          |
                     +--------------------+--------------------+
                     |                                         |
                     v                                         v
              [6. Security]                              [7. Release]
              Security Specialist                        DevOps & Deployment
```

| # | Persona | Primary Skill & Responsibility | Output Artifact | Workflow Runbook |
|---|---------|--------------------------------|-----------------|------------------|
| 1 | **Multi-Agent Orchestrator** | Task scheduling, dependency resolution, SSE telemetry, context dispatch | Orchestrator Plan, DAG | [workflow-pipeline.md](file:///home/andrew/hospital-suite/.agents/workflows/workflow-pipeline.md) |
| 2 | **Product / Spec Specialist** | Requirements discovery, user stories, acceptance criteria, edge-case matrix | `docs/specs/{feature_id}.spec.md` | [workflow-spec.md](file:///home/andrew/hospital-suite/.agents/workflows/workflow-spec.md) |
| 3 | **Architect / Planner** | System design, contract definition, database schemas, component topology | `docs/plans/{feature_id}.plan.md` | [workflow-plan.md](file:///home/andrew/hospital-suite/.agents/workflows/workflow-plan.md) |
| 4 | **Software Builder** | Code implementation, UI/API development, minimal blast radius edits | Source Code Files on disk | [workflow-build.md](file:///home/andrew/hospital-suite/.agents/workflows/workflow-build.md) |
| 5 | **Test Specialist** | Test suites, mocks, unit tests, integration tests, E2E fixtures | `docs/reports/test_report.json` | [workflow-test.md](file:///home/andrew/hospital-suite/.agents/workflows/workflow-test.md) |
| 6 | **Code Reviewer** | Code quality inspection, anti-pattern detection, style invariants | `docs/reviews/review_signoff.md` | [workflow-review.md](file:///home/andrew/hospital-suite/.agents/workflows/workflow-review.md) |
| 7 | **Security Specialist** | Threat modeling, OWASP verification, secret scanning, RBAC checks | `docs/security/security_audit.md` | [workflow-security.md](file:///home/andrew/hospital-suite/.agents/workflows/workflow-security.md) |
| 8 | **Performance Specialist** | Profiling, query latency optimization, bundle size, caching | Benchmark Reports, Tuning Diffs | - |
| 9 | **Release / DevOps Specialist** | CI/CD pipelines, containerization, migration safety, rollbacks | Dockerfiles, Migration Scripts | - |

---

## 2.0 Handoff Pipeline & Artifact Data Contracts (Output(N) ➔ Input(N+1))

Every stage delivers an explicit, structured file artifact that serves as the strictly bounded input for the next stage. Raw conversation histories are never passed directly to subagents; instead, only the target artifact path is provided:

```
[User Request]
       │
       ▼
[Stage 1: Spec] ──▶ docs/specs/{feature_id}.spec.md
                           │
                           ▼
                   [Stage 2: Plan] ──▶ docs/plans/{feature_id}.plan.md (with Task DAG)
                                               │
                                               ▼
                                      [Stage 3: Parallel Builders] ──▶ Code Files on Disk
                                                                               │
                                                                               ▼
                                      [Stage 4: Tests] ◀── (Code + Spec AC)
                                               │
                                               ▼ docs/reports/test_report.json
                                      [Stage 5: Review] ──▶ docs/reviews/review_signoff.md
                                                                      │
                                                                      ▼
                                                              [Stage 6: Security] ──▶ docs/security/security_audit.md
                                                                                              │
                                                                                              ▼
                                                                                      [Stage 7: Release]
```

---

## 2.1 Dynamic Model Selection & Tiering Matrix

To balance high precision reasoning with cost efficiency, subagents are dynamically allocated models based on task complexity and error criticality:

| Complexity Tier | Engine Model | `invoke_subagent` Model | Role Specialization & Rationale |
| :--- | :--- | :---: | :--- |
| **CRITICAL / HIGH** | **Gemini 4 Argon** (Deep Reasoning) | `"pro"` | - `spec-engineer`: Eliminating ambiguity, identifying boundary edges, PRD precision.<br>- `task-planner`: Architecture modeling, dependency graphs, sequencing.<br>- `security-auditor`: Deep vulnerability discovery, OWASP modeling, auth/authz audits.<br>- `code-reviewer`: 5-axis rigorous review (correctness, architecture, security).<br>- `debugger`: Complex multi-component root-cause isolation and reasoning.<br>- Core cryptographic, financial, or medical data logic. |
| **MEDIUM / LOW** | **Gemini 3.8 Flash** (Cost-Efficient) | `"flash"` / `"flash_lite"` | - `builder`: Standard boilerplate, UI components, CRUD handlers, CSS styling.<br>- `test-engineer`: Standard unit assertions, mock factories, test runs.<br>- `code-simplifier`: Dead code cleanup, flattening nested blocks.<br>- `performance-auditor`: Standard Core Web Vitals profiling. |

### Dynamic Escalation Rules:
1. **Critical Domain Escalation**: If an implementation task touches cryptographic keys, authentication state, or critical database schema migrations, escalate to `pro` (Gemini 4 Argon).
2. **Defect Escalation**: When a test fails or unexpected bugs occur, immediately escalate diagnostic responsibility to `debugger` with `pro` (Gemini 4 Argon).
3. **Telemetry Tracking**: Always include `--model` and `--complexity` when updating task status via `tools/orchestrator/client.py`.

---

## 2.2 Parallel Worker Execution & Condition-Based DAG (Fan-Out / Fan-In)

Rather than executing tasks in a rigid single-threaded pipeline, the Orchestrator implements a **Condition-Based Directed Acyclic Graph (DAG)** with automated Fan-Out and Fan-In capabilities:

```
            ┌──▶ [Parallel Worker 1: Frontend UI] (Flash) ──┐
            │                                                │
[Plan (Argon)] ──┼──▶ [Parallel Worker 2: Backend API] (Flash) ──┼──▶ [Barrier Sync & Fan-In]
            │                                                │
            └──▶ [Parallel Worker 3: Unit Tests] (Flash) ───┘
```

### Core Concurrency Invariants:
1. **Prerequisite Conditions (`depends_on`)**:
   - Each task specifies prerequisite dependencies via `depends_on: ["TASK-ID"]`.
   - A task enters the `READY` state only when all tasks in `depends_on` have reached `status == "completed"`.
2. **Multi-Worker Fan-Out**:
   - When 2 or more tasks are in the `READY` state simultaneously, the Orchestrator **dispatches them concurrently in the same turn** by invoking multiple subagents back-to-back (`invoke_subagent`).
   - Group them using `--group <GROUP-NAME>` (e.g. `BUILD-PARALLEL`, `AUDIT-FANOUT`).
3. **Decoupled File Scope Invariant**:
   - Parallel builder workers MUST operate on disjoint, non-overlapping file paths (e.g., `frontend/...` vs `backend/...`).
   - Read-only auditors (`code-reviewer`, `security-auditor`, `performance-auditor`) can safely analyze the same codebase simultaneously without conflict.
4. **Barrier Synchronization (Fan-In)**:
   - When all subagents in a parallel group finish their assignments, the Orchestrator synthesizes outputs, validates cross-cutting contracts, and advances to dependent stages.

---

## 3. Context Minimization Protocol

Context window exhaustion is the primary source of hallucinations and drift in LLM agent swarms. The Orchestrator enforces:

1. **Pointers Over Copies**:
   - Never copy entire files into prompts.
   - Reference files using exact absolute paths and line numbers:
     `[server.py](file:///home/andrew/hospital-suite/tools/orchestrator/server.py#L45-L80)`.
2. **Strictly Bounded Slices**:
   - Limit each subagent assignment to a maximum of 1-3 target files and 1 discrete objective.
3. **Structured Handoff Summaries**:
   - When a subagent completes a task, it reports:
     - Exact files modified or created.
     - Verification command and output.
     - Brief 2-3 sentence execution summary.
4. **No Sprawl**:
   - Subagents must not introduce speculative abstractions or modify unassigned files.

---

## 4. Real-Time Telemetry & Dashboard

Hospital Suite includes a zero-dependency, real-time Python dashboard powered by SSE (Server-Sent Events) and REST endpoints.

### Starting the Server
```bash
# Start server on default port 8484
python3 tools/orchestrator/server.py

# Or customize port via flag or environment variable
python3 tools/orchestrator/server.py --port 9000
ORCHESTRATOR_PORT=9000 python3 tools/orchestrator/server.py
```

### Dashboard Features (`GET http://localhost:8484/`)
- **Modern Dark UI**: Built with Tailwind CSS and typography suited for developer consoles.
- **Pipeline Stage Visualizer**: Tracks progress across the 7 stages (`Spec` -> `Plan` -> `Build` -> `Test` -> `Review` -> `Security` -> `Ship`).
- **Metric Cards**: Real-time counter of Total Tasks, In Progress, Completed, Blocked, and Active Agents.
- **Live Task Table**: Dynamic progress bars, agent badges, scope, notes, and last updated timestamps.
- **Live Log Stream**: Console log stream with severity filtering (`info`, `warn`, `error`, `thought`) and autoscroll.
- **Zero-Latency SSE**: JavaScript EventSource listener connected to `/events` with automated reconnects.

### REST API Endpoints
- `GET /`: Dashboard Web UI.
- `GET /events`: Server-Sent Events stream (`text/event-stream`).
- `GET /api/state`: Full JSON snapshot of tasks, logs, and metrics.
- `POST /api/tasks`: Upsert task status.
  ```json
  {
    "task_id": "TASK-01",
    "agent_type": "builder",
    "status": "running",
    "progress": 45,
    "scope": "Implement SSE handlers",
    "notes": "Compiling endpoints",
    "conv_id": "conv-123"
  }
  ```
- `POST /api/logs`: Append log entry.
  ```json
  {
    "task_id": "TASK-01",
    "agent_type": "builder",
    "level": "info",
    "message": "Handler unit test passed"
  }
  ```
- `POST /api/reset`: Reset all task and log states.

---

## 5. Subagent Reporting Protocol

Subagents report their execution lifecycle in two ways: via Python library or via CLI command.

### CLI Usage (Recommended in Shell Scripts or Agent Commands)
```bash
# 1. Announce task start
python3 tools/orchestrator/client.py update \
  --task TASK-01 \
  --agent builder \
  --status running \
  --progress 10 \
  --scope "Build API endpoints" \
  --notes "Setting up HTTP handler"

# 2. Emit telemetry logs
python3 tools/orchestrator/client.py log \
  --task TASK-01 \
  --agent builder \
  --level info \
  --message "Compiling server.py and verifying routes"

# 3. Report progress milestone
python3 tools/orchestrator/client.py update \
  --task TASK-01 \
  --agent builder \
  --status running \
  --progress 75 \
  --notes "Unit tests passing"

# 4. Mark task completed
python3 tools/orchestrator/client.py update \
  --task TASK-01 \
  --agent builder \
  --status completed \
  --progress 100 \
  --notes "Delivered all endpoints with SSE verification"
```

### Python Library Usage
```python
from tools.orchestrator.client import OrchestratorClient

client = OrchestratorClient(base_url="http://localhost:8484")

# Update task status
client.update_task(
    task_id="TASK-02",
    agent_type="tester",
    status="running",
    progress=30,
    scope="Integration tests for SSE stream",
    notes="Running mock subscriber test suite"
)

# Stream thought or log
client.log(
    task_id="TASK-02",
    agent_type="tester",
    level="thought",
    message="Inspecting event-stream buffer flush behavior"
)

# Finish task
client.update_task(
    task_id="TASK-02",
    agent_type="tester",
    status="completed",
    progress=100,
    notes="All integration tests green"
)
```

---

## 6. Execution Lifecycle & Escalation Matrix

```
[Pending] ---> [Running] ---> [Completed]
                   |
                   v
             [Blocked / Failed] ---> [Orchestrator Escalation]
```

### Status Invariants:
- **`pending`**: Task is queued in dependency graph awaiting upstream completion.
- **`running`**: Subagent is actively executing. `progress` should be between `1` and `99`.
- **`completed`**: All verification gates passed. `progress` is set to `100`.
- **`blocked`**: Subagent cannot proceed due to missing dependency, environment error, or ambiguous spec.
- **`failed`**: Verification gate failed or unrecoverable error encountered.

### Escalation Protocol:
1. Subagent transitions task to `blocked` or `failed` with descriptive notes.
2. Subagent logs an `error` level event with error trace.
3. Subagent uses `send_message` back to Orchestrator detailing the obstacle.
4. Orchestrator inspects `/api/state`, adjusts task dependencies, or dispatches a specialized fixer agent (e.g. Architect or Test Specialist).
