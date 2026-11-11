#!/usr/bin/env python3
"""
Comprehensive Automated Test Suite for Gemini 4 Carbon Evolution.
Validates:
1. Model Catalog & Carbon Pricing (MODEL_REGISTRY, aliases, rates, exact USD/VND math, cache savings)
2. Non-Destructive Legacy SQLite Schema Migration (automatic ALTER TABLE, preserving legacy rows)
3. REST API Endpoints (/api/models, /api/tasks, /api/router/recommend, /api/dag/ready, /api/analytics/models, /api/audit/export)
4. Dashboard Integration (DASHBOARD_HTML with Gemini 4 Carbon, SVG DAG visualizer, model analytics, legacy contracts)
5. SDK & CLI Subprocess End-to-End (OrchestratorClient methods and CLI subprocess calls against ephemeral server)
"""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

# Add repo root and packages to path
REPO_ROOT = Path(__file__).resolve().parent.parent
ORCH_DIR = REPO_ROOT / "packages" / "orchestrator"

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(ORCH_DIR))

from server import (
    GLOBAL_STORE,
    OrchestratorHandler,
    StateStore,
    ThreadingHTTPServer,
)
from client import OrchestratorClient
from models import (
    MODEL_REGISTRY,
    PRICING_TABLE,
    USD_TO_VND_RATE,
    VALID_REASONING_EFFORTS,
    compute_cost,
    get_model_metadata,
    normalize_model_name,
    resolve_model_id,
    validate_reasoning_effort,
)
from router import (
    compute_model_analytics,
    evaluate_dag_ready,
    evaluate_ready_tasks,
    generate_audit_report,
    recommend_model,
)


