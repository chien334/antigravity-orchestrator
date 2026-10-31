#!/usr/bin/env python3
"""
Automated Test Suite for Orchestrator Dashboard Server & Client
Tests HTTP endpoints, SSE event streams, StateStore, OrchestratorClient API, and CLI.
"""

import json
import os
import subprocess
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.client import HTTPConnection
from pathlib import Path

# Add repo root and orchestrator package to path
REPO_ROOT = Path(__file__).resolve().parent.parent
if (REPO_ROOT / "packages" / "orchestrator").exists():
    ORCH_DIR = REPO_ROOT / "packages" / "orchestrator"
elif (REPO_ROOT / "tools" / "orchestrator").exists():
    ORCH_DIR = REPO_ROOT / "tools" / "orchestrator"
else:
    ORCH_DIR = REPO_ROOT

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(ORCH_DIR))

from server import GLOBAL_STORE, OrchestratorHandler, ThreadingHTTPServer
from client import OrchestratorClient

TEST_PORT = 8585
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"


class OrchestratorTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Reset store
        GLOBAL_STORE.reset()
        # Bind server on test port
        cls.server = ThreadingHTTPServer(("127.0.0.1", TEST_PORT), OrchestratorHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        # Wait a short moment for the server to accept connections
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join(timeout=2.0)

    def setUp(self):
        # Reset state store before each test
        GLOBAL_STORE.reset()


class TestDashboardAndREST(OrchestratorTestBase):
    """Verify HTTP GET / and REST API endpoints."""

    def test_get_dashboard_html(self):
        """GET / and GET /index.html: verify 200, Content-Type, and UI content."""
        for path in ["/", "/index.html"]:
            url = f"{BASE_URL}{path}"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as response:
                self.assertEqual(response.status, 200)
                content_type = response.headers.get("Content-Type", "")
                self.assertIn("text/html", content_type)
                body = response.read().decode("utf-8")
                self.assertIn("Hospital Suite - Multi-Agent Orchestrator", body)
                self.assertIn("Live Tasks Status", body)
                self.assertIn("Live Agent Telemetry", body)
                self.assertIn("Pipeline Stage Visualizer", body)
                self.assertIn("connectSSE", body)

    def test_cors_headers(self):
        """OPTIONS /api/tasks: verify CORS preflight headers."""
        url = f"{BASE_URL}/api/tasks"
        req = urllib.request.Request(url, method="OPTIONS")
        with urllib.request.urlopen(req, timeout=5) as response:
            self.assertEqual(response.status, 204)
            self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "*")
            self.assertIn("POST", response.headers.get("Access-Control-Allow-Methods", ""))

    def test_post_tasks_and_get_state(self):
        """POST /api/tasks registers task, GET /api/state reflects updated state and metrics."""
        task_payload = {
            "task_id": "TASK-01",
            "agent_type": "builder",
            "model": "gemini-4-argon",
            "complexity": "high",
            "parallel_group": "BUILD-PARALLEL",
            "depends_on": ["TASK-PRE-01"],
            "input_tokens": 1500,
            "output_tokens": 300,
            "cache_tokens": 4200,
            "status": "running",
            "progress": 45,
            "scope": "Frontend Components",
            "notes": "Building patient admission form",
            "conv_id": "conv-1234",
        }
        req = urllib.request.Request(
            f"{BASE_URL}/api/tasks",
            data=json.dumps(task_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            self.assertEqual(response.status, 200)
            data = json.loads(response.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "ok")
            task = data.get("task", {})
            self.assertEqual(task.get("task_id"), "TASK-01")
            self.assertEqual(task.get("agent_type"), "builder")
            self.assertEqual(task.get("model"), "gemini-4-argon")
            self.assertEqual(task.get("complexity"), "high")
            self.assertEqual(task.get("parallel_group"), "BUILD-PARALLEL")
            self.assertEqual(task.get("depends_on"), ["TASK-PRE-01"])
            self.assertEqual(task.get("tokens"), {"input": 1500, "output": 300, "cache": 4200, "total": 6000})
            self.assertEqual(task.get("status"), "running")
            self.assertEqual(task.get("progress"), 45)
            self.assertEqual(task.get("notes"), "Building patient admission form")
            self.assertIn("updated_at", task)

        # Verify GET /api/state
        req = urllib.request.Request(f"{BASE_URL}/api/state", method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            self.assertEqual(response.status, 200)
            state = json.loads(response.read().decode("utf-8"))
            self.assertEqual(len(state["tasks"]), 1)
            self.assertEqual(state["tasks"][0]["task_id"], "TASK-01")
            self.assertEqual(state["tasks"][0]["parallel_group"], "BUILD-PARALLEL")
            self.assertEqual(state["tasks"][0]["depends_on"], ["TASK-PRE-01"])
            self.assertEqual(state["tasks"][0]["tokens"]["total"], 6000)

            metrics = state["metrics"]
            self.assertEqual(metrics["total"], 1)
            self.assertEqual(metrics["running"], 1)
            self.assertEqual(metrics["pending"], 0)
            self.assertEqual(metrics["completed"], 0)
            self.assertEqual(metrics["blocked"], 0)
            self.assertEqual(metrics["active_agents"], 1)
            self.assertEqual(metrics["parallel_running"], 1)
            self.assertEqual(metrics["active_groups"], ["BUILD-PARALLEL"])
            self.assertEqual(metrics["total_input_tokens"], 1500)
            self.assertEqual(metrics["total_output_tokens"], 300)
            self.assertEqual(metrics["total_cache_tokens"], 4200)
            self.assertEqual(metrics["grand_total_tokens"], 6000)
            self.assertGreater(metrics["cache_rate"], 0.0)

    def test_post_logs(self):
        """POST /api/logs appends a log entry, verified in /api/state."""
        log_payload = {
            "task_id": "TASK-01",
            "agent_type": "tester",
            "level": "warn",
            "message": "Encountered slow query response",
        }
        req = urllib.request.Request(
            f"{BASE_URL}/api/logs",
            data=json.dumps(log_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            self.assertEqual(response.status, 200)
            data = json.loads(response.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "ok")
            log = data.get("log", {})
            self.assertEqual(log.get("task_id"), "TASK-01")
            self.assertEqual(log.get("agent_type"), "tester")
            self.assertEqual(log.get("level"), "warn")
            self.assertEqual(log.get("message"), "Encountered slow query response")
            self.assertIn("timestamp", log)

        # State check
        req = urllib.request.Request(f"{BASE_URL}/api/state", method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            state = json.loads(response.read().decode("utf-8"))
            self.assertEqual(len(state["logs"]), 1)
            self.assertEqual(state["logs"][0]["message"], "Encountered slow query response")

    def test_progress_clamping_and_task_updates(self):
        """Verify progress values < 0 clamped to 0 and > 100 clamped to 100."""
        # Progress < 0
        req = urllib.request.Request(
            f"{BASE_URL}/api/tasks",
            data=json.dumps({"task_id": "TASK-CLAMP", "status": "pending", "progress": -10}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            self.assertEqual(data["task"]["progress"], 0)

        # Progress > 100
        req = urllib.request.Request(
            f"{BASE_URL}/api/tasks",
            data=json.dumps({"task_id": "TASK-CLAMP", "progress": 150}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            self.assertEqual(data["task"]["progress"], 100)

    def test_validation_and_error_handling(self):
        """Verify 400 Bad Request on missing task_id or invalid JSON, and 404 for unknown endpoints."""
        # Missing task_id
        req = urllib.request.Request(
            f"{BASE_URL}/api/tasks",
            data=json.dumps({"agent_type": "builder"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=5)
        self.assertEqual(ctx.exception.code, 400)
        ctx.exception.close()

        # Malformed JSON
        req = urllib.request.Request(
            f"{BASE_URL}/api/tasks",
            data=b"not-json",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=5)
        self.assertEqual(ctx.exception.code, 400)
        ctx.exception.close()

        # 404 GET
        req = urllib.request.Request(f"{BASE_URL}/api/nonexistent", method="GET")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=5)
        self.assertEqual(ctx.exception.code, 404)
        ctx.exception.close()

        # 404 POST
        req = urllib.request.Request(f"{BASE_URL}/api/nonexistent", data=b"{}", method="POST")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=5)
        self.assertEqual(ctx.exception.code, 404)
        ctx.exception.close()

    def test_reset_endpoint(self):
        """POST /api/reset resets all state and logs."""
        GLOBAL_STORE.upsert_task("T1", "agent", "running")
        GLOBAL_STORE.append_log("T1", "agent", "info", "log message")

        req = urllib.request.Request(f"{BASE_URL}/api/reset", data=b"{}", method="POST")
        with urllib.request.urlopen(req, timeout=5) as response:
            self.assertEqual(response.status, 200)
            data = json.loads(response.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "ok")
            self.assertEqual(data["metrics"]["total"], 0)

        state = GLOBAL_STORE.get_state()
        self.assertEqual(len(state["tasks"]), 0)
        self.assertEqual(len(state["logs"]), 0)


class TestOrchestratorClient(OrchestratorTestBase):
    """Verify OrchestratorClient python library methods and CLI execution."""

    def test_client_python_methods(self):
        """Test OrchestratorClient Python methods: update_task, log, get_state, reset."""
        client = OrchestratorClient(base_url=BASE_URL)

        # 1. update_task
        res = client.update_task(
            task_id="TASK-PY-01",
            agent_type="architect",
            status="running",
            progress=30,
            scope="Design Data Pipeline",
            notes="Schema draft complete",
            conv_id="conv-py",
        )
        self.assertEqual(res.get("status"), "ok")
        self.assertEqual(res["task"]["task_id"], "TASK-PY-01")
        self.assertEqual(res["task"]["agent_type"], "architect")

        # 2. log
        res_log = client.log(
            task_id="TASK-PY-01",
            agent_type="architect",
            level="thought",
            message="Evaluating trade-offs between SSE and WebSockets",
        )
        self.assertEqual(res_log.get("status"), "ok")
        self.assertEqual(res_log["log"]["level"], "thought")

        # 3. get_state
        state = client.get_state()
        self.assertEqual(len(state["tasks"]), 1)
        self.assertEqual(state["tasks"][0]["task_id"], "TASK-PY-01")
        self.assertEqual(len(state["logs"]), 1)
        self.assertEqual(state["metrics"]["running"], 1)

        # 4. reset
        res_reset = client.reset()
        self.assertEqual(res_reset.get("status"), "ok")
        state_after = client.get_state()
        self.assertEqual(len(state_after["tasks"]), 0)

    def test_client_connection_error_handling(self):
        """Test client gracefully returns error dict when target server is unreachable."""
        bad_client = OrchestratorClient(base_url="http://127.0.0.1:59999")
        res = bad_client.get_state()
        self.assertIn("error", res)

    def test_client_cli_commands(self):
        """Test Orchestrator CLI commands: update, log, state, reset via subprocess."""
        cli_path = str(ORCH_DIR / "client.py")

        # 1. CLI update
        cmd_update = [
            sys.executable,
            cli_path,
            "--url",
            BASE_URL,
            "update",
            "--task",
            "TASK-CLI-01",
            "--agent",
            "reviewer",
            "--model",
            "gemini-4-argon",
            "--complexity",
            "high",
            "--depends-on",
            "TASK-01,TASK-02",
            "--group",
            "AUDIT-FANOUT",
            "--input-tokens",
            "2400",
            "--output-tokens",
            "450",
            "--cache-tokens",
            "6000",
            "--status",
            "running",
            "--progress",
            "60",
            "--scope",
            "Security Review",
            "--notes",
            "Running bandit static scan",
        ]
        result = subprocess.run(cmd_update, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data["task"]["task_id"], "TASK-CLI-01")
        self.assertEqual(data["task"]["model"], "gemini-4-argon")
        self.assertEqual(data["task"]["complexity"], "high")
        self.assertEqual(data["task"]["parallel_group"], "AUDIT-FANOUT")
        self.assertEqual(data["task"]["depends_on"], ["TASK-01", "TASK-02"])
        self.assertEqual(data["task"]["tokens"], {"input": 2400, "output": 450, "cache": 6000, "total": 8850})

        # 2. CLI log
        cmd_log = [
            sys.executable,
            cli_path,
            "--url",
            BASE_URL,
            "log",
            "--task",
            "TASK-CLI-01",
            "--agent",
            "reviewer",
            "--level",
            "warn",
            "--message",
            "Found dependency alert in yarn.lock",
        ]
        result = subprocess.run(cmd_log, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data["log"]["level"], "warn")

        # 3. CLI state
        cmd_state = [sys.executable, cli_path, "--url", BASE_URL, "state"]
        result = subprocess.run(cmd_state, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        self.assertEqual(len(data["tasks"]), 1)
        self.assertEqual(data["tasks"][0]["task_id"], "TASK-CLI-01")
        self.assertEqual(len(data["logs"]), 1)
        self.assertEqual(data["metrics"]["total"], 1)

        # 4. CLI reset
        cmd_reset = [sys.executable, cli_path, "--url", BASE_URL, "reset"]
        result = subprocess.run(cmd_reset, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        self.assertEqual(data.get("status"), "ok")

        # Verify state is cleared
        state = GLOBAL_STORE.get_state()
        self.assertEqual(len(state["tasks"]), 0)


class TestOrchestratorSSE(OrchestratorTestBase):
    """Verify Server-Sent Events stream: initial_state and real-time task_update / log_event."""

    def test_sse_stream_initial_state_and_live_updates(self):
        """Connect to /events, verify receipt of initial_state followed by task_update event."""
        # Prepopulate one task
        GLOBAL_STORE.upsert_task("TASK-PRE", "spec", "completed", 100)

        conn = HTTPConnection("127.0.0.1", TEST_PORT, timeout=5)
        conn.request("GET", "/events")
        response = conn.getresponse()

        self.assertEqual(response.status, 200)
        self.assertIn("text/event-stream", response.getheader("Content-Type", ""))

        # Read initial_state event
        # Format:
        # event: initial_state\n
        # data: {...}\n\n
        line1 = response.fp.readline().decode("utf-8").strip()
        line2 = response.fp.readline().decode("utf-8").strip()
        _empty = response.fp.readline().decode("utf-8")  # blank separator line

        self.assertEqual(line1, "event: initial_state")
        self.assertTrue(line2.startswith("data: "))
        init_data = json.loads(line2[len("data: ") :])
        self.assertEqual(len(init_data["tasks"]), 1)
        self.assertEqual(init_data["tasks"][0]["task_id"], "TASK-PRE")

        # In a separate thread, trigger a task update
        def trigger_update():
            time.sleep(0.05)
            GLOBAL_STORE.upsert_task("TASK-LIVE", "tester", "running", 75, notes="Live event test")

        t = threading.Thread(target=trigger_update)
        t.start()

        # Read task_update event from stream
        ev_line = response.fp.readline().decode("utf-8").strip()
        data_line = response.fp.readline().decode("utf-8").strip()
        _empty = response.fp.readline().decode("utf-8")

        self.assertEqual(ev_line, "event: task_update")
        self.assertTrue(data_line.startswith("data: "))
        update_data = json.loads(data_line[len("data: ") :])
        self.assertEqual(update_data["task"]["task_id"], "TASK-LIVE")
        self.assertEqual(update_data["task"]["progress"], 75)
        self.assertEqual(update_data["metrics"]["total"], 2)

        t.join()
        conn.close()


class TestSQLitePersistence(unittest.TestCase):
    """Verify SQLite database persistence across independent store instances."""

    def test_sqlite_persistence_across_instances(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            tmp_db = f.name

        try:
            from server import StateStore
            # Instance 1: write task and log
            store1 = StateStore(db_path=tmp_db)
            task = store1.upsert_task(
                task_id="SQL-01",
                agent_type="security-auditor",
                model="gemini-4-argon",
                complexity="high",
                parallel_group="SEC-GROUP",
                depends_on=["SQL-PRE"],
                input_tokens=1200,
                output_tokens=400,
                cache_tokens=3000,
                status="completed",
                progress=100,
                scope="Security Scan",
                notes="Zero vulnerabilities found",
            )
            store1.append_log(task_id="SQL-01", agent_type="security-auditor", level="info", message="Scan complete")

            # Instance 2: reopen same SQLite database
            store2 = StateStore(db_path=tmp_db)
            state = store2.get_state()
            self.assertEqual(len(state["tasks"]), 1)
            t = state["tasks"][0]
            self.assertEqual(t["task_id"], "SQL-01")
            self.assertEqual(t["agent_type"], "security-auditor")
            self.assertEqual(t["model"], "gemini-4-argon")
            self.assertEqual(t["complexity"], "high")
            self.assertEqual(t["status"], "completed")
            self.assertEqual(t["progress"], 100)
            self.assertEqual(t["parallel_group"], "SEC-GROUP")
            self.assertEqual(t["depends_on"], ["SQL-PRE"])
            self.assertEqual(t["tokens"]["input"], 1200)
            self.assertEqual(t["tokens"]["output"], 400)
            self.assertEqual(t["tokens"]["cache"], 3000)
            self.assertEqual(t["tokens"]["total"], 4600)

            # Check logs
            self.assertEqual(len(state["logs"]), 1)
            self.assertEqual(state["logs"][0]["message"], "Scan complete")

            # Check metrics
            metrics = state["metrics"]
            self.assertEqual(metrics["completed"], 1)
            self.assertEqual(metrics["total_input_tokens"], 1200)
            self.assertEqual(metrics["total_output_tokens"], 400)
            self.assertEqual(metrics["total_cache_tokens"], 3000)
            self.assertEqual(metrics["grand_total_tokens"], 4600)
        finally:
            if os.path.exists(tmp_db):
                os.remove(tmp_db)


def run_tests():
    """Run all test suites and output results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestDashboardAndREST))
    suite.addTests(loader.loadTestsFromTestCase(TestOrchestratorClient))
    suite.addTests(loader.loadTestsFromTestCase(TestOrchestratorSSE))
    suite.addTests(loader.loadTestsFromTestCase(TestSQLitePersistence))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
