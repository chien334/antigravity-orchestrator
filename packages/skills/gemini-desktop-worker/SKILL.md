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
| **macOS (`darwin`)** | `macos_ax` *(or optional `orca`)* | Discovers `com.google.GeminiMacOS` / `com.google.gemini` (`/Applications/Gemini.app`, `mdfind`, PWA fallback) via `plistlib`. Checks screen lock & `AXIsProcessTrustedWithOptions(null)`. Runs in **Silent Background Mode (`background=True` default)**: opens fresh chat via `googlegemini://newchat?ext_src=app_shortcut`, selects **`Task` mode** (default) or `Chat` mode, mounts `--workspace` via daemon-thread `AXPress` on `Folders` (`ConnectedFolderNSMenu`, zero `CGEvent` cursor movement), injects prompt via direct `AXValue` write + `AXPress` submit (zero keystrokes, zero clipboard touch), passively tails `~/Library/Caches/com.google.GeminiMacOS/Logs/diagnostic*.log` (`0%` focus theft during 15–240s analysis), extracts verbatim `AXStaticText.AXDescription`, and restores `AXFrontmost` if `OmnichatWindow` was hidden (with `pbcopy`+`Cmd+V` / `Cmd+Shift+C` fallback only when needed). |
| **Windows (`win32`)** | `windows_uia` | Discovers `%LOCALAPPDATA%\Programs\Gemini\Gemini.exe`, Start Menu `.lnk` / `Get-StartApps`, or Edge/Chrome PWA. Runs in **Silent Background Mode (`background=True` default)** via `powershell.exe -NoProfile -NonInteractive -Sta -WindowStyle Minimized -ExecutionPolicy Bypass -Command -` using pure `.NET System.Windows.Automation` (`ValuePattern` + `InvokePattern` + `TextPattern`) with **`0` `SetForegroundWindow`, `0` `SendKeys`, and `0` `Clipboard`** via a private `0600` temp file (`AGY_DESKTOP_PROMPT_FILE`). |
| **Linux (`linux`)** | `linux_pwa` | Detects `$DISPLAY` or `$WAYLAND_DISPLAY`, launches Chromium/Chrome/Edge `--app=https://gemini.google.com --new-window`, injects via `wl-copy`/`xclip`/`xsel` + `xdotool`/`wtype`, restores clipboard, and degrades gracefully on headless hosts with `--driver mock` guidance. |
| **CI / Headless** | `mock` | Deterministic zero-GUI simulator (`MockGeminiDriver`) with configurable `MOCK_DELAY_MS` and fault-injection tags (`[MOCK_TIMEOUT]`, `[MOCK_ERROR]`, `[MOCK_PARTIAL]`, `[MOCK_CHROME]`). Never touches OS windows or clipboard. |

---

## 2. Interaction Modes & Direct Workspace Binding (`Task` vs. `Chat`)

`Gemini.app` supports two distinct interaction modes controlled by `--mode` (CLI) or `mode` (REST API `POST /api/desktop/dispatch`):

| Mode | Flag / Value | Default? | Workspace Access | Best Use Case |
|---|---|---|---|---|
| **`Task` Mode** | `--mode task` | **Yes (Default)** | Mounts local `--workspace` via `Folders` (`ConnectedFolderNSMenu`) | Repository-wide architecture reviews, multi-file root-cause synthesis, spec critiques referencing relative project paths. |
| **`Chat` Mode** | `--mode chat` | No | Standalone prompt window (no folder mounted) | Self-contained conceptual prompts, pasted log snippets, or standalone design questions without workspace attachment. |

