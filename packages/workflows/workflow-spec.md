---
name: workflow-spec
description: Stage 1 Spec Workflow - Dual-Channel requirements analysis producing docs/specs/{feature_id}.spec.md via Channel A Gemini.app Desktop (when preflight reports HYBRID_60_DESKTOP, $0.00 API spend), Channel B Gemini 4 Neon fallback, or Gemini 4 Carbon (security/critical)
---

# Stage 1: Specification Engineering Workflow

## 1. Objective & Persona
- **Persona**: `spec-engineer`
- **Dual-Channel Model & Dispatch Routing** (governed by Turn-1 `python3 ~/.gemini/tools/orchestrator/client.py preflight --workspace .`):
  - **Non-Security / Standard Specs when `EXECUTION_MODE: HYBRID_60_DESKTOP` (`desktop_ready == true`, Default)**:
    🖥️ **Channel A — `gemini-desktop-app`** (`$0.00` AGY API spend, `0` focus switches, `mode="task"`, `allow_edits=False` — omit `--allow-edits`).
    **HARD INVARIANT**: Do **NOT** dispatch non-security `spec-engineer` to an AGY `pro`/`inherit` `invoke_subagent` when `desktop_ready == true`! Dispatch via `run_command` (`WaitMsBeforeAsync: 500`):
    ```bash
    python3 ~/.gemini/tools/orchestrator/client.py desktop-ask \
      --task "SPEC-{FEATURE}" \
      --agent spec-engineer \
      --workspace . \
      --output "docs/reports/desktop_worker/SPEC-{FEATURE}.md" \
      --prompt "Analyze requirements and codebase for {FEATURE}. Produce a complete specification (Background, Formal Invariants, Gherkin Acceptance Criteria, Edge-Case Matrix) to save as docs/specs/{feature_id}.spec.md. Read-only analysis only."
    ```
  - **Non-Security / Standard Specs when `EXECUTION_MODE: API_ONLY_100` (`desktop_ready == false`)**:
    ⚡✦ **Channel B — Gemini 4 Neon** (`invoke_subagent(Model="pro")` or `"inherit"`, `--model gemini-4-neon`, `reasoning_effort: high`), delivering ~32% lower cost/task and ~2x throughput vs Carbon.
  - **Security / Critical Specs (`has_security_impact=True` or `complexity == "critical"` or `quality_first`)**:
    ✦ **Channel B — Gemini 4 Carbon** (`invoke_subagent(Model="pro")`, `--model gemini-4-carbon`, `reasoning_effort: high`).  
    *Rule 1 Guardrail: Security-impacting specs (`has_security_impact=True`, auth/crypto/OWASP/CVE/migration) NEVER offload to Desktop and NEVER downgrade.*
- **Primary Skill**: `spec-driven-development` *(+ `gemini-desktop-worker` when Channel A Desktop is active)*

---

## 2. Input Contract
- **Source**: User request, bug description, or feature brief.
- **Context Provided**:
  * Functional goals and business constraints.
  * Codebase pointers gathered via fast `gemini-4-hydrogen` scouts (`invoke_subagent(Model="flash")`) under the **Scout-Then-Architect** pattern (or mounted directly in `Gemini.app` Task mode via `--workspace .`).

---

## 3. Execution Steps
1. **Emit Start Telemetry**:
   ```bash
   # Use --model gemini-desktop-app for Channel A, gemini-4-neon for API_ONLY_100, or gemini-4-carbon for security/critical
   python3 ~/.gemini/tools/orchestrator/client.py update \
     --task "SPEC-{FEATURE}" \
     --agent "spec-engineer" \
     --model "gemini-desktop-app" \
     --complexity "high" \
     --status "running" \
     --progress 20 \
     --scope "Requirements & Edge-Case Discovery" \
     --notes "Dispatched to Channel A Gemini.app Desktop ($0.00 API spend)"
   ```
2. **Ambiguity Resolution & Deep Reasoning**:
   - Identify implicit assumptions, non-functional requirements (latency, security, concurrency), and edge cases.
   - Formulate formal verification invariants and Gherkin acceptance scenarios.
3. **Artifact Generation**: Produce `docs/specs/{feature_id}.spec.md` following the standard schema below (from Channel A `docs/reports/desktop_worker/SPEC-{FEATURE}.md` output or Channel B subagent).
4. **Emit Completion Telemetry**:
   ```bash
   python3 ~/.gemini/tools/orchestrator/client.py update \
     --task "SPEC-{FEATURE}" \
     --agent "spec-engineer" \
     --model "gemini-desktop-app" \
     --status "completed" \
     --progress 100 \
     --scope "docs/specs/{feature_id}.spec.md" \
     --notes "Spec complete with acceptance criteria, edge cases, and verification invariants"
   ```

---

## 4. Output Contract (Artifact Schema)
Save to: `docs/specs/{feature_id}.spec.md`

```markdown
# Feature Specification: {Feature Name}

## 1. Background & Business Value
- **Problem Statement**: ...
- **Target Persona**: ...

## 2. Formal Verification Invariants
- **Invariant 1**: ...
- **Invariant 2**: ...

## 3. User Stories & Acceptance Criteria (Gherkin format)
```gherkin
Feature: Feature Name
  Scenario: Happy path execution
    Given ...
    When ...
    Then ...
```

## 4. Edge-Case Matrix
| Scenario | Boundary Condition | Expected Behavior |
|---|---|---|
| ... | ... | ... |
```

> **Handoff**: The completed spec `docs/specs/{feature_id}.spec.md` is passed directly as a pointer to **Stage 2 (`workflow-plan`)**.
