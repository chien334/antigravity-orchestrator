#!/usr/bin/env python3
"""
Real-time Orchestrator Dashboard Server
Zero-dependency HTTP server with SSE (Server-Sent Events), REST API,
financial token cost computation, historical audit reporting, and agent kill controls.
"""

import argparse
import datetime
import json
import os
import queue
import sys
import threading
import time
import sqlite3
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

DEFAULT_PORT = int(os.environ.get("ORCHESTRATOR_PORT", "8484"))
DEFAULT_DB_PATH = os.environ.get(
    "ORCHESTRATOR_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "orchestrator.db")
)

# ---------------------------------------------------------------------------
# Pricing Constants & Cost Estimation
# ---------------------------------------------------------------------------
# Gemini Token Rates (USD per 1,000,000 tokens)
PRICING_TABLE = {
    "argon": {"in": 1.25, "out": 5.00, "cache": 0.3125},
    "pro": {"in": 1.25, "out": 5.00, "cache": 0.3125},
    "gemini-4-argon": {"in": 1.25, "out": 5.00, "cache": 0.3125},
    "gemini-1.5-pro": {"in": 1.25, "out": 5.00, "cache": 0.3125},
    "flash": {"in": 0.075, "out": 0.30, "cache": 0.01875},
    "gemini-3.8-flash": {"in": 0.075, "out": 0.30, "cache": 0.01875},
    "flash_lite": {"in": 0.0375, "out": 0.15, "cache": 0.01},
    "default": {"in": 1.25, "out": 5.00, "cache": 0.3125},
}
USD_TO_VND_RATE = 25400.0


def compute_cost(model, in_tok, out_tok, cache_tok):
    """Calculate actual cost and cache savings in USD and VND."""
    m = (model or "").lower()
    rates = PRICING_TABLE["default"]
    for k in PRICING_TABLE:
        if k in m:
            rates = PRICING_TABLE[k]
            break

    in_cost = (in_tok / 1_000_000.0) * rates["in"]
    out_cost = (out_tok / 1_000_000.0) * rates["out"]
    cache_cost = (cache_tok / 1_000_000.0) * rates["cache"]
    actual_usd = in_cost + out_cost + cache_cost

    # Standard baseline cost if cache tokens were charged at full input prompt rate
    baseline_usd = ((in_tok + cache_tok) / 1_000_000.0) * rates["in"] + out_cost
    saved_usd = max(0.0, baseline_usd - actual_usd)

    actual_vnd = round(actual_usd * USD_TO_VND_RATE)
    saved_vnd = round(saved_usd * USD_TO_VND_RATE)

    return {
        "usd": round(actual_usd, 4),
        "vnd": actual_vnd,
        "saved_usd": round(saved_usd, 4),
        "saved_vnd": saved_vnd,
        "rates": rates,
    }


# ---------------------------------------------------------------------------
# State Store (SQLite-backed)
# ---------------------------------------------------------------------------