### 2.1 Direct Workspace Connection (`--workspace <path>`)
- **Auto-Default**: `--workspace` automatically defaults to `os.getcwd()` when omitted (pass `--workspace .` or `--workspace /path/to/project` to bind explicitly).
- **Zero-Copy Prompting via `Folders` (`ConnectedFolderNSMenu`)**: Because Gemini App in **`Task` mode** mounts the local project directory directly through its `Folders` (`ConnectedFolderNSMenu`) menu, AGY orchestrators and subagents do **NOT** need to copy huge source files into prompts or `--context-file` payloads.
- Instead, dispatch a concise prompt referencing **relative file paths** (for example, `packages/orchestrator/router.py` or `docs/specs/my_feature.spec.md`) with `--mode task --workspace /path/to/project` and let `Gemini.app` inspect the workspace directly.

### 2.2 Read-Only Analysis Contract in `Task` Mode
Direct workspace binding gives `Gemini.app` read visibility into project files, while strictly preserving the orchestrator's **read-only offloading boundary**:
1. **Inspect Directly, Edit Zero Files**: `Gemini.app` inspects the mounted workspace directly for analysis, critique, and synthesis, and MUST write **zero edits** to any workspace file.
2. **Avoid Confirmation Blocks**: Prompts in `Task` mode must request pure analysis/reporting (never shell mutations, git writes, or file edits) so `Gemini.app` does not stall on interactive tool-approval/confirmation dialogs.
3. **Structured Sentinel Artifact Output**: Findings are returned inside the Split-Literal Sentinel envelope and persisted solely to `docs/reports/desktop_worker/{job_id}.md` (never mutating source code).

### 2.3 Silent Background Execution (`--background` Default `True` & `--allow-foreground`)
By default (`--background`, `background=True`), the Desktop Worker runs with **zero focus theft** so developers can keep typing in their IDE, browser, or terminal uninterrupted during 15–240s heavy analysis:

- **macOS (`macos_ax`) Zero-Focus-Theft Pipeline (`0` Focus Switches)**:
  1. **Stealth `OmnichatWindow` Hydration**: If `OmnichatWindow` is closed or in `MinichatWindow` (`AXSystemDialog`), opens `OmnichatWindow` via `AXMenuBar -> File -> Open App` (`AXPress`) with `AXHidden=True` — **0 `AXFrontmost` transitions, 0 `open -a` focus theft**.
  2. **Daemon-Thread `Folders` Selection**: Opens `Folders` (`ConnectedFolderNSMenu`) via background daemon-thread `AXPress` with **zero `CGEvent` cursor movement**.
  3. **Direct `AXValue` Write + `AXPress` Submit**: Writes the Sentinel-wrapped prompt directly into the input `AXTextArea` via `AXValue` and triggers submission via `AXPress` (**zero synthetic keystrokes, zero clipboard touch**).
  4. **Passive AX & Diagnostic Log Tailing**: Passively inspects `AXHidden` `OmnichatWindow` via `poll_chat` and tails `~/Library/Caches/com.google.GeminiMacOS/Logs/diagnostic*.log` (`removeStreamingConversation()` / `agentModeTask: ended` + quiet debounce in Task mode so intermediate stream turns never bounce windows).
  5. **Verbatim `AXStaticText.AXDescription` Extraction**: Reads the completed response directly from `AXStaticText.AXDescription` / `AXButton.AXDescription` with `0` focus switches and `0` clipboard mutations.
- **Windows (`windows_uia`) Zero-Focus-Theft Pipeline**:
  - Uses pure `.NET UIAutomation` (**`ValuePattern` + `InvokePattern` + `TextPattern`**) launched with `-WindowStyle Minimized` (`0` `SetForegroundWindow`, `0` `SendKeys`, `0` `Clipboard`).
- **`--allow-foreground` (Opt-in Only)**:
  - Foreground activation is disabled by default (`allow_foreground=False`). Pass `--allow-foreground` **only once** when registering a brand-new unbookmarked folder via the macOS `NSOpenPanel` (`Add new folder…`) dialog; all subsequent runs in that workspace execute silently in the background.

---

## 3. Task Offloading Fit Matrix (When to Offload vs. Keep on API Fleet)

Because the Desktop Worker communicates through a local GUI window (with read-only `Folders` workspace inspection in `Task` mode) without direct AGY file-editing or test-execution gates, strict routing boundaries apply:

