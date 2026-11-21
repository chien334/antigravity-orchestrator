#!/usr/bin/env python3
"""
Comprehensive Automated Test Suite for Conditional 60% Gemini Desktop App Peer Routing.
Validates:
1. Conditional Gate (desktop_available=False -> 100% Pure API; desktop_available=True -> Peer Routing
   with allow_edits=False on read-only personas, allow_edits=True on mutating personas,
   Rule 1 Security strictly locked on Gemini 4 Carbon high, and Rule 2 retries on fast API)
2. 60% Target Share Cap, Queue-Busy Spillover & api_only Budget Guardrail
3. allocate_dag_models() Batch 60/40 Splitter & Parallel-Group Mutex Safety (<= 1 Desktop task per wave)
4. Live Ephemeral Server (POST /api/router/allocate-dag apply=True, _get_cached_desktop_status
   auto-detection on POST /api/router/recommend, Dashboard #desktop-share-badge & CLI allocate-dag)
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
ORCH_DIR = REPO_ROOT / "packages" / "orchestrator"

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(ORCH_DIR))

from client import OrchestratorClient, format_preflight_text
from router import allocate_dag_models, is_task_desktop_eligible, recommend_model
from server import (
    GLOBAL_STORE,
    OrchestratorHandler,
    ThreadingHTTPServer,
)


class TestConditionalGateAndGuardrails(unittest.TestCase):
    """1. Conditional Gate (desktop_available=False vs True), allow_edits, Rule 1 & Rule 2."""

    def test_desktop_unavailable_routes_100_percent_pure_api(self):
        """When desktop_available=False, 100% of tasks match pure API (Neon/Hydrogen/Carbon/Flash) with zero desktop assignments."""
        cases = [
            # (kwargs, expected_model, expected_effort)
            ({"agent_type": "spec-engineer", "complexity": "high"}, "gemini-4-neon", "high"),
            ({"agent_type": "task-planner", "complexity": "high"}, "gemini-4-neon", "medium"),
            ({"agent_type": "code-reviewer", "complexity": "high", "read_only": True}, "gemini-4-neon", "high"),
            ({"agent_type": "debugger", "complexity": "high"}, "gemini-4-neon", "high"),
            ({"agent_type": "builder", "complexity": "medium", "file_count": 2}, "gemini-4-hydrogen", "high"),
            ({"agent_type": "builder", "complexity": "medium", "file_count": 5}, "gemini-4-neon", "high"),
            ({"agent_type": "test-engineer", "complexity": "medium"}, "gemini-4-hydrogen", "high"),
            ({"agent_type": "code-simplifier", "complexity": "low"}, "gemini-3.8-flash", None),
            ({"agent_type": "doc-generator", "complexity": "low"}, "gemini-3.8-flash", None),
            ({"agent_type": "security-auditor", "complexity": "critical"}, "gemini-4-carbon", "high"),
            # Even when prefer_desktop / hybrid_desktop requested, desktop_available=False keeps API
            ({"agent_type": "spec-engineer", "complexity": "high", "budget_mode": "hybrid_desktop", "prefer_desktop": True}, "gemini-4-neon", "high"),
            ({"agent_type": "builder", "complexity": "medium", "budget_mode": "offload_heavy_to_desktop", "prefer_desktop": True}, "gemini-4-hydrogen", "high"),
        ]

        for kwargs, exp_model, exp_effort in cases:
            with self.subTest(kwargs=kwargs):
                rec = recommend_model(desktop_available=False, **kwargs)["recommendation"]
                self.assertEqual(rec["model"], exp_model)
                self.assertEqual(rec["recommended_model"], exp_model)
                self.assertEqual(rec["reasoning_effort"], exp_effort)
                self.assertNotEqual(rec["model"], "gemini-desktop-app")
                self.assertNotIn("desktop_execution", rec)

    def test_desktop_available_peer_routing_allow_edits_and_rule1_rule2_guardrails(self):
        """When desktop_available=True, eligible peers use gemini-desktop-app with persona-scoped allow_edits while Rule 1 & 2 stay locked on API."""
        # Read-only synthesis personas -> allow_edits=False
        for ro_agent in ("spec-engineer", "task-planner", "code-reviewer"):
            with self.subTest(read_only_agent=ro_agent):
                rec = recommend_model(
                    agent_type=ro_agent,
                    complexity="high",
                    desktop_available=True,
                )["recommendation"]
                self.assertEqual(rec["model"], "gemini-desktop-app")
                self.assertEqual(rec["recommended_model"], "gemini-desktop-app")
                self.assertEqual(rec["execution_mode"], "desktop_bridge")
                self.assertEqual(rec["estimated_cost_tier"], "$0")
                self.assertEqual(rec["fallback_model"], "gemini-4-neon")
                self.assertFalse(rec["allow_edits"])
                self.assertFalse(rec["desktop_execution"]["allow_edits"])

        # Mutating SWE personas -> allow_edits=True (when read_only=False)
        mutating_cases = [
            {"agent_type": "builder", "complexity": "medium", "file_count": 4},
            {"agent_type": "builder", "complexity": "medium", "current_desktop_share": 0.20},
            {"agent_type": "debugger", "complexity": "high"},
            {"agent_type": "test-engineer", "complexity": "medium", "current_desktop_share": 0.20},
        ]
        for kwargs in mutating_cases:
            with self.subTest(mutating_case=kwargs):
                rec = recommend_model(desktop_available=True, read_only=False, **kwargs)["recommendation"]
                self.assertEqual(rec["model"], "gemini-desktop-app")
                self.assertTrue(rec["allow_edits"])
                self.assertTrue(rec["desktop_execution"]["allow_edits"])

        # Explicit read_only=True forces allow_edits=False even for builder
        rec_ro_builder = recommend_model(
            agent_type="builder",
            complexity="high",
            desktop_available=True,
            read_only=True,
        )["recommendation"]
        self.assertEqual(rec_ro_builder["model"], "gemini-desktop-app")
        self.assertFalse(rec_ro_builder["allow_edits"])
        self.assertFalse(rec_ro_builder["desktop_execution"]["allow_edits"])

        # Rule 1 Security Guardrail strictly locked on gemini-4-carbon (high)
        sec_cases = [
            {"agent_type": "security-auditor", "complexity": "high"},
            {"agent_type": "builder", "complexity": "medium", "has_security_impact": True},
            {"agent_type": "spec-engineer", "complexity": "critical"},
            {"agent_type": "code-reviewer", "complexity": "high", "scope": "auth crypto owasp audit"},
        ]
        for kwargs in sec_cases:
            with self.subTest(security_case=kwargs):
                rec = recommend_model(
                    desktop_available=True,
                    prefer_desktop=True,
                    current_desktop_share=0.0,
                    **kwargs,
                )["recommendation"]
                self.assertEqual(rec["model"], "gemini-4-carbon")
                self.assertEqual(rec["reasoning_effort"], "high")
                self.assertFalse(is_task_desktop_eligible(budget_mode="hybrid_desktop", **kwargs))

        # Rule 2 Circuit Breaker retries stay on fast API (never offloaded to Desktop)
        cb1 = recommend_model(agent_type="spec-engineer", complexity="high", desktop_available=True, prefer_desktop=True, retry_count=1)["recommendation"]
        self.assertEqual(cb1["model"], "gemini-4-hydrogen")
        self.assertEqual(cb1["reasoning_effort"], "xhigh")
        self.assertEqual(cb1["circuit_breaker"]["stage"], 1)

        cb2 = recommend_model(agent_type="spec-engineer", complexity="high", desktop_available=True, prefer_desktop=True, retry_count=2)["recommendation"]
        self.assertEqual(cb2["model"], "gemini-4-neon")
        self.assertEqual(cb2["reasoning_effort"], "high")
        self.assertEqual(cb2["circuit_breaker"]["stage"], 2)

        cb3 = recommend_model(agent_type="spec-engineer", complexity="high", desktop_available=True, prefer_desktop=True, retry_count=3)["recommendation"]
        self.assertEqual(cb3["model"], "gemini-4-carbon")
        self.assertEqual(cb3["reasoning_effort"], "high")
        self.assertEqual(cb3["circuit_breaker"]["stage"], 3)


class TestShareCapAndQueueBusySpillover(unittest.TestCase):
    """2. 60% Target Share Cap, Queue-Busy Spillover & api_only Mode."""

    def test_under_target_promotes_and_over_target_or_busy_spills_over(self):
        """current_desktop_share=0.20 promotes to Desktop; 0.65 or desktop_queue_busy=True spills to API fallback."""
        # 1. Under 60% target & queue idle -> promotes eligible builder/test-engineer/spec-engineer to gemini-desktop-app
        for agent, expected_fb in [
            ("builder", "gemini-4-hydrogen"),
            ("test-engineer", "gemini-4-hydrogen"),
            ("spec-engineer", "gemini-4-neon"),
        ]:
            rec = recommend_model(
                agent_type=agent,
                complexity="medium",
                desktop_available=True,
                current_desktop_share=0.20,
                desktop_target_share=0.60,
                desktop_queue_busy=False,
            )["recommendation"]
            self.assertEqual(rec["model"], "gemini-desktop-app")
            self.assertEqual(rec["fallback_model"], expected_fb)
            self.assertEqual(rec["desktop_execution"]["target_share"], 0.6)
            self.assertEqual(rec["desktop_execution"]["current_share"], 0.2)

        # 2. current_desktop_share=0.65 (>= 0.60) -> spills over to API fallback
        rec_cap_spec = recommend_model(
            agent_type="spec-engineer",
            complexity="high",
            desktop_available=True,
            current_desktop_share=0.65,
            desktop_target_share=0.60,
            desktop_queue_busy=False,
        )["recommendation"]
        self.assertEqual(rec_cap_spec["model"], "gemini-4-neon")
        self.assertEqual(rec_cap_spec.get("desktop_spillover_reason"), "target_share_reached")

        rec_cap_bld = recommend_model(
            agent_type="builder",
            complexity="medium",
            file_count=2,
            desktop_available=True,
            current_desktop_share=0.65,
            desktop_target_share=0.60,
            desktop_queue_busy=False,
        )["recommendation"]
        self.assertEqual(rec_cap_bld["model"], "gemini-4-hydrogen")
        self.assertEqual(rec_cap_bld.get("desktop_spillover_reason"), "target_share_reached")

        # 3. desktop_queue_busy=True -> spills over immediately even when current_desktop_share=0.20
        rec_busy_spec = recommend_model(
            agent_type="spec-engineer",
            complexity="high",
            desktop_available=True,
            current_desktop_share=0.20,
            desktop_target_share=0.60,
            desktop_queue_busy=True,
        )["recommendation"]
        self.assertEqual(rec_busy_spec["model"], "gemini-4-neon")
        self.assertEqual(rec_busy_spec.get("desktop_spillover_reason"), "queue_busy")

        rec_busy_bld = recommend_model(
            agent_type="builder",
            complexity="medium",
            file_count=5,
            desktop_available=True,
            current_desktop_share=0.20,
            desktop_target_share=0.60,
            desktop_queue_busy=True,
        )["recommendation"]
        self.assertEqual(rec_busy_bld["model"], "gemini-4-neon")
        self.assertEqual(rec_busy_bld.get("desktop_spillover_reason"), "queue_busy")

    def test_budget_mode_api_only_forces_pure_api_even_when_desktop_ready(self):
        """budget_mode='api_only' suppresses Desktop routing even when desktop_available=True & prefer_desktop=True."""
        r_spec = recommend_model(
            agent_type="spec-engineer",
            complexity="high",
            budget_mode="api_only",
            desktop_available=True,
            prefer_desktop=True,
            current_desktop_share=0.0,
        )["recommendation"]
        self.assertEqual(r_spec["model"], "gemini-4-neon")

        r_bld = recommend_model(
            agent_type="builder",
            complexity="medium",
            file_count=2,
            budget_mode="api_only",
            desktop_available=True,
            prefer_desktop=True,
            current_desktop_share=0.0,
        )["recommendation"]
        self.assertEqual(r_bld["model"], "gemini-4-hydrogen")


class TestAllocateDagModels6040AndMutex(unittest.TestCase):
    """3. allocate_dag_models() Batch 60/40 Splitter & Parallel-Group Mutex Safety."""

    @staticmethod
    def _sample_10_task_swe_dag() -> list[dict]:
        return [
            {"task_id": "T-SPEC", "agent_type": "spec-engineer", "complexity": "high", "scope": "Draft architecture spec"},
            {"task_id": "T-PLAN", "agent_type": "task-planner", "complexity": "high", "scope": "Plan DAG waves"},
            {"task_id": "T-BLD-1", "agent_type": "builder", "complexity": "medium", "file_count": 4, "parallel_group": "BUILD-PARALLEL", "scope": "Core router"},
            {"task_id": "T-BLD-2", "agent_type": "builder", "complexity": "medium", "file_count": 2, "parallel_group": "BUILD-PARALLEL", "scope": "API handler"},
            {"task_id": "T-BLD-3", "agent_type": "ui-builder", "complexity": "medium", "file_count": 2, "parallel_group": "BUILD-PARALLEL", "scope": "Dashboard widget"},
            {"task_id": "T-BLD-4", "agent_type": "builder", "complexity": "medium", "file_count": 1, "parallel_group": "BUILD-PARALLEL", "scope": "CLI flags"},
            {"task_id": "T-TEST", "agent_type": "test-engineer", "complexity": "medium", "scope": "Integration test suite"},
            {"task_id": "T-REV", "agent_type": "code-reviewer", "complexity": "high", "read_only": True, "scope": "PR review"},
            {"task_id": "T-DOC", "agent_type": "doc-generator", "complexity": "low", "scope": "Update README"},
            {"task_id": "T-SEC", "agent_type": "security-auditor", "complexity": "critical", "has_security_impact": True, "scope": "Audit auth boundaries"},
        ]

    def test_10_task_swe_dag_60_40_split_parallel_mutex_and_security_lock(self):
        """10-task SWE DAG targets ~60% Desktop share, <= 1 Desktop inside BUILD-PARALLEL, and Carbon on security-auditor."""
        dag = self._sample_10_task_swe_dag()

        # 1. desktop_available=True -> ~60% eligible share, <= 1 BUILD-PARALLEL on Desktop, security on Carbon
        res_on = allocate_dag_models(dag, desktop_available=True, desktop_target_share=0.60)
        self.assertEqual(res_on["status"], "ok")
        self.assertTrue(res_on["desktop_available"])
        self.assertTrue(res_on["concurrency_safe"])
        self.assertEqual(res_on["total_task_count"], 10)
        self.assertEqual(res_on["eligible_task_count"], 9)
        self.assertAlmostEqual(res_on["achieved_desktop_share"], 5 / 9, places=3)
        self.assertGreaterEqual(res_on["achieved_desktop_share"], 0.50)
        self.assertLessEqual(res_on["achieved_desktop_share"], 0.70)

        by_id = {a["task_id"]: a for a in res_on["allocations"]}

        # Parallel-group mutex safety: at most 1 of the 4 BUILD-PARALLEL workers uses gemini-desktop-app
        parallel_allocs = [by_id[f"T-BLD-{i}"] for i in range(1, 5)]
        parallel_desktop = [a for a in parallel_allocs if a["model"] == "gemini-desktop-app"]
        parallel_api = [a for a in parallel_allocs if a["model"] != "gemini-desktop-app"]
        self.assertLessEqual(len(parallel_desktop), 1)
        self.assertEqual(len(parallel_desktop), 1)
        self.assertEqual(len(parallel_api), 3)
        self.assertEqual(parallel_desktop[0]["task_id"], "T-BLD-1")
        self.assertTrue(parallel_desktop[0]["allow_edits"])
        for api_a in parallel_api:
            self.assertIn(api_a["model"], ("gemini-4-hydrogen", "gemini-4-neon"))
            self.assertEqual(api_a["execution_mode"], "api")

        # Security auditor strictly locked on gemini-4-carbon (high)
        self.assertEqual(by_id["T-SEC"]["model"], "gemini-4-carbon")
        self.assertEqual(by_id["T-SEC"]["reasoning_effort"], "high")
        self.assertFalse(by_id["T-SEC"]["desktop_eligible"])

        # Read-only tasks assigned to Desktop keep allow_edits=False
        self.assertEqual(by_id["T-SPEC"]["model"], "gemini-desktop-app")
        self.assertFalse(by_id["T-SPEC"]["allow_edits"])
        self.assertEqual(by_id["T-REV"]["model"], "gemini-desktop-app")
        self.assertFalse(by_id["T-REV"]["allow_edits"])

        # 2. desktop_available=False -> 0% Desktop share, 100% pure API
        res_off = allocate_dag_models(dag, desktop_available=False, desktop_target_share=0.60)
        self.assertFalse(res_off["desktop_available"])
        self.assertEqual(res_off["achieved_desktop_share"], 0.0)
        self.assertEqual(res_off["desktop_task_count"], 0)
        self.assertEqual(res_off["api_task_count"], 10)
        for a in res_off["allocations"]:
            self.assertNotEqual(a["model"], "gemini-desktop-app")
        off_by_id = {a["task_id"]: a for a in res_off["allocations"]}
        self.assertEqual(off_by_id["T-SPEC"]["model"], "gemini-4-neon")
        self.assertEqual(off_by_id["T-BLD-2"]["model"], "gemini-4-hydrogen")
        self.assertEqual(off_by_id["T-DOC"]["model"], "gemini-3.8-flash")
        self.assertEqual(off_by_id["T-SEC"]["model"], "gemini-4-carbon")

    def test_exact_60_percent_split_on_10_eligible_sequential_tasks(self):
        """With 10 eligible sequential tasks and target_share=0.60, achieved_desktop_share is exact 0.60."""
        seq_tasks = [
            {"task_id": f"SEQ-{i}", "agent_type": "builder" if i % 2 else "spec-engineer", "complexity": "medium"}
            for i in range(10)
        ]
        res = allocate_dag_models(seq_tasks, desktop_available=True, desktop_target_share=0.60)
        self.assertEqual(res["desktop_task_count"], 6)
        self.assertEqual(res["api_task_count"], 4)
        self.assertEqual(res["achieved_desktop_share"], 0.60)


class TestLiveServerDashboardAndCLI60PeerRouting(unittest.TestCase):
    """4. Ephemeral Server Auto-Detection, /api/router/allocate-dag apply=True, Dashboard & CLI."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls.temp_dir.name, "desktop_60_peer_test.db")

        cls.original_db = GLOBAL_STORE.db_path
        GLOBAL_STORE.db_path = cls.db_path
        GLOBAL_STORE._init_db()
        GLOBAL_STORE.reset()

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), OrchestratorHandler)
        cls.port = cls.server.server_address[1]
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join(timeout=2.0)
        GLOBAL_STORE.db_path = cls.original_db
        cls.temp_dir.cleanup()

    def setUp(self):
        GLOBAL_STORE.reset()

    def _get(self, path: str):
        req = urllib.request.Request(f"{self.base_url}{path}", method="GET")
        with urllib.request.urlopen(req, timeout=10) as res:
            ct = res.headers.get("Content-Type", "")
            raw = res.read().decode("utf-8")
            body = json.loads(raw) if "application/json" in ct else raw
            return res.status, ct, body

    def _post(self, path: str, payload: dict):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status, json.loads(res.read().decode("utf-8"))

    def test_auto_detection_on_router_recommend_with_mocked_desktop_status(self):
        """Mocking _get_cached_desktop_status drives deterministic auto-detection on POST /api/router/recommend."""
        ready_snapshot = {
            "status": "ok",
            "desktop": {"ready": True, "lock_busy": False, "queue_depth": 0, "driver_name": "mock"},
        }
        offline_snapshot = {
            "status": "ok",
            "desktop": {"ready": False, "lock_busy": False, "queue_depth": 0, "driver_name": "mock"},
        }

        with mock.patch.object(GLOBAL_STORE, "_get_cached_desktop_status", return_value=ready_snapshot):
            st, data_on = self._post("/api/router/recommend", {
                "agent_type": "spec-engineer",
                "complexity": "high",
            })
            self.assertEqual(st, 200)
            self.assertEqual(data_on["recommendation"]["model"], "gemini-desktop-app")
            self.assertEqual(data_on["desktop_routing_context"]["detection_source"], "auto_cached")
            self.assertTrue(data_on["desktop_routing_context"]["desktop_available"])

        with mock.patch.object(GLOBAL_STORE, "_get_cached_desktop_status", return_value=offline_snapshot):
            st, data_off = self._post("/api/router/recommend", {
                "agent_type": "spec-engineer",
                "complexity": "high",
            })
            self.assertEqual(st, 200)
            self.assertEqual(data_off["recommendation"]["model"], "gemini-4-neon")
            self.assertEqual(data_off["desktop_routing_context"]["detection_source"], "auto_cached")
            self.assertFalse(data_off["desktop_routing_context"]["desktop_available"])

        locked_snapshot = {
            "status": "ok",
            "desktop": {
                "ready": True,
                "lock_busy": False,
                "queue_depth": 0,
                "driver_name": "macos_ax",
                "permissions": {"accessibility": "granted", "clipboard": "ok", "screen_lock": "locked"},
            },
        }
        with mock.patch.object(GLOBAL_STORE, "_get_cached_desktop_status", return_value=locked_snapshot):
            st, data_locked = self._post("/api/router/recommend", {
                "agent_type": "task-planner",
                "complexity": "medium",
            })
            self.assertEqual(st, 200)
            self.assertEqual(data_locked["recommendation"]["model"], "gemini-4-neon")
            self.assertEqual(data_locked["desktop_routing_context"]["detection_source"], "auto_cached")
            self.assertFalse(data_locked["desktop_routing_context"]["desktop_available"])

    def test_allocate_dag_apply_persists_pending_tasks_and_skips_active(self):
        """POST /api/router/allocate-dag with apply=True updates pending SQLite tasks and leaves running tasks intact."""
        client = OrchestratorClient(base_url=self.base_url)

        # Seed one completed, one running, and 5 pending tasks
        client.update_task("DONE-01", "spec-engineer", "completed", progress=100, model="gemini-4-neon")
        client.update_task("RUN-01", "builder", "running", progress=50, model="gemini-4-hydrogen")
        client.update_task("P-SPEC", "spec-engineer", "pending", complexity="high", scope="Spec draft")
        client.update_task("P-BLD-1", "builder", "pending", complexity="medium", parallel_group="BUILD-PARALLEL", scope="Module A")
        client.update_task("P-BLD-2", "builder", "pending", complexity="medium", parallel_group="BUILD-PARALLEL", scope="Module B")
        client.update_task("P-REV", "code-reviewer", "pending", complexity="high", scope="Review")
        client.update_task("P-SEC", "security-auditor", "pending", complexity="critical", scope="Auth security audit")

        st, alloc_res = self._post("/api/router/allocate-dag", {
            "desktop_available": True,
            "desktop_target_share": 0.60,
            "apply": True,
        })
        self.assertEqual(st, 200)
        self.assertEqual(alloc_res["status"], "ok")
        self.assertTrue(alloc_res["applied"])
        self.assertEqual(alloc_res["applied_count"], 5)
        self.assertEqual(sorted(alloc_res["applied_task_ids"]), ["P-BLD-1", "P-BLD-2", "P-REV", "P-SEC", "P-SPEC"])

        # Verify SQLite state updated pending tasks while leaving RUN-01 untouched
        state = client.get_state()
        tasks_by_id = {t["task_id"]: t for t in state["tasks"]}
        self.assertEqual(tasks_by_id["RUN-01"]["model"], "gemini-4-hydrogen")
        self.assertEqual(tasks_by_id["P-SEC"]["model"], "gemini-4-carbon")
        self.assertEqual(tasks_by_id["P-SEC"]["reasoning_effort"], "high")

        # At most 1 of P-BLD-1 / P-BLD-2 is gemini-desktop-app
        bld_models = [tasks_by_id["P-BLD-1"]["model"], tasks_by_id["P-BLD-2"]["model"]]
        self.assertLessEqual(bld_models.count("gemini-desktop-app"), 1)
        self.assertIn("gemini-desktop-app", [tasks_by_id["P-SPEC"]["model"], tasks_by_id["P-REV"]["model"]])
        self.assertIn("desktop_share", alloc_res)

    def test_dashboard_renders_desktop_share_badge_and_controls(self):
        """GET / Dashboard HTML contains #desktop-share-badge, target share controls, and 60% peer badge logic."""
        st, ct, html = self._get("/")
        self.assertEqual(st, 200)
        self.assertIn("text/html", ct)
        self.assertIn('id="desktop-share-badge"', html)
        self.assertIn('id="analytics-desktop-share-badge"', html)
        self.assertIn("updateDesktopShareBadge", html)
        self.assertIn("Desktop Offload:", html)
        self.assertIn("60%", html)

    def test_cli_allocate_dag_and_recommend_desktop_flags(self):
        """Verify client.py allocate-dag --desktop-available --target-desktop-share 0.60 --apply --json and recommend flags."""
        client = OrchestratorClient(base_url=self.base_url)
        client.update_task("CLI-SPEC", "spec-engineer", "pending", complexity="high", scope="Architecture spec")
        client.update_task("CLI-PLAN", "task-planner", "pending", complexity="high", scope="Execution plan")
        client.update_task("CLI-BLD1", "builder", "pending", complexity="medium", parallel_group="BUILD-PARALLEL", scope="Worker 1")
        client.update_task("CLI-BLD2", "builder", "pending", complexity="medium", parallel_group="BUILD-PARALLEL", scope="Worker 2")
        client.update_task("CLI-SEC", "security-auditor", "pending", complexity="critical", scope="Crypto audit")

        cli_path = str(ORCH_DIR / "client.py")

        # 1. CLI allocate-dag --desktop-available --target-desktop-share 0.60 --apply --json
        proc_alloc = subprocess.run(
            [
                sys.executable, cli_path, "--url", self.base_url, "allocate-dag",
                "--desktop-available",
                "--target-desktop-share", "0.60",
                "--apply",
                "--json",
            ],
            capture_output=True, text=True, check=True,
        )
        alloc_json = json.loads(proc_alloc.stdout)
        self.assertEqual(alloc_json["status"], "ok")
        self.assertTrue(alloc_json["applied"])
        self.assertEqual(alloc_json["applied_count"], 5)

        state = client.get_state()
        by_id = {t["task_id"]: t for t in state["tasks"]}
        self.assertEqual(by_id["CLI-SEC"]["model"], "gemini-4-carbon")
        self.assertEqual(by_id["CLI-SPEC"]["model"], "gemini-desktop-app")
        self.assertLessEqual(
            [by_id["CLI-BLD1"]["model"], by_id["CLI-BLD2"]["model"]].count("gemini-desktop-app"),
            1,
        )

        # 2. CLI allocate-dag --format text
        proc_alloc_txt = subprocess.run(
            [
                sys.executable, cli_path, "--url", self.base_url, "allocate-dag",
                "--desktop-available",
                "--target-desktop-share", "0.60",
                "--format", "text",
            ],
            capture_output=True, text=True, check=True,
        )
        self.assertIn("DAG Multi-Model Peer Allocation", proc_alloc_txt.stdout)
        self.assertIn("Parallel-Group Safety: SAFE", proc_alloc_txt.stdout)

        # 3. CLI recommend --no-desktop vs --desktop-available
        proc_no_desk = subprocess.run(
            [
                sys.executable, cli_path, "--url", self.base_url, "recommend",
                "--agent", "spec-engineer", "--complexity", "high", "--no-desktop", "--json",
            ],
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(json.loads(proc_no_desk.stdout)["recommendation"]["model"], "gemini-4-neon")

        proc_with_desk = subprocess.run(
            [
                sys.executable, cli_path, "--url", self.base_url, "recommend",
                "--agent", "spec-engineer", "--complexity", "high", "--desktop-available", "--json",
            ],
            capture_output=True, text=True, check=True,
        )
        desk_rec = json.loads(proc_with_desk.stdout)["recommendation"]
        self.assertEqual(desk_rec["model"], "gemini-desktop-app")
        self.assertFalse(desk_rec["allow_edits"])

    def test_sdk_preflight_hybrid_60_desktop_and_api_only_100_fallback(self):
        """OrchestratorClient.preflight probes desktop_ready, partitions pending DAG 60/40, and emits Dual-Channel directives."""
        client = OrchestratorClient(base_url=self.base_url)
        client.update_task("PF-SPEC", "spec-engineer", "pending", complexity="high", scope="Architecture spec")
        client.update_task("PF-BLD1", "builder", "pending", complexity="high", parallel_group="BUILD-PARALLEL", scope="Core module")
        client.update_task("PF-BLD2", "builder", "pending", complexity="medium", parallel_group="BUILD-PARALLEL", scope="UI widget")
        client.update_task("PF-TEST", "test-engineer", "pending", complexity="medium", scope="Unit tests")
        client.update_task("PF-SEC", "security-auditor", "pending", complexity="critical", scope="Auth boundary audit")

        ready_payload = {
            "status": "ok",
            "desktop": {
                "ready": True,
                "app_detected": True,
                "app_name": "Gemini",
                "driver_name": "macos_ax",
                "permissions": {"accessibility": "granted", "clipboard": "ok", "screen_lock": "unlocked"},
                "queue_depth": 0,
                "lock_busy": False,
                "warnings": [],
            },
            "desktop_share": {
                "target_share": 0.60,
                "current_share": 0.0,
                "eligible_tasks": 4,
                "desktop_tasks": 0,
                "desktop_ready": True,
            },
        }
        offline_payload = {
            "status": "ok",
            "desktop": {
                "ready": False,
                "app_detected": False,
                "driver_name": "macos_ax",
                "permissions": {"accessibility": "denied", "screen_lock": "unlocked"},
                "warnings": ["Accessibility permission not granted"],
            },
            "desktop_share": {
                "target_share": 0.60,
                "current_share": 0.0,
                "eligible_tasks": 4,
                "desktop_tasks": 0,
                "desktop_ready": False,
            },
        }

        with mock.patch.object(GLOBAL_STORE, "get_desktop_status", return_value=ready_payload):
            pf_on = client.preflight(auto_start=False, workspace=".")
            self.assertEqual(pf_on["status"], "ok")
            self.assertTrue(pf_on["server_reachable"])
            self.assertTrue(pf_on["desktop_ready"])
            self.assertEqual(pf_on["execution_mode"], "HYBRID_60_DESKTOP")
            self.assertIn("EXECUTION_MODE: HYBRID_60_DESKTOP", pf_on["execution_banner"])
            self.assertGreaterEqual(len(pf_on["channel_a_tasks"]), 2)
            self.assertGreaterEqual(len(pf_on["channel_b_tasks"]), 1)

            ch_a_by_id = {t["task_id"]: t for t in pf_on["channel_a_tasks"]}
            ch_b_by_id = {t["task_id"]: t for t in pf_on["channel_b_tasks"]}
            self.assertIn("PF-SPEC", ch_a_by_id)
            self.assertIn("desktop-ask", ch_a_by_id["PF-SPEC"]["suggested_command"])
            self.assertNotIn("--allow-edits", ch_a_by_id["PF-SPEC"]["suggested_command"])
            self.assertEqual(ch_a_by_id["PF-SPEC"]["dispatch_via"], "run_command")
            self.assertEqual(ch_a_by_id["PF-SPEC"]["wait_ms_before_async"], 500)
            # At most 1 BUILD-PARALLEL task on Channel A and it gets --allow-edits
            bld_ch_a = [t for tid, t in ch_a_by_id.items() if tid.startswith("PF-BLD")]
            self.assertEqual(len(bld_ch_a), 1)
            self.assertIn("--allow-edits", bld_ch_a[0]["suggested_command"])
            # Security auditor stays on Channel B invoke_subagent(Model="pro")
            self.assertIn("PF-SEC", ch_b_by_id)
            self.assertEqual(ch_b_by_id["PF-SEC"]["dispatch_via"], "invoke_subagent")
            self.assertEqual(ch_b_by_id["PF-SEC"]["invoke_subagent_model"], "pro")

            text_on = format_preflight_text(pf_on)
            self.assertIn("EXECUTION_MODE: HYBRID_60_DESKTOP", text_on)
            self.assertIn("CHANNEL A", text_on)
            self.assertIn("desktop-ask", text_on)
            self.assertIn("CHANNEL B", text_on)
            self.assertIn("invoke_subagent", text_on)

        with mock.patch.object(GLOBAL_STORE, "get_desktop_status", return_value=offline_payload):
            pf_off = client.preflight(auto_start=False, workspace=".")
            self.assertEqual(pf_off["status"], "ok")
            self.assertTrue(pf_off["server_reachable"])
            self.assertFalse(pf_off["desktop_ready"])
            self.assertEqual(pf_off["execution_mode"], "API_ONLY_100")
            self.assertIn("EXECUTION_MODE: API_ONLY_100", pf_off["execution_banner"])
            self.assertEqual(pf_off["channel_a_tasks"], [])
            self.assertEqual(len(pf_off["channel_b_tasks"]), 5)
            text_off = format_preflight_text(pf_off)
            self.assertIn("EXECUTION_MODE: API_ONLY_100", text_off)
            self.assertIn("invoke_subagent", text_off)
            self.assertNotIn("CHANNEL A:", text_off)

    def test_sdk_preflight_auto_start_and_unreachable_fallback(self):
        """preflight handles auto_start=False cleanly and attempts auto-start when local server is down."""
        dead_client = OrchestratorClient(base_url="http://127.0.0.1:19847")
        res_dead = dead_client.preflight(auto_start=False)
        self.assertEqual(res_dead["status"], "ok")
        self.assertFalse(res_dead["server_reachable"])
        self.assertFalse(res_dead["server_auto_started"])
        self.assertFalse(res_dead["desktop_ready"])
        self.assertEqual(res_dead["execution_mode"], "API_ONLY_100")

        # Verify auto_start=True launches detached server.py and waits for health
        with tempfile.NamedTemporaryFile(suffix=".py") as tmp_srv:
            call_count = {"state": 0}

            def fake_get(path: str, timeout: int = 10):
                if path.startswith("/api/desktop/status"):
                    if call_count["state"] == 0:
                        return {"error": "Failed to connect to Orchestrator at http://127.0.0.1:19848/api/desktop/status: refused"}
                    return {
                        "status": "ok",
                        "desktop": {"ready": True, "driver_name": "mock", "permissions": {"screen_lock": "unlocked"}},
                        "desktop_share": {"desktop_ready": True, "target_share": 0.60, "current_share": 0.0, "eligible_tasks": 0},
                    }
                if path == "/api/state":
                    call_count["state"] += 1
                    return {"status": "ok", "tasks": [], "logs": [], "metrics": {}}
                return {"error": "Unexpected path"}

            auto_client = OrchestratorClient(base_url="http://127.0.0.1:19848")
            with mock.patch.object(auto_client, "_get", side_effect=fake_get), \
                 mock.patch("client.subprocess.Popen") as popen_mock:
                res_auto = auto_client.preflight(
                    auto_start=True,
                    wait_timeout=1.0,
                    server_script=tmp_srv.name,
                )
                popen_mock.assert_called_once()
                spawn_cmd = popen_mock.call_args[0][0]
                self.assertIn(tmp_srv.name, spawn_cmd)
                self.assertIn("--port", spawn_cmd)
                self.assertIn("19848", spawn_cmd)
                self.assertTrue(res_auto["server_reachable"])
                self.assertTrue(res_auto["server_auto_started"])
                self.assertTrue(res_auto["desktop_ready"])
                self.assertEqual(res_auto["execution_mode"], "HYBRID_60_DESKTOP")

    def test_cli_preflight_subprocess_desktop_ready_true_and_false(self):
        """CLI `client.py preflight` subprocess emits HYBRID_60_DESKTOP when ready and API_ONLY_100 when unavailable/locked."""
        cli_path = str(ORCH_DIR / "client.py")
        tasks_payload = json.dumps([
            {"task_id": "E2E-SPEC", "agent_type": "spec-engineer", "complexity": "high", "scope": "Spec"},
            {"task_id": "E2E-BLD1", "agent_type": "builder", "complexity": "high", "parallel_group": "BUILD-PARALLEL", "scope": "Core"},
            {"task_id": "E2E-BLD2", "agent_type": "builder", "complexity": "medium", "parallel_group": "BUILD-PARALLEL", "scope": "UI"},
            {"task_id": "E2E-SEC", "agent_type": "security-auditor", "complexity": "critical", "scope": "Security"},
        ])

        ready_snapshot = {
            "status": "ok",
            "desktop": {
                "ready": True,
                "app_detected": True,
                "app_name": "Gemini",
                "driver_name": "macos_ax",
                "permissions": {"accessibility": "granted", "clipboard": "ok", "screen_lock": "unlocked"},
                "queue_depth": 0,
                "lock_busy": False,
                "warnings": [],
            },
            "desktop_share": {
                "target_share": 0.60,
                "current_share": 0.0,
                "eligible_tasks": 0,
                "desktop_tasks": 0,
                "desktop_ready": True,
            },
        }
        locked_snapshot = {
            "status": "ok",
            "desktop": {
                "ready": True,
                "app_detected": True,
                "driver_name": "macos_ax",
                "permissions": {"accessibility": "granted", "clipboard": "ok", "screen_lock": "locked"},
                "warnings": ["Host screen is locked"],
            },
            "desktop_share": {
                "target_share": 0.60,
                "current_share": 0.0,
                "eligible_tasks": 0,
                "desktop_tasks": 0,
                "desktop_ready": False,
            },
        }

        # 1. desktop_ready == True -> HYBRID_60_DESKTOP banner + desktop-ask Channel A directives
        with mock.patch.object(GLOBAL_STORE, "get_desktop_status", return_value=ready_snapshot):
            proc_txt = subprocess.run(
                [
                    sys.executable, cli_path, "--url", self.base_url,
                    "preflight", "--no-auto-start", "--workspace", ".", "--tasks-json", tasks_payload,
                ],
                capture_output=True, text=True, check=True,
            )
            self.assertIn("EXECUTION_MODE: HYBRID_60_DESKTOP", proc_txt.stdout)
            self.assertIn("CHANNEL A: Gemini Desktop App", proc_txt.stdout)
            self.assertIn("desktop-ask", proc_txt.stdout)
            self.assertIn("--allow-edits", proc_txt.stdout)
            self.assertIn("CHANNEL B: AGY Subagents", proc_txt.stdout)
            self.assertIn("invoke_subagent", proc_txt.stdout)

            proc_json = subprocess.run(
                [
                    sys.executable, cli_path, "--url", self.base_url,
                    "preflight", "--no-auto-start", "--tasks-json", tasks_payload, "--json",
                ],
                capture_output=True, text=True, check=True,
            )
            parsed_on = json.loads(proc_json.stdout)
            self.assertEqual(parsed_on["execution_mode"], "HYBRID_60_DESKTOP")
            self.assertTrue(parsed_on["desktop_ready"])
            self.assertGreaterEqual(len(parsed_on["channel_a_tasks"]), 2)
            self.assertTrue(any("desktop-ask" in t["suggested_command"] for t in parsed_on["channel_a_tasks"]))

        # 2. desktop_ready == False (screen locked) -> API_ONLY_100 fallback + invoke_subagent
        with mock.patch.object(GLOBAL_STORE, "get_desktop_status", return_value=locked_snapshot):
            proc_locked = subprocess.run(
                [
                    sys.executable, cli_path, "--url", self.base_url,
                    "preflight", "--no-auto-start", "--tasks-json", tasks_payload,
                ],
                capture_output=True, text=True, check=True,
            )
            self.assertIn("EXECUTION_MODE: API_ONLY_100", proc_locked.stdout)
            self.assertIn("screen_lock=locked", proc_locked.stdout)
            self.assertIn("invoke_subagent", proc_locked.stdout)
            self.assertNotIn("CHANNEL A: Gemini Desktop App", proc_locked.stdout)

            proc_locked_json = subprocess.run(
                [
                    sys.executable, cli_path, "--url", self.base_url,
                    "preflight", "--no-auto-start", "--tasks-json", tasks_payload, "--json",
                ],
                capture_output=True, text=True, check=True,
            )
            parsed_off = json.loads(proc_locked_json.stdout)
            self.assertEqual(parsed_off["execution_mode"], "API_ONLY_100")
            self.assertFalse(parsed_off["desktop_ready"])
            self.assertEqual(parsed_off["channel_a_tasks"], [])
            self.assertEqual(len(parsed_off["channel_b_tasks"]), 4)


class TestDualChannelTemplatesAndWorkflows(unittest.TestCase):
    """5. Verify orchestrator.toml, workflows, SKILL.md, rules, and install.sh enforce Turn-1 preflight & Dual-Channel dispatch."""

    def test_orchestrator_toml_workflows_skill_and_installer_contain_preflight_and_desktop_ask(self):
        toml_path = REPO_ROOT / "packages" / "commands" / "orchestrator.toml"
        with open(toml_path, "rb") as f:
            toml_data = tomllib.load(f)
        prompt_txt = toml_data["prompt"]
        self.assertIn("preflight", prompt_txt)
        self.assertIn("desktop-ask", prompt_txt)
        self.assertIn("HYBRID_60_DESKTOP", prompt_txt)
        self.assertIn("API_ONLY_100", prompt_txt)
        self.assertIn("WaitMsBeforeAsync", prompt_txt)
        self.assertNotIn("Gemini 4 Argon", toml_data["description"])
        self.assertNotIn("Gemini 4 Argon", prompt_txt)

        required_files = [
            REPO_ROOT / "packages" / "workflows" / "orchestrator.md",
            REPO_ROOT / "packages" / "workflows" / "workflow-pipeline.md",
            REPO_ROOT / "packages" / "workflows" / "workflow-spec.md",
            REPO_ROOT / "packages" / "workflows" / "workflow-plan.md",
            REPO_ROOT / "packages" / "workflows" / "workflow-build.md",
            REPO_ROOT / "packages" / "workflows" / "workflow-review.md",
            REPO_ROOT / "packages" / "skills" / "multi-agent-orchestrator" / "SKILL.md",
            REPO_ROOT / "packages" / "rules" / "GEMINI.md",
            REPO_ROOT / "packages" / "orchestrator" / "rules" / "pure-orchestrator.md",
        ]
        for path in required_files:
            with self.subTest(file=str(path.relative_to(REPO_ROOT))):
                content = path.read_text(encoding="utf-8")
                self.assertIn("preflight", content)
                self.assertIn("desktop-ask", content)
                self.assertIn("HYBRID_60_DESKTOP", content)
                self.assertIn("API_ONLY_100", content)

        install_sh = (REPO_ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn("orchestrator.toml", install_sh)
        self.assertIn("preflight", install_sh)
        self.assertIn("desktop-ask", install_sh)


if __name__ == "__main__":
    unittest.main()