class StateStore:
    def __init__(self, db_path=None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._lock = threading.Lock()
        self.subscribers = set()  # set of queue.Queue
        self._init_db()
        self._start_token_auditor()

    def _start_token_auditor(self):
        """Background daemon: automatically audits and synchronizes tokens from Antigravity transcripts every 3 seconds."""
        def _audit_loop():
            brain_dir = os.path.expanduser("~/.gemini/antigravity/brain")
            while True:
                time.sleep(3)
                if not os.path.isdir(brain_dir):
                    continue
                try:
                    updates = []
                    with self._lock:
                        conn = self._get_connection()
                        try:
                            cur = conn.cursor()
                            cur.execute("SELECT task_id, conv_id, input_tokens, output_tokens, cache_tokens, total_tokens FROM tasks")
                            rows = cur.fetchall()
                            for r in rows:
                                c_id = r["conv_id"]
                                if not c_id:
                                    continue
                                t_path = os.path.join(brain_dir, c_id, ".system_generated", "logs", "transcript.jsonl")
                                if not os.path.isfile(t_path):
                                    continue
                                in_t, out_t, cache_t = 0, 0, 0
                                with open(t_path, "r", encoding="utf-8") as f:
                                    for line in f:
                                        try:
                                            d = json.loads(line)
                                            in_t += d.get("input_tokens", 0)
                                            out_t += d.get("output_tokens", 0)
                                            cache_t += d.get("cache_read_tokens", 0)
                                        except Exception:
                                            pass
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

                    if updates:
                        self.broadcast("state_sync", {"metrics": metrics})
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
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_group ON tasks(parallel_group)")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_id ON logs(id DESC)")
            finally:
                conn.close()

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
        }

    def upsert_task(self, task_id, agent_type, status, progress=None, scope=None, notes=None, conv_id=None, model=None, complexity=None, depends_on=None, parallel_group=None, input_tokens=None, output_tokens=None, cache_tokens=None):
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
                final_model = model if model is not None else existing.get("model", "auto")
                final_complexity = (complexity if complexity is not None else existing.get("complexity", "medium")).lower()
                final_status = status or existing.get("status", "pending")
                final_progress = max(0, min(100, int(progress) if progress is not None else existing.get("progress", 0)))
                final_scope = scope if scope is not None else existing.get("scope", "")
                final_notes = notes if notes is not None else existing.get("notes", "")
                final_conv_id = conv_id if conv_id is not None else existing.get("conv_id", "")
                created_at = existing.get("created_at", now)

                with conn:
                    conn.execute("""
                        INSERT INTO tasks (
                            task_id, agent_type, model, complexity, status, progress, scope,
                            notes, conv_id, depends_on, parallel_group, input_tokens,
                            output_tokens, cache_tokens, total_tokens, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                            input_tokens=excluded.input_tokens,
                            output_tokens=excluded.output_tokens,
                            cache_tokens=excluded.cache_tokens,
                            total_tokens=excluded.total_tokens,
                            updated_at=excluded.updated_at
                    """, (
                        task_id, final_agent, final_model, final_complexity, final_status,
                        final_progress, final_scope, final_notes, final_conv_id,
                        json.dumps(deps), group, in_tok, out_tok, cache_tok, total_tok,
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
                            SELECT id FROM logs ORDER BY id DESC LIMIT 1000
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

                metrics = self._calculate_metrics_conn(conn)
                return {
                    "tasks": tasks,
                    "logs": logs,
                    "metrics": metrics,
                }
            finally:
                conn.close()

    def reset(self):
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("DELETE FROM tasks")
                    conn.execute("DELETE FROM logs")
                metrics = self._calculate_metrics_conn(conn)
            finally:
                conn.close()
        self.broadcast("reset_event", {"metrics": metrics})
        return {"status": "ok", "metrics": metrics}

    def subscribe(self):
        q = queue.Queue(maxsize=100)
        with self._lock:
            self.subscribers.add(q)
        return q

    def unsubscribe(self, q):
        with self._lock:
            self.subscribers.discard(q)

    def broadcast(self, event_type, payload):
        data = f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
        with self._lock:
            dead = []
            for q in self.subscribers:
                try:
                    q.put_nowait(data)
                except queue.Full:
                    dead.append(q)
            for q in dead:
                self.subscribers.discard(q)


GLOBAL_STORE = StateStore()

# ---------------------------------------------------------------------------
# HTML Dashboard Template
# ---------------------------------------------------------------------------

DASHBOARD_HTML = """<!DOCTYPE html>
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
            <span id="task-count-badge" class="px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 text-xs font-semibold">0</span>
            <span class="text-xs text-slate-400 font-normal hidden sm:inline">&middot; Đang thực hiện & chờ xử lý</span>
          </div>

          <div class="flex items-center space-x-3 text-xs">
            <label class="flex items-center space-x-1.5 cursor-pointer text-slate-400 hover:text-slate-200 select-none">
              <input type="checkbox" id="live-show-completed-toggle" onchange="renderTasksTable()" class="rounded bg-slate-800 border-slate-700 text-indigo-600 focus:ring-0">
              <span>Hiện cả task đã xong</span>
            </label>
            <button onclick="switchTab('history')" class="text-indigo-400 hover:text-indigo-300 font-medium flex items-center space-x-1">
              <span>Xem lịch sử chi tiết</span>
              <span>&rarr;</span>
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
              <option value="argon">Gemini 4 Argon (Pro)</option>
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
      if (m.includes('argon') || m.includes('pro') || m.includes('gemini-4')) {
        return `<span class="px-2 py-0.5 rounded text-[11px] font-mono border bg-purple-500/15 text-purple-300 border-purple-500/30 flex items-center gap-1 inline-flex"><span class="text-[9px]">✦</span>Argon (Pro)</span>`;
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
      const showCompleted = document.getElementById('live-show-completed-toggle')?.checked || false;
      const allTasks = Object.values(state.tasks).sort((a, b) => (b.updated_at || '').localeCompare(a.updated_at || ''));
      
      // Live Dashboard focuses only on active/in-flight tasks (pending, running, blocked)
      const activeTasks = allTasks.filter(t => t.status === 'running' || t.status === 'pending' || t.status === 'blocked');
      const displayedTasks = showCompleted ? allTasks : activeTasks;

      const countBadge = document.getElementById('task-count-badge');
      if (countBadge) {
        countBadge.textContent = displayedTasks.length;
      }
      
      if (displayedTasks.length === 0) {
        if (!showCompleted && allTasks.some(t => t.status === 'completed' || t.status === 'cancelled')) {
          const completedCount = allTasks.filter(t => t.status === 'completed').length;
          tbody.innerHTML = `
            <tr>
              <td colspan="13" class="py-12 text-center">
                <div class="flex flex-col items-center justify-center space-y-2.5">
                  <div class="h-10 w-10 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
                  </div>
                  <div class="text-sm font-bold text-slate-200">Không có tác vụ đang chạy hoặc chờ xử lý</div>
                  <div class="text-xs text-slate-400 max-w-md">Toàn bộ ${completedCount} tác vụ trước đó đã hoàn thành thành công và được lưu trữ trong lịch sử để giao diện Live luôn gọn gàng.</div>
                  <div class="pt-2 flex items-center space-x-3">
                    <button onclick="switchTab('history')" class="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow-md shadow-indigo-600/20 transition flex items-center space-x-1.5">
                      <span>Mở tab Lịch sử & Chi phí</span>
                      <span>&rarr;</span>
                    </button>
                    <button onclick="document.getElementById('live-show-completed-toggle').checked = true; renderTasksTable();" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-medium transition">
                      Hiện task hoàn tất tại đây
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

      tbody.innerHTML = displayedTasks.map(t => {
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
        let actionBtn = `<span class="text-slate-600 text-xs">-</span>`;
        if (t.status === 'running') {
          actionBtn = `
            <button onclick="killTask('${t.task_id}')" class="px-2.5 py-1 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 transition text-[11px] font-bold flex items-center gap-1 mx-auto shadow-sm">
              <svg class="w-3 h-3 text-rose-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clip-rule="evenodd" /></svg>
              <span>Kill</span>
            </button>
          `;
        }

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
          if (modelFilter === 'argon' && !m.includes('argon') && !m.includes('pro')) return false;
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

        let actionBtn = `<span class="text-slate-600 text-xs">-</span>`;
        if (t.status === 'running') {
          actionBtn = `
            <button onclick="killTask('${t.task_id}')" class="px-2.5 py-1 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 font-bold text-[10px] transition">
              Kill
            </button>
          `;
        }

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
    }

    window.addEventListener('DOMContentLoaded', () => {
      initPipeline();
      connectSSE();
    });
  </script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# HTTP Request Handler
# ---------------------------------------------------------------------------

class OrchestratorHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            body = DASHBOARD_HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self._set_cors_headers()
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/state":
            data = GLOBAL_STORE.get_state()
            body = json.dumps(data).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
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

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            payload = json.loads(post_body.decode("utf-8")) if post_body else {}
        except json.JSONDecodeError:
            self.send_response(HTTPStatus.BAD_REQUEST)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Invalid JSON body"}')
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
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_tokens=cache_tokens,
            )

            res = json.dumps({"status": "ok", "task": task}).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(res)))
            self.end_headers()
            self.wfile.write(res)
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


def run_server(port=DEFAULT_PORT, host="0.0.0.0", db_path=None):
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
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address (default: 0.0.0.0)")
    parser.add_argument("--db", type=str, default=DEFAULT_DB_PATH, help=f"SQLite database file path (default: {DEFAULT_DB_PATH})")
    args = parser.parse_args()
    run_server(port=args.port, host=args.host, db_path=args.db)