| Workload Type | Route to `gemini-desktop-app`? | Recommended Tier / Rule |
|---|---|---|
| **Large Architecture Synthesis & Spec Second-Opinion** | **YES (Recommended)** | Offload in `hybrid_desktop` or `offload_heavy_to_desktop` mode (`read_only=True`). Saves `$0.20–$2.50+` per run at `$0.00` AGY API spend. |
| **Multi-Document / Log Root-Cause Synthesis** | **YES (Recommended)** | Scrub secrets via `SecretRedactor` first, then dispatch bounded logs/context for deep hypothesis generation. |
| **Non-Mutating 5-Axis Design Critique** | **YES (Optional in `hybrid_desktop`)** | Dispatch bounded diff/spec summary and consume `docs/reports/desktop_worker/{job_id}.md` pointer in `code-reviewer`. |
| **Workspace Code Edits, Refactors, Git, or Tests** | **NEVER** | Keep on **`gemini-4-hydrogen`** (`builder`, `test-engineer`, `ui-builder`) for 198 tok/s parallel execution and direct tool access. |
| **Security Audits / Unredacted Auth, Secrets, PII** | **NEVER** | **Rule 1 Guardrail**: `has_security_impact=True` or security keywords (`auth`, `crypto`, `jwt`, `owasp`, `cve`, `rbac`) MUST stay on **`gemini-4-carbon`** (`high`). Use `--strict-secrets` whenever accidental secret presence must abort. |
| **Low-Latency Telemetry / Micro-Linting** | **NEVER** | GUI round-trip (`10s–180s`) is unsuitable for sub-second tasks; keep on **`gemini-3.8-flash-lite`**. |

---

## 4. Pre-Flight Setup & Diagnostics (`desktop-doctor`)

Always verify local desktop readiness before dispatching jobs in `hybrid_desktop` mode.

### 4.1 CLI Pre-Flight Check
```bash
# Via Orchestrator Server (or standalone desktop_worker.py doctor)
python3 packages/orchestrator/client.py desktop-doctor --format text
python3 packages/orchestrator/client.py desktop-doctor --json

# Standalone check without server.py running:
python3 packages/orchestrator/desktop_worker.py doctor --json
```

### 4.2 Platform Permission Checklist
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

## 5. Execution Protocol & Context Minimization

### 5.1 Smart Router Integration
Query the Smart Router with `hybrid_desktop` or `offload_heavy_to_desktop` when dispatching non-mutating high-complexity analysis:
```bash
python3 packages/orchestrator/client.py recommend \
  --agent spec-engineer \
  --complexity high \
  --budget-mode hybrid_desktop \
  --desktop-available \
  --read-only
```

### 5.2 Dispatching Jobs (`desktop-ask` / `desktop-dispatch` & REST API)
```bash
# 1. Task mode (default) with Silent Background Execution (background=True default)
#    Mounts --workspace via Folders (ConnectedFolderNSMenu) with zero focus theft & zero clipboard touch!
python3 packages/orchestrator/client.py desktop-ask \
  --task TASK-20 \
  --mode task \
  --workspace . \
  --background \
  --prompt "Read docs/specs/my_feature.spec.md and packages/orchestrator/router.py. Return a read-only architectural critique without editing any files." \
  --driver auto \
  --timeout 180

# 2. First-time registration of a brand-new unbookmarked workspace folder on macOS
#    (--allow-foreground is opt-in only for the one-time NSOpenPanel "Add new folder…" dialog)
python3 packages/orchestrator/client.py desktop-ask \
  --task TASK-21 \
  --mode task \
  --workspace /path/to/new-project \
  --allow-foreground \
  --prompt-file docs/specs/my_feature.spec.md \
  --driver auto \
  --timeout 180

# 3. Chat mode (no workspace folder attached) queued asynchronously in background
python3 packages/orchestrator/client.py desktop-dispatch \
  --task REVIEW-01 \
  --mode chat \
  --prompt "Critique the module boundaries in docs/plans/my_feature.plan.md" \
  --async

# 4. Inspect queue & job results or cancel an active/queued job
python3 packages/orchestrator/client.py desktop-jobs --limit 20 --format text
python3 packages/orchestrator/client.py desktop-cancel --job-id dsk-20261117-a1b2
```

