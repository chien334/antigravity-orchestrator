---
name: workflow-security
description: Stage 6 Security Audit Workflow - Deep OWASP, authentication, data privacy, and secret scanning using Gemini 4 Carbon producing docs/security/security_audit.md
---

# Stage 6: Security & Hardening Audit Workflow

## 1. Objective & Persona
- **Persona**: `security-auditor`
- **Model Engine**: ✦ **Gemini 4 Carbon** (`model: gemini-4-carbon`, `reasoning_effort: high`)  
  *Google Frontier Reasoning model dedicated to deep vulnerability fuzzing, formal invariants, and cryptographic validation.*  
  *(**Strict Security Guardrail Invariant**: Security audits, OWASP vulnerability scans, and auth/crypto logic NEVER downgrade to lower tiers under any budget mode, including `speed_first` and `cost_saving`).*
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
     --input-tokens {IN_TOK} \
     --output-tokens {OUT_TOK} \
     --cache-tokens {CACHE_TOK} \
     --scope "docs/security/security_audit.md" \
     --notes "Security audit passed: Zero high/critical vulnerabilities"
   ```

---

## 4. Output Contract (Artifact Schema)
Save to: `docs/security/security_audit.md`

```markdown
# Security & Hardening Audit Report: {Feature Name}

- **Auditor**: `security-auditor`
- **Model Engine**: `gemini-4-carbon` (effort: high)
- **Verdict**: `PASSED` | `FAILED`

## Threat Model & Findings
| Vulnerability Class | Risk Level | Status | Notes |
|---|---|---|---|
| OWASP Injection | Critical | PASS | Input validation and parameterized calls verified |
| Auth & RBAC Bypass | High | PASS | Role checks strictly enforced |
| Secret Leakage | Critical | PASS | Zero plaintext tokens in source code |

## Sign-Off Signature
- **Security Checksum**: `{SHA256}`
- **Release Approved**: `YES`
```

> **Handoff**: The finalized security audit unlocks the **Mission Audit Exporter (`GET /api/audit/export`)** and production release.