class TestModelCatalogAndPricing(unittest.TestCase):
    """1. Model Catalog & Carbon Pricing Verification."""

    def test_carbon_model_registration(self):
        """Verify gemini-4-carbon registration in MODEL_REGISTRY with all required fields."""
        self.assertIn("gemini-4-carbon", MODEL_REGISTRY)
        meta = MODEL_REGISTRY["gemini-4-carbon"]
        self.assertEqual(meta["canonical_name"], "gemini-4-carbon")
        self.assertEqual(meta["display_name"], "Gemini 4 Carbon")
        self.assertEqual(meta["tier"], "frontier")
        self.assertEqual(meta["rates"], {"in": 2.00, "out": 10.00, "cache": 0.50})
        self.assertEqual(meta["supported_reasoning_efforts"], ["low", "medium", "high"])
        self.assertEqual(meta["default_reasoning_effort"], "medium")
        self.assertEqual(meta["max_context_tokens"], 1_048_576)
        self.assertIn("ui_badge", meta)
        self.assertIn("security-auditor", meta["target_personas"])

    def test_carbon_aliases(self):
        """Verify aliases normalize to canonical gemini-4-carbon."""
        aliases = [
            "carbon",
            "gemini-carbon",
            "gemini-4-carbon-preview",
            "gemini-4-carbon",
            "CARBON",
            "Gemini-Carbon",
            "gemini-4-carbon-preview",
        ]
        for alias in aliases:
            self.assertEqual(
                normalize_model_name(alias),
                "gemini-4-carbon",
                f"Alias {alias} did not normalize to gemini-4-carbon",
            )
            self.assertEqual(
                resolve_model_id(alias),
                "gemini-4-carbon",
                f"resolve_model_id failed for {alias}",
            )

    def test_pricing_table_compatibility(self):
        """Verify PRICING_TABLE contains backward compatible keys for Carbon."""
        rates = {"in": 2.00, "out": 10.00, "cache": 0.50}
        self.assertEqual(PRICING_TABLE.get("carbon"), rates)
        self.assertEqual(PRICING_TABLE.get("gemini-4-carbon"), rates)
        self.assertEqual(PRICING_TABLE.get("gemini-carbon"), rates)
        self.assertEqual(PRICING_TABLE.get("gemini-4-carbon-preview"), rates)

    def test_carbon_cost_math_usd_and_vnd(self):
        """Verify exact USD ($2.00 in, $10.00 out, $0.50 cache per 1M) & VND cost math with context cache savings."""
        # 1,000,000 prompt, 1,000,000 output, 1,000,000 cache read
        cost = compute_cost("gemini-4-carbon", 1_000_000, 1_000_000, 1_000_000)
        # Actual USD: 2.00 + 10.00 + 0.50 = 12.50
        self.assertEqual(cost["usd"], 12.5)
        # Baseline USD: (1M + 1M) * 2.00 + 10.00 = 14.00
        # Saved USD: 14.00 - 12.50 = 1.50
        self.assertEqual(cost["saved_usd"], 1.5)
        # VND conversion: 12.5 * 25400 = 317500
        self.assertEqual(cost["vnd"], round(12.5 * USD_TO_VND_RATE))
        self.assertEqual(cost["vnd"], 317500)
        # Saved VND: 1.5 * 25400 = 38100
        self.assertEqual(cost["saved_vnd"], round(1.5 * USD_TO_VND_RATE))
        self.assertEqual(cost["saved_vnd"], 38100)
        self.assertEqual(cost["rates"], {"in": 2.00, "out": 10.00, "cache": 0.50})

        # Test partial numbers
        # 500,000 in ($1.00), 200,000 out ($2.00), 1,000,000 cache ($0.50) -> actual = 3.50 USD
        cost_partial = compute_cost("carbon", 500_000, 200_000, 1_000_000)
        self.assertEqual(cost_partial["usd"], 3.5)
        self.assertEqual(cost_partial["saved_usd"], 1.5)
        self.assertEqual(cost_partial["vnd"], 88900)
        self.assertEqual(cost_partial["saved_vnd"], 38100)

        # Zero tokens edge case
        cost_zero = compute_cost("gemini-4-carbon", 0, 0, 0)
        self.assertEqual(cost_zero["usd"], 0.0)
        self.assertEqual(cost_zero["saved_usd"], 0.0)
        self.assertEqual(cost_zero["vnd"], 0)
        self.assertEqual(cost_zero["saved_vnd"], 0)

        # Zero cache tokens edge case
        cost_no_cache = compute_cost("gemini-4-carbon", 100_000, 50_000, 0)
        self.assertEqual(cost_no_cache["usd"], 0.7)
        self.assertEqual(cost_no_cache["saved_usd"], 0.0)

    def test_reasoning_effort_validation(self):
        """Verify VALID_REASONING_EFFORTS and validate_reasoning_effort logic."""
        self.assertEqual(VALID_REASONING_EFFORTS, {"low", "medium", "high"})

        # Gemini 4 Carbon supports low, medium, high
        for effort in ["low", "medium", "high", "LOW", "High"]:
            valid, norm = validate_reasoning_effort("gemini-4-carbon", effort)
            self.assertTrue(valid)
            self.assertEqual(norm, effort.strip().lower())

        # Empty / None effort is valid
        valid, norm = validate_reasoning_effort("gemini-4-carbon", None)
        self.assertTrue(valid)
        self.assertIsNone(norm)

        valid, norm = validate_reasoning_effort("gemini-4-carbon", "")
        self.assertTrue(valid)
        self.assertIsNone(norm)

        # Invalid effort values
        for invalid in ["maximum", "ultra", "extreme", "none", "123"]:
            valid, norm = validate_reasoning_effort("gemini-4-carbon", invalid)
            self.assertFalse(valid)
            self.assertIsNone(norm)

        # Gemini 3.8 Flash does not support reasoning efforts
        for effort in ["low", "medium", "high"]:
            valid, norm = validate_reasoning_effort("gemini-3.8-flash", effort)
            self.assertFalse(valid)
            self.assertIsNone(norm)

    def test_get_model_metadata(self):
        """Verify get_model_metadata returns correct configuration."""
        meta = get_model_metadata("carbon")
        self.assertEqual(meta["canonical_name"], "gemini-4-carbon")
        self.assertEqual(meta["rates"]["in"], 2.00)