REST API (`POST /api/desktop/dispatch`) supports the same `mode` (default `"task"`), `workspace` (defaults to server `cwd`), `background` (default `true`), and `allow_foreground` (default `false`) parameters:
```json
{
  "task_id": "TASK-20",
  "mode": "task",
  "workspace": ".",
  "background": true,
  "allow_foreground": false,
  "prompt": "Inspect packages/orchestrator/router.py and summarize routing invariants (read-only, zero edits).",
  "driver": "auto",
  "redact_secrets": true,
  "async_mode": true
}
```

### 5.3 Consuming Context-Minimized Outputs
- Full responses are stripped of UI chrome (`"Gemini said"`, `"Show thinking"`, `"Copy"`, `"Export to Docs"`, `"Send feedback"`, `"Stop response"`) and saved to:
  `docs/reports/desktop_worker/{job_id}.md`
- Parent orchestrators and downstream agents should pass **only** the `artifact_path` pointer and the compact `summary_excerpt` (`<= 600` chars), never pasting raw multi-kilobyte transcripts into agent chat history.

---

## 6. Sentinel Protocol & Security Invariants

1. **Split-Literal Sentinel Framing (Prompt-Echo Immunity)**:
   - Prompts are wrapped by `SentinelEnvelope.build_prompt()` with `<<<AGY_DESKTOP_START:{job_id}>>>` and a **split-literal** end instruction (`"<<<AGY_DESKTOP_DONE:"` + `"{job_id}>>>"`) placed before `--- TASK CONTEXT ---`.
   - Because the unbroken end marker never appears in the user prompt bubble, `has_complete_sentinel()` cannot false-trigger on echoed prompt text.
   - Completion requires: busy indicators (`"Stop response"`, `"Generating your response…"`) absent + start/done sentinels present + `>= 500ms` length stability across 2 consecutive reads.
2. **Pre-Flight `SecretRedactor`**:
   - Automatically scrubs 8 credential classes (`google_api_key`, `openai_anthropic_key`, `github_token`, `aws_access_key`, `jwt_token`, `private_key_pem`, `dsn_credentials`, `bearer_or_secret_kv`) before touching the clipboard or SQLite `prompt_preview`.
   - Pass `--strict-secrets` to abort immediately (`status="rejected_secrets"`) whenever any credential pattern is detected.
3. **Zero-Clipboard Silent Mode & Clipboard Save/Restore Invariant**:
   - In default Silent Background Mode (`background=True`), macOS (`AXValue` + `AXPress` + `AXStaticText.AXDescription`) and Windows (`ValuePattern` + `InvokePattern` + `TextPattern`) perform **zero clipboard mutations** and **zero focus theft**.
   - Whenever clipboard-based fallback (`Cmd+V` / `Cmd+Shift+C` / `linux_pwa`) is used, drivers read prior clipboard content before injection and restore it inside `try ... finally` immediately after paste (`<= 300ms` window) and after extraction.
4. **Single-Window Mutex & Sequential Queue**:
   - GUI execution is serialized via an in-process `threading.Lock`, a cross-process advisory file lock (`fcntl.flock` / `msvcrt.locking`), and the server's FIFO `desktop_jobs` queue so parallel `gemini-4-hydrogen` builders can keep coding while desktop jobs drain safely one at a time.
5. **Prompt Size & Path Traversal Guards**:
   - Soft warning at `60,000` chars; hard rejection above `150,000` chars.
   - Custom `--output` paths dispatched via `POST /api/desktop/dispatch` must resolve strictly inside `<workspace_root>/docs/reports`.
