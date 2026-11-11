---
name: workflow-pipeline
description: End-to-End Chained Multi-Agent Pipeline - Orchestrate Spec -> Plan -> Parallel Build -> Test -> Review -> Security with zero context bloat and 4-Tier Model Routing
---

# End-to-End Multi-Agent Pipeline Workflow

## 1. Pipeline Overview & Handoff Graph

This workflow orchestrates the complete software delivery lifecycle across 6 sequential and parallel stages, passing **file pointers instead of raw context** to keep subagents focused and hallucination-free. It leverages the **4-Tier Intelligent Model Routing matrix** featuring **Gemini 4 Carbon** for frontier reasoning and security, **Gemini 4 Argon** for architecture and review, and **Gemini 3.8 Flash** for parallel execution.

```mermaid
flowchart TD
    Start([User Request]) --> S1[1. workflow-spec\nModel: Gemini 4 Carbon\nEffort: high]
    S1 -->|docs/specs/feature.spec.md| S2[2. workflow-plan\nModel: Gemini 4 Argon\nEffort: medium/high]
    
    S2 -->|Task DAG & Boundaries| S3Ready{DAG Ready-Queue\nGET /api/dag/ready}
    S3Ready -->|Fan-Out BUILD-PARALLEL| S3A[3A. Worker 1: Frontend\nModel: Gemini 3.8 Flash]
    S3Ready -->|Fan-Out BUILD-PARALLEL| S3B[3B. Worker 2: Backend\nModel: Gemini 3.8 Flash]
    S3Ready -->|Fan-Out BUILD-PARALLEL| S3C[3C. Worker 3: Database\nModel: Gemini 3.8 Flash]
    
    S3A --> S3Sync{Barrier Sync\nFan-In}
    S3B --> S3Sync
    S3C --> S3Sync
    
    S3Sync -->|Code Files + Spec Criteria| S4[4. workflow-test\nModel: Gemini 3.8 Flash]
    S4 -->|docs/reports/test_report.json| S5[5. workflow-review\nModel: Gemini 4 Argon\nEffort: high]
    S5 -->|docs/reviews/review_signoff.md| S6[6. workflow-security\nModel: Gemini 4 Carbon\nEffort: high]
    S6 -->|docs/security/security_audit.md| Audit[Audit Exporter\nGET /api/audit/export]
    Audit --> Done([Ship / Release Ready])
```

---

## 2. Stage-by-Stage Input/Output Contract Summary

| Stage | Workflow File | Persona | Model Engine | Reasoning Effort | Input Pointer | Output Artifact |
| :---: | :--- | :--- | :---: | :---: | :--- | :--- |
| **1** | [`workflow-spec.md`](./workflow-spec.md) | `spec-engineer` | ✦ **Gemini 4 Carbon** | `high` | User request & codebase context | `docs/specs/{feature_id}.spec.md` |
| **2** | [`workflow-plan.md`](./workflow-plan.md) | `task-planner` | ✦ **Gemini 4 Argon** | `medium` / `high` | `docs/specs/{feature_id}.spec.md` | `docs/plans/{feature_id}.plan.md` |
| **3** | [`workflow-build.md`](./workflow-build.md) | `builder` (1..N) | ⚡ **Gemini 3.8 Flash** | `None` | Task slice from `.plan.md` | Code changes on disjoint files |
| **4** | [`workflow-test.md`](./workflow-test.md) | `test-engineer` | ⚡ **Gemini 3.8 Flash** | `None` | Code + Gherkin AC from `.spec.md` | `docs/reports/test_report.json` |
| **5** | [`workflow-review.md`](./workflow-review.md) | `code-reviewer` | ✦ **Gemini 4 Argon** | `high` | Git Diff + `.plan.md` + test report | `docs/reviews/review_signoff.md` |
| **6** | [`workflow-security.md`](./workflow-security.md) | `security-auditor`| ✦ **Gemini 4 Carbon** | `high` | Code diff + `review_signoff.md` | `docs/security/security_audit.md` |

---

## 3. Orchestrator Dispatch Protocol (How to Chain)

When running the pipeline, the Orchestrator invokes subagents sequentially and in parallel using pointer references:

### Step 0: Smart Model Recommendation (Optional / Dynamic)
Before dispatching any complex task, query the Smart Router to dynamically determine the optimal model, reasoning effort, and fallback:
```bash
python3 packages/orchestrator/client.py recommend --agent spec-engineer --complexity critical --security-impact
```

### Step 1 ➔ Step 2 Handoff:
```python
# Orchestrator invokes task-planner with the path to the spec:
invoke_subagent(
    typeName="task-planner",
    Role="Architect & Task Planner",
    Model="pro",  # Gemini 4 Argon
    Prompt="""
Read the approved specification at file:///path/to/docs/specs/{feature_id}.spec.md.
Design the system architecture, component boundaries, database schemas, and create docs/plans/{feature_id}.plan.md
with a complete task DAG, parallel groups, and 4-tier model assignments according to workflow-plan.
"""
)
```

### Step 2 ➔ Step 3 Automated DAG Ready-Queue Discovery & Parallel Fan-Out:
Before dispatching builder workers, query the DAG ready queue to find all unblocked tasks:
```bash
python3 packages/orchestrator/client.py next-ready
```

When 2 or more tasks are ready simultaneously, dispatch them concurrently in the same turn:
```python
# Orchestrator dispatches parallel builders in the same turn:
invoke_subagent(
    typeName="builder",
    Role="Frontend Builder Worker",
    Model="flash",  # Gemini 3.8 Flash
    Prompt="""
Execute Task BUILD-01 from file:///path/to/docs/plans/{feature_id}.plan.md.
Scope is strictly limited to frontend/src/components/....
Report progress and tokens via python3 packages/orchestrator/client.py update --task BUILD-01 --model gemini-3.8-flash.
"""
)

invoke_subagent(
    typeName="builder",
    Role="Backend Builder Worker",
    Model="flash",  # Gemini 3.8 Flash
    Prompt="""
Execute Task BUILD-02 from file:///path/to/docs/plans/{feature_id}.plan.md.
Scope is strictly limited to backend/api/....
Report progress and tokens via python3 packages/orchestrator/client.py update --task BUILD-02 --model gemini-3.8-flash.
"""
)
```

### Step 3 ➔ Step 4 Barrier Sync:
Wait until all tasks in the parallel group report `status == "completed"` in SQLite (`packages/orchestrator/orchestrator.db`), then dispatch `test-engineer`.

### Step 4 ➔ Step 5 ➔ Step 6 Verification Gate:
- Pass `docs/reports/test_report.json` to `code-reviewer` (Gemini 4 Argon).
- If review status is `APPROVED`, pass `docs/reviews/review_signoff.md` to `security-auditor` with **Gemini 4 Carbon** (`reasoning_effort: high`).
- If any stage reports failures, escalate to `debugger` (Gemini 4 Carbon) before repeating.

### Post-Mission Step: Audit Export
Export the permanent mission audit report:
```bash
python3 packages/orchestrator/client.py export --format markdown --out docs/reports/mission_audit_report.md
```
