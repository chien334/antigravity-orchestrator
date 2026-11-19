#!/usr/bin/env python3
"""
Real-time Orchestrator Dashboard Server
Zero-dependency HTTP server with SSE (Server-Sent Events), REST API,
financial token cost computation, historical audit reporting, and agent kill controls.
"""

import argparse
import datetime
import hmac
import inspect
import json
import os
import queue
import re
import sqlite3
import sys
import tempfile
import threading
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

DEFAULT_PORT = int(os.environ.get("ORCHESTRATOR_PORT", "8484"))
DEFAULT_HOST = os.environ.get("ORCHESTRATOR_HOST", "127.0.0.1")
MAX_JSON_BODY_BYTES = 2 * 1024 * 1024  # 2 MB cap
LOOPBACK_IPS = frozenset({"127.0.0.1", "::1", "::ffff:127.0.0.1"})
_LOOPBACK_ORIGIN_RE = re.compile(
    r"^https?://(?:localhost|127\.0\.0\.1|\[::1\])(?::\d{1,5})?$",
    re.IGNORECASE,
)
_ALLOWED_ARTIFACT_EXTENSIONS = frozenset({".md", ".json", ".txt"})
DEFAULT_DB_PATH = os.environ.get(
    "ORCHESTRATOR_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "orchestrator.db")
)

# ---------------------------------------------------------------------------
# Pricing Constants, Models & Router Imports (Backward Compatible Exports)
# ---------------------------------------------------------------------------
try:
    from models import (
        DEFAULT_DESKTOP_TARGET_SHARE,
        EXTERNAL_WORKERS,
        MODEL_REGISTRY,
        PRICING_TABLE,
        USD_TO_VND_RATE,
        VALID_REASONING_EFFORTS,
        clamp_desktop_share,
        compute_cost,
        compute_desktop_quota_saved,
        extract_model_and_effort,
        get_all_models_catalog,
        get_model_metadata,
        is_external_worker,
        normalize_model_name,
        resolve_model_id,
        validate_reasoning_effort,
    )
    from router import (
        allocate_dag_models,
        recommend_model,
        evaluate_dag_ready,
        evaluate_ready_tasks,
        compute_model_analytics,
        generate_audit_report,
        is_task_desktop_eligible,
    )
except ImportError:
    try:
        from packages.orchestrator.models import (
            DEFAULT_DESKTOP_TARGET_SHARE,
            EXTERNAL_WORKERS,
            MODEL_REGISTRY,
            PRICING_TABLE,
            USD_TO_VND_RATE,
            VALID_REASONING_EFFORTS,
            clamp_desktop_share,
            compute_cost,
            compute_desktop_quota_saved,
            extract_model_and_effort,
            get_all_models_catalog,
            get_model_metadata,
            is_external_worker,
            normalize_model_name,
            resolve_model_id,
            validate_reasoning_effort,
        )
        from packages.orchestrator.router import (
            allocate_dag_models,
            recommend_model,
            evaluate_dag_ready,
            evaluate_ready_tasks,
            compute_model_analytics,
            generate_audit_report,
            is_task_desktop_eligible,
        )
    except ImportError:
        from .models import (
            DEFAULT_DESKTOP_TARGET_SHARE,
            EXTERNAL_WORKERS,
            MODEL_REGISTRY,
            PRICING_TABLE,
            USD_TO_VND_RATE,
            VALID_REASONING_EFFORTS,
            clamp_desktop_share,
            compute_cost,
            compute_desktop_quota_saved,
            extract_model_and_effort,
            get_all_models_catalog,
            get_model_metadata,
            is_external_worker,
            normalize_model_name,
            resolve_model_id,
            validate_reasoning_effort,
        )
        from .router import (
            allocate_dag_models,
            recommend_model,
            evaluate_dag_ready,
            evaluate_ready_tasks,
            compute_model_analytics,
            generate_audit_report,
            is_task_desktop_eligible,
        )

# ---------------------------------------------------------------------------
# Resilient Desktop Worker Imports (Parallel Builder Decoupling)
# ---------------------------------------------------------------------------
DESKTOP_WORKER_AVAILABLE = False
DEFAULT_MAX_PROMPT_CHARS = 150_000
DEFAULT_TIMEOUT_SEC = 240
SUPPORTED_DRIVERS = ("auto", "macos_ax", "orca", "windows_uia", "linux_pwa", "mock")
VALID_JOB_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,63}$")
DesktopDriverStatus = None
DesktopJobRequest = None
DesktopJobResult = None
DesktopWorkerManager = None
detect_desktop_environment = None
redact_secrets = None
validate_app_path = None


def _load_desktop_worker_symbols() -> bool:
    """Attempt dual-path import of desktop_worker module safely."""
    global DESKTOP_WORKER_AVAILABLE
    global DEFAULT_MAX_PROMPT_CHARS, DEFAULT_TIMEOUT_SEC, SUPPORTED_DRIVERS, VALID_JOB_ID_RE
    global DesktopDriverStatus, DesktopJobRequest, DesktopJobResult, DesktopWorkerManager
    global detect_desktop_environment, redact_secrets, validate_app_path

    for mod_name in ("desktop_worker", "packages.orchestrator.desktop_worker"):
        try:
            mod = __import__(mod_name, fromlist=["*"])
            DEFAULT_MAX_PROMPT_CHARS = getattr(mod, "DEFAULT_MAX_PROMPT_CHARS", 150_000)
            DEFAULT_TIMEOUT_SEC = getattr(mod, "DEFAULT_TIMEOUT_SEC", 240)
            SUPPORTED_DRIVERS = getattr(mod, "SUPPORTED_DRIVERS", SUPPORTED_DRIVERS)
            VALID_JOB_ID_RE = getattr(mod, "VALID_JOB_ID_RE", VALID_JOB_ID_RE)
            DesktopDriverStatus = getattr(mod, "DesktopDriverStatus", None)
            DesktopJobRequest = getattr(mod, "DesktopJobRequest", None)
            DesktopJobResult = getattr(mod, "DesktopJobResult", None)
            DesktopWorkerManager = getattr(mod, "DesktopWorkerManager", None)
            detect_desktop_environment = getattr(mod, "detect_desktop_environment", None)
            redact_secrets = getattr(mod, "redact_secrets", None)
            validate_app_path = getattr(mod, "validate_app_path", None)
            DESKTOP_WORKER_AVAILABLE = DesktopWorkerManager is not None
            if DESKTOP_WORKER_AVAILABLE:
                return True
        except ImportError:
            continue

    if __package__:
        try:
            from . import desktop_worker as mod  # type: ignore
            DEFAULT_MAX_PROMPT_CHARS = getattr(mod, "DEFAULT_MAX_PROMPT_CHARS", 150_000)
            DEFAULT_TIMEOUT_SEC = getattr(mod, "DEFAULT_TIMEOUT_SEC", 240)
            SUPPORTED_DRIVERS = getattr(mod, "SUPPORTED_DRIVERS", SUPPORTED_DRIVERS)
            VALID_JOB_ID_RE = getattr(mod, "VALID_JOB_ID_RE", VALID_JOB_ID_RE)
            DesktopDriverStatus = getattr(mod, "DesktopDriverStatus", None)
            DesktopJobRequest = getattr(mod, "DesktopJobRequest", None)
            DesktopJobResult = getattr(mod, "DesktopJobResult", None)
            DesktopWorkerManager = getattr(mod, "DesktopWorkerManager", None)
            detect_desktop_environment = getattr(mod, "detect_desktop_environment", None)
            redact_secrets = getattr(mod, "redact_secrets", None)
            validate_app_path = getattr(mod, "validate_app_path", None)
            DESKTOP_WORKER_AVAILABLE = DesktopWorkerManager is not None
            if DESKTOP_WORKER_AVAILABLE:
                return True
        except ImportError:
            pass

    return False


_load_desktop_worker_symbols()

_FALLBACK_SECRET_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("google_api_key", re.compile(r"AIza[0-9A-Za-z\-_]{35}"), "[REDACTED:GOOGLE_API_KEY]"),
    ("openai_anthropic_key", re.compile(r"sk-(?:proj-|ant-)?[A-Za-z0-9\-_]{20,}"), "[REDACTED:LLM_API_KEY]"),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"), "[REDACTED:GITHUB_TOKEN]"),
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED:AWS_ACCESS_KEY]"),
    ("jwt_token", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "[REDACTED:JWT]"),
    ("private_key_pem", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----"), "[REDACTED:PRIVATE_KEY]"),
    ("dsn_credentials", re.compile(r"(postgresql|postgres|mysql|mongodb|redis)(?:\+[a-z]+)?://[^:\s/@]+:[^@\s]+@"), r"\1://[REDACTED_USER:PASS]@"),
    ("bearer_or_secret_kv", re.compile(r"(?i)(?:authorization:\s*bearer\s+\S+|bearer\s+[A-Za-z0-9_\-.=+/]{16,}|[\"']?(?:api_key|apiKey|secret|client_secret|password|passwd|access_token|refresh_token|auth_token|token)[\"']?\s*[=:]\s*[\"']?[A-Za-z0-9_.\-+/=]{12,}[\"']?)"), "[REDACTED:CREDENTIAL]"),
]


def _is_desktop_path(path: str) -> bool:
    return path == "/api/desktop" or path.startswith("/api/desktop/")


def _is_desktop_auto_ready(status_dict: dict | None) -> bool:
    """Return True only when Desktop Worker is ready and the host screen is unlocked."""
    if not isinstance(status_dict, dict):
        return False
    perms = status_dict.get("permissions") or {}
    return bool(status_dict.get("ready", False)) and perms.get("screen_lock") != "locked"


def _is_loopback_origin(origin: str) -> bool:
    if not origin or not isinstance(origin, str):
        return False
    cand = origin.strip()
    if not _LOOPBACK_ORIGIN_RE.match(cand):
        return False
    parsed = urlparse(cand)
    try:
        port = parsed.port
    except ValueError:
        return False
    if port is not None and not (1 <= port <= 65535):
        return False
    return parsed.hostname in ("localhost", "127.0.0.1", "::1")


def _validate_desktop_app_path(app_path: str, target_os: str = "auto") -> str:
    if not DESKTOP_WORKER_AVAILABLE:
        _load_desktop_worker_symbols()
    if validate_app_path is None:
        raise ValueError("app_path validation is unavailable; custom app_path rejected")
    return validate_app_path(app_path, target_os)


def _get_workspace_root() -> Path:
    """Resolve workspace/repository root cleanly across package and installed layouts."""
    env_ws = os.environ.get("ORCHESTRATOR_WORKSPACE") or os.environ.get("WORKSPACE_ROOT")
    if env_ws:
        return Path(os.path.realpath(env_ws))
    pkg_parent = Path(__file__).resolve().parent.parent
    if pkg_parent.name in ("packages", "tools"):
        return Path(os.path.realpath(str(pkg_parent.parent)))
    return Path(os.path.realpath(str(Path.cwd())))


def _validate_output_path(output_path: str | None) -> str | None:
    """Validate optional output_path stays strictly within <workspace_root>/docs/reports."""
    if output_path is None or str(output_path).strip() == "":
        return None
    raw_str = str(output_path).strip()
    if "\x00" in raw_str:
        raise ValueError("Invalid output_path: null byte is not allowed")

    ws_root = _get_workspace_root()
    ws_reports_dir = Path(os.path.realpath(str(ws_root / "docs" / "reports")))

    raw_path = Path(raw_str).expanduser()
    if raw_path.is_absolute():
        resolved = Path(os.path.realpath(str(raw_path)))
    else:
        resolved = Path(os.path.realpath(str(ws_root / raw_path)))

    if not resolved.is_relative_to(ws_reports_dir) or resolved == ws_reports_dir:
        raise ValueError("Invalid output_path: path traversal outside docs/reports rejected")
    if resolved.suffix.lower() not in _ALLOWED_ARTIFACT_EXTENSIONS:
        raise ValueError(
            f"Invalid output_path extension {resolved.suffix!r}: must be .md, .json, or .txt"
        )
    if resolved.exists() and resolved.is_dir():
        raise ValueError("Invalid output_path: target cannot be a directory")
    return str(resolved)


def _is_sensitive_workspace_root(resolved_ws: str) -> bool:
    """Return True if resolved_ws points to /, a system root, or a protected OS directory."""
    if not resolved_ws:
        return True
    p = Path(resolved_ws)
    norm = resolved_ws.rstrip("/\\") or "/"
    norm_lower = norm.lower()

    if norm_lower == "/" or (len(p.parts) <= 1 and p.anchor):
        return True

    if os.name == "nt" or sys.platform == "win32":
        win_roots = (
            "windows",
            "program files",
            "program files (x86)",
            "programdata",
            "system volume information",
        )
        parts_lower = [part.lower() for part in p.parts]
        if len(parts_lower) >= 2 and parts_lower[1] in win_roots:
            return True
        return False

    protected_trees = (
        "/etc",
        "/private/etc",
        "/system",
        "/library",
        "/usr",
        "/bin",
        "/sbin",
        "/dev",
        "/proc",
        "/sys",
        "/boot",
        "/cores",
    )
    for tree in protected_trees:
        if norm_lower == tree or norm_lower.startswith(tree + "/"):
            return True

    if norm_lower == "/private":
        return True

    if norm_lower in ("/var", "/private/var") or norm_lower.startswith(("/var/", "/private/var/")):
        allowed_var_temp_prefixes = (
            "/var/folders/",
            "/private/var/folders/",
            "/var/tmp/",
            "/private/var/tmp/",
        )
        if norm_lower.startswith(allowed_var_temp_prefixes):
            return False
        sys_tmp = os.path.realpath(tempfile.gettempdir()).rstrip("/").lower()
        if sys_tmp not in ("/var", "/private/var") and (
            norm_lower == sys_tmp or norm_lower.startswith(sys_tmp + "/")
        ):
            return False
        return True

    return False


def _validate_workspace_path(workspace_path: str) -> str:
    """Validate and resolve a user-supplied workspace directory path safely."""
    if not isinstance(workspace_path, str):
        raise ValueError("workspace_path must be a string")
    if "\x00" in workspace_path:
        raise ValueError("Invalid workspace_path: null byte is not allowed")
    stripped = workspace_path.strip()
    if not stripped:
        raise ValueError("Invalid workspace_path: path must not be empty")
    if workspace_path.startswith("-") or stripped.startswith("-"):
        raise ValueError("Invalid workspace_path: leading '-' is not allowed")

    expanded = os.path.expanduser(stripped)
    resolved = os.path.realpath(expanded)
    if not os.path.isdir(resolved):
        raise ValueError(f"Invalid workspace_path: directory does not exist: {stripped!r}")
    if _is_sensitive_workspace_root(resolved):
        raise ValueError(f"Invalid workspace_path: sensitive system root is not allowed: {resolved!r}")
    return resolved


# ---------------------------------------------------------------------------
# State Store (SQLite-backed)
# ---------------------------------------------------------------------------

