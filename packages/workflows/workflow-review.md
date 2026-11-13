---
name: workflow-review
description: Stage 5 Code Review Workflow - Conduct multi-axis review of git diff against plan and test report, producing docs/reviews/review_signoff.md
---

# Stage 5: Multi-Axis Code Review Workflow

## 1. Objective & Persona
- **Persona**: `code-reviewer`
- **Model Engine**: ✦ **Gemini 4 Argon** (`model: gemini-4-argon`, `reasoning_effort: high`)  
  *Deep reasoning engine for 5-axis code quality inspection and architectural compliance.*  
  *(Escalate to ✦ **Gemini 4 Carbon** with `reasoning_effort: high` in `quality_first` mode or when reviewing mission-critical core subsystems).*  
  *(In `speed_first` / `latency_sensitive` mode, rapid code reviews of non-critical PRs are dispatched to ✦ **Gemini 4 Hydrogen** with `reasoning_effort: xhigh` thinking depth).*
- **Primary Skill**: `code-review-and-quality`

---

## 2. Input Contract
- **Prerequisite**: Stage 4 Automated Tests must be completed and passing (100% green).
- **Inputs Required**:
  1. Git Diff of changed files (`git diff origin/main...HEAD` or working tree diff).
  2. Architecture & Task Plan: `docs/plans/{feature_id}.plan.md`.
  3. Test verification report: `docs/reports/test_report.json`.

---

## 3. Execution Steps
1. **Emit Start Telemetry**:
   ```bash
   python3 packages/orchestrator/client.py update \
     --task "REVIEW-{FEATURE}" \
     --agent "code-reviewer" \
     --model "gemini-4-argon" \
     --effort "high" \
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
   python3 packages/orchestrator/client.py update \
     --task "REVIEW-{FEATURE}" \
     --agent "code-reviewer" \
     --model "gemini-4-argon" \
     --effort "high" \
     --status "completed" \
     --progress 100 \
     --input-tokens {IN_TOK} \
     --output-tokens {OUT_TOK} \
     --cache-tokens {CACHE_TOK} \
     --scope "docs/reviews/review_signoff.md" \
     --notes "Review completed with sign-off status: APPROVED"
   ```

---

## 4. Output Contract (Artifact Schema)
Save to: `docs/reviews/review_signoff.md`

```markdown
# Code Review Sign-Off: {Feature Name}

- **Reviewer**: `code-reviewer`
- **Model Engine**: `gemini-4-argon` (effort: high)
- **Verdict**: `APPROVED` | `REQUEST_CHANGES`

## 5-Axis Assessment
1. **Correctness**: ...
2. **Architecture**: ...
3. **Maintainability**: ...
4. **Performance**: ...
5. **Error Handling**: ...

## Sign-Off Signature
- **Sign-Off Hash**: `{GIT_HEAD_SHA}`
- **Ready for Security Audit**: `YES`
```

> **Handoff**: The approved sign-off `docs/reviews/review_signoff.md` is passed as input to **Stage 6 (`workflow-security`)**.
