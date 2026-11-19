#!/usr/bin/env python3
"""
Model registry, tiering taxonomy, rates, and financial token calculations.
Part of Antigravity Multi-Agent Orchestrator.
"""

from __future__ import annotations

USD_TO_VND_RATE: float = 25400.0

VALID_REASONING_EFFORTS: set[str] = {"low", "medium", "high", "xhigh"}

MODEL_REGISTRY: dict[str, dict] = {
    # 1. Tier 1: Gemini 4 Carbon (Frontier Reasoning & Security Guardrail)
    "gemini-4-carbon": {
        "canonical_name": "gemini-4-carbon",
        "aliases": [
            "carbon",
            "gemini-4-carbon-preview",
            "gemini-carbon",
            "gemini-pro-orchestrator",
            "orchestrator-carbon",
        ],
        "display_name": "Gemini 4 Carbon",
        "tier": "frontier",
        "description": "Google Frontier model for deep reasoning, cybersecurity, and complex system synthesis",
        "rates": {"in": 2.00, "out": 10.00, "cache": 0.50},  # USD per 1M tokens
        "supported_reasoning_efforts": ["low", "medium", "high"],
        "default_reasoning_effort": "medium",
        "max_context_tokens": 1_048_576,
        "ui_badge": {
            "bg": "bg-emerald-950/60",
            "border": "border-emerald-500/40",
            "text": "text-emerald-300",
            "dot": "bg-emerald-400",
            "label": "Gemini 4 Carbon",
        },
        "target_personas": ["security-auditor", "spec-engineer", "debugger"],
    },

    # 2. Tier 1.5 / SWE Frontier: Gemini 4 Neon (#1 Coding-Agent & SWE Workhorse)
    "gemini-4-neon": {
        "canonical_name": "gemini-4-neon",
        "aliases": [
            "neon",
            "gemini-neon",
            "gemini-4-neon-preview",
            "gemini-pro-orchestrator-neon",
            "orchestrator-neon",
            "neco",
            "gemini-neco",
            "gemini-4-neco",
            "gemini-4-neco-preview",
            "gemini-4-neon-low",
            "gemini-4-neon-medium",
            "gemini-4-neon-high",
            "gemini-4-neon-xhigh",
        ],
        "display_name": "Gemini 4 Neon",
        "tier": "swe_frontier",
        "description": (
            "Google #1 Coding-Agent & SWE Mid-Frontier Workhorse "
            "(61 AA Intelligence, 65.2% Terminal-Bench, 90.5% SEC-bench Pro, 101-122 tok/s, 95% cache discount)"
        ),
        "rates": {"in": 3.00, "out": 15.00, "cache": 0.15},  # USD per 1M tokens (95% cache read discount)
        "supported_reasoning_efforts": ["low", "medium", "high", "xhigh"],
        "default_reasoning_effort": "high",
        "max_context_tokens": 1_048_576,
        "badge_color": "#f43f5e",
        "ui_badge": {
            "bg": "bg-rose-950/60",
            "border": "border-rose-500/40",
            "text": "text-rose-300",
            "dot": "bg-rose-400",
            "label": "Gemini 4 Neon",
            "color": "#f43f5e",
        },
        "target_personas": [
            "orchestrator",
            "spec-engineer",
            "task-planner",
            "code-reviewer",
            "debugger",
            "builder",
        ],
    },

    # 3. Tier 2 (Legacy): Gemini 4 Argon (Deep Reasoning)
    "gemini-4-argon": {
        "canonical_name": "gemini-4-argon",
        "aliases": [
            "argon",
            "pro",
            "gemini-4-argon-preview",
            "gemini-1.5-pro",
            "gemini-pro-orchestrator-argon",
            "orchestrator-argon",
        ],
        "display_name": "Gemini 4 Argon",
        "tier": "deep_reasoning",
        "legacy": True,
        "description": "Legacy deep reasoning tier superseded by Gemini 4 Neon in SWE workflows",
        "rates": {"in": 1.25, "out": 5.00, "cache": 0.3125},
        "supported_reasoning_efforts": ["low", "medium", "high"],
        "default_reasoning_effort": "medium",
        "max_context_tokens": 1_048_576,
        "ui_badge": {
            "bg": "bg-indigo-950/60",
            "border": "border-indigo-500/40",
            "text": "text-indigo-300",
            "dot": "bg-indigo-400",
            "label": "Gemini 4 Argon",
        },
        "target_personas": ["task-planner", "code-reviewer", "orchestrator"],
    },

    # 4. Tier 3: Gemini 4 Hydrogen (High-Throughput Workhorse)
    "gemini-4-hydrogen": {
        "canonical_name": "gemini-4-hydrogen",
        "aliases": [
            "hydrogen",
            "gemini-hydrogen",
            "gemini-4-hydrogen-preview",
            "gemini-4-hydrogen-low",
            "gemini-4-hydrogen-medium",
            "gemini-4-hydrogen-high",
            "gemini-4-hydrogen-xhigh",
        ],
        "display_name": "Gemini 4 Hydrogen",
        "tier": "high_throughput",
        "description": "Ultra-fast, high-throughput agentic workhorse for parallel code generation, testing, and scouting (198 tok/s, 2.5x speed)",
        "rates": {"in": 1.50, "out": 7.50, "cache": 0.075},  # USD per 1M tokens
        "supported_reasoning_efforts": ["low", "medium", "high", "xhigh"],
        "default_reasoning_effort": "medium",
        "max_context_tokens": 1_048_576,
        "ui_badge": {
            "bg": "bg-cyan-950/60",
            "border": "border-cyan-500/40",
            "text": "text-cyan-300",
            "dot": "bg-cyan-400",
            "label": "Gemini 4 Hydrogen",
        },
        "target_personas": [
            "builder",
            "test-engineer",
            "scout",
            "codebase-researcher",
            "ui-builder",
            "frontend-engineer",
        ],
    },

    # 5. Tier 4: Gemini 3.8 Flash (Cost-Efficient)
    "gemini-3.8-flash": {
        "canonical_name": "gemini-3.8-flash",
        "aliases": [
            "flash",
            "gemini-flash",
            "gemini-2.0-flash",
            "gemini-3.8-flash-low",
            "gemini-3.8-flash-medium",
            "gemini-3.8-flash-high",
        ],
        "display_name": "Gemini 3.8 Flash",
        "tier": "cost_efficient",
        "description": "Ultra-fast, cost-efficient model for docs, code simplification, and bulk scaffolding",
        "rates": {"in": 0.075, "out": 0.30, "cache": 0.01875},
        "supported_reasoning_efforts": ["low", "medium", "high"],
        "default_reasoning_effort": None,
        "max_context_tokens": 1_048_576,
        "ui_badge": {
            "bg": "bg-amber-950/60",
            "border": "border-amber-500/40",
            "text": "text-amber-300",
            "dot": "bg-amber-400",
            "label": "Gemini 3.8 Flash",
        },
        "target_personas": ["code-simplifier", "doc-generator", "observability"],
    },

    # 6. Tier 5 (Deprecated): Gemini 3.8 Flash-Lite (Retained for SQLite Backward Compatibility)
    "gemini-3.8-flash-lite": {
        "canonical_name": "gemini-3.8-flash-lite",
        "aliases": ["flash_lite", "flash-lite", "gemini-flash-lite"],
        "display_name": "Gemini 3.8 Flash-Lite",
        "tier": "ultra_fast",
        "deprecated": True,
        "description": "Deprecated micro-tier retained for historical SQLite ledger compatibility (absent from live runtime)",
        "rates": {"in": 0.0375, "out": 0.15, "cache": 0.01},
        "supported_reasoning_efforts": [],
        "default_reasoning_effort": None,
        "max_context_tokens": 1_048_576,
        "ui_badge": {
            "bg": "bg-slate-900",
            "border": "border-slate-700",
            "text": "text-slate-300",
            "dot": "bg-slate-400",
            "label": "Gemini 3.8 Flash-Lite",
        },
        "target_personas": ["observability-and-instrumentation"],
    },
}

