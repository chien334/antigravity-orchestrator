---
name: workflow-spec
description: Stage 1 Spec Workflow - Analyze requirements, user stories, boundary conditions, and produce docs/specs/{feature_id}.spec.md using Gemini 4 Carbon with Scout-Then-Architect integration
---

# Stage 1: Specification Engineering Workflow

## 1. Objective & Persona
- **Persona**: `spec-engineer`
- **Model Engine**: ✦ **Gemini 4 Carbon** (`model: gemini-4-carbon`, `reasoning_effort: high`)  
  *Frontier reasoning engine for formal specification proofs, boundary invariants, and edge-case discovery.*
- **Primary Skill**: `spec-driven-development`

---

## 2. Input Contract
- **Source**: User request, bug description, or feature brief.
- **Context Provided**:
  * Functional goals and business constraints.
  * Codebase pointers gathered via fast `gemini-4-hydrogen` scouts under the **Scout-Then-Architect** pattern (reducing prompt tokens by 80%).

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
     --input-tokens {IN_TOK} \
     --output-tokens {OUT_TOK} \
     --cache-tokens {CACHE_TOK} \
     --scope "docs/specs/{feature_id}.spec.md" \
     --notes "Spec complete with acceptance criteria, edge cases, and frontier reasoning invariants"
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
