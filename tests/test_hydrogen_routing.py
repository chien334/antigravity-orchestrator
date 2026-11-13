#!/usr/bin/env python3
"""
Comprehensive Automated Test Suite for Gemini 4 Hydrogen Integration & High-Throughput Routing.
Validates:
1. Catalog, Pricing & Suffix Extraction (MODEL_REGISTRY, rates, exact USD/VND math, 95% cache discount,
   alias normalization, extract_model_and_effort suffix parsing, xhigh clamping policy)
2. 5-Tier Smart Router & Budget Modes (balanced, speed_first, latency_sensitive, quality_first, cost_saving)
3. Uncompromised Security Guardrails (has_security_impact=True, security-auditor, auth/crypto/owasp/cve scopes)
4. Fast-Retry & Escalation Circuit Breaker (retry_count=0, retry_count=1 self-heal, retry_count>=2 trip to Carbon)
5. Server HTTP Endpoints & Dashboard UI Integration (POST /api/tasks, POST /api/router/recommend, GET /index.html)
6. Python SDK & CLI Subprocess End-to-End (OrchestratorClient and client.py subprocess commands)
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

# Add repository root and orchestrator directory to sys.path
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
    extract_model_and_effort,
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


class TestHydrogenCatalogPricingAndEffort(unittest.TestCase):
    """1. Model Catalog, Pricing Math, Suffix Parsing & Effort Validation."""

    def test_hydrogen_registration(self):
        """Verify gemini-4-hydrogen is registered in MODEL_REGISTRY with correct metadata."""
        self.assertIn("gemini-4-hydrogen", MODEL_REGISTRY)
        meta = MODEL_REGISTRY["gemini-4-hydrogen"]
        self.assertEqual(meta["canonical_name"], "gemini-4-hydrogen")
        self.assertEqual(meta["display_name"], "Gemini 4 Hydrogen")
        self.assertEqual(meta["tier"], "high_throughput")
        self.assertEqual(meta["rates"], {"in": 1.50, "out": 7.50, "cache": 0.075})
        self.assertEqual(meta["supported_reasoning_efforts"], ["low", "medium", "high", "xhigh"])
        self.assertEqual(meta["default_reasoning_effort"], "medium")
        self.assertEqual(meta["max_context_tokens"], 1_048_576)
        self.assertIn("ui_badge", meta)
        self.assertIn("bg-cyan-950/60", meta["ui_badge"]["bg"])
        self.assertIn("text-cyan-300", meta["ui_badge"]["text"])

        # Check target personas
        target_personas = meta["target_personas"]
        for expected in ["builder", "test-engineer", "scout", "codebase-researcher", "ui-builder", "frontend-engineer"]:
            self.assertIn(expected, target_personas)

    def test_hydrogen_aliases(self):
        """Verify all aliases normalize to canonical gemini-4-hydrogen."""
        aliases = [
            "hydrogen",
            "gemini-hydrogen",
            "gemini-4-hydrogen-preview",
            "gemini-4-hydrogen-low",
            "gemini-4-hydrogen-medium",
            "gemini-4-hydrogen-high",
            "gemini-4-hydrogen-xhigh",
            "HYDROGEN",
            "Gemini-Hydrogen",
            "GEMINI-4-HYDROGEN",
        ]
        for alias in aliases:
            self.assertEqual(
                normalize_model_name(alias),
                "gemini-4-hydrogen",
                f"normalize_model_name failed for alias: {alias}",
            )
            self.assertEqual(
                resolve_model_id(alias),
                "gemini-4-hydrogen",
                f"resolve_model_id failed for alias: {alias}",
            )

    def test_pricing_table_hydrogen(self):
        """Verify PRICING_TABLE contains backward compatible keys for Hydrogen."""
        expected_rates = {"in": 1.50, "out": 7.50, "cache": 0.075}
        for key in [
            "hydrogen",
            "gemini-4-hydrogen",
            "gemini-hydrogen",
            "gemini-4-hydrogen-preview",
            "gemini-4-hydrogen-low",
            "gemini-4-hydrogen-medium",
            "gemini-4-hydrogen-high",
            "gemini-4-hydrogen-xhigh",
        ]:
            self.assertIn(key, PRICING_TABLE, f"Key {key} missing in PRICING_TABLE")
            self.assertEqual(PRICING_TABLE[key], expected_rates)

    def test_hydrogen_cost_math_usd_and_vnd(self):
        """
        Verify exact USD ($1.50 in, $7.50 out, $0.075 cache read) and VND math.
        Cache read gives a 95% discount over regular prompt input rate ($1.50 -> $0.075).
        """
        # Test Case 1: 1M input, 1M output, 1M cache read
        # in_cost = (1M/1M)*$1.50 = $1.50
        # out_cost = (1M/1M)*$7.50 = $7.50
        # cache_cost = (1M/1M)*$0.075 = $0.075
        # total_usd = $9.075
        # baseline_usd = ((1M+1M)/1M)*$1.50 + $7.50 = $10.50
        # saved_usd = $10.50 - $9.075 = $1.425
        # total_vnd = round(9.075 * 25400) = 230,505
        # saved_vnd = round(1.425 * 25400) = 36,195
        cost1 = compute_cost("gemini-4-hydrogen", 1_000_000, 1_000_000, 1_000_000)
        self.assertEqual(cost1["usd"], 9.075)
        self.assertEqual(cost1["vnd"], 230505)
        self.assertEqual(cost1["saved_usd"], 1.425)
        self.assertEqual(cost1["saved_vnd"], 36195)
        self.assertEqual(cost1["rates"], {"in": 1.50, "out": 7.50, "cache": 0.075})

        # Test Case 2: 500k input, 100k output, 200k cache
        # in: 0.5 * 1.50 = 0.75
        # out: 0.1 * 7.50 = 0.75
        # cache: 0.2 * 0.075 = 0.015
        # total_usd = 1.515
        # baseline: 0.7 * 1.50 + 0.75 = 1.05 + 0.75 = 1.80
        # saved_usd = 1.80 - 1.515 = 0.285
        # vnd: round(1.515 * 25400) = 38481
        # saved_vnd: round(0.285 * 25400) = 7239
        cost2 = compute_cost("gemini-4-hydrogen", 500_000, 100_000, 200_000)
        self.assertEqual(cost2["usd"], 1.515)
        self.assertEqual(cost2["vnd"], 38481)
        self.assertEqual(cost2["saved_usd"], 0.285)
        self.assertEqual(cost2["saved_vnd"], 7239)

        # Test Case 3: Zero tokens
        cost_zero = compute_cost("gemini-4-hydrogen", 0, 0, 0)
        self.assertEqual(cost_zero["usd"], 0.0)
        self.assertEqual(cost_zero["vnd"], 0)
        self.assertEqual(cost_zero["saved_usd"], 0.0)
        self.assertEqual(cost_zero["saved_vnd"], 0)

    def test_suffix_effort_extraction(self):
        """Verify extract_model_and_effort parses model suffixes (-low, -medium, -high, -xhigh)."""
        # When reasoning_effort is None, extracts from suffix
        m1, e1 = extract_model_and_effort("gemini-4-hydrogen-xhigh")
        self.assertEqual(m1, "gemini-4-hydrogen")
        self.assertEqual(e1, "xhigh")

        m2, e2 = extract_model_and_effort("gemini-4-hydrogen-high")
        self.assertEqual(m2, "gemini-4-hydrogen")
        self.assertEqual(e2, "high")

        m3, e3 = extract_model_and_effort("gemini-4-hydrogen-medium")
        self.assertEqual(m3, "gemini-4-hydrogen")
        self.assertEqual(e3, "medium")

        m4, e4 = extract_model_and_effort("gemini-4-hydrogen-low")
        self.assertEqual(m4, "gemini-4-hydrogen")
        self.assertEqual(e4, "low")

        # Explicit effort parameter takes precedence
        m5, e5 = extract_model_and_effort("gemini-4-hydrogen-xhigh", effort="medium")
        self.assertEqual(m5, "gemini-4-hydrogen")
        self.assertEqual(e5, "medium")

        # Base model without suffix
        m6, e6 = extract_model_and_effort("gemini-4-hydrogen")
        self.assertEqual(m6, "gemini-4-hydrogen")
        self.assertIsNone(e6)

        # None defaults to gemini-4-argon
        m7, e7 = extract_model_and_effort(None)
        self.assertEqual(m7, "gemini-4-argon")
        self.assertIsNone(e7)

    def test_xhigh_reasoning_effort_and_clamping(self):
        """Verify validate_reasoning_effort allows xhigh on Hydrogen and applies clamping on Carbon/Argon."""
        self.assertIn("xhigh", VALID_REASONING_EFFORTS)

        # Gemini 4 Hydrogen supports xhigh natively
        valid, norm = validate_reasoning_effort("gemini-4-hydrogen", "xhigh")
        self.assertTrue(valid)
        self.assertEqual(norm, "xhigh")

        # Uppercase normalization
        valid, norm = validate_reasoning_effort("gemini-4-hydrogen", "XHIGH")
        self.assertTrue(valid)
        self.assertEqual(norm, "xhigh")

        # Carbon & Argon without clamp -> False
        valid, norm = validate_reasoning_effort("gemini-4-carbon", "xhigh", clamp=False)
        self.assertFalse(valid)
        self.assertIsNone(norm)

        valid, norm = validate_reasoning_effort("gemini-4-argon", "xhigh", clamp=False)
        self.assertFalse(valid)
        self.assertIsNone(norm)

        # Carbon & Argon with clamp=True -> clamped to 'high'
        valid, norm = validate_reasoning_effort("gemini-4-carbon", "xhigh", clamp=True)
        self.assertTrue(valid)
        self.assertEqual(norm, "high")

        valid, norm = validate_reasoning_effort("gemini-4-argon", "xhigh", clamp=True)
        self.assertTrue(valid)
        self.assertEqual(norm, "high")

        # Flash models do not support reasoning efforts
        valid, norm = validate_reasoning_effort("gemini-3.8-flash", "xhigh", clamp=True)
        self.assertFalse(valid)
        self.assertIsNone(norm)

        valid, norm = validate_reasoning_effort("gemini-3.8-flash-lite", "xhigh", clamp=True)
        self.assertFalse(valid)
        self.assertIsNone(norm)

        # Invalid effort string
        valid, norm = validate_reasoning_effort("gemini-4-hydrogen", "ultra")
        self.assertFalse(valid)
        self.assertIsNone(norm)


class Test5TierSmartRouterAndBudgetModes(unittest.TestCase):
    """2. 5-Tier Smart Router & Budget Modes (balanced, speed_first, quality_first, cost_saving)."""

    def test_router_balanced_mode(self):
        """Verify routing for all personas under default balanced mode."""
        # 1. Builders, UI Builders, Testers, Scouts -> gemini-4-hydrogen
        rec_builder = recommend_model("builder", complexity="medium")
        self.assertEqual(rec_builder["recommendation"]["model"], "gemini-4-hydrogen")
        self.assertEqual(rec_builder["recommendation"]["reasoning_effort"], "high")
        self.assertEqual(rec_builder["recommendation"]["tier"], "high_throughput")
        self.assertEqual(rec_builder["recommendation"]["fallback_model"], "gemini-3.8-flash")

        rec_tester = recommend_model("test-engineer", complexity="medium")
        self.assertEqual(rec_tester["recommendation"]["model"], "gemini-4-hydrogen")

        rec_scout = recommend_model("scout", complexity="low")
        self.assertEqual(rec_scout["recommendation"]["model"], "gemini-4-hydrogen")
        self.assertEqual(rec_scout["recommendation"]["reasoning_effort"], "medium")

        rec_ui = recommend_model("ui-builder", complexity="medium")
        self.assertEqual(rec_ui["recommendation"]["model"], "gemini-4-hydrogen")

        # 2. Spec Engineer, Task Planner, Code Reviewer -> gemini-4-argon
        rec_planner = recommend_model("task-planner", complexity="high")
        self.assertEqual(rec_planner["recommendation"]["model"], "gemini-4-argon")
        self.assertEqual(rec_planner["recommendation"]["reasoning_effort"], "medium")
        self.assertEqual(rec_planner["recommendation"]["tier"], "deep_reasoning")

        rec_spec = recommend_model("spec-engineer", complexity="high")
        self.assertEqual(rec_spec["recommendation"]["model"], "gemini-4-argon")

        rec_rev = recommend_model("code-reviewer", complexity="medium")
        self.assertEqual(rec_rev["recommendation"]["model"], "gemini-4-argon")

        # 3. Micro-tier / Simplifier -> gemini-3.8-flash-lite
        rec_simp = recommend_model("code-simplifier", complexity="low")
        self.assertEqual(rec_simp["recommendation"]["model"], "gemini-3.8-flash-lite")
        self.assertIsNone(rec_simp["recommendation"]["reasoning_effort"])
        self.assertEqual(rec_simp["recommendation"]["tier"], "ultra_fast")

    def test_router_speed_first_and_latency_sensitive_mode(self):
        """Verify speed_first and latency_sensitive modes route rapid tasks to gemini-4-hydrogen."""
        # Builder in speed_first
        rec1 = recommend_model("builder", complexity="medium", budget_mode="speed_first")
        self.assertEqual(rec1["recommendation"]["model"], "gemini-4-hydrogen")

        # Test engineer in latency_sensitive
        rec2 = recommend_model("test-engineer", complexity="medium", budget_mode="latency_sensitive")
        self.assertEqual(rec2["recommendation"]["model"], "gemini-4-hydrogen")

        # Code reviewer in speed_first mode (medium complexity) routes to Hydrogen with xhigh!
        rec_rev = recommend_model("code-reviewer", complexity="medium", budget_mode="speed_first")
        self.assertEqual(rec_rev["recommendation"]["model"], "gemini-4-hydrogen")
        self.assertEqual(rec_rev["recommendation"]["reasoning_effort"], "xhigh")
        self.assertEqual(rec_rev["recommendation"]["tier"], "high_throughput")

        # Code reviewer in latency_sensitive mode routes to Hydrogen with xhigh
        rec_rev_ls = recommend_model("code-reviewer", complexity="medium", budget_mode="latency_sensitive")
        self.assertEqual(rec_rev_ls["recommendation"]["model"], "gemini-4-hydrogen")
        self.assertEqual(rec_rev_ls["recommendation"]["reasoning_effort"], "xhigh")

    def test_router_quality_first_mode(self):
        """Verify quality_first mode upgrades builders to Argon and planners to Carbon."""
        # Builder medium in quality_first -> gemini-4-argon
        rec_b = recommend_model("builder", complexity="medium", budget_mode="quality_first")
        self.assertEqual(rec_b["recommendation"]["model"], "gemini-4-argon")
        self.assertEqual(rec_b["recommendation"]["reasoning_effort"], "medium")
        self.assertEqual(rec_b["recommendation"]["tier"], "deep_reasoning")

        # Spec engineer in quality_first -> gemini-4-carbon
        rec_spec = recommend_model("spec-engineer", complexity="high", budget_mode="quality_first")
        self.assertEqual(rec_spec["recommendation"]["model"], "gemini-4-carbon")
        self.assertEqual(rec_spec["recommendation"]["reasoning_effort"], "medium")
        self.assertEqual(rec_spec["recommendation"]["tier"], "frontier")

        # Code reviewer in quality_first -> gemini-4-carbon
        rec_rev = recommend_model("code-reviewer", complexity="medium", budget_mode="quality_first")
        self.assertEqual(rec_rev["recommendation"]["model"], "gemini-4-carbon")

    def test_router_cost_saving_mode(self):
        """Verify cost_saving mode routes implementation to Flash while preserving architecture."""
        # Builder in cost_saving -> gemini-3.8-flash
        rec_b = recommend_model("builder", complexity="medium", budget_mode="cost_saving")
        self.assertEqual(rec_b["recommendation"]["model"], "gemini-3.8-flash")
        self.assertIsNone(rec_b["recommendation"]["reasoning_effort"])
        self.assertEqual(rec_b["recommendation"]["tier"], "cost_efficient")

        # Test engineer in cost_saving -> gemini-3.8-flash
        rec_t = recommend_model("test-engineer", complexity="medium", budget_mode="cost_first")
        self.assertEqual(rec_t["recommendation"]["model"], "gemini-3.8-flash")

        # Task planner high complexity preserves Argon deep reasoning
        rec_p = recommend_model("task-planner", complexity="high", budget_mode="cost_saving")
        self.assertEqual(rec_p["recommendation"]["model"], "gemini-4-argon")


class TestSecurityGuardrailsUncompromised(unittest.TestCase):
    """3. Uncompromised Security Guardrails (Zero-Downgrade Invariant)."""

    def test_security_impact_flag_overrides_all_modes(self):
        """Verify has_security_impact=True forces gemini-4-carbon (high) even in cost_saving / speed_first."""
        # In speed_first mode
        rec_speed = recommend_model(
            agent_type="builder",
            complexity="low",
            has_security_impact=True,
            budget_mode="speed_first",
        )
        self.assertEqual(rec_speed["recommendation"]["model"], "gemini-4-carbon")
        self.assertEqual(rec_speed["recommendation"]["reasoning_effort"], "high")
        self.assertEqual(rec_speed["recommendation"]["tier"], "frontier")

        # In cost_saving mode
        rec_cost = recommend_model(
            agent_type="scout",
            complexity="low",
            has_security_impact=True,
            budget_mode="cost_saving",
        )
        self.assertEqual(rec_cost["recommendation"]["model"], "gemini-4-carbon")
        self.assertEqual(rec_cost["recommendation"]["reasoning_effort"], "high")

    def test_security_auditor_and_critical_complexity(self):
        """Verify security-auditor and critical complexity enforce Gemini 4 Carbon."""
        rec_crit = recommend_model("security-auditor", complexity="critical")
        self.assertEqual(rec_crit["recommendation"]["model"], "gemini-4-carbon")
        self.assertEqual(rec_crit["recommendation"]["reasoning_effort"], "high")

        rec_high = recommend_model("security-auditor", complexity="high")
        self.assertEqual(rec_high["recommendation"]["model"], "gemini-4-carbon")
        self.assertEqual(rec_high["recommendation"]["reasoning_effort"], "medium")

        rec_deb = recommend_model("debugger", complexity="critical")
        self.assertEqual(rec_deb["recommendation"]["model"], "gemini-4-carbon")
        self.assertEqual(rec_deb["recommendation"]["reasoning_effort"], "high")

    def test_security_keywords_in_scope_lock_to_carbon(self):
        """Verify scope keywords (auth, crypto, owasp, cve, etc.) lock routing to Gemini 4 Carbon."""
        keywords = ["vulnerability", "cve", "penetration", "auth", "crypto", "owasp", "rbac", "jwt", "migration"]
        for kw in keywords:
            rec = recommend_model(
                agent_type="builder",
                complexity="low",
                scope=f"Refactor {kw} handling in session manager",
                budget_mode="cost_saving",
            )
            self.assertEqual(
                rec["recommendation"]["model"],
                "gemini-4-carbon",
                f"Scope keyword '{kw}' did not route to gemini-4-carbon in cost_saving mode",
            )
            self.assertEqual(rec["recommendation"]["tier"], "frontier")


class TestFastRetryCircuitBreaker(unittest.TestCase):
    """4. Fast-Retry & Escalation Circuit Breaker."""

    def test_circuit_breaker_attempt_0_initial_hydrogen(self):
        """Verify retry_count=0 routes to Hydrogen with active circuit breaker metadata."""
        rec = recommend_model("builder", complexity="medium", retry_count=0)
        self.assertEqual(rec["recommendation"]["model"], "gemini-4-hydrogen")
        self.assertEqual(rec["recommendation"]["reasoning_effort"], "high")
        self.assertIn("circuit_breaker", rec["recommendation"])
        cb = rec["recommendation"]["circuit_breaker"]
        self.assertEqual(cb["status"], "active")
        self.assertEqual(cb["retry_count"], 0)
        self.assertEqual(cb["max_self_retries"], 1)
        self.assertEqual(cb["escalate_to"], "gemini-4-carbon")
        self.assertEqual(cb["escalate_effort"], "high")

    def test_circuit_breaker_attempt_1_fast_self_heal(self):
        """Verify retry_count=1 keeps Hydrogen but elevates thinking to xhigh for self-healing."""
        rec = recommend_model("builder", complexity="medium", retry_count=1)
        self.assertEqual(rec["recommendation"]["model"], "gemini-4-hydrogen")
        self.assertEqual(rec["recommendation"]["reasoning_effort"], "xhigh")
        self.assertIn("circuit_breaker", rec["recommendation"])
        cb = rec["recommendation"]["circuit_breaker"]
        self.assertEqual(cb["status"], "retrying")
        self.assertEqual(cb["retry_count"], 1)

    def test_circuit_breaker_attempt_2_tripped_to_carbon(self):
        """Verify retry_count=2 trips the Circuit Breaker and auto-escalates to gemini-4-carbon (high)."""
        rec = recommend_model("builder", complexity="medium", retry_count=2)
        self.assertEqual(rec["recommendation"]["model"], "gemini-4-carbon")
        self.assertEqual(rec["recommendation"]["reasoning_effort"], "high")
        self.assertEqual(rec["recommendation"]["tier"], "frontier")
        self.assertIn("circuit_breaker", rec["recommendation"])
        cb = rec["recommendation"]["circuit_breaker"]
        self.assertEqual(cb["status"], "tripped")
        self.assertEqual(cb["retries"], 2)
        self.assertEqual(cb["escalated_from"], "gemini-4-hydrogen")
        self.assertIn("Circuit breaker tripped after 2 failed attempts", rec["recommendation"]["rationale"])

    def test_circuit_breaker_attempt_3_or_higher_overrides_budget_mode(self):
        """Verify retry_count>=2 trips circuit breaker even when budget_mode is cost_saving or speed_first."""
        rec_cost = recommend_model("builder", complexity="medium", retry_count=3, budget_mode="cost_saving")
        self.assertEqual(rec_cost["recommendation"]["model"], "gemini-4-carbon")
        self.assertEqual(rec_cost["recommendation"]["reasoning_effort"], "high")
        cb_cost = rec_cost["recommendation"]["circuit_breaker"]
        self.assertEqual(cb_cost["status"], "tripped")
        self.assertEqual(cb_cost["retries"], 3)

        rec_speed = recommend_model("builder", complexity="medium", retry_count=4, budget_mode="speed_first")
        self.assertEqual(rec_speed["recommendation"]["model"], "gemini-4-carbon")
        self.assertEqual(rec_speed["recommendation"]["reasoning_effort"], "high")


class TestHydrogenE2ERESTAndDashboard(unittest.TestCase):
    """5. Live Ephemeral HTTP Server & Dashboard UI Integration."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls.temp_dir.name, "hydrogen_rest_test.db")

        cls.original_db = GLOBAL_STORE.db_path
        GLOBAL_STORE.db_path = cls.db_path
        GLOBAL_STORE._init_db()
        GLOBAL_STORE.reset()

        # Ephemeral HTTP server
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

    def test_get_models_includes_hydrogen(self):
        """GET /api/models returns 200 with gemini-4-hydrogen in registry."""
        status, content_type, data = self._get("/api/models")
        self.assertEqual(status, 200)
        self.assertIn("application/json", content_type)
        self.assertEqual(data["status"], "ok")
        self.assertIn("gemini-4-hydrogen", data["models"])
        hydro = data["models"]["gemini-4-hydrogen"]
        self.assertEqual(hydro["canonical_name"], "gemini-4-hydrogen")
        self.assertEqual(hydro["tier"], "high_throughput")
        self.assertEqual(hydro["rates"]["in"], 1.50)
        self.assertEqual(hydro["rates"]["out"], 7.50)
        self.assertEqual(hydro["rates"]["cache"], 0.075)
        self.assertEqual(hydro["supported_reasoning_efforts"], ["low", "medium", "high", "xhigh"])

    def test_post_task_with_suffix_effort(self):
        """POST /api/tasks with model='gemini-4-hydrogen-xhigh' extracts model and sets xhigh effort."""
        status, _, data = self._post("/api/tasks", {
            "task_id": "HYDRO-API-01",
            "agent_type": "builder",
            "model": "gemini-4-hydrogen-xhigh",
            "status": "running",
            "progress": 25,
            "scope": "Verify suffix extraction on task creation",
        })
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "ok")
        task = data["task"]
        self.assertEqual(task["task_id"], "HYDRO-API-01")
        self.assertEqual(task["model"], "gemini-4-hydrogen")
        self.assertEqual(task["reasoning_effort"], "xhigh")

    def test_post_task_cost_calculation_hydrogen(self):
        """POST /api/tasks calculates exact USD and VND costs for Hydrogen."""
        status, _, data = self._post("/api/tasks", {
            "task_id": "HYDRO-COST-01",
            "agent_type": "builder",
            "model": "gemini-4-hydrogen",
            "status": "completed",
            "progress": 100,
            "input_tokens": 1_000_000,
            "output_tokens": 1_000_000,
            "cache_tokens": 1_000_000,
        })
        self.assertEqual(status, 200)
        task = data["task"]
        self.assertEqual(task["cost"]["usd"], 9.075)
        self.assertEqual(task["cost"]["vnd"], 230505)
        self.assertEqual(task["cost"]["saved_usd"], 1.425)
        self.assertEqual(task["cost"]["saved_vnd"], 36195)

    def test_post_router_recommend_with_retry_and_circuit_breaker(self):
        """POST /api/router/recommend tests retry_count and budget_mode via HTTP."""
        # 1. Normal builder
        status, _, d1 = self._post("/api/router/recommend", {
            "agent_type": "builder",
            "complexity": "medium",
            "retry_count": 0,
        })
        self.assertEqual(status, 200)
        self.assertEqual(d1["recommendation"]["model"], "gemini-4-hydrogen")
        self.assertEqual(d1["recommendation"]["reasoning_effort"], "high")

        # 2. Builder retry_count=1 -> elevated xhigh
        status, _, d2 = self._post("/api/router/recommend", {
            "agent_type": "builder",
            "complexity": "medium",
            "retry_count": 1,
        })
        self.assertEqual(status, 200)
        self.assertEqual(d2["recommendation"]["model"], "gemini-4-hydrogen")
        self.assertEqual(d2["recommendation"]["reasoning_effort"], "xhigh")

        # 3. Builder retry_count=2 -> Circuit Breaker Tripped to Carbon
        status, _, d3 = self._post("/api/router/recommend", {
            "agent_type": "builder",
            "complexity": "medium",
            "retry_count": 2,
        })
        self.assertEqual(status, 200)
        self.assertEqual(d3["recommendation"]["model"], "gemini-4-carbon")
        self.assertEqual(d3["recommendation"]["reasoning_effort"], "high")
        self.assertEqual(d3["recommendation"]["circuit_breaker"]["status"], "tripped")

    def test_dashboard_html_contains_hydrogen_and_cyan(self):
        """GET / and GET /index.html serve dashboard with Hydrogen Cyan (#06b6d4) elements."""
        status, content_type, html = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", content_type)
        self.assertIn("Gemini 4 Hydrogen", html)
        self.assertIn("#06b6d4", html)
        self.assertIn("bg-cyan-500", html)
        self.assertIn("bar-hydrogen", html)
        self.assertIn("legend-hydrogen", html)
        self.assertIn("router-circuit-breaker-banner", html)
        self.assertIn("XHigh", html)