# External Zero-API-Spend Desktop Worker Catalog (kept separate from 5-tier MODEL_REGISTRY)
EXTERNAL_WORKERS: dict[str, dict] = {
    "gemini-desktop-app": {
        "canonical_name": "gemini-desktop-app",
        "aliases": [
            "desktop",
            "gemini-app",
            "gemini-desktop",
            "gemini-desktop-bridge",
            "gui-worker",
            "desktop-worker",
            "gemini-macos-app",
            "gemini-windows-app",
        ],
        "display_name": "Gemini Desktop App",
        "tier": "external_desktop",
        "execution_mode": "desktop_bridge",
        "description": (
            "Cross-platform local Gemini Desktop GUI worker (macOS/Windows/Linux) "
            "for zero-API-cost deep synthesis and second-opinion reasoning."
        ),
        "rates": {"in": 0.0, "out": 0.0, "cache": 0.0},
        "baseline_comparison_model": "gemini-4-carbon",
        "supported_reasoning_efforts": [],
        "default_reasoning_effort": None,
        "max_context_tokens": 1_048_576,
        "ui_badge": {
            "bg": "bg-teal-950/60",
            "border": "border-teal-500/40",
            "text": "text-teal-300",
            "dot": "bg-teal-400",
            "label": "Gemini Desktop App",
        },
        "target_personas": ["spec-engineer", "code-reviewer", "debugger", "task-planner"],
    }
}

