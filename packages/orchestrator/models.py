#!/usr/bin/env python3
"""
Model registry, tiering taxonomy, rates, and financial token calculations.
Part of Antigravity Multi-Agent Orchestrator.
"""

from __future__ import annotations

USD_TO_VND_RATE: float = 25400.0

VALID_REASONING_EFFORTS: set[str] = {"low", "medium", "high"}

MODEL_REGISTRY: dict[str, dict] = {
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
        "target_personas": ["builder", "test-engineer", "code-simplifier"],
    },
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

def validate_reasoning_effort(model: str | None, effort: str | None) -> tuple[bool, str | None]:
    """
    Validate reasoning effort for a model.
    Returns (is_valid, normalized_effort).
    """
    if effort is None or effort == "":
        return True, None
    clean_effort = str(effort).strip().lower()
    if clean_effort not in VALID_REASONING_EFFORTS:
        return False, None
    canon = normalize_model_name(model)
    supported = MODEL_REGISTRY[canon].get("supported_reasoning_efforts", [])
    if clean_effort not in supported:
        return False, None
    return True, clean_effort
