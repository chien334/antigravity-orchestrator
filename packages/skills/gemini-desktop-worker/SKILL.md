---
name: gemini-desktop-worker
description: Cross-platform Gemini Desktop App Worker Bridge (macOS Gemini.app, Windows Gemini.exe/UIAutomation, Linux PWA, and Mock CI) for offloading heavy, read-only analytical workloads at $0.00 AGY API token spend with pre-flight SecretRedactor, Clipboard Save/Restore, Sentinel anti-truncation framing, and Context-Minimized artifact pointers.
---

# Gemini Desktop Worker Skill

## 1. Overview & Purpose

The **Gemini Desktop Worker** (`gemini-desktop-app` in `EXTERNAL_WORKERS`) enables Antigravity (`agy`) orchestrators and subagents to offload bounded, **read-only**, high-token cognitive workloads to the developer's locally authenticated **Google Gemini Desktop App** (`$0.00` AGY API spend), while tracking equivalent baseline savings (`AGY Quota Saved` vs `gemini-4-carbon`) and preserving strict **Context Minimization** via file pointers (`docs/reports/desktop_worker/{job_id}.md`).

### Supported Platforms & Stdlib-Only Drivers
| Platform | Driver Name | App Discovery & Automation Strategy (Zero External `pip` Packages) |
|---|---|---|
| **macOS (`darwin`)** | `macos_ax` *(or optional `orca`)* | Discovers `com.google.GeminiMacOS` / `com.google.gemini` (`/Applications/Gemini.app`, `mdfind`, PWA fallback) via `plistlib`. Checks screen lock & `AXIsProcessTrustedWithOptions(null)`. Opens fresh chat via `googlegemini://newchat?ext_src=app_shortcut`, injects via `pbcopy` + `Cmd+V`, immediately restores clipboard, and reads AX tree (`AXStaticText`/`AXTextArea`/`AXWebArea`) or `Cmd+Shift+C` fallback. |
| **Windows (`win32`)** | `windows_uia` | Discovers `%LOCALAPPDATA%\Programs\Gemini\Gemini.exe`, Start Menu `.lnk` / `Get-StartApps`, or Edge/Chrome PWA. Invokes `powershell.exe -NoProfile -NonInteractive -Sta -ExecutionPolicy Bypass -Command -` with `.NET System.Windows.Automation` (`UIAutomationClient`), `System.Windows.Forms.Clipboard`, and `SetForegroundWindow` using a private `0600` temp file (`AGY_DESKTOP_PROMPT_FILE`). |
| **Linux (`linux`)** | `linux_pwa` | Detects `$DISPLAY` or `$WAYLAND_DISPLAY`, launches Chromium/Chrome/Edge `--app=https://gemini.google.com --new-window`, injects via `wl-copy`/`xclip`/`xsel` + `xdotool`/`wtype`, restores clipboard, and degrades gracefully on headless hosts with `--driver mock` guidance. |
| **CI / Headless** | `mock` | Deterministic zero-GUI simulator (`MockGeminiDriver`) with configurable `MOCK_DELAY_MS` and fault-injection tags (`[MOCK_TIMEOUT]`, `[MOCK_ERROR]`, `[MOCK_PARTIAL]`, `[MOCK_CHROME]`). Never touches OS windows or clipboard. |

---

## 2. Task Offloading Fit Matrix (When to Offload vs. Keep on API Fleet)

Because the Desktop Worker communicates through a single local GUI chat window without direct workspace file-editing or test-execution tools, strict routing boundaries apply:

| Workload Type | Route to `gemini-desktop-app`? | Recommended Tier / Rule |
|---|---|---|
| **Large Architecture Synthesis & Spec Second-Opinion** | **YES (Recommended)** | Offload in `hybrid_desktop` or `offload_heavy_to_desktop` mode (`read_only=True`). Saves `$0.20–$2.50+` per run at `$0.00` AGY API spend. |
| **Multi-Document / Log Root-Cause Synthesis** | **YES (Recommended)** | Scrub secrets via `SecretRedactor` first, then dispatch bounded logs/context for deep hypothesis generation. |
| **Non-Mutating 5-Axis Design Critique** | **YES (Optional in `hybrid_desktop`)** | Dispatch bounded diff/spec summary and consume `docs/reports/desktop_worker/{job_id}.md` pointer in `code-reviewer`. |
| **Workspace Code Edits, Refactors, Git, or Tests** | **NEVER** | Keep on **`gemini-4-hydrogen`** (`builder`, `test-engineer`, `ui-builder`) for 198 tok/s parallel execution and direct tool access. |
| **Security Audits / Unredacted Auth, Secrets, PII** | **NEVER** | **Rule 1 Guardrail**: `has_security_impact=True` or security keywords (`auth`, `crypto`, `jwt`, `owasp`, `cve`, `rbac`) MUST stay on **`gemini-4-carbon`** (`high`). Use `--strict-secrets` whenever accidental secret presence must abort. |
| **Low-Latency Telemetry / Micro-Linting** | **NEVER** | GUI round-trip (`10s–180s`) is unsuitable for sub-second tasks; keep on **`gemini-3.8-flash-lite`**. |

---

## 3. Pre-Flight Setup & Diagnostics (`desktop-doctor`)

Always verify local desktop readiness before dispatching jobs in `hybrid_desktop` mode.

### 3.1 CLI Pre-Flight Check
```bash
# Via Orchestrator Server (or standalone desktop_worker.py doctor)
python3 packages/orchestrator/client.py desktop-doctor --format text
python3 packages/orchestrator/client.py desktop-doctor --json

# Standalone check without server.py running:
python3 packages/orchestrator/desktop_worker.py doctor --json
```