# Compatibility PRICING_TABLE
PRICING_TABLE: dict[str, dict] = {
    "carbon": MODEL_REGISTRY["gemini-4-carbon"]["rates"],
    "gemini-4-carbon": MODEL_REGISTRY["gemini-4-carbon"]["rates"],
    "gemini-carbon": MODEL_REGISTRY["gemini-4-carbon"]["rates"],
    "gemini-4-carbon-preview": MODEL_REGISTRY["gemini-4-carbon"]["rates"],
    "gemini-pro-orchestrator": MODEL_REGISTRY["gemini-4-carbon"]["rates"],
    "orchestrator-carbon": MODEL_REGISTRY["gemini-4-carbon"]["rates"],
    "neon": MODEL_REGISTRY["gemini-4-neon"]["rates"],
    "gemini-4-neon": MODEL_REGISTRY["gemini-4-neon"]["rates"],
    "gemini-neon": MODEL_REGISTRY["gemini-4-neon"]["rates"],
    "gemini-4-neon-preview": MODEL_REGISTRY["gemini-4-neon"]["rates"],
    "gemini-4-neon-low": MODEL_REGISTRY["gemini-4-neon"]["rates"],
    "gemini-4-neon-medium": MODEL_REGISTRY["gemini-4-neon"]["rates"],
    "gemini-4-neon-high": MODEL_REGISTRY["gemini-4-neon"]["rates"],
    "gemini-4-neon-xhigh": MODEL_REGISTRY["gemini-4-neon"]["rates"],
    "gemini-pro-orchestrator-neon": MODEL_REGISTRY["gemini-4-neon"]["rates"],
    "orchestrator-neon": MODEL_REGISTRY["gemini-4-neon"]["rates"],
    "neco": MODEL_REGISTRY["gemini-4-neon"]["rates"],
    "gemini-neco": MODEL_REGISTRY["gemini-4-neon"]["rates"],
    "gemini-4-neco": MODEL_REGISTRY["gemini-4-neon"]["rates"],
    "gemini-4-neco-preview": MODEL_REGISTRY["gemini-4-neon"]["rates"],
    "argon": MODEL_REGISTRY["gemini-4-argon"]["rates"],
    "pro": MODEL_REGISTRY["gemini-4-argon"]["rates"],
    "gemini-4-argon": MODEL_REGISTRY["gemini-4-argon"]["rates"],
    "gemini-1.5-pro": MODEL_REGISTRY["gemini-4-argon"]["rates"],
    "gemini-pro-orchestrator-argon": MODEL_REGISTRY["gemini-4-argon"]["rates"],
    "orchestrator-argon": MODEL_REGISTRY["gemini-4-argon"]["rates"],
    "hydrogen": MODEL_REGISTRY["gemini-4-hydrogen"]["rates"],
    "gemini-4-hydrogen": MODEL_REGISTRY["gemini-4-hydrogen"]["rates"],
    "gemini-hydrogen": MODEL_REGISTRY["gemini-4-hydrogen"]["rates"],
    "gemini-4-hydrogen-preview": MODEL_REGISTRY["gemini-4-hydrogen"]["rates"],
    "gemini-4-hydrogen-low": MODEL_REGISTRY["gemini-4-hydrogen"]["rates"],
    "gemini-4-hydrogen-medium": MODEL_REGISTRY["gemini-4-hydrogen"]["rates"],
    "gemini-4-hydrogen-high": MODEL_REGISTRY["gemini-4-hydrogen"]["rates"],
    "gemini-4-hydrogen-xhigh": MODEL_REGISTRY["gemini-4-hydrogen"]["rates"],
    "flash": MODEL_REGISTRY["gemini-3.8-flash"]["rates"],
    "gemini-flash": MODEL_REGISTRY["gemini-3.8-flash"]["rates"],
    "gemini-2.0-flash": MODEL_REGISTRY["gemini-3.8-flash"]["rates"],
    "gemini-3.8-flash": MODEL_REGISTRY["gemini-3.8-flash"]["rates"],
    "gemini-3.8-flash-low": MODEL_REGISTRY["gemini-3.8-flash"]["rates"],
    "gemini-3.8-flash-medium": MODEL_REGISTRY["gemini-3.8-flash"]["rates"],
    "gemini-3.8-flash-high": MODEL_REGISTRY["gemini-3.8-flash"]["rates"],
    "flash_lite": MODEL_REGISTRY["gemini-3.8-flash-lite"]["rates"],
    "flash-lite": MODEL_REGISTRY["gemini-3.8-flash-lite"]["rates"],
    "gemini-flash-lite": MODEL_REGISTRY["gemini-3.8-flash-lite"]["rates"],
    "gemini-3.8-flash-lite": MODEL_REGISTRY["gemini-3.8-flash-lite"]["rates"],
    "gemini-desktop-app": EXTERNAL_WORKERS["gemini-desktop-app"]["rates"],
    "desktop": EXTERNAL_WORKERS["gemini-desktop-app"]["rates"],
    "gemini-app": EXTERNAL_WORKERS["gemini-desktop-app"]["rates"],
    "gemini-desktop": EXTERNAL_WORKERS["gemini-desktop-app"]["rates"],
    "gemini-desktop-bridge": EXTERNAL_WORKERS["gemini-desktop-app"]["rates"],
    "gui-worker": EXTERNAL_WORKERS["gemini-desktop-app"]["rates"],
    "desktop-worker": EXTERNAL_WORKERS["gemini-desktop-app"]["rates"],
    "gemini-macos-app": EXTERNAL_WORKERS["gemini-desktop-app"]["rates"],
    "gemini-windows-app": EXTERNAL_WORKERS["gemini-desktop-app"]["rates"],
    "default": MODEL_REGISTRY["gemini-4-neon"]["rates"],
}


