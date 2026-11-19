#!/usr/bin/env python3
"""
Multi-Agent Orchestrator Client
Python library and CLI utility for sending telemetry, task updates, and logs to the Orchestrator Server.
Features Gemini 4 Carbon, Gemini 4 Neon (#1 SWE Coding Agent), and Gemini 4 Hydrogen evolution:
smart SWE model routing, 3-Stage Circuit Breaker escalation, DAG ready-queue querying, model analytics, and audit exporting.
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Union
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = os.environ.get("ORCHESTRATOR_URL", "http://localhost:8484").rstrip("/")


def _fmt_rate(val: Any) -> str:
    """Format per-1M token USD rate cleanly (e.g. $3.00, $15.00, $0.15, $0.075)."""
    try:
        num = float(val or 0.0)
    except (TypeError, ValueError):
        return "$0.00"
    trimmed = f"{num:.6f}".rstrip("0").rstrip(".")
    if "." not in trimmed or len(trimmed.split(".")[1]) < 2:
        return f"${num:.2f}"
    return f"${trimmed}"


def _normalize_desktop_driver(driver: Optional[str]) -> str:
    """Normalize driver aliases (e.g. linux_x11 -> linux_pwa) while preserving defaults."""
    val = (driver or "auto").strip()
    if val == "linux_x11":
        return "linux_pwa"
    return val


def _to_pct(val: Any, default_ratio: float = 0.0) -> int:
    """Convert a 0.0-1.0 ratio or 0-100 percentage into a rounded integer percentage."""
    try:
        num = float(default_ratio if val is None else val)
    except (TypeError, ValueError):
        num = default_ratio
    if 0.0 <= num <= 1.0:
        return int(round(num * 100))
    return int(round(num))


class OrchestratorClient:
    """Client for interacting with the Multi-Agent Orchestrator Server."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")

    def _request(
        self,
        method: str,
        path: str,
        payload: Optional[dict] = None,
        timeout: int = 10,
    ) -> dict:
        url = f"{self.base_url}{path}"
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method=method.upper(),
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
                try:
                    return json.loads(raw)
                except json.JSONDecodeError as je:
                    return {"error": f"Invalid JSON response from {url}: {je}"}
        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            if err_body:
                try:
                    parsed = json.loads(err_body)
                    if isinstance(parsed, dict):
                        if "error" not in parsed:
                            parsed["error"] = parsed.get("message") or f"HTTP {e.code} from {url}"
                        return parsed
                except json.JSONDecodeError:
                    pass
            return {"error": f"HTTP {e.code} from {url}: {err_body or e.reason}"}
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            return {"error": f"Failed to connect to Orchestrator at {url}: {e}"}

    def _post(self, path: str, payload: dict, timeout: int = 10) -> dict:
        return self._request("POST", path, payload=payload, timeout=timeout)

    def _get(self, path: str, timeout: int = 10) -> dict:
        return self._request("GET", path, payload=None, timeout=timeout)

    def update_task(
        self,
        task_id: str,
        agent_type: str,
        status: str,
        progress: Optional[int] = None,
        scope: Optional[str] = None,
        notes: Optional[str] = None,
        conv_id: Optional[str] = None,
        model: Optional[str] = None,
        complexity: Optional[str] = None,
        depends_on: Optional[list] = None,
        parallel_group: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        cache_tokens: Optional[int] = None,
        reasoning_effort: Optional[str] = None,
    ) -> dict:
        """Update or create a task status in the Orchestrator dashboard."""
        payload = {
            "task_id": task_id,
            "agent_type": agent_type,
            "status": status,
        }
        if progress is not None:
            payload["progress"] = progress
        if scope is not None:
            payload["scope"] = scope
        if notes is not None:
            payload["notes"] = notes
        if conv_id is not None:
            payload["conv_id"] = conv_id
        if model is not None:
            payload["model"] = model
        if complexity is not None:
            payload["complexity"] = complexity
        if depends_on is not None:
            payload["depends_on"] = depends_on
        if parallel_group is not None:
            payload["parallel_group"] = parallel_group
        if input_tokens is not None:
            payload["input_tokens"] = input_tokens
        if output_tokens is not None:
            payload["output_tokens"] = output_tokens
        if cache_tokens is not None:
            payload["cache_tokens"] = cache_tokens
        if reasoning_effort is not None:
            payload["reasoning_effort"] = reasoning_effort

        return self._post("/api/tasks", payload)

    def kill_task(self, task_id: str, reason: Optional[str] = None) -> dict:
        """Kill or cancel a running task via the Orchestrator."""
        payload = {"task_id": task_id}
        if reason:
            payload["reason"] = reason
        return self._post("/api/tasks/kill", payload)

    def log(
        self,
        task_id: str,
        agent_type: str,
        message: str,
        level: str = "info",
    ) -> dict:
        """Append a log event to the Orchestrator dashboard."""
        payload = {
            "task_id": task_id,
            "agent_type": agent_type,
            "level": level,
            "message": message,
        }
        return self._post("/api/logs", payload)

    def get_state(self) -> dict:
        """Retrieve full state snapshot (tasks, logs, metrics)."""
        return self._get("/api/state")

    def reset(self) -> dict:
        """Reset state in the Orchestrator dashboard."""
        return self._post("/api/reset", {})

    def list_models(self) -> dict:
        """Retrieve registered models, pricing, and capabilities (GET /api/models)."""
        return self._get("/api/models")

    def recommend_model(
        self,
        agent_type: str,
        complexity: str = "medium",
        scope: str = "",
        file_count: int = 0,
        has_security_impact: bool = False,
        budget_mode: str = "balanced",
        retry_count: int = 0,
        desktop_available: Optional[bool] = None,
        read_only: bool = False,
        prefer_desktop: bool = False,
        desktop_target_share: float = 0.60,
        desktop_queue_busy: Optional[bool] = None,
        **kwargs,
    ) -> dict:
        """Call POST /api/router/recommend to dynamically recommend model and reasoning effort."""
        files = kwargs.get("files", file_count)
        sec_impact = kwargs.get("security_impact", has_security_impact)
        retries = kwargs.get("retries", retry_count)
        desk_avail = kwargs.get("desktop_available", desktop_available)
        ro = kwargs.get("read_only", read_only)
        pref_desk = kwargs.get("prefer_desktop", prefer_desktop)
        target_share = kwargs.get("target_desktop_share", desktop_target_share)
        queue_busy = kwargs.get("queue_busy", desktop_queue_busy)
        payload: dict[str, Any] = {
            "agent_type": agent_type,
            "complexity": complexity,
            "scope": scope,
            "file_count": files,
            "has_security_impact": sec_impact,
            "budget_mode": budget_mode,
            "retry_count": retries,
            "desktop_target_share": float(target_share if target_share is not None else 0.60),
        }
        if desk_avail is not None:
            payload["desktop_available"] = bool(desk_avail)
        if queue_busy is not None:
            payload["desktop_queue_busy"] = bool(queue_busy)
        if ro:
            payload["read_only"] = True
        if pref_desk:
            payload["prefer_desktop"] = True
        return self._post("/api/router/recommend", payload)

    def recommend(
        self,
        agent_type: str,
        complexity: str = "medium",
        scope: str = "",
        files: int = 0,
        security_impact: bool = False,
        budget_mode: str = "balanced",
        retry_count: int = 0,
        desktop_available: Optional[bool] = None,
        read_only: bool = False,
        prefer_desktop: bool = False,
        desktop_target_share: float = 0.60,
        desktop_queue_busy: Optional[bool] = None,
        **kwargs,
    ) -> dict:
        """Alias for recommend_model matching plan specification."""
        file_count = kwargs.pop("file_count", files)
        has_sec = kwargs.pop("has_security_impact", security_impact)
        retries = kwargs.pop("retries", retry_count)
        desk_avail = kwargs.pop("desktop_available", desktop_available)
        ro = kwargs.pop("read_only", read_only)
        pref_desk = kwargs.pop("prefer_desktop", prefer_desktop)
        target_share = kwargs.pop("target_desktop_share", desktop_target_share)
        queue_busy = kwargs.pop("queue_busy", desktop_queue_busy)
        return self.recommend_model(
            agent_type=agent_type,
            complexity=complexity,
            scope=scope,
            file_count=file_count,
            has_security_impact=has_sec,
            budget_mode=budget_mode,
            retry_count=retries,
            desktop_available=desk_avail,
            read_only=ro,
            prefer_desktop=pref_desk,
            desktop_target_share=target_share,
            desktop_queue_busy=queue_busy,
            **kwargs,
        )

    def allocate_dag(
        self,
        tasks: Optional[List[Dict[str, Any]]] = None,
        desktop_available: Optional[bool] = None,
        desktop_target_share: float = 0.60,
        apply: bool = False,
        budget_mode: str = "balanced",
        desktop_queue_busy: Optional[bool] = None,
    ) -> dict:
        """Allocate pending DAG tasks across Gemini Desktop App and API models (POST /api/router/allocate-dag)."""
        if tasks is None:
            state = self.get_state()
            if isinstance(state, dict) and "error" in state:
                return state
            raw_tasks = state.get("tasks", []) if isinstance(state, dict) else []
            if isinstance(raw_tasks, dict):
                raw_tasks = list(raw_tasks.values())
            task_list = [
                t for t in raw_tasks
                if isinstance(t, dict) and str(t.get("status", "pending")).lower() == "pending"
            ]
        else:
            task_list = list(tasks)

        payload: dict[str, Any] = {
            "tasks": task_list,
            "desktop_target_share": float(desktop_target_share if desktop_target_share is not None else 0.60),
            "apply": bool(apply),
            "budget_mode": budget_mode,
        }
        if desktop_available is not None:
            payload["desktop_available"] = bool(desktop_available)
        if desktop_queue_busy is not None:
            payload["desktop_queue_busy"] = bool(desktop_queue_busy)

        return self._post("/api/router/allocate-dag", payload)

    def get_ready_tasks(self) -> dict:
        """Retrieve ready and unblocked tasks from the DAG Ready Queue (GET /api/dag/ready)."""
        return self._get("/api/dag/ready")

    def next_ready(self) -> dict:
        """Call GET /api/dag/ready to retrieve ready and unblocked tasks."""
        return self.get_ready_tasks()

    def get_model_analytics(self) -> dict:
        """Retrieve per-model token consumption and financial spend breakdown (GET /api/analytics/models)."""
        return self._get("/api/analytics/models")

    def export_audit(
        self,
        fmt: Optional[str] = None,
        format: Optional[str] = None,
        out_path: Optional[str] = None,
        output: Optional[str] = None,
    ) -> Union[str, dict]:
        """Fetch audit report from GET /api/audit/export?format=... and optionally write to file.

        Supports format/fmt='markdown' or 'json'.
        """
        export_format = (format or fmt or "markdown").lower()
        target_path = out_path or output
        url = f"{self.base_url}/api/audit/export?format={export_format}"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                content = res.read().decode("utf-8")
                if export_format == "json":
                    try:
                        data = json.loads(content)
                    except json.JSONDecodeError:
                        data = content
                else:
                    data = content
        except urllib.error.URLError as e:
            return {"error": f"Failed to export audit from Orchestrator at {url}: {e}"}

        if target_path:
            try:
                parent_dir = os.path.dirname(target_path)
                if parent_dir and not os.path.exists(parent_dir):
                    os.makedirs(parent_dir, exist_ok=True)
                with open(target_path, "w", encoding="utf-8") as f:
                    if isinstance(data, (dict, list)):
                        f.write(json.dumps(data, indent=2))
                    else:
                        f.write(str(data))
            except Exception as e:
                return {"error": f"Failed to write audit report to {target_path}: {e}"}

        return data

    def desktop_status(
        self,
        driver: str = "auto",
        target_os: str = "auto",
        app_path: Optional[str] = None,
        os_override: Optional[str] = None,
    ) -> dict:
        """Probe cross-platform Gemini Desktop App readiness and driver health (GET /api/desktop/status)."""
        eff_driver = _normalize_desktop_driver(driver)
        eff_os = (os_override if os_override is not None else target_os) or "auto"
        params: dict[str, str] = {
            "driver": eff_driver,
            "target_os": eff_os,
        }
        if app_path:
            params["app_path"] = app_path
        query = urllib.parse.urlencode(params)
        return self._get(f"/api/desktop/status?{query}", timeout=15)

    def desktop_dispatch(
        self,
        prompt: str,
        task_id: Optional[str] = None,
        driver: str = "auto",
        timeout_sec: int = 240,
        output_path: Optional[str] = None,
        redact_secrets: bool = True,
        strict_secrets: bool = False,
        restore_clipboard: bool = True,
        new_chat: bool = True,
        async_mode: bool = False,
        target_os: str = "auto",
        app_path: Optional[str] = None,
        metadata: Optional[dict] = None,
        job_id: Optional[str] = None,
        mode: str = "task",
        workspace_path: Optional[str] = None,
        no_workspace: bool = False,
        background: bool = True,
        allow_edits: bool = False,
    ) -> dict:
        """Dispatch a bounded prompt to the local Gemini Desktop Worker (POST /api/desktop/dispatch)."""
        eff_mode = (mode or "task").strip().lower() or "task"
        eff_workspace = None if no_workspace else workspace_path
        payload: dict[str, Any] = {
            "prompt": prompt,
            "driver": _normalize_desktop_driver(driver),
            "target_os": target_os or "auto",
            "timeout_sec": int(timeout_sec),
            "redact_secrets": bool(redact_secrets),
            "strict_secrets": bool(strict_secrets),
            "restore_clipboard": bool(restore_clipboard),
            "new_chat": bool(new_chat),
            "async_mode": bool(async_mode),
            "mode": eff_mode,
            "workspace_path": eff_workspace,
            "no_workspace": bool(no_workspace),
            "background": bool(background),
            "allow_edits": bool(allow_edits),
        }
        if task_id is not None:
            payload["task_id"] = task_id
        if output_path is not None:
            payload["output_path"] = output_path
        if app_path is not None:
            payload["app_path"] = app_path
        if metadata is not None:
            payload["metadata"] = metadata
        if job_id is not None:
            payload["job_id"] = job_id

        req_timeout = 15 if async_mode else max(30, int(timeout_sec) + 20)
        return self._post("/api/desktop/dispatch", payload, timeout=req_timeout)

    def desktop_jobs(
        self,
        job_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        """List queued, running, or completed desktop worker jobs (GET /api/desktop/jobs)."""
        params: dict[str, Any] = {"limit": int(limit)}
        if job_id:
            params["job_id"] = job_id
        if status:
            params["status"] = status
        query = urllib.parse.urlencode(params)
        return self._get(f"/api/desktop/jobs?{query}")

    def desktop_cancel(self, job_id: str) -> dict:
        """Cancel a queued or running desktop worker job (POST /api/desktop/cancel)."""
        return self._post("/api/desktop/cancel", {"job_id": job_id})


def auto_detect_tokens_and_conv(conv_id=None, in_tok=None, out_tok=None, cache_tok=None):
    """Auto-detect current Antigravity conversation ID and token metrics if not explicitly provided."""
    brain_dir = os.path.expanduser("~/.gemini/antigravity/brain")
    if not conv_id:
        conv_id = os.environ.get("AGY_CONVERSATION_ID")
    if not conv_id and os.path.isdir(brain_dir):
        candidates = []
        try:
            for entry in os.scandir(brain_dir):
                if entry.is_dir() and entry.name != "tempmediaStorage":
                    t_path = os.path.join(entry.path, ".system_generated", "logs", "transcript.jsonl")
                    if os.path.isfile(t_path):
                        candidates.append((os.path.getmtime(t_path), entry.name, t_path))
            if candidates:
                candidates.sort(key=lambda x: x[0], reverse=True)
                conv_id = candidates[0][1]
        except Exception:
            pass

    if (in_tok is None or out_tok is None or cache_tok is None) and conv_id and os.path.isdir(brain_dir):
        t_path = os.path.join(brain_dir, conv_id, ".system_generated", "logs", "transcript.jsonl")
        if os.path.isfile(t_path):
            calc_in, calc_out, calc_cache = 0, 0, 0
            try:
                with open(t_path, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            d = json.loads(line)
                            calc_in += d.get("input_tokens", 0)
                            calc_out += d.get("output_tokens", 0)
                            calc_cache += d.get("cache_read_tokens", 0)
                        except Exception:
                            pass
                if in_tok is None:
                    in_tok = calc_in
                if out_tok is None:
                    out_tok = calc_out
                if cache_tok is None:
                    cache_tok = calc_cache
            except Exception:
                pass

    return conv_id, in_tok, out_tok, cache_tok


def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Orchestrator CLI")
    parser.add_argument(
        "--url",
        type=str,
        default=DEFAULT_BASE_URL,
        help=f"Orchestrator base URL (default: {DEFAULT_BASE_URL})",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # update
    update_parser = subparsers.add_parser("update", help="Update or create a task")
    update_parser.add_argument("--task", required=True, help="Task ID (e.g. TASK-01)")
    update_parser.add_argument("--agent", required=True, help="Agent persona name (e.g. builder, reviewer)")
    update_parser.add_argument(
        "--status",
        required=True,
        choices=["pending", "running", "completed", "blocked", "failed"],
        help="Task status",
    )
    update_parser.add_argument("--progress", type=int, default=None, help="Task progress percentage (0-100)")
    update_parser.add_argument("--scope", type=str, default=None, help="Task scope or description")
    update_parser.add_argument("--notes", type=str, default=None, help="Additional notes or status update")
    update_parser.add_argument("--conv-id", type=str, default=None, help="Subagent conversation ID")
    update_parser.add_argument(
        "--model",
        type=str,
        default=None,
        help=(
            "Assigned Model (e.g. gemini-4-neon, neon, gemini-pro-orchestrator-neon, "
            "gemini-4-carbon, carbon, gemini-4-hydrogen, hydrogen, "
            "gemini-4-argon, pro, gemini-3.8-flash, flash, flash_lite)"
        ),
    )
    update_parser.add_argument(
        "--reasoning-effort",
        "--effort",
        dest="reasoning_effort",
        type=str,
        default=None,
        choices=["low", "medium", "high", "xhigh"],
        help="Tunable reasoning effort for models supporting reasoning depth (low, medium, high, xhigh)",
    )
    update_parser.add_argument(
        "--complexity",
        "--tier",
        dest="complexity",
        type=str,
        default=None,
        choices=["low", "medium", "high", "critical"],
        help="Task complexity tier (low, medium, high, critical)",
    )
    update_parser.add_argument(
        "--depends-on",
        type=str,
        default=None,
        help="Comma-separated prerequisite task IDs that must complete before this task (e.g. TASK-01,TASK-02)",
    )
    update_parser.add_argument(
        "--group",
        "--parallel-group",
        dest="parallel_group",
        type=str,
        default=None,
        help="Parallel execution group tag (e.g. BUILD-PARALLEL, AUDIT-FANOUT)",
    )
    update_parser.add_argument("--input-tokens", type=int, default=None, help="Input (prompt) tokens consumed")
    update_parser.add_argument("--output-tokens", type=int, default=None, help="Output (completion) tokens generated")
    update_parser.add_argument("--cache-tokens", type=int, default=None, help="Context cache read tokens")

    # log
    log_parser = subparsers.add_parser("log", help="Append a log message")
    log_parser.add_argument("--task", default="GENERAL", help="Task ID")
    log_parser.add_argument("--agent", default="system", help="Agent persona name")
    log_parser.add_argument("--message", required=True, help="Log message text")
    log_parser.add_argument(
        "--level",
        default="info",
        choices=["info", "warn", "error", "thought"],
        help="Log severity level",
    )

    # kill
    kill_parser = subparsers.add_parser("kill", help="Kill or cancel an active task/agent")
    kill_parser.add_argument("--task", required=True, help="Task ID to cancel/kill")
    kill_parser.add_argument("--reason", default="Killed by user CLI", help="Optional reason for cancellation")

    # state
    subparsers.add_parser("state", help="Get current orchestrator state")

    # reset
    subparsers.add_parser("reset", help="Reset all orchestrator tasks and logs")

    # models
    models_parser = subparsers.add_parser(
        "models",
        aliases=["list-models", "model-list"],
        help="List registered models, pricing, and capabilities",
    )
    models_parser.add_argument("--json", action="store_true", help="Output raw JSON response")
    models_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (json, text, default: json)",
    )

    # recommend
    recommend_parser = subparsers.add_parser(
        "recommend",
        help="Recommend optimal model and reasoning effort via Smart Router",
    )
    recommend_parser.add_argument(
        "--agent",
        required=True,
        help="Agent persona name (e.g. security-auditor, spec-engineer, task-planner, code-reviewer, builder, test-engineer)",
    )
    recommend_parser.add_argument(
        "--complexity",
        type=str,
        default="medium",
        choices=["low", "medium", "high", "critical"],
        help="Task complexity tier (low, medium, high, critical, default: medium)",
    )
    recommend_parser.add_argument("--scope", type=str, default="", help="Task scope description")
    recommend_parser.add_argument("--files", "--file-count", dest="files", type=int, default=0, help="Number of files to be modified")
    recommend_parser.add_argument(
        "--security-impact",
        "--has-security-impact",
        dest="security_impact",
        action="store_true",
        help="Flag if task has cybersecurity or vulnerability impact",
    )
    recommend_parser.add_argument(
        "--budget-mode",
        type=str,
        default="balanced",
        choices=[
            "balanced",
            "quality_first",
            "speed_first",
            "latency_sensitive",
            "cost_saving",
            "cost_first",
            "hybrid_desktop",
            "offload_heavy_to_desktop",
            "api_only",
        ],
        help="Routing optimization mode (balanced, quality_first, speed_first, latency_sensitive, cost_saving, cost_first, hybrid_desktop, offload_heavy_to_desktop, api_only, default: balanced)",
    )
    recommend_parser.add_argument(
        "--retry-count",
        "--retries",
        dest="retry_count",
        type=int,
        default=0,
        help="Prior failure retry count for 3-Stage Circuit Breaker (0=Hydrogen, 1=Hydrogen xhigh, 2=Neon high, 3+=Carbon high, default: 0)",
    )
    rec_desktop_group = recommend_parser.add_mutually_exclusive_group()
    rec_desktop_group.add_argument(
        "--desktop-available",
        dest="desktop_available",
        action="store_const",
        const=True,
        default=None,
        help="Indicate local Gemini Desktop App bridge is ready for offload",
    )
    rec_desktop_group.add_argument(
        "--no-desktop",
        "--api-only",
        dest="desktop_available",
        action="store_const",
        const=False,
        help="Disable Desktop App offload and force pure API model routing",
    )
    recommend_parser.add_argument(
        "--target-desktop-share",
        dest="target_desktop_share",
        type=float,
        default=0.60,
        help="Target Gemini Desktop App peer share ratio 0.0-1.0 (default: 0.60)",
    )
    recommend_parser.add_argument(
        "--desktop-queue-busy",
        "--queue-busy",
        dest="desktop_queue_busy",
        action="store_const",
        const=True,
        default=None,
        help="Indicate local Gemini Desktop App queue is currently busy",
    )
    recommend_parser.add_argument(
        "--read-only",
        action="store_true",
        help="Indicate task is strictly non-mutating / read-only",
    )
    recommend_parser.add_argument(
        "--prefer-desktop",
        action="store_true",
        help="Prefer offloading eligible non-mutating synthesis to Gemini Desktop App",
    )
    recommend_parser.add_argument("--json", action="store_true", help="Output raw JSON response")
    recommend_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (json, text, default: json)",
    )

    # allocate-dag
    allocate_dag_parser = subparsers.add_parser(
        "allocate-dag",
        aliases=["allocate_dag"],
        help="Allocate pending DAG tasks across Gemini Desktop App (60%% target) and API models",
    )
    allocate_dag_parser.add_argument(
        "--target-desktop-share",
        dest="target_desktop_share",
        type=float,
        default=0.60,
        help="Target Gemini Desktop App peer share ratio 0.0-1.0 (default: 0.60)",
    )
    alloc_desktop_group = allocate_dag_parser.add_mutually_exclusive_group()
    alloc_desktop_group.add_argument(
        "--desktop-available",
        dest="desktop_available",
        action="store_const",
        const=True,
        default=None,
        help="Assume local Gemini Desktop App bridge is ready",
    )
    alloc_desktop_group.add_argument(
        "--no-desktop",
        "--api-only",
        dest="desktop_available",
        action="store_const",
        const=False,
        help="Disable Desktop App offload and route 100%% to API models",
    )
    allocate_dag_parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist assigned models to pending tasks on the Orchestrator server",
    )
    allocate_dag_parser.add_argument("--json", action="store_true", help="Output raw JSON response")
    allocate_dag_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (text, json, default: text)",
    )

    # next-ready
    next_ready_parser = subparsers.add_parser(
        "next-ready",
        aliases=["next_ready", "ready"],
        help="Query DAG Ready-Queue for unblocked tasks ready for immediate execution",
    )
    next_ready_parser.add_argument("--json", action="store_true", help="Output raw JSON response")
    next_ready_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (json, text, default: json)",
    )

    # analytics
    analytics_parser = subparsers.add_parser(
        "analytics",
        aliases=["model-analytics"],
        help="Retrieve per-model token consumption and financial spend breakdown",
    )
    analytics_parser.add_argument("--json", action="store_true", help="Output raw JSON response")
    analytics_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (json, text, default: json)",
    )

    # export
    export_parser = subparsers.add_parser(
        "export",
        aliases=["audit-export", "export-audit"],
        help="Export mission audit report in Markdown or JSON format",
    )
    export_parser.add_argument(
        "--format",
        "--fmt",
        dest="format",
        type=str,
        default="markdown",
        choices=["markdown", "json"],
        help="Export format (markdown, json, default: markdown)",
    )
    export_parser.add_argument(
        "--output",
        "--out",
        dest="output",
        type=str,
        default=None,
        help="Output file path to save report (writes to stdout if omitted)",
    )

    # desktop-status / desktop-doctor
    desktop_status_parser = subparsers.add_parser(
        "desktop-status",
        aliases=["desktop-doctor"],
        help="Check cross-platform Gemini Desktop App readiness, permissions, and active driver",
    )
    desktop_status_parser.add_argument(
        "--driver",
        type=str,
        default="auto",
        choices=["auto", "macos_ax", "orca", "windows_uia", "linux_pwa", "linux_x11", "mock"],
        help="Desktop automation driver to probe (default: auto)",
    )
    desktop_status_parser.add_argument(
        "--target-os",
        "--os",
        dest="target_os",
        type=str,
        default="auto",
        choices=["auto", "darwin", "win32", "linux"],
        help="Target OS platform override for diagnostics (default: auto)",
    )
    desktop_status_parser.add_argument(
        "--app-path",
        type=str,
        default=None,
        help="Explicit path to Gemini Desktop App bundle or executable",
    )
    desktop_status_parser.add_argument("--json", action="store_true", help="Output raw JSON response")
    desktop_status_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (json, text, default: json)",
    )

    # desktop-dispatch / desktop-ask
    desktop_dispatch_parser = subparsers.add_parser(
        "desktop-dispatch",
        aliases=["desktop-ask"],
        help="Dispatch a bounded read-only analysis task to the local Gemini Desktop App",
    )
    desktop_dispatch_parser.add_argument("--prompt", type=str, default=None, help="Prompt text to send")
    desktop_dispatch_parser.add_argument("--prompt-file", type=str, default=None, help="Path to Markdown/text file containing prompt")
    desktop_dispatch_parser.add_argument(
        "--context-file",
        action="append",
        default=None,
        help="Optional context file path(s) to append to the prompt",
    )
    desktop_dispatch_parser.add_argument("--task", "--task-id", dest="task", type=str, default=None, help="Optional Orchestrator task ID")
    desktop_dispatch_parser.add_argument("--agent", type=str, default=None, help="Optional requesting agent persona metadata")
    desktop_dispatch_parser.add_argument(
        "--driver",
        type=str,
        default="auto",
        choices=["auto", "macos_ax", "orca", "windows_uia", "linux_pwa", "linux_x11", "mock"],
        help="Desktop automation driver (default: auto)",
    )
    desktop_dispatch_parser.add_argument(
        "--target-os",
        "--os",
        dest="target_os",
        type=str,
        default="auto",
        choices=["auto", "darwin", "win32", "linux"],
        help="Target OS override (default: auto)",
    )
    desktop_dispatch_parser.add_argument("--app-path", type=str, default=None, help="Explicit Gemini app path")
    desktop_dispatch_parser.add_argument(
        "--mode",
        type=str,
        default="task",
        choices=["task", "chat"],
        help="Execution mode in Gemini Desktop App: task (Workspace Agent, default) or chat (Quick Q&A)",
    )
    desktop_dispatch_parser.add_argument(
        "-w",
        "--workspace",
        dest="workspace",
        type=str,
        default=None,
        help="Workspace directory path to attach in task mode (defaults to current working directory unless --no-workspace)",
    )
    desktop_dispatch_parser.add_argument(
        "--no-workspace",
        action="store_true",
        help="Disable automatic current working directory workspace attachment",
    )
    desktop_dispatch_parser.add_argument(
        "--background",
        dest="background",
        action="store_true",
        default=True,
        help="Run silently in background without stealing mouse/clipboard/focus (default)",
    )
    desktop_dispatch_parser.add_argument(
        "--allow-foreground",
        dest="background",
        action="store_false",
        help="Allow foreground UI interaction (only needed once to bookmark a new workspace folder)",
    )
    desktop_dispatch_parser.add_argument(
        "--allow-edits",
        action="store_true",
        default=False,
        help="Authorize Gemini.app Task mode to edit specified files inside --workspace directly (and silently approve edit confirmation cards in background)",
    )
    desktop_dispatch_parser.add_argument("--timeout", type=int, default=240, help="Job timeout in seconds (default: 240)")
    desktop_dispatch_parser.add_argument("--output", "--out", dest="output", type=str, default=None, help="Optional output Markdown artifact path inside docs/reports/")
    desktop_dispatch_parser.add_argument("--no-redact", action="store_true", help="Disable pre-flight secret redaction")
    desktop_dispatch_parser.add_argument("--strict-secrets", action="store_true", help="Reject job if any secret pattern is detected")
    desktop_dispatch_parser.add_argument("--no-restore-clipboard", action="store_true", help="Do not restore prior OS clipboard after paste")
    desktop_dispatch_parser.add_argument("--no-new-chat", action="store_true", help="Reuse active chat instead of opening a new chat")
    desktop_dispatch_parser.add_argument("--async", dest="async_mode", action="store_true", help="Queue job asynchronously and return immediately")
    desktop_dispatch_parser.add_argument("--json", action="store_true", help="Output raw JSON response")
    desktop_dispatch_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (json, text, default: json)",
    )

    # desktop-jobs
    desktop_jobs_parser = subparsers.add_parser(
        "desktop-jobs",
        help="List queued, running, and completed Gemini Desktop Worker jobs",
    )
    desktop_jobs_parser.add_argument("--job-id", type=str, default=None, help="Filter by specific desktop job ID")
    desktop_jobs_parser.add_argument("--status", type=str, default=None, help="Filter by job status (queued, running, completed, failed, timed_out, cancelled, rejected_secrets)")
    desktop_jobs_parser.add_argument("--limit", type=int, default=50, help="Maximum number of jobs to return (default: 50)")
    desktop_jobs_parser.add_argument("--json", action="store_true", help="Output raw JSON response")
    desktop_jobs_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (json, text, default: json)",
    )

    # desktop-cancel
    desktop_cancel_parser = subparsers.add_parser(
        "desktop-cancel",
        help="Cancel a queued or running Gemini Desktop Worker job",
    )
    desktop_cancel_parser.add_argument("pos_job_id", nargs="?", metavar="job_id", default=None, help="Desktop job ID to cancel")
    desktop_cancel_parser.add_argument("--job-id", dest="job_id", type=str, default=None, help="Desktop job ID to cancel")
    desktop_cancel_parser.add_argument("--json", action="store_true", help="Output raw JSON response")
    desktop_cancel_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (json, text, default: json)",
    )

    args = parser.parse_args()
    client = OrchestratorClient(base_url=args.url)

    if args.command == "kill":
        res = client.kill_task(task_id=args.task, reason=args.reason)
        print(json.dumps(res, indent=2))
        if "error" in res:
            sys.exit(1)

    elif args.command == "update":
        conv_id, in_tokens, out_tokens, cache_tokens = auto_detect_tokens_and_conv(
            conv_id=args.conv_id,
            in_tok=args.input_tokens,
            out_tok=args.output_tokens,
            cache_tok=args.cache_tokens,
        )

        res = client.update_task(
            task_id=args.task,
            agent_type=args.agent,
            status=args.status,
            progress=args.progress,
            scope=args.scope,
            notes=args.notes,
            conv_id=conv_id,
            model=args.model,
            complexity=args.complexity,
            depends_on=args.depends_on,
            parallel_group=args.parallel_group,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            cache_tokens=cache_tokens,
            reasoning_effort=args.reasoning_effort,
        )
        print(json.dumps(res, indent=2))
        if "error" in res:
            sys.exit(1)

    elif args.command == "log":
        res = client.log(
            task_id=args.task,
            agent_type=args.agent,
            message=args.message,
            level=args.level,
        )
        print(json.dumps(res, indent=2))
        if "error" in res:
            sys.exit(1)

    elif args.command == "state":
        res = client.get_state()
        print(json.dumps(res, indent=2))
        if "error" in res:
            sys.exit(1)

    elif args.command == "reset":
        res = client.reset()
        print(json.dumps(res, indent=2))
        if "error" in res:
            sys.exit(1)

    elif args.command in ("models", "list-models", "model-list"):
        res = client.list_models()
        if "error" in res:
            print(json.dumps(res, indent=2))
            sys.exit(1)
        if args.format == "text" and not args.json:
            models = res.get("models", {})
            print(f"{'Model':<24} {'Tier':<18} {'Rates ($ in/out/cache per 1M)':<32} {'Reasoning Efforts':<28} {'Notes'}")
            print("-" * 130)
            for m_id, m_data in models.items():
                rates = m_data.get("rates", {})
                rate_str = f"{_fmt_rate(rates.get('in', 0))} / {_fmt_rate(rates.get('out', 0))} / {_fmt_rate(rates.get('cache', 0))}"
                efforts = "|".join(m_data.get("supported_reasoning_efforts", [])) or "None"
                note = ""
                if "neon" in m_id.lower():
                    note = "* #1 SWE Coding Agent | 95% cache savings"
                elif "hydrogen" in m_id.lower():
                    note = "198 tok/s fast workers | 95% cache savings"
                elif "carbon" in m_id.lower():
                    note = "Frontier security & CB Stage 3"
                print(f"{m_id:<24} {m_data.get('tier', ''):<18} {rate_str:<32} {efforts:<28} {note}")
            print("\n3-Stage Circuit Breaker: Retry 0=Hydrogen -> Retry 1=Hydrogen(xhigh) -> Retry 2=Gemini 4 Neon(high) -> Retry 3+=Gemini 4 Carbon(high)")
            external_workers = res.get("external_workers", {})
            if external_workers:
                print("\n=== External Workers ===")
                for w_id, w_data in external_workers.items():
                    rates = w_data.get("rates", {})
                    rate_str = f"{_fmt_rate(rates.get('in', 0))} / {_fmt_rate(rates.get('out', 0))} / {_fmt_rate(rates.get('cache', 0))}"
                    mode = w_data.get("execution_mode", "desktop_bridge")
                    print(f"{w_id:<24} {w_data.get('tier', 'external_desktop'):<18} {rate_str:<32} mode={mode}")
        else:
            print(json.dumps(res, indent=2))

    elif args.command == "recommend":
        res = client.recommend_model(
            agent_type=args.agent,
            complexity=args.complexity,
            scope=args.scope,
            file_count=args.files,
            has_security_impact=args.security_impact,
            budget_mode=args.budget_mode,
            retry_count=args.retry_count,
            desktop_available=args.desktop_available,
            read_only=args.read_only,
            prefer_desktop=args.prefer_desktop,
            desktop_target_share=args.target_desktop_share,
            desktop_queue_busy=args.desktop_queue_busy,
        )
        if "error" in res:
            print(json.dumps(res, indent=2))
            sys.exit(1)
        if args.format == "text" and not args.json:
            rec = res.get("recommendation", {})
            print(f"Recommended Model: {rec.get('model', 'unknown')}")
            if rec.get("reasoning_effort"):
                print(f"Reasoning Effort:  {rec.get('reasoning_effort')}")
            print(f"Tier:              {rec.get('tier', 'unknown')}")
            if rec.get("execution_mode"):
                print(f"Execution Mode:    {rec.get('execution_mode')}")
            print(f"Cost Tier:         {rec.get('estimated_cost_tier', '-')}")
            print(f"Fallback Model:    {rec.get('fallback_model', '-')}")
            if str(rec.get("model", "")).lower() == "gemini-desktop-app":
                cur_raw = rec.get("desktop_share", rec.get("current_desktop_share", res.get("desktop_share", 0.0)))
                tgt_raw = rec.get("desktop_target_share", rec.get("target_desktop_share", args.target_desktop_share))
                cur_pct = _to_pct(cur_raw)
                tgt_pct = _to_pct(tgt_raw)
                fallback_m = rec.get("fallback_model", "-")
                allow_edits = bool(rec.get("allow_edits", rec.get("desktop_allow_edits", False)))
                print(
                    f"Desktop Share: current {cur_pct}% / target {tgt_pct}% | "
                    f"Fallback: {fallback_m} | Allow Edits: {allow_edits}"
                )
            if rec.get("circuit_breaker"):
                cb = rec["circuit_breaker"]
                cb_status = str(cb.get("status", "unknown")).lower()
                retries = cb.get("retries", cb.get("retry_count", 0))
                stage = cb.get("stage")
                if cb_status == "tripped":
                    s_lbl = f"Stage {stage if stage is not None else 3}/3 | "
                    print(f"Circuit Breaker:   TRIPPED ({s_lbl}retries: {retries}, escalated from: {cb.get('escalated_from', 'gemini-4-neon')})")
                elif cb_status == "escalated_neon":
                    s_lbl = f"Stage {stage if stage is not None else 2}/3 | "
                    print(
                        f"Circuit Breaker:   ESCALATED_NEON ({s_lbl}retry #{retries}, "
                        f"escalated from: {cb.get('escalated_from', 'gemini-4-hydrogen')}, "
                        f"next trip: {cb.get('escalate_to', 'gemini-4-carbon')})"
                    )
                elif cb_status == "retrying":
                    s_lbl = f"Stage {stage if stage is not None else 1}/3 | "
                    print(f"Circuit Breaker:   RETRYING ({s_lbl}retry #{retries}, escalating to: {cb.get('escalate_to', 'gemini-4-neon')})")
                else:
                    s_lbl = f"Stage {stage if stage is not None else 0}/3 | "
                    print(f"Circuit Breaker:   {cb_status.upper()} ({s_lbl}retries: {retries}, escalate_to: {cb.get('escalate_to', 'gemini-4-neon')})")
            print(f"Rationale:         {rec.get('rationale', '')}")
        else:
            print(json.dumps(res, indent=2))

    elif args.command in ("allocate-dag", "allocate_dag"):
        res = client.allocate_dag(
            tasks=None,
            desktop_available=args.desktop_available,
            desktop_target_share=args.target_desktop_share,
            apply=args.apply,
        )
        if "error" in res:
            print(json.dumps(res, indent=2))
            sys.exit(1)
        if args.format == "text" and not args.json:
            allocs = res.get("allocations") or res.get("assignments") or res.get("tasks") or []
            summary = res.get("summary") or {}
            total_cnt = summary.get("total_tasks", len(allocs))
            desktop_cnt = summary.get(
                "desktop_tasks",
                summary.get(
                    "desktop_count",
                    sum(1 for a in allocs if "desktop" in str(a.get("assigned_model") or a.get("model") or "").lower()),
                ),
            )
            achieved_raw = summary.get(
                "achieved_desktop_share",
                summary.get(
                    "desktop_share",
                    res.get("achieved_desktop_share", (desktop_cnt / total_cnt) if total_cnt > 0 else 0.0),
                ),
            )
            target_raw = summary.get(
                "target_desktop_share",
                summary.get("desktop_target_share", res.get("desktop_target_share", args.target_desktop_share)),
            )
            achieved_pct = _to_pct(achieved_raw)
            target_pct = _to_pct(target_raw)
            pg_safe = summary.get("parallel_group_safe", summary.get("concurrency_safe", res.get("concurrency_safe", True)))
            desk_ready = summary.get("desktop_available", res.get("desktop_available"))

            print("=== DAG Multi-Model Peer Allocation ===")
            print(
                f"Desktop Ready: {desk_ready if desk_ready is not None else 'auto'} | "
                f"Achieved Desktop Share: {achieved_pct}% ({desktop_cnt}/{total_cnt} tasks) vs {target_pct}% target | "
                f"Parallel-Group Safety: {'SAFE' if pg_safe else 'CONFLICT'}"
            )
            if args.apply or summary.get("applied") or res.get("applied"):
                print("Applied:       True (persisted assigned models to pending tasks on server)")
            print()
            if not allocs:
                print("No pending tasks to allocate.")
            else:
                print(f"{'Task ID':<12} {'Agent':<20} {'Assigned Model':<22} {'Effort':<8} {'Group':<18} {'Concurrency':<14} {'Mode'}")
                print("-" * 112)
                for a in allocs:
                    tid = str(a.get("task_id", "-"))
                    agent = str(a.get("agent_type", "-"))
                    model = str(a.get("assigned_model") or a.get("model") or "-")
                    effort = str(a.get("reasoning_effort") or "-")
                    group = str(a.get("parallel_group") or "-")
                    mode = str(a.get("execution_mode") or ("desktop_bridge" if "desktop" in model.lower() else "api"))
                    safe_val = a.get("concurrency_safe", a.get("parallel_safe", True))
                    safety_note = a.get("concurrency_note") or ("SAFE" if safe_val else "SERIALIZED")
                    print(f"{tid:<12} {agent:<20} {model:<22} {effort:<8} {group:<18} {str(safety_note):<14} {mode}")
        else:
            print(json.dumps(res, indent=2))

    elif args.command in ("next-ready", "next_ready", "ready"):
        res = client.get_ready_tasks()
        if "error" in res:
            print(json.dumps(res, indent=2))
            sys.exit(1)
        if args.format == "text" and not args.json:
            ready = res.get("ready_tasks", [])
            blocked = res.get("blocked_tasks", [])
            print(f"=== Ready Tasks ({len(ready)}) ===")
            for t in ready:
                print(f"  [{t.get('task_id')}] agent={t.get('agent_type')} model={t.get('model')} group={t.get('parallel_group')} scope={t.get('scope', '')}")
            if res.get("can_fan_out"):
                print(f"  => Parallel Fan-Out Available: group={res.get('fan_out_group')}")
            print(f"\n=== Blocked Tasks ({len(blocked)}) ===")
            for t in blocked:
                print(f"  [{t.get('task_id')}] agent={t.get('agent_type')} waiting_for={','.join(t.get('waiting_for', []))}")
        else:
            print(json.dumps(res, indent=2))

    elif args.command in ("analytics", "model-analytics"):
        res = client.get_model_analytics()
        if "error" in res:
            print(json.dumps(res, indent=2))
            sys.exit(1)
        if args.format == "text" and not args.json:
            summary = res.get("summary", {})
            print("=== Model Analytics Summary ===")
            print(f"Total Spend:    ${summary.get('total_spend_usd', 0.0):.4f} ({summary.get('total_spend_vnd', 0):,} VND)")
            print(f"Total Saved:    ${summary.get('total_saved_usd', 0.0):.4f} ({summary.get('total_saved_vnd', 0):,} VND)")
            print(f"Most Used:      {summary.get('most_used_model', '-')}")
            print(f"Highest Cost:   {summary.get('highest_cost_model', '-')}")
            print("\n=== Per-Model Breakdown ===")
            models = res.get("models", {})
            for m_id, s in models.items():
                print(f"  {m_id:<22}: {s.get('task_count', 0):>3} tasks | {s.get('total_tokens', 0):>12,} tokens | Hit Rate: {s.get('cache_hit_rate', 0):>5.1f}% | Cost: ${s.get('cost_usd', 0.0):>9.4f}")
        else:
            print(json.dumps(res, indent=2))

    elif args.command in ("export", "audit-export", "export-audit"):
        res = client.export_audit(format=args.format, out_path=args.output)
        if isinstance(res, dict) and "error" in res:
            print(json.dumps(res, indent=2), file=sys.stderr)
            sys.exit(1)
        if not args.output:
            if isinstance(res, (dict, list)):
                print(json.dumps(res, indent=2))
            else:
                print(res)
        else:
            print(f"Audit report successfully exported to {args.output}")

    elif args.command in ("desktop-status", "desktop-doctor"):
        res = client.desktop_status(
            driver=args.driver,
            target_os=args.target_os,
            app_path=args.app_path,
        )
        if "error" in res:
            print(json.dumps(res, indent=2))
            sys.exit(1)
        if args.format == "text" and not args.json:
            d = res.get("desktop", res)
            print("=== Gemini Desktop Worker Status ===")
            print(f"OS Platform:   {d.get('os_platform', '-')}")
            print(f"Active Driver: {d.get('driver_name', '-')}")
            print(f"Ready:         {d.get('ready', False)}")
            print(f"App Detected:  {d.get('app_detected', False)}")
            print(f"App Name:      {d.get('app_name') or '-'}")
            print(f"App Path:      {d.get('app_path') or '-'}")
            print(f"Bundle ID:     {d.get('bundle_id') or '-'}")
            print(f"App Version:   {d.get('app_version') or '-'}")
            print(f"App Running:   {d.get('app_running', False)}")
            perms = d.get("permissions") or {}
            perm_str = ", ".join(f"{k}={v}" for k, v in perms.items()) if perms else "-"
            print(f"Permissions:   {perm_str}")
            print(f"Queue Depth:   {res.get('queue_depth', d.get('queue_depth', 0))}")
            print(f"Lock Busy:     {d.get('lock_busy', False)}")
            print(f"Quota Saved:   ${res.get('quota_saved_usd', 0.0):.4f} ({res.get('quota_saved_vnd', 0):,} VND)")
            print("Supported Modes: task (default), chat")
            if d.get("warnings"):
                print("Warnings:")
                for w in d["warnings"]:
                    print(f"  - {w}")
            if d.get("remediation_steps"):
                print("Setup / Remediation Hints:")
                for step in d["remediation_steps"]:
                    print(f"  * {step}")
        else:
            print(json.dumps(res, indent=2))

    elif args.command in ("desktop-dispatch", "desktop-ask"):
        parts: list[str] = []
        if args.prompt:
            parts.append(args.prompt)
        if args.prompt_file:
            try:
                with open(args.prompt_file, "r", encoding="utf-8") as f:
                    parts.append(f.read())
            except Exception as e:
                print(json.dumps({"error": f"Failed to read --prompt-file '{args.prompt_file}': {e}"}, indent=2))
                sys.exit(1)
        if args.context_file:
            for ctx_path in args.context_file:
                try:
                    with open(ctx_path, "r", encoding="utf-8") as f:
                        parts.append(f"--- CONTEXT FILE: {ctx_path} ---\n{f.read()}")
                except Exception as e:
                    print(json.dumps({"error": f"Failed to read --context-file '{ctx_path}': {e}"}, indent=2))
                    sys.exit(1)

        full_prompt = "\n\n".join(p for p in parts if p and p.strip())
        if not full_prompt.strip():
            print(json.dumps({"error": "Must provide --prompt, --prompt-file, or --context-file"}, indent=2))
            sys.exit(2)

        eff_mode = (args.mode or "task").strip().lower()
        if args.no_workspace or eff_mode == "chat":
            resolved_workspace = None
        elif args.workspace:
            resolved_workspace = os.path.abspath(os.path.expanduser(args.workspace))
        else:
            resolved_workspace = os.getcwd()

        metadata = {"agent_type": args.agent} if args.agent else None
        res = client.desktop_dispatch(
            prompt=full_prompt,
            task_id=args.task,
            driver=args.driver,
            timeout_sec=args.timeout,
            output_path=args.output,
            redact_secrets=not args.no_redact,
            strict_secrets=args.strict_secrets,
            restore_clipboard=not args.no_restore_clipboard,
            new_chat=not args.no_new_chat,
            async_mode=args.async_mode,
            target_os=args.target_os,
            app_path=args.app_path,
            metadata=metadata,
            mode=eff_mode,
            workspace_path=resolved_workspace,
            no_workspace=args.no_workspace,
            background=args.background,
            allow_edits=bool(args.allow_edits),
        )
        if "error" in res:
            print(json.dumps(res, indent=2))
            sys.exit(1)
        if args.format == "text" and not args.json:
            job = res.get("job", res)
            job_mode = job.get("mode") or eff_mode or "task"
            job_ws = job.get("workspace_path") if "workspace_path" in job else resolved_workspace
            ws_display = f"{job_ws} (attached)" if job_ws else "none"
            is_bg = bool(job.get("background", args.background))
            exec_display = "background (silent)" if is_bg else "foreground"
            is_edits = bool(job.get("allow_edits", args.allow_edits))
            print("=== Desktop Worker Dispatch ===")
            print(f"Job ID:            {job.get('job_id', '-')}")
            print(f"Status:            {job.get('status', res.get('status', '-'))}")
            print(f"Mode: {job_mode} | Workspace: {ws_display} | Allow Edits: {is_edits}")
            print(f"Execution: {exec_display}")
            print(f"Driver / OS:       {job.get('driver_used') or job.get('driver_name', '-')} ({job.get('os_platform', '-')})")
            print(f"Artifact Path:     {job.get('artifact_path') or '-'}")
            print(f"Duration:          {job.get('duration_ms', 0)} ms")
            saved_usd = job.get("estimated_saved_usd", 0.0)
            saved_vnd = job.get("estimated_saved_vnd", 0)
            print(f"AGY Quota Saved:   ${saved_usd:.4f} ({saved_vnd:,} VND)")
            redactions = job.get("redactions") or {}
            red_count = sum(redactions.values()) if isinstance(redactions, dict) else job.get("redaction_count", 0)
            print(f"Redactions:        {red_count}")
            if job.get("error") or job.get("error_message"):
                print(f"Error:             {job.get('error') or job.get('error_message')}")
            if job.get("summary_excerpt"):
                print(f"\n--- Summary Excerpt ---\n{job['summary_excerpt']}")
        else:
            print(json.dumps(res, indent=2))

    elif args.command == "desktop-jobs":
        res = client.desktop_jobs(
            job_id=args.job_id,
            status=args.status,
            limit=args.limit,
        )
        if "error" in res:
            print(json.dumps(res, indent=2))
            sys.exit(1)
        if args.format == "text" and not args.json:
            summary = res.get("summary", {})
            jobs = res.get("jobs", [])
            print(f"=== Desktop Jobs ({len(jobs)}) ===")
            if summary:
                print(
                    f"Total: {summary.get('total', len(jobs))} | "
                    f"Completed: {summary.get('completed', 0)} | "
                    f"Total Saved: ${summary.get('total_saved_usd', 0.0):.4f}"
                )
            for j in jobs:
                j_mode = j.get("mode") or "task"
                j_ws = j.get("workspace_path")
                j_ws_display = f"{j_ws} (attached)" if j_ws else "none"
                print(
                    f"  [{j.get('job_id', '-')}] status={j.get('status', '-')} "
                    f"Mode: {j_mode} | Workspace: {j_ws_display} "
                    f"driver={j.get('driver_name', '-')} task={j.get('task_id') or '-'} "
                    f"saved=${j.get('estimated_saved_usd', 0.0):.4f} "
                    f"artifact={j.get('artifact_path') or '-'}"
                )
        else:
            print(json.dumps(res, indent=2))

    elif args.command == "desktop-cancel":
        target_job_id = args.job_id or args.pos_job_id
        if not target_job_id:
            print(json.dumps({"error": "Missing job_id: provide --job-id or positional job_id"}, indent=2))
            sys.exit(2)
        res = client.desktop_cancel(job_id=target_job_id)
        if "error" in res:
            print(json.dumps(res, indent=2))
            sys.exit(1)
        if args.format == "text" and not args.json:
            job = res.get("job", res)
            print(f"Cancelled desktop job {job.get('job_id', target_job_id)}: status={job.get('status', 'cancelled')}")
        else:
            print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