class TestHydrogenSDKAndCLISubprocess(unittest.TestCase):
    """6. Python SDK & CLI Subprocess End-to-End."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls.temp_dir.name, "hydrogen_sdk_test.db")

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

    def test_sdk_methods_hydrogen(self):
        """Verify OrchestratorClient methods for Hydrogen and Circuit Breaker."""
        client = OrchestratorClient(base_url=self.base_url)

        # 1. Update task with Hydrogen and xhigh
        res = client.update_task(
            task_id="SDK-HYDRO-01",
            agent_type="builder",
            status="running",
            progress=30,
            model="gemini-4-hydrogen",
            reasoning_effort="xhigh",
            complexity="medium",
            scope="SDK Hydrogen Verification",
        )
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["task"]["model"], "gemini-4-hydrogen")
        self.assertEqual(res["task"]["reasoning_effort"], "xhigh")

        # 2. recommend with budget_mode="speed_first"
        rec_spd = client.recommend(agent_type="builder", budget_mode="speed_first")
        self.assertEqual(rec_spd["status"], "ok")
        self.assertEqual(rec_spd["recommendation"]["model"], "gemini-4-hydrogen")

        # 3. recommend with retry_count=1 -> elevated xhigh
        rec_retry1 = client.recommend(agent_type="builder", retry_count=1)
        self.assertEqual(rec_retry1["recommendation"]["model"], "gemini-4-hydrogen")
        self.assertEqual(rec_retry1["recommendation"]["reasoning_effort"], "xhigh")

        # 4. recommend with retry_count=2 -> Circuit breaker tripped to Carbon
        rec_retry2 = client.recommend(agent_type="builder", retry_count=2)
        self.assertEqual(rec_retry2["recommendation"]["model"], "gemini-4-carbon")
        self.assertEqual(rec_retry2["recommendation"]["reasoning_effort"], "high")

    def test_cli_subprocess_hydrogen_commands(self):
        """Verify client.py CLI commands via subprocess with Hydrogen flags and Circuit Breaker."""
        cli_path = str(ORCH_DIR / "client.py")

        # 1. CLI update --model gemini-4-hydrogen --reasoning-effort xhigh
        proc = subprocess.run([
            sys.executable, cli_path, "--url", self.base_url, "update",
            "--task", "CLI-HYDRO-01",
            "--agent", "builder",
            "--status", "running",
            "--progress", "40",
            "--model", "gemini-4-hydrogen",
            "--reasoning-effort", "xhigh",
            "--complexity", "medium",
            "--scope", "CLI Subprocess Hydrogen Test",
            "--notes", "Testing Hydrogen with xhigh reasoning effort",
            "--conv-id", "conv-hydro-cli",
            "--input-tokens", "10000",
            "--output-tokens", "2500",
            "--cache-tokens", "50000",
        ], capture_output=True, text=True, check=True)
        res = json.loads(proc.stdout)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["task"]["task_id"], "CLI-HYDRO-01")
        self.assertEqual(res["task"]["model"], "gemini-4-hydrogen")
        self.assertEqual(res["task"]["reasoning_effort"], "xhigh")

        # 2. CLI models --json
        proc = subprocess.run([
            sys.executable, cli_path, "--url", self.base_url, "models", "--json"
        ], capture_output=True, text=True, check=True)
        res = json.loads(proc.stdout)
        self.assertEqual(res["status"], "ok")
        self.assertIn("gemini-4-hydrogen", res["models"])

        # 3. CLI recommend --budget-mode speed_first --retry-count 2 --json (Circuit Breaker Tripped)
        proc = subprocess.run([
            sys.executable, cli_path, "--url", self.base_url, "recommend",
            "--agent", "builder",
            "--complexity", "medium",
            "--budget-mode", "speed_first",
            "--retry-count", "2",
            "--json",
        ], capture_output=True, text=True, check=True)
        res = json.loads(proc.stdout)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["recommendation"]["model"], "gemini-4-carbon")
        self.assertEqual(res["recommendation"]["reasoning_effort"], "high")
        self.assertEqual(res["recommendation"]["circuit_breaker"]["status"], "tripped")

        # 4. CLI recommend --retry-count 1 --json (Fast Self-Heal with xhigh)
        proc = subprocess.run([
            sys.executable, cli_path, "--url", self.base_url, "recommend",
            "--agent", "builder",
            "--complexity", "medium",
            "--retry-count", "1",
            "--json",
        ], capture_output=True, text=True, check=True)
        res = json.loads(proc.stdout)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["recommendation"]["model"], "gemini-4-hydrogen")
        self.assertEqual(res["recommendation"]["reasoning_effort"], "xhigh")


if __name__ == "__main__":
    unittest.main()
