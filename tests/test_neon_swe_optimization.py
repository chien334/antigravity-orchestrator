#!/usr/bin/env python3
"""
Comprehensive Automated Test Suite for Gemini 4 Neon SWE Fleet Optimization.
Validates:
1. Neon Catalog, Pricing & Alias Normalization ($3.00/$15.00/$0.15, 95% cache savings,
   USD/VND math, 'neon'/'neco'/'gemini-pro-orchestrator-neon' aliases, suffix effort extraction)
2. SWE-Optimized Smart Router Matrix (Rule 3 Neon SWE Brain & multi-file builders >=4 files,
   Rule 4 Hydrogen bounded workers <=3 files, Rule 5 retiring 3.8-flash-lite to 3.8-flash)
3. 3-Stage SWE Circuit Breaker (retry 0/1 Hydrogen -> retry 2 Neon -> retry 3+ Carbon)
4. Uncompromised Rule 1 Security Guardrail (Carbon high + fallback_model='gemini-4-neon')
5. Live Ephemeral Server, Dashboard #f43f5e Badge Precedence & CLI Subprocess E2E
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ORCH_DIR = REPO_ROOT / "packages" / "orchestrator"

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(ORCH_DIR))

from client import OrchestratorClient
from models import (
    EXTERNAL_WORKERS,
    MODEL_REGISTRY,
    PRICING_TABLE,
    USD_TO_VND_RATE,
    compute_cost,
    extract_model_and_effort,
    get_model_metadata,
    normalize_model_name,
    resolve_model_id,
    validate_reasoning_effort,
)
from router import recommend_model
from server import (
    GLOBAL_STORE,
    OrchestratorHandler,
    ThreadingHTTPServer,
)


class TestNeonCatalogPricingAndAliases(unittest.TestCase):
    """1. Neon Catalog, Pricing Math, Alias Normalization & Reasoning Effort."""

    def test_neon_model_registration(self):
        """Verify gemini-4-neon registration in MODEL_REGISTRY with SWE Frontier metadata."""
        self.assertEqual(len(MODEL_REGISTRY), 6)
        self.assertIn("gemini-4-neon", MODEL_REGISTRY)

        meta = MODEL_REGISTRY["gemini-4-neon"]
        self.assertEqual(meta["canonical_name"], "gemini-4-neon")
        self.assertEqual(meta["display_name"], "Gemini 4 Neon")
        self.assertEqual(meta["tier"], "swe_frontier")
        self.assertEqual(meta["rates"], {"in": 3.00, "out": 15.00, "cache": 0.15})
        self.assertEqual(meta["supported_reasoning_efforts"], ["low", "medium", "high", "xhigh"])
        self.assertEqual(meta["default_reasoning_effort"], "high")
        self.assertEqual(meta["max_context_tokens"], 1_048_576)
        self.assertEqual(meta["badge_color"], "#f43f5e")
        self.assertEqual(meta["ui_badge"]["color"], "#f43f5e")
        self.assertEqual(meta["ui_badge"]["label"], "Gemini 4 Neon")
        for persona in ["orchestrator", "spec-engineer", "task-planner", "code-reviewer", "debugger", "builder"]:
            self.assertIn(persona, meta["target_personas"])

        meta_alias = get_model_metadata("gemini-4-neco")
        self.assertEqual(meta_alias["canonical_name"], "gemini-4-neon")

    def test_neon_aliases_and_longest_pattern_precedence(self):
        """Verify Neon/Neco/Orchestrator aliases and longest-pattern-first substring safety."""
        neon_aliases = [
            "neon",
            "NEON",
            "neco",
            "NECO",
            "gemini-4-neco",
            "gemini-neco",
            "gemini-4-neco-preview",
            "gemini-neon",
            "gemini-4-neon",
            "gemini-4-neon-preview",
            "gemini-pro-orchestrator-neon",
            "orchestrator-neon",
            "gemini-4-neon-low",
            "gemini-4-neon-medium",
            "gemini-4-neon-high",
            "gemini-4-neon-xhigh",
        ]
        for alias in neon_aliases:
            self.assertEqual(normalize_model_name(alias), "gemini-4-neon", f"Failed alias: {alias}")
            self.assertEqual(resolve_model_id(alias), "gemini-4-neon", f"Failed resolve_model_id: {alias}")

        # Ensure 'pro' substring in gemini-pro-orchestrator-neon does NOT match Argon!
        self.assertEqual(normalize_model_name("gemini-pro-orchestrator-neon"), "gemini-4-neon")
        self.assertEqual(normalize_model_name("gemini-pro-orchestrator"), "gemini-4-carbon")
        self.assertEqual(normalize_model_name("gemini-pro-orchestrator-argon"), "gemini-4-argon")

        # Default / unknown fallback normalizes to gemini-4-neon
        self.assertEqual(normalize_model_name(None), "gemini-4-neon")
        self.assertEqual(normalize_model_name("unknown-model-xyz"), "gemini-4-neon")

    def test_neon_suffix_extraction_and_effort_validation(self):
        """Verify suffix effort extraction and xhigh support on gemini-4-neon."""
        for suffix in ["low", "medium", "high", "xhigh"]:
            canon, effort = extract_model_and_effort(f"gemini-4-neon-{suffix}")
            self.assertEqual(canon, "gemini-4-neon")
            self.assertEqual(effort, suffix)

        # Explicit effort parameter overrides suffix
        canon_ovr, effort_ovr = extract_model_and_effort("gemini-4-neon-xhigh", effort="medium")
        self.assertEqual(canon_ovr, "gemini-4-neon")
        self.assertEqual(effort_ovr, "medium")

        # Neco & orchestrator aliases without suffix
        self.assertEqual(extract_model_and_effort("gemini-4-neco"), ("gemini-4-neon", None))
        self.assertEqual(extract_model_and_effort("gemini-pro-orchestrator-neon"), ("gemini-4-neon", None))

        # Reasoning effort validation
        for effort in ["low", "medium", "high", "xhigh"]:
            valid, norm = validate_reasoning_effort("gemini-4-neon", effort)
            self.assertTrue(valid)
            self.assertEqual(norm, effort)

        valid_bad, norm_bad = validate_reasoning_effort("gemini-4-neon", "ultra")
        self.assertFalse(valid_bad)
        self.assertIsNone(norm_bad)

        # Carbon & Argon still clamp xhigh -> high only when clamp=True
        self.assertEqual(validate_reasoning_effort("gemini-4-carbon", "xhigh", clamp=False), (False, None))
        self.assertEqual(validate_reasoning_effort("gemini-4-carbon", "xhigh", clamp=True), (True, "high"))
        self.assertEqual(validate_reasoning_effort("gemini-4-argon", "xhigh", clamp=True), (True, "high"))

    def test_neon_pricing_table_and_cost_math_usd_and_vnd(self):
        """Verify $3.00 in / $15.00 out / $0.15 cache read (95% discount) USD & VND math."""
        expected_rates = {"in": 3.00, "out": 15.00, "cache": 0.15}
        for key in [
            "neon",
            "neco",
            "gemini-4-neon",
            "gemini-4-neco",
            "gemini-pro-orchestrator-neon",
            "gemini-4-neon-xhigh",
            "default",
        ]:
            self.assertEqual(PRICING_TABLE[key], expected_rates)

        # 1M input ($3.00) + 1M output ($15.00) + 1M cache ($0.15) = $18.15
        # Baseline without cache discount: 2M input ($6.00) + 1M output ($15.00) = $21.00
        # Saved: $2.85 (95% discount on 1M cached input tokens)
        cost = compute_cost("gemini-4-neon", 1_000_000, 1_000_000, 1_000_000)
        self.assertEqual(cost["usd"], 18.15)
        self.assertEqual(cost["vnd"], round(18.15 * USD_TO_VND_RATE))
        self.assertEqual(cost["saved_usd"], 2.85)
        self.assertEqual(cost["saved_vnd"], round(2.85 * USD_TO_VND_RATE))
        self.assertEqual(cost["rates"], expected_rates)

        # Realistic SWE task slice: 200k in ($0.60), 50k out ($0.75), 400k cache ($0.06) -> $1.41
        # Baseline: 600k in ($1.80) + 50k out ($0.75) = $2.55 -> saved $1.14
        cost_slice = compute_cost("gemini-4-neco", 200_000, 50_000, 400_000)
        self.assertEqual(cost_slice["usd"], 1.41)
        self.assertEqual(cost_slice["vnd"], round(1.41 * USD_TO_VND_RATE))
        self.assertEqual(cost_slice["saved_usd"], 1.14)
        self.assertEqual(cost_slice["saved_vnd"], round(1.14 * USD_TO_VND_RATE))

        cost_zero = compute_cost("neon", 0, 0, 0)
        self.assertEqual(cost_zero["usd"], 0.0)
        self.assertEqual(cost_zero["vnd"], 0)


class TestNeonSWERouterMatrix(unittest.TestCase):
    """2. SWE-Optimized Router Matrix across Personas, File Counts & Budget Modes."""

    def test_rule3_swe_brain_and_multifile_builder_balanced(self):
        """Verify orchestrator, spec, planner, reviewer, non-critical debugger & multi-file builders route to Neon."""
        expected_efforts = {
            "orchestrator": "medium",
            "task-planner": "medium",
            "performance-auditor": "medium",
            "spec-engineer": "high",
            "code-reviewer": "high",
            "debugger": "high",
        }
        for agent, exp_effort in expected_efforts.items():
            rec = recommend_model(agent, complexity="medium", budget_mode="balanced")["recommendation"]
            self.assertEqual(rec["model"], "gemini-4-neon", f"Agent {agent} should route to Neon")
            self.assertEqual(rec["reasoning_effort"], exp_effort, f"Agent {agent} effort mismatch")
            self.assertEqual(rec["tier"], "swe_frontier")
            self.assertEqual(rec["fallback_model"], "gemini-4-hydrogen")

        # Non-critical high complexity debugger uses Neon (not Carbon)
        rec_dbg_high = recommend_model("debugger", complexity="high")["recommendation"]
        self.assertEqual(rec_dbg_high["model"], "gemini-4-neon")
        self.assertEqual(rec_dbg_high["reasoning_effort"], "high")

        # Multi-file builder / ui-builder / frontend-engineer (file_count >= 4) -> Neon
        for agent in ["builder", "ui-builder", "frontend-engineer"]:
            rec_mf = recommend_model(agent, complexity="medium", file_count=4)["recommendation"]
            self.assertEqual(rec_mf["model"], "gemini-4-neon", f"{agent} file_count=4 should route to Neon")
            self.assertEqual(rec_mf["tier"], "swe_frontier")

    def test_rule4_bounded_workers_balanced_quality_and_cost_saving(self):
        """Verify bounded builder (<=3 files), ui-builder, test-engineer, scout use Hydrogen and scale per budget_mode."""
        for agent, comp, exp_eff in [
            ("builder", "medium", "high"),
            ("ui-builder", "medium", "high"),
            ("test-engineer", "medium", "high"),
            ("scout", "low", "low"),
        ]:
            rec_bal = recommend_model(agent, complexity=comp, file_count=3, budget_mode="balanced")["recommendation"]
            self.assertEqual(rec_bal["model"], "gemini-4-hydrogen")
            self.assertEqual(rec_bal["reasoning_effort"], exp_eff)
            self.assertEqual(rec_bal["tier"], "high_throughput")

            rec_qf = recommend_model(agent, complexity=comp, file_count=3, budget_mode="quality_first")["recommendation"]
            self.assertEqual(rec_qf["model"], "gemini-4-neon")
            self.assertEqual(rec_qf["reasoning_effort"], "high")
            self.assertEqual(rec_qf["tier"], "swe_frontier")

            rec_cs = recommend_model(agent, complexity=comp, file_count=3, budget_mode="cost_saving")["recommendation"]
            self.assertEqual(rec_cs["model"], "gemini-3.8-flash")
            self.assertIsNone(rec_cs["reasoning_effort"])
            self.assertEqual(rec_cs["tier"], "cost_efficient")

    def test_rule3_budget_modes_quality_speed_cost(self):
        """Verify quality_first, speed_first, and cost_saving behavior on Rule 3 SWE Brain personas."""
        # quality_first: code-reviewer & multi-file builder -> Neon (xhigh); spec/planner/debugger -> Carbon
        rec_rev_qf = recommend_model("code-reviewer", complexity="medium", budget_mode="quality_first")["recommendation"]
        self.assertEqual(rec_rev_qf["model"], "gemini-4-neon")
        self.assertEqual(rec_rev_qf["reasoning_effort"], "xhigh")

        rec_mf_qf = recommend_model("builder", complexity="medium", file_count=5, budget_mode="quality_first")["recommendation"]
        self.assertEqual(rec_mf_qf["model"], "gemini-4-neon")
        self.assertEqual(rec_mf_qf["reasoning_effort"], "xhigh")

        rec_spec_qf = recommend_model("spec-engineer", complexity="high", budget_mode="quality_first")["recommendation"]
        self.assertEqual(rec_spec_qf["model"], "gemini-4-carbon")
        self.assertEqual(rec_spec_qf["fallback_model"], "gemini-4-neon")

        # speed_first: code-reviewer & multi-file builder -> Hydrogen (xhigh); planner -> Neon (low)
        rec_rev_sf = recommend_model("code-reviewer", complexity="medium", budget_mode="speed_first")["recommendation"]
        self.assertEqual(rec_rev_sf["model"], "gemini-4-hydrogen")
        self.assertEqual(rec_rev_sf["reasoning_effort"], "xhigh")

        rec_plan_sf = recommend_model("task-planner", complexity="medium", budget_mode="speed_first")["recommendation"]
        self.assertEqual(rec_plan_sf["model"], "gemini-4-neon")
        self.assertEqual(rec_plan_sf["reasoning_effort"], "low")

        # cost_saving: orchestrator retains Neon (low); other Rule 3 personas offload to Hydrogen (high/xhigh)
        rec_orch_cs = recommend_model("orchestrator", complexity="medium", budget_mode="cost_saving")["recommendation"]
        self.assertEqual(rec_orch_cs["model"], "gemini-4-neon")
        self.assertEqual(rec_orch_cs["reasoning_effort"], "low")

        rec_spec_cs = recommend_model("spec-engineer", complexity="high", budget_mode="cost_saving")["recommendation"]
        self.assertEqual(rec_spec_cs["model"], "gemini-4-hydrogen")
        self.assertEqual(rec_spec_cs["reasoning_effort"], "xhigh")

    def test_rule5_micro_tier_retires_flash_lite(self):
        """Confirm code-simplifier, doc-generator & observability route to 3.8-flash and never 3.8-flash-lite."""
        for agent in ["code-simplifier", "doc-generator", "observability", "observability-and-instrumentation"]:
            for mode in ["balanced", "cost_saving", "quality_first"]:
                rec = recommend_model(agent, complexity="low", budget_mode=mode)["recommendation"]
                self.assertEqual(rec["model"], "gemini-3.8-flash")
                self.assertNotEqual(rec["model"], "gemini-3.8-flash-lite")

            rec_sf = recommend_model(agent, complexity="low", budget_mode="speed_first")["recommendation"]
            self.assertEqual(rec_sf["model"], "gemini-4-hydrogen")
            self.assertEqual(rec_sf["reasoning_effort"], "low")


class TestNeonCircuitBreakerAndSecurityGuardrail(unittest.TestCase):
    """3. 3-Stage SWE Circuit Breaker & Rule 1 Security Guardrail."""

    def test_three_stage_swe_circuit_breaker(self):
        """Verify retry 0 -> hydrogen, retry 1 -> hydrogen(xhigh), retry 2 -> neon(high), retry 3+ -> carbon(high)."""
        r0 = recommend_model("builder", complexity="medium", retry_count=0)["recommendation"]
        self.assertEqual(r0["model"], "gemini-4-hydrogen")
        self.assertEqual(r0["circuit_breaker"]["stage"], 0)
        self.assertEqual(r0["circuit_breaker"]["escalate_to"], "gemini-4-neon")

        r1 = recommend_model("builder", complexity="medium", retry_count=1)["recommendation"]
        self.assertEqual(r1["model"], "gemini-4-hydrogen")
        self.assertEqual(r1["reasoning_effort"], "xhigh")
        self.assertEqual(r1["circuit_breaker"]["stage"], 1)
        self.assertEqual(r1["circuit_breaker"]["status"], "retrying")
        self.assertEqual(r1["circuit_breaker"]["escalate_to"], "gemini-4-neon")

        r2 = recommend_model("builder", complexity="medium", retry_count=2)["recommendation"]
        self.assertEqual(r2["model"], "gemini-4-neon")
        self.assertEqual(r2["reasoning_effort"], "high")
        self.assertEqual(r2["tier"], "swe_frontier")
        self.assertEqual(r2["fallback_model"], "gemini-4-carbon")
        self.assertEqual(r2["circuit_breaker"]["stage"], 2)
        self.assertEqual(r2["circuit_breaker"]["status"], "tripped")
        self.assertEqual(r2["circuit_breaker"]["escalated_from"], "gemini-4-hydrogen")
        self.assertEqual(r2["circuit_breaker"]["escalated_to"], "gemini-4-neon")

        for retry in [3, 5]:
            r3 = recommend_model("builder", complexity="medium", retry_count=retry, budget_mode="cost_saving")["recommendation"]
            self.assertEqual(r3["model"], "gemini-4-carbon")
            self.assertEqual(r3["reasoning_effort"], "high")
            self.assertEqual(r3["tier"], "frontier")
            self.assertEqual(r3["fallback_model"], "gemini-4-neon")
            self.assertEqual(r3["circuit_breaker"]["stage"], 3)
            self.assertEqual(r3["circuit_breaker"]["status"], "tripped")
            self.assertEqual(r3["circuit_breaker"]["escalated_from"], "gemini-4-neon")
            self.assertEqual(r3["circuit_breaker"]["escalated_to"], "gemini-4-carbon")

    def test_rule1_security_guardrail_uncompromised_with_neon_fallback(self):
        """Verify security triggers stay locked on gemini-4-carbon (high) with fallback_model='gemini-4-neon'."""
        cases = [
            {"agent_type": "security-auditor", "complexity": "low", "budget_mode": "cost_saving"},
            {"agent_type": "builder", "complexity": "low", "has_security_impact": True, "budget_mode": "speed_first"},
            {"agent_type": "task-planner", "complexity": "critical", "budget_mode": "offload_heavy_to_desktop", "desktop_available": True},
            {"agent_type": "debugger", "complexity": "critical", "retry_count": 2},
        ]
        for kwargs in cases:
            rec = recommend_model(**kwargs)["recommendation"]
            self.assertEqual(rec["model"], "gemini-4-carbon")
            self.assertEqual(rec["reasoning_effort"], "high")
            self.assertEqual(rec["tier"], "frontier")
            self.assertEqual(rec["fallback_model"], "gemini-4-neon")

        for kw in ["auth", "crypto", "owasp", "cve", "migration"]:
            rec_kw = recommend_model(
                agent_type="builder",
                complexity="low",
                scope=f"Patch {kw} handler",
                budget_mode="cost_saving",
            )["recommendation"]
            self.assertEqual(rec_kw["model"], "gemini-4-carbon")
            self.assertEqual(rec_kw["reasoning_effort"], "high")
            self.assertEqual(rec_kw["fallback_model"], "gemini-4-neon")


class TestNeonServerDashboardAndCLIE2E(unittest.TestCase):
    """4. Ephemeral Server, Dashboard #f43f5e Badge Precedence & CLI Subprocess E2E."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls.temp_dir.name, "neon_e2e_test.db")

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
        with urllib.request.urlopen(req, timeout=5) as resp:
            ct = resp.headers.get("Content-Type", "")
            raw = resp.read().decode("utf-8")
            return resp.status, ct, (json.loads(raw) if "application/json" in ct else raw)

    def _post(self, path: str, payload: dict):
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            ct = resp.headers.get("Content-Type", "")
            raw = resp.read().decode("utf-8")
            return resp.status, ct, json.loads(raw)

    def test_get_models_and_post_tasks_neon_aliases(self):
        """Verify GET /api/models, POST /api/tasks normalization & costs, analytics, and audit export."""
        st, _, models_res = self._get("/api/models")
        self.assertEqual(st, 200)
        self.assertEqual(len(models_res["models"]), 6)
        self.assertIn("gemini-4-neon", models_res["models"])
        neon_meta = models_res["models"]["gemini-4-neon"]
        self.assertEqual(neon_meta["rates"], {"in": 3.00, "out": 15.00, "cache": 0.15})
        self.assertEqual(neon_meta["badge_color"], "#f43f5e")
        self.assertEqual(neon_meta["supported_reasoning_efforts"], ["low", "medium", "high", "xhigh"])
        self.assertEqual(len(models_res["external_workers"]), len(EXTERNAL_WORKERS))

        # POST /api/tasks with gemini-pro-orchestrator-neon
        st1, _, t1 = self._post("/api/tasks", {
            "task_id": "NEON-ORCH-01",
            "agent_type": "orchestrator",
            "model": "gemini-pro-orchestrator-neon",
            "status": "completed",
            "progress": 100,
            "input_tokens": 1_000_000,
            "output_tokens": 1_000_000,
            "cache_tokens": 1_000_000,
        })
        self.assertEqual(st1, 200)
        self.assertEqual(t1["task"]["model"], "gemini-4-neon")
        self.assertEqual(t1["task"]["cost"]["usd"], 18.15)
        self.assertEqual(t1["task"]["cost"]["saved_usd"], 2.85)
        self.assertEqual(t1["task"]["cost"]["vnd"], round(18.15 * USD_TO_VND_RATE))

        # POST /api/tasks with gemini-4-neco and suffix gemini-4-neon-xhigh
        st2, _, t2 = self._post("/api/tasks", {
            "task_id": "NEON-NECO-01",
            "agent_type": "code-reviewer",
            "model": "gemini-4-neco",
            "reasoning_effort": "high",
            "status": "running",
            "progress": 50,
        })
        self.assertEqual(st2, 200)
        self.assertEqual(t2["task"]["model"], "gemini-4-neon")
        self.assertEqual(t2["task"]["reasoning_effort"], "high")

        st3, _, t3 = self._post("/api/tasks", {
            "task_id": "NEON-XHIGH-01",
            "agent_type": "debugger",
            "model": "gemini-4-neon-xhigh",
            "status": "running",
            "progress": 25,
        })
        self.assertEqual(st3, 200)
        self.assertEqual(t3["task"]["model"], "gemini-4-neon")
        self.assertEqual(t3["task"]["reasoning_effort"], "xhigh")

        # Analytics & Audit Export reflect gemini-4-neon
        _, _, ana = self._get("/api/analytics/models")
        self.assertEqual(ana["models"]["gemini-4-neon"]["task_count"], 3)
        self.assertEqual(ana["models"]["gemini-4-neon"]["cost_usd"], 18.15)

        _, _, exp_json = self._get("/api/audit/export?format=json")
        self.assertEqual(exp_json["model_analytics"]["models"]["gemini-4-neon"]["task_count"], 3)

    def test_post_router_recommend_neon_swe_matrix(self):
        """Verify POST /api/router/recommend across SWE Neon matrix, CB stages, and Rule 1."""
        # Task planner -> Neon (medium)
        _, _, r_plan = self._post("/api/router/recommend", {"agent_type": "task-planner", "complexity": "high"})
        self.assertEqual(r_plan["recommendation"]["model"], "gemini-4-neon")
        self.assertEqual(r_plan["recommendation"]["reasoning_effort"], "medium")

        # Multi-file builder (file_count=5) -> Neon
        _, _, r_mf = self._post("/api/router/recommend", {"agent_type": "builder", "complexity": "medium", "file_count": 5})
        self.assertEqual(r_mf["recommendation"]["model"], "gemini-4-neon")

        # Bounded builder (file_count=2) -> Hydrogen
        _, _, r_bnd = self._post("/api/router/recommend", {"agent_type": "builder", "complexity": "medium", "file_count": 2})
        self.assertEqual(r_bnd["recommendation"]["model"], "gemini-4-hydrogen")

        # Circuit breaker Stage 2 (retry_count=2) -> Neon, Stage 3 (retry_count=3) -> Carbon
        _, _, r_cb2 = self._post("/api/router/recommend", {"agent_type": "builder", "retry_count": 2})
        self.assertEqual(r_cb2["recommendation"]["model"], "gemini-4-neon")
        self.assertEqual(r_cb2["recommendation"]["circuit_breaker"]["stage"], 2)

        _, _, r_cb3 = self._post("/api/router/recommend", {"agent_type": "builder", "retry_count": 3})
        self.assertEqual(r_cb3["recommendation"]["model"], "gemini-4-carbon")
        self.assertEqual(r_cb3["recommendation"]["circuit_breaker"]["stage"], 3)

        # Rule 1 security -> Carbon with fallback_model='gemini-4-neon'
        _, _, r_sec = self._post("/api/router/recommend", {"agent_type": "builder", "scope": "auth owasp audit"})
        self.assertEqual(r_sec["recommendation"]["model"], "gemini-4-carbon")
        self.assertEqual(r_sec["recommendation"]["fallback_model"], "gemini-4-neon")

    def test_dashboard_html_neon_rose_and_badge_precedence(self):
        """Verify Dashboard HTML renders #f43f5e Neon markers and checks neon before argon/pro."""
        st, ct, html = self._get("/")
        self.assertEqual(st, 200)
        self.assertIn("text/html", ct)
        self.assertIn("#f43f5e", html)
        self.assertIn("Gemini 4 Neon", html)
        self.assertIn('id="bar-neon"', html)
        self.assertIn('id="legend-neon"', html)
        self.assertIn('<option value="neon">', html)

        # Badge precedence inside getModelBadge(): m.includes('neon') MUST precede m.includes('argon')
        fn_start = html.find("function getModelBadge")
        self.assertNotEqual(fn_start, -1)
        fn_body = html[fn_start : fn_start + 2500]
        neon_idx = fn_body.find("m.includes('neon')")
        argon_idx = fn_body.find("m.includes('argon')")
        self.assertNotEqual(neon_idx, -1)
        self.assertNotEqual(argon_idx, -1)
        self.assertLess(
            neon_idx,
            argon_idx,
            "getModelBadge must check m.includes('neon') before m.includes('argon') || m.includes('pro')",
        )

    def test_sdk_and_cli_subprocess_neon_e2e(self):
        """Verify OrchestratorClient SDK and client.py subprocess calls for Neon SWE routing."""
        client = OrchestratorClient(base_url=self.base_url)

        sdk_task = client.update_task(
            task_id="SDK-NEON-01",
            agent_type="code-reviewer",
            status="running",
            progress=45,
            model="gemini-pro-orchestrator-neon",
            reasoning_effort="xhigh",
            scope="SDK Neon SWE verification",
        )
        self.assertEqual(sdk_task["status"], "ok")
        self.assertEqual(sdk_task["task"]["model"], "gemini-4-neon")
        self.assertEqual(sdk_task["task"]["reasoning_effort"], "xhigh")

        cli_path = str(ORCH_DIR / "client.py")

        # 1. CLI update --model gemini-4-neco
        proc_upd = subprocess.run(
            [
                sys.executable, cli_path, "--url", self.base_url, "update",
                "--task", "CLI-NEON-01",
                "--agent", "task-planner",
                "--status", "running",
                "--progress", "60",
                "--model", "gemini-4-neco",
                "--reasoning-effort", "high",
                "--scope", "CLI Neco alias test",
            ],
            capture_output=True, text=True, check=True,
        )
        upd_json = json.loads(proc_upd.stdout)
        self.assertEqual(upd_json["task"]["model"], "gemini-4-neon")
        self.assertEqual(upd_json["task"]["reasoning_effort"], "high")

        # 2. CLI models --json
        proc_mod = subprocess.run(
            [sys.executable, cli_path, "--url", self.base_url, "models", "--json"],
            capture_output=True, text=True, check=True,
        )
        mod_json = json.loads(proc_mod.stdout)
        self.assertIn("gemini-4-neon", mod_json["models"])
        self.assertEqual(mod_json["models"]["gemini-4-neon"]["rates"]["cache"], 0.15)

        # 3. CLI recommend --agent task-planner --json -> gemini-4-neon
        proc_plan = subprocess.run(
            [
                sys.executable, cli_path, "--url", self.base_url, "recommend",
                "--agent", "task-planner", "--complexity", "high", "--json",
            ],
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(json.loads(proc_plan.stdout)["recommendation"]["model"], "gemini-4-neon")

        # 4. CLI recommend --agent builder --files 5 --json -> gemini-4-neon
        proc_mf = subprocess.run(
            [
                sys.executable, cli_path, "--url", self.base_url, "recommend",
                "--agent", "builder", "--complexity", "medium", "--files", "5", "--json",
            ],
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(json.loads(proc_mf.stdout)["recommendation"]["model"], "gemini-4-neon")

        # 5. CLI recommend --agent builder --retry-count 2 --json -> gemini-4-neon (Stage 2)
        proc_cb2 = subprocess.run(
            [
                sys.executable, cli_path, "--url", self.base_url, "recommend",
                "--agent", "builder", "--retry-count", "2", "--json",
            ],
            capture_output=True, text=True, check=True,
        )
        cb2 = json.loads(proc_cb2.stdout)["recommendation"]
        self.assertEqual(cb2["model"], "gemini-4-neon")
        self.assertEqual(cb2["circuit_breaker"]["stage"], 2)

        # 6. CLI recommend --agent builder --retry-count 3 --json -> gemini-4-carbon (Stage 3)
        proc_cb3 = subprocess.run(
            [
                sys.executable, cli_path, "--url", self.base_url, "recommend",
                "--agent", "builder", "--retry-count", "3", "--json",
            ],
            capture_output=True, text=True, check=True,
        )
        cb3 = json.loads(proc_cb3.stdout)["recommendation"]
        self.assertEqual(cb3["model"], "gemini-4-carbon")
        self.assertEqual(cb3["circuit_breaker"]["stage"], 3)


if __name__ == "__main__":
    unittest.main()
