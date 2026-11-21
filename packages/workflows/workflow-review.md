---
name: workflow-review
description: Stage 5 Code Review Workflow - Conduct 5-axis review of git diff against plan and test report via Channel A Gemini.app Desktop (when HYBRID_60_DESKTOP, $0.00 API spend) or Channel B Gemini 4 Neon fallback, producing docs/reviews/review_signoff.md
---

# Stage 5: Multi-Axis Code Review Workflow

## 1. Objective & Persona
- **Persona**: `code-reviewer`
- **Dual-Channel Model & Dispatch Routing** (governed by Turn-1 `python3 ~/.gemini/tools/orchestrator/client.py preflight --workspace .`):
  - **Non-Security 5-Axis Reviews when `EXECUTION_MODE: HYBRID_60_DESKTOP` (`desktop_ready == true`, Default)**:
    🖥️ **Channel A — `gemini-desktop-app`** (`$0.00` AGY API spend, `0` focus switches, `mode="task"`, `allow_edits=False` — omit `--allow-edits`).
    **HARD INVARIANT**: Do **NOT** dispatch non-security `code-reviewer` to an AGY `pro`/`inherit` `invoke_subagent` when `desktop_ready == true`! Dispatch via `run_command` (`WaitMsBeforeAsync: 500`):
    ```bash
    python3 ~/.gemini/tools/orchestrator/client.py desktop-ask \
      --task "REVIEW-{FEATURE}" \
      --agent code-reviewer \
      --workspace . \
      --output "docs/reports/desktop_worker/REVIEW-{FEATURE}.md" \
      --prompt "Conduct a 5-axis review (Correctness, Architecture, Maintainability, Performance, Error Handling) of changes for {FEATURE} against docs/plans/{feature_id}.plan.md and docs/reports/test_report.json. Return APPROVED or REQUEST_CHANGES with exact file/line findings. Read-only inspection only."
    ```
  - **Non-Security Reviews when `EXECUTION_MODE: API_ONLY_100` (`desktop_ready == false`)**:
    ⚡✦ **Channel B — Gemini 4 Neon** (`invoke_subagent(Model="pro")` or `"inherit"`, `--model gemini-4-neon`, `reasoning_effort: high` or `xhigh` in `quality_first`).  
    *(In `speed_first` mode for medium PRs, dispatch to ⚡ **Gemini 4 Hydrogen** via `invoke_subagent(Model="flash")` with `effort: xhigh`.)*
  - **Security-Sensitive Subsystems**:
    ✦ **Channel B — Gemini 4 Carbon** (`invoke_subagent(Model="pro")`, `--model gemini-4-carbon`, `reasoning_effort: high`). Security-critical diffs NEVER offload to Desktop.
- **Primary Skill**: `code-review-and-quality` *(+ `gemini-desktop-worker` when Channel A Desktop is active)*

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
   # Use --model gemini-desktop-app in HYBRID_60_DESKTOP mode, or --model gemini-4-neon in API_ONLY_100 mode
   python3 ~/.gemini/tools/orchestrator/client.py update \
     --task "REVIEW-{FEATURE}" \
     --agent "code-reviewer" \
     --model "gemini-desktop-app" \
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
   python3 ~/.gemini/tools/orchestrator/client.py update \
     --task "REVIEW-{FEATURE}" \
     --agent "code-reviewer" \
     --model "gemini-desktop-app" \
     --status "completed" \
     --progress 100 \
     --scope "docs/reviews/review_signoff.md" \
     --notes "Review completed with sign-off status: APPROVED"
   ```

---

## 4. Output Contract (Artifact Schema)
Save to: `docs/reviews/review_signoff.md`

```markdown
# Code Review Sign-Off: {Feature Name}

- **Reviewer**: `code-reviewer`
- **Model Engine**: `gemini-desktop-app` (or `gemini-4-neon` in `API_ONLY_100`)
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

> **Handoff**: The approved sign-off `docs/reviews/review_signoff.md` is passed as input to **Stage 6 (`workflow-security`)** on Channel B **Gemini 4 Carbon** (`invoke_subagent(Model="pro")`).