def get_all_models_catalog() -> dict[str, dict]:
    """Return combined catalog containing both 5-tier API models and external workers."""
    return {**MODEL_REGISTRY, **EXTERNAL_WORKERS}


def normalize_model_name(name: str | None) -> str:
    """Resolve aliases or raw model strings to canonical model or external worker name."""
    if not name:
        return "gemini-4-neon"
    raw = str(name).strip().lower()
    catalog = get_all_models_catalog()

    # 1. Exact match on canonical key or alias
    for canon, data in catalog.items():
        if raw == canon or raw in [a.lower() for a in data.get("aliases", [])]:
            return canon

    # 2. Substring match, sorting longest patterns first to prevent 'pro' matching 'gemini-pro-orchestrator-neon'
    patterns: list[tuple[str, str]] = []
    for canon, data in catalog.items():
        patterns.append((canon, canon))
        for alias in data.get("aliases", []):
            patterns.append((alias.lower(), canon))
    patterns.sort(key=lambda x: len(x[0]), reverse=True)

    for pattern, canon in patterns:
        if pattern in raw:
            return canon

    return "gemini-4-neon"


# Alias per contract specification
resolve_model_id = normalize_model_name


def is_external_worker(name: str | None) -> bool:
    """Return True if the model identifier resolves to an external worker (e.g. gemini-desktop-app)."""
    if not name:
        return False
    return normalize_model_name(name) in EXTERNAL_WORKERS


