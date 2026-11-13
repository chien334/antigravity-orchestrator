#!/usr/bin/env python3
"""
Multi-Agent Orchestrator Client
Python library and CLI utility for sending telemetry, task updates, and logs to the Orchestrator Server.
Features Gemini 4 Carbon and Gemini 4 Hydrogen evolution: 5-tier smart model routing, Circuit Breaker escalation, DAG ready-queue querying, model analytics, and audit exporting.
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Union
import urllib.error
import urllib.request

DEFAULT_BASE_URL = os.environ.get("ORCHESTRATOR_URL", "http://localhost:8484").rstrip("/")


class OrchestratorClient:
    """Client for interacting with the Multi-Agent Orchestrator Server."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")

    def _post(self, path: str, payload: dict) -> dict:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as e:
            return {"error": f"Failed to connect to Orchestrator at {url}: {e}"}

    def _get(self, path: str) -> dict:
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as e:
            return {"error": f"Failed to connect to Orchestrator at {url}: {e}"}

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
        **kwargs,
    ) -> dict:
        """Call POST /api/router/recommend to dynamically recommend model and reasoning effort."""
        files = kwargs.get("files", file_count)
        sec_impact = kwargs.get("security_impact", has_security_impact)
        retries = kwargs.get("retries", retry_count)
        payload = {
            "agent_type": agent_type,
            "complexity": complexity,
            "scope": scope,
            "file_count": files,
            "has_security_impact": sec_impact,
            "budget_mode": budget_mode,
            "retry_count": retries,
        }
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
        **kwargs,
    ) -> dict:
        """Alias for recommend_model matching plan specification."""
        file_count = kwargs.get("file_count", files)
        has_sec = kwargs.get("has_security_impact", security_impact)
        retries = kwargs.get("retries", retry_count)
        return self.recommend_model(
            agent_type=agent_type,
            complexity=complexity,
            scope=scope,
            file_count=file_count,
            has_security_impact=has_sec,
            budget_mode=budget_mode,
            retry_count=retries,
            **kwargs,
        )

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
        help="Assigned Model (e.g. gemini-4-carbon, carbon, gemini-4-argon, pro, gemini-4-hydrogen, hydrogen, gemini-3.8-flash, flash, flash_lite)",
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
    recommend_parser.add_argument("--agent", required=True, help="Agent persona name (e.g. security-auditor, builder, spec-engineer)")
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
        choices=["balanced", "quality_first", "speed_first", "latency_sensitive", "cost_saving"],
        help="Routing optimization mode (balanced, quality_first, speed_first, latency_sensitive, cost_saving, default: balanced)",
    )
    recommend_parser.add_argument(
        "--retry-count",
        "--retries",
        dest="retry_count",
        type=int,
        default=0,
        help="Prior failure retry count for Circuit Breaker escalation (default: 0)",
    )
    recommend_parser.add_argument("--json", action="store_true", help="Output raw JSON response")
    recommend_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (json, text, default: json)",
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
            print(f"{'Model':<24} {'Tier':<18} {'Rates ($ in/out/cache per 1M)':<32} {'Reasoning Efforts':<26}")
            print("-" * 102)
            for m_id, m_data in models.items():
                rates = m_data.get("rates", {})
                rate_str = f"${rates.get('in', 0):.3f} / ${rates.get('out', 0):.2f} / ${rates.get('cache', 0):.4f}"
                efforts = ", ".join(m_data.get("supported_reasoning_efforts", [])) or "None"
                print(f"{m_id:<24} {m_data.get('tier', ''):<18} {rate_str:<32} {efforts:<26}")
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
            print(f"Cost Tier:         {rec.get('estimated_cost_tier', '-')}")
            print(f"Fallback Model:    {rec.get('fallback_model', '-')}")
            if rec.get("circuit_breaker"):
                cb = rec["circuit_breaker"]
                cb_status = str(cb.get("status", "unknown")).upper()
                if cb.get("status") == "tripped":
                    print(f"Circuit Breaker:   TRIPPED (retries: {cb.get('retries', 0)}, escalated from: {cb.get('escalated_from', 'gemini-4-hydrogen')})")
                elif cb.get("status") == "retrying":
                    print(f"Circuit Breaker:   RETRYING (retry #{cb.get('retry_count', 1)}, escalating to: {cb.get('escalate_to', 'gemini-4-carbon')})")
                else:
                    print(f"Circuit Breaker:   {cb_status} (retries: {cb.get('retry_count', 0)})")
            print(f"Rationale:         {rec.get('rationale', '')}")
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


if __name__ == "__main__":
    main()