class TestLegacySQLiteMigration(unittest.TestCase):
    """2. Non-Destructive Legacy SQLite Migration Verification."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "legacy_test.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_legacy_database_migration_and_row_preservation(self):
        """
        Pre-create a legacy SQLite DB without reasoning_effort column,
        insert legacy rows, boot StateStore, verify legacy rows survive intact,
        and upsert a gemini-4-carbon task with reasoning_effort='high'.
        """
        # 1. Create legacy DB with old schema (no reasoning_effort column)
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE tasks (
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
            CREATE TABLE logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                task_id TEXT NOT NULL,
                agent_type TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL
            )
        """)

        # Insert legacy tasks
        conn.execute("""
            INSERT INTO tasks (
                task_id, agent_type, model, complexity, status, progress, scope, notes,
                conv_id, depends_on, parallel_group, input_tokens, output_tokens, cache_tokens,
                total_tokens, created_at, updated_at
            ) VALUES (
                'LEGACY-01', 'spec-engineer', 'gemini-4-argon', 'high', 'completed', 100,
                'Legacy System Specification', 'Done without errors', 'conv-legacy-01',
                NULL, 'STAGE-1', 5000, 1000, 20000, 26000, '2026-11-10T10:00:00Z', '2026-11-10T11:00:00Z'
            )
        """)
        conn.execute("""
            INSERT INTO tasks (
                task_id, agent_type, model, complexity, status, progress, scope, notes,
                conv_id, depends_on, parallel_group, input_tokens, output_tokens, cache_tokens,
                total_tokens, created_at, updated_at
            ) VALUES (
                'LEGACY-02', 'builder', 'gemini-3.8-flash', 'medium', 'running', 60,
                'Legacy Frontend Build', 'In progress', 'conv-legacy-02',
                '["LEGACY-01"]', 'BUILD-PARALLEL', 3000, 800, 10000, 13800, '2026-11-10T11:05:00Z', '2026-11-10T11:30:00Z'
            )
        """)
        conn.execute("""
            INSERT INTO logs (timestamp, task_id, agent_type, level, message)
            VALUES ('2026-11-10T10:01:00Z', 'LEGACY-01', 'spec-engineer', 'info', 'Legacy log message')
        """)
        conn.commit()

        # Verify legacy table does not have reasoning_effort column yet
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(tasks)")
        cols_before = [r[1] for r in cur.fetchall()]
        self.assertNotIn("reasoning_effort", cols_before)
        conn.close()

        # 2. Boot StateStore against this legacy DB (triggers automated migration)
        store = StateStore(db_path=self.db_path)

        # Check schema was upgraded
        check_conn = sqlite3.connect(self.db_path)
        cur = check_conn.cursor()
        cur.execute("PRAGMA table_info(tasks)")
        cols_after = [r[1] for r in cur.fetchall()]
        self.assertIn("reasoning_effort", cols_after)

        # Check index idx_tasks_model was created
        cur.execute("PRAGMA index_list(tasks)")
        indexes = [r[1] for r in cur.fetchall()]
        self.assertIn("idx_tasks_model", indexes)
        check_conn.close()

        # 3. Verify legacy rows survived intact with correct values
        state = store.get_state()
        tasks_map = {t["task_id"]: t for t in state["tasks"]}
        self.assertEqual(len(tasks_map), 2)

        t1 = tasks_map["LEGACY-01"]
        self.assertEqual(t1["task_id"], "LEGACY-01")
        self.assertEqual(t1["agent_type"], "spec-engineer")
        self.assertEqual(t1["model"], "gemini-4-argon")
        self.assertEqual(t1["status"], "completed")
        self.assertEqual(t1["progress"], 100)
        self.assertEqual(t1["scope"], "Legacy System Specification")
        self.assertEqual(t1["tokens"]["total"], 26000)
        self.assertIsNone(t1["reasoning_effort"])

        t2 = tasks_map["LEGACY-02"]
        self.assertEqual(t2["task_id"], "LEGACY-02")
        self.assertEqual(t2["agent_type"], "builder")
        self.assertEqual(t2["model"], "gemini-3.8-flash")
        self.assertEqual(t2["status"], "running")
        self.assertEqual(t2["depends_on"], ["LEGACY-01"])
        self.assertIsNone(t2["reasoning_effort"])

        # Check logs survived
        self.assertEqual(len(state["logs"]), 1)
        self.assertEqual(state["logs"][0]["message"], "Legacy log message")

        # 4. Upsert a gemini-4-carbon task with reasoning_effort="high"
        carbon_task = store.upsert_task(
            task_id="CARBON-MIG-01",
            agent_type="security-auditor",
            model="gemini-4-carbon",
            complexity="critical",
            status="running",
            progress=35,
            scope="Zero-Day Kernel Sandbox Pentest",
            notes="Active fuzzing with high reasoning effort",
            reasoning_effort="high",
            depends_on=["LEGACY-01"],
            parallel_group="AUDIT-FANOUT",
            input_tokens=15000,
            output_tokens=4000,
            cache_tokens=100000,
        )

        self.assertEqual(carbon_task["task_id"], "CARBON-MIG-01")
        self.assertEqual(carbon_task["model"], "gemini-4-carbon")
        self.assertEqual(carbon_task["reasoning_effort"], "high")
        self.assertEqual(carbon_task["complexity"], "critical")
        self.assertEqual(carbon_task["tokens"]["total"], 119000)

        # 5. Retrieve state again to verify persistence of all 3 tasks
        state2 = store.get_state()
        self.assertEqual(len(state2["tasks"]), 3)
        tasks_map2 = {t["task_id"]: t for t in state2["tasks"]}
        self.assertEqual(tasks_map2["CARBON-MIG-01"]["reasoning_effort"], "high")
        self.assertIsNone(tasks_map2["LEGACY-01"]["reasoning_effort"])


