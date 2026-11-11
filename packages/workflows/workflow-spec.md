---
name: workflow-spec
description: Stage 1 Spec Workflow - Analyze requirements, user stories, boundary conditions, and produce docs/specs/{feature_id}.spec.md using Gemini 4 Carbon
---

# Stage 1: Specification Engineering Workflow

## 1. Objective & Persona
- **Persona**: `spec-engineer`
- **Model Engine**: ✦ **Gemini 4 Carbon** (`model: gemini-4-carbon`, `reasoning_effort: high`)
- **Primary Skill**: `spec-driven-development`

---

## 2. Input Contract
- **Source**: User request, bug description, or feature brief.
- **Context Provided**:
  * Functional goals and business constraints.
  * Existing architectural guidelines or pointers to relevant modules.

---

## 3. Execution Steps
1. **Emit Start Telemetry**:
   ```bash
   python3 packages/orchestrator/client.py update \
     --task "SPEC-{FEATURE}" \
     --agent "spec-engineer" \
     --model "gemini-4-carbon" \
     --effort "high" \
     --complexity "critical" \
     --status "running" \
     --progress 20 \
     --scope "Requirements & Edge-Case Discovery" \
     --notes "Analyzing user stories and boundary conditions with Gemini 4 Carbon"
   ```
2. **Ambiguity Resolution & Deep Reasoning**:
   - Activate deep frontier reasoning to identify implicit assumptions, non-functional requirements (latency, security, concurrency), and edge cases.
   - Formulate formal verification invariants and acceptance scenarios.
3. **Artifact Generation**: Produce `docs/specs/{feature_id}.spec.md` following the standard schema below.
4. **Emit Completion Telemetry**:
   ```bash
   python3 packages/orchestrator/client.py update \
     --task "SPEC-{FEATURE}" \
     --agent "spec-engineer" \
     --model "gemini-4-carbon" \
     --effort "high" \
     --status "completed" \
     --progress 100 \
     --scope "docs/specs/{feature_id}.spec.md" \
     --notes "Spec complete with acceptance criteria, edge cases, and frontier reasoning invariants"
   ```

---

## 4. Output Contract (Artifact Schema)
Save to: `docs/specs/{feature_id}.spec.md`

```markdown
# Feature Specification: {Feature Name}

- **Feature ID**: {feature_id}
- **Author**: spec-engineer (Gemini 4 Carbon, reasoning_effort: high)
- **Status**: APPROVED
- **Date**: {YYYY-MM-DD}

## 1. Problem Statement & User Value
- What user problem does this solve?
- What is the business or clinical impact?

## 2. User Stories & Acceptance Criteria (Gherkin format)
- **Scenario 1**: Successful path
  - **Given** ...
  - **When** ...
  - **Then** ...
- **Scenario 2**: Error handling / validation failure

## 3. Boundary Conditions & Non-Functional Requirements
- Input limits, payload bounds, concurrent load.
- Security constraints (authentication, authorization, data privacy).

## 4. Upstream / Downstream Impact
- Target modules to be created or modified.
- Breaking change assessment.
```

> **Handoff**: The output path `docs/specs/{feature_id}.spec.md` is passed as the direct pointer input to **Stage 2 (`workflow-plan`)**.