### 3.2 Platform Permission Checklist
- **macOS (`darwin`)**:
  1. Ensure `/Applications/Gemini.app` (or `~/Applications/Gemini.app`) is installed and signed in.
  2. Grant Accessibility access to your terminal / Antigravity host in **System Settings -> Privacy & Security -> Accessibility**.
  3. Keep the screen unlocked during execution (`CGSSessionScreenIsLocked` fails fast to avoid blind timeouts).
  4. Optional: set `GEMINI_PREFER_ORCA=1` if you want `orca computer` prioritized over `macos_ax` when `orca` is on `PATH`.
- **Windows (`win32`)**:
  1. Ensure `Gemini.exe` is installed (`%LOCALAPPDATA%\Programs\Gemini\Gemini.exe`) or Gemini is installed as an Edge/Chrome PWA and signed in.
  2. Ensure `powershell.exe` is available (requires `-Sta` mode for `.NET` Clipboard access, handled automatically by `WindowsGeminiDriver`).
- **Linux (`linux`)**:
  1. Run inside an active X11 (`$DISPLAY`) or Wayland (`$WAYLAND_DISPLAY`) session with Chromium/Chrome/Edge and `wl-copy`/`xclip` + `xdotool`/`wtype`.
  2. On headless CI runners, pass `--driver mock` (or `GEMINI_DESKTOP_DRIVER=mock`).

---

## 4. Execution Protocol & Context Minimization

### 4.1 Smart Router Integration
Query the Smart Router with `hybrid_desktop` or `offload_heavy_to_desktop` when dispatching non-mutating high-complexity analysis:
```bash
python3 packages/orchestrator/client.py recommend \
  --agent spec-engineer \
  --complexity high \
  --budget-mode hybrid_desktop \
  --desktop-available \
  --read-only
```

### 4.2 Dispatching Jobs (`desktop-ask` / `desktop-dispatch`)
```bash
# 1. Dispatch a bounded prompt file (blocking until artifact is written)
python3 packages/orchestrator/client.py desktop-ask \
  --task TASK-20 \
  --prompt-file docs/specs/my_feature.spec.md \
  --driver auto \
  --timeout 180

# 2. Enqueue asynchronously and monitor via SSE / desktop-jobs
python3 packages/orchestrator/client.py desktop-dispatch \
  --task REVIEW-01 \
  --prompt "Critique the module boundaries in docs/plans/my_feature.plan.md" \
  --async

# 3. Inspect queue & job results or cancel an active/queued job
python3 packages/orchestrator/client.py desktop-jobs --limit 20 --format text
python3 packages/orchestrator/client.py desktop-cancel --job-id dsk-20261117-a1b2
```

### 4.3 Consuming Context-Minimized Outputs
- Full responses are stripped of UI chrome (`"Gemini said"`, `"Show thinking"`, `"Copy"`, `"Export to Docs"`, `"Send feedback"`, `"Stop response"`) and saved to:
  `docs/reports/desktop_worker/{job_id}.md`
- Parent orchestrators and downstream agents should pass **only** the `artifact_path` pointer and the compact `summary_excerpt` (`<= 600` chars), never pasting raw multi-kilobyte transcripts into agent chat history.

---

## 5. Sentinel Protocol & Security Invariants

1. **Split-Literal Sentinel Framing (Prompt-Echo Immunity)**:
   - Prompts are wrapped by `SentinelEnvelope.build_prompt()` with `<<<AGY_DESKTOP_START:{job_id}>>>` and a **split-literal** end instruction (`"<<<AGY_DESKTOP_DONE:"` + `"{job_id}>>>"`) placed before `--- TASK CONTEXT ---`.
   - Because the unbroken end marker never appears in the user prompt bubble, `has_complete_sentinel()` cannot false-trigger on echoed prompt text.
   - Completion requires: busy indicators (`"Stop response"`, `"Generating your response…"`) absent + start/done sentinels present + `>= 500ms` length stability across 2 consecutive reads.
2. **Pre-Flight `SecretRedactor`**:
   - Automatically scrubs 8 credential classes (`google_api_key`, `openai_anthropic_key`, `github_token`, `aws_access_key`, `jwt_token`, `private_key_pem`, `dsn_credentials`, `bearer_or_secret_kv`) before touching the clipboard or SQLite `prompt_preview`.
   - Pass `--strict-secrets` to abort immediately (`status="rejected_secrets"`) whenever any credential pattern is detected.
3. **Clipboard Save/Restore Invariant**:
   - All real OS drivers read prior clipboard content before injection and restore it inside `try ... finally` immediately after paste (`<= 300ms` window) and after any fallback copy extraction (`Cmd+Shift+C` / `Ctrl+Shift+C`).
4. **Single-Window Mutex & Sequential Queue**:
   - GUI execution is serialized via an in-process `threading.Lock`, a cross-process advisory file lock (`fcntl.flock` / `msvcrt.locking`), and the server's FIFO `desktop_jobs` queue so parallel `gemini-4-hydrogen` builders can keep coding while desktop jobs drain safely one at a time.
5. **Prompt Size & Path Traversal Guards**:
   - Soft warning at `60,000` chars; hard rejection above `150,000` chars.
   - Custom `--output` paths dispatched via `POST /api/desktop/dispatch` must resolve strictly inside `<workspace_root>/docs/reports`.
