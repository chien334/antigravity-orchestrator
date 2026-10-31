---
name: workflow-review
description: Stage 5 Code Review Workflow - Conduct multi-axis review of git diff against plan and test report, producing docs/reviews/review_signoff.md
---

# Stage 5: Multi-Axis Code Review Workflow

## 1. Objective & Persona
- **Persona**: `code-reviewer`
- **Model Engine**: ✦ **Gemini 4 Argon** (`model: gemini-4-argon`, `reasoning_effort: high`)
- **Primary Skill**: `code-review-and-quality`

---

## 2. Input Contract
- **Prerequisite**: Stage 4 Automated Tests must be completed and passing.
- **Inputs Required**:
  1. Git Diff of changed files (`git diff origin/main...HEAD` or working tree diff).
  2. Architecture & Task Plan: `docs/plans/{feature_id}.plan.md`.
  3. Test verification report: `docs/reports/test_report.json`.

---

## 3. Execution Steps
1. **Emit Start Telemetry**:
   ```bash
   python3 tools/orchestrator/client.py update \
     --task "REVIEW-{FEATURE}" \
     --agent "code-reviewer" \
     --model "gemini-4-argon" \
     --complexity "high" \
     --status "running" \
     --progress 20 \
     --scope "Git Diff & Quality Inspection" \
     --notes "Analyzing diff against 5 review axes"
   ```
2. **5-Axis Review Inspection**:
   - **Correctness**: Does the code implement all requirements without regressions?
   - **Architecture**: Does it adhere to boundary contracts and avoid leaking abstractions?
   - **Maintainability & Simplicity**: Is code clean, minimal, and devoid of dead code or overly clever hacks?
   - **Performance**: Are there N+1 query leaks, blocking calls, or unindexed lookups?
   - **Error Handling**: Are edge cases gracefully captured and logged?
3. **Verdict Determination**:
   - If issues found: issue actionable change requests (`status: REQUEST_CHANGES`).
   - If clean: issue formal approval (`status: APPROVED`).
4. **Artifact Generation**: Produce `docs/reviews/review_signoff.md`.
5. **Emit Completion Telemetry**:
   ```bash
   python3 tools/orchestrator/client.py update \
     --task "REVIEW-{FEATURE}" \
     --agent "code-reviewer" \
     --model "gemini-4-argon" \
     --status "completed" \
     --progress 100 \
     --scope "docs/reviews/review_signoff.md" \
     --notes "Review completed with sign-off status: APPROVED"
   ```

---

## 4. Output Contract (Artifact Schema)
Save to: `docs/reviews/review_signoff.md`

```markdown
# Code Review Sign-off: {Feature Name}

- **Feature ID**: {feature_id}
- **Reviewer**: code-reviewer (Gemini 4 Argon)
- **Status**: APPROVED | REQUEST_CHANGES
- **Date**: {YYYY-MM-DD}

## 1. Summary of Changes
- Total files reviewed: {count}
- Additions / Deletions: +{added} / -{deleted}

## 2. Review Axes Scorecard

| Axis | Status | Notes |
| :--- | :---: | :--- |
| **1. Correctness & Logic** | ✅ PASS | Matches acceptance criteria from spec |
| **2. Architecture & Contracts** | ✅ PASS | Adheres to plan data interfaces |
| **3. Maintainability** | ✅ PASS | Readable, modular, no dead code |
| **4. Performance** | ✅ PASS | No quadratic loops or unbounded buffers |
| **5. Error Handling** | ✅ PASS | Exceptions typed and handled |

## 3. Findings & Required Modifications
- None (or itemized list if REQUEST_CHANGES)

## 4. Final Verdict
- **Sign-off**: `APPROVED`
```

> **Handoff**: On `APPROVED`, the Orchestrator routes the changes to **Stage 6 (`workflow-security`)**.
