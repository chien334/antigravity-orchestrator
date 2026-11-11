---
name: workflow-security
description: Stage 6 Security Audit Workflow - Deep OWASP, authentication, data privacy, and secret scanning using Gemini 4 Carbon producing docs/security/security_audit.md
---

# Stage 6: Security & Hardening Audit Workflow

## 1. Objective & Persona
- **Persona**: `security-auditor`
- **Model Engine**: ✦ **Gemini 4 Carbon** (`model: gemini-4-carbon`, `reasoning_effort: high`)
- **Primary Skill**: `security-and-hardening`

---

## 2. Input Contract
- **Prerequisite**: Stage 5 Code Review must be in `APPROVED` status.
- **Inputs Required**:
  1. Complete codebase diff and modified source files.
  2. Code review sign-off: `docs/reviews/review_signoff.md`.
  3. Sensitive configuration/environment variable usages.

---

## 3. Execution Steps
1. **Emit Start Telemetry**:
   ```bash
   python3 packages/orchestrator/client.py update \
     --task "SEC-{FEATURE}" \
     --agent "security-auditor" \
     --model "gemini-4-carbon" \
     --effort "high" \
     --complexity "critical" \
     --status "running" \
     --progress 20 \
     --scope "Threat Modeling & Vulnerability Scan" \
     --notes "Deep frontier reasoning: OWASP Top 10, Auth/Authz, and Secret Leaks"
   ```
2. **Deep Security Inspection with Gemini 4 Carbon**:
   - **Injection Defense**: SQL injection, command execution, path traversal, XSS, SSRF.
   - **Authentication & Authorization**: Session token integrity, RBAC checks, privilege escalation boundaries.
   - **Data Privacy & Compliance**: Sanitization of PII / medical data in logs, queries, and errors.
   - **Secret & Credential Leakage**: Hardcoded passwords, API tokens, private keys.
   - **Denial of Service**: Unbounded loops, memory allocation limits, payload size limits.
   - **Autonomous Verification Loops**: Fuzz edge-case payloads against security boundary contracts.
3. **Artifact Generation**: Produce `docs/security/security_audit.md`.
4. **Emit Completion Telemetry**:
   ```bash
   python3 packages/orchestrator/client.py update \
     --task "SEC-{FEATURE}" \
     --agent "security-auditor" \
     --model "gemini-4-carbon" \
     --effort "high" \
     --complexity "critical" \
     --status "completed" \
     --progress 100 \
     --scope "docs/security/security_audit.md" \
     --notes "Security audit passed: Zero high/critical vulnerabilities"
   ```

---

## 4. Output Contract (Artifact Schema)
Save to: `docs/security/security_audit.md`

```markdown
# Security & Hardening Audit: {Feature Name}

- **Feature ID**: {feature_id}
- **Auditor**: security-auditor (Gemini 4 Carbon, reasoning_effort: high)
- **Status**: PASSED | BLOCKED
- **Date**: {YYYY-MM-DD}

## 1. Executive Summary
- Scope of audit: {target_modules}
- Overall Risk Rating: `LOW` / `NEGLIGIBLE`

## 2. Threat Vector Scorecard

| Threat Vector | Status | Finding & Mitigation |
| :--- | :---: | :--- |
| **SQL / Command Injection** | ✅ SECURE | Parameterized queries & ORM bounds |
| **Authentication & RBAC** | ✅ SECURE | Context-level permission verification |
| **PII & Data Sanitization** | ✅ SECURE | Zero sensitive data logged |
| **Secret Scanning** | ✅ SECURE | No hardcoded tokens detected |
| **Rate Limiting & DoS** | ✅ SECURE | Payload bounds & timeouts enforced |

## 3. Vulnerability Findings (CVSS v3)
- No critical, high, or medium severity vulnerabilities found.

## 4. Final Security Sign-off
- **Verdict**: `PASSED FOR PRODUCTION DEPLOYMENT`
```

> **Handoff**: On `PASSED`, the Orchestrator marks the entire feature pipeline as `READY_FOR_RELEASE` and triggers audit export via `python3 packages/orchestrator/client.py export --format markdown`.