class StateStore:
    def __init__(self, db_path=None, workspace_root=None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._explicit_workspace_root = workspace_root
        self._lock = threading.Lock()
        self.subscribers = set()  # set of queue.Queue
        self._processed_steps = {}  # conv_id -> last processed step
        self._desktop_queue = queue.Queue()
        self._desktop_cancel_events = {}  # job_id -> threading.Event
        self._desktop_done_events = {}    # job_id -> threading.Event
        self._desktop_requests = {}       # job_id -> DesktopJobRequest or dict
        self._desktop_redactions = {}     # job_id -> dict[str, int]
        self._desktop_active_job_id = None
        self._desktop_manager = None
        self._desktop_manager_lock_dir = None
        self._desktop_manager_reports_root = None
        self.auto_desktop_routing: bool = (
            os.environ.get("ORCHESTRATOR_AUTO_DESKTOP_ROUTING", "1").strip().lower()
            not in ("0", "false", "no", "off")
        )
        self._desktop_status_cache_lock = threading.Lock()
        self._desktop_status_cache_ts: float = 0.0
        self._desktop_status_cache_val: dict | None = None
        self._desktop_status_cache_ttl: float = 3.0
        self._init_db()
        self._start_token_auditor()
        self._start_desktop_worker()

    @property
    def workspace_root(self) -> Path:
        if self._explicit_workspace_root is not None:
            return Path(os.path.realpath(str(self._explicit_workspace_root)))
        return _get_workspace_root()

    @workspace_root.setter
    def workspace_root(self, value) -> None:
        self._explicit_workspace_root = value

    def _start_token_auditor(self):
        """Background daemon: automatically audits tokens and streams live agent activities from transcripts."""
        def _audit_loop():
            brain_dir = os.path.expanduser("~/.gemini/antigravity/brain")
            while True:
                time.sleep(2.5)
                if not os.path.isdir(brain_dir):
                    continue
                try:
                    updates = []
                    new_logs = []
                    with self._lock:
                        conn = self._get_connection()
                        try:
                            cur = conn.cursor()
                            cur.execute("SELECT task_id, agent_type, status, conv_id, input_tokens, output_tokens, cache_tokens, total_tokens FROM tasks")
                            rows = cur.fetchall()
                            for r in rows:
                                c_id = r["conv_id"]
                                if not c_id:
                                    continue
                                t_path = os.path.join(brain_dir, c_id, ".system_generated", "logs", "transcript.jsonl")
                                if not os.path.isfile(t_path):
                                    continue

                                # Auto-detect if c_id is parent orchestrator dispatching a child subagent
                                target_child = None
                                try:
                                    with open(t_path, "r", encoding="utf-8") as f_check:
                                        for line in f_check:
                                            try:
                                                d_chk = json.loads(line)
                                                for tc in d_chk.get("tool_calls", []):
                                                    if tc.get("name") == "send_message":
                                                        recip = tc.get("args", {}).get("Recipient")
                                                        if recip:
                                                            target_child = recip.strip().strip('"').strip("'")
                                            except Exception:
                                                pass
                                    if target_child and target_child != c_id:
                                        child_t_path = os.path.join(brain_dir, target_child, ".system_generated", "logs", "transcript.jsonl")
                                        if os.path.isfile(child_t_path):
                                            c_id = target_child
                                            t_path = child_t_path
                                            conn.execute("UPDATE tasks SET conv_id = ? WHERE task_id = ?", (target_child, r["task_id"]))
                                except Exception:
                                    pass

                                in_t, out_t, cache_t = 0, 0, 0
                                last_step = self._processed_steps.get(c_id, -1)
                                max_step_in_file = last_step
                                
                                with open(t_path, "r", encoding="utf-8") as f:
                                    for line in f:
                                        try:
                                            d = json.loads(line)
                                            in_t += d.get("input_tokens", 0)
                                            out_t += d.get("output_tokens", 0)
                                            cache_t += d.get("cache_read_tokens", 0)
                                            
                                            s_idx = d.get("step_index", 0)
                                            if s_idx > max_step_in_file:
                                                max_step_in_file = s_idx
                                            
                                            # If this step is new and task is active, generate live activity logs
                                            if s_idx > last_step and r["status"] == "running":
                                                # 1. Tool calls
                                                for tc in d.get("tool_calls", []):
                                                    t_name = tc.get("name", "tool")
                                                    t_args = tc.get("args", {})
                                                    t_summary = ""
                                                    if t_name == "run_command":
                                                        t_summary = t_args.get("toolSummary") or t_args.get("CommandLine", "")[:120]
                                                    elif t_name in ("read_file", "view_file", "edit_file", "write_file"):
                                                        t_summary = t_args.get("Path") or t_args.get("AbsolutePath", "")
                                                    elif t_name == "call_mcp_tool":
                                                        t_summary = f"{t_args.get('ServerName')}.{t_args.get('ToolName')}"
                                                    else:
                                                        t_summary = str(t_args)[:100]
                                                    clean_sum = str(t_summary).replace('"', '')
                                                    new_logs.append((r["task_id"], r["agent_type"], "info", f"[Step {s_idx}] 🔧 {t_name}: {clean_sum}"))
                                                
                                                # 2. Thinking
                                                th = d.get("thinking")
                                                if th:
                                                    th_line = th.strip().splitlines()[0][:140].replace('"', '')
                                                    new_logs.append((r["task_id"], r["agent_type"], "thought", f"[Step {s_idx}] 💭 {th_line}"))
                                                
                                                # 3. Errors
                                                if d.get("status") == "ERROR" and d.get("error"):
                                                    err_snippet = str(d.get("error", ""))[:140].replace('"', '')
                                                    new_logs.append((r["task_id"], r["agent_type"], "error", f"[Step {s_idx}] ❌ {err_snippet}"))
                                        except Exception:
                                            pass
                                
                                self._processed_steps[c_id] = max_step_in_file
                                tot = in_t + out_t + cache_t
                                if tot > r["total_tokens"]:
                                    updates.append((in_t, out_t, cache_t, tot, r["task_id"]))

                            if updates:
                                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                                with conn:
                                    for in_t, out_t, cache_t, tot, t_id in updates:
                                        conn.execute("""
                                            UPDATE tasks SET
                                                input_tokens = ?,
                                                output_tokens = ?,
                                                cache_tokens = ?,
                                                total_tokens = ?,
                                                updated_at = ?
                                            WHERE task_id = ?
                                        """, (in_t, out_t, cache_t, tot, now, t_id))
                                metrics = self._calculate_metrics_conn(conn)
                        finally:
                            conn.close()

                    # Broadcast token metrics update
                    if updates:
                        self.broadcast("state_sync", {"metrics": metrics})
                    
                    # Append and broadcast new live activity logs in batch
                    if new_logs:
                        self.append_logs_batch(new_logs)
                except Exception:
                    pass

        t = threading.Thread(target=_audit_loop, daemon=True)
        t.start()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    @staticmethod
    def _migrate_db(conn):
        """Automatically adds missing columns to existing tables without data loss."""
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(tasks)")
        columns = [row["name"] for row in cur.fetchall()]
        if "reasoning_effort" not in columns:
            conn.execute("ALTER TABLE tasks ADD COLUMN reasoning_effort TEXT DEFAULT NULL")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_model ON tasks(model)")

        cur.execute("PRAGMA table_info(desktop_jobs)")
        dj_cols = [row["name"] for row in cur.fetchall()]
        if dj_cols:
            if "estimated_saved_vnd" not in dj_cols:
                conn.execute("ALTER TABLE desktop_jobs ADD COLUMN estimated_saved_vnd INTEGER NOT NULL DEFAULT 0")
            if "mode" not in dj_cols:
                conn.execute("ALTER TABLE desktop_jobs ADD COLUMN mode TEXT DEFAULT 'task'")
            if "workspace_path" not in dj_cols:
                conn.execute("ALTER TABLE desktop_jobs ADD COLUMN workspace_path TEXT DEFAULT NULL")
            if "workspace_attached" not in dj_cols:
                conn.execute("ALTER TABLE desktop_jobs ADD COLUMN workspace_attached INTEGER DEFAULT 0")
            if "background" not in dj_cols:
                conn.execute("ALTER TABLE desktop_jobs ADD COLUMN background INTEGER DEFAULT 1")
            if "allow_edits" not in dj_cols:
                conn.execute("ALTER TABLE desktop_jobs ADD COLUMN allow_edits INTEGER DEFAULT 0")

    def _init_db(self):
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS tasks (
                            task_id TEXT PRIMARY KEY,
                            agent_type TEXT NOT NULL,
                            model TEXT NOT NULL,
                            complexity TEXT NOT NULL,
                            status TEXT NOT NULL,
                            progress INTEGER NOT NULL,
                            scope TEXT,
                            notes TEXT,
                            conv_id TEXT,
                            depends_on TEXT,
                            parallel_group TEXT,
                            reasoning_effort TEXT DEFAULT NULL,
                            input_tokens INTEGER NOT NULL DEFAULT 0,
                            output_tokens INTEGER NOT NULL DEFAULT 0,
                            cache_tokens INTEGER NOT NULL DEFAULT 0,
                            total_tokens INTEGER NOT NULL DEFAULT 0,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL
                        )
                    """)
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS logs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TEXT NOT NULL,
                            task_id TEXT NOT NULL,
                            agent_type TEXT NOT NULL,
                            level TEXT NOT NULL,
                            message TEXT NOT NULL
                        )
                    """)
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS desktop_jobs (
                            job_id TEXT PRIMARY KEY,
                            task_id TEXT,
                            status TEXT NOT NULL,
                            os_platform TEXT NOT NULL,
                            driver_name TEXT NOT NULL,
                            app_path TEXT,
                            mode TEXT DEFAULT 'task',
                            workspace_path TEXT DEFAULT NULL,
                            workspace_attached INTEGER DEFAULT 0,
                            background INTEGER DEFAULT 1,
                            allow_edits INTEGER DEFAULT 0,
                            prompt_chars INTEGER NOT NULL DEFAULT 0,
                            prompt_preview TEXT,
                            redaction_count INTEGER NOT NULL DEFAULT 0,
                            redactions_json TEXT,
                            artifact_path TEXT,
                            summary_excerpt TEXT,
                            output_chars INTEGER NOT NULL DEFAULT 0,
                            duration_ms INTEGER NOT NULL DEFAULT 0,
                            estimated_saved_usd REAL NOT NULL DEFAULT 0.0,
                            estimated_saved_vnd INTEGER NOT NULL DEFAULT 0,
                            clipboard_restored INTEGER NOT NULL DEFAULT 1,
                            error_message TEXT,
                            created_at TEXT NOT NULL,
                            started_at TEXT,
                            completed_at TEXT
                        )
                    """)
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_group ON tasks(parallel_group)")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_model ON tasks(model)")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_id ON logs(id DESC)")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_desktop_jobs_status ON desktop_jobs(status)")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_desktop_jobs_created ON desktop_jobs(created_at DESC)")
                    self._migrate_db(conn)
            finally:
                conn.close()
        with self._desktop_status_cache_lock:
            self._desktop_status_cache_val = None
            self._desktop_status_cache_ts = 0.0

    def _row_to_task(self, row):
        deps_raw = row["depends_on"]
        deps = []
        if deps_raw:
            try:
                deps = json.loads(deps_raw)
            except Exception:
                deps = [d.strip() for d in deps_raw.split(",") if d.strip()]

        in_tok = int(row["input_tokens"])
        out_tok = int(row["output_tokens"])
        cache_tok = int(row["cache_tokens"])
        total_tok = int(row["total_tokens"])
        cost = compute_cost(row["model"], in_tok, out_tok, cache_tok)
        reasoning_effort = row["reasoning_effort"] if "reasoning_effort" in row.keys() else None

        return {
            "task_id": row["task_id"],
            "agent_type": row["agent_type"],
            "model": row["model"],
            "complexity": row["complexity"],
            "status": row["status"],
            "progress": int(row["progress"]),
            "scope": row["scope"] or "",
            "notes": row["notes"] or "",
            "conv_id": row["conv_id"] or "",
            "depends_on": deps,
            "parallel_group": row["parallel_group"] or "",
            "reasoning_effort": reasoning_effort,
            "tokens": {
                "input": in_tok,
                "output": out_tok,
                "cache": cache_tok,
                "total": total_tok,
            },
            "cost": cost,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _row_to_desktop_job(self, row):
        redactions_raw = row["redactions_json"]
        redactions = {}
        if redactions_raw:
            try:
                redactions = json.loads(redactions_raw)
            except Exception:
                redactions = {}

        est_usd = float(row["estimated_saved_usd"] or 0.0)
        if "estimated_saved_vnd" in row.keys() and row["estimated_saved_vnd"] is not None:
            est_vnd = int(row["estimated_saved_vnd"])
        else:
            est_vnd = round(est_usd * USD_TO_VND_RATE)

        out_chars = int(row["output_chars"] or 0)
        driver_name = row["driver_name"]
        err_msg = row["error_message"]
        row_keys = row.keys()
        mode = row["mode"] if "mode" in row_keys and row["mode"] else "task"
        workspace_path = row["workspace_path"] if "workspace_path" in row_keys else None
        workspace_attached = (
            bool(row["workspace_attached"])
            if "workspace_attached" in row_keys and row["workspace_attached"] is not None
            else False
        )
        background = (
            bool(row["background"])
            if "background" in row_keys and row["background"] is not None
            else True
        )
        allow_edits = (
            bool(row["allow_edits"])
            if "allow_edits" in row_keys and row["allow_edits"] is not None
            else False
        )

        return {
            "job_id": row["job_id"],
            "task_id": row["task_id"],
            "status": row["status"],
            "os_platform": row["os_platform"],
            "driver_name": driver_name,
            "driver_used": driver_name,
            "app_path": row["app_path"],
            "mode": mode,
            "workspace_path": workspace_path,
            "workspace_attached": workspace_attached,
            "background": background,
            "allow_edits": allow_edits,
            "prompt_chars": int(row["prompt_chars"] or 0),
            "prompt_preview": row["prompt_preview"] or "",
            "redaction_count": int(row["redaction_count"] or 0),
            "redactions": redactions,
            "artifact_path": row["artifact_path"],
            "summary_excerpt": row["summary_excerpt"] or "",
            "output_chars": out_chars,
            "raw_char_count": out_chars,
            "duration_ms": int(row["duration_ms"] or 0),
            "estimated_saved_usd": round(est_usd, 4),
            "estimated_saved_vnd": est_vnd,
            "clipboard_restored": bool(row["clipboard_restored"]),
            "error_message": err_msg,
            "error": err_msg,
            "created_at": row["created_at"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
        }

    def _calculate_metrics_conn(self, conn):
        cur = conn.cursor()
        cur.execute("SELECT * FROM tasks")
        task_rows = cur.fetchall()
        tasks = [self._row_to_task(r) for r in task_rows]

        total = len(tasks)
        pending = sum(1 for t in tasks if t["status"] == "pending")
        running = sum(1 for t in tasks if t["status"] == "running")
        completed = sum(1 for t in tasks if t["status"] == "completed")
        blocked = sum(1 for t in tasks if t["status"] in ("blocked", "failed"))
        cancelled = sum(1 for t in tasks if t["status"] == "cancelled")
        active_agents = len(set(t["agent_type"] for t in tasks if t["status"] == "running"))

        # Parallel metrics
        running_tasks = [t for t in tasks if t["status"] == "running"]
        parallel_running = len(running_tasks)
        active_groups = sorted(list(set(t["parallel_group"] for t in running_tasks if t.get("parallel_group"))))

        # Token telemetry aggregates
        total_input_tokens = sum(t.get("tokens", {}).get("input", 0) for t in tasks)
        total_output_tokens = sum(t.get("tokens", {}).get("output", 0) for t in tasks)
        total_cache_tokens = sum(t.get("tokens", {}).get("cache", 0) for t in tasks)
        grand_total_tokens = total_input_tokens + total_output_tokens + total_cache_tokens
        cache_rate = round((total_cache_tokens / (total_input_tokens + total_cache_tokens) * 100), 1) if (total_input_tokens + total_cache_tokens) > 0 else 0.0

        # Cost telemetry aggregates
        total_cost_usd = round(sum(t.get("cost", {}).get("usd", 0.0) for t in tasks), 4)
        total_cost_vnd = sum(t.get("cost", {}).get("vnd", 0) for t in tasks)
        total_saved_usd = round(sum(t.get("cost", {}).get("saved_usd", 0.0) for t in tasks), 4)
        total_saved_vnd = sum(t.get("cost", {}).get("saved_vnd", 0) for t in tasks)

        # Desktop Worker offload telemetry aggregates
        desktop_jobs_total = 0
        desktop_jobs_queued = 0
        desktop_jobs_running = 0
        desktop_jobs_completed = 0
        desktop_quota_saved_usd = 0.0
        desktop_quota_saved_vnd = 0
        try:
            cur.execute("SELECT status, estimated_saved_usd, estimated_saved_vnd FROM desktop_jobs")
            dj_rows = cur.fetchall()
            desktop_jobs_total = len(dj_rows)
            desktop_jobs_queued = sum(1 for r in dj_rows if r["status"] == "queued")
            desktop_jobs_running = sum(1 for r in dj_rows if r["status"] == "running")
            desktop_jobs_completed = sum(1 for r in dj_rows if r["status"] == "completed")
            desktop_quota_saved_usd = round(
                sum(float(r["estimated_saved_usd"] or 0.0) for r in dj_rows if r["status"] == "completed"),
                4,
            )
            desktop_quota_saved_vnd = sum(
                int(
                    r["estimated_saved_vnd"]
                    if "estimated_saved_vnd" in r.keys() and r["estimated_saved_vnd"] is not None
                    else round(float(r["estimated_saved_usd"] or 0.0) * USD_TO_VND_RATE)
                )
                for r in dj_rows
                if r["status"] == "completed"
            )
        except sqlite3.OperationalError:
            pass

        return {
            "total": total,
            "pending": pending,
            "running": running,
            "completed": completed,
            "blocked": blocked,
            "cancelled": cancelled,
            "active_agents": active_agents,
            "parallel_running": parallel_running,
            "active_groups": active_groups,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_cache_tokens": total_cache_tokens,
            "grand_total_tokens": grand_total_tokens,
            "cache_rate": cache_rate,
            "total_cost_usd": total_cost_usd,
            "total_cost_vnd": total_cost_vnd,
            "total_saved_usd": total_saved_usd,
            "total_saved_vnd": total_saved_vnd,
            "desktop_jobs_total": desktop_jobs_total,
            "desktop_jobs_queued": desktop_jobs_queued,
            "desktop_jobs_running": desktop_jobs_running,
            "desktop_jobs_completed": desktop_jobs_completed,
            "desktop_quota_saved_usd": desktop_quota_saved_usd,
            "desktop_quota_saved_vnd": desktop_quota_saved_vnd,
            "agy_quota_saved_usd": desktop_quota_saved_usd,
        }

    def upsert_task(
        self,
        task_id,
        agent_type=None,
        status=None,
        progress=None,
        scope=None,
        notes=None,
        conv_id=None,
        model=None,
        complexity=None,
        depends_on=None,
        parallel_group=None,
        input_tokens=None,
        output_tokens=None,
        cache_tokens=None,
        reasoning_effort=None,
    ):
        with self._lock:
            conn = self._get_connection()
            try:
                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                cur = conn.cursor()
                cur.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
                existing_row = cur.fetchone()
                existing = self._row_to_task(existing_row) if existing_row else {}

                # Normalize depends_on to list of strings
                deps = depends_on if depends_on is not None else existing.get("depends_on", [])
                if isinstance(deps, str):
                    deps = [d.strip() for d in deps.split(",") if d.strip()]
                elif not isinstance(deps, list):
                    deps = []

                group = parallel_group if parallel_group is not None else existing.get("parallel_group", "")

                # Token tracking (input, output, cache read)
                existing_tokens = existing.get("tokens", {"input": 0, "output": 0, "cache": 0, "total": 0})
                in_tok = int(input_tokens) if input_tokens is not None else existing_tokens.get("input", 0)
                out_tok = int(output_tokens) if output_tokens is not None else existing_tokens.get("output", 0)
                cache_tok = int(cache_tokens) if cache_tokens is not None else existing_tokens.get("cache", 0)
                total_tok = in_tok + out_tok + cache_tok

                final_agent = agent_type or existing.get("agent_type", "orchestrator")
                if model is not None:
                    final_model, extracted_effort = extract_model_and_effort(model, reasoning_effort)
                    if reasoning_effort is None:
                        reasoning_effort = extracted_effort
                else:
                    final_model = existing.get("model") or "gemini-4-neon"

                final_complexity = (complexity if complexity is not None else existing.get("complexity", "medium")).lower()
                final_status = status or existing.get("status", "pending")
                final_progress = max(0, min(100, int(progress) if progress is not None else existing.get("progress", 0)))
                final_scope = scope if scope is not None else existing.get("scope", "")
                final_notes = notes if notes is not None else existing.get("notes", "")
                final_conv_id = conv_id if conv_id is not None else existing.get("conv_id", "")
                created_at = existing.get("created_at", now)

                # Reasoning effort validation/normalization
                if reasoning_effort is not None:
                    raw_effort = str(reasoning_effort).strip().lower() if reasoning_effort else ""
                    if raw_effort in VALID_REASONING_EFFORTS:
                        final_reasoning_effort = raw_effort
                    else:
                        final_reasoning_effort = None
                else:
                    final_reasoning_effort = existing.get("reasoning_effort", None)

                with conn:
                    conn.execute("""
                        INSERT INTO tasks (
                            task_id, agent_type, model, complexity, status, progress, scope,
                            notes, conv_id, depends_on, parallel_group, reasoning_effort, input_tokens,
                            output_tokens, cache_tokens, total_tokens, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(task_id) DO UPDATE SET
                            agent_type=excluded.agent_type,
                            model=excluded.model,
                            complexity=excluded.complexity,
                            status=excluded.status,
                            progress=excluded.progress,
                            scope=excluded.scope,
                            notes=excluded.notes,
                            conv_id=excluded.conv_id,
                            depends_on=excluded.depends_on,
                            parallel_group=excluded.parallel_group,
                            reasoning_effort=excluded.reasoning_effort,
                            input_tokens=excluded.input_tokens,
                            output_tokens=excluded.output_tokens,
                            cache_tokens=excluded.cache_tokens,
                            total_tokens=excluded.total_tokens,
                            updated_at=excluded.updated_at
                    """, (
                        task_id, final_agent, final_model, final_complexity, final_status,
                        final_progress, final_scope, final_notes, final_conv_id,
                        json.dumps(deps), group, final_reasoning_effort, in_tok, out_tok, cache_tok, total_tok,
                        created_at, now
                    ))

                cur.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
                task_row = cur.fetchone()
                task = self._row_to_task(task_row)
                metrics = self._calculate_metrics_conn(conn)
            finally:
                conn.close()

        # Notify subscribers
        self.broadcast("task_update", {"task": task, "metrics": metrics})
        return task

    def kill_task(self, task_id, reason=None):
        """Cancel/kill a running task and record an audit log."""
        with self._lock:
            conn = self._get_connection()
            try:
                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                cur = conn.cursor()
                cur.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
                row = cur.fetchone()
                if not row:
                    return None
                existing = self._row_to_task(row)
                prev_status = existing["status"]

                with conn:
                    conn.execute("""
                        UPDATE tasks SET
                            status = 'cancelled',
                            updated_at = ?
                        WHERE task_id = ?
                    """, (now, task_id))

                    reason_msg = f"Task stopped/cancelled via Orchestrator UI (was {prev_status}). {reason or ''}".strip()
                    conn.execute("""
                        INSERT INTO logs (timestamp, task_id, agent_type, level, message)
                        VALUES (?, ?, ?, 'warn', ?)
                    """, (now, task_id, existing["agent_type"], reason_msg))

                cur.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
                updated_row = cur.fetchone()
                task = self._row_to_task(updated_row)
                metrics = self._calculate_metrics_conn(conn)
            finally:
                conn.close()

        # Notify subscribers
        self.broadcast("task_update", {"task": task, "metrics": metrics})
        self.broadcast("log_event", {
            "timestamp": now,
            "task_id": task_id,
            "agent_type": existing["agent_type"],
            "level": "warn",
            "message": f"Task {task_id} stopped/cancelled by user (was {prev_status}).",
        })
        return task

    def append_log(self, task_id, agent_type, level, message):
        with self._lock:
            conn = self._get_connection()
            try:
                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                t_id = task_id or "GENERAL"
                a_type = agent_type or "system"
                lvl = (level or "info").lower()
                msg = str(message)
                with conn:
                    conn.execute("""
                        INSERT INTO logs (timestamp, task_id, agent_type, level, message)
                        VALUES (?, ?, ?, ?, ?)
                    """, (now, t_id, a_type, lvl, msg))
                    conn.execute("""
                        DELETE FROM logs WHERE id NOT IN (
                            SELECT id FROM logs ORDER BY id DESC LIMIT 5000
                        )
                    """)
                log_entry = {
                    "timestamp": now,
                    "task_id": t_id,
                    "agent_type": a_type,
                    "level": lvl,
                    "message": msg,
                }
            finally:
                conn.close()

        # Notify subscribers
        self.broadcast("log_event", log_entry)
        return log_entry

    def append_logs_batch(self, entries):
        """Append multiple log entries in a single transaction with ring-buffer broadcasting."""
        if not entries:
            return []
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        log_entries = []
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    for t_id, a_type, lvl, msg in entries:
                        t_id = t_id or "GENERAL"
                        a_type = a_type or "system"
                        lvl = (lvl or "info").lower()
                        msg = str(msg)
                        conn.execute("""
                            INSERT INTO logs (timestamp, task_id, agent_type, level, message)
                            VALUES (?, ?, ?, ?, ?)
                        """, (now, t_id, a_type, lvl, msg))
                        log_entries.append({
                            "timestamp": now,
                            "task_id": t_id,
                            "agent_type": a_type,
                            "level": lvl,
                            "message": msg,
                        })
                    conn.execute("""
                        DELETE FROM logs WHERE id NOT IN (
                            SELECT id FROM logs ORDER BY id DESC LIMIT 5000
                        )
                    """)
            finally:
                conn.close()

        # Notify subscribers
        for entry in log_entries:
            self.broadcast("log_event", entry)
        return log_entries

    def get_task_transcript(self, task_id):
        """Retrieve and parse the live activity stream from a subagent transcript."""
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
                row = cur.fetchone()
                if not row:
                    return {"status": "error", "error": f"Task {task_id} not found"}
                task = self._row_to_task(row)
            finally:
                conn.close()

        c_id = task.get("conv_id")
        activities = []
        latest_action = "Khởi tạo tác vụ"
        
        brain_dir = os.path.expanduser("~/.gemini/antigravity/brain")
        if c_id and os.path.isdir(brain_dir):
            t_path = os.path.join(brain_dir, c_id, ".system_generated", "logs", "transcript.jsonl")
            if os.path.isfile(t_path):
                # Auto-detect if c_id was parent orchestrator that sent a message to child subagent
                try:
                    target_child = None
                    with open(t_path, "r", encoding="utf-8") as f_check:
                        for line in f_check:
                            try:
                                d_chk = json.loads(line)
                                for tc in d_chk.get("tool_calls", []):
                                    if tc.get("name") == "send_message":
                                        recip = tc.get("args", {}).get("Recipient")
                                        if recip:
                                            target_child = recip.strip().strip('"').strip("'")
                            except Exception:
                                pass
                    if target_child and target_child != c_id:
                        child_t_path = os.path.join(brain_dir, target_child, ".system_generated", "logs", "transcript.jsonl")
                        if os.path.isfile(child_t_path):
                            c_id = target_child
                            t_path = child_t_path
                            with self._lock:
                                conn_up = self._get_connection()
                                try:
                                    with conn_up:
                                        conn_up.execute("UPDATE tasks SET conv_id = ? WHERE task_id = ?", (target_child, task_id))
                                finally:
                                    conn_up.close()
                except Exception:
                    pass

                try:
                    with open(t_path, "r", encoding="utf-8") as f:
                        for line in f:
                            try:
                                d = json.loads(line)
                                step = d.get("step_index", 0)
                                t_time = d.get("created_at", "")
                                
                                # 1. Thinking
                                th = d.get("thinking")
                                if th:
                                    th_line = th.strip().splitlines()[0][:140].replace('"', '')
                                    activities.append({
                                        "step": step,
                                        "time": t_time,
                                        "type": "thought",
                                        "title": "Suy nghĩ & Phân tích",
                                        "detail": th_line
                                    })
                                    latest_action = f"💭 {th_line}"

                                # 2. Tool calls
                                for tc in d.get("tool_calls", []):
                                    t_name = tc.get("name", "tool")
                                    t_args = tc.get("args", {})
                                    t_sum = ""
                                    if t_name == "run_command":
                                        t_sum = t_args.get("toolSummary") or t_args.get("CommandLine", "")[:120]
                                    elif t_name in ("read_file", "view_file", "edit_file", "write_file"):
                                        t_sum = t_args.get("Path") or t_args.get("AbsolutePath", "")
                                    elif t_name == "call_mcp_tool":
                                        t_sum = f"{t_args.get('ServerName')}.{t_args.get('ToolName')}"
                                    else:
                                        t_sum = str(t_args)[:100]
                                    clean_sum = str(t_sum).replace('"', '')
                                    activities.append({
                                        "step": step,
                                        "time": t_time,
                                        "type": "tool",
                                        "title": f"Công cụ ({t_name})",
                                        "detail": clean_sum
                                    })
                                    latest_action = f"🔧 {t_name}: {clean_sum}"

                                # 3. Status errors
                                if d.get("status") == "ERROR" and d.get("error"):
                                    err_msg = str(d.get("error", ""))[:140].replace('"', '')
                                    activities.append({
                                        "step": step,
                                        "time": t_time,
                                        "type": "error",
                                        "title": "Lỗi thực thi",
                                        "detail": err_msg
                                    })
                            except Exception:
                                pass
                except Exception as e:
                    activities.append({
                        "step": 0,
                        "time": "",
                        "type": "error",
                        "title": "Transcript Error",
                        "detail": str(e)
                    })

        return {
            "status": "ok",
            "task_id": task["task_id"],
            "agent_type": task["agent_type"],
            "model": task["model"],
            "task_status": task["status"],
            "progress": task["progress"],
            "scope": task["scope"],
            "notes": task["notes"],
            "conv_id": c_id,
            "tokens": task["tokens"],
            "cost": task["cost"],
            "latest_action": latest_action,
            "activities": activities[-1000:]
        }

    def _get_desktop_manager(self):
        """Lazily initialize or refresh DesktopWorkerManager aligned with current db_path and workspace."""
        if not DESKTOP_WORKER_AVAILABLE:
            _load_desktop_worker_symbols()
        if DesktopWorkerManager is None:
            return None
        ws_root = self.workspace_root
        reports_root = Path(os.path.realpath(str(ws_root / "docs" / "reports")))
        artifacts_dir = Path(os.path.realpath(str(reports_root / "desktop_worker")))
        db_dir = str(Path(self.db_path).resolve().parent)
        lock_path = Path(db_dir) / "agy_desktop_worker.lock"
        if (
            self._desktop_manager is None
            or self._desktop_manager_lock_dir != db_dir
            or getattr(self, "_desktop_manager_reports_root", None) != str(reports_root)
        ):
            self._desktop_manager = DesktopWorkerManager(
                artifacts_dir=artifacts_dir,
                lock_path=lock_path,
                reports_root=reports_root,
                workspace_root=ws_root,
            )
            self._desktop_manager_lock_dir = db_dir
            self._desktop_manager_reports_root = str(reports_root)
        return self._desktop_manager

    @staticmethod
    def _scrub_prompt(prompt: str, strict: bool = False, redact: bool = True) -> tuple[str, dict[str, int], bool]:
        """Run SecretRedactor pre-flight scan using desktop_worker or stdlib fallback."""
        if not DESKTOP_WORKER_AVAILABLE:
            _load_desktop_worker_symbols()
        if redact_secrets is not None:
            return redact_secrets(prompt, strict=strict, redact=redact)

        counts: dict[str, int] = {}
        sanitized = prompt
        total_found = 0
        for name, pattern, repl in _FALLBACK_SECRET_PATTERNS:
            matches = pattern.findall(sanitized)
            if matches:
                cnt = len(matches)
                counts[name] = cnt
                total_found += cnt
                if redact:
                    sanitized = pattern.sub(repl, sanitized)
        blocked = bool(strict and total_found > 0)
        return sanitized, counts, blocked

    def _start_desktop_worker(self):
        """Start single-window FIFO background worker draining desktop_jobs sequentially."""
        t = threading.Thread(target=self._desktop_worker_loop, daemon=True)
        t.start()

    def _desktop_worker_loop(self):
        while True:
            job_id = self._desktop_queue.get()
            try:
                if job_id:
                    self._process_desktop_job(job_id)
            except Exception:
                pass
            finally:
                self._desktop_queue.task_done()

    def _process_desktop_job(self, job_id: str):
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._lock:
            cancel_ev = self._desktop_cancel_events.get(job_id)
            done_ev = self._desktop_done_events.get(job_id)
            req_obj = self._desktop_requests.get(job_id)
            pre_redactions = dict(self._desktop_redactions.get(job_id) or {})

            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM desktop_jobs WHERE job_id = ?", (job_id,))
                row = cur.fetchone()
                if not row:
                    if done_ev:
                        done_ev.set()
                    self._desktop_cancel_events.pop(job_id, None)
                    self._desktop_done_events.pop(job_id, None)
                    self._desktop_requests.pop(job_id, None)
                    self._desktop_redactions.pop(job_id, None)
                    return

                if row["status"] == "cancelled" or (cancel_ev is not None and cancel_ev.is_set()):
                    already_cancelled = row["status"] == "cancelled"
                    if not already_cancelled:
                        with conn:
                            conn.execute(
                                "UPDATE desktop_jobs SET status = 'cancelled', completed_at = ?, error_message = COALESCE(error_message, 'Cancelled before execution') WHERE job_id = ?",
                                (now, job_id),
                            )
                    cur.execute("SELECT * FROM desktop_jobs WHERE job_id = ?", (job_id,))
                    cancelled_row = cur.fetchone()
                    cancelled_job = self._row_to_desktop_job(cancelled_row) if cancelled_row else None
                    metrics = self._calculate_metrics_conn(conn)
                    if done_ev:
                        done_ev.set()
                    self._desktop_cancel_events.pop(job_id, None)
                    self._desktop_done_events.pop(job_id, None)
                    self._desktop_requests.pop(job_id, None)
                    self._desktop_redactions.pop(job_id, None)
                    skip_exec = True
                else:
                    already_cancelled = False
                    skip_exec = False
                    with conn:
                        conn.execute(
                            "UPDATE desktop_jobs SET status = 'running', started_at = ? WHERE job_id = ?",
                            (now, job_id),
                        )
                    self._desktop_active_job_id = job_id
                    cur.execute("SELECT * FROM desktop_jobs WHERE job_id = ?", (job_id,))
                    running_job = self._row_to_desktop_job(cur.fetchone())
                    metrics = self._calculate_metrics_conn(conn)
            finally:
                conn.close()

        if skip_exec:
            if cancelled_job and not already_cancelled:
                self.broadcast("desktop_job_cancelled", {"job": cancelled_job, "metrics": metrics})
            return

        self.broadcast("desktop_job_started", {"job": running_job, "metrics": metrics})

        exec_result = None
        exec_error = None
        try:
            manager = self._get_desktop_manager()
            if manager is None or req_obj is None:
                raise RuntimeError("desktop_worker module is not available")
            exec_result = manager.execute_job(req_obj, cancel_event=cancel_ev)
        except Exception as exc:
            exec_error = str(exc)

        done_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        should_broadcast = False
        sse_event = "desktop_job_failed"
        final_job = None

        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM desktop_jobs WHERE job_id = ?", (job_id,))
                row = cur.fetchone()
                if row:
                    row_already_cancelled = row["status"] == "cancelled"
                    was_cancelled = (
                        row_already_cancelled
                        or (cancel_ev is not None and cancel_ev.is_set())
                        or (exec_result is not None and exec_result.status == "cancelled")
                    )
                    if was_cancelled:
                        final_status = "cancelled"
                        err_msg = row["error_message"] or (exec_result.error if exec_result else None) or "Cancelled by user"
                        sse_event = "desktop_job_cancelled"
                        should_broadcast = not row_already_cancelled
                    elif exec_error is not None:
                        final_status = "failed"
                        err_msg = exec_error
                        sse_event = "desktop_job_failed"
                        should_broadcast = True
                    else:
                        final_status = exec_result.status
                        err_msg = exec_result.error
                        sse_event = "desktop_job_completed" if final_status == "completed" else "desktop_job_failed"
                        should_broadcast = True

                    merged_redactions = dict(pre_redactions)
                    if exec_result is not None and exec_result.redactions:
                        for k, v in exec_result.redactions.items():
                            merged_redactions[k] = max(int(merged_redactions.get(k, 0)), int(v or 0))
                    redaction_count = sum(int(v) for v in merged_redactions.values())

                    os_platform = exec_result.os_platform if exec_result is not None else row["os_platform"]
                    driver_name = exec_result.driver_used if exec_result is not None else row["driver_name"]
                    artifact_path = exec_result.artifact_path if exec_result is not None else row["artifact_path"]
                    summary_excerpt = exec_result.summary_excerpt if exec_result is not None else (row["summary_excerpt"] or "")
                    output_chars = int(exec_result.raw_char_count or 0) if exec_result is not None else 0
                    duration_ms = int(exec_result.duration_ms or 0) if exec_result is not None else 0
                    clipboard_restored = 1 if (exec_result.clipboard_restored if exec_result is not None else True) else 0
                    row_keys = row.keys()
                    workspace_attached = (
                        int(bool(getattr(exec_result, "workspace_attached", False)))
                        if exec_result is not None
                        else (int(bool(row["workspace_attached"])) if "workspace_attached" in row_keys else 0)
                    )

                    if final_status == "completed" and exec_result is not None:
                        saved_usd = float(getattr(exec_result, "estimated_saved_usd", 0.0) or 0.0)
                        saved_vnd = int(getattr(exec_result, "estimated_saved_vnd", 0) or 0)
                        if saved_usd == 0.0 or saved_vnd == 0:
                            quota = compute_desktop_quota_saved(
                                int(row["prompt_chars"] or 0),
                                output_chars or len(summary_excerpt or ""),
                            )
                            if saved_usd == 0.0:
                                saved_usd = quota["saved_usd"]
                            if saved_vnd == 0:
                                saved_vnd = quota["saved_vnd"]
                    else:
                        saved_usd = 0.0
                        saved_vnd = 0

                    completed_ts = row["completed_at"] or done_at
                    with conn:
                        conn.execute(
                            """
                            UPDATE desktop_jobs SET
                                status = ?,
                                os_platform = ?,
                                driver_name = ?,
                                workspace_attached = ?,
                                redaction_count = ?,
                                redactions_json = ?,
                                artifact_path = ?,
                                summary_excerpt = ?,
                                output_chars = ?,
                                duration_ms = ?,
                                estimated_saved_usd = ?,
                                estimated_saved_vnd = ?,
                                clipboard_restored = ?,
                                error_message = ?,
                                completed_at = ?
                            WHERE job_id = ?
                            """,
                            (
                                final_status,
                                os_platform,
                                driver_name,
                                workspace_attached,
                                redaction_count,
                                json.dumps(merged_redactions),
                                artifact_path,
                                summary_excerpt,
                                output_chars,
                                duration_ms,
                                round(saved_usd, 4),
                                int(saved_vnd),
                                clipboard_restored,
                                err_msg,
                                completed_ts,
                                job_id,
                            ),
                        )
                    cur.execute("SELECT * FROM desktop_jobs WHERE job_id = ?", (job_id,))
                    updated_row = cur.fetchone()
                    final_job = self._row_to_desktop_job(updated_row) if updated_row else None
                    metrics = self._calculate_metrics_conn(conn)
            finally:
                conn.close()

            if self._desktop_active_job_id == job_id:
                self._desktop_active_job_id = None
            if done_ev:
                done_ev.set()
            self._desktop_cancel_events.pop(job_id, None)
            self._desktop_done_events.pop(job_id, None)
            self._desktop_requests.pop(job_id, None)
            self._desktop_redactions.pop(job_id, None)

        if should_broadcast and final_job is not None:
            self.broadcast(sse_event, {"job": final_job, "metrics": metrics})

    def get_desktop_status(self, driver: str = "auto", target_os: str = "auto", app_path: str | None = None) -> dict:
        norm_target_os = str(target_os or "auto").strip().lower()
        if norm_target_os not in ("auto", "darwin", "win32", "linux"):
            raise ValueError(f"Invalid target_os '{target_os}'")
        clean_app_path: str | None = None
        if app_path is not None and str(app_path).strip() != "":
            if not isinstance(app_path, str):
                raise ValueError("app_path must be a string")
            clean_app_path = _validate_desktop_app_path(app_path.strip(), norm_target_os)

        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM desktop_jobs WHERE status = 'running' ORDER BY started_at DESC LIMIT 1")
                active_row = cur.fetchone()
                active_job = self._row_to_desktop_job(active_row) if active_row else None
                metrics = self._calculate_metrics_conn(conn)
                queue_depth = metrics.get("desktop_jobs_queued", 0)
                quota_usd = metrics.get("desktop_quota_saved_usd", 0.0)
                quota_vnd = metrics.get("desktop_quota_saved_vnd", 0)
            finally:
                conn.close()

        manager = self._get_desktop_manager()
        if manager is not None:
            status_dict = manager.get_status(
                driver=driver,
                target_os=norm_target_os,
                app_path=clean_app_path,
                queue_depth=queue_depth,
            ).to_dict()
        elif detect_desktop_environment is not None:
            status_dict = detect_desktop_environment(
                driver=driver,
                target_os=norm_target_os,
                app_path=clean_app_path,
            ).to_dict()
            status_dict["queue_depth"] = queue_depth
        else:
            status_dict = {
                "os_platform": sys.platform if norm_target_os == "auto" else norm_target_os,
                "driver_name": driver,
                "ready": False,
                "app_detected": False,
                "app_name": None,
                "app_path": clean_app_path,
                "bundle_id": None,
                "app_version": None,
                "app_running": False,
                "available_backends": [],
                "permissions": {},
                "queue_depth": queue_depth,
                "lock_busy": False,
                "warnings": ["desktop_worker module is not available"],
                "remediation_steps": ["Ensure packages/orchestrator/desktop_worker.py is installed."],
            }

        ws_candidate = os.path.realpath(str(self.workspace_root))
        default_ws = ws_candidate if (os.path.isdir(ws_candidate) and not _is_sensitive_workspace_root(ws_candidate)) else None
        share_metrics = self.get_desktop_share_metrics()
        desktop_share_summary = {
            "target_share": share_metrics["target_desktop_share"],
            "current_share": share_metrics["current_desktop_share"],
            "eligible_tasks": share_metrics["eligible_tasks"],
            "desktop_tasks": share_metrics["desktop_tasks"],
            "desktop_ready": _is_desktop_auto_ready(status_dict),
        }

        return {
            "status": "ok",
            "desktop": status_dict,
            "desktop_share": desktop_share_summary,
            "quota_saved_usd": quota_usd,
            "quota_saved_vnd": quota_vnd,
            "agy_quota_saved_usd": quota_usd,
            "active_job": active_job,
            "queue_depth": queue_depth,
            "workspace_root": default_ws,
        }

    def _get_cached_desktop_status(self, force_refresh: bool = False) -> dict:
        """Return cached get_desktop_status() with a 3.0s TTL for fast router auto-detection."""
        now_mono = time.monotonic()
        with self._desktop_status_cache_lock:
            cached = self._desktop_status_cache_val
            age = now_mono - self._desktop_status_cache_ts
            if not force_refresh and cached is not None and age < self._desktop_status_cache_ttl:
                snapshot = dict(cached)
                desk = dict(snapshot.get("desktop") or {})
                live_qsize = self._desktop_queue.qsize()
                live_busy = bool(self._desktop_active_job_id is not None)
                if live_busy or live_qsize > 0:
                    desk["lock_busy"] = bool(desk.get("lock_busy") or live_busy)
                    desk["queue_depth"] = max(int(desk.get("queue_depth") or 0), live_qsize)
                snapshot["desktop"] = desk
                return snapshot

        fresh = self.get_desktop_status(driver="auto")
        with self._desktop_status_cache_lock:
            self._desktop_status_cache_val = fresh
            self._desktop_status_cache_ts = time.monotonic()
            return dict(fresh)

    def get_desktop_share_metrics(self, target_share: float | None = None) -> dict:
        """Compute current Gemini Desktop App peer share across non-cancelled eligible tasks."""
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("SELECT task_id, agent_type, model, complexity, status, scope FROM tasks")
                rows = cur.fetchall()
            finally:
                conn.close()
        return self._compute_desktop_share_from_tasks([dict(r) for r in rows], target_share=target_share)

    def apply_dag_allocations(self, allocations: list[dict], source_tasks: list[dict] | None = None) -> dict:
        """Persist DAG-allocated models to pending tasks in SQLite tasks table."""
        src_by_id: dict[str, dict] = {}
        for st in (source_tasks or []):
            if isinstance(st, dict) and st.get("task_id"):
                src_by_id[str(st["task_id"])] = st

        applied_ids: list[str] = []
        skipped_ids: list[str] = []
        updated_tasks: list[dict] = []

        for alloc in allocations:
            tid = str(alloc.get("task_id") or "").strip()
            if not tid:
                continue
            src = src_by_id.get(tid, {})
            with self._lock:
                conn = self._get_connection()
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT status FROM tasks WHERE task_id = ?", (tid,))
                    row = cur.fetchone()
                    existing_status = str(row["status"]).strip().lower() if row else None
                finally:
                    conn.close()

            if existing_status is not None and existing_status != "pending":
                skipped_ids.append(tid)
                continue
            if existing_status is None and str(src.get("status") or "pending").strip().lower() != "pending":
                skipped_ids.append(tid)
                continue

            effort_val = alloc.get("reasoning_effort")
            task_obj = self.upsert_task(
                task_id=tid,
                agent_type=alloc.get("agent_type") or src.get("agent_type") or ("builder" if existing_status is None else None),
                status="pending" if existing_status is None else None,
                progress=0 if existing_status is None else None,
                scope=src.get("scope") if existing_status is None else None,
                notes=src.get("notes") if existing_status is None else None,
                model=alloc.get("model"),
                complexity=(src.get("complexity") or src.get("tier")) if existing_status is None else None,
                depends_on=src.get("depends_on") if existing_status is None else None,
                parallel_group=(alloc.get("parallel_group") or src.get("parallel_group")) if existing_status is None else None,
                reasoning_effort=effort_val if effort_val else "",
            )
            applied_ids.append(tid)
            updated_tasks.append(task_obj)

        return {
            "applied_task_ids": applied_ids,
            "skipped_task_ids": skipped_ids,
            "applied_count": len(applied_ids),
            "tasks": updated_tasks,
        }

    @staticmethod
    def _parse_bool_flag(raw_value: Any, field_name: str, default: bool) -> bool:
        """Parse optional JSON boolean flag strictly."""
        if raw_value is None:
            return default
        if isinstance(raw_value, bool):
            return raw_value
        if isinstance(raw_value, (int, float)):
            return bool(raw_value)
        if isinstance(raw_value, str):
            val_str = raw_value.strip().lower()
            if val_str in ("true", "1", "yes", "on"):
                return True
            if val_str in ("false", "0", "no", "off"):
                return False
            raise ValueError(f"{field_name} must be a boolean")
        raise ValueError(f"{field_name} must be a boolean")

    def enqueue_desktop_job(self, payload: dict) -> tuple[dict, bool, bool]:
        """Validate, scrub secrets, persist queued job, and dispatch sync or async."""
        if not isinstance(payload, dict):
            raise ValueError("JSON object body is required")

        prompt = payload.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt is required and must be a non-empty string")
        if len(prompt) > DEFAULT_MAX_PROMPT_CHARS:
            raise ValueError(f"prompt exceeds maximum allowed length of {DEFAULT_MAX_PROMPT_CHARS} chars")

        raw_mode = payload.get("mode")
        if raw_mode is None:
            mode = "task"
        elif not isinstance(raw_mode, str):
            raise ValueError("Invalid mode: must be 'task' or 'chat'")
        else:
            mode = raw_mode.strip().lower()
            if mode not in ("task", "chat"):
                raise ValueError(f"Invalid mode '{raw_mode}': must be 'task' or 'chat'")

        no_workspace = bool(payload.get("no_workspace", False))
        raw_ws = payload.get("workspace_path")
        if raw_ws is not None and not isinstance(raw_ws, str):
            raise ValueError("workspace_path must be a string or null")

        if isinstance(raw_ws, str) and ("\x00" in raw_ws or raw_ws.strip() != ""):
            resolved_ws = _validate_workspace_path(raw_ws)
            workspace_path: str | None = None if no_workspace else resolved_ws
        else:
            workspace_path = None
            if mode == "task" and not no_workspace:
                ws_candidate = os.path.realpath(str(self.workspace_root))
                if os.path.isdir(ws_candidate) and not _is_sensitive_workspace_root(ws_candidate):
                    workspace_path = ws_candidate

        driver = str(payload.get("driver") or "auto").strip().lower()
        if driver not in SUPPORTED_DRIVERS:
            raise ValueError(f"Invalid driver '{driver}'. Must be one of: {', '.join(SUPPORTED_DRIVERS)}")

        target_os = str(payload.get("target_os") or "auto").strip().lower()
        if target_os not in ("auto", "darwin", "win32", "linux"):
            raise ValueError(f"Invalid target_os '{target_os}'")

        raw_job_id = payload.get("job_id")
        if raw_job_id is not None and str(raw_job_id).strip() != "":
            job_id = str(raw_job_id).strip()
            if not VALID_JOB_ID_RE.match(job_id):
                raise ValueError("Invalid job_id format: must match ^[A-Za-z0-9][A-Za-z0-9._-]{1,63}$")
        else:
            ts_part = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
            job_id = f"dsk-{ts_part}-{uuid.uuid4().hex[:6]}"

        try:
            raw_timeout = payload.get("timeout_sec")
            default_timeout = 240 if int(DEFAULT_TIMEOUT_SEC or 240) == 180 else int(DEFAULT_TIMEOUT_SEC or 240)
            timeout_sec = int(default_timeout if raw_timeout is None else raw_timeout)
        except (TypeError, ValueError):
            raise ValueError("timeout_sec must be an integer")
        if timeout_sec < 1 or timeout_sec > 1800:
            raise ValueError("timeout_sec must be between 1 and 1800")

        try:
            poll_interval_ms = int(payload.get("poll_interval_ms", 750) if payload.get("poll_interval_ms") is not None else 750)
        except (TypeError, ValueError):
            raise ValueError("poll_interval_ms must be an integer")
        if poll_interval_ms < 10 or poll_interval_ms > 10000:
            raise ValueError("poll_interval_ms must be between 10 and 10000")

        validated_output_path = _validate_output_path(payload.get("output_path"))

        redact_flag = bool(payload.get("redact_secrets", True))
        strict_flag = bool(payload.get("strict_secrets", False))
        restore_clipboard = bool(payload.get("restore_clipboard", True))
        restore_focus = bool(payload.get("restore_focus", False))
        new_chat = bool(payload.get("new_chat", True))
        async_mode = True if payload.get("async_mode") is None else bool(payload.get("async_mode"))
        background = self._parse_bool_flag(payload.get("background"), "background", True)
        allow_edits = self._parse_bool_flag(payload.get("allow_edits"), "allow_edits", False)

        task_id = str(payload["task_id"]).strip() if payload.get("task_id") else None
        raw_app_path = payload.get("app_path")
        app_path: str | None = None
        if raw_app_path is not None and str(raw_app_path).strip() != "":
            if not isinstance(raw_app_path, str):
                raise ValueError("app_path must be a string")
            app_path = _validate_desktop_app_path(raw_app_path.strip(), target_os)
        raw_meta = payload.get("metadata")
        clean_metadata = {str(k): str(v) for k, v in raw_meta.items()} if isinstance(raw_meta, dict) else {}

        # Always redact preview stored in SQLite so raw secrets are never persisted
        preview_scrubbed, _, _ = self._scrub_prompt(prompt, strict=False, redact=True)
        prompt_preview = preview_scrubbed[:200]

        sanitized_prompt, redactions, blocked_by_strict = self._scrub_prompt(
            prompt, strict=strict_flag, redact=redact_flag
        )
        redaction_count = sum(int(v) for v in redactions.values())
        os_platform = sys.platform if target_os == "auto" else target_os
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if blocked_by_strict:
            err_msg = "Rejected by strict_secrets policy: secret pattern(s) detected in prompt."
            with self._lock:
                conn = self._get_connection()
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT job_id FROM desktop_jobs WHERE job_id = ?", (job_id,))
                    if cur.fetchone():
                        raise ValueError(f"Duplicate job_id '{job_id}'")
                    with conn:
                        conn.execute(
                            """
                            INSERT INTO desktop_jobs (
                                job_id, task_id, status, os_platform, driver_name, app_path,
                                mode, workspace_path, workspace_attached, background, allow_edits,
                                prompt_chars, prompt_preview, redaction_count, redactions_json,
                                artifact_path, summary_excerpt, output_chars, duration_ms,
                                estimated_saved_usd, estimated_saved_vnd, clipboard_restored,
                                error_message, created_at, started_at, completed_at
                            ) VALUES (?, ?, 'rejected_secrets', ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, NULL, '', 0, 0, 0.0, 0, 1, ?, ?, NULL, ?)
                            """,
                            (
                                job_id,
                                task_id,
                                os_platform,
                                driver,
                                app_path,
                                mode,
                                workspace_path,
                                1 if background else 0,
                                1 if allow_edits else 0,
                                len(prompt),
                                prompt_preview,
                                redaction_count,
                                json.dumps(redactions),
                                err_msg,
                                now,
                                now,
                            ),
                        )
                    cur.execute("SELECT * FROM desktop_jobs WHERE job_id = ?", (job_id,))
                    rejected_job = self._row_to_desktop_job(cur.fetchone())
                    metrics = self._calculate_metrics_conn(conn)
                finally:
                    conn.close()

            self.append_log(
                task_id or job_id,
                "desktop-worker",
                "warn",
                f"Desktop job {job_id} rejected by strict_secrets ({redaction_count} secret match(es): {redactions})",
            )
            self.broadcast("desktop_job_failed", {"job": rejected_job, "metrics": metrics})
            return rejected_job, async_mode, True

        # Ensure DesktopWorkerManager symbols loaded so we can construct DesktopJobRequest
        self._get_desktop_manager()
        if DesktopJobRequest is not None:
            req_kwargs = dict(
                job_id=job_id,
                prompt=sanitized_prompt,
                task_id=task_id,
                driver=driver,
                target_os=target_os,
                app_path=app_path,
                timeout_sec=timeout_sec,
                poll_interval_ms=poll_interval_ms,
                output_path=validated_output_path,
                redact_secrets=redact_flag,
                strict_secrets=strict_flag,
                restore_clipboard=restore_clipboard,
                restore_focus=restore_focus,
                new_chat=new_chat,
                metadata=clean_metadata,
            )
            try:
                sig_params = inspect.signature(DesktopJobRequest).parameters
                has_var_kw = any(
                    p.kind == inspect.Parameter.VAR_KEYWORD
                    for p in sig_params.values()
                )
                if has_var_kw or "mode" in sig_params:
                    req_kwargs["mode"] = mode
                if has_var_kw or "workspace_path" in sig_params:
                    req_kwargs["workspace_path"] = workspace_path
                if has_var_kw or "background" in sig_params:
                    req_kwargs["background"] = bool(background)
                if has_var_kw or "allow_edits" in sig_params:
                    req_kwargs["allow_edits"] = bool(allow_edits)
            except (TypeError, ValueError):
                pass
            req_obj = DesktopJobRequest(**req_kwargs)
        else:
            req_obj = None

        cancel_event = threading.Event()
        done_event = threading.Event()

        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("SELECT job_id FROM desktop_jobs WHERE job_id = ?", (job_id,))
                if cur.fetchone():
                    raise ValueError(f"Duplicate job_id '{job_id}'")
                with conn:
                    conn.execute(
                        """
                        INSERT INTO desktop_jobs (
                            job_id, task_id, status, os_platform, driver_name, app_path,
                            mode, workspace_path, workspace_attached, background, allow_edits,
                            prompt_chars, prompt_preview, redaction_count, redactions_json,
                            artifact_path, summary_excerpt, output_chars, duration_ms,
                            estimated_saved_usd, estimated_saved_vnd, clipboard_restored,
                            error_message, created_at, started_at, completed_at
                        ) VALUES (?, ?, 'queued', ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, NULL, '', 0, 0, 0.0, 0, 1, NULL, ?, NULL, NULL)
                        """,
                        (
                            job_id,
                            task_id,
                            os_platform,
                            driver,
                            app_path,
                            mode,
                            workspace_path,
                            1 if background else 0,
                            1 if allow_edits else 0,
                            len(prompt),
                            prompt_preview,
                            redaction_count,
                            json.dumps(redactions),
                            now,
                        ),
                    )
                cur.execute("SELECT * FROM desktop_jobs WHERE job_id = ?", (job_id,))
                queued_job = self._row_to_desktop_job(cur.fetchone())
                metrics = self._calculate_metrics_conn(conn)
            finally:
                conn.close()

            self._desktop_cancel_events[job_id] = cancel_event
            self._desktop_done_events[job_id] = done_event
            self._desktop_requests[job_id] = req_obj
            self._desktop_redactions[job_id] = redactions

        if not redact_flag:
            self.append_log(
                task_id or job_id,
                "desktop-worker",
                "warn",
                f"Desktop job {job_id} dispatched with redact_secrets=False",
            )
        elif redaction_count > 0:
            self.append_log(
                task_id or job_id,
                "desktop-worker",
                "warn",
                f"SecretRedactor scrubbed {redaction_count} secret(s) prior to Desktop dispatch for {job_id}: {redactions}",
            )

        self.broadcast("desktop_job_queued", {"job": queued_job, "metrics": metrics})
        self._desktop_queue.put(job_id)

        if not async_mode:
            done_event.wait(timeout=timeout_sec + 15)
            final_job = self.get_desktop_job(job_id) or queued_job
            return final_job, False, False

        return queued_job, True, False

    def list_desktop_jobs(
        self,
        job_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        safe_limit = max(1, min(1000, int(limit or 50)))
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                clauses = []
                params: list = []
                if job_id:
                    clauses.append("job_id = ?")
                    params.append(job_id)
                if status and status.lower() != "all":
                    clauses.append("status = ?")
                    params.append(status.lower())
                where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
                params.append(safe_limit)
                cur.execute(
                    f"SELECT * FROM desktop_jobs {where_sql} ORDER BY created_at DESC, rowid DESC LIMIT ?",
                    tuple(params),
                )
                return [self._row_to_desktop_job(r) for r in cur.fetchall()]
            finally:
                conn.close()

    def get_desktop_jobs_response(
        self,
        job_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> dict:
        jobs = self.list_desktop_jobs(job_id=job_id, status=status, limit=limit)
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("SELECT status, estimated_saved_usd, estimated_saved_vnd FROM desktop_jobs")
                all_rows = cur.fetchall()
            finally:
                conn.close()

        total = len(all_rows)
        queued = sum(1 for r in all_rows if r["status"] == "queued")
        running = sum(1 for r in all_rows if r["status"] == "running")
        completed = sum(1 for r in all_rows if r["status"] == "completed")
        failed = sum(1 for r in all_rows if r["status"] in ("failed", "timed_out", "rejected_secrets"))
        cancelled = sum(1 for r in all_rows if r["status"] == "cancelled")
        total_saved_usd = round(
            sum(float(r["estimated_saved_usd"] or 0.0) for r in all_rows if r["status"] == "completed"),
            4,
        )
        total_saved_vnd = sum(
            int(
                r["estimated_saved_vnd"]
                if "estimated_saved_vnd" in r.keys() and r["estimated_saved_vnd"] is not None
                else round(float(r["estimated_saved_usd"] or 0.0) * USD_TO_VND_RATE)
            )
            for r in all_rows
            if r["status"] == "completed"
        )
        return {
            "status": "ok",
            "jobs": jobs,
            "summary": {
                "total": total,
                "queued": queued,
                "running": running,
                "completed": completed,
                "failed": failed,
                "cancelled": cancelled,
                "total_saved_usd": total_saved_usd,
                "total_saved_vnd": total_saved_vnd,
            },
        }

    def get_desktop_job(self, job_id: str) -> dict | None:
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM desktop_jobs WHERE job_id = ?", (job_id,))
                row = cur.fetchone()
                return self._row_to_desktop_job(row) if row else None
            finally:
                conn.close()

    def cancel_desktop_job(self, job_id: str) -> dict | None:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        transitioned = False
        agent_task_id = None
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM desktop_jobs WHERE job_id = ?", (job_id,))
                row = cur.fetchone()
                if not row:
                    return None

                cancel_ev = self._desktop_cancel_events.get(job_id)
                if cancel_ev is not None:
                    cancel_ev.set()

                prev_status = row["status"]
                agent_task_id = row["task_id"]
                if prev_status in ("queued", "running"):
                    transitioned = True
                    with conn:
                        conn.execute(
                            "UPDATE desktop_jobs SET status = 'cancelled', completed_at = COALESCE(completed_at, ?), error_message = COALESCE(error_message, 'Cancelled by user') WHERE job_id = ?",
                            (now, job_id),
                        )
                    if prev_status == "queued":
                        done_ev = self._desktop_done_events.get(job_id)
                        if done_ev is not None:
                            done_ev.set()

                cur.execute("SELECT * FROM desktop_jobs WHERE job_id = ?", (job_id,))
                job_dict = self._row_to_desktop_job(cur.fetchone())
                metrics = self._calculate_metrics_conn(conn)
            finally:
                conn.close()

        if transitioned:
            self.append_log(
                agent_task_id or job_id,
                "desktop-worker",
                "warn",
                f"Desktop job {job_id} cancelled by user (was {prev_status}).",
            )
            self.broadcast("desktop_job_cancelled", {"job": job_dict, "metrics": metrics})
        return job_dict

    def get_state(self):
        with self._lock:
            conn = self._get_connection()
            try:
                cur = conn.cursor()
                cur.execute("SELECT * FROM tasks ORDER BY created_at ASC")
                task_rows = cur.fetchall()
                tasks = [self._row_to_task(r) for r in task_rows]

                cur.execute("SELECT timestamp, task_id, agent_type, level, message FROM logs ORDER BY id DESC LIMIT 200")
                log_rows = cur.fetchall()
                logs = [dict(r) for r in reversed(log_rows)]

                cur.execute("SELECT * FROM desktop_jobs ORDER BY created_at DESC, rowid DESC LIMIT 50")
                desktop_rows = cur.fetchall()
                desktop_jobs = [self._row_to_desktop_job(r) for r in desktop_rows]

                metrics = self._calculate_metrics_conn(conn)
                share_metrics = self._compute_desktop_share_from_tasks(tasks)
                return {
                    "tasks": tasks,
                    "logs": logs,
                    "metrics": metrics,
                    "desktop_jobs": desktop_jobs,
                    "desktop": {
                        "jobs_total": metrics["desktop_jobs_total"],
                        "jobs_queued": metrics["desktop_jobs_queued"],
                        "jobs_running": metrics["desktop_jobs_running"],
                        "jobs_completed": metrics["desktop_jobs_completed"],
                        "queue_depth": metrics["desktop_jobs_queued"],
                        "active_job_id": self._desktop_active_job_id,
                        "agy_quota_saved_usd": metrics["desktop_quota_saved_usd"],
                        "agy_quota_saved_vnd": metrics["desktop_quota_saved_vnd"],
                        "desktop_share": share_metrics,
                    },
                }
            finally:
                conn.close()

    @staticmethod
    def _compute_desktop_share_from_tasks(
        tasks: list[dict],
        target_share: float | None = None,
    ) -> dict:
        """Compute desktop share metrics from an already-fetched task list."""
        resolved_target = (
            DEFAULT_DESKTOP_TARGET_SHARE
            if target_share is None
            else clamp_desktop_share(target_share, DEFAULT_DESKTOP_TARGET_SHARE)
        )
        eligible_tasks = 0
        desktop_tasks = 0
        for t in tasks:
            status = str(t.get("status") or "pending").strip().lower()
            if status == "cancelled":
                continue
            canon_model = normalize_model_name(t.get("model"))
            is_desktop = canon_model == "gemini-desktop-app"
            if is_desktop or is_task_desktop_eligible(
                agent_type=t.get("agent_type") or "",
                complexity=t.get("complexity") or "medium",
                scope=t.get("scope") or "",
            ):
                eligible_tasks += 1
                if is_desktop:
                    desktop_tasks += 1
        current_share = round(desktop_tasks / eligible_tasks, 4) if eligible_tasks > 0 else 0.0
        return {
            "eligible_tasks": eligible_tasks,
            "desktop_tasks": desktop_tasks,
            "api_tasks": max(0, eligible_tasks - desktop_tasks),
            "current_desktop_share": current_share,
            "current_share": current_share,
            "target_desktop_share": resolved_target,
            "target_share": resolved_target,
        }

    def reset(self):
        with self._lock:
            for ev in list(self._desktop_cancel_events.values()):
                ev.set()
            for ev in list(self._desktop_done_events.values()):
                ev.set()
            while True:
                try:
                    self._desktop_queue.get_nowait()
                    self._desktop_queue.task_done()
                except queue.Empty:
                    break
            self._desktop_requests.clear()
            self._desktop_redactions.clear()
            self._desktop_active_job_id = None

            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("DELETE FROM tasks")
                    conn.execute("DELETE FROM logs")
                    conn.execute("DELETE FROM desktop_jobs")
                metrics = self._calculate_metrics_conn(conn)
            finally:
                conn.close()
        with self._desktop_status_cache_lock:
            self._desktop_status_cache_val = None
            self._desktop_status_cache_ts = 0.0
        self.broadcast("reset_event", {"metrics": metrics})
        return {"status": "ok", "metrics": metrics}

    def subscribe(self):
        q = queue.Queue(maxsize=5000)
        with self._lock:
            self.subscribers.add(q)
        return q

    def unsubscribe(self, q):
        with self._lock:
            self.subscribers.discard(q)

    def broadcast(self, event_type, payload):
        data = f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
        with self._lock:
            for q in list(self.subscribers):
                try:
                    q.put_nowait(data)
                except queue.Full:
                    # Ring-buffer policy: discard oldest unread message, push newest event.
                    # NEVER kill or drop the subscriber connection on high log volume!
                    try:
                        q.get_nowait()
                        q.put_nowait(data)
                    except Exception:
                        pass


GLOBAL_STORE = StateStore()
_migrate_db = StateStore._migrate_db

# ---------------------------------------------------------------------------
# HTML Dashboard Fallback Template
# ---------------------------------------------------------------------------

_FALLBACK_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Hospital Suite - Multi-Agent Orchestrator</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          fontFamily: {
            sans: ['"Plus Jakarta Sans"', 'sans-serif'],
            mono: ['"JetBrains Mono"', 'monospace'],
          },
          colors: {
            brand: {
              50: '#eef2ff',
              100: '#e0e7ff',
              500: '#6366f1',
              600: '#4f46e5',
              700: '#4338ca',
            }
          }
        }
      }
    }
  </script>
  <style>
    @keyframes pulse-slow {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.4; }
    }
    .pulse-slow {
      animation: pulse-slow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }
    ::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    ::-webkit-scrollbar-track {
      background: #090d16;
    }
    ::-webkit-scrollbar-thumb {
      background: #1e293b;
      border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: #334155;
    }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 font-sans min-h-screen antialiased flex flex-col">

  <!-- Header -->
  <header class="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <div class="h-9 w-9 rounded-xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <div>
          <div class="flex items-center space-x-2">
            <h1 class="text-base font-bold tracking-tight text-white">Hospital Suite</h1>
            <span class="text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 font-medium border border-indigo-500/20">Orchestrator v2.0</span>
          </div>
          <p class="text-xs text-slate-400">1-Agent = 1-Skill Real-Time Execution Engine</p>
        </div>
      </div>
      
      <div class="flex items-center space-x-4">
        <!-- SSE Status Indicator -->
        <div id="sse-indicator" class="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-slate-800/70 border border-slate-700/50 text-xs">
          <span id="sse-dot" class="h-2 w-2 rounded-full bg-amber-400 pulse-slow"></span>
          <span id="sse-status" class="text-slate-300 font-medium">Connecting...</span>
        </div>

        <button onclick="resetState()" class="text-xs px-3 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 transition font-medium flex items-center space-x-1.5">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
          <span>Reset</span>
        </button>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="border-t border-slate-800/80 px-4 sm:px-6 lg:px-8 bg-slate-900/40">
      <div class="max-w-7xl mx-auto flex space-x-2 sm:space-x-4">
        <button id="tab-btn-live" onclick="switchTab('live')" class="py-2.5 px-3 border-b-2 font-semibold text-xs sm:text-sm flex items-center space-x-2 transition border-indigo-500 text-white">
          <svg class="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
          <span>⚡ Live Dashboard</span>
          <span id="tab-live-badge" class="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-indigo-500/20 text-indigo-300 font-mono">0</span>
        </button>

        <button id="tab-btn-history" onclick="switchTab('history')" class="py-2.5 px-3 border-b-2 font-semibold text-xs sm:text-sm flex items-center space-x-2 transition border-transparent text-slate-400 hover:text-slate-200">
          <svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          <span>📜 Usage History & Cost Audit</span>
          <span id="tab-cost-badge" class="ml-1 px-2 py-0.5 rounded-full text-[10px] bg-emerald-500/20 text-emerald-300 font-mono font-bold">$0.00</span>
        </button>

        <button id="tab-btn-logs" onclick="switchTab('logs')" class="py-2.5 px-3 border-b-2 font-semibold text-xs sm:text-sm flex items-center space-x-2 transition border-transparent text-slate-400 hover:text-slate-200">
          <svg class="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
          <span>🖥️ System Logs</span>
        </button>
      </div>
    </div>
  </header>

  <!-- Main Content -->
  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 w-full space-y-6">

    <!-- =================================================================== -->
    <!-- TAB 1: LIVE DASHBOARD -->
    <!-- =================================================================== -->
    <div id="tab-view-live" class="space-y-6">
      <!-- Pipeline Stage Visualizer -->
      <div class="bg-slate-900/50 border border-slate-800/70 rounded-2xl p-4 sm:p-5">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-xs font-semibold tracking-wider text-slate-400 uppercase">Delivery Pipeline Stages</h2>
          <span id="pipeline-status-text" class="text-xs text-indigo-400 font-medium">Auto-synced</span>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5" id="pipeline-stages">
          <!-- Rendered dynamically -->
        </div>
      </div>

      <!-- Parallel Concurrency Banner (Visible when multiple workers active) -->
      <div id="parallel-concurrency-banner" class="hidden bg-gradient-to-r from-amber-500/10 via-indigo-500/10 to-purple-500/10 border border-amber-500/30 rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3 shadow-lg shadow-amber-500/5">
        <div class="flex items-center space-x-3">
          <div class="h-3 w-3 rounded-full bg-amber-400 animate-ping"></div>
          <div>
            <div class="text-xs font-bold text-amber-300 flex items-center gap-1.5">
              <span>⚡ CONCURRENT PARALLEL WORKERS ACTIVE</span>
              <span id="parallel-worker-count" class="px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 text-[10px] font-mono border border-amber-500/30">0 Workers</span>
            </div>
            <p class="text-[11px] text-slate-300 mt-0.5">Tasks running in parallel with decoupled dependencies and isolated non-overlapping scopes.</p>
          </div>
        </div>
        <div id="parallel-groups-badges" class="flex flex-wrap gap-1.5">
          <!-- Rendered dynamically -->
        </div>
      </div>

      <!-- Metric Cards Grid -->
      <div class="grid grid-cols-2 lg:grid-cols-6 gap-3 sm:gap-4">
        <!-- Total Tasks -->
        <div class="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 hover:border-slate-700 transition">
          <div class="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Total Tasks</span>
            <svg class="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>
          </div>
          <div class="mt-2 flex items-baseline space-x-2">
            <span id="metric-total" class="text-2xl sm:text-3xl font-bold text-white">0</span>
          </div>
        </div>

        <!-- In Progress -->
        <div class="bg-slate-900/60 border border-blue-900/30 rounded-2xl p-4 hover:border-blue-800/50 transition">
          <div class="flex items-center justify-between text-blue-400 text-xs font-medium">
            <span>In Progress</span>
            <svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
          </div>
          <div class="mt-2 flex items-baseline space-x-2">
            <span id="metric-running" class="text-2xl sm:text-3xl font-bold text-blue-400">0</span>
            <span class="text-xs text-blue-400/70">active</span>
          </div>
        </div>

        <!-- Parallel Active Workers -->
        <div class="bg-slate-900/60 border border-amber-900/30 rounded-2xl p-4 hover:border-amber-800/50 transition">
          <div class="flex items-center justify-between text-amber-400 text-xs font-medium">
            <span>Parallel Workers</span>
            <svg class="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
          </div>
          <div class="mt-2 flex items-baseline space-x-2">
            <span id="metric-parallel" class="text-2xl sm:text-3xl font-bold text-amber-400">0</span>
            <span class="text-xs text-amber-400/70">concurrent</span>
          </div>
        </div>

        <!-- Completed -->
        <div class="bg-slate-900/60 border border-emerald-900/30 rounded-2xl p-4 hover:border-emerald-800/50 transition">
          <div class="flex items-center justify-between text-emerald-400 text-xs font-medium">
            <span>Completed</span>
            <svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
          </div>
          <div class="mt-2 flex items-baseline space-x-2">
            <span id="metric-completed" class="text-2xl sm:text-3xl font-bold text-emerald-400">0</span>
            <span class="text-xs text-emerald-400/70">done</span>
          </div>
        </div>

        <!-- Blocked / Failed / Cancelled -->
        <div class="bg-slate-900/60 border border-rose-900/30 rounded-2xl p-4 hover:border-rose-800/50 transition">
          <div class="flex items-center justify-between text-rose-400 text-xs font-medium">
            <span>Blocked / Stop</span>
            <svg class="w-4 h-4 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
          </div>
          <div class="mt-2 flex items-baseline space-x-2">
            <span id="metric-blocked" class="text-2xl sm:text-3xl font-bold text-rose-400">0</span>
          </div>
        </div>

        <!-- Active Agents -->
        <div class="bg-slate-900/60 border border-purple-900/30 rounded-2xl p-4 hover:border-purple-800/50 transition">
          <div class="flex items-center justify-between text-purple-400 text-xs font-medium">
            <span>Active Agents</span>
            <svg class="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" /></svg>
          </div>
          <div class="mt-2 flex items-baseline space-x-2">
            <span id="metric-agents" class="text-2xl sm:text-3xl font-bold text-purple-400">0</span>
            <span class="text-xs text-purple-400/70">working</span>
          </div>
        </div>
      </div>

      <!-- Token Consumption, Cost & Context Cache Telemetry -->
      <div class="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 sm:p-5 shadow-lg">
        <div class="flex items-center justify-between mb-3 border-b border-slate-800/60 pb-2">
          <div class="flex items-center space-x-2">
            <div class="h-2 w-2 rounded-full bg-cyan-400"></div>
            <h2 class="text-xs font-semibold tracking-wider text-slate-300 uppercase">Token Consumption, Financial Cost & Context Cache Telemetry</h2>
          </div>
          <div class="flex items-center space-x-2">
            <span class="text-xs text-slate-400">Context Cache Hit Rate:</span>
            <span id="metric-cache-rate" class="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-bold border border-emerald-500/20 font-mono">0%</span>
          </div>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <!-- Input Tokens -->
          <div class="bg-slate-950/60 border border-slate-800/60 rounded-xl p-3">
            <div class="text-[11px] text-slate-400 font-medium flex items-center justify-between">
              <span>Input (Prompt)</span>
              <span class="text-cyan-400 text-xs font-mono">📥 In</span>
            </div>
            <div class="mt-1 flex items-baseline space-x-1.5">
              <span id="metric-tokens-in" class="text-lg sm:text-xl font-bold font-mono text-cyan-400">0</span>
              <span class="text-[10px] text-slate-500">tok</span>
            </div>
          </div>

          <!-- Output Tokens -->
          <div class="bg-slate-950/60 border border-slate-800/60 rounded-xl p-3">
            <div class="text-[11px] text-slate-400 font-medium flex items-center justify-between">
              <span>Output (Generated)</span>
              <span class="text-purple-400 text-xs font-mono">📤 Out</span>
            </div>
            <div class="mt-1 flex items-baseline space-x-1.5">
              <span id="metric-tokens-out" class="text-lg sm:text-xl font-bold font-mono text-purple-400">0</span>
              <span class="text-[10px] text-slate-500">tok</span>
            </div>
          </div>

          <!-- Cached Tokens -->
          <div class="bg-slate-950/60 border border-slate-800/60 rounded-xl p-3">
            <div class="text-[11px] text-slate-400 font-medium flex items-center justify-between">
              <span>Context Cache Read</span>
              <span class="text-emerald-400 text-xs font-mono">⚡ Cache</span>
            </div>
            <div class="mt-1 flex items-baseline space-x-1.5">
              <span id="metric-tokens-cache" class="text-lg sm:text-xl font-bold font-mono text-emerald-400">0</span>
              <span class="text-[10px] text-slate-500">tok</span>
            </div>
          </div>

          <!-- Grand Total Tokens -->
          <div class="bg-slate-950/60 border border-slate-800/60 rounded-xl p-3">
            <div class="text-[11px] text-slate-400 font-medium flex items-center justify-between">
              <span>Total Footprint</span>
              <span class="text-amber-400 text-xs font-mono">📊 Total</span>
            </div>
            <div class="mt-1 flex items-baseline space-x-1.5">
              <span id="metric-tokens-total" class="text-lg sm:text-xl font-bold font-mono text-amber-400">0</span>
              <span class="text-[10px] text-slate-500">tok</span>
            </div>
          </div>

          <!-- Financial Cost -->
          <div class="bg-gradient-to-br from-indigo-950/40 to-slate-950/80 border border-indigo-500/30 rounded-xl p-3 shadow-sm">
            <div class="text-[11px] text-indigo-300 font-medium flex items-center justify-between">
              <span>Estimated Cost</span>
              <span class="text-indigo-400 text-xs font-mono">💰 Spend</span>
            </div>
            <div class="mt-1 flex flex-col">
              <span id="metric-cost-usd" class="text-lg sm:text-xl font-bold font-mono text-indigo-400">$0.00</span>
              <span id="metric-cost-vnd" class="text-[10px] text-indigo-300/80 font-mono">~ 0 ₫</span>
            </div>
          </div>

          <!-- Cache Savings -->
          <div class="bg-gradient-to-br from-emerald-950/40 to-slate-950/80 border border-emerald-500/30 rounded-xl p-3 shadow-sm">
            <div class="text-[11px] text-emerald-300 font-medium flex items-center justify-between">
              <span>Cache Savings</span>
              <span class="text-emerald-400 text-xs font-mono">🛡️ Saved</span>
            </div>
            <div class="mt-1 flex flex-col">
              <span id="metric-saved-usd" class="text-lg sm:text-xl font-bold font-mono text-emerald-400">$0.00</span>
              <span id="metric-saved-vnd" class="text-[10px] text-emerald-300/80 font-mono">~ 0 ₫ saved</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Active Tasks Table -->
      <div class="bg-slate-900/50 border border-slate-800/80 rounded-2xl overflow-hidden shadow-xl">
        <div class="px-5 py-4 border-b border-slate-800/80 flex flex-wrap items-center justify-between gap-3 bg-slate-900/30">
          <div class="flex items-center space-x-2.5">
            <div class="h-2 w-2 rounded-full bg-indigo-500"></div>
            <h2 class="text-sm font-bold text-white tracking-wide">Live Tasks Status</h2>
            <span id="task-count-badge" class="px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 text-xs font-semibold">0 active</span>
            <span class="text-xs text-slate-400 font-normal hidden sm:inline">&middot; Chỉ hiển thị các tác vụ đang thực hiện & chờ xử lý</span>
          </div>

          <div class="flex items-center space-x-3 text-xs">
            <button onclick="switchTab('history')" class="text-indigo-400 hover:text-indigo-300 font-medium flex items-center space-x-1">
              <span>Xem lịch sử tác vụ &rarr;</span>
            </button>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-900/80 text-slate-400 uppercase tracking-wider text-[11px] font-semibold border-b border-slate-800/80">
              <tr>
                <th scope="col" class="py-3 px-4">Task ID</th>
                <th scope="col" class="py-3 px-4">Agent Persona</th>
                <th scope="col" class="py-3 px-4">Model Engine</th>
                <th scope="col" class="py-3 px-4">Complexity</th>
                <th scope="col" class="py-3 px-4">Parallel Group</th>
                <th scope="col" class="py-3 px-4">Conditions</th>
                <th scope="col" class="py-3 px-4">Token Usage</th>
                <th scope="col" class="py-3 px-4">Est. Cost</th>
                <th scope="col" class="py-3 px-4">Scope / Focus</th>
                <th scope="col" class="py-3 px-4">Status</th>
                <th scope="col" class="py-3 px-4 w-32">Progress</th>
                <th scope="col" class="py-3 px-4 text-center">Action</th>
                <th scope="col" class="py-3 px-4 text-right">Updated</th>
              </tr>
            </thead>
            <tbody id="tasks-tbody" class="divide-y divide-slate-800/50 text-slate-300">
              <tr>
                <td colspan="13" class="py-8 text-center text-slate-500">No tasks registered yet. Dispatch tasks using OrchestratorClient.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Real-time Console Log Stream Preview in Live View -->
      <div class="bg-slate-900/60 border border-slate-800/80 rounded-2xl overflow-hidden shadow-xl flex flex-col h-72">
        <div class="px-5 py-3 border-b border-slate-800/80 bg-slate-900/90 flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center space-x-2.5">
            <span class="flex h-2 w-2 relative">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <h2 class="text-sm font-bold text-white tracking-wide">Live Agent Telemetry & Activity Stream</h2>
          </div>
          <button onclick="switchTab('logs')" class="text-xs text-indigo-400 hover:text-indigo-300 font-medium">Open Full Log Console &rarr;</button>
        </div>
        <div id="live-logs-container" class="flex-1 p-4 font-mono text-[11px] leading-relaxed overflow-y-auto space-y-1 bg-black/60">
          <!-- Live logs rendered here -->
        </div>
      </div>
    </div>

    <!-- =================================================================== -->
    <!-- TAB 2: USAGE HISTORY & COST AUDIT -->
    <!-- =================================================================== -->
    <div id="tab-view-history" class="hidden space-y-6">
      <!-- Historical KPI Summary -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="bg-slate-900/60 border border-indigo-500/30 rounded-2xl p-5 shadow-lg">
          <div class="text-xs text-indigo-300 font-semibold uppercase tracking-wider">Total Spent</div>
          <div class="mt-2 flex items-baseline space-x-2">
            <span id="hist-total-cost-usd" class="text-3xl font-extrabold font-mono text-white">$0.00</span>
          </div>
          <div id="hist-total-cost-vnd" class="text-xs font-mono text-indigo-400 mt-1">~ 0 ₫</div>
          <div class="text-[11px] text-slate-500 mt-2">Billed token spend across all Gemini models</div>
        </div>

        <div class="bg-slate-900/60 border border-emerald-500/30 rounded-2xl p-5 shadow-lg">
          <div class="text-xs text-emerald-300 font-semibold uppercase tracking-wider flex items-center justify-between">
            <span>Cache Savings</span>
            <span class="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px] font-mono font-bold border border-emerald-500/30">75% Discount</span>
          </div>
          <div class="mt-2 flex items-baseline space-x-2">
            <span id="hist-total-saved-usd" class="text-3xl font-extrabold font-mono text-emerald-400">$0.00</span>
          </div>
          <div id="hist-total-saved-vnd" class="text-xs font-mono text-emerald-300 mt-1">~ 0 ₫ saved</div>
          <div class="text-[11px] text-slate-500 mt-2">Money saved via Gemini Context Caching</div>
        </div>

        <div class="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 shadow-lg">
          <div class="text-xs text-slate-400 font-semibold uppercase tracking-wider">Total Tokens Processed</div>
          <div class="mt-2 flex items-baseline space-x-2">
            <span id="hist-total-tokens" class="text-3xl font-extrabold font-mono text-cyan-400">0</span>
          </div>
          <div id="hist-token-breakdown" class="text-xs font-mono text-slate-400 mt-1">Prompt: 0 | Gen: 0 | Cache: 0</div>
          <div class="text-[11px] text-slate-500 mt-2">Total context window footprints</div>
        </div>

        <div class="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 shadow-lg">
          <div class="text-xs text-slate-400 font-semibold uppercase tracking-wider">Execution Efficiency</div>
          <div class="mt-2 flex items-baseline space-x-2">
            <span id="hist-cache-rate" class="text-3xl font-extrabold font-mono text-purple-400">0.0%</span>
            <span class="text-xs text-slate-400">cache hit</span>
          </div>
          <div id="hist-avg-task-cost" class="text-xs font-mono text-slate-400 mt-1">Avg cost / task: $0.00</div>
          <div class="text-[11px] text-slate-500 mt-2">Efficiency & savings ratio across pipeline</div>
        </div>
      </div>

      <!-- Filters & Actions Toolbar -->
      <div class="bg-slate-900/50 border border-slate-800/80 rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3">
        <div class="flex flex-wrap items-center gap-3 flex-1 min-w-[280px]">
          <!-- Search input -->
          <div class="relative flex-1 min-w-[200px] max-w-md">
            <span class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
            </span>
            <input type="text" id="hist-filter-search" oninput="renderHistoryTable()" placeholder="Search by task ID, persona, or scope..." class="w-full pl-9 pr-3 py-1.5 bg-slate-800/80 border border-slate-700/80 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition">
          </div>

          <!-- Filter by Status -->
          <div class="flex items-center space-x-1.5 text-xs">
            <span class="text-slate-400">Status:</span>
            <select id="hist-filter-status" onchange="renderHistoryTable()" class="bg-slate-800/80 border border-slate-700/80 rounded-xl px-2.5 py-1.5 text-slate-200 text-xs focus:outline-none focus:border-indigo-500">
              <option value="all">All Statuses</option>
              <option value="completed">Completed</option>
              <option value="running">Running</option>
              <option value="cancelled">Cancelled / Killed</option>
              <option value="blocked">Blocked / Failed</option>
              <option value="pending">Pending</option>
            </select>
          </div>

          <!-- Filter by Model -->
          <div class="flex items-center space-x-1.5 text-xs">
            <span class="text-slate-400">Model:</span>
            <select id="hist-filter-model" onchange="renderHistoryTable()" class="bg-slate-800/80 border border-slate-700/80 rounded-xl px-2.5 py-1.5 text-slate-200 text-xs focus:outline-none focus:border-indigo-500">
              <option value="all">All Models</option>
              <option value="neon">Gemini 4 Neon</option>
              <option value="carbon">Gemini 4 Carbon</option>
              <option value="hydrogen">Gemini 4 Hydrogen</option>
              <option value="argon">Gemini 4 Argon (Legacy)</option>
              <option value="flash">Gemini 3.8 Flash</option>
            </select>
          </div>
        </div>

        <!-- Export CSV Button -->
        <button onclick="exportHistoryCSV()" class="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow-md shadow-indigo-600/20 transition flex items-center space-x-1.5">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
          <span>Export CSV Audit Report</span>
        </button>
      </div>

      <!-- Detailed History Audit Table -->
      <div class="bg-slate-900/50 border border-slate-800/80 rounded-2xl overflow-hidden shadow-xl">
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-900/80 text-slate-400 uppercase tracking-wider text-[11px] font-semibold border-b border-slate-800/80">
              <tr>
                <th scope="col" class="py-3 px-4">Task ID</th>
                <th scope="col" class="py-3 px-4">Agent / Persona</th>
                <th scope="col" class="py-3 px-4">Model Engine</th>
                <th scope="col" class="py-3 px-4">Status</th>
                <th scope="col" class="py-3 px-4">Prompt In</th>
                <th scope="col" class="py-3 px-4">Generated Out</th>
                <th scope="col" class="py-3 px-4">Cache Read</th>
                <th scope="col" class="py-3 px-4">Total Tokens</th>
                <th scope="col" class="py-3 px-4">Cache Hit %</th>
                <th scope="col" class="py-3 px-4">Cost (USD / VND)</th>
                <th scope="col" class="py-3 px-4">Cache Savings</th>
                <th scope="col" class="py-3 px-4 text-center">Action</th>
                <th scope="col" class="py-3 px-4 text-right">Timestamp</th>
              </tr>
            </thead>
            <tbody id="history-tbody" class="divide-y divide-slate-800/50 text-slate-300">
              <tr>
                <td colspan="13" class="py-8 text-center text-slate-500">Loading audit records...</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- =================================================================== -->
    <!-- TAB 3: SYSTEM CONSOLE LOGS -->
    <!-- =================================================================== -->
    <div id="tab-view-logs" class="hidden space-y-4">
      <div class="bg-slate-900/60 border border-slate-800/80 rounded-2xl overflow-hidden shadow-xl flex flex-col h-[650px]">
        <div class="px-5 py-3 border-b border-slate-800/80 bg-slate-900/90 flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center space-x-2.5">
            <span class="flex h-2 w-2 relative">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <h2 class="text-sm font-bold text-white tracking-wide">Full Agent Activity & Execution Console</h2>
          </div>

          <div class="flex items-center space-x-3 text-xs">
            <!-- Level Filter -->
            <div class="flex items-center space-x-1.5">
              <span class="text-slate-400">Level:</span>
              <select id="log-filter-level" onchange="filterLogs()" class="bg-slate-800 border border-slate-700 rounded-lg px-2 py-1 text-slate-200 text-xs focus:outline-none focus:border-indigo-500">
                <option value="all">ALL</option>
                <option value="info">INFO</option>
                <option value="warn">WARN</option>
                <option value="error">ERROR</option>
                <option value="thought">THOUGHT</option>
              </select>
            </div>

            <!-- Auto Scroll Toggle -->
            <label class="flex items-center space-x-1.5 cursor-pointer text-slate-300 select-none">
              <input type="checkbox" id="autoscroll-toggle" checked class="rounded bg-slate-800 border-slate-700 text-indigo-600 focus:ring-0">
              <span>Autoscroll</span>
            </label>

            <!-- Clear Button -->
            <button onclick="clearLogConsole()" class="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition text-xs">
              Clear
            </button>
          </div>
        </div>

        <!-- Logs Container -->
        <div id="logs-container" class="flex-1 p-4 font-mono text-[11px] leading-relaxed overflow-y-auto space-y-1 bg-black/70">
          <!-- Full Logs rendered here -->
        </div>
      </div>
    </div>

  </main>

  <footer class="border-t border-slate-800/60 py-4 text-center text-xs text-slate-500">
    Hospital Suite Real-Time Multi-Agent Orchestrator &middot; Zero-Dependency SSE Architecture &middot; Automated Token & Cost Auditing
  </footer>

  <!-- Scripts -->
  <script>
    const PIPELINE_STAGES = [
      { id: 'spec', name: '1. Spec', role: 'Product / Spec' },
      { id: 'plan', name: '2. Plan', role: 'Architect' },
      { id: 'build', name: '3. Build', role: 'Software Builder' },
      { id: 'test', name: '4. Test', role: 'Test Specialist' },
      { id: 'review', name: '5. Review', role: 'Code Reviewer' },
      { id: 'security', name: '6. Security', role: 'Security Spec' },
      { id: 'ship', name: '7. Ship', role: 'DevOps / Release' }
    ];

    let currentTab = 'live';
    let state = {
      tasks: {},
      logs: [],
      metrics: {
        total: 0, pending: 0, running: 0, completed: 0, blocked: 0, cancelled: 0, active_agents: 0,
        total_input_tokens: 0, total_output_tokens: 0, total_cache_tokens: 0, grand_total_tokens: 0,
        total_cost_usd: 0, total_cost_vnd: 0, total_saved_usd: 0, total_saved_vnd: 0, cache_rate: 0
      }
    };

    function switchTab(tab) {
      currentTab = tab;
      const tabs = ['live', 'history', 'logs'];
      tabs.forEach(t => {
        const btn = document.getElementById(`tab-btn-${t}`);
        const view = document.getElementById(`tab-view-${t}`);
        if (!btn || !view) return;
        if (t === tab) {
          btn.className = "py-2.5 px-3 border-b-2 font-semibold text-xs sm:text-sm flex items-center space-x-2 transition border-indigo-500 text-white";
          view.classList.remove('hidden');
        } else {
          btn.className = "py-2.5 px-3 border-b-2 font-semibold text-xs sm:text-sm flex items-center space-x-2 transition border-transparent text-slate-400 hover:text-slate-200";
          view.classList.add('hidden');
        }
      });
      if (tab === 'history') {
        renderHistoryTable();
      }
    }

    function initPipeline() {
      const container = document.getElementById('pipeline-stages');
      if (!container) return;
      container.innerHTML = PIPELINE_STAGES.map(stage => `
        <div id="stage-${stage.id}" class="border border-slate-800 bg-slate-950/60 rounded-xl p-3 text-center transition">
          <div class="text-xs font-bold text-slate-300">${stage.name}</div>
          <div class="text-[10px] text-slate-500 mt-0.5 truncate">${stage.role}</div>
          <div id="stage-badge-${stage.id}" class="mt-2 text-[10px] py-0.5 px-2 rounded-full inline-block bg-slate-800/80 text-slate-400 font-mono">Idle</div>
        </div>
      `).join('');
    }

    function updatePipelineStages() {
      const tasks = Object.values(state.tasks);
      const stageMap = {
        spec: ['spec', 'product', 'requirements'],
        plan: ['architect', 'planner', 'design'],
        build: ['builder', 'software', 'developer'],
        test: ['test', 'tester', 'qa'],
        review: ['review', 'reviewer'],
        security: ['security', 'sec'],
        ship: ['ship', 'release', 'devops']
      };

      PIPELINE_STAGES.forEach(st => {
        const keywords = stageMap[st.id] || [st.id];
        const matched = tasks.filter(t => keywords.some(k => (t.agent_type || '').toLowerCase().includes(k)));
        const badge = document.getElementById(`stage-badge-${st.id}`);
        const card = document.getElementById(`stage-${st.id}`);
        if (!badge || !card) return;

        if (matched.some(t => t.status === 'running')) {
          badge.className = "mt-2 text-[10px] py-0.5 px-2 rounded-full inline-block bg-blue-500/20 text-blue-400 border border-blue-500/30 font-bold pulse-slow";
          badge.textContent = 'Active';
          card.className = "border border-blue-500/40 bg-blue-950/20 rounded-xl p-3 text-center shadow-lg shadow-blue-500/10";
        } else if (matched.length > 0 && matched.every(t => t.status === 'completed')) {
          badge.className = "mt-2 text-[10px] py-0.5 px-2 rounded-full inline-block bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-bold";
          badge.textContent = 'Done';
          card.className = "border border-emerald-500/30 bg-emerald-950/10 rounded-xl p-3 text-center";
        } else if (matched.some(t => t.status === 'blocked' || t.status === 'failed')) {
          badge.className = "mt-2 text-[10px] py-0.5 px-2 rounded-full inline-block bg-rose-500/20 text-rose-400 border border-rose-500/30 font-bold";
          badge.textContent = 'Blocked';
          card.className = "border border-rose-500/30 bg-rose-950/10 rounded-xl p-3 text-center";
        } else {
          badge.className = "mt-2 text-[10px] py-0.5 px-2 rounded-full inline-block bg-slate-800/80 text-slate-400 font-mono";
          badge.textContent = matched.length > 0 ? 'Queued' : 'Idle';
          card.className = "border border-slate-800 bg-slate-950/60 rounded-xl p-3 text-center";
        }
      });
    }

    function formatTokens(num) {
      if (!num || num === 0) return '0';
      if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
      if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
      return num.toLocaleString();
    }

    function formatMoneyUSD(num) {
      if (!num || num === 0) return '$0.00';
      if (num < 0.01) return '$' + num.toFixed(4);
      return '$' + num.toFixed(2);
    }

    function formatMoneyVND(num) {
      if (!num || num === 0) return '0 ₫';
      return Math.round(num).toLocaleString('vi-VN') + ' ₫';
    }

    function renderMetrics(metrics) {
      // Metric cards
      document.getElementById('metric-total').textContent = metrics.total;
      document.getElementById('metric-running').textContent = metrics.running;
      document.getElementById('metric-completed').textContent = metrics.completed;
      document.getElementById('metric-blocked').textContent = (metrics.blocked || 0) + (metrics.cancelled || 0);
      document.getElementById('metric-agents').textContent = metrics.active_agents;
      document.getElementById('task-count-badge').textContent = metrics.total;
      document.getElementById('tab-live-badge').textContent = metrics.running > 0 ? `${metrics.running} active` : metrics.total;

      const parallelCount = metrics.parallel_running || 0;
      const parallelEl = document.getElementById('metric-parallel');
      if (parallelEl) {
        parallelEl.textContent = parallelCount;
      }

      // Parallel execution banner
      const banner = document.getElementById('parallel-concurrency-banner');
      const countEl = document.getElementById('parallel-worker-count');
      const groupsEl = document.getElementById('parallel-groups-badges');
      if (banner && countEl && groupsEl) {
        if (parallelCount > 1) {
          banner.classList.remove('hidden');
          countEl.textContent = `${parallelCount} Workers Concurrently`;
          const groups = metrics.active_groups || [];
          groupsEl.innerHTML = groups.map(g => `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">⚡ ${escapeHtml(g)}</span>`).join('');
        } else {
          banner.classList.add('hidden');
        }
      }

      // Token Telemetry
      const inTok = metrics.total_input_tokens || 0;
      const outTok = metrics.total_output_tokens || 0;
      const cacheTok = metrics.total_cache_tokens || 0;
      const grandTok = metrics.grand_total_tokens || 0;
      const cacheRate = metrics.cache_rate || 0.0;

      document.getElementById('metric-tokens-in').textContent = formatTokens(inTok);
      document.getElementById('metric-tokens-out').textContent = formatTokens(outTok);
      document.getElementById('metric-tokens-cache').textContent = formatTokens(cacheTok);
      document.getElementById('metric-tokens-total').textContent = formatTokens(grandTok);
      document.getElementById('metric-cache-rate').textContent = `${cacheRate}%`;

      // Cost Telemetry
      const costUsd = metrics.total_cost_usd || 0.0;
      const costVnd = metrics.total_cost_vnd || 0;
      const savedUsd = metrics.total_saved_usd || 0.0;
      const savedVnd = metrics.total_saved_vnd || 0;

      document.getElementById('metric-cost-usd').textContent = formatMoneyUSD(costUsd);
      document.getElementById('metric-cost-vnd').textContent = `~ ${formatMoneyVND(costVnd)}`;
      document.getElementById('metric-saved-usd').textContent = formatMoneyUSD(savedUsd);
      document.getElementById('metric-saved-vnd').textContent = `~ ${formatMoneyVND(savedVnd)} saved`;
      document.getElementById('tab-cost-badge').textContent = formatMoneyUSD(costUsd);

      // Historical tab header cards
      const histCostUsd = document.getElementById('hist-total-cost-usd');
      if (histCostUsd) {
        histCostUsd.textContent = formatMoneyUSD(costUsd);
        document.getElementById('hist-total-cost-vnd').textContent = `~ ${formatMoneyVND(costVnd)}`;
        document.getElementById('hist-total-saved-usd').textContent = formatMoneyUSD(savedUsd);
        document.getElementById('hist-total-saved-vnd').textContent = `~ ${formatMoneyVND(savedVnd)} saved`;
        document.getElementById('hist-total-tokens').textContent = formatTokens(grandTok);
        document.getElementById('hist-token-breakdown').textContent = `In: ${formatTokens(inTok)} | Out: ${formatTokens(outTok)} | Cache: ${formatTokens(cacheTok)}`;
        document.getElementById('hist-cache-rate').textContent = `${cacheRate}%`;
        const completedCount = metrics.completed || 0;
        const avgCost = completedCount > 0 ? (costUsd / completedCount) : 0.0;
        document.getElementById('hist-avg-task-cost').textContent = `Avg cost / task: ${formatMoneyUSD(avgCost)} (~${formatMoneyVND(costVnd / (completedCount || 1))})`;
      }
    }

    function getStatusBadge(status) {
      switch(status) {
        case 'running':
          return '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30 inline-flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-blue-400 pulse-slow"></span>RUNNING</span>';
        case 'completed':
          return '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 inline-flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>DONE</span>';
        case 'cancelled':
          return '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30 inline-flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-rose-400"></span>CANCELLED</span>';
        case 'blocked':
        case 'failed':
          return '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30 inline-flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-rose-400"></span>BLOCKED</span>';
        default:
          return '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-800 text-slate-400 border border-slate-700">PENDING</span>';
      }
    }

    function getAgentBadge(agent) {
      const colors = {
        'builder': 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30',
        'software-builder': 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30',
        'architect': 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
        'planner': 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
        'test': 'bg-amber-500/10 text-amber-400 border-amber-500/30',
        'tester': 'bg-amber-500/10 text-amber-400 border-amber-500/30',
        'review': 'bg-purple-500/10 text-purple-400 border-purple-500/30',
        'reviewer': 'bg-purple-500/10 text-purple-400 border-purple-500/30',
        'security': 'bg-red-500/10 text-red-400 border-red-500/30',
        'orchestrator': 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
      };
      const key = (agent || '').toLowerCase();
      const style = colors[key] || 'bg-slate-800 text-slate-300 border-slate-700';
      return `<span class="px-2 py-0.5 rounded text-[11px] font-mono border ${style}">${agent || 'unknown'}</span>`;
    }

    function getModelBadge(model) {
      const m = (model || '').toLowerCase();
      if (m.includes('neon') || m.includes('neco')) {
        return `<span class="px-2 py-0.5 rounded text-[11px] font-mono border bg-rose-500/15 text-rose-300 border-rose-500/30 flex items-center gap-1 inline-flex"><span class="text-[9px]">⚡✦</span>Gemini 4 Neon</span>`;
      }
      if (m.includes('carbon') || m === 'gemini-pro-orchestrator') {
        return `<span class="px-2 py-0.5 rounded text-[11px] font-mono border bg-emerald-500/15 text-emerald-300 border-emerald-500/30 flex items-center gap-1 inline-flex"><span class="text-[9px]">✦</span>Gemini 4 Carbon</span>`;
      }
      if (m.includes('hydrogen')) {
        return `<span class="px-2 py-0.5 rounded text-[11px] font-mono border bg-cyan-500/15 text-cyan-300 border-cyan-500/30 flex items-center gap-1 inline-flex"><span class="text-[9px]">⚡</span>Gemini 4 Hydrogen</span>`;
      }
      if (m.includes('argon') || m.includes('pro')) {
        return `<span class="px-2 py-0.5 rounded text-[11px] font-mono border bg-indigo-500/15 text-indigo-300 border-indigo-500/30 flex items-center gap-1 inline-flex"><span class="text-[9px]">✦</span>Argon (Legacy)</span>`;
      }
      if (m.includes('flash_lite') || m.includes('lite')) {
        return `<span class="px-2 py-0.5 rounded text-[11px] font-mono border bg-teal-500/15 text-teal-300 border-teal-500/30 flex items-center gap-1 inline-flex"><span class="text-[9px]">⚡</span>Flash-Lite</span>`;
      }
      if (m.includes('flash') || m.includes('3.8')) {
        return `<span class="px-2 py-0.5 rounded text-[11px] font-mono border bg-sky-500/15 text-sky-300 border-sky-500/30 flex items-center gap-1 inline-flex"><span class="text-[9px]">⚡</span>3.8 Flash</span>`;
      }
      return `<span class="px-2 py-0.5 rounded text-[11px] font-mono border bg-slate-800 text-slate-400 border-slate-700">${model || 'auto'}</span>`;
    }

    function getComplexityBadge(comp) {
      const c = (comp || 'medium').toLowerCase();
      const badges = {
        'critical': 'bg-rose-500/20 text-rose-300 border-rose-500/40 font-bold',
        'high': 'bg-amber-500/20 text-amber-300 border-amber-500/40 font-bold',
        'medium': 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30',
        'low': 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
      };
      const style = badges[c] || badges['medium'];
      return `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase border ${style}">${c}</span>`;
    }

    function formatTime(isoStr) {
      if (!isoStr) return '-';
      try {
        const d = new Date(isoStr);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      } catch (e) {
        return isoStr;
      }
    }

    function killTask(taskId) {
      if (!confirm(`Are you sure you want to stop/kill agent running task ${taskId}?`)) {
        return;
      }
      fetch('/api/tasks/kill', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: taskId, reason: 'Manual kill from Dashboard UI' })
      })
      .then(res => res.json())
      .then(data => {
        if (data.task) {
          state.tasks[data.task.task_id] = data.task;
          renderTasksTable();
          renderHistoryTable();
        }
      })
      .catch(err => alert('Failed to kill task: ' + err));
    }

    function renderTasksTable() {
      const tbody = document.getElementById('tasks-tbody');
      if (!tbody) return;
      const allTasks = Object.values(state.tasks).sort((a, b) => (b.updated_at || '').localeCompare(a.updated_at || ''));
      
      // Live Dashboard STRICTLY ONLY shows active/in-flight tasks (pending, running, blocked)
      // Completed and cancelled tasks are strictly kept in the History tab
      const activeTasks = allTasks.filter(t => t.status === 'running' || t.status === 'pending' || t.status === 'blocked');

      const countBadge = document.getElementById('task-count-badge');
      if (countBadge) {
        countBadge.textContent = `${activeTasks.length} active`;
      }
      
      if (activeTasks.length === 0) {
        const completedCount = allTasks.filter(t => t.status === 'completed').length;
        if (completedCount > 0) {
          tbody.innerHTML = `
            <tr>
              <td colspan="13" class="py-12 text-center">
                <div class="flex flex-col items-center justify-center space-y-2.5">
                  <div class="h-10 w-10 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
                  </div>
                  <div class="text-sm font-bold text-slate-200">Không có tác vụ đang chạy hoặc chờ xử lý</div>
                  <div class="text-xs text-slate-400 max-w-md">Toàn bộ ${completedCount} tác vụ trước đó đã hoàn thành và được lưu trữ gọn gàng trong tab Lịch sử.</div>
                  <div class="pt-2">
                    <button onclick="switchTab('history')" class="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow-md shadow-indigo-600/20 transition flex items-center space-x-1.5 mx-auto">
                      <span>Mở tab Usage History & Cost Audit</span>
                      <span>&rarr;</span>
                    </button>
                  </div>
                </div>
              </td>
            </tr>
          `;
        } else {
          tbody.innerHTML = '<tr><td colspan="13" class="py-8 text-center text-slate-500">Chưa có tác vụ nào được kích hoạt. Hãy điều phối task mới thông qua OrchestratorClient.</td></tr>';
        }
        return;
      }

      tbody.innerHTML = activeTasks.map(t => {
        const pct = t.progress || 0;
        const barColor = t.status === 'completed' ? 'bg-emerald-500' : (t.status === 'blocked' || t.status === 'cancelled' ? 'bg-rose-500' : 'bg-indigo-500');

        // Parallel Group badge
        const groupBadge = t.parallel_group ? 
          `<span class="px-2 py-0.5 rounded text-[10px] font-mono border bg-amber-500/15 text-amber-300 border-amber-500/30 flex items-center gap-1 inline-flex">⚡ ${escapeHtml(t.parallel_group)}</span>` : 
          `<span class="text-slate-600 font-mono text-[10px]">-</span>`;

        // Conditions / Depends On
        let depsBadge = `<span class="text-slate-500 font-mono text-[10px]">None (Ready)</span>`;
        if (t.depends_on && t.depends_on.length > 0) {
          depsBadge = t.depends_on.map(dep => {
            const parentTask = state.tasks[dep];
            const isDone = parentTask && parentTask.status === 'completed';
            const color = isDone ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' : 'bg-rose-500/15 text-rose-300 border-rose-500/30';
            const icon = isDone ? '✓' : '⏳';
            return `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono border ${color} mr-1 inline-block" title="${dep}: ${parentTask ? parentTask.status : 'not found'}">${icon} ${dep}</span>`;
          }).join('');
        }

        // Token consumption breakdown
        const tok = t.tokens || { input: 0, output: 0, cache: 0, total: 0 };
        const tokenBadge = `
          <div class="font-mono text-[10px] flex items-center space-x-1 whitespace-nowrap bg-slate-950/60 px-2 py-1 rounded border border-slate-800/80" title="Prompt In: ${tok.input.toLocaleString()} | Output: ${tok.output.toLocaleString()} | Cache Read: ${tok.cache.toLocaleString()} | Total: ${tok.total.toLocaleString()}">
            <span class="text-cyan-400">📥 ${formatTokens(tok.input)}</span>
            <span class="text-slate-600">/</span>
            <span class="text-purple-400">📤 ${formatTokens(tok.output)}</span>
            <span class="text-slate-600">/</span>
            <span class="text-emerald-400">⚡ ${formatTokens(tok.cache)}</span>
          </div>
        `;

        // Cost breakdown
        const cost = t.cost || { usd: 0.0, vnd: 0, saved_usd: 0.0, saved_vnd: 0 };
        const costBadge = `
          <div class="font-mono text-[10px] bg-indigo-950/30 px-2 py-1 rounded border border-indigo-900/40" title="Actual Spend: ${formatMoneyUSD(cost.usd)} (~${formatMoneyVND(cost.vnd)}) | Saved: ${formatMoneyUSD(cost.saved_usd)}">
            <div class="text-indigo-300 font-bold">${formatMoneyUSD(cost.usd)}</div>
            <div class="text-[9px] text-slate-500">~${formatMoneyVND(cost.vnd)}</div>
          </div>
        `;

        // Action button
        let killBtn = '';
        if (t.status === 'running') {
          killBtn = `
            <button onclick="killTask('${t.task_id}')" class="px-2 py-1 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 transition text-[11px] font-bold flex items-center gap-1 shadow-sm" title="Dừng khẩn cấp Agent">
              <svg class="w-3 h-3 text-rose-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clip-rule="evenodd" /></svg>
              <span>Kill</span>
            </button>
          `;
        }
        const actionBtn = `
          <div class="flex items-center justify-center space-x-1.5">
            <button onclick="openAgentLiveModal('${t.task_id}')" class="px-2.5 py-1 rounded-lg bg-indigo-500/15 hover:bg-indigo-500/25 text-indigo-300 border border-indigo-500/30 transition text-[11px] font-semibold flex items-center gap-1 shadow-sm" title="Xem trực tiếp logs, suy nghĩ và công cụ của Agent">
              <span>👁️ Live Logs</span>
            </button>
            ${killBtn}
          </div>
        `;

        return `
          <tr class="hover:bg-slate-800/30 transition">
            <td class="py-3 px-4 font-mono font-bold text-white">${t.task_id}</td>
            <td class="py-3 px-4">${getAgentBadge(t.agent_type)}</td>
            <td class="py-3 px-4">${getModelBadge(t.model)}</td>
            <td class="py-3 px-4">${getComplexityBadge(t.complexity)}</td>
            <td class="py-3 px-4">${groupBadge}</td>
            <td class="py-3 px-4">${depsBadge}</td>
            <td class="py-3 px-4">${tokenBadge}</td>
            <td class="py-3 px-4">${costBadge}</td>
            <td class="py-3 px-4 text-slate-300 max-w-xs truncate" title="${t.scope || ''}">${t.scope || '-'}</td>
            <td class="py-3 px-4">${getStatusBadge(t.status)}</td>
            <td class="py-3 px-4">
              <div class="flex items-center space-x-2">
                <div class="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                  <div class="${barColor} h-2 rounded-full transition-all duration-300" style="width: ${pct}%"></div>
                </div>
                <span class="font-mono text-[10px] text-slate-400 w-8 text-right">${pct}%</span>
              </div>
            </td>
            <td class="py-3 px-4 text-center">${actionBtn}</td>
            <td class="py-3 px-4 text-right text-slate-500 font-mono">${formatTime(t.updated_at)}</td>
          </tr>
        `;
      }).join('');
    }

    function renderHistoryTable() {
      const tbody = document.getElementById('history-tbody');
      if (!tbody) return;
      const search = (document.getElementById('hist-filter-search')?.value || '').toLowerCase();
      const statusFilter = document.getElementById('hist-filter-status')?.value || 'all';
      const modelFilter = document.getElementById('hist-filter-model')?.value || 'all';

      let tasks = Object.values(state.tasks).sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''));

      tasks = tasks.filter(t => {
        if (statusFilter !== 'all' && t.status !== statusFilter) return false;
        if (modelFilter !== 'all') {
          const m = (t.model || '').toLowerCase();
          if (modelFilter === 'neon' && !m.includes('neon') && !m.includes('neco')) return false;
          if (modelFilter === 'carbon' && !m.includes('carbon') && m !== 'gemini-pro-orchestrator') return false;
          if (modelFilter === 'hydrogen' && !m.includes('hydrogen')) return false;
          if (modelFilter === 'argon' && !m.includes('argon') && !(m.includes('pro') && !m.includes('neon') && m !== 'gemini-pro-orchestrator')) return false;
          if (modelFilter === 'flash' && !m.includes('flash')) return false;
        }
        if (search) {
          const matchId = (t.task_id || '').toLowerCase().includes(search);
          const matchAgent = (t.agent_type || '').toLowerCase().includes(search);
          const matchScope = (t.scope || '').toLowerCase().includes(search);
          if (!matchId && !matchAgent && !matchScope) return false;
        }
        return true;
      });

      if (tasks.length === 0) {
        tbody.innerHTML = '<tr><td colspan="13" class="py-8 text-center text-slate-500">No matching task history records found.</td></tr>';
        return;
      }

      tbody.innerHTML = tasks.map(t => {
        const tok = t.tokens || { input: 0, output: 0, cache: 0, total: 0 };
        const cost = t.cost || { usd: 0.0, vnd: 0, saved_usd: 0.0, saved_vnd: 0 };
        const hitRate = (tok.input + tok.cache) > 0 ? ((tok.cache / (tok.input + tok.cache)) * 100).toFixed(1) : '0.0';

        let killBtn = '';
        if (t.status === 'running') {
          killBtn = `
            <button onclick="killTask('${t.task_id}')" class="px-2 py-1 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 font-bold text-[10px] transition">
              Kill
            </button>
          `;
        }
        const actionBtn = `
          <div class="flex items-center justify-center space-x-1.5">
            <button onclick="openAgentLiveModal('${t.task_id}')" class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 font-semibold text-[10px] transition flex items-center gap-1" title="Xem chi tiết các bước Agent đã thực hiện">
              <span>👁️ Logs</span>
            </button>
            ${killBtn}
          </div>
        `;

        return `
          <tr class="hover:bg-slate-800/30 transition">
            <td class="py-3 px-4 font-mono font-bold text-white">${t.task_id}</td>
            <td class="py-3 px-4">${getAgentBadge(t.agent_type)}</td>
            <td class="py-3 px-4">${getModelBadge(t.model)}</td>
            <td class="py-3 px-4">${getStatusBadge(t.status)}</td>
            <td class="py-3 px-4 font-mono text-cyan-400">${tok.input.toLocaleString()}</td>
            <td class="py-3 px-4 font-mono text-purple-400">${tok.output.toLocaleString()}</td>
            <td class="py-3 px-4 font-mono text-emerald-400">${tok.cache.toLocaleString()}</td>
            <td class="py-3 px-4 font-mono font-bold text-slate-200">${tok.total.toLocaleString()}</td>
            <td class="py-3 px-4 font-mono text-emerald-300 font-semibold">${hitRate}%</td>
            <td class="py-3 px-4 font-mono">
              <span class="text-indigo-300 font-bold">${formatMoneyUSD(cost.usd)}</span>
              <span class="text-[10px] text-slate-500 block">~${formatMoneyVND(cost.vnd)}</span>
            </td>
            <td class="py-3 px-4 font-mono">
              <span class="text-emerald-400 font-semibold">+${formatMoneyUSD(cost.saved_usd)}</span>
              <span class="text-[10px] text-emerald-500/80 block">~${formatMoneyVND(cost.saved_vnd)}</span>
            </td>
            <td class="py-3 px-4 text-center">${actionBtn}</td>
            <td class="py-3 px-4 text-right text-slate-500 font-mono">${formatTime(t.updated_at || t.created_at)}</td>
          </tr>
        `;
      }).join('');
    }

    function exportHistoryCSV() {
      const tasks = Object.values(state.tasks).sort((a, b) => (a.created_at || '').localeCompare(b.created_at || ''));
      if (tasks.length === 0) {
        alert('No tasks to export.');
        return;
      }

      const headers = [
        "task_id", "agent_type", "model", "complexity", "status", "progress",
        "input_tokens", "output_tokens", "cache_tokens", "total_tokens", "cache_hit_rate_pct",
        "cost_usd", "cost_vnd", "saved_usd", "saved_vnd",
        "scope", "created_at", "updated_at"
      ];

      const rows = tasks.map(t => {
        const tok = t.tokens || { input: 0, output: 0, cache: 0, total: 0 };
        const cost = t.cost || { usd: 0.0, vnd: 0, saved_usd: 0.0, saved_vnd: 0 };
        const hitRate = (tok.input + tok.cache) > 0 ? ((tok.cache / (tok.input + tok.cache)) * 100).toFixed(1) : '0.0';

        return [
          t.task_id,
          t.agent_type,
          t.model,
          t.complexity,
          t.status,
          t.progress,
          tok.input,
          tok.output,
          tok.cache,
          tok.total,
          hitRate,
          cost.usd,
          cost.vnd,
          cost.saved_usd,
          cost.saved_vnd,
          `"${(t.scope || '').replace(/"/g, '""')}"`,
          t.created_at,
          t.updated_at
        ].join(",");
      });

      const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows].join(String.fromCharCode(10));
      const encodedUri = encodeURI(csvContent);
      const link = document.createElement("a");
      const dateStr = new Date().toISOString().slice(0, 10);
      link.setAttribute("href", encodedUri);
      link.setAttribute("download", `orchestrator_token_cost_audit_${dateStr}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }

    function appendLogElement(log) {
      const containers = [
        document.getElementById('logs-container'),
        document.getElementById('live-logs-container')
      ];

      const levelColors = {
        'info': 'text-cyan-400',
        'warn': 'text-amber-400',
        'error': 'text-rose-400 font-bold',
        'thought': 'text-purple-400 italic',
      };
      const color = levelColors[log.level] || 'text-slate-300';
      const timeStr = formatTime(log.timestamp);

      containers.forEach(container => {
        if (!container) return;
        while (container.children.length > 2000) {
          container.removeChild(container.firstChild);
        }
        const el = document.createElement('div');
        el.className = `log-item font-mono py-0.5 border-b border-slate-900/40 hover:bg-slate-900/60 flex items-start space-x-2`;
        el.dataset.level = log.level || 'info';
        el.innerHTML = `
          <span class="text-slate-600 select-none">${timeStr}</span>
          <span class="px-1.5 rounded text-[10px] font-bold uppercase ${color} bg-slate-900 border border-slate-800">${log.level}</span>
          <span class="text-indigo-400 font-semibold">[${log.task_id || 'SYS'}]</span>
          <span class="text-slate-400 text-[10px]">(${log.agent_type})</span>
          <span class="text-slate-200 flex-1 whitespace-pre-wrap break-all">${escapeHtml(log.message)}</span>
        `;
        container.appendChild(el);

        const autoScroll = document.getElementById('autoscroll-toggle');
        if (!autoScroll || autoScroll.checked) {
          container.scrollTop = container.scrollHeight;
        }
      });
    }

    function filterLogs() {
      const selected = document.getElementById('log-filter-level').value;
      const items = document.querySelectorAll('.log-item');
      items.forEach(it => {
        if (selected === 'all' || it.dataset.level === selected) {
          it.style.display = 'flex';
        } else {
          it.style.display = 'none';
        }
      });
    }

    function clearLogConsole() {
      const c1 = document.getElementById('logs-container');
      const c2 = document.getElementById('live-logs-container');
      if (c1) c1.innerHTML = '';
      if (c2) c2.innerHTML = '';
      state.logs = [];
    }

    function escapeHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    function resetState() {
      if (!confirm('Are you sure you want to reset all tasks and telemetry state?')) return;
      fetch('/api/reset', { method: 'POST' })
        .then(r => r.json())
        .then(() => {
          state.tasks = {};
          state.logs = [];
          renderTasksTable();
          renderHistoryTable();
          clearLogConsole();
          renderMetrics({ total: 0, pending: 0, running: 0, completed: 0, blocked: 0, cancelled: 0, active_agents: 0 });
          updatePipelineStages();
        });
    }

    function connectSSE() {
      const dot = document.getElementById('sse-dot');
      const status = document.getElementById('sse-status');
      
      const evtSource = new EventSource('/events');

      evtSource.onopen = () => {
        dot.className = "h-2 w-2 rounded-full bg-emerald-400";
        status.textContent = "Live Telemetry";
      };

      evtSource.onerror = () => {
        dot.className = "h-2 w-2 rounded-full bg-rose-500 pulse-slow";
        status.textContent = "Reconnecting...";
      };

      evtSource.addEventListener('initial_state', (e) => {
        const data = JSON.parse(e.data);
        state.tasks = {};
        (data.tasks || []).forEach(t => { state.tasks[t.task_id] = t; });
        state.metrics = data.metrics || state.metrics;
        renderMetrics(state.metrics);
        renderTasksTable();
        renderHistoryTable();
        updatePipelineStages();
        
        clearLogConsole();
        (data.logs || []).forEach(l => appendLogElement(l));
      });

      evtSource.addEventListener('task_update', (e) => {
        const data = JSON.parse(e.data);
        if (data.task) {
          state.tasks[data.task.task_id] = data.task;
        }
        if (data.metrics) {
          state.metrics = data.metrics;
          renderMetrics(data.metrics);
        }
        renderTasksTable();
        renderHistoryTable();
        updatePipelineStages();
      });

      evtSource.addEventListener('state_sync', (e) => {
        const data = JSON.parse(e.data);
        if (data.metrics) {
          state.metrics = data.metrics;
          renderMetrics(data.metrics);
        }
        // Refresh full state
        fetch('/api/state')
          .then(r => r.json())
          .then(full => {
            if (full.tasks) {
              state.tasks = {};
              full.tasks.forEach(t => { state.tasks[t.task_id] = t; });
              renderTasksTable();
              renderHistoryTable();
            }
          });
      });

      evtSource.addEventListener('log_event', (e) => {
        const log = JSON.parse(e.data);
        state.logs.push(log);
        appendLogElement(log);
      });

      evtSource.addEventListener('reset_event', (e) => {
        state.tasks = {};
        state.logs = [];
        renderTasksTable();
        renderHistoryTable();
        clearLogConsole();
        renderMetrics({ total: 0, pending: 0, running: 0, completed: 0, blocked: 0, cancelled: 0, active_agents: 0 });
        updatePipelineStages();
      });

      // Robust fallback state polling: ensures tasks, progress and metrics stay fresh
      // even if extreme log storms or proxy buffers momentarily delay SSE delivery.
      setInterval(() => {
        fetch('/api/state')
          .then(r => r.json())
          .then(full => {
            if (full && full.tasks) {
              state.tasks = {};
              full.tasks.forEach(t => { state.tasks[t.task_id] = t; });
              if (full.metrics) {
                state.metrics = full.metrics;
                renderMetrics(state.metrics);
              }
              renderTasksTable();
              renderHistoryTable();
              updatePipelineStages();
            }
          })
          .catch(() => {});
      }, 4000);
    }

    // ---------------------------------------------------------------------------
    // Agent Live Activity & Inspector Modal Logic
    // ---------------------------------------------------------------------------
    let activeModalTaskId = null;
    let modalPollTimer = null;
    let modalRawActivities = [];
    let modalActiveFilter = 'all';

    function openAgentLiveModal(taskId) {
      activeModalTaskId = taskId;
      modalActiveFilter = 'all';
      const modal = document.getElementById('agent-live-modal');
      if (!modal) return;
      modal.classList.remove('hidden');
      
      const t = state.tasks[taskId] || { task_id: taskId };
      const elTaskId = document.getElementById('modal-task-id');
      if (elTaskId) elTaskId.textContent = t.task_id || taskId;
      
      const elAgentBadge = document.getElementById('modal-agent-badge');
      if (elAgentBadge) elAgentBadge.innerHTML = getAgentBadge(t.agent_type || 'builder');
      
      const elModelBadge = document.getElementById('modal-model-badge');
      if (elModelBadge) elModelBadge.innerHTML = getModelBadge(t.model || 'neon');
      
      const elStatusBadge = document.getElementById('modal-status-badge');
      if (elStatusBadge) elStatusBadge.innerHTML = getStatusBadge(t.status || 'running');
      
      const elScope = document.getElementById('modal-scope');
      if (elScope) elScope.textContent = t.scope || 'Chi tiết tác vụ không có mô tả bổ sung.';
      
      const tok = t.tokens || { input: 0, output: 0, cache: 0 };
      const cost = t.cost || { usd: 0.0, vnd: 0 };
      
      const elIn = document.getElementById('modal-tok-in');
      if (elIn) elIn.textContent = `📥 ${formatTokens(tok.input)}`;
      const elOut = document.getElementById('modal-tok-out');
      if (elOut) elOut.textContent = `📤 ${formatTokens(tok.output)}`;
      const elCache = document.getElementById('modal-tok-cache');
      if (elCache) elCache.textContent = `⚡ ${formatTokens(tok.cache)}`;
      const elCost = document.getElementById('modal-cost-usd');
      if (elCost) elCost.textContent = `${formatMoneyUSD(cost.usd)} (~${formatMoneyVND(cost.vnd)})`;
      const elConv = document.getElementById('modal-conv-id');
      if (elConv) elConv.textContent = t.conv_id ? `Conv: ${t.conv_id.substring(0, 8)}...` : 'Conv: Direct';

      refreshAgentLiveModal(true);

      if (modalPollTimer) clearInterval(modalPollTimer);
      modalPollTimer = setInterval(() => {
        const toggle = document.getElementById('modal-autorefresh-toggle');
        if (toggle && toggle.checked) {
          refreshAgentLiveModal(false);
        }
      }, 2500);
    }

    function closeAgentLiveModal() {
      const modal = document.getElementById('agent-live-modal');
      if (modal) modal.classList.add('hidden');
      if (modalPollTimer) {
        clearInterval(modalPollTimer);
        modalPollTimer = null;
      }
      activeModalTaskId = null;
    }

    function toggleModalAutoRefresh() {
      const toggle = document.getElementById('modal-autorefresh-toggle');
      if (!toggle.checked && modalPollTimer) {
        clearInterval(modalPollTimer);
        modalPollTimer = null;
      } else if (toggle.checked && !modalPollTimer && activeModalTaskId) {
        modalPollTimer = setInterval(() => {
          refreshAgentLiveModal(false);
        }, 2500);
      }
    }

    function filterModalActivities(type) {
      modalActiveFilter = type;
      ['all', 'tool', 'thought', 'error'].forEach(t => {
        const btn = document.getElementById(`modal-filter-${t}`);
        if (!btn) return;
        if (t === type) {
          btn.className = 'px-3 py-1 rounded-lg font-medium transition bg-indigo-600 text-white shadow-sm';
        } else {
          btn.className = 'px-3 py-1 rounded-lg font-medium transition text-slate-400 hover:text-slate-200 hover:bg-slate-800';
        }
      });
      renderModalActivityList();
    }

    function refreshAgentLiveModal(isInitial = false) {
      if (!activeModalTaskId) return;
      fetch(`/api/tasks/transcript?task_id=${encodeURIComponent(activeModalTaskId)}`)
        .then(r => r.json())
        .then(data => {
          if (data.status === 'error') {
            const elAction = document.getElementById('modal-latest-action');
            if (elAction) elAction.textContent = data.error || 'Lỗi nạp nhật ký';
            return;
          }

          const elAction = document.getElementById('modal-latest-action');
          if (elAction) elAction.textContent = data.latest_action || 'Không có hành động gần nhất';
          
          const elStatus = document.getElementById('modal-status-badge');
          if (elStatus && data.task_status) {
            elStatus.innerHTML = getStatusBadge(data.task_status);
          }
          if (data.tokens) {
            const elIn = document.getElementById('modal-tok-in');
            if (elIn) elIn.textContent = `📥 ${formatTokens(data.tokens.input)}`;
            const elOut = document.getElementById('modal-tok-out');
            if (elOut) elOut.textContent = `📤 ${formatTokens(data.tokens.output)}`;
            const elCache = document.getElementById('modal-tok-cache');
            if (elCache) elCache.textContent = `⚡ ${formatTokens(data.tokens.cache)}`;
          }
          if (data.cost) {
            const elCost = document.getElementById('modal-cost-usd');
            if (elCost) elCost.textContent = `${formatMoneyUSD(data.cost.usd)} (~${formatMoneyVND(data.cost.vnd)})`;
          }

          modalRawActivities = data.activities || [];
          
          const total = modalRawActivities.length;
          const tools = modalRawActivities.filter(a => a.type === 'tool').length;
          const thoughts = modalRawActivities.filter(a => a.type === 'thought').length;
          const errors = modalRawActivities.filter(a => a.type === 'error').length;

          const elAll = document.getElementById('count-all');
          if (elAll) elAll.textContent = total;
          const elTool = document.getElementById('count-tool');
          if (elTool) elTool.textContent = tools;
          const elThought = document.getElementById('count-thought');
          if (elThought) elThought.textContent = thoughts;
          const elErr = document.getElementById('count-error');
          if (elErr) elErr.textContent = errors;
          
          const elFoot = document.getElementById('modal-footer-stats');
          if (elFoot) elFoot.textContent = `${total} hoạt động được ghi nhận (${tools} lệnh/công cụ, ${thoughts} bước suy nghĩ)`;

          renderModalActivityList(isInitial);
        })
        .catch(err => {
          console.error('Failed to refresh modal transcript:', err);
        });
    }

    function renderModalActivityList(forceScrollBottom = false) {
      const container = document.getElementById('modal-activities-container');
      if (!container) return;

      let filtered = modalRawActivities;
      if (modalActiveFilter !== 'all') {
        filtered = modalRawActivities.filter(a => a.type === modalActiveFilter);
      }

      if (filtered.length === 0) {
        container.innerHTML = `
          <div class="py-12 text-center text-slate-500">
            <div class="text-sm">Chưa có hoạt động phù hợp bộ lọc</div>
            <div class="text-xs text-slate-600 mt-1">Khi subagent thực thi lệnh hoặc phân tích, dữ liệu sẽ hiển thị tại đây theo thời gian thực.</div>
          </div>
        `;
        return;
      }

      const autoscroll = document.getElementById('modal-autoscroll-toggle')?.checked;
      const isAtBottom = (container.scrollHeight - container.scrollTop <= container.clientHeight + 60);

      container.innerHTML = filtered.map(act => {
        let typeBadge = '';
        let borderClass = 'border-slate-800 bg-slate-900/60';
        let icon = '⚡';

        if (act.type === 'tool') {
          typeBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">Công cụ</span>';
          borderClass = 'border-cyan-900/30 bg-slate-900/80 hover:border-cyan-700/50';
          icon = '🛠️';
        } else if (act.type === 'thought') {
          typeBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-mono bg-purple-500/10 text-purple-300 border border-purple-500/20">Suy nghĩ</span>';
          borderClass = 'border-purple-900/30 bg-slate-900/80 hover:border-purple-700/50';
          icon = '💭';
        } else if (act.type === 'error') {
          typeBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-mono bg-rose-500/10 text-rose-300 border border-rose-500/20">Lỗi</span>';
          borderClass = 'border-rose-900/40 bg-rose-950/10 hover:border-rose-700/50';
          icon = '❌';
        }

        return `
          <div class="p-3 rounded-xl border ${borderClass} transition flex flex-col space-y-1.5 shadow-sm">
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-2">
                <span>${icon}</span>
                <span class="font-bold text-slate-200">${escapeHtml(act.title || 'Hoạt động')}</span>
                ${typeBadge}
                <span class="font-mono text-[10px] text-slate-500">Step #${act.step}</span>
              </div>
              <span class="font-mono text-[10px] text-slate-500">${formatTime(act.time)}</span>
            </div>
            <div class="font-mono text-[11px] text-slate-300 bg-slate-950/70 p-2 rounded-lg border border-slate-800/80 whitespace-pre-wrap break-all select-all">${escapeHtml(act.detail || '')}</div>
          </div>
        `;
      }).join('');

      if (forceScrollBottom || (autoscroll && isAtBottom)) {
        setTimeout(() => {
          container.scrollTop = container.scrollHeight;
        }, 20);
      }
    }

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeAgentLiveModal();
    });

    window.addEventListener('DOMContentLoaded', () => {
      initPipeline();
      connectSSE();
    });
  </script>

  <!-- Agent Live Activity & Inspector Modal -->
  <div id="agent-live-modal" class="fixed inset-0 z-50 hidden flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
    <div class="relative w-full max-w-4xl max-h-[90vh] bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
      
      <!-- Modal Header -->
      <div class="px-6 py-4 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <div class="h-3 w-3 rounded-full bg-emerald-500 animate-pulse"></div>
          <div>
            <div class="flex items-center space-x-2">
              <span id="modal-task-id" class="font-mono font-bold text-base text-white">TASK-...</span>
              <span id="modal-agent-badge"></span>
              <span id="modal-model-badge"></span>
              <span id="modal-status-badge"></span>
            </div>
            <div id="modal-scope" class="text-xs text-slate-400 mt-0.5 truncate max-w-xl">-</div>
          </div>
        </div>
        <div class="flex items-center space-x-2">
          <button onclick="refreshAgentLiveModal()" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium flex items-center space-x-1.5 transition">
            <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            <span>Làm mới</span>
          </button>
          <button onclick="closeAgentLiveModal()" class="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
      </div>

      <!-- Live Telemetry & Action Bar -->
      <div class="px-6 py-3 bg-slate-900/90 border-b border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div class="flex items-center space-x-3 font-mono">
          <div class="bg-slate-950 px-2.5 py-1 rounded border border-slate-800 text-slate-300 flex items-center space-x-2">
            <span class="text-cyan-400" id="modal-tok-in">📥 0</span>
            <span class="text-slate-600">/</span>
            <span class="text-purple-400" id="modal-tok-out">📤 0</span>
            <span class="text-slate-600">/</span>
            <span class="text-emerald-400" id="modal-tok-cache">⚡ 0</span>
          </div>
          <div class="bg-indigo-950/40 px-2.5 py-1 rounded border border-indigo-900/50 text-indigo-300 font-bold" id="modal-cost-usd">$0.00</div>
          <div class="text-[11px] text-slate-500 font-sans" id="modal-conv-id">Conv: -</div>
        </div>

        <div class="flex items-center space-x-4">
          <label class="flex items-center space-x-1.5 cursor-pointer text-slate-300 text-xs select-none">
            <input type="checkbox" id="modal-autorefresh-toggle" checked onchange="toggleModalAutoRefresh()" class="rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 bg-slate-800 w-3.5 h-3.5">
            <span>Tự động cập nhật (2.5s)</span>
          </label>
          <label class="flex items-center space-x-1.5 cursor-pointer text-slate-300 text-xs select-none">
            <input type="checkbox" id="modal-autoscroll-toggle" checked class="rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 bg-slate-800 w-3.5 h-3.5">
            <span>Cuộn theo dòng mới</span>
          </label>
        </div>
      </div>

      <!-- Current Ongoing Action Highlight Box -->
      <div class="px-6 py-2.5 bg-gradient-to-r from-indigo-950/30 to-purple-950/20 border-b border-indigo-900/30 flex items-center space-x-3">
        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 uppercase tracking-wider whitespace-nowrap">Đang làm:</span>
        <div id="modal-latest-action" class="font-mono text-xs text-indigo-200 truncate font-medium">Đang tải trạng thái hoạt động...</div>
      </div>

      <!-- Filter tabs -->
      <div class="px-6 pt-3 pb-2 bg-slate-900 flex items-center justify-between border-b border-slate-800/60">
        <div class="flex items-center space-x-2 text-xs">
          <button id="modal-filter-all" onclick="filterModalActivities('all')" class="px-3 py-1 rounded-lg font-medium transition bg-indigo-600 text-white shadow-sm">Tất cả (<span id="count-all">0</span>)</button>
          <button id="modal-filter-tool" onclick="filterModalActivities('tool')" class="px-3 py-1 rounded-lg font-medium transition text-slate-400 hover:text-slate-200 hover:bg-slate-800">🛠️ Công cụ (<span id="count-tool">0</span>)</button>
          <button id="modal-filter-thought" onclick="filterModalActivities('thought')" class="px-3 py-1 rounded-lg font-medium transition text-slate-400 hover:text-slate-200 hover:bg-slate-800">💭 Suy nghĩ (<span id="count-thought">0</span>)</button>
          <button id="modal-filter-error" onclick="filterModalActivities('error')" class="px-3 py-1 rounded-lg font-medium transition text-slate-400 hover:text-slate-200 hover:bg-slate-800">❌ Lỗi (<span id="count-error">0</span>)</button>
        </div>
        <div class="text-[11px] text-slate-500 font-mono">Real-time Subagent Execution Trace</div>
      </div>

      <!-- Scrollable Activities / Logs Container -->
      <div id="modal-activities-container" class="flex-1 overflow-y-auto p-6 space-y-3 bg-slate-950/40 font-sans text-xs min-h-[320px] max-h-[500px]">
        <div class="text-center py-12 text-slate-500">Đang nạp nhật ký từ subagent transcript...</div>
      </div>

      <!-- Modal Footer -->
      <div class="px-6 py-3 border-t border-slate-800 bg-slate-950/80 flex items-center justify-between text-xs text-slate-400">
        <div id="modal-footer-stats">0 hoạt động được ghi nhận</div>
        <button onclick="closeAgentLiveModal()" class="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium transition">Đóng</button>
      </div>

    </div>
  </div>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Dashboard Loader & Dynamic Resolver
# ---------------------------------------------------------------------------

def get_dashboard_html() -> str:
    """Return upgraded dashboard HTML from dashboard.py, or fallback."""
    try:
        from dashboard import DASHBOARD_HTML as D_HTML
        if D_HTML:
            return D_HTML
    except ImportError:
        pass
    try:
        from packages.orchestrator.dashboard import DASHBOARD_HTML as D_HTML
        if D_HTML:
            return D_HTML
    except ImportError:
        pass
    return _FALLBACK_DASHBOARD_HTML

DASHBOARD_HTML = get_dashboard_html()

# ---------------------------------------------------------------------------
# HTTP Request Handler
# ---------------------------------------------------------------------------

class OrchestratorHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _set_cors_headers(self, request_path: str | None = None):
        raw_path = request_path if request_path is not None else urlparse(getattr(self, "path", "")).path
        if _is_desktop_path(raw_path):
            origin = (self.headers.get("Origin") or "").strip()
            if origin and _is_loopback_origin(origin):
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            return
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _check_desktop_access(self) -> bool:
        client_ip = (self.client_address[0] if self.client_address else "") or ""
        expected_token = os.environ.get("ORCHESTRATOR_DESKTOP_TOKEN", "").strip()
        auth_header = (self.headers.get("Authorization") or "").strip()
        token_ok = False
        if expected_token and auth_header.lower().startswith("bearer "):
            supplied = auth_header[7:].strip()
            token_ok = hmac.compare_digest(supplied, expected_token)

        if client_ip not in LOOPBACK_IPS and not token_ok:
            self.close_connection = True
            self._send_json(
                HTTPStatus.FORBIDDEN,
                {"error": "Desktop endpoints require loopback client IP or valid ORCHESTRATOR_DESKTOP_TOKEN"},
            )
            return False

        origin = (self.headers.get("Origin") or "").strip()
        if origin and not _is_loopback_origin(origin) and not token_ok:
            self.close_connection = True
            self._send_json(
                HTTPStatus.FORBIDDEN,
                {"error": "Cross-origin requests to desktop endpoints are restricted to loopback origins"},
            )
            return False
        return True

    def _require_json_content_type(self) -> bool:
        raw_ct = (self.headers.get("Content-Type") or "").strip()
        media_type = raw_ct.split(";", 1)[0].strip().lower()
        if media_type != "application/json":
            self.close_connection = True
            self._send_json(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                {"error": "Content-Type header must be application/json"},
            )
            return False
        return True

    def _read_json_body(self, max_bytes: int = MAX_JSON_BODY_BYTES) -> dict | None:
        raw_len = self.headers.get("Content-Length")
        if raw_len is None or raw_len.strip() == "":
            content_length = 0
        else:
            try:
                content_length = int(raw_len.strip())
            except ValueError:
                self.close_connection = True
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid Content-Length header"})
                return None

        if content_length < 0:
            self.close_connection = True
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid negative Content-Length"})
            return None
        if content_length > max_bytes:
            self.close_connection = True
            self._send_json(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                {"error": f"Request body exceeds maximum allowed size ({max_bytes} bytes)"},
            )
            return None

        post_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            decoded = post_body.decode("utf-8") if post_body else "{}"
            payload = json.loads(decoded) if decoded else {}
        except UnicodeDecodeError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Request body must be valid UTF-8"})
            return None
        except json.JSONDecodeError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON body"})
            return None

        if not isinstance(payload, dict):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "JSON object body is required"})
            return None
        return payload

    def _send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self._set_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            body = get_dashboard_html().encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self._set_cors_headers()
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/state":
            data = GLOBAL_STORE.get_state()
            self._send_json(HTTPStatus.OK, data)
            return

        if path == "/api/models":
            data = {
                "status": "ok",
                "default_model": "gemini-4-neon",
                "models": MODEL_REGISTRY,
                "external_workers": EXTERNAL_WORKERS,
                "circuit_breaker_stages": [
                    {
                        "stage": 1,
                        "retry_count": 1,
                        "model": "gemini-4-hydrogen",
                        "reasoning_effort": "xhigh",
                        "status": "retrying",
                    },
                    {
                        "stage": 2,
                        "retry_count": 2,
                        "model": "gemini-4-neon",
                        "reasoning_effort": "high",
                        "status": "tripped",
                        "escalated_to": "gemini-4-neon",
                    },
                    {
                        "stage": 3,
                        "retry_count": 3,
                        "model": "gemini-4-carbon",
                        "reasoning_effort": "high",
                        "status": "tripped",
                        "escalated_to": "gemini-4-carbon",
                    },
                ],
            }
            self._send_json(HTTPStatus.OK, data)
            return

        if path == "/api/desktop/status":
            if not self._check_desktop_access():
                return
            qs = parse_qs(parsed.query)
            driver = (qs.get("driver", ["auto"])[0] or "auto").strip().lower()
            if driver not in SUPPORTED_DRIVERS:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"Invalid driver '{driver}'"})
                return
            target_os = (qs.get("target_os", ["auto"])[0] or "auto").strip().lower()
            if target_os not in ("auto", "darwin", "win32", "linux"):
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"Invalid target_os '{target_os}'"})
                return
            raw_app_path = qs.get("app_path", [None])[0]
            app_path = str(raw_app_path).strip() if raw_app_path is not None and str(raw_app_path).strip() != "" else None
            if app_path is not None and os.environ.get("ORCHESTRATOR_ALLOW_CUSTOM_APP_PATH") != "1":
                self._send_json(
                    HTTPStatus.FORBIDDEN,
                    {"error": "Custom app_path over HTTP is disabled; set ORCHESTRATOR_ALLOW_CUSTOM_APP_PATH=1 to allow validated paths"},
                )
                return
            try:
                data = GLOBAL_STORE.get_desktop_status(driver=driver, target_os=target_os, app_path=app_path)
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            self._send_json(HTTPStatus.OK, data)
            return

        if path in ("/api/desktop/jobs", "/api/desktop/jobs/"):
            if not self._check_desktop_access():
                return
            qs = parse_qs(parsed.query)
            job_id = qs.get("job_id", [None])[0]
            status_filter = qs.get("status", [None])[0]
            limit_raw = qs.get("limit", ["50"])[0]
            try:
                limit = int(limit_raw)
            except (TypeError, ValueError):
                limit = 50
            data = GLOBAL_STORE.get_desktop_jobs_response(job_id=job_id, status=status_filter, limit=limit)
            self._send_json(HTTPStatus.OK, data)
            return

        if path.startswith("/api/desktop/jobs/"):
            if not self._check_desktop_access():
                return
            raw_id = unquote(path[len("/api/desktop/jobs/"):]).strip("/")
            if not raw_id or "/" in raw_id:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not Found"})
                return
            job = GLOBAL_STORE.get_desktop_job(raw_id)
            if not job:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "Desktop job not found"})
                return
            self._send_json(HTTPStatus.OK, {"status": "ok", "job": job})
            return

        if path == "/api/dag/ready":
            state = GLOBAL_STORE.get_state()
            data = evaluate_dag_ready(state["tasks"])
            self._send_json(HTTPStatus.OK, data)
            return

        if path == "/api/analytics/models":
            state = GLOBAL_STORE.get_state()
            desktop_jobs = GLOBAL_STORE.list_desktop_jobs(limit=1000)
            data = compute_model_analytics(state["tasks"], desktop_jobs=desktop_jobs)
            share_metrics = GLOBAL_STORE.get_desktop_share_metrics()
            cached_status = GLOBAL_STORE._get_cached_desktop_status()
            desk_info = cached_status.get("desktop", {}) if isinstance(cached_status, dict) else {}
            desktop_ready = _is_desktop_auto_ready(desk_info)
            desktop_share_summary = {
                "target_share": share_metrics["target_desktop_share"],
                "current_share": share_metrics["current_desktop_share"],
                "eligible_tasks": share_metrics["eligible_tasks"],
                "desktop_tasks": share_metrics["desktop_tasks"],
                "desktop_ready": desktop_ready,
            }
            data["desktop_share"] = desktop_share_summary
            if isinstance(data.get("summary"), dict):
                data["summary"]["desktop_share"] = desktop_share_summary
            self._send_json(HTTPStatus.OK, data)
            return

        if path == "/api/audit/export":
            qs = parse_qs(parsed.query)
            fmt = qs.get("format", ["markdown"])[0].lower()
            state = GLOBAL_STORE.get_state()
            desktop_jobs = GLOBAL_STORE.list_desktop_jobs(limit=1000)
            report = generate_audit_report(
                state["tasks"],
                state["logs"],
                state["metrics"],
                format=fmt,
                desktop_jobs=desktop_jobs,
            )
            self.send_response(HTTPStatus.OK)
            self._set_cors_headers()
            if fmt == "json":
                body = json.dumps(report).encode("utf-8")
                self.send_header("Content-Type", "application/json; charset=utf-8")
            else:
                body = report.encode("utf-8")
                self.send_header("Content-Type", "text/markdown; charset=utf-8")
                self.send_header("Content-Disposition", 'attachment; filename="mission_audit_report.md"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/tasks/transcript":
            qs = parse_qs(parsed.query)
            task_id = qs.get("task_id", [None])[0]
            if not task_id:
                self.send_response(HTTPStatus.BAD_REQUEST)
                self._set_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error": "task_id query parameter is required"}')
                return

            data = GLOBAL_STORE.get_task_transcript(task_id)
            self._send_json(HTTPStatus.OK, data)
            return

        if path == "/events":
            self.send_response(HTTPStatus.OK)
            self._set_cors_headers()
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            q = GLOBAL_STORE.subscribe()
            try:
                initial = GLOBAL_STORE.get_state()
                init_msg = f"event: initial_state\ndata: {json.dumps(initial)}\n\n"
                self.wfile.write(init_msg.encode("utf-8"))
                self.wfile.flush()

                while True:
                    try:
                        msg = q.get(timeout=15)
                        self.wfile.write(msg.encode("utf-8"))
                        self.wfile.flush()
                    except queue.Empty:
                        heartbeat = ": ping\n\n"
                        self.wfile.write(heartbeat.encode("utf-8"))
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                GLOBAL_STORE.unsubscribe(q)
            return

        self.send_response(HTTPStatus.NOT_FOUND)
        self._set_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"error": "Not Found"}')

    @staticmethod
    def _resolve_router_desktop_context(payload: dict, budget_mode: str) -> tuple[bool, bool, float, str]:
        """Resolve desktop_available, desktop_queue_busy, target_share, and detection_source."""
        raw_target_share = payload.get(
            "desktop_target_share",
            payload.get("target_desktop_share", payload.get("target_share")),
        )
        target_share = (
            DEFAULT_DESKTOP_TARGET_SHARE
            if raw_target_share is None
            else clamp_desktop_share(raw_target_share, DEFAULT_DESKTOP_TARGET_SHARE)
        )
        raw_desktop_avail = payload.get("desktop_available")
        raw_queue_busy = payload.get("desktop_queue_busy")

        if raw_desktop_avail is not None:
            desktop_available = GLOBAL_STORE._parse_bool_flag(raw_desktop_avail, "desktop_available", False)
            desktop_queue_busy = (
                GLOBAL_STORE._parse_bool_flag(raw_queue_busy, "desktop_queue_busy", False)
                if raw_queue_busy is not None
                else False
            )
            return desktop_available, desktop_queue_busy, target_share, "explicit"

        if budget_mode == "api_only":
            desktop_queue_busy = (
                GLOBAL_STORE._parse_bool_flag(raw_queue_busy, "desktop_queue_busy", False)
                if raw_queue_busy is not None
                else False
            )
            return False, desktop_queue_busy, target_share, "api_only"

        if not getattr(GLOBAL_STORE, "auto_desktop_routing", True):
            return False, False, target_share, "auto_disabled"

        cached_status = GLOBAL_STORE._get_cached_desktop_status()
        desk_info = cached_status.get("desktop", {}) if isinstance(cached_status, dict) else {}
        desktop_available = _is_desktop_auto_ready(desk_info)
        if raw_queue_busy is not None:
            desktop_queue_busy = GLOBAL_STORE._parse_bool_flag(raw_queue_busy, "desktop_queue_busy", False)
        else:
            desktop_queue_busy = bool(
                desk_info.get("lock_busy", False)
                or int(desk_info.get("queue_depth", 0) or 0) > 0
            )
        return desktop_available, desktop_queue_busy, target_share, "auto_cached"

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if _is_desktop_path(path):
            if not self._check_desktop_access():
                return
            if not self._require_json_content_type():
                return

        payload = self._read_json_body()
        if payload is None:
            return

        if path == "/api/desktop/dispatch":
            raw_app_path = payload.get("app_path")
            if raw_app_path is not None and (not isinstance(raw_app_path, str) or raw_app_path.strip() != ""):
                if os.environ.get("ORCHESTRATOR_ALLOW_CUSTOM_APP_PATH") != "1":
                    self._send_json(
                        HTTPStatus.FORBIDDEN,
                        {"error": "Custom app_path over HTTP is disabled; set ORCHESTRATOR_ALLOW_CUSTOM_APP_PATH=1 to allow validated paths"},
                    )
                    return
            try:
                job, is_async, was_rejected_secrets = GLOBAL_STORE.enqueue_desktop_job(payload)
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return

            if was_rejected_secrets or job.get("status") == "rejected_secrets":
                self._send_json(HTTPStatus.OK, {"status": "rejected_secrets", "job": job})
                return
            if is_async:
                self._send_json(HTTPStatus.ACCEPTED, {"status": "queued", "job": job})
                return
            res_status = "ok" if job.get("status") == "completed" else "error"
            self._send_json(HTTPStatus.OK, {"status": res_status, "job": job})
            return

        if path == "/api/desktop/cancel":
            job_id = payload.get("job_id") if isinstance(payload, dict) else None
            if not job_id or not str(job_id).strip():
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "job_id is required"})
                return
            job = GLOBAL_STORE.cancel_desktop_job(str(job_id).strip())
            if not job:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "Desktop job not found"})
                return
            self._send_json(HTTPStatus.OK, {"status": "ok", "job": job})
            return

        if path.startswith("/api/desktop/jobs/") and path.endswith("/cancel"):
            raw_id = unquote(path[len("/api/desktop/jobs/"):-len("/cancel")]).strip("/")
            if not raw_id or "/" in raw_id:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "job_id is required"})
                return
            job = GLOBAL_STORE.cancel_desktop_job(raw_id)
            if not job:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "Desktop job not found"})
                return
            self._send_json(HTTPStatus.OK, {"status": "ok", "job": job})
            return

        if path == "/api/tasks":
            task_id = payload.get("task_id")
            if not task_id:
                self.send_response(HTTPStatus.BAD_REQUEST)
                self._set_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error": "task_id is required"}')
                return

            agent_type = payload.get("agent_type", "orchestrator")
            status = payload.get("status", "pending")
            progress = payload.get("progress")
            scope = payload.get("scope")
            notes = payload.get("notes")
            conv_id = payload.get("conv_id")
            model = payload.get("model")
            complexity = payload.get("complexity") or payload.get("tier")
            depends_on = payload.get("depends_on")
            parallel_group = payload.get("parallel_group") or payload.get("group")
            reasoning_effort = payload.get("reasoning_effort") or payload.get("effort")
            input_tokens = payload.get("input_tokens")
            output_tokens = payload.get("output_tokens")
            cache_tokens = payload.get("cache_tokens") or payload.get("cache_read_tokens")

            task = GLOBAL_STORE.upsert_task(
                task_id=task_id,
                agent_type=agent_type,
                status=status,
                progress=progress,
                scope=scope,
                notes=notes,
                conv_id=conv_id,
                model=model,
                complexity=complexity,
                depends_on=depends_on,
                parallel_group=parallel_group,
                reasoning_effort=reasoning_effort,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_tokens=cache_tokens,
            )

            self._send_json(HTTPStatus.OK, {"status": "ok", "task": task})
            return

        if path == "/api/router/recommend":
            agent_type = payload.get("agent_type", "")
            complexity = payload.get("complexity", "medium")
            scope = payload.get("scope", "")
            file_count = int(payload.get("file_count") or payload.get("files") or 0)
            has_security_impact = bool(payload.get("has_security_impact") or payload.get("security_impact") or False)
            budget_mode = str(payload.get("budget_mode") or "balanced").strip().lower()
            if payload.get("api_only"):
                budget_mode = "api_only"
            retry_count = int(payload.get("retry_count") or payload.get("retries") or 0)
            read_only = bool(payload.get("read_only", False))
            prefer_desktop = bool(payload.get("prefer_desktop", False))

            try:
                desktop_available, desktop_queue_busy, target_share, detection_source = (
                    self._resolve_router_desktop_context(payload, budget_mode)
                )
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return

            share_metrics = GLOBAL_STORE.get_desktop_share_metrics(target_share=target_share)
            raw_current_share = payload.get("current_desktop_share")
            if raw_current_share is not None:
                try:
                    current_share: float | None = max(0.0, min(1.0, float(raw_current_share)))
                except (TypeError, ValueError):
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "current_desktop_share must be a float in [0.0, 1.0]"})
                    return
            else:
                current_share = (
                    share_metrics["current_desktop_share"]
                    if share_metrics["eligible_tasks"] > 0
                    else None
                )

            rec = recommend_model(
                agent_type=agent_type,
                complexity=complexity,
                scope=scope,
                file_count=file_count,
                has_security_impact=has_security_impact,
                budget_mode=budget_mode,
                retry_count=retry_count,
                desktop_available=desktop_available,
                read_only=read_only,
                prefer_desktop=prefer_desktop,
                desktop_queue_busy=desktop_queue_busy,
                current_desktop_share=current_share,
                desktop_target_share=target_share,
            )
            rec["desktop_routing_context"] = {
                "desktop_available": desktop_available,
                "desktop_queue_busy": desktop_queue_busy,
                "current_desktop_share": current_share,
                "target_desktop_share": target_share,
                "eligible_tasks": share_metrics["eligible_tasks"],
                "desktop_tasks": share_metrics["desktop_tasks"],
                "detection_source": detection_source,
            }
            self._send_json(HTTPStatus.OK, rec)
            return

        if path == "/api/router/allocate-dag":
            raw_tasks = payload.get("tasks")
            if raw_tasks is None:
                state = GLOBAL_STORE.get_state()
                dag_tasks = [t for t in state["tasks"] if t.get("status") == "pending"]
            elif isinstance(raw_tasks, list):
                if not all(isinstance(item, dict) for item in raw_tasks):
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Each item in 'tasks' must be a JSON object"})
                    return
                dag_tasks = raw_tasks
            else:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "'tasks' must be a JSON array"})
                return

            budget_mode = str(payload.get("budget_mode") or "balanced").strip().lower()
            if payload.get("api_only"):
                budget_mode = "api_only"

            try:
                apply_changes = GLOBAL_STORE._parse_bool_flag(payload.get("apply"), "apply", False)
                use_store_share = GLOBAL_STORE._parse_bool_flag(payload.get("use_store_share"), "use_store_share", False)
                desktop_available, _, target_share, detection_source = (
                    self._resolve_router_desktop_context(payload, budget_mode)
                )
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return

            raw_existing_share = payload.get("existing_desktop_share")
            if raw_existing_share is not None:
                try:
                    existing_share: float | None = max(0.0, min(1.0, float(raw_existing_share)))
                except (TypeError, ValueError):
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "existing_desktop_share must be a float in [0.0, 1.0]"})
                    return
            elif use_store_share:
                sm = GLOBAL_STORE.get_desktop_share_metrics(target_share=target_share)
                existing_share = sm["current_desktop_share"] if sm["eligible_tasks"] > 0 else None
            else:
                existing_share = None

            allocation_res = allocate_dag_models(
                tasks=dag_tasks,
                desktop_available=desktop_available,
                desktop_target_share=target_share,
                existing_desktop_share=existing_share,
                budget_mode=budget_mode,
            )
            allocation_res["detection_source"] = detection_source
            allocation_res["applied"] = apply_changes
            if apply_changes:
                apply_info = GLOBAL_STORE.apply_dag_allocations(
                    allocations=allocation_res["allocations"],
                    source_tasks=dag_tasks,
                )
                allocation_res["applied_count"] = apply_info["applied_count"]
                allocation_res["applied_task_ids"] = apply_info["applied_task_ids"]
                allocation_res["skipped_task_ids"] = apply_info["skipped_task_ids"]
                allocation_res["desktop_share"] = GLOBAL_STORE.get_desktop_share_metrics(target_share=target_share)

            self._send_json(HTTPStatus.OK, allocation_res)
            return

        if path == "/api/tasks/kill":
            task_id = payload.get("task_id")
            if not task_id:
                self.send_response(HTTPStatus.BAD_REQUEST)
                self._set_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error": "task_id is required"}')
                return

            reason = payload.get("reason", "Cancelled by user via UI")
            task = GLOBAL_STORE.kill_task(task_id, reason)
            if not task:
                self.send_response(HTTPStatus.NOT_FOUND)
                self._set_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error": "Task not found"}')
                return

            res = json.dumps({"status": "ok", "task": task}).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(res)))
            self.end_headers()
            self.wfile.write(res)
            return

        if path == "/api/logs":
            task_id = payload.get("task_id", "GENERAL")
            agent_type = payload.get("agent_type", "system")
            level = payload.get("level", "info")
            message = payload.get("message", "")

            log_entry = GLOBAL_STORE.append_log(
                task_id=task_id,
                agent_type=agent_type,
                level=level,
                message=message,
            )

            res = json.dumps({"status": "ok", "log": log_entry}).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(res)))
            self.end_headers()
            self.wfile.write(res)
            return

        if path == "/api/reset":
            data = GLOBAL_STORE.reset()
            res = json.dumps(data).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(res)))
            self.end_headers()
            self.wfile.write(res)
            return

        self.send_response(HTTPStatus.NOT_FOUND)
        self._set_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"error": "Not Found"}')


def run_server(port=DEFAULT_PORT, host=DEFAULT_HOST, db_path=None):
    if db_path and db_path != GLOBAL_STORE.db_path:
        GLOBAL_STORE.db_path = db_path
        GLOBAL_STORE._init_db()

    server = ThreadingHTTPServer((host, port), OrchestratorHandler)
    print(f"[*] Multi-Agent Orchestrator Server running on http://{host}:{port}")
    print(f"[*] Dashboard URL: http://localhost:{port}/")
    print(f"[*] SQLite DB:     {GLOBAL_STORE.db_path}")
    print(f"[*] SSE Stream:   http://localhost:{port}/events")
    print(f"[*] Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Agent Orchestrator Real-Time Server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port number (default: {DEFAULT_PORT})")
    parser.add_argument("--host", type=str, default=DEFAULT_HOST, help=f"Host address (default: {DEFAULT_HOST})")
    parser.add_argument("--db", type=str, default=DEFAULT_DB_PATH, help=f"SQLite database file path (default: {DEFAULT_DB_PATH})")
    args = parser.parse_args()
    run_server(port=args.port, host=args.host, db_path=args.db)