class TestCarbonRESTEndpoints(unittest.TestCase):
    """3. REST API Endpoints Verification."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls.temp_dir.name, "rest_test.db")

        # Point GLOBAL_STORE to test DB
        cls.original_db = GLOBAL_STORE.db_path
        GLOBAL_STORE.db_path = cls.db_path
        GLOBAL_STORE._init_db()
        GLOBAL_STORE.reset()

        # Ephemeral server on port 0
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

    def _get(self, path):
        req = urllib.request.Request(f"{self.base_url}{path}", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            content_type = resp.headers.get("Content-Type", "")
            data = resp.read()
            if "application/json" in content_type:
                return resp.status, content_type, json.loads(data.decode("utf-8"))
            return resp.status, content_type, data.decode("utf-8")

    def _post(self, path, payload):
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            content_type = resp.headers.get("Content-Type", "")
            data = resp.read()
            return resp.status, content_type, json.loads(data.decode("utf-8"))

    def test_get_models_endpoint(self):
        """GET /api/models returns 200 with full MODEL_REGISTRY containing gemini-4-carbon."""
        status, content_type, data = self._get("/api/models")
        self.assertEqual(status, 200)
        self.assertIn("application/json", content_type)
        self.assertEqual(data["status"], "ok")
        self.assertIn("gemini-4-carbon", data["models"])
        carbon = data["models"]["gemini-4-carbon"]
        self.assertEqual(carbon["canonical_name"], "gemini-4-carbon")
        self.assertEqual(carbon["tier"], "frontier")
        self.assertEqual(carbon["rates"]["in"], 2.00)
        self.assertEqual(carbon["rates"]["out"], 10.00)
        self.assertEqual(carbon["rates"]["cache"], 0.50)

    def test_post_tasks_with_reasoning_effort(self):
        """POST /api/tasks stores and returns reasoning_effort for gemini-4-carbon."""
        payload = {
            "task_id": "SEC-API-01",
            "agent_type": "security-auditor",
            "model": "gemini-4-carbon",
            "reasoning_effort": "high",
            "complexity": "critical",
            "status": "running",
            "progress": 30,
            "scope": "RBAC & Authentication Penetration Test",
            "notes": "Testing token validation",
            "depends_on": ["PLAN-01"],
            "parallel_group": "AUDIT-GROUP",
            "input_tokens": 10000,
            "output_tokens": 2000,
            "cache_tokens": 50000,
        }
        status, content_type, data = self._post("/api/tasks", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "ok")
        task = data["task"]
        self.assertEqual(task["task_id"], "SEC-API-01")
        self.assertEqual(task["model"], "gemini-4-carbon")
        self.assertEqual(task["reasoning_effort"], "high")
        self.assertEqual(task["complexity"], "critical")
        self.assertEqual(task["status"], "running")
        self.assertEqual(task["progress"], 30)

        # Cost check: (10k/1M)*2.00 + (2k/1M)*10.00 + (50k/1M)*0.50 = 0.02 + 0.02 + 0.025 = 0.065
        self.assertEqual(task["cost"]["usd"], 0.065)

        # GET /api/state confirms persistence
        status, _, state = self._get("/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(len(state["tasks"]), 1)
        self.assertEqual(state["tasks"][0]["reasoning_effort"], "high")

    def test_post_tasks_effort_normalization_and_alias(self):
        """POST /api/tasks normalizes aliases and handles invalid reasoning_effort gracefully."""
        # 1. Alias 'carbon' with effort 'medium'
        p1 = {
            "task_id": "TASK-ALIAS",
            "agent_type": "planner",
            "model": "carbon",
            "reasoning_effort": "medium",
            "status": "pending",
        }
        _, _, d1 = self._post("/api/tasks", p1)
        self.assertEqual(d1["task"]["model"], "gemini-4-carbon")
        self.assertEqual(d1["task"]["reasoning_effort"], "medium")

        # 2. Invalid reasoning effort string normalized to None
        p2 = {
            "task_id": "TASK-INV-EFFORT",
            "agent_type": "builder",
            "model": "gemini-3.8-flash",
            "reasoning_effort": "super_saiyan",
            "status": "pending",
        }
        _, _, d2 = self._post("/api/tasks", p2)
        self.assertEqual(d2["task"]["reasoning_effort"], None)

    def test_post_router_recommend_endpoint_tiers(self):
        """POST /api/router/recommend verifies all 4 complexity tiers, security escalation, and budget modes."""
        # 1. Critical / Security impact -> Carbon high
        status, _, d1 = self._post("/api/router/recommend", {
            "agent_type": "security-auditor",
            "complexity": "critical",
            "has_security_impact": True,
        })
        self.assertEqual(status, 200)
        self.assertEqual(d1["status"], "ok")
        rec1 = d1["recommendation"]
        self.assertEqual(rec1["model"], "gemini-4-carbon")
        self.assertEqual(rec1["reasoning_effort"], "high")
        self.assertEqual(rec1["tier"], "frontier")

        # Security keyword in scope escalation
        status, _, d1_kw = self._post("/api/router/recommend", {
            "agent_type": "builder",
            "complexity": "medium",
            "scope": "Fix critical CVE vulnerability in auth module",
        })
        self.assertEqual(d1_kw["recommendation"]["model"], "gemini-4-carbon")

        # 2. High complexity - quality_first mode -> Carbon medium
        status, _, d2_qf = self._post("/api/router/recommend", {
            "agent_type": "spec-engineer",
            "complexity": "high",
            "budget_mode": "quality_first",
        })
        self.assertEqual(status, 200)
        rec2_qf = d2_qf["recommendation"]
        self.assertEqual(rec2_qf["model"], "gemini-4-carbon")
        self.assertEqual(rec2_qf["reasoning_effort"], "medium")

        # 2b. High complexity - balanced mode -> Argon medium
        status, _, d2_bal = self._post("/api/router/recommend", {
            "agent_type": "task-planner",
            "complexity": "high",
            "budget_mode": "balanced",
        })
        self.assertEqual(status, 200)
        rec2_bal = d2_bal["recommendation"]
        self.assertEqual(rec2_bal["model"], "gemini-4-argon")
        self.assertEqual(rec2_bal["reasoning_effort"], "medium")
        self.assertEqual(rec2_bal["tier"], "deep_reasoning")

        # 3. Medium complexity / Builder -> Flash None
        status, _, d3 = self._post("/api/router/recommend", {
            "agent_type": "builder",
            "complexity": "medium",
        })
        self.assertEqual(status, 200)
        rec3 = d3["recommendation"]
        self.assertEqual(rec3["model"], "gemini-3.8-flash")
        self.assertIsNone(rec3["reasoning_effort"])
        self.assertEqual(rec3["tier"], "cost_efficient")

        # 4. Low complexity / Simplifier -> Flash-Lite None
        status, _, d4 = self._post("/api/router/recommend", {
            "agent_type": "code-simplifier",
            "complexity": "low",
        })
        self.assertEqual(status, 200)
        rec4 = d4["recommendation"]
        self.assertEqual(rec4["model"], "gemini-3.8-flash-lite")
        self.assertIsNone(rec4["reasoning_effort"])
        self.assertEqual(rec4["tier"], "ultra_fast")

    def test_dag_ready_queue_and_fan_out(self):
        """GET /api/dag/ready correctly computes ready queue, blocked tasks, and parallel Fan-Out groups."""
        # Setup DAG:
        # PLAN-01 (completed)
        # BUILD-FE (pending, depends on PLAN-01, parallel group: BUILD-FANOUT)
        # BUILD-BE (pending, depends on PLAN-01, parallel group: BUILD-FANOUT)
        # TEST-01 (pending, depends on BUILD-FE and BUILD-BE)
        self._post("/api/tasks", {"task_id": "PLAN-01", "status": "completed", "progress": 100})
        self._post("/api/tasks", {
            "task_id": "BUILD-FE",
            "status": "pending",
            "depends_on": ["PLAN-01"],
            "parallel_group": "BUILD-FANOUT",
        })
        self._post("/api/tasks", {
            "task_id": "BUILD-BE",
            "status": "pending",
            "depends_on": ["PLAN-01"],
            "parallel_group": "BUILD-FANOUT",
        })
        self._post("/api/tasks", {
            "task_id": "TEST-01",
            "status": "pending",
            "depends_on": ["BUILD-FE", "BUILD-BE"],
            "parallel_group": "TEST-STAGE",
        })

        status, _, data = self._get("/api/dag/ready")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "ok")

        ready_ids = [t["task_id"] for t in data["ready_tasks"]]
        self.assertEqual(set(ready_ids), {"BUILD-FE", "BUILD-BE"})

        blocked_ids = [t["task_id"] for t in data["blocked_tasks"]]
        self.assertEqual(blocked_ids, ["TEST-01"])
        self.assertEqual(data["blocked_tasks"][0]["waiting_for"], ["BUILD-FE", "BUILD-BE"])

        self.assertTrue(data["can_fan_out"])
        self.assertEqual(data["fan_out_group"], "BUILD-FANOUT")
        self.assertFalse(data["cycle_detected"])

    def test_dag_ready_cycle_detection(self):
        """GET /api/dag/ready detects cyclic deadlock when remaining pending tasks cannot proceed."""
        # Deadlock: CYC-1 depends on CYC-2, CYC-2 depends on CYC-1; none are running or completed
        self._post("/api/tasks", {"task_id": "CYC-1", "status": "pending", "depends_on": ["CYC-2"]})
        self._post("/api/tasks", {"task_id": "CYC-2", "status": "pending", "depends_on": ["CYC-1"]})

        status, _, data = self._get("/api/dag/ready")
        self.assertEqual(status, 200)
        self.assertEqual(data["ready_tasks"], [])
        self.assertEqual(len(data["blocked_tasks"]), 2)
        self.assertTrue(data["cycle_detected"])

    def test_model_analytics_endpoint(self):
        """GET /api/analytics/models returns per-model token consumption and financial spend."""
        # Seed tasks with Carbon, Argon, and Flash
        self._post("/api/tasks", {
            "task_id": "TASK-C1",
            "model": "gemini-4-carbon",
            "status": "completed",
            "input_tokens": 10000,
            "output_tokens": 2000,
            "cache_tokens": 50000,
        })
        self._post("/api/tasks", {
            "task_id": "TASK-C2",
            "model": "gemini-4-carbon",
            "status": "completed",
            "input_tokens": 20000,
            "output_tokens": 5000,
            "cache_tokens": 100000,
        })
        self._post("/api/tasks", {
            "task_id": "TASK-A1",
            "model": "gemini-4-argon",
            "status": "completed",
            "input_tokens": 50000,
            "output_tokens": 10000,
            "cache_tokens": 200000,
        })
        self._post("/api/tasks", {
            "task_id": "TASK-F1",
            "model": "gemini-3.8-flash",
            "status": "completed",
            "input_tokens": 100000,
            "output_tokens": 20000,
            "cache_tokens": 500000,
        })

        status, _, data = self._get("/api/analytics/models")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "ok")
        models = data["models"]

        carbon = models["gemini-4-carbon"]
        self.assertEqual(carbon["task_count"], 2)
        self.assertEqual(carbon["input_tokens"], 30000)
        self.assertEqual(carbon["output_tokens"], 7000)
        self.assertEqual(carbon["cache_tokens"], 150000)
        self.assertEqual(carbon["total_tokens"], 187000)
        self.assertGreater(carbon["cost_usd"], 0.0)
        self.assertGreater(carbon["saved_usd"], 0.0)

        argon = models["gemini-4-argon"]
        self.assertEqual(argon["task_count"], 1)

        flash = models["gemini-3.8-flash"]
        self.assertEqual(flash["task_count"], 1)

        summary = data["summary"]
        self.assertGreater(summary["total_spend_usd"], 0.0)
        self.assertGreater(summary["total_saved_usd"], 0.0)
        self.assertIn("gemini-", summary["most_used_model"])
        self.assertIn("gemini-", summary["highest_cost_model"])

    def test_audit_export_markdown_and_json(self):
        """GET /api/audit/export serves formatted markdown report and JSON structured report."""
        self._post("/api/tasks", {
            "task_id": "TASK-EXP-01",
            "agent_type": "security-auditor",
            "model": "gemini-4-carbon",
            "reasoning_effort": "high",
            "complexity": "critical",
            "status": "completed",
            "progress": 100,
            "scope": "Export Verification Audit",
            "input_tokens": 20000,
            "output_tokens": 4000,
            "cache_tokens": 80000,
        })
        self._post("/api/logs", {
            "task_id": "TASK-EXP-01",
            "agent_type": "security-auditor",
            "message": "Audit completed with 0 high vulnerabilities",
            "level": "info",
        })

        # 1. Markdown Export
        status, content_type, md = self._get("/api/audit/export?format=markdown")
        self.assertEqual(status, 200)
        self.assertIn("text/markdown", content_type)
        self.assertIn("# Antigravity Multi-Agent Orchestrator - Mission Audit Report", md)
        self.assertIn("## 1. Per-Model Consumption & Financial Ledger", md)
        self.assertIn("## 2. Task Execution Matrix", md)
        self.assertIn("gemini-4-carbon", md)
        self.assertIn("TASK-EXP-01", md)
        self.assertIn("Export Verification Audit", md)
        self.assertIn("PASS", md)

        # 2. JSON Export
        status, content_type, js = self._get("/api/audit/export?format=json")
        self.assertEqual(status, 200)
        self.assertIn("application/json", content_type)
        self.assertEqual(js["status"], "ok")
        self.assertIn("generated_at", js)
        self.assertIn("metrics", js)
        self.assertIn("model_analytics", js)
        self.assertIn("tasks", js)
        self.assertEqual(len(js["tasks"]), 1)
        self.assertEqual(js["tasks"][0]["task_id"], "TASK-EXP-01")


class TestDashboardIntegration(unittest.TestCase):
    """4. Dashboard Web UI Integration Verification."""

    @classmethod
    def setUpClass(cls):
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

    def test_dashboard_serves_html_with_carbon_and_legacy_contracts(self):
        """GET / and GET /index.html serve upgraded HTML with Carbon elements and preserve legacy test assertions."""
        for path in ["/", "/index.html"]:
            url = f"{self.base_url}{path}"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                content_type = resp.headers.get("Content-Type", "")
                self.assertIn("text/html", content_type)
                body = resp.read().decode("utf-8")

                # Mandatory legacy assertions from original test_orchestrator.py
                self.assertIn("Hospital Suite - Multi-Agent Orchestrator", body)
                self.assertIn("Live Tasks Status", body)
                self.assertIn("Live Agent Telemetry", body)
                self.assertIn("Pipeline Stage Visualizer", body)
                self.assertIn("connectSSE", body)

                # Upgraded Gemini 4 Carbon Evolution elements
                self.assertIn("Gemini 4 Carbon", body)
                # Smart Router Sandbox trigger
                self.assertTrue("router" in body.lower() or "openRouterModal" in body)
                # SVG DAG visualizer container or script
                self.assertTrue("dag" in body.lower())
                # Per-Model analytics / ledger section
                self.assertTrue("analytics" in body.lower() or "usage history" in body.lower())
                # Export button / function
                self.assertTrue("export" in body.lower())


class TestCarbonSDKAndCLI(unittest.TestCase):
    """5. SDK & CLI Subprocess End-to-End Verification."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls.temp_dir.name, "sdk_cli_test.db")

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

    def test_sdk_python_methods_carbon_evolution(self):
        """Verify OrchestratorClient methods for models, reasoning_effort, router, dag, and export."""
        client = OrchestratorClient(base_url=self.base_url)

        # 1. list_models()
        models = client.list_models()
        self.assertEqual(models["status"], "ok")
        self.assertIn("gemini-4-carbon", models["models"])

        # 2. update_task() with Carbon and reasoning_effort
        res = client.update_task(
            task_id="SDK-TASK-01",
            agent_type="security-auditor",
            status="running",
            progress=40,
            model="gemini-4-carbon",
            reasoning_effort="high",
            complexity="critical",
            scope="SDK Test Task",
            input_tokens=5000,
            output_tokens=1000,
            cache_tokens=25000,
        )
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["task"]["model"], "gemini-4-carbon")
        self.assertEqual(res["task"]["reasoning_effort"], "high")

        # 3. recommend_model() and alias recommend()
        rec1 = client.recommend_model(agent_type="security-auditor", complexity="critical")
        self.assertEqual(rec1["status"], "ok")
        self.assertEqual(rec1["recommendation"]["model"], "gemini-4-carbon")
        self.assertEqual(rec1["recommendation"]["reasoning_effort"], "high")

        rec2 = client.recommend(agent_type="builder", complexity="medium")
        self.assertEqual(rec2["status"], "ok")
        self.assertEqual(rec2["recommendation"]["model"], "gemini-3.8-flash")

        # 4. next_ready() and alias get_ready_tasks()
        ready = client.next_ready()
        self.assertEqual(ready["status"], "ok")
        self.assertIn("ready_tasks", ready)
        self.assertIn("blocked_tasks", ready)

        # 5. get_model_analytics()
        analytics = client.get_model_analytics()
        self.assertEqual(analytics["status"], "ok")
        self.assertIn("gemini-4-carbon", analytics["models"])
        self.assertEqual(analytics["models"]["gemini-4-carbon"]["task_count"], 1)

        # 6. export_audit()
        export_md = client.export_audit(format="markdown")
        self.assertIn("# Antigravity Multi-Agent Orchestrator", export_md)

        export_json = client.export_audit(format="json")
        self.assertIsInstance(export_json, dict)
        self.assertEqual(export_json["status"], "ok")

        # export_audit writing to disk
        out_file = os.path.join(self.temp_dir.name, "sdk_audit_out.md")
        res_file = client.export_audit(format="markdown", out_path=out_file)
        self.assertTrue(os.path.isfile(out_file))
        with open(out_file, "r", encoding="utf-8") as f:
            disk_content = f.read()
        self.assertIn("# Antigravity Multi-Agent Orchestrator", disk_content)

    def test_cli_subprocess_commands_carbon_evolution(self):
        """Verify client.py CLI commands via subprocess: update, models, recommend, next-ready, analytics, export."""
        cli_path = str(ORCH_DIR / "client.py")

        # 1. CLI update --model gemini-4-carbon --reasoning-effort high
        proc = subprocess.run([
            sys.executable, cli_path, "--url", self.base_url, "update",
            "--task", "CLI-SEC-01",
            "--agent", "security-auditor",
            "--status", "running",
            "--progress", "55",
            "--model", "gemini-4-carbon",
            "--reasoning-effort", "high",
            "--complexity", "critical",
            "--scope", "CLI Subprocess Verification",
            "--notes", "Testing CLI flags",
            "--input-tokens", "12000",
            "--output-tokens", "3000",
            "--cache-tokens", "60000",
        ], capture_output=True, text=True, check=True)
        res = json.loads(proc.stdout)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["task"]["task_id"], "CLI-SEC-01")
        self.assertEqual(res["task"]["model"], "gemini-4-carbon")
        self.assertEqual(res["task"]["reasoning_effort"], "high")

        # 2. CLI models --json
        proc = subprocess.run([
            sys.executable, cli_path, "--url", self.base_url, "models", "--json"
        ], capture_output=True, text=True, check=True)
        res = json.loads(proc.stdout)
        self.assertEqual(res["status"], "ok")
        self.assertIn("gemini-4-carbon", res["models"])

        # 3. CLI recommend --agent security-auditor --complexity critical --security-impact --json
        proc = subprocess.run([
            sys.executable, cli_path, "--url", self.base_url, "recommend",
            "--agent", "security-auditor",
            "--complexity", "critical",
            "--security-impact",
            "--json",
        ], capture_output=True, text=True, check=True)
        res = json.loads(proc.stdout)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["recommendation"]["model"], "gemini-4-carbon")
        self.assertEqual(res["recommendation"]["reasoning_effort"], "high")

        # 4. CLI next-ready --json
        proc = subprocess.run([
            sys.executable, cli_path, "--url", self.base_url, "next-ready", "--json"
        ], capture_output=True, text=True, check=True)
        res = json.loads(proc.stdout)
        self.assertEqual(res["status"], "ok")
        self.assertIn("ready_tasks", res)

        # 5. CLI analytics --json
        proc = subprocess.run([
            sys.executable, cli_path, "--url", self.base_url, "analytics", "--json"
        ], capture_output=True, text=True, check=True)
        res = json.loads(proc.stdout)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["models"]["gemini-4-carbon"]["task_count"], 1)

        # 6. CLI export --format markdown --output <file>
        export_file = os.path.join(self.temp_dir.name, "cli_audit_report.md")
        proc = subprocess.run([
            sys.executable, cli_path, "--url", self.base_url, "export",
            "--format", "markdown",
            "--output", export_file,
        ], capture_output=True, text=True, check=True)
        self.assertEqual(proc.returncode, 0)
        self.assertTrue(os.path.isfile(export_file))
        with open(export_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("# Antigravity Multi-Agent Orchestrator - Mission Audit Report", content)
        self.assertIn("CLI-SEC-01", content)
        self.assertIn("gemini-4-carbon", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
