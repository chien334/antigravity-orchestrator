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

    # state
    subparsers.add_parser("state", help="Get current orchestrator state")

    # reset
    subparsers.add_parser("reset", help="Reset all orchestrator tasks and logs")

    args = parser.parse_args()
    client = OrchestratorClient(base_url=args.url)

    if args.command == "update":
        res = client.update_task(
            task_id=args.task,
            agent_type=args.agent,
            status=args.status,
            progress=args.progress,
            scope=args.scope,
            notes=args.notes,
            conv_id=args.conv_id,
            model=args.model,
            complexity=args.complexity,
            depends_on=args.depends_on,
            parallel_group=args.parallel_group,
            input_tokens=args.input_tokens,
            output_tokens=args.output_tokens,
            cache_tokens=args.cache_tokens,
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
