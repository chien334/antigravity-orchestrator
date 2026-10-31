---
name: workflow-test
description: Stage 4 Testing Workflow - Implement tests matching acceptance criteria from docs/specs/{feature_id}.spec.md and produce docs/reports/test_report.json
---

# Stage 4: Automated Verification & Testing Workflow

## 1. Objective & Persona
- **Persona**: `test-engineer`
- **Model Engine**: ⚡ **Gemini 3.8 Flash** (`model: gemini-3.8-flash`, `reasoning_effort: low/medium`)
- **Primary Skill**: `test-driven-development`

---

## 2. Input Contract
- **Prerequisite**: Stage 3 Builders must have completed implementation.
- **Inputs Required**:
  1. Acceptance Criteria & Gherkin Scenarios from `docs/specs/{feature_id}.spec.md`.
  2. Modified source code files from Stage 3.
  3. Existing project test conventions.

---

## 3. Execution Steps
1. **Emit Start Telemetry**:
   ```bash
   python3 tools/orchestrator/client.py update \
     --task "TEST-{FEATURE}" \
     --agent "test-engineer" \
     --model "gemini-3.8-flash" \
     --complexity "low" \
     --status "running" \
     --progress 20 \
     --scope "tests/test_{feature}.py" \
     --notes "Writing unit and integration assertions"
   ```
2. **Implement Test Scenarios**:
   - Write comprehensive unit tests for every branch, boundary condition, and edge case defined in the spec.
   - Use standard frameworks (e.g. `unittest`, `pytest`, `jest`).
3. **Execute Test Suite**:
   - Run tests and capture machine-readable output.
   - All tests must pass 100%. If any test fails, report failure details to the Orchestrator for escalation.
4. **Artifact Generation**: Produce `docs/reports/test_report.json`.
5. **Emit Completion Telemetry**:
   ```bash
   python3 tools/orchestrator/client.py update \
     --task "TEST-{FEATURE}" \
     --agent "test-engineer" \
     --model "gemini-3.8-flash" \
     --status "completed" \
     --progress 100 \
     --scope "docs/reports/test_report.json" \
     --notes "All tests passed with 100% success rate"
   ```

---

## 4. Output Contract (Artifact Schema)
Save to: `docs/reports/test_report.json`

```json
{
  "feature_id": "{feature_id}",
  "timestamp": "{ISO_8601_TIMESTAMP}",
  "tester": "test-engineer",
  "engine": "gemini-3.8-flash",
  "summary": {
    "total_tests": 12,
    "passed": 12,
    "failed": 0,
    "skipped": 0,
    "duration_seconds": 2.45
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
