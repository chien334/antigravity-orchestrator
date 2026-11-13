#!/usr/bin/env python3
"""
Model registry, tiering taxonomy, rates, and financial token calculations.
Part of Antigravity Multi-Agent Orchestrator.
"""

from __future__ import annotations

USD_TO_VND_RATE: float = 25400.0

VALID_REASONING_EFFORTS: set[str] = {"low", "medium", "high", "xhigh"}

MODEL_REGISTRY: dict[str, dict] = {
    # 1. Tier 1: Gemini 4 Carbon (Frontier Reasoning)
    "gemini-4-carbon": {
        "canonical_name": "gemini-4-carbon",
        "aliases": ["carbon", "gemini-4-carbon-preview", "gemini-carbon"],
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

    # 2. Tier 2: Gemini 4 Argon (Deep Reasoning)
    "gemini-4-argon": {
        "canonical_name": "gemini-4-argon",
        "aliases": ["argon", "pro", "gemini-4-argon-preview", "gemini-1.5-pro"],
        "display_name": "Gemini 4 Argon",
        "tier": "deep_reasoning",
        "description": "High-velocity deep reasoning for architecture, reviews, and task scheduling",
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

    # 3. Tier 3: Gemini 4 Hydrogen (High-Throughput Workhorse - NEW)
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

    # 4. Tier 4: Gemini 3.8 Flash (Cost-Efficient)
    "gemini-3.8-flash": {
        "canonical_name": "gemini-3.8-flash",
        "aliases": ["flash", "gemini-flash", "gemini-2.0-flash"],
        "display_name": "Gemini 3.8 Flash",
        "tier": "cost_efficient",
        "description": "Ultra-fast, high-throughput model for parallel code implementation and test suites",
        "rates": {"in": 0.075, "out": 0.30, "cache": 0.01875},
        "supported_reasoning_efforts": [],
        "default_reasoning_effort": None,
        "max_context_tokens": 1_048_576,
        "ui_badge": {
            "bg": "bg-amber-950/60",
            "border": "border-amber-500/40",
            "text": "text-amber-300",
            "dot": "bg-amber-400",
            "label": "Gemini 3.8 Flash",
        },
        "target_personas": ["code-simplifier", "doc-generator"],
    },

    # 5. Tier 5: Gemini 3.8 Flash-Lite (Ultra-Fast Telemetry)
    "gemini-3.8-flash-lite": {
        "canonical_name": "gemini-3.8-flash-lite",
        "aliases": ["flash_lite", "flash-lite", "gemini-flash-lite"],
        "display_name": "Gemini 3.8 Flash-Lite",
        "tier": "ultra_fast",
        "description": "Low-latency micro-tier for telemetry heartbeats, quick formatting, and linting",
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

# Compatibility PRICING_TABLE
PRICING_TABLE: dict[str, dict] = {
    "carbon": MODEL_REGISTRY["gemini-4-carbon"]["rates"],
    "gemini-4-carbon": MODEL_REGISTRY["gemini-4-carbon"]["rates"],
    "gemini-carbon": MODEL_REGISTRY["gemini-4-carbon"]["rates"],
    "gemini-4-carbon-preview": MODEL_REGISTRY["gemini-4-carbon"]["rates"],
    "argon": MODEL_REGISTRY["gemini-4-argon"]["rates"],
    "pro": MODEL_REGISTRY["gemini-4-argon"]["rates"],
    "gemini-4-argon": MODEL_REGISTRY["gemini-4-argon"]["rates"],
    "gemini-1.5-pro": MODEL_REGISTRY["gemini-4-argon"]["rates"],
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
    "flash_lite": MODEL_REGISTRY["gemini-3.8-flash-lite"]["rates"],
    "flash-lite": MODEL_REGISTRY["gemini-3.8-flash-lite"]["rates"],
    "gemini-flash-lite": MODEL_REGISTRY["gemini-3.8-flash-lite"]["rates"],
    "gemini-3.8-flash-lite": MODEL_REGISTRY["gemini-3.8-flash-lite"]["rates"],
    "default": MODEL_REGISTRY["gemini-4-argon"]["rates"],
}

def normalize_model_name(name: str | None) -> str:
    """Resolve aliases or raw model strings to canonical model name."""
    if not name:
        return "gemini-4-argon"
    raw = str(name).strip().lower()

    # 1. Exact match on canonical key or alias
    for canon, data in MODEL_REGISTRY.items():
        if raw == canon or raw in [a.lower() for a in data.get("aliases", [])]:
            return canon

    # 2. Substring match, sorting longest patterns first to prevent 'flash' matching 'flash-lite'
    patterns: list[tuple[str, str]] = []
    for canon, data in MODEL_REGISTRY.items():
        patterns.append((canon, canon))
        for alias in data.get("aliases", []):
            patterns.append((alias.lower(), canon))
    patterns.sort(key=lambda x: len(x[0]), reverse=True)

    for pattern, canon in patterns:
        if pattern in raw:
            return canon

    return "gemini-4-argon"

# Alias per contract specification
resolve_model_id = normalize_model_name

def extract_model_and_effort(name: str | None, effort: str | None = None) -> tuple[str, str | None]:
    """
    Extract canonical model name and implied reasoning effort.
    E.g. 'gemini-4-hydrogen-xhigh' with effort=None -> ('gemini-4-hydrogen', 'xhigh').
    """
    if not name:
        return "gemini-4-argon", effort

    raw = str(name).strip().lower()
    inferred_effort = effort

    # Check for suffix effort patterns: -low, -medium, -high, -xhigh
    for suffix in ["-xhigh", "-high", "-medium", "-low"]:
        if raw.endswith(suffix):
            cand_canon = normalize_model_name(raw[: -len(suffix)])
            if cand_canon in MODEL_REGISTRY:
                eff = suffix.lstrip("-")
                if not inferred_effort:
                    inferred_effort = eff
                return cand_canon, inferred_effort

    canon = normalize_model_name(raw)
    return canon, inferred_effort

def compute_cost(model: str | None, in_tok: int, out_tok: int, cache_tok: int) -> dict:
    """Calculate actual cost and cache savings in USD and VND."""
    canon = normalize_model_name(model)
    rates = MODEL_REGISTRY[canon]["rates"]

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

def get_model_metadata(model: str | None) -> dict:
    """Return model configuration and metadata for given model identifier."""
    canon = normalize_model_name(model)
    return MODEL_REGISTRY[canon]

def validate_reasoning_effort(model: str | None, effort: str | None, clamp: bool = False) -> tuple[bool, str | None]:
    """
    Validate reasoning effort for a model.
    'xhigh' is strictly allowed on gemini-4-hydrogen.
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
    supported = MODEL_REGISTRY[canon].get("supported_reasoning_efforts", [])

    if clean_effort in supported:
        return True, clean_effort

    # Clamping policy for Carbon & Argon when xhigh is supplied
    if clean_effort == "xhigh" and clamp and canon in ("gemini-4-carbon", "gemini-4-argon"):
        return True, "high"

    return False, None