def extract_model_and_effort(name: str | None, effort: str | None = None) -> tuple[str, str | None]:
    """
    Extract canonical model name and implied reasoning effort.
    E.g. 'gemini-4-neon-xhigh' with effort=None -> ('gemini-4-neon', 'xhigh').
    """
    if not name:
        return "gemini-4-neon", effort

    raw = str(name).strip().lower()
    inferred_effort = effort
    catalog = get_all_models_catalog()

    # Check for suffix effort patterns: -low, -medium, -high, -xhigh
    for suffix in ["-xhigh", "-high", "-medium", "-low"]:
        if raw.endswith(suffix):
            cand_canon = normalize_model_name(raw[: -len(suffix)])
            if cand_canon in catalog:
                eff = suffix.lstrip("-")
                if not inferred_effort:
                    inferred_effort = eff
                return cand_canon, inferred_effort

    canon = normalize_model_name(raw)
    return canon, inferred_effort


def compute_cost(model: str | None, in_tok: int, out_tok: int, cache_tok: int) -> dict:
    """Calculate actual cost and cache savings in USD and VND."""
    canon = normalize_model_name(model)
    catalog = get_all_models_catalog()
    rates = catalog[canon]["rates"]

    in_val = int(in_tok or 0)
    out_val = int(out_tok or 0)
    cache_val = int(cache_tok or 0)

    in_cost = (in_val / 1_000_000.0) * rates["in"]
    out_cost = (out_val / 1_000_000.0) * rates["out"]
    cache_cost = (cache_val / 1_000_000.0) * rates["cache"]
    actual_usd = in_cost + out_cost + cache_cost

    baseline_usd = ((in_val + cache_val) / 1_000_000.0) * rates["in"] + out_cost
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


def compute_desktop_quota_saved(
    input_chars: int,
    output_chars: int,
    baseline_model: str = "gemini-4-carbon",
) -> dict:
    """Estimate equivalent API spend saved (USD & VND) by offloading to Gemini Desktop App."""
    est_in = (max(0, int(input_chars or 0)) + 3) // 4
    est_out = (max(0, int(output_chars or 0)) + 3) // 4
    canon_base = normalize_model_name(baseline_model)
    rates = MODEL_REGISTRY.get(canon_base, MODEL_REGISTRY["gemini-4-carbon"])["rates"]
    saved_usd = round((est_in / 1_000_000.0) * rates["in"] + (est_out / 1_000_000.0) * rates["out"], 4)
    saved_vnd = round(saved_usd * USD_TO_VND_RATE)
    return {
        "est_input_tokens": est_in,
        "est_output_tokens": est_out,
        "est_total_tokens": est_in + est_out,
        "baseline_model": canon_base,
        "saved_usd": saved_usd,
        "saved_vnd": saved_vnd,
    }


def get_model_metadata(model: str | None) -> dict:
    """Return model configuration and metadata for given model or external worker identifier."""
    canon = normalize_model_name(model)
    return get_all_models_catalog()[canon]


def validate_reasoning_effort(model: str | None, effort: str | None, clamp: bool = False) -> tuple[bool, str | None]:
    """
    Validate reasoning effort for a model.
    'xhigh' is natively allowed on gemini-4-neon and gemini-4-hydrogen.
    For Carbon and Argon:
      - If clamp=True: clamps 'xhigh' -> 'high'.
      - If clamp=False: returns (False, None) for 'xhigh' on models not supporting it.
    Returns (is_valid, normalized_effort).
    """
    if effort is None or effort == "":
        return True, None
    clean_effort = str(effort).strip().lower()
    if clean_effort not in VALID_REASONING_EFFORTS:
        return False, None

    canon = normalize_model_name(model)
    supported = get_all_models_catalog()[canon].get("supported_reasoning_efforts", [])

    if clean_effort in supported:
        return True, clean_effort

    # Clamping policy for Carbon & Argon when xhigh is supplied
    if clean_effort == "xhigh" and clamp and canon in ("gemini-4-carbon", "gemini-4-argon"):
        return True, "high"

    return False, None
