---
name: workflow-spec
description: Stage 1 Spec Workflow - Analyze requirements, user stories, boundary conditions, and produce docs/specs/{feature_id}.spec.md using Gemini 4 Neon (non-security, ~32% cheaper) or Gemini 4 Carbon (security/critical) with Scout-Then-Architect integration
---

# Stage 1: Specification Engineering Workflow

## 1. Objective & Persona
- **Persona**: `spec-engineer`
- **Model Engine**:
  - **Non-Security / Standard Specs (Default)**: ⚡✦ **Gemini 4 Neon** (`model: gemini-4-neon`, `reasoning_effort: high`)  
    *SWE Frontier & Mid-Frontier Brain (Intelligence `61`, Coding Agent Index #1 `58.64`, `~105 tok/s`, `$3.00 / $15.00 / $0.15` with 95% cache savings) delivering ~32% lower cost/task and ~2x throughput vs Carbon.*
  - **Security / Critical Specs (`has_security_impact=True` or `complexity == "critical"` or `quality_first`)**: ✦ **Gemini 4 Carbon** (`model: gemini-4-carbon`, `reasoning_effort: high`)  
    *Frontier reasoning engine strictly reserved for security-impacting specifications, auth/crypto/OWASP/migration invariants, and `critical` complexity.*
  *(Optional `hybrid_desktop` Offload: For large non-security-sensitive briefs or second-opinion edge-case synthesis, run `client.py desktop-doctor` and dispatch via `client.py desktop-ask --prompt-file ...` using the `gemini-desktop-worker` skill at `$0.00` AGY API spend. `SecretRedactor` scrubs credentials pre-flight and writes a compact pointer artifact to `docs/reports/desktop_worker/{job_id}.md`. Security-impacting specs (`has_security_impact=True`) MUST stay exclusively on `gemini-4-carbon`).*
- **Primary Skill**: `spec-driven-development` *(+ `gemini-desktop-worker` when `hybrid_desktop` offload is active)*

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
   # Use --model gemini-4-neon for standard specs, or --model gemini-4-carbon for security/critical specs
   python3 packages/orchestrator/client.py update \
     --task "SPEC-{FEATURE}" \
     --agent "spec-engineer" \
     --model "gemini-4-neon" \
     --effort "high" \
     --complexity "high" \
     --status "running" \
     --progress 20 \
     --scope "Requirements & Edge-Case Discovery" \
     --notes "Analyzing user stories and boundary conditions with Gemini 4 Neon"
   ```
2. **Ambiguity Resolution & Deep Reasoning**:
   - Activate deep reasoning to identify implicit assumptions, non-functional requirements (latency, security, concurrency), and edge cases.
   - Formulate formal verification invariants and acceptance scenarios.
3. **Artifact Generation**: Produce `docs/specs/{feature_id}.spec.md` following the standard schema below.
4. **Emit Completion Telemetry**:
   ```bash
   python3 packages/orchestrator/client.py update \
     --task "SPEC-{FEATURE}" \
     --agent "spec-engineer" \
     --model "gemini-4-neon" \
     --effort "high" \
     --status "completed" \
     --progress 100 \
     --input-tokens {IN_TOK} \
     --output-tokens {OUT_TOK} \
     --cache-tokens {CACHE_TOK} \
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
