#!/usr/bin/env python3
"""
Multi-Agent Orchestrator Client
Python library and CLI utility for sending telemetry, task updates, and logs to the Orchestrator Server.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_BASE_URL = os.environ.get("ORCHESTRATOR_URL", "http://localhost:8484").rstrip("/")


class OrchestratorClient:
    """Client for interacting with the Multi-Agent Orchestrator Server."""

    def __init__(self, base_url: str = None):
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
        progress: int = None,
        scope: str = None,
        notes: str = None,
        conv_id: str = None,
        model: str = None,
        complexity: str = None,
        depends_on: list = None,
        parallel_group: str = None,
        input_tokens: int = None,
        output_tokens: int = None,
        cache_tokens: int = None,
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

        return self._post("/api/tasks", payload)

    def kill_task(self, task_id: str, reason: str = None) -> dict:
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
    update_parser.add_argument("--model", type=str, default=None, help="Assigned Model (e.g. gemini-4-argon, pro, gemini-3.8-flash, flash, flash_lite)")
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

    args = parser.parse_args()
    client = OrchestratorClient(base_url=args.url)

    if args.command == "kill":
        res = client.kill_task(task_id=args.task, reason=args.reason)
        print(json.dumps(res, indent=2))
        if "error" in res:
            sys.exit(1)

    elif args.command == "update":
        # Auto-detect conversation ID and token metrics if not explicitly passed
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


if __name__ == "__main__":
    main()
