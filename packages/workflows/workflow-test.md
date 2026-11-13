---
name: workflow-test
description: Stage 4 Testing Workflow - Implement tests matching acceptance criteria from docs/specs/{feature_id}.spec.md using Gemini 4 Hydrogen and produce docs/reports/test_report.json
---

# Stage 4: Automated Verification & Testing Workflow

## 1. Objective & Persona
- **Persona**: `test-engineer`
- **Model Engine**: ✦ **Gemini 4 Hydrogen** (`model: gemini-4-hydrogen`, `reasoning_effort: medium | high`)  
  *High-throughput test authoring and sandbox test execution (198 tok/s, 2.5x speed) with 95% cache savings ($0.075 / 1M cache tokens).*  
  *(Fallback to ⚡ **Gemini 3.8 Flash** in `cost_saving` mode).*  
  *(**Fast-Retry Circuit Breaker**: If unexpected test failures occur, allow 1 fast self-healing turn on Hydrogen with `effort: xhigh`. If regressions persist after 2 attempts (`retry_count >= 2`), trip the circuit breaker and escalate diagnostic responsibility to `debugger` with ✦ **Gemini 4 Carbon** and `reasoning_effort: high`).*
- **Primary Skill**: `test-driven-development`

---

## 2. Input Contract
- **Prerequisite**: Stage 3 Builders must have completed implementation and passed syntax sanity checks.
- **Inputs Required**:
  1. Acceptance Criteria & Gherkin Scenarios from `docs/specs/{feature_id}.spec.md`.
  2. Modified source code files from Stage 3.
  3. Existing project test conventions.

---

## 3. Execution Steps
1. **Emit Start Telemetry**:
   ```bash
   python3 packages/orchestrator/client.py update \
     --task "TEST-{FEATURE}" \
     --agent "test-engineer" \
     --model "gemini-4-hydrogen" \
     --effort "medium" \
     --complexity "medium" \
     --status "running" \
     --progress 20 \
     --scope "tests/test_{feature}.py" \
     --notes "Writing unit and integration assertions at 198 tok/sec"
   ```
2. **Implement Test Scenarios**:
   - Write comprehensive unit tests for every branch, boundary condition, and edge case defined in the spec.
   - Use standard frameworks (e.g. `unittest`, `pytest`, `jest`, `vitest`).
3. **Execute Test Suite & Fast-Retry Circuit Breaker**:
   - Run tests and capture machine-readable output.
   - If tests fail:
     * **Attempt 1 (`retry_count: 1`)**: Fast self-healing retry turn on `gemini-4-hydrogen` with elevated reasoning (`--effort xhigh`).
     * **Attempt 2+ (`retry_count >= 2`)**: Trip circuit breaker! Escalate to `debugger` with **Gemini 4 Carbon** (`--effort high`) for deep failure isolation.
   - All tests must achieve 100% pass rate before advancing.
4. **Artifact Generation**: Produce `docs/reports/test_report.json`.
5. **Emit Completion Telemetry**:
   ```bash
   python3 packages/orchestrator/client.py update \
     --task "TEST-{FEATURE}" \
     --agent "test-engineer" \
     --model "gemini-4-hydrogen" \
     --effort "medium" \
     --status "completed" \
     --progress 100 \
     --input-tokens {IN_TOK} \
     --output-tokens {OUT_TOK} \
     --cache-tokens {CACHE_TOK} \
     --scope "docs/reports/test_report.json" \
     --notes "All tests passed with 100% success rate on Gemini 4 Hydrogen"
   ```

---

## 4. Output Contract (Artifact Schema)
Save to: `docs/reports/test_report.json`

```json
{
  "feature_id": "{feature_id}",
  "timestamp": "{ISO_8601_TIMESTAMP}",
  "tester": "test-engineer",
  "engine": "gemini-4-hydrogen",
  "summary": {
    "total_tests": 12,
    "passed": 12,
    "failed": 0,
    "skipped": 0,
    "duration_seconds": 1.15
  },
  "test_suites": [
    {
      "name": "tests/test_{feature}.py",
      "status": "PASSED",
      "assertions": 28
    }
  ],
  "acceptance_criteria_verified": [
    "AC-1: Successful payload processing",
    "AC-2: Input boundary validation rejection",
    "AC-3: Error handling on network timeout"
  ],
  "verdict": "PASSED"
}
```

> **Handoff**: The test report `docs/reports/test_report.json` and git diff are passed as input to **Stage 5 (`workflow-review`)**.
