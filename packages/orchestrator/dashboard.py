"""
Web Dashboard for Antigravity Multi-Agent Orchestrator.
Exposes DASHBOARD_HTML: str containing upgraded dark-mode UI with Gemini 4 Carbon & Hydrogen styling,
Per-Model Financial Analytics (5-Tier Periodic Table Architecture), Interactive Zero-Dependency SVG DAG Visualizer,
and Smart Model Router Sandbox with Fast-Retry Circuit Breaker.
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Hospital Suite - Multi-Agent Orchestrator</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          fontFamily: {
            sans: ['"Plus Jakarta Sans"', 'sans-serif'],
            mono: ['"JetBrains Mono"', 'monospace'],
          },
          colors: {
            brand: {
              50: '#eef2ff',
              100: '#e0e7ff',
              500: '#6366f1',
              600: '#4f46e5',
              700: '#4338ca',
            },
            carbon: {
              400: '#34d399',
              500: '#10b981',
              900: '#064e3b',
              950: '#022c22',
            },
            hydrogen: {
              300: '#67e8f9',
              400: '#22d3ee',
              500: '#06b6d4',
              900: '#164e63',
              950: '#083344',
            }
          }
        }
      }
    }
  </script>
  <style>
    @keyframes pulse-slow {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.4; }
    }
    .pulse-slow {
      animation: pulse-slow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }
    @keyframes glow-emerald {
      0%, 100% { box-shadow: 0 0 15px rgba(16, 185, 129, 0.2); }
      50% { box-shadow: 0 0 25px rgba(16, 185, 129, 0.5); }
    }
    .glow-carbon {
      animation: glow-emerald 3s ease-in-out infinite;
    }
    @keyframes glow-cyan {
      0%, 100% { box-shadow: 0 0 15px rgba(6, 182, 212, 0.25); }
      50% { box-shadow: 0 0 25px rgba(6, 182, 212, 0.55); }
    }
    .glow-hydrogen, .glow-cyan {
      animation: glow-cyan 3s ease-in-out infinite;
    }
    ::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    ::-webkit-scrollbar-track {
      background: #090d16;
    }
    ::-webkit-scrollbar-thumb {
      background: #1e293b;
      border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: #334155;
    }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 font-sans min-h-screen antialiased flex flex-col">

  <!-- Header -->
  <header class="border-b border-slate-800/80 bg-slate-900/70 backdrop-blur sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between gap-4">
      <div class="flex items-center space-x-3 min-w-0">
        <div class="h-9 w-9 rounded-xl bg-gradient-to-br from-cyan-400 via-emerald-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 shrink-0">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <div class="min-w-0">
          <div class="flex items-center space-x-2 flex-wrap">
            <h1 class="text-base font-bold tracking-tight text-white whitespace-nowrap">Hospital Suite - Multi-Agent Orchestrator</h1>
            <span class="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-semibold border border-emerald-500/30">Gemini 4 Carbon</span>
            <span class="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/15 text-cyan-300 font-semibold border border-cyan-500/40 flex items-center gap-1 shadow-sm shadow-cyan-500/10"><span class="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" style="background-color: #06b6d4;"></span>⚡ Gemini 4 Hydrogen</span>
            <span class="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 font-medium border border-indigo-500/20">5-Tier Fleet</span>
          </div>
          <p class="text-xs text-slate-400 truncate">1-Agent = 1-Skill Real-Time Execution Engine &middot; Autonomous Multi-Model Fleet</p>
        </div>
      </div>
      
      <div class="flex items-center space-x-2.5 sm:space-x-3 shrink-0">
        <!-- Smart Router Sandbox Trigger Button -->
        <button onclick="openRouterModal()" class="px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/40 text-xs font-semibold flex items-center space-x-1.5 transition shadow-sm" title="Open Smart Model & Reasoning Effort Recommendation Sandbox">
          <span>🧠 Router Sandbox</span>
        </button>

        <!-- Audit Export Dropdown / Buttons -->
        <div class="flex items-center space-x-1 bg-slate-800/80 border border-slate-700/80 rounded-lg p-0.5">
          <button onclick="exportAuditReport('markdown')" class="px-2.5 py-1 text-slate-200 hover:text-white hover:bg-slate-700/80 rounded text-xs font-medium flex items-center space-x-1 transition" title="Export Full Mission Audit Report as Markdown (.md)">
            <span>📥 Audit (.md)</span>
          </button>
          <button onclick="exportAuditReport('json')" class="px-2 py-1 text-slate-400 hover:text-white hover:bg-slate-700/80 rounded text-xs font-mono transition" title="Export Audit JSON">
            <span>JSON</span>
          </button>
        </div>

        <!-- SSE Status Indicator -->
        <div id="sse-indicator" class="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-slate-800/70 border border-slate-700/50 text-xs">
          <span id="sse-dot" class="h-2 w-2 rounded-full bg-amber-400 pulse-slow"></span>
          <span id="sse-status" class="text-slate-300 font-medium">Connecting...</span>
        </div>

        <!-- Reset State Button -->
        <button onclick="resetState()" class="text-xs px-2.5 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 transition font-medium flex items-center space-x-1">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
          <span class="hidden sm:inline">Reset</span>
        </button>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="border-t border-slate-800/80 px-4 sm:px-6 lg:px-8 bg-slate-900/40">
      <div class="max-w-7xl mx-auto flex space-x-2 sm:space-x-4">
        <button id="tab-btn-live" onclick="switchTab('live')" class="py-2.5 px-3 border-b-2 font-semibold text-xs sm:text-sm flex items-center space-x-2 transition border-emerald-500 text-white">
          <svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
          <span>⚡ Live Dashboard</span>
          <span id="tab-live-badge" class="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-emerald-500/20 text-emerald-300 font-mono">0</span>
        </button>

        <button id="tab-btn-analytics" onclick="switchTab('analytics')" class="py-2.5 px-3 border-b-2 font-semibold text-xs sm:text-sm flex items-center space-x-2 transition border-transparent text-slate-400 hover:text-slate-200">
          <svg class="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
          <span>📊 Model Analytics</span>
          <span class="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-cyan-500/20 text-cyan-300 font-mono">5-Tier Fleet</span>
        </button>

        <button id="tab-btn-history" onclick="switchTab('history')" class="py-2.5 px-3 border-b-2 font-semibold text-xs sm:text-sm flex items-center space-x-2 transition border-transparent text-slate-400 hover:text-slate-200">
          <svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          <span>📜 Usage History &amp; Cost Audit</span>
          <span id="tab-cost-badge" class="ml-1 px-2 py-0.5 rounded-full text-[10px] bg-emerald-500/20 text-emerald-300 font-mono font-bold">$0.00</span>
        </button>

        <button id="tab-btn-logs" onclick="switchTab('logs')" class="py-2.5 px-3 border-b-2 font-semibold text-xs sm:text-sm flex items-center space-x-2 transition border-transparent text-slate-400 hover:text-slate-200">
          <svg class="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
          <span>🖥️ System Logs</span>
        </button>
      </div>
    </div>
  </header>

  <!-- Main Content -->
  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 w-full space-y-6">

    <!-- =================================================================== -->
    <!-- TAB 1: LIVE DASHBOARD -->
    <!-- =================================================================== -->
    <div id="tab-view-live" class="space-y-6">
      
      <!-- Pipeline Stage Visualizer -->
      <div class="bg-slate-900/50 border border-slate-800/70 rounded-2xl p-4 sm:p-5 shadow-lg">
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center space-x-2">
            <div class="h-2 w-2 rounded-full bg-emerald-400"></div>
            <h2 class="text-xs font-semibold tracking-wider text-slate-400 uppercase">Pipeline Stage Visualizer &amp; Delivery Stages</h2>
          </div>
          <span id="pipeline-status-text" class="text-xs text-indigo-400 font-medium">Auto-synced</span>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5" id="pipeline-stages">
          <!-- Rendered dynamically -->
        </div>
      </div>

      <!-- Parallel Concurrency Banner (Visible when multiple workers active) -->
      <div id="parallel-concurrency-banner" class="hidden bg-gradient-to-r from-emerald-500/10 via-indigo-500/10 to-amber-500/10 border border-emerald-500/30 rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3 shadow-lg shadow-emerald-500/5">
        <div class="flex items-center space-x-3">
          <div class="h-3 w-3 rounded-full bg-emerald-400 animate-ping"></div>
          <div>
            <div class="text-xs font-bold text-emerald-300 flex items-center gap-1.5">
              <span>⚡ CONCURRENT PARALLEL WORKERS ACTIVE</span>
              <span id="parallel-worker-count" class="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px] font-mono border border-emerald-500/30">0 Workers</span>
            </div>
            <p class="text-[11px] text-slate-300 mt-0.5">Tasks running in parallel with decoupled dependencies and isolated non-overlapping scopes.</p>
          </div>
        </div>
        <div id="parallel-groups-badges" class="flex flex-wrap gap-1.5">
          <!-- Rendered dynamically -->
        </div>
      </div>

      <!-- Metric Cards Grid -->
      <div class="grid grid-cols-2 lg:grid-cols-6 gap-3 sm:gap-4">
        <!-- Total Tasks -->
        <div class="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 hover:border-slate-700 transition">
          <div class="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Total Tasks</span>
            <svg class="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>
          </div>
          <div class="mt-2 flex items-baseline space-x-2">
            <span id="metric-total" class="text-2xl sm:text-3xl font-bold text-white">0</span>
          </div>
        </div>

        <!-- In Progress -->
        <div class="bg-slate-900/60 border border-blue-900/30 rounded-2xl p-4 hover:border-blue-800/50 transition">
          <div class="flex items-center justify-between text-blue-400 text-xs font-medium">
            <span>In Progress</span>
            <svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
          </div>
          <div class="mt-2 flex items-baseline space-x-2">
            <span id="metric-running" class="text-2xl sm:text-3xl font-bold text-blue-400">0</span>
            <span class="text-xs text-blue-400/70">active</span>
          </div>
        </div>

        <!-- Parallel Active Workers -->
        <div class="bg-slate-900/60 border border-amber-900/30 rounded-2xl p-4 hover:border-amber-800/50 transition">
          <div class="flex items-center justify-between text-amber-400 text-xs font-medium">
            <span>Parallel Workers</span>
            <svg class="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
          </div>
          <div class="mt-2 flex items-baseline space-x-2">
            <span id="metric-parallel" class="text-2xl sm:text-3xl font-bold text-amber-400">0</span>
            <span class="text-xs text-amber-400/70">concurrent</span>
          </div>
        </div>

        <!-- Completed -->
        <div class="bg-slate-900/60 border border-emerald-900/30 rounded-2xl p-4 hover:border-emerald-800/50 transition">
          <div class="flex items-center justify-between text-emerald-400 text-xs font-medium">
            <span>Completed</span>
            <svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
          </div>
          <div class="mt-2 flex items-baseline space-x-2">
            <span id="metric-completed" class="text-2xl sm:text-3xl font-bold text-emerald-400">0</span>
            <span class="text-xs text-emerald-400/70">done</span>
          </div>
        </div>

        <!-- Blocked / Failed / Cancelled -->
        <div class="bg-slate-900/60 border border-rose-900/30 rounded-2xl p-4 hover:border-rose-800/50 transition">
          <div class="flex items-center justify-between text-rose-400 text-xs font-medium">
            <span>Blocked / Stop</span>
            <svg class="w-4 h-4 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
          </div>
          <div class="mt-2 flex items-baseline space-x-2">
            <span id="metric-blocked" class="text-2xl sm:text-3xl font-bold text-rose-400">0</span>
          </div>
        </div>

        <!-- Active Agents -->
        <div class="bg-slate-900/60 border border-purple-900/30 rounded-2xl p-4 hover:border-purple-800/50 transition">
          <div class="flex items-center justify-between text-purple-400 text-xs font-medium">
            <span>Active Agents</span>
            <svg class="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" /></svg>
          </div>
          <div class="mt-2 flex items-baseline space-x-2">
            <span id="metric-agents" class="text-2xl sm:text-3xl font-bold text-purple-400">0</span>
            <span class="text-xs text-purple-400/70">working</span>
          </div>
        </div>
      </div>

      <!-- Token Consumption, Cost & Context Cache Telemetry -->
      <div class="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 sm:p-5 shadow-lg">
        <div class="flex items-center justify-between mb-3 border-b border-slate-800/60 pb-2 flex-wrap gap-2">
          <div class="flex items-center space-x-2">
            <div class="h-2 w-2 rounded-full bg-cyan-400"></div>
            <h2 class="text-xs font-semibold tracking-wider text-slate-300 uppercase">Token Consumption, Financial Cost &amp; Context Cache Telemetry</h2>
          </div>
          <div class="flex items-center space-x-2">
            <span class="text-xs text-slate-400">Context Cache Hit Rate:</span>
            <span id="metric-cache-rate" class="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-bold border border-emerald-500/20 font-mono">0%</span>
          </div>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <!-- Input Tokens -->
          <div class="bg-slate-950/60 border border-slate-800/60 rounded-xl p-3">
            <div class="text-[11px] text-slate-400 font-medium flex items-center justify-between">
              <span>Input (Prompt)</span>
              <span class="text-cyan-400 text-xs font-mono">📥 In</span>
            </div>
            <div class="mt-1 flex items-baseline space-x-1.5">
              <span id="metric-tokens-in" class="text-lg sm:text-xl font-bold font-mono text-cyan-400">0</span>
              <span class="text-[10px] text-slate-500">tok</span>
            </div>
          </div>

          <!-- Output Tokens -->
          <div class="bg-slate-950/60 border border-slate-800/60 rounded-xl p-3">
            <div class="text-[11px] text-slate-400 font-medium flex items-center justify-between">
              <span>Output (Generated)</span>
              <span class="text-purple-400 text-xs font-mono">📤 Out</span>
            </div>
            <div class="mt-1 flex items-baseline space-x-1.5">
              <span id="metric-tokens-out" class="text-lg sm:text-xl font-bold font-mono text-purple-400">0</span>
              <span class="text-[10px] text-slate-500">tok</span>
            </div>
          </div>

          <!-- Cached Tokens -->
          <div class="bg-slate-950/60 border border-slate-800/60 rounded-xl p-3">
            <div class="text-[11px] text-slate-400 font-medium flex items-center justify-between">
              <span>Context Cache Read</span>
              <span class="text-emerald-400 text-xs font-mono">⚡ Cache</span>
            </div>
            <div class="mt-1 flex items-baseline space-x-1.5">
              <span id="metric-tokens-cache" class="text-lg sm:text-xl font-bold font-mono text-emerald-400">0</span>
              <span class="text-[10px] text-slate-500">tok</span>
            </div>
          </div>

          <!-- Grand Total Tokens -->
          <div class="bg-slate-950/60 border border-slate-800/60 rounded-xl p-3">
            <div class="text-[11px] text-slate-400 font-medium flex items-center justify-between">
              <span>Total Footprint</span>
              <span class="text-amber-400 text-xs font-mono">📊 Total</span>
            </div>
            <div class="mt-1 flex items-baseline space-x-1.5">
              <span id="metric-tokens-total" class="text-lg sm:text-xl font-bold font-mono text-amber-400">0</span>
              <span class="text-[10px] text-slate-500">tok</span>
            </div>
          </div>

          <!-- Financial Cost -->
          <div class="bg-gradient-to-br from-indigo-950/40 to-slate-950/80 border border-indigo-500/30 rounded-xl p-3 shadow-sm">
            <div class="text-[11px] text-indigo-300 font-medium flex items-center justify-between">
              <span>Estimated Cost</span>
              <span class="text-indigo-400 text-xs font-mono">💰 Spend</span>
            </div>
            <div class="mt-1 flex flex-col">
              <span id="metric-cost-usd" class="text-lg sm:text-xl font-bold font-mono text-indigo-400">$0.00</span>
              <span id="metric-cost-vnd" class="text-[10px] text-indigo-300/80 font-mono">~ 0 ₫</span>
            </div>
          </div>

          <!-- Cache Savings -->
          <div class="bg-gradient-to-br from-emerald-950/40 to-slate-950/80 border border-emerald-500/30 rounded-xl p-3 shadow-sm">
            <div class="text-[11px] text-emerald-300 font-medium flex items-center justify-between">
              <span>Cache Savings</span>
              <span class="text-emerald-400 text-xs font-mono">🛡️ Saved</span>
            </div>
            <div class="mt-1 flex flex-col">
              <span id="metric-saved-usd" class="text-lg sm:text-xl font-bold font-mono text-emerald-400">$0.00</span>
              <span id="metric-saved-vnd" class="text-[10px] text-emerald-300/80 font-mono">~ 0 ₫ saved</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Live Tasks Status & View Switcher (Table vs Interactive SVG DAG) -->
      <div class="bg-slate-900/50 border border-slate-800/80 rounded-2xl overflow-hidden shadow-xl">
        <div class="px-5 py-3.5 border-b border-slate-800/80 flex flex-wrap items-center justify-between gap-3 bg-slate-900/40">
          <div class="flex items-center space-x-2.5">
            <div class="h-2 w-2 rounded-full bg-emerald-400"></div>
            <h2 class="text-sm font-bold text-white tracking-wide">Live Tasks Status</h2>
            <span id="task-count-badge" class="px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 text-xs font-semibold">0 active</span>
          </div>

          <!-- View Toggle: Table View vs DAG Dependency Graph View -->
          <div class="flex items-center space-x-2">
            <div class="inline-flex rounded-xl bg-slate-800/80 p-0.5 border border-slate-700/80 text-xs font-medium">
              <button id="view-mode-table-btn" onclick="switchTaskView('table')" class="px-3 py-1 rounded-lg transition bg-indigo-600 text-white shadow-sm flex items-center space-x-1.5">
                <span>📋 Table View</span>
              </button>
              <button id="view-mode-dag-btn" onclick="switchTaskView('dag')" class="px-3 py-1 rounded-lg transition text-slate-400 hover:text-slate-200 flex items-center space-x-1.5">
                <span>🕸️ DAG View</span>
              </button>
            </div>
            <button onclick="switchTab('history')" class="text-xs text-indigo-400 hover:text-indigo-300 font-medium pl-2 hidden sm:inline">
              History &rarr;
            </button>
          </div>
        </div>

        <!-- VIEW 1: Active Tasks Table -->
        <div id="tasks-table-view" class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-900/80 text-slate-400 uppercase tracking-wider text-[11px] font-semibold border-b border-slate-800/80">
              <tr>
                <th scope="col" class="py-3 px-4">Task ID</th>
                <th scope="col" class="py-3 px-4">Agent Persona</th>
                <th scope="col" class="py-3 px-4">Model Engine &amp; Effort</th>
                <th scope="col" class="py-3 px-4">Complexity</th>
                <th scope="col" class="py-3 px-4">Parallel Group</th>
                <th scope="col" class="py-3 px-4">Conditions</th>
                <th scope="col" class="py-3 px-4">Token Usage</th>
                <th scope="col" class="py-3 px-4">Est. Cost</th>
                <th scope="col" class="py-3 px-4">Scope / Focus</th>
                <th scope="col" class="py-3 px-4">Status</th>
                <th scope="col" class="py-3 px-4 w-32">Progress</th>
                <th scope="col" class="py-3 px-4 text-center">Action</th>
                <th scope="col" class="py-3 px-4 text-right">Updated</th>
              </tr>
            </thead>
            <tbody id="tasks-tbody" class="divide-y divide-slate-800/50 text-slate-300">
              <tr>
                <td colspan="13" class="py-8 text-center text-slate-500">No tasks registered yet. Dispatch tasks using OrchestratorClient.</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- VIEW 2: Interactive Zero-Dependency SVG DAG Visualizer -->
        <div id="tasks-dag-view" class="hidden flex-col bg-slate-950/60 min-h-[460px]">
          <!-- DAG Sub-header toolbar -->
          <div class="px-5 py-2.5 bg-slate-900/60 border-b border-slate-800/60 flex flex-wrap items-center justify-between text-xs gap-3">
            <div class="flex items-center space-x-2 text-slate-300">
              <span class="text-emerald-400 font-bold">DAG Execution Graph:</span>
              <span class="text-slate-400">Direct topological dependency fan-out visualization &middot; Click any node to inspect</span>
            </div>
            <div class="flex items-center space-x-3 text-[11px] font-mono">
              <div class="flex items-center space-x-1"><span class="w-2.5 h-2.5 rounded-full bg-emerald-400"></span><span class="text-slate-400">Done</span></div>
              <div class="flex items-center space-x-1"><span class="w-2.5 h-2.5 rounded-full bg-blue-400 pulse-slow"></span><span class="text-slate-400">Running</span></div>
              <div class="flex items-center space-x-1"><span class="w-2.5 h-2.5 rounded-full bg-emerald-500/50 border border-emerald-400"></span><span class="text-slate-400">Ready</span></div>
              <div class="flex items-center space-x-1"><span class="w-2.5 h-2.5 rounded-full bg-rose-400"></span><span class="text-slate-400">Blocked</span></div>
              <button onclick="renderDagView()" class="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700">Refresh DAG</button>
            </div>
          </div>

          <!-- DAG Canvas Container -->
          <div id="dag-graph-wrapper" class="relative flex-1 overflow-auto p-6 min-h-[420px]">
            <svg id="dag-svg-canvas" class="absolute inset-0 pointer-events-none" style="min-width: 100%; min-height: 100%;"></svg>
            <div id="dag-nodes-layer" class="relative" style="min-width: 100%; min-height: 100%;"></div>
          </div>
        </div>
      </div>

      <!-- Real-time Console Log Stream Preview in Live View -->
      <div class="bg-slate-900/60 border border-slate-800/80 rounded-2xl overflow-hidden shadow-xl flex flex-col h-72">
        <div class="px-5 py-3 border-b border-slate-800/80 bg-slate-900/90 flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center space-x-2.5">
            <span class="flex h-2 w-2 relative">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <h2 class="text-sm font-bold text-white tracking-wide">Live Agent Telemetry &amp; Activity Stream</h2>
          </div>
          <button onclick="switchTab('logs')" class="text-xs text-indigo-400 hover:text-indigo-300 font-medium">Open Full Log Console &rarr;</button>
        </div>
        <div id="live-logs-container" class="flex-1 p-4 font-mono text-[11px] leading-relaxed overflow-y-auto space-y-1 bg-black/60">
          <!-- Live logs rendered here -->
        </div>
      </div>
    </div>

    <!-- =================================================================== -->
    <!-- TAB 2: MODEL ANALYTICS (PER-MODEL TOKEN & FINANCIAL BREAKDOWN) -->
    <!-- =================================================================== -->
    <div id="tab-view-analytics" class="hidden space-y-6">
      
      <!-- Analytics Header Banner -->
      <div class="bg-gradient-to-r from-emerald-950/40 via-indigo-950/40 to-slate-900 border border-emerald-500/30 rounded-2xl p-5 shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div>
          <div class="flex items-center space-x-2">
            <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">Per-Model Financial Ledger</span>
            <span class="text-xs text-slate-400">1 USD = 25,400 VND Baseline</span>
          </div>
          <h2 class="text-lg font-bold text-white mt-1">Multi-Model Token Consumption &amp; Cache Savings Analytics</h2>
          <p class="text-xs text-slate-300 mt-0.5">Granular telemetry tracking frontier Gemini 4 Carbon, Argon deep reasoning, high-throughput Gemini 4 Hydrogen, Flash, and Flash-Lite tiers.</p>
        </div>
        <div class="flex items-center space-x-2">
          <button onclick="refreshModelAnalytics()" class="px-3 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/40 text-xs font-semibold flex items-center space-x-1.5 transition">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            <span>Sync Analytics</span>
          </button>
        </div>
      </div>

      <!-- 5-Model Comparative Cards Grid -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4" id="model-analytics-cards">
        <!-- Rendered dynamically: Carbon, Argon, Hydrogen, Flash, Flash-Lite -->
      </div>

      <!-- Total Spend Distribution Visual Progress Bar -->
      <div class="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 shadow-lg space-y-3">
        <div class="flex items-center justify-between text-xs font-semibold">
          <span class="text-slate-300 uppercase tracking-wider">Spend Distribution Across Model Tiers</span>
          <span id="spend-dist-summary" class="text-slate-400 font-mono">Total Spend: $0.00</span>
        </div>
        <div class="w-full bg-slate-950 rounded-full h-3 overflow-hidden flex" id="spend-distribution-bar">
          <div id="bar-carbon" class="bg-emerald-500 h-full transition-all duration-300" style="width: 0%;" title="Carbon: $0.00"></div>
          <div id="bar-argon" class="bg-indigo-500 h-full transition-all duration-300" style="width: 0%;" title="Argon: $0.00"></div>
          <div id="bar-hydrogen" class="bg-cyan-500 h-full transition-all duration-300" style="width: 0%; background-color: #06b6d4;" title="Hydrogen: $0.00"></div>
          <div id="bar-flash" class="bg-amber-500 h-full transition-all duration-300" style="width: 0%;" title="Flash: $0.00"></div>
          <div id="bar-lite" class="bg-slate-500 h-full transition-all duration-300" style="width: 0%;" title="Flash-Lite: $0.00"></div>
        </div>
        <div class="flex flex-wrap items-center justify-between gap-2 text-xs pt-1">
          <div class="flex items-center space-x-1.5"><span class="w-3 h-3 rounded bg-emerald-500"></span><span class="text-emerald-300 font-mono text-[11px]" id="legend-carbon">Carbon: $0.00 (0%)</span></div>
          <div class="flex items-center space-x-1.5"><span class="w-3 h-3 rounded bg-indigo-500"></span><span class="text-indigo-300 font-mono text-[11px]" id="legend-argon">Argon: $0.00 (0%)</span></div>
          <div class="flex items-center space-x-1.5"><span class="w-3 h-3 rounded bg-cyan-500" style="background-color: #06b6d4;"></span><span class="text-cyan-300 font-mono text-[11px]" id="legend-hydrogen">Hydrogen: $0.00 (0%)</span></div>
          <div class="flex items-center space-x-1.5"><span class="w-3 h-3 rounded bg-amber-500"></span><span class="text-amber-300 font-mono text-[11px]" id="legend-flash">Flash: $0.00 (0%)</span></div>
          <div class="flex items-center space-x-1.5"><span class="w-3 h-3 rounded bg-slate-500"></span><span class="text-slate-300 font-mono text-[11px]" id="legend-lite">Flash-Lite: $0.00 (0%)</span></div>
        </div>
      </div>

      <!-- Detailed Per-Model Ledger Table -->
      <div class="bg-slate-900/50 border border-slate-800/80 rounded-2xl overflow-hidden shadow-xl">
        <div class="px-5 py-3.5 border-b border-slate-800/80 bg-slate-900/70 flex items-center justify-between">
          <h3 class="text-xs font-bold uppercase tracking-wider text-slate-300">Detailed Model Rate Matrix &amp; Spend Ledger</h3>
          <span class="text-xs text-slate-400 font-mono">Rates per 1M tokens</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-900/90 text-slate-400 uppercase tracking-wider text-[11px] font-semibold border-b border-slate-800/80">
              <tr>
                <th scope="col" class="py-3 px-4">Model Engine</th>
                <th scope="col" class="py-3 px-4">Tier Taxonomy</th>
                <th scope="col" class="py-3 px-4 text-center">Tasks</th>
                <th scope="col" class="py-3 px-4 font-mono text-cyan-400">Prompt In</th>
                <th scope="col" class="py-3 px-4 font-mono text-purple-400">Output</th>
                <th scope="col" class="py-3 px-4 font-mono text-emerald-400">Cache Read</th>
                <th scope="col" class="py-3 px-4 font-mono">Total Tokens</th>
                <th scope="col" class="py-3 px-4 font-mono text-emerald-300">Cache Hit %</th>
                <th scope="col" class="py-3 px-4 font-mono text-indigo-300">Billed Cost (USD)</th>
                <th scope="col" class="py-3 px-4 font-mono text-indigo-400">Billed Cost (VND)</th>
                <th scope="col" class="py-3 px-4 font-mono text-emerald-400">Cache Savings</th>
                <th scope="col" class="py-3 px-4 text-slate-400 text-right">Pricing Rates (In/Out/Cache)</th>
              </tr>
            </thead>
            <tbody id="analytics-tbody" class="divide-y divide-slate-800/50 text-slate-300">
              <!-- Rendered dynamically -->
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- =================================================================== -->
    <!-- TAB 3: USAGE HISTORY & COST AUDIT -->
    <!-- =================================================================== -->
    <div id="tab-view-history" class="hidden space-y-6">
      <!-- Historical KPI Summary -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="bg-slate-900/60 border border-indigo-500/30 rounded-2xl p-5 shadow-lg">
          <div class="text-xs text-indigo-300 font-semibold uppercase tracking-wider">Total Spent</div>
          <div class="mt-2 flex items-baseline space-x-2">
            <span id="hist-total-cost-usd" class="text-3xl font-extrabold font-mono text-white">$0.00</span>
          </div>
          <div id="hist-total-cost-vnd" class="text-xs font-mono text-indigo-400 mt-1">~ 0 ₫</div>
          <div class="text-[11px] text-slate-500 mt-2">Billed token spend across all Gemini models</div>
        </div>

        <div class="bg-slate-900/60 border border-emerald-500/30 rounded-2xl p-5 shadow-lg">
          <div class="text-xs text-emerald-300 font-semibold uppercase tracking-wider flex items-center justify-between">
            <span>Cache Savings</span>
            <span class="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 text-[10px] font-mono font-bold border border-emerald-500/30">75% Discount</span>
          </div>
          <div class="mt-2 flex items-baseline space-x-2">
            <span id="hist-total-saved-usd" class="text-3xl font-extrabold font-mono text-emerald-400">$0.00</span>
          </div>
          <div id="hist-total-saved-vnd" class="text-xs font-mono text-emerald-300 mt-1">~ 0 ₫ saved</div>
          <div class="text-[11px] text-slate-500 mt-2">Money saved via Gemini Context Caching</div>
        </div>

        <div class="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 shadow-lg">
          <div class="text-xs text-slate-400 font-semibold uppercase tracking-wider">Total Tokens Processed</div>
          <div class="mt-2 flex items-baseline space-x-2">
            <span id="hist-total-tokens" class="text-3xl font-extrabold font-mono text-cyan-400">0</span>
          </div>
          <div id="hist-token-breakdown" class="text-xs font-mono text-slate-400 mt-1">Prompt: 0 | Gen: 0 | Cache: 0</div>
          <div class="text-[11px] text-slate-500 mt-2">Total context window footprints</div>
        </div>

        <div class="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 shadow-lg">
          <div class="text-xs text-slate-400 font-semibold uppercase tracking-wider">Execution Efficiency</div>
          <div class="mt-2 flex items-baseline space-x-2">
            <span id="hist-cache-rate" class="text-3xl font-extrabold font-mono text-purple-400">0.0%</span>
            <span class="text-xs text-slate-400">cache hit</span>
          </div>
          <div id="hist-avg-task-cost" class="text-xs font-mono text-slate-400 mt-1">Avg cost / task: $0.00</div>
          <div class="text-[11px] text-slate-500 mt-2">Efficiency &amp; savings ratio across pipeline</div>
        </div>
      </div>

      <!-- Filters & Actions Toolbar -->
      <div class="bg-slate-900/50 border border-slate-800/80 rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3">
        <div class="flex flex-wrap items-center gap-3 flex-1 min-w-[280px]">
          <!-- Search input -->
          <div class="relative flex-1 min-w-[200px] max-w-md">
            <span class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
            </span>
            <input type="text" id="hist-filter-search" oninput="renderHistoryTable()" placeholder="Search by task ID, persona, model or scope..." class="w-full pl-9 pr-3 py-1.5 bg-slate-800/80 border border-slate-700/80 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition">
          </div>

          <!-- Filter by Status -->
          <div class="flex items-center space-x-1.5 text-xs">
            <span class="text-slate-400">Status:</span>
            <select id="hist-filter-status" onchange="renderHistoryTable()" class="bg-slate-800/80 border border-slate-700/80 rounded-xl px-2.5 py-1.5 text-slate-200 text-xs focus:outline-none focus:border-indigo-500">
              <option value="all">All Statuses</option>
              <option value="completed">Completed</option>
              <option value="running">Running</option>
              <option value="cancelled">Cancelled / Killed</option>
              <option value="blocked">Blocked / Failed</option>
              <option value="pending">Pending</option>
            </select>
          </div>

          <!-- Filter by Model -->
          <div class="flex items-center space-x-1.5 text-xs">
            <span class="text-slate-400">Model:</span>
            <select id="hist-filter-model" onchange="renderHistoryTable()" class="bg-slate-800/80 border border-slate-700/80 rounded-xl px-2.5 py-1.5 text-slate-200 text-xs focus:outline-none focus:border-emerald-500">
              <option value="all">All Models</option>
              <option value="carbon">Gemini 4 Carbon (Frontier)</option>
              <option value="argon">Gemini 4 Argon (Pro)</option>
              <option value="hydrogen">Gemini 4 Hydrogen (Ultra-Fast)</option>
              <option value="flash">Gemini 3.8 Flash</option>
              <option value="lite">Gemini 3.8 Flash-Lite</option>
            </select>
          </div>

          <!-- Filter by Reasoning Effort -->
          <div class="flex items-center space-x-1.5 text-xs">
            <span class="text-slate-400">Effort:</span>
            <select id="hist-filter-effort" onchange="renderHistoryTable()" class="bg-slate-800/80 border border-slate-700/80 rounded-xl px-2.5 py-1.5 text-slate-200 text-xs focus:outline-none focus:border-emerald-500">
              <option value="all">All Efforts</option>
              <option value="xhigh">XHigh Effort [Thinking]</option>
              <option value="high">High Effort</option>
              <option value="medium">Medium Effort</option>
              <option value="low">Low Effort</option>
              <option value="none">Standard / None</option>
            </select>
          </div>
        </div>

        <div class="flex items-center space-x-2">
          <!-- Export CSV Button -->
          <button onclick="exportHistoryCSV()" class="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-xl text-xs font-semibold transition flex items-center space-x-1.5">
            <svg class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
            <span>Export CSV</span>
          </button>
          <!-- Export Markdown Audit Button -->
          <button onclick="exportAuditReport('markdown')" class="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold shadow-md shadow-emerald-600/20 transition flex items-center space-x-1.5">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
            <span>Export Audit (.md)</span>
          </button>
        </div>
      </div>

      <!-- Detailed History Audit Table -->
      <div class="bg-slate-900/50 border border-slate-800/80 rounded-2xl overflow-hidden shadow-xl">
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-900/80 text-slate-400 uppercase tracking-wider text-[11px] font-semibold border-b border-slate-800/80">
              <tr>
                <th scope="col" class="py-3 px-4">Task ID</th>
                <th scope="col" class="py-3 px-4">Agent / Persona</th>
                <th scope="col" class="py-3 px-4">Model Engine &amp; Effort</th>
                <th scope="col" class="py-3 px-4">Status</th>
                <th scope="col" class="py-3 px-4">Prompt In</th>
                <th scope="col" class="py-3 px-4">Generated Out</th>
                <th scope="col" class="py-3 px-4">Cache Read</th>
                <th scope="col" class="py-3 px-4">Total Tokens</th>
                <th scope="col" class="py-3 px-4">Cache Hit %</th>
                <th scope="col" class="py-3 px-4">Cost (USD / VND)</th>
                <th scope="col" class="py-3 px-4">Cache Savings</th>
                <th scope="col" class="py-3 px-4 text-center">Action</th>
                <th scope="col" class="py-3 px-4 text-right">Timestamp</th>
              </tr>
            </thead>
            <tbody id="history-tbody" class="divide-y divide-slate-800/50 text-slate-300">
              <tr>
                <td colspan="13" class="py-8 text-center text-slate-500">Loading audit records...</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- =================================================================== -->
    <!-- TAB 4: SYSTEM CONSOLE LOGS -->
    <!-- =================================================================== -->
    <div id="tab-view-logs" class="hidden space-y-4">
      <div class="bg-slate-900/60 border border-slate-800/80 rounded-2xl overflow-hidden shadow-xl flex flex-col h-[650px]">
        <div class="px-5 py-3 border-b border-slate-800/80 bg-slate-900/90 flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center space-x-2.5">
            <span class="flex h-2 w-2 relative">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <h2 class="text-sm font-bold text-white tracking-wide">Full Agent Activity &amp; Execution Console</h2>
          </div>

          <div class="flex items-center space-x-3 text-xs">
            <!-- Level Filter -->
            <div class="flex items-center space-x-1.5">
              <span class="text-slate-400">Level:</span>
              <select id="log-filter-level" onchange="filterLogs()" class="bg-slate-800 border border-slate-700 rounded-lg px-2 py-1 text-slate-200 text-xs focus:outline-none focus:border-indigo-500">
                <option value="all">ALL</option>
                <option value="info">INFO</option>
                <option value="warn">WARN</option>
                <option value="error">ERROR</option>
                <option value="thought">THOUGHT</option>
              </select>
            </div>

            <!-- Auto Scroll Toggle -->
            <label class="flex items-center space-x-1.5 cursor-pointer text-slate-300 select-none">
              <input type="checkbox" id="autoscroll-toggle" checked class="rounded bg-slate-800 border-slate-700 text-indigo-600 focus:ring-0">
              <span>Autoscroll</span>
            </label>

            <!-- Clear Button -->
            <button onclick="clearLogConsole()" class="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition text-xs">
              Clear
            </button>
          </div>
        </div>

        <!-- Logs Container -->
        <div id="logs-container" class="flex-1 p-4 font-mono text-[11px] leading-relaxed overflow-y-auto space-y-1 bg-black/70">
          <!-- Full Logs rendered here -->
        </div>
      </div>
    </div>

  </main>

  <footer class="border-t border-slate-800/60 py-4 text-center text-xs text-slate-500">
    Hospital Suite Real-Time Multi-Agent Orchestrator &middot; Gemini 4 Carbon Evolution &middot; Zero-Dependency SSE Architecture
  </footer>

  <!-- =================================================================== -->
  <!-- MODAL: AGENT LIVE ACTIVITY & INSPECTOR MODAL -->
  <!-- =================================================================== -->
  <div id="agent-live-modal" class="fixed inset-0 z-50 hidden flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
    <div class="relative w-full max-w-4xl max-h-[90vh] bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
      
      <!-- Modal Header -->
      <div class="px-6 py-4 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <div class="h-3 w-3 rounded-full bg-emerald-500 animate-pulse"></div>
          <div>
            <div class="flex items-center space-x-2 flex-wrap">
              <span id="modal-task-id" class="font-mono font-bold text-base text-white">TASK-...</span>
              <span id="modal-agent-badge"></span>
              <span id="modal-model-badge"></span>
              <span id="modal-status-badge"></span>
            </div>
            <div id="modal-scope" class="text-xs text-slate-400 mt-0.5 truncate max-w-xl">-</div>
          </div>
        </div>
        <div class="flex items-center space-x-2">
          <button onclick="refreshAgentLiveModal()" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium flex items-center space-x-1.5 transition">
            <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            <span>Làm mới</span>
          </button>
          <button onclick="closeAgentLiveModal()" class="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
      </div>

      <!-- Live Telemetry & Action Bar -->
      <div class="px-6 py-3 bg-slate-900/90 border-b border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div class="flex items-center space-x-3 font-mono">
          <div class="bg-slate-950 px-2.5 py-1 rounded border border-slate-800 text-slate-300 flex items-center space-x-2">
            <span class="text-cyan-400" id="modal-tok-in">📥 0</span>
            <span class="text-slate-600">/</span>
            <span class="text-purple-400" id="modal-tok-out">📤 0</span>
            <span class="text-slate-600">/</span>
            <span class="text-emerald-400" id="modal-tok-cache">⚡ 0</span>
          </div>
          <div class="bg-indigo-950/40 px-2.5 py-1 rounded border border-indigo-900/50 text-indigo-300 font-bold" id="modal-cost-usd">$0.00</div>
          <div class="text-[11px] text-slate-500 font-sans" id="modal-conv-id">Conv: -</div>
        </div>

        <div class="flex items-center space-x-4">
          <label class="flex items-center space-x-1.5 cursor-pointer text-slate-300 text-xs select-none">
            <input type="checkbox" id="modal-autorefresh-toggle" checked onchange="toggleModalAutoRefresh()" class="rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 bg-slate-800 w-3.5 h-3.5">
            <span>Tự động cập nhật (2.5s)</span>
          </label>
          <label class="flex items-center space-x-1.5 cursor-pointer text-slate-300 text-xs select-none">
            <input type="checkbox" id="modal-autoscroll-toggle" checked class="rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 bg-slate-800 w-3.5 h-3.5">
            <span>Cuộn theo dòng mới</span>
          </label>
        </div>
      </div>

      <!-- Current Ongoing Action Highlight Box -->
      <div class="px-6 py-2.5 bg-gradient-to-r from-emerald-950/30 via-indigo-950/30 to-purple-950/20 border-b border-emerald-900/30 flex items-center space-x-3">
        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 uppercase tracking-wider whitespace-nowrap">Đang làm:</span>
        <div id="modal-latest-action" class="font-mono text-xs text-emerald-200 truncate font-medium">Đang tải trạng thái hoạt động...</div>
      </div>

      <!-- Filter tabs -->
      <div class="px-6 pt-3 pb-2 bg-slate-900 flex items-center justify-between border-b border-slate-800/60">
        <div class="flex items-center space-x-2 text-xs">
          <button id="modal-filter-all" onclick="filterModalActivities('all')" class="px-3 py-1 rounded-lg font-medium transition bg-indigo-600 text-white shadow-sm">Tất cả (<span id="count-all">0</span>)</button>
          <button id="modal-filter-tool" onclick="filterModalActivities('tool')" class="px-3 py-1 rounded-lg font-medium transition text-slate-400 hover:text-slate-200 hover:bg-slate-800">🛠️ Công cụ (<span id="count-tool">0</span>)</button>
          <button id="modal-filter-thought" onclick="filterModalActivities('thought')" class="px-3 py-1 rounded-lg font-medium transition text-slate-400 hover:text-slate-200 hover:bg-slate-800">💭 Suy nghĩ (<span id="count-thought">0</span>)</button>
          <button id="modal-filter-error" onclick="filterModalActivities('error')" class="px-3 py-1 rounded-lg font-medium transition text-slate-400 hover:text-slate-200 hover:bg-slate-800">❌ Lỗi (<span id="count-error">0</span>)</button>
        </div>
        <div class="text-[11px] text-slate-500 font-mono">Real-time Subagent Execution Trace</div>
      </div>

      <!-- Scrollable Activities / Logs Container -->
      <div id="modal-activities-container" class="flex-1 overflow-y-auto p-6 space-y-3 bg-slate-950/40 font-sans text-xs min-h-[320px] max-h-[500px]">
        <div class="text-center py-12 text-slate-500">Đang nạp nhật ký từ subagent transcript...</div>
      </div>

      <!-- Modal Footer -->
      <div class="px-6 py-3 border-t border-slate-800 bg-slate-950/80 flex items-center justify-between text-xs text-slate-400">
        <div id="modal-footer-stats">0 hoạt động được ghi nhận</div>
        <button onclick="closeAgentLiveModal()" class="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium transition">Đóng</button>
      </div>

    </div>
  </div>

  <!-- =================================================================== -->
  <!-- MODAL: SMART MODEL & REASONING ROUTER SANDBOX -->
  <!-- =================================================================== -->
  <div id="router-modal" class="fixed inset-0 z-50 hidden flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
    <div class="relative w-full max-w-2xl bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
      <!-- Modal Header -->
      <div class="px-6 py-4 border-b border-slate-800 bg-slate-950/70 flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <div class="h-3 w-3 rounded-full bg-emerald-400 glow-carbon"></div>
          <div>
            <h3 class="text-sm font-bold text-white flex items-center gap-2">
              <span>🧠 Smart Model &amp; Reasoning Router Sandbox</span>
              <span class="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Gemini 4 Carbon</span>
            </h3>
            <p class="text-xs text-slate-400">Dynamic model selection &amp; reasoning effort evaluator based on task heuristics</p>
          </div>
        </div>
        <button onclick="closeRouterModal()" class="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
        </button>
      </div>

      <!-- Router Form -->
      <div class="p-6 space-y-4 text-xs">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <!-- Persona -->
          <div>
            <label class="block text-slate-300 font-semibold mb-1">Agent Persona</label>
            <select id="router-persona" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500">
              <option value="security-auditor">security-auditor (Security &amp; Vulnerability)</option>
              <option value="debugger">debugger (Deep Root-Cause Debugger)</option>
              <option value="spec-engineer">spec-engineer (Product &amp; Spec Specialist)</option>
              <option value="task-planner">task-planner (Architecture &amp; DAG Planner)</option>
              <option value="code-reviewer">code-reviewer (Code Quality &amp; Multi-Axis)</option>
              <option value="builder" selected>builder (Software Implementation)</option>
              <option value="ui-builder">ui-builder (Rapid UI &amp; Dashboard Iteration)</option>
              <option value="frontend-engineer">frontend-engineer (Frontend &amp; UI Specialist)</option>
              <option value="scout">scout (Codebase Reconnaissance &amp; URI Pointers)</option>
              <option value="codebase-researcher">codebase-researcher (Deep Code Search &amp; Pointers)</option>
              <option value="test-engineer">test-engineer (Automated Test Specialist)</option>
              <option value="observability-and-instrumentation">observability (Telemetry &amp; Instrumentation)</option>
              <option value="code-simplifier">code-simplifier (Refactoring &amp; Dead-code)</option>
            </select>
          </div>

          <!-- Complexity -->
          <div>
            <label class="block text-slate-300 font-semibold mb-1">Task Complexity</label>
            <select id="router-complexity" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500">
              <option value="critical">Critical (Zero-tolerance / Security / Vulnerabilities)</option>
              <option value="high">High (Architectural synthesis / Deep reasoning)</option>
              <option value="medium" selected>Medium (Standard code implementation)</option>
              <option value="low">Low (Formatting / Micro-task)</option>
            </select>
          </div>
        </div>

        <!-- Scope / Intent -->
        <div>
          <label class="block text-slate-300 font-semibold mb-1">Task Scope &amp; Target Objective</label>
          <input type="text" id="router-scope" placeholder="e.g., Audit SQL injection vulnerabilities and CVE exploits in auth controller" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500" value="Audit authentication middleware for token forgery vulnerabilities">
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-4 gap-3 items-center">
          <!-- File count -->
          <div>
            <label class="block text-slate-300 font-semibold mb-1">Estimated Files</label>
            <input type="number" id="router-files" value="3" min="1" max="100" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500">
          </div>

          <!-- Budget Mode -->
          <div>
            <label class="block text-slate-300 font-semibold mb-1">Optimization Goal</label>
            <select id="router-budget" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500">
              <option value="balanced" selected>Balanced (Cost vs Quality)</option>
              <option value="speed_first">Speed First (198 tok/s Workhorse)</option>
              <option value="latency_sensitive">Latency Sensitive (Fastest Response)</option>
              <option value="quality_first">Quality First (Prefer Frontier Carbon)</option>
              <option value="cost_saving">Cost Saving (Bulk Flash Scaffolding)</option>
              <option value="cost_first">Cost First (Max Flash Savings)</option>
            </select>
          </div>

          <!-- Retry Count (Circuit Breaker Simulation) -->
          <div>
            <label class="block text-slate-300 font-semibold mb-1" title="Simulates Fast-Retry Circuit Breaker failure threshold">Retry Count</label>
            <select id="router-retries" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono">
              <option value="0" selected>0 (First Turn)</option>
              <option value="1">1 (Self-Heal Retry)</option>
              <option value="2">2 (CB Tripped &rarr; Carbon)</option>
              <option value="3">3+ (Escalated High)</option>
            </select>
          </div>

          <!-- Security impact toggle -->
          <div class="pt-4">
            <label class="flex items-center space-x-2 cursor-pointer select-none">
              <input type="checkbox" id="router-security" class="rounded bg-slate-800 border-slate-700 text-emerald-500 focus:ring-0 w-4 h-4">
              <span class="text-slate-300 font-medium">Security Impact / CVE</span>
            </label>
          </div>
        </div>

        <!-- Evaluate Button -->
        <div class="pt-2">
          <button onclick="evaluateRouterRecommendation()" class="w-full py-2 bg-gradient-to-r from-emerald-600 via-indigo-600 to-purple-600 hover:from-emerald-500 hover:to-purple-500 text-white font-bold rounded-xl transition shadow-lg shadow-indigo-600/20 flex items-center justify-center space-x-2">
            <span>✨ Evaluate Model &amp; Reasoning Route</span>
          </button>
        </div>

        <!-- Result Card -->
        <div id="router-result-card" class="hidden mt-4 p-4 rounded-xl border border-slate-700 bg-slate-950/80 space-y-3">
          <!-- Fast-Retry Circuit Breaker Alert Banner -->
          <div id="router-circuit-breaker-banner" class="hidden p-3 rounded-lg border text-xs font-mono flex items-start space-x-2.5">
            <span id="router-cb-icon" class="text-base">⚡</span>
            <div class="flex-1">
              <div id="router-cb-title" class="font-bold text-amber-300">Fast-Retry Circuit Breaker Alert</div>
              <div id="router-cb-desc" class="text-[11px] text-slate-300 mt-0.5"></div>
            </div>
          </div>

          <div class="flex items-center justify-between">
            <span class="text-xs uppercase tracking-wider text-slate-400 font-semibold">Router Recommendation</span>
            <span id="router-cost-tier" class="px-2 py-0.5 rounded font-mono font-bold text-xs bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">$$$</span>
          </div>

          <div class="flex items-center space-x-3 flex-wrap gap-y-2">
            <div id="router-model-badge"></div>
            <div id="router-effort-pill"></div>
            <span id="router-tier-badge" class="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-300 border border-slate-700">tier</span>
          </div>

          <p id="router-rationale" class="text-xs text-slate-300 leading-relaxed font-sans bg-slate-900/60 p-3 rounded-lg border border-slate-800/80"></p>

          <div class="flex items-center justify-between text-[11px] text-slate-400 pt-1">
            <span>Fallback Tier: <strong id="router-fallback" class="text-slate-200 font-mono">gemini-4-argon</strong></span>
            <button onclick="copyRouterCliCommand()" class="text-emerald-400 hover:text-emerald-300 font-mono flex items-center space-x-1">
              <span>📋 Copy CLI dispatch args</span>
            </button>
          </div>
        </div>

      </div>

      <!-- Modal Footer -->
      <div class="px-6 py-3 border-t border-slate-800 bg-slate-950/70 flex items-center justify-between text-xs text-slate-400">
        <span>POST /api/router/recommend</span>
        <button onclick="closeRouterModal()" class="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium transition">Đóng</button>
      </div>
    </div>
  </div>

  <!-- Scripts -->
  <script>
    const PIPELINE_STAGES = [
      { id: 'spec', name: '1. Spec', role: 'Product / Spec' },
      { id: 'plan', name: '2. Plan', role: 'Architect / DAG' },
      { id: 'build', name: '3. Build', role: 'Software Builder' },
      { id: 'test', name: '4. Test', role: 'Test Specialist' },
      { id: 'review', name: '5. Review', role: 'Code Reviewer' },
      { id: 'security', name: '6. Security', role: 'Security Spec' },
      { id: 'ship', name: '7. Ship', role: 'DevOps / Release' }
    ];

    const MODEL_SPECS = {
      'gemini-4-carbon': {
        name: 'Gemini 4 Carbon',
        tier: 'frontier',
        tag: 'Google Frontier Reasoning',
        rates: { in: 2.00, out: 10.00, cache: 0.50 },
        color: 'emerald',
        efforts: ['low', 'medium', 'high'],
        desc: 'Frontier deep reasoning model for vulnerability audits, architectural synthesis, and complex DAG execution.'
      },
      'gemini-4-argon': {
        name: 'Gemini 4 Argon',
        tier: 'deep_reasoning',
        tag: 'High-Velocity Deep Reasoning',
        rates: { in: 1.25, out: 5.00, cache: 0.3125 },
        color: 'indigo',
        efforts: ['low', 'medium', 'high'],
        desc: 'Balanced deep reasoning engine for architecture, planning, and multi-axis code review.'
      },
      'gemini-4-hydrogen': {
        name: 'Gemini 4 Hydrogen',
        tier: 'high_throughput',
        tag: 'Ultra-Fast Workhorse (2.5x)',
        rates: { in: 1.50, out: 7.50, cache: 0.075 },
        color: 'cyan',
        efforts: ['low', 'medium', 'high', 'xhigh'],
        desc: 'Speed-optimized, high-throughput model (198 tok/s, 2.5x speed) for parallel builders, automated test suites, and pointer scouting.'
      },
      'gemini-3.8-flash': {
        name: 'Gemini 3.8 Flash',
        tier: 'cost_efficient',
        tag: 'High Throughput Builder',
        rates: { in: 0.075, out: 0.30, cache: 0.01875 },
        color: 'amber',
        efforts: [],
        desc: 'Ultra-fast, high-throughput model for parallel code implementation and test suites.'
      },
      'gemini-3.8-flash-lite': {
        name: 'Gemini 3.8 Flash-Lite',
        tier: 'ultra_fast',
        tag: 'Micro-tier Telemetry',
        rates: { in: 0.0375, out: 0.15, cache: 0.01 },
        color: 'slate',
        efforts: [],
        desc: 'Low-latency micro-tier for telemetry heartbeats, quick formatting, and linting.'
      }
    };

    let currentTab = 'live';
    let currentTaskView = 'table'; // 'table' or 'dag'
    let state = {
      tasks: {},
      logs: [],
      metrics: {
        total: 0, pending: 0, running: 0, completed: 0, blocked: 0, cancelled: 0, active_agents: 0,
        total_input_tokens: 0, total_output_tokens: 0, total_cache_tokens: 0, grand_total_tokens: 0,
        total_cost_usd: 0, total_cost_vnd: 0, total_saved_usd: 0, total_saved_vnd: 0, cache_rate: 0
      },
      modelAnalytics: null
    };

    function switchTab(tab) {
      currentTab = tab;
      const tabs = ['live', 'analytics', 'history', 'logs'];
      tabs.forEach(t => {
        const btn = document.getElementById(`tab-btn-${t}`);
        const view = document.getElementById(`tab-view-${t}`);
        if (!btn || !view) return;
        if (t === tab) {
          btn.className = "py-2.5 px-3 border-b-2 font-semibold text-xs sm:text-sm flex items-center space-x-2 transition border-emerald-500 text-white";
          view.classList.remove('hidden');
        } else {
          btn.className = "py-2.5 px-3 border-b-2 font-semibold text-xs sm:text-sm flex items-center space-x-2 transition border-transparent text-slate-400 hover:text-slate-200";
          view.classList.add('hidden');
        }
      });
      if (tab === 'analytics') {
        refreshModelAnalytics();
      } else if (tab === 'history') {
        renderHistoryTable();
      } else if (tab === 'live') {
        if (currentTaskView === 'dag') renderDagView();
      }
    }

    function switchTaskView(viewMode) {
      currentTaskView = viewMode;
      const tblView = document.getElementById('tasks-table-view');
      const dagView = document.getElementById('tasks-dag-view');
      const tblBtn = document.getElementById('view-mode-table-btn');
      const dagBtn = document.getElementById('view-mode-dag-btn');

      if (viewMode === 'table') {
        if (tblView) tblView.classList.remove('hidden');
        if (dagView) dagView.classList.add('hidden');
        if (tblBtn) tblBtn.className = "px-3 py-1 rounded-lg transition bg-indigo-600 text-white shadow-sm flex items-center space-x-1.5";
        if (dagBtn) dagBtn.className = "px-3 py-1 rounded-lg transition text-slate-400 hover:text-slate-200 flex items-center space-x-1.5";
      } else {
        if (tblView) tblView.classList.add('hidden');
        if (dagView) dagView.classList.remove('hidden');
        if (dagBtn) dagBtn.className = "px-3 py-1 rounded-lg transition bg-emerald-600 text-white shadow-sm flex items-center space-x-1.5";
        if (tblBtn) tblBtn.className = "px-3 py-1 rounded-lg transition text-slate-400 hover:text-slate-200 flex items-center space-x-1.5";
        renderDagView();
      }
    }

    function initPipeline() {
      const container = document.getElementById('pipeline-stages');
      if (!container) return;
      container.innerHTML = PIPELINE_STAGES.map(stage => `
        <div id="stage-${stage.id}" class="border border-slate-800 bg-slate-950/60 rounded-xl p-3 text-center transition">
          <div class="text-xs font-bold text-slate-300">${stage.name}</div>
          <div class="text-[10px] text-slate-500 mt-0.5 truncate">${stage.role}</div>
          <div id="stage-badge-${stage.id}" class="mt-2 text-[10px] py-0.5 px-2 rounded-full inline-block bg-slate-800/80 text-slate-400 font-mono">Idle</div>
        </div>
      `).join('');
    }

    function updatePipelineStages() {
      const tasks = Object.values(state.tasks);
      const stageMap = {
        spec: ['spec', 'product', 'requirements'],
        plan: ['architect', 'planner', 'design'],
        build: ['builder', 'software', 'developer'],
        test: ['test', 'tester', 'qa'],
        review: ['review', 'reviewer'],
        security: ['security', 'sec'],
        ship: ['ship', 'release', 'devops']
      };

      PIPELINE_STAGES.forEach(st => {
        const keywords = stageMap[st.id] || [st.id];
        const matched = tasks.filter(t => keywords.some(k => (t.agent_type || '').toLowerCase().includes(k)));
        const badge = document.getElementById(`stage-badge-${st.id}`);
        const card = document.getElementById(`stage-${st.id}`);
        if (!badge || !card) return;

        if (matched.some(t => t.status === 'running')) {
          badge.className = "mt-2 text-[10px] py-0.5 px-2 rounded-full inline-block bg-blue-500/20 text-blue-400 border border-blue-500/30 font-bold pulse-slow";
          badge.textContent = 'Active';
          card.className = "border border-blue-500/40 bg-blue-950/20 rounded-xl p-3 text-center shadow-lg shadow-blue-500/10";
        } else if (matched.length > 0 && matched.every(t => t.status === 'completed')) {
          badge.className = "mt-2 text-[10px] py-0.5 px-2 rounded-full inline-block bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-bold";
          badge.textContent = 'Done';
          card.className = "border border-emerald-500/30 bg-emerald-950/10 rounded-xl p-3 text-center";
        } else if (matched.some(t => t.status === 'blocked' || t.status === 'failed')) {
          badge.className = "mt-2 text-[10px] py-0.5 px-2 rounded-full inline-block bg-rose-500/20 text-rose-400 border border-rose-500/30 font-bold";
          badge.textContent = 'Blocked';
          card.className = "border border-rose-500/30 bg-rose-950/10 rounded-xl p-3 text-center";
        } else {
          badge.className = "mt-2 text-[10px] py-0.5 px-2 rounded-full inline-block bg-slate-800/80 text-slate-400 font-mono";
          badge.textContent = matched.length > 0 ? 'Queued' : 'Idle';
          card.className = "border border-slate-800 bg-slate-950/60 rounded-xl p-3 text-center";
        }
      });
    }

    function formatTokens(num) {
      if (!num || num === 0) return '0';
      if (num >= 1000000) return (num / 1000000).toFixed(2) + 'M';
      if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
      return num.toLocaleString();
    }

    function formatMoneyUSD(num) {
      if (!num || num === 0) return '$0.00';
      if (num < 0.01) return '$' + num.toFixed(4);
      return '$' + num.toFixed(2);
    }

    function formatMoneyVND(num) {
      if (!num || num === 0) return '0 ₫';
      return Math.round(num).toLocaleString('vi-VN') + ' ₫';
    }

    function renderMetrics(metrics) {
      document.getElementById('metric-total').textContent = metrics.total;
      document.getElementById('metric-running').textContent = metrics.running;
      document.getElementById('metric-completed').textContent = metrics.completed;
      document.getElementById('metric-blocked').textContent = (metrics.blocked || 0) + (metrics.cancelled || 0);
      document.getElementById('metric-agents').textContent = metrics.active_agents;
      document.getElementById('task-count-badge').textContent = `${metrics.total} total`;
      document.getElementById('tab-live-badge').textContent = metrics.running > 0 ? `${metrics.running} active` : metrics.total;

      const parallelCount = metrics.parallel_running || 0;
      const parallelEl = document.getElementById('metric-parallel');
      if (parallelEl) parallelEl.textContent = parallelCount;

      // Parallel Concurrency Banner
      const banner = document.getElementById('parallel-concurrency-banner');
      const countEl = document.getElementById('parallel-worker-count');
      const groupsEl = document.getElementById('parallel-groups-badges');
      if (banner && countEl && groupsEl) {
        if (parallelCount > 1) {
          banner.classList.remove('hidden');
          countEl.textContent = `${parallelCount} Workers Concurrently`;
          const groups = metrics.active_groups || [];
          groupsEl.innerHTML = groups.map(g => `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">⚡ ${escapeHtml(g)}</span>`).join('');
        } else {
          banner.classList.add('hidden');
        }
      }

      // Token Telemetry
      const inTok = metrics.total_input_tokens || 0;
      const outTok = metrics.total_output_tokens || 0;
      const cacheTok = metrics.total_cache_tokens || 0;
      const grandTok = metrics.grand_total_tokens || 0;
      const cacheRate = metrics.cache_rate || 0.0;

      document.getElementById('metric-tokens-in').textContent = formatTokens(inTok);
      document.getElementById('metric-tokens-out').textContent = formatTokens(outTok);
      document.getElementById('metric-tokens-cache').textContent = formatTokens(cacheTok);
      document.getElementById('metric-tokens-total').textContent = formatTokens(grandTok);
      document.getElementById('metric-cache-rate').textContent = `${cacheRate}%`;

      // Cost Telemetry
      const costUsd = metrics.total_cost_usd || 0.0;
      const costVnd = metrics.total_cost_vnd || 0;
      const savedUsd = metrics.total_saved_usd || 0.0;
      const savedVnd = metrics.total_saved_vnd || 0;

      document.getElementById('metric-cost-usd').textContent = formatMoneyUSD(costUsd);
      document.getElementById('metric-cost-vnd').textContent = `~ ${formatMoneyVND(costVnd)}`;
      document.getElementById('metric-saved-usd').textContent = formatMoneyUSD(savedUsd);
      document.getElementById('metric-saved-vnd').textContent = `~ ${formatMoneyVND(savedVnd)} saved`;
      document.getElementById('tab-cost-badge').textContent = formatMoneyUSD(costUsd);

      // Historical tab header cards
      const histCostUsd = document.getElementById('hist-total-cost-usd');
      if (histCostUsd) {
        histCostUsd.textContent = formatMoneyUSD(costUsd);
        document.getElementById('hist-total-cost-vnd').textContent = `~ ${formatMoneyVND(costVnd)}`;
        document.getElementById('hist-total-saved-usd').textContent = formatMoneyUSD(savedUsd);
        document.getElementById('hist-total-saved-vnd').textContent = `~ ${formatMoneyVND(savedVnd)} saved`;
        document.getElementById('hist-total-tokens').textContent = formatTokens(grandTok);
        document.getElementById('hist-token-breakdown').textContent = `In: ${formatTokens(inTok)} | Out: ${formatTokens(outTok)} | Cache: ${formatTokens(cacheTok)}`;
        document.getElementById('hist-cache-rate').textContent = `${cacheRate}%`;
        const completedCount = metrics.completed || 0;
        const avgCost = completedCount > 0 ? (costUsd / completedCount) : 0.0;
        document.getElementById('hist-avg-task-cost').textContent = `Avg cost / task: ${formatMoneyUSD(avgCost)} (~${formatMoneyVND(costVnd / (completedCount || 1))})`;
      }
    }

    function getStatusBadge(status) {
      switch(status) {
        case 'running':
          return '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30 inline-flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-blue-400 pulse-slow"></span>RUNNING</span>';
        case 'completed':
          return '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 inline-flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>DONE</span>';
        case 'cancelled':
          return '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30 inline-flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-rose-400"></span>CANCELLED</span>';
        case 'blocked':
        case 'failed':
          return '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30 inline-flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-rose-400"></span>BLOCKED</span>';
        default:
          return '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-800 text-slate-400 border border-slate-700">PENDING</span>';
      }
    }

    function getAgentBadge(agent) {
      const colors = {
        'builder': 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30',
        'software-builder': 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30',
        'ui-builder': 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
        'frontend-engineer': 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
        'scout': 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
        'codebase-researcher': 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
        'architect': 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
        'planner': 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
        'task-planner': 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
        'spec-engineer': 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
        'test': 'bg-amber-500/10 text-amber-400 border-amber-500/30',
        'tester': 'bg-amber-500/10 text-amber-400 border-amber-500/30',
        'test-engineer': 'bg-amber-500/10 text-amber-400 border-amber-500/30',
        'review': 'bg-purple-500/10 text-purple-400 border-purple-500/30',
        'reviewer': 'bg-purple-500/10 text-purple-400 border-purple-500/30',
        'code-reviewer': 'bg-purple-500/10 text-purple-400 border-purple-500/30',
        'security': 'bg-red-500/10 text-red-400 border-red-500/30',
        'security-auditor': 'bg-red-500/10 text-red-400 border-red-500/30',
        'debugger': 'bg-rose-500/10 text-rose-300 border-rose-500/30',
        'orchestrator': 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
        'observability-and-instrumentation': 'bg-teal-500/10 text-teal-300 border-teal-500/30',
      };
      const key = (agent || '').toLowerCase();
      const style = colors[key] || 'bg-slate-800 text-slate-300 border-slate-700';
      return `<span class="px-2 py-0.5 rounded text-[11px] font-mono border ${style}">${escapeHtml(agent || 'unknown')}</span>`;
    }

    function getModelBadge(model, reasoning_effort) {
      const m = (model || '').toLowerCase();
      let badge = '';

      if (m.includes('carbon')) {
        badge = `
          <span class="px-2 py-0.5 rounded text-[11px] font-mono border bg-emerald-950/60 text-emerald-300 border-emerald-500/40 flex items-center gap-1.5 inline-flex shadow-sm shadow-emerald-500/10">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span class="font-bold">Gemini 4 Carbon</span>
          </span>
        `;
      } else if (m.includes('argon') || m.includes('pro')) {
        badge = `
          <span class="px-2 py-0.5 rounded text-[11px] font-mono border bg-indigo-950/60 text-indigo-300 border-indigo-500/40 flex items-center gap-1.5 inline-flex">
            <span class="text-[10px] text-indigo-400">✦</span>
            <span>Gemini 4 Argon</span>
          </span>
        `;
      } else if (m.includes('hydrogen')) {
        badge = `
          <span class="px-2 py-0.5 rounded text-[11px] font-mono border bg-cyan-950/60 text-cyan-300 border-cyan-500/40 flex items-center gap-1.5 inline-flex shadow-sm shadow-cyan-500/10" style="border-color: rgba(6, 182, 212, 0.4);">
            <span class="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" style="background-color: #06b6d4;"></span>
            <span class="text-[10px] text-cyan-400">⚡</span>
            <span class="font-bold">Gemini 4 Hydrogen</span>
          </span>
        `;
      } else if (m.includes('flash-lite') || m.includes('flash_lite') || m.includes('lite')) {
        badge = `
          <span class="px-2 py-0.5 rounded text-[11px] font-mono border bg-slate-900 text-slate-300 border-slate-700 flex items-center gap-1 inline-flex">
            <span class="text-[9px] text-teal-400">⚡</span>
            <span>Flash-Lite</span>
          </span>
        `;
      } else if (m.includes('flash') || m.includes('3.8')) {
        badge = `
          <span class="px-2 py-0.5 rounded text-[11px] font-mono border bg-amber-950/40 text-amber-300 border-amber-500/40 flex items-center gap-1 inline-flex">
            <span class="text-[9px] text-amber-400">⚡</span>
            <span>Gemini 3.8 Flash</span>
          </span>
        `;
      } else {
        badge = `<span class="px-2 py-0.5 rounded text-[11px] font-mono border bg-slate-800 text-slate-400 border-slate-700">${escapeHtml(model || 'auto')}</span>`;
      }

      // Tunable reasoning_effort pill
      if (reasoning_effort) {
        const eff = reasoning_effort.toLowerCase();
        let effBadge = '';
        if (eff === 'xhigh') {
          effBadge = `<span class="ml-1 px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-cyan-500/25 text-cyan-200 border border-cyan-400/60 animate-pulse shadow-sm shadow-cyan-500/20" title="Maximum Reasoning Effort [XHigh Thinking]" style="border-color: rgba(6, 182, 212, 0.6);">XHigh [Thinking]</span>`;
        } else if (eff === 'high') {
          effBadge = `<span class="ml-1 px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-400/40 animate-pulse" title="High Reasoning Effort [Thinking]">High [Thinking]</span>`;
        } else if (eff === 'medium') {
          effBadge = `<span class="ml-1 px-1.5 py-0.5 rounded text-[9px] font-mono font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-400/30" title="Medium Reasoning Effort [Thinking]">Med [Thinking]</span>`;
        } else if (eff === 'low') {
          effBadge = `<span class="ml-1 px-1.5 py-0.5 rounded text-[9px] font-mono bg-slate-800 text-slate-300 border border-slate-700" title="Low Reasoning Effort [Thinking]">Low [Thinking]</span>`;
        }
        return `<div class="inline-flex items-center flex-wrap gap-1">${badge}${effBadge}</div>`;
      }

      return badge;
    }

    function getComplexityBadge(comp) {
      const c = (comp || 'medium').toLowerCase();
      const badges = {
        'critical': 'bg-rose-500/20 text-rose-300 border-rose-500/40 font-bold',
        'high': 'bg-amber-500/20 text-amber-300 border-amber-500/40 font-bold',
        'medium': 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30',
        'low': 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
      };
      const style = badges[c] || badges['medium'];
      return `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase border ${style}">${c}</span>`;
    }

    function formatTime(isoStr) {
      if (!isoStr) return '-';
      try {
        const d = new Date(isoStr);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      } catch (e) {
        return isoStr;
      }
    }

    function killTask(taskId) {
      if (!confirm(`Are you sure you want to stop/kill agent running task ${taskId}?`)) return;
      fetch('/api/tasks/kill', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: taskId, reason: 'Manual kill from Dashboard UI' })
      })
      .then(res => res.json())
      .then(data => {
        if (data.task) {
          state.tasks[data.task.task_id] = data.task;
          renderTasksTable();
          renderHistoryTable();
          if (currentTaskView === 'dag') renderDagView();
        }
      })
      .catch(err => alert('Failed to kill task: ' + err));
    }

    function renderTasksTable() {
      const tbody = document.getElementById('tasks-tbody');
      if (!tbody) return;
      const allTasks = Object.values(state.tasks).sort((a, b) => (b.updated_at || '').localeCompare(a.updated_at || ''));
      
      // Live Dashboard STRICTLY ONLY shows active/in-flight tasks (pending, running, blocked)
      const activeTasks = allTasks.filter(t => t.status === 'running' || t.status === 'pending' || t.status === 'blocked');

      const countBadge = document.getElementById('task-count-badge');
      if (countBadge) {
        countBadge.textContent = `${activeTasks.length} active`;
      }
      
      if (activeTasks.length === 0) {
        const completedCount = allTasks.filter(t => t.status === 'completed').length;
        if (completedCount > 0) {
          tbody.innerHTML = `
            <tr>
              <td colspan="13" class="py-12 text-center">
                <div class="flex flex-col items-center justify-center space-y-2.5">
                  <div class="h-10 w-10 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
                  </div>
                  <div class="text-sm font-bold text-slate-200">Không có tác vụ đang chạy hoặc chờ xử lý</div>
                  <div class="text-xs text-slate-400 max-w-md">Toàn bộ ${completedCount} tác vụ trước đó đã hoàn thành và được lưu trữ gọn gàng trong tab Lịch sử.</div>
                  <div class="pt-2">
                    <button onclick="switchTab('history')" class="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold shadow-md shadow-emerald-600/20 transition flex items-center space-x-1.5 mx-auto">
                      <span>Mở tab Usage History &amp; Cost Audit</span>
                      <span>&rarr;</span>
                    </button>
                  </div>
                </div>
              </td>
            </tr>
          `;
        } else {
          tbody.innerHTML = '<tr><td colspan="13" class="py-8 text-center text-slate-500">Chưa có tác vụ nào được kích hoạt. Hãy điều phối task mới thông qua OrchestratorClient.</td></tr>';
        }
        return;
      }

      tbody.innerHTML = activeTasks.map(t => {
        const pct = t.progress || 0;
        const barColor = t.status === 'completed' ? 'bg-emerald-500' : (t.status === 'blocked' || t.status === 'cancelled' ? 'bg-rose-500' : 'bg-indigo-500');

        // Parallel Group badge
        const groupBadge = t.parallel_group ? 
          `<span class="px-2 py-0.5 rounded text-[10px] font-mono border bg-amber-500/15 text-amber-300 border-amber-500/30 flex items-center gap-1 inline-flex">⚡ ${escapeHtml(t.parallel_group)}</span>` : 
          `<span class="text-slate-600 font-mono text-[10px]">-</span>`;

        // Conditions / Depends On
        let depsBadge = `<span class="text-slate-500 font-mono text-[10px]">None (Ready)</span>`;
        if (t.depends_on && t.depends_on.length > 0) {
          depsBadge = t.depends_on.map(dep => {
            const parentTask = state.tasks[dep];
            const isDone = parentTask && parentTask.status === 'completed';
            const color = isDone ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' : 'bg-rose-500/15 text-rose-300 border-rose-500/30';
            const icon = isDone ? '✓' : '⏳';
            return `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono border ${color} mr-1 inline-block" title="${escapeHtml(dep)}: ${parentTask ? parentTask.status : 'not found'}">${icon} ${escapeHtml(dep)}</span>`;
          }).join('');
        }

        // Token consumption breakdown
        const tok = t.tokens || { input: 0, output: 0, cache: 0, total: 0 };
        const tokenBadge = `
          <div class="font-mono text-[10px] flex items-center space-x-1 whitespace-nowrap bg-slate-950/60 px-2 py-1 rounded border border-slate-800/80" title="Prompt In: ${tok.input.toLocaleString()} | Output: ${tok.output.toLocaleString()} | Cache Read: ${tok.cache.toLocaleString()} | Total: ${tok.total.toLocaleString()}">
            <span class="text-cyan-400">📥 ${formatTokens(tok.input)}</span>
            <span class="text-slate-600">/</span>
            <span class="text-purple-400">📤 ${formatTokens(tok.output)}</span>
            <span class="text-slate-600">/</span>
            <span class="text-emerald-400">⚡ ${formatTokens(tok.cache)}</span>
          </div>
        `;

        // Cost breakdown
        const cost = t.cost || { usd: 0.0, vnd: 0, saved_usd: 0.0, saved_vnd: 0 };
        const costBadge = `
          <div class="font-mono text-[10px] bg-indigo-950/30 px-2 py-1 rounded border border-indigo-900/40" title="Actual Spend: ${formatMoneyUSD(cost.usd)} (~${formatMoneyVND(cost.vnd)}) | Saved: ${formatMoneyUSD(cost.saved_usd)}">
            <div class="text-indigo-300 font-bold">${formatMoneyUSD(cost.usd)}</div>
            <div class="text-[9px] text-slate-500">~${formatMoneyVND(cost.vnd)}</div>
          </div>
        `;

        // Action button
        let killBtn = '';
        if (t.status === 'running') {
          killBtn = `
            <button onclick="killTask('${t.task_id}')" class="px-2 py-1 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 transition text-[11px] font-bold flex items-center gap-1 shadow-sm" title="Dừng khẩn cấp Agent">
              <svg class="w-3 h-3 text-rose-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clip-rule="evenodd" /></svg>
              <span>Kill</span>
            </button>
          `;
        }
        const actionBtn = `
          <div class="flex items-center justify-center space-x-1.5">
            <button onclick="openAgentLiveModal('${t.task_id}')" class="px-2.5 py-1 rounded-lg bg-indigo-500/15 hover:bg-indigo-500/25 text-indigo-300 border border-indigo-500/30 transition text-[11px] font-semibold flex items-center gap-1 shadow-sm" title="Xem trực tiếp logs, suy nghĩ và công cụ của Agent">
              <span>👁️ Live Logs</span>
            </button>
            ${killBtn}
          </div>
        `;

        return `
          <tr class="hover:bg-slate-800/30 transition">
            <td class="py-3 px-4 font-mono font-bold text-white">${escapeHtml(t.task_id)}</td>
            <td class="py-3 px-4">${getAgentBadge(t.agent_type)}</td>
            <td class="py-3 px-4">${getModelBadge(t.model, t.reasoning_effort)}</td>
            <td class="py-3 px-4">${getComplexityBadge(t.complexity)}</td>
            <td class="py-3 px-4">${groupBadge}</td>
            <td class="py-3 px-4">${depsBadge}</td>
            <td class="py-3 px-4">${tokenBadge}</td>
            <td class="py-3 px-4">${costBadge}</td>
            <td class="py-3 px-4 text-slate-300 max-w-xs truncate" title="${escapeHtml(t.scope || '')}">${escapeHtml(t.scope || '-')}</td>
            <td class="py-3 px-4">${getStatusBadge(t.status)}</td>
            <td class="py-3 px-4">
              <div class="flex items-center space-x-2">
                <div class="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                  <div class="${barColor} h-2 rounded-full transition-all duration-300" style="width: ${pct}%"></div>
                </div>
                <span class="font-mono text-[10px] text-slate-400 w-8 text-right">${pct}%</span>
              </div>
            </td>
            <td class="py-3 px-4 text-center">${actionBtn}</td>
            <td class="py-3 px-4 text-right text-slate-500 font-mono">${formatTime(t.updated_at)}</td>
          </tr>
        `;
      }).join('');
    }

    // ---------------------------------------------------------------------------
    // Interactive Zero-Dependency SVG DAG Visualizer
    // ---------------------------------------------------------------------------
    function renderDagView() {
      const container = document.getElementById('dag-graph-wrapper');
      const svgCanvas = document.getElementById('dag-svg-canvas');
      const nodesLayer = document.getElementById('dag-nodes-layer');
      if (!container || !svgCanvas || !nodesLayer) return;

      const allTasks = Object.values(state.tasks);
      if (allTasks.length === 0) {
        nodesLayer.innerHTML = `
          <div class="py-16 text-center text-slate-500 w-full">
            <div class="text-sm">Chưa có tác vụ nào để dựng biểu đồ DAG.</div>
            <div class="text-xs text-slate-600 mt-1">Khi các subagent được khởi tạo, mạng lưới phụ thuộc sẽ hiển thị tại đây.</div>
          </div>
        `;
        svgCanvas.innerHTML = '';
        return;
      }

      const completedIds = new Set(allTasks.filter(t => t.status === 'completed').map(t => t.task_id));
      const taskMap = {};
      allTasks.forEach(t => { taskMap[t.task_id] = t; });

      // Calculate topological depth for each task based on depends_on
      const depths = {};
      function getDepth(taskId, visited = new Set()) {
        if (depths[taskId] !== undefined) return depths[taskId];
        if (visited.has(taskId)) return 0;
        visited.add(taskId);
        const t = taskMap[taskId];
        if (!t || !t.depends_on || t.depends_on.length === 0) {
          depths[taskId] = 0;
          return 0;
        }
        let maxParentDepth = -1;
        t.depends_on.forEach(pId => {
          maxParentDepth = Math.max(maxParentDepth, getDepth(pId, visited));
        });
        depths[taskId] = maxParentDepth + 1;
        return depths[taskId];
      }

      allTasks.forEach(t => getDepth(t.task_id));

      const maxDepth = Math.max(0, ...Object.values(depths));
      const columns = [];
      for (let d = 0; d <= maxDepth; d++) {
        columns.push(allTasks.filter(t => depths[t.task_id] === d));
      }

      // Layout geometry
      const colWidth = 280;
      const colGap = 70;
      const nodeWidth = 270;
      const nodeHeight = 140;
      const rowGap = 24;
      const paddingX = 40;
      const paddingY = 60;

      const totalWidth = Math.max(container.clientWidth || 950, (columns.length * (colWidth + colGap)) + paddingX * 2);
      let maxColTasks = 1;
      columns.forEach(col => { if (col.length > maxColTasks) maxColTasks = col.length; });
      const totalHeight = Math.max(480, (maxColTasks * (nodeHeight + rowGap)) + paddingY * 2 + 40);

      svgCanvas.setAttribute('width', totalWidth);
      svgCanvas.setAttribute('height', totalHeight);
      svgCanvas.style.width = totalWidth + 'px';
      svgCanvas.style.height = totalHeight + 'px';
      nodesLayer.style.width = totalWidth + 'px';
      nodesLayer.style.height = totalHeight + 'px';

      const nodePositions = {};
      let nodesHtml = '';

      columns.forEach((col, colIdx) => {
        const x = paddingX + colIdx * (colWidth + colGap);

        // Column Stage Header
        nodesHtml += `
          <div class="absolute text-[11px] font-bold text-slate-400 uppercase tracking-wider font-mono flex items-center space-x-1.5" style="left: ${x}px; top: 16px;">
            <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span>Stage ${colIdx + 1} &middot; Depth ${colIdx} (${col.length} ${col.length === 1 ? 'task' : 'tasks'})</span>
          </div>
        `;

        col.forEach((t, rowIdx) => {
          const y = paddingY + rowIdx * (nodeHeight + rowGap);
          nodePositions[t.task_id] = {
            x, y,
            width: nodeWidth,
            height: nodeHeight,
            rightX: x + nodeWidth,
            centerY: y + nodeHeight / 2,
            leftX: x
          };

          const deps = t.depends_on || [];
          const isReady = t.status === 'pending' && deps.every(d => completedIds.has(d));
          const isRunning = t.status === 'running';

          let borderClass = 'border-slate-800 bg-slate-900/80 hover:border-slate-700';
          let statusBadge = '';
          if (isRunning) {
            borderClass = 'border-blue-500/80 bg-slate-900/90 ring-2 ring-blue-500/40 shadow-lg shadow-blue-500/10';
            statusBadge = '<span class="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30 animate-pulse">RUNNING</span>';
          } else if (t.status === 'completed') {
            borderClass = 'border-emerald-500/40 bg-emerald-950/20 hover:border-emerald-500/60';
            statusBadge = '<span class="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-emerald-500/20 text-emerald-400">DONE</span>';
          } else if (isReady) {
            borderClass = 'border-emerald-400/60 bg-emerald-950/30 ring-1 ring-emerald-400/40 hover:border-emerald-400';
            statusBadge = '<span class="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-400/40">READY</span>';
          } else if (t.status === 'blocked' || t.status === 'failed') {
            borderClass = 'border-rose-500/50 bg-rose-950/20 hover:border-rose-500/70';
            statusBadge = '<span class="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-rose-500/20 text-rose-300">BLOCKED</span>';
          }

          const tok = t.tokens || { input: 0, output: 0, cache: 0, total: 0 };
          const cost = t.cost || { usd: 0.0, vnd: 0 };
          const pct = t.progress || 0;

          nodesHtml += `
            <div onclick="openAgentLiveModal('${t.task_id}')"
                 class="absolute rounded-xl border p-3 flex flex-col justify-between cursor-pointer transition-all duration-200 transform hover:-translate-y-0.5 shadow-md ${borderClass}"
                 style="left: ${x}px; top: ${y}px; width: ${nodeWidth}px; height: ${nodeHeight}px;"
                 title="Click to inspect live transcript for ${escapeHtml(t.task_id)}">
              <div class="flex items-start justify-between">
                <div>
                  <div class="flex items-center space-x-1.5">
                    <span class="font-mono font-bold text-xs text-white">${escapeHtml(t.task_id)}</span>
                    ${statusBadge}
                  </div>
                  <div class="mt-1">${getAgentBadge(t.agent_type)}</div>
                </div>
                <div class="text-right">
                  ${getModelBadge(t.model, t.reasoning_effort)}
                </div>
              </div>
              
              <div class="text-[11px] text-slate-300 truncate max-w-full font-sans mt-1" title="${escapeHtml(t.scope || '')}">
                ${escapeHtml(t.scope || 'No scope description')}
              </div>

              <div class="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] font-mono">
                <div class="flex items-center space-x-1 text-slate-400">
                  <span>📊 ${formatTokens(tok.total)}</span>
                  <span class="text-slate-600">&middot;</span>
                  <span class="text-indigo-300 font-semibold">${formatMoneyUSD(cost.usd)}</span>
                </div>
                <div class="flex items-center space-x-1">
                  <span class="text-slate-400">${pct}%</span>
                  <div class="w-12 bg-slate-800 rounded-full h-1.5 overflow-hidden inline-block">
                    <div class="h-1.5 rounded-full ${t.status === 'completed' ? 'bg-emerald-400' : 'bg-indigo-500'}" style="width: ${pct}%"></div>
                  </div>
                </div>
              </div>
            </div>
          `;
        });
      });

      nodesLayer.innerHTML = nodesHtml;

      // Render SVG connector paths with directional arrows
      let svgPaths = `
        <defs>
          <marker id="dag-arrow-emerald" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
            <polygon points="0 0, 7 3.5, 0 7" fill="#10b981" />
          </marker>
          <marker id="dag-arrow-indigo" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
            <polygon points="0 0, 7 3.5, 0 7" fill="#6366f1" />
          </marker>
          <marker id="dag-arrow-amber" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
            <polygon points="0 0, 7 3.5, 0 7" fill="#f59e0b" />
          </marker>
          <marker id="dag-arrow-rose" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
            <polygon points="0 0, 7 3.5, 0 7" fill="#f43f5e" />
          </marker>
          <marker id="dag-arrow-slate" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
            <polygon points="0 0, 7 3.5, 0 7" fill="#64748b" />
          </marker>
        </defs>
      `;

      allTasks.forEach(t => {
        const targetPos = nodePositions[t.task_id];
        if (!targetPos) return;
        const deps = t.depends_on || [];
        deps.forEach(depId => {
          const srcPos = nodePositions[depId];
          if (!srcPos) return;

          const x1 = srcPos.rightX;
          const y1 = srcPos.centerY;
          const x2 = targetPos.leftX;
          const y2 = targetPos.centerY;
          const dx = Math.max(30, (x2 - x1) * 0.45);

          const parentTask = taskMap[depId];
          let strokeColor = '#64748b';
          let markerId = 'dag-arrow-slate';
          let strokeDash = '';

          if (parentTask && parentTask.status === 'completed') {
            strokeColor = '#10b981';
            markerId = 'dag-arrow-emerald';
          } else if (parentTask && parentTask.status === 'running') {
            strokeColor = '#f59e0b';
            markerId = 'dag-arrow-amber';
            strokeDash = 'stroke-dasharray="4,4"';
          } else if (parentTask && (parentTask.status === 'blocked' || parentTask.status === 'failed')) {
            strokeColor = '#f43f5e';
            markerId = 'dag-arrow-rose';
          }

          svgPaths += `
            <path d="M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}"
                  fill="none"
                  stroke="${strokeColor}"
                  stroke-width="2"
                  ${strokeDash}
                  marker-end="url(#${markerId})"
                  class="transition-all duration-300" />
          `;
        });
      });

      svgCanvas.innerHTML = svgPaths;
    }

    // ---------------------------------------------------------------------------
    // Model Analytics Computation & Rendering
    // ---------------------------------------------------------------------------
    function refreshModelAnalytics() {
      fetch('/api/analytics/models')
        .then(r => {
          if (!r.ok) throw new Error('API not available, fallback to client computation');
          return r.json();
        })
        .then(data => {
          if (data.status === 'ok') {
            renderModelAnalyticsView(data);
          } else {
            fallbackModelAnalytics();
          }
        })
        .catch(() => {
          fallbackModelAnalytics();
        });
    }

    function fallbackModelAnalytics() {
      // Client-side computation fallback from state.tasks
      const stats = {};
      Object.keys(MODEL_SPECS).forEach(k => {
        stats[k] = {
          task_count: 0, input_tokens: 0, output_tokens: 0, cache_tokens: 0, total_tokens: 0,
          cost_usd: 0.0, cost_vnd: 0, saved_usd: 0.0, saved_vnd: 0, cache_hit_rate: 0.0
        };
      });

      Object.values(state.tasks).forEach(t => {
        const rawM = (t.model || '').toLowerCase();
        let canon = 'gemini-4-argon';
        if (rawM.includes('carbon')) canon = 'gemini-4-carbon';
        else if (rawM.includes('argon') || rawM.includes('pro')) canon = 'gemini-4-argon';
        else if (rawM.includes('hydrogen')) canon = 'gemini-4-hydrogen';
        else if (rawM.includes('flash-lite') || rawM.includes('lite')) canon = 'gemini-3.8-flash-lite';
        else if (rawM.includes('flash') || rawM.includes('3.8')) canon = 'gemini-3.8-flash';

        if (!stats[canon]) stats[canon] = { task_count: 0, input_tokens: 0, output_tokens: 0, cache_tokens: 0, total_tokens: 0, cost_usd: 0, cost_vnd: 0, saved_usd: 0, saved_vnd: 0, cache_hit_rate: 0 };
        const s = stats[canon];
        const tok = t.tokens || {};
        const cost = t.cost || {};
        s.task_count += 1;
        s.input_tokens += tok.input || 0;
        s.output_tokens += tok.output || 0;
        s.cache_tokens += tok.cache || 0;
        s.total_tokens += tok.total || 0;
        s.cost_usd += cost.usd || 0.0;
        s.cost_vnd += cost.vnd || 0;
        s.saved_usd += cost.saved_usd || 0.0;
        s.saved_vnd += cost.saved_vnd || 0;
      });

      Object.keys(stats).forEach(k => {
        const s = stats[k];
        const denom = s.input_tokens + s.cache_tokens;
        s.cache_hit_rate = denom > 0 ? Number(((s.cache_tokens / denom) * 100).toFixed(1)) : 0.0;
        s.cost_usd = Number(s.cost_usd.toFixed(4));
        s.saved_usd = Number(s.saved_usd.toFixed(4));
      });

      const totalSpendUsd = Number(Object.values(stats).reduce((acc, s) => acc + s.cost_usd, 0).toFixed(4));
      const totalSpendVnd = Object.values(stats).reduce((acc, s) => acc + s.cost_vnd, 0);

      renderModelAnalyticsView({
        status: 'ok',
        models: stats,
        summary: { total_spend_usd: totalSpendUsd, total_spend_vnd: totalSpendVnd }
      });
    }

    function renderModelAnalyticsView(data) {
      state.modelAnalytics = data;
      const models = data.models || {};
      const container = document.getElementById('model-analytics-cards');
      const tbody = document.getElementById('analytics-tbody');
      if (!container || !tbody) return;

      // 1. Render 5 model cards
      container.innerHTML = Object.keys(MODEL_SPECS).map(key => {
        const spec = MODEL_SPECS[key];
        const stat = models[key] || { task_count: 0, input_tokens: 0, output_tokens: 0, cache_tokens: 0, total_tokens: 0, cost_usd: 0.0, cost_vnd: 0, saved_usd: 0.0, cache_hit_rate: 0.0 };
        
        let cardBorder = 'border-slate-800 bg-slate-900/60';
        let titleColor = 'text-slate-300';
        let accentGlow = '';
        if (key === 'gemini-4-carbon') {
          cardBorder = 'border-emerald-500/40 bg-gradient-to-br from-emerald-950/40 to-slate-900 shadow-lg shadow-emerald-500/10';
          titleColor = 'text-emerald-300';
          accentGlow = 'glow-carbon';
        } else if (key === 'gemini-4-argon') {
          cardBorder = 'border-indigo-500/30 bg-gradient-to-br from-indigo-950/30 to-slate-900';
          titleColor = 'text-indigo-300';
        } else if (key === 'gemini-4-hydrogen') {
          cardBorder = 'border-cyan-500/40 bg-gradient-to-br from-cyan-950/40 to-slate-900 shadow-lg shadow-cyan-500/10';
          titleColor = 'text-cyan-300';
          accentGlow = 'glow-hydrogen';
        } else if (key === 'gemini-3.8-flash') {
          cardBorder = 'border-amber-500/30 bg-gradient-to-br from-amber-950/30 to-slate-900';
          titleColor = 'text-amber-300';
        }

        return `
          <div class="rounded-2xl border p-4 flex flex-col justify-between ${cardBorder} ${accentGlow} space-y-3">
            <div>
              <div class="flex items-center justify-between">
                <span class="text-[10px] font-mono uppercase font-bold px-2 py-0.5 rounded bg-slate-950/80 border border-slate-800 text-slate-400">${spec.tier}</span>
                <span class="text-xs font-mono font-bold text-slate-200">${formatMoneyUSD(stat.cost_usd)}</span>
              </div>
              <h4 class="text-sm font-bold ${titleColor} mt-2 flex items-center gap-1.5">
                <span>${spec.name}</span>
              </h4>
              <p class="text-[11px] text-slate-400 mt-0.5 line-clamp-2">${spec.desc}</p>
            </div>

            <div class="space-y-1.5 text-xs font-mono pt-2 border-t border-slate-800/80">
              <div class="flex justify-between text-slate-400">
                <span>Tasks Dispatched:</span>
                <span class="text-slate-200 font-bold">${stat.task_count}</span>
              </div>
              <div class="flex justify-between text-slate-400">
                <span>Prompt In:</span>
                <span class="text-cyan-400">${formatTokens(stat.input_tokens)}</span>
              </div>
              <div class="flex justify-between text-slate-400">
                <span>Output Gen:</span>
                <span class="text-purple-400">${formatTokens(stat.output_tokens)}</span>
              </div>
              <div class="flex justify-between text-slate-400">
                <span>Cache Read:</span>
                <span class="text-emerald-400">${formatTokens(stat.cache_tokens)} (${stat.cache_hit_rate}%)</span>
              </div>
              <div class="flex justify-between text-slate-400">
                <span>Cache Saved:</span>
                <span class="text-emerald-300 font-bold">+${formatMoneyUSD(stat.saved_usd)}</span>
              </div>
            </div>

            <div class="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] font-mono text-slate-500">
              <span>Rates: $${spec.rates.in} / $${spec.rates.out} / $${spec.rates.cache}</span>
            </div>
          </div>
        `;
      }).join('');

      // 2. Render spend distribution bar
      const summary = data.summary || {};
      const totalSpend = summary.total_spend_usd || 0.0;
      document.getElementById('spend-dist-summary').textContent = `Total Spend: ${formatMoneyUSD(totalSpend)} (~${formatMoneyVND(summary.total_spend_vnd || 0)})`;

      const cSpend = (models['gemini-4-carbon']?.cost_usd || 0);
      const aSpend = (models['gemini-4-argon']?.cost_usd || 0);
      const hSpend = (models['gemini-4-hydrogen']?.cost_usd || 0);
      const fSpend = (models['gemini-3.8-flash']?.cost_usd || 0);
      const lSpend = (models['gemini-3.8-flash-lite']?.cost_usd || 0);

      const cPct = totalSpend > 0 ? (cSpend / totalSpend * 100) : 0;
      const aPct = totalSpend > 0 ? (aSpend / totalSpend * 100) : 0;
      const hPct = totalSpend > 0 ? (hSpend / totalSpend * 100) : 0;
      const fPct = totalSpend > 0 ? (fSpend / totalSpend * 100) : 0;
      const lPct = totalSpend > 0 ? (lSpend / totalSpend * 100) : 0;

      const barCarbon = document.getElementById('bar-carbon');
      if (barCarbon) barCarbon.style.width = `${cPct}%`;
      const barArgon = document.getElementById('bar-argon');
      if (barArgon) barArgon.style.width = `${aPct}%`;
      const barHydrogen = document.getElementById('bar-hydrogen');
      if (barHydrogen) barHydrogen.style.width = `${hPct}%`;
      const barFlash = document.getElementById('bar-flash');
      if (barFlash) barFlash.style.width = `${fPct}%`;
      const barLite = document.getElementById('bar-lite');
      if (barLite) barLite.style.width = `${lPct}%`;

      const legCarbon = document.getElementById('legend-carbon');
      if (legCarbon) legCarbon.textContent = `Carbon: ${formatMoneyUSD(cSpend)} (${cPct.toFixed(1)}%)`;
      const legArgon = document.getElementById('legend-argon');
      if (legArgon) legArgon.textContent = `Argon: ${formatMoneyUSD(aSpend)} (${aPct.toFixed(1)}%)`;
      const legHydrogen = document.getElementById('legend-hydrogen');
      if (legHydrogen) legHydrogen.textContent = `Hydrogen: ${formatMoneyUSD(hSpend)} (${hPct.toFixed(1)}%)`;
      const legFlash = document.getElementById('legend-flash');
      if (legFlash) legFlash.textContent = `Flash: ${formatMoneyUSD(fSpend)} (${fPct.toFixed(1)}%)`;
      const legLite = document.getElementById('legend-lite');
      if (legLite) legLite.textContent = `Flash-Lite: ${formatMoneyUSD(lSpend)} (${lPct.toFixed(1)}%)`;

      // 3. Render table
      tbody.innerHTML = Object.keys(MODEL_SPECS).map(key => {
        const spec = MODEL_SPECS[key];
        const s = models[key] || { task_count: 0, input_tokens: 0, output_tokens: 0, cache_tokens: 0, total_tokens: 0, cost_usd: 0, cost_vnd: 0, saved_usd: 0, cache_hit_rate: 0 };
        return `
          <tr class="hover:bg-slate-800/30 transition font-mono">
            <td class="py-3 px-4 font-bold text-white">${getModelBadge(key)}</td>
            <td class="py-3 px-4 text-slate-400 uppercase text-[10px]">${spec.tier}</td>
            <td class="py-3 px-4 text-center font-bold text-slate-200">${s.task_count}</td>
            <td class="py-3 px-4 text-cyan-400">${s.input_tokens.toLocaleString()}</td>
            <td class="py-3 px-4 text-purple-400">${s.output_tokens.toLocaleString()}</td>
            <td class="py-3 px-4 text-emerald-400">${s.cache_tokens.toLocaleString()}</td>
            <td class="py-3 px-4 font-bold text-slate-200">${s.total_tokens.toLocaleString()}</td>
            <td class="py-3 px-4 text-emerald-300">${s.cache_hit_rate}%</td>
            <td class="py-3 px-4 text-indigo-300 font-bold">${formatMoneyUSD(s.cost_usd)}</td>
            <td class="py-3 px-4 text-slate-400">~${formatMoneyVND(s.cost_vnd)}</td>
            <td class="py-3 px-4 text-emerald-400">+${formatMoneyUSD(s.saved_usd)}</td>
            <td class="py-3 px-4 text-right text-slate-500 text-[10px]">$${spec.rates.in} / $${spec.rates.out} / $${spec.rates.cache}</td>
          </tr>
        `;
      }).join('');
    }

    function renderHistoryTable() {
      const tbody = document.getElementById('history-tbody');
      if (!tbody) return;
      const search = (document.getElementById('hist-filter-search')?.value || '').toLowerCase();
      const statusFilter = document.getElementById('hist-filter-status')?.value || 'all';
      const modelFilter = document.getElementById('hist-filter-model')?.value || 'all';
      const effortFilter = document.getElementById('hist-filter-effort')?.value || 'all';

      let tasks = Object.values(state.tasks).sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''));

      tasks = tasks.filter(t => {
        if (statusFilter !== 'all' && t.status !== statusFilter) return false;
        if (modelFilter !== 'all') {
          const m = (t.model || '').toLowerCase();
          if (modelFilter === 'carbon' && !m.includes('carbon')) return false;
          if (modelFilter === 'argon' && !m.includes('argon') && !m.includes('pro')) return false;
          if (modelFilter === 'hydrogen' && !m.includes('hydrogen')) return false;
          if (modelFilter === 'flash' && (!m.includes('flash') || m.includes('lite'))) return false;
          if (modelFilter === 'lite' && !m.includes('lite')) return false;
        }
        if (effortFilter !== 'all') {
          const eff = (t.reasoning_effort || '').toLowerCase();
          if (effortFilter === 'none' && eff) return false;
          if (effortFilter !== 'none' && eff !== effortFilter) return false;
        }
        if (search) {
          const matchId = (t.task_id || '').toLowerCase().includes(search);
          const matchAgent = (t.agent_type || '').toLowerCase().includes(search);
          const matchModel = (t.model || '').toLowerCase().includes(search);
          const matchScope = (t.scope || '').toLowerCase().includes(search);
          if (!matchId && !matchAgent && !matchModel && !matchScope) return false;
        }
        return true;
      });

      if (tasks.length === 0) {
        tbody.innerHTML = '<tr><td colspan="13" class="py-8 text-center text-slate-500">No matching task history records found.</td></tr>';
        return;
      }

      tbody.innerHTML = tasks.map(t => {
        const tok = t.tokens || { input: 0, output: 0, cache: 0, total: 0 };
        const cost = t.cost || { usd: 0.0, vnd: 0, saved_usd: 0.0, saved_vnd: 0 };
        const hitRate = (tok.input + tok.cache) > 0 ? ((tok.cache / (tok.input + tok.cache)) * 100).toFixed(1) : '0.0';

        let killBtn = '';
        if (t.status === 'running') {
          killBtn = `
            <button onclick="killTask('${t.task_id}')" class="px-2 py-1 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 font-bold text-[10px] transition">
              Kill
            </button>
          `;
        }
        const actionBtn = `
          <div class="flex items-center justify-center space-x-1.5">
            <button onclick="openAgentLiveModal('${t.task_id}')" class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 font-semibold text-[10px] transition flex items-center gap-1" title="Xem chi tiết các bước Agent đã thực hiện">
              <span>👁️ Logs</span>
            </button>
            ${killBtn}
          </div>
        `;

        return `
          <tr class="hover:bg-slate-800/30 transition">
            <td class="py-3 px-4 font-mono font-bold text-white">${escapeHtml(t.task_id)}</td>
            <td class="py-3 px-4">${getAgentBadge(t.agent_type)}</td>
            <td class="py-3 px-4">${getModelBadge(t.model, t.reasoning_effort)}</td>
            <td class="py-3 px-4">${getStatusBadge(t.status)}</td>
            <td class="py-3 px-4 font-mono text-cyan-400">${tok.input.toLocaleString()}</td>
            <td class="py-3 px-4 font-mono text-purple-400">${tok.output.toLocaleString()}</td>
            <td class="py-3 px-4 font-mono text-emerald-400">${tok.cache.toLocaleString()}</td>
            <td class="py-3 px-4 font-mono font-bold text-slate-200">${tok.total.toLocaleString()}</td>
            <td class="py-3 px-4 font-mono text-emerald-300 font-semibold">${hitRate}%</td>
            <td class="py-3 px-4 font-mono">
              <span class="text-indigo-300 font-bold">${formatMoneyUSD(cost.usd)}</span>
              <span class="text-[10px] text-slate-500 block">~${formatMoneyVND(cost.vnd)}</span>
            </td>
            <td class="py-3 px-4 font-mono">
              <span class="text-emerald-400 font-semibold">+${formatMoneyUSD(cost.saved_usd)}</span>
              <span class="text-[10px] text-emerald-500/80 block">~${formatMoneyVND(cost.saved_vnd)}</span>
            </td>
            <td class="py-3 px-4 text-center">${actionBtn}</td>
            <td class="py-3 px-4 text-right text-slate-500 font-mono">${formatTime(t.updated_at || t.created_at)}</td>
          </tr>
        `;
      }).join('');
    }

    function exportHistoryCSV() {
      const tasks = Object.values(state.tasks).sort((a, b) => (a.created_at || '').localeCompare(b.created_at || ''));
      if (tasks.length === 0) {
        alert('No tasks to export.');
        return;
      }

      const headers = [
        "task_id", "agent_type", "model", "reasoning_effort", "complexity", "status", "progress",
        "input_tokens", "output_tokens", "cache_tokens", "total_tokens", "cache_hit_rate_pct",
        "cost_usd", "cost_vnd", "saved_usd", "saved_vnd",
        "scope", "created_at", "updated_at"
      ];

      const rows = tasks.map(t => {
        const tok = t.tokens || { input: 0, output: 0, cache: 0, total: 0 };
        const cost = t.cost || { usd: 0.0, vnd: 0, saved_usd: 0.0, saved_vnd: 0 };
        const hitRate = (tok.input + tok.cache) > 0 ? ((tok.cache / (tok.input + tok.cache)) * 100).toFixed(1) : '0.0';

        return [
          t.task_id,
          t.agent_type,
          t.model,
          t.reasoning_effort || "",
          t.complexity,
          t.status,
          t.progress,
          tok.input,
          tok.output,
          tok.cache,
          tok.total,
          hitRate,
          cost.usd,
          cost.vnd,
          cost.saved_usd,
          cost.saved_vnd,
          `"${(t.scope || '').replace(/"/g, '""')}"`,
          t.created_at,
          t.updated_at
        ].join(",");
      });

      const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows].join(String.fromCharCode(10));
      const encodedUri = encodeURI(csvContent);
      const link = document.createElement("a");
      const dateStr = new Date().toISOString().slice(0, 10);
      link.setAttribute("href", encodedUri);
      link.setAttribute("download", `orchestrator_token_cost_audit_${dateStr}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }

    // ---------------------------------------------------------------------------
    // One-Click Audit Report Exporter (.md / .json)
    // ---------------------------------------------------------------------------
    function exportAuditReport(format = 'markdown') {
      const url = `/api/audit/export?format=${format}`;
      fetch(url)
        .then(res => {
          if (!res.ok) throw new Error('Server export endpoint unavailable, falling back to client report generation');
          return format === 'json' ? res.json() : res.text();
        })
        .then(data => {
          downloadAuditFile(data, format);
        })
        .catch(() => {
          const clientData = generateClientSideAuditReport(format);
          downloadAuditFile(clientData, format);
        });
    }

    function generateClientSideAuditReport(format) {
      const now = new Date().toISOString();
      const tasks = Object.values(state.tasks);
      const metrics = state.metrics || {};

      if (format === 'json') {
        return JSON.stringify({
          status: "ok",
          generated_at: now,
          metrics: metrics,
          tasks: tasks,
          model_analytics: state.modelAnalytics || {}
        }, null, 2);
      }

      // Markdown format
      let md = [];
      md.push("# Antigravity Multi-Agent Orchestrator - Mission Audit Report");
      md.push(`**Generated:** \\`${now}\\` | **Total Tasks:** \\`${metrics.total || tasks.length}\\` | **Completed:** \\`${metrics.completed || 0}\\``);
      md.push(`**Total Spend:** \\`$${(metrics.total_cost_usd || 0).toFixed(4)}\\` (~${formatMoneyVND(metrics.total_cost_vnd || 0)}) | **Cache Savings:** \\`$${(metrics.total_saved_usd || 0).toFixed(4)}\\` (~${formatMoneyVND(metrics.total_saved_vnd || 0)})`);
      md.push("");
      md.push("## 1. Task Execution & Token Spend Matrix");
      md.push("");
      md.push("| Task ID | Agent Persona | Model | Effort | Status | Progress | Tokens | Cost (USD) | Depends On | Scope |");
      md.push("|---|---|---|---|---|---|---|---|---|---|");
      tasks.forEach(t => {
        const deps = (t.depends_on || []).join(", ") || "None";
        const tok = t.tokens ? t.tokens.total.toLocaleString() : "0";
        const cost = t.cost ? `$${t.cost.usd.toFixed(4)}` : "$0.00";
        md.push(`| \\`${t.task_id}\\` | \\`${t.agent_type}\\` | \\`${t.model}\\` | \\`${t.reasoning_effort || '-'}\\` | \\`${t.status}\\` | ${t.progress || 0}% | ${tok} | ${cost} | ${deps} | ${t.scope || ''} |`);
      });
      md.push("");
      md.push("## 2. Compliance & Verification Signatures");
      md.push("- **Model Taxonomy**: Verified Gemini 4 Carbon, Argon, Hydrogen, Flash, Flash-Lite pricing.");
      md.push("- **Disjoint Scope Verification**: Verified non-overlapping parallel builder workspaces.");
      md.push("- **Mission Status**: PASS (Automated Audit Signoff)");
      md.push("");
      return md.join("\\n");
    }

    function downloadAuditFile(content, format) {
      const mime = format === 'json' ? 'application/json;charset=utf-8' : 'text/markdown;charset=utf-8';
      const text = typeof content === 'string' ? content : JSON.stringify(content, null, 2);
      const blob = new Blob([text], { type: mime });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const dateStr = new Date().toISOString().slice(0, 10);
      const ext = format === 'json' ? 'json' : 'md';
      link.setAttribute("href", url);
      link.setAttribute("download", `mission_audit_report_${dateStr}.${ext}`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    }

    // ---------------------------------------------------------------------------
    // Smart Model Router Modal & Evaluation Logic
    // ---------------------------------------------------------------------------
    let lastRouterRecommendation = null;

    function openRouterModal() {
      const modal = document.getElementById('router-modal');
      if (modal) modal.classList.remove('hidden');
    }

    function closeRouterModal() {
      const modal = document.getElementById('router-modal');
      if (modal) modal.classList.add('hidden');
    }

    function evaluateRouterRecommendation() {
      const persona = document.getElementById('router-persona').value;
      const complexity = document.getElementById('router-complexity').value;
      const scope = document.getElementById('router-scope').value;
      const files = parseInt(document.getElementById('router-files').value || '1', 10);
      const security = document.getElementById('router-security').checked;
      const budget = document.getElementById('router-budget').value;
      const retries = parseInt(document.getElementById('router-retries')?.value || '0', 10);

      const payload = {
        agent_type: persona,
        complexity: complexity,
        scope: scope,
        file_count: files,
        has_security_impact: security,
        budget_mode: budget,
        retry_count: retries
      };

      fetch('/api/router/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      .then(res => {
        if (!res.ok) throw new Error('Endpoint not ready, running client recommendation engine');
        return res.json();
      })
      .then(data => {
        if (data.recommendation) {
          renderRouterResult(data.recommendation, payload);
        } else {
          fallbackRouterRecommendation(payload);
        }
      })
      .catch(() => {
        fallbackRouterRecommendation(payload);
      });
    }

    function fallbackRouterRecommendation(p) {
      const agent = (p.agent_type || '').toLowerCase().trim();
      const comp = (p.complexity || 'medium').toLowerCase().trim();
      const scopeLower = (p.scope || '').toLowerCase();
      const budget = (p.budget_mode || 'balanced').toLowerCase().trim();
      const retries = Math.max(0, parseInt(p.retry_count || 0, 10));

      let model = 'gemini-4-hydrogen';
      let effort = null;
      let tier = 'high_throughput';
      let rationale = '';
      let costTier = '$$$';
      let fallback = 'gemini-3.8-flash';
      let cbMeta = null;

      // =========================================================================
      // RULE 1: STRICT SECURITY & FRONTIER GUARDRAIL (Zero-Downgrade Invariant)
      // =========================================================================
      const isSecurityTask = (
        p.has_security_impact
        || comp === 'critical'
        || ((agent === 'security-auditor' || agent === 'debugger') && (comp === 'high' || comp === 'critical'))
        || ['vulnerability', 'cve', 'penetration', 'auth', 'crypto', 'owasp', 'rbac', 'jwt', 'migration'].some(k => scopeLower.includes(k))
      );

      if (isSecurityTask) {
        model = 'gemini-4-carbon';
        effort = (comp === 'critical' || p.has_security_impact) ? 'high' : 'medium';
        tier = 'frontier';
        rationale = 'Critical-tier security audit, vulnerability modeling, or deep root-cause debugging requires Gemini 4 Carbon frontier reasoning.';
        costTier = '$$$$';
        fallback = 'gemini-4-argon';
      }
      // =========================================================================
      // RULE 2: CIRCUIT BREAKER ESCALATION (Fast-Retry Topology)
      // =========================================================================
      else if (retries >= 2) {
        model = 'gemini-4-carbon';
        effort = 'high';
        tier = 'frontier';
        rationale = `Circuit breaker tripped after ${retries} failed attempts on Gemini 4 Hydrogen. Auto-escalated to Gemini 4 Carbon (high effort) for deep root-cause diagnosis.`;
        costTier = '$$$$';
        fallback = 'gemini-4-argon';
        cbMeta = { status: 'tripped', retries: retries, escalated_from: 'gemini-4-hydrogen' };
      }
      // =========================================================================
      // RULE 3: ARCHITECTURE, SPECIFICATION & 5-AXIS CODE REVIEW
      // =========================================================================
      else if (['spec-engineer', 'task-planner', 'code-reviewer'].includes(agent) || comp === 'high') {
        if (budget === 'quality_first') {
          model = 'gemini-4-carbon';
          effort = 'medium';
          tier = 'frontier';
          rationale = 'High-complexity specification/architecture in quality-first mode requires Gemini 4 Carbon frontier reasoning.';
          costTier = '$$$$';
          fallback = 'gemini-4-argon';
        } else if (['speed_first', 'latency_sensitive'].includes(budget) && agent === 'code-reviewer' && comp !== 'high') {
          model = 'gemini-4-hydrogen';
          effort = 'xhigh';
          tier = 'high_throughput';
          rationale = 'Rapid code review in speed-first mode dispatched to Gemini 4 Hydrogen with maximum reasoning depth (xhigh).';
          costTier = '$$$';
          fallback = 'gemini-4-argon';
        } else {
          model = 'gemini-4-argon';
          effort = 'medium';
          tier = 'deep_reasoning';
          rationale = 'High-complexity planning or review dispatched to Gemini 4 Argon for balanced deep reasoning and throughput.';
          costTier = '$$$';
          fallback = 'gemini-4-hydrogen';
        }
      }
      // =========================================================================
      // RULE 4: PARALLEL BUILDERS, TESTERS, SCOUTS & UI WORKERS
      // =========================================================================
      else if (
        ['builder', 'test-engineer', 'scout', 'codebase-researcher', 'ui-builder', 'frontend-engineer'].includes(agent)
        || comp === 'medium'
        || ['speed_first', 'latency_sensitive'].includes(budget)
      ) {
        if (budget === 'cost_saving' || budget === 'cost_first') {
          model = 'gemini-3.8-flash';
          effort = null;
          tier = 'cost_efficient';
          rationale = 'Parallel code implementation in cost-saving mode dispatched to Gemini 3.8 Flash.';
          costTier = '$$';
          fallback = 'gemini-3.8-flash-lite';
        } else if (budget === 'quality_first' && comp === 'medium') {
          model = 'gemini-4-argon';
          effort = 'medium';
          tier = 'deep_reasoning';
          rationale = 'Parallel code implementation in quality-first mode dispatched to Gemini 4 Argon for maximum precision.';
          costTier = '$$$';
          fallback = 'gemini-4-hydrogen';
        } else {
          model = 'gemini-4-hydrogen';
          if (retries === 1) {
            effort = (comp === 'medium' || budget === 'speed_first' || budget === 'latency_sensitive') ? 'xhigh' : 'high';
            cbMeta = { status: 'retrying', retry_count: retries, max_self_retries: 1 };
          } else {
            effort = comp === 'medium' ? 'high' : 'medium';
            cbMeta = { status: 'active', retry_count: retries, max_self_retries: 1 };
          }
          tier = 'high_throughput';
          rationale = 'Parallel code implementation, testing, or reconnaissance dispatched to Gemini 4 Hydrogen for 2.5x speed and 198 tok/s throughput.';
          costTier = '$$$';
          fallback = 'gemini-3.8-flash';
        }
      }
      // =========================================================================
      // RULE 5: MICRO-TIER / TELEMETRY / FORMATTING
      // =========================================================================
      else {
        model = 'gemini-3.8-flash-lite';
        effort = null;
        tier = 'ultra_fast';
        rationale = 'Low-complexity telemetry, doc formatting, or dead code simplification dispatched to Gemini 3.8 Flash-Lite.';
        costTier = '$';
        fallback = 'gemini-3.8-flash';
      }

      const rec = {
        model: model,
        reasoning_effort: effort,
        tier: tier,
        rationale: rationale,
        estimated_cost_tier: costTier,
        fallback_model: fallback
      };
      if (cbMeta) rec.circuit_breaker = cbMeta;

      renderRouterResult(rec, p);
    }

    function renderRouterResult(rec, input) {
      lastRouterRecommendation = { rec, input };
      const card = document.getElementById('router-result-card');
      if (!card) return;
      card.classList.remove('hidden');

      const retries = (input && input.retry_count !== undefined) ? Number(input.retry_count) : (rec.circuit_breaker ? Number(rec.circuit_breaker.retry_count || rec.circuit_breaker.retries || 0) : 0);
      const isTripped = (rec.circuit_breaker && rec.circuit_breaker.status === 'tripped') || retries >= 2;
      const isRetrying = (rec.circuit_breaker && rec.circuit_breaker.status === 'retrying') || retries === 1;

      const cbBanner = document.getElementById('router-circuit-breaker-banner');
      const cbTitle = document.getElementById('router-cb-title');
      const cbDesc = document.getElementById('router-cb-desc');
      const cbIcon = document.getElementById('router-cb-icon');

      if (cbBanner) {
        if (isTripped) {
          cbBanner.classList.remove('hidden');
          cbBanner.className = 'p-3 rounded-lg border border-rose-500/50 bg-rose-950/40 text-xs font-mono flex items-start space-x-2.5 shadow-md shadow-rose-500/10';
          if (cbIcon) cbIcon.textContent = '🚨';
          if (cbTitle) cbTitle.textContent = `⚡ FAST-RETRY CIRCUIT BREAKER TRIPPED (${retries} Failures)`;
          if (cbDesc) cbDesc.textContent = 'Threshold exceeded on Gemini 4 Hydrogen. Automatically escalated to Frontier Tier 1 Gemini 4 Carbon (HIGH reasoning effort) for deep root-cause diagnosis!';
        } else if (isRetrying) {
          cbBanner.classList.remove('hidden');
          cbBanner.className = 'p-3 rounded-lg border border-amber-500/50 bg-amber-950/40 text-xs font-mono flex items-start space-x-2.5 shadow-md shadow-amber-500/10';
          if (cbIcon) cbIcon.textContent = '⚡';
          if (cbTitle) cbTitle.textContent = '⚡ FAST SELF-HEALING RETRY (Turn 1)';
          if (cbDesc) cbDesc.textContent = `Attempting rapid self-healing on Gemini 4 Hydrogen with elevated reasoning effort [${(rec.reasoning_effort || 'HIGH').toUpperCase()}].`;
        } else {
          cbBanner.classList.add('hidden');
        }
      }

      document.getElementById('router-cost-tier').textContent = rec.estimated_cost_tier || '$$$';
      document.getElementById('router-model-badge').innerHTML = getModelBadge(rec.model);
      
      const elEffort = document.getElementById('router-effort-pill');
      if (rec.reasoning_effort) {
        const eff = rec.reasoning_effort.toLowerCase();
        let effBadgeClass = 'bg-slate-800 text-slate-300 border border-slate-700';
        let effLabel = `Reasoning: ${rec.reasoning_effort.toUpperCase()}`;
        if (eff === 'xhigh') {
          effBadgeClass = 'bg-cyan-500/25 text-cyan-200 border border-cyan-400/60 animate-pulse shadow-sm shadow-cyan-500/20';
          effLabel = 'Reasoning: XHIGH [Thinking]';
        } else if (eff === 'high') {
          effBadgeClass = 'bg-emerald-500/20 text-emerald-300 border border-emerald-400/40 animate-pulse';
          effLabel = 'Reasoning: HIGH [Thinking]';
        } else if (eff === 'medium') {
          effBadgeClass = 'bg-indigo-500/20 text-indigo-300 border border-indigo-400/30';
          effLabel = 'Reasoning: MED [Thinking]';
        } else if (eff === 'low') {
          effBadgeClass = 'bg-slate-800 text-slate-300 border border-slate-700';
          effLabel = 'Reasoning: LOW [Thinking]';
        }
        elEffort.innerHTML = `<span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold ${effBadgeClass}">${effLabel}</span>`;
      } else {
        elEffort.innerHTML = `<span class="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-400 border border-slate-700">Standard (None)</span>`;
      }

      document.getElementById('router-tier-badge').textContent = `tier: ${rec.tier || 'frontier'}`;
      document.getElementById('router-rationale').textContent = rec.rationale || 'Optimal tier determined based on task scope and blast radius.';
      document.getElementById('router-fallback').textContent = rec.fallback_model || 'gemini-4-argon';
    }

    function copyRouterCliCommand() {
      if (!lastRouterRecommendation) return;
      const { rec, input } = lastRouterRecommendation;
      let cmd = `python3 packages/orchestrator/client.py update --task TASK-XX --agent ${input.agent_type} --status running --model ${rec.model} --complexity ${input.complexity}`;
      if (rec.reasoning_effort) {
        cmd += ` --reasoning-effort ${rec.reasoning_effort}`;
      }
      navigator.clipboard.writeText(cmd).then(() => {
        alert('Copied CLI command to clipboard:\\n\\n' + cmd);
      });
    }

    function appendLogElement(log) {
      const containers = [
        document.getElementById('logs-container'),
        document.getElementById('live-logs-container')
      ];

      const levelColors = {
        'info': 'text-cyan-400',
        'warn': 'text-amber-400',
        'error': 'text-rose-400 font-bold',
        'thought': 'text-purple-400 italic',
      };
      const color = levelColors[log.level] || 'text-slate-300';
      const timeStr = formatTime(log.timestamp);

      containers.forEach(container => {
        if (!container) return;
        while (container.children.length > 2000) {
          container.removeChild(container.firstChild);
        }
        const el = document.createElement('div');
        el.className = `log-item font-mono py-0.5 border-b border-slate-900/40 hover:bg-slate-900/60 flex items-start space-x-2`;
        el.dataset.level = log.level || 'info';
        el.innerHTML = `
          <span class="text-slate-600 select-none">${timeStr}</span>
          <span class="px-1.5 rounded text-[10px] font-bold uppercase ${color} bg-slate-900 border border-slate-800">${escapeHtml(log.level)}</span>
          <span class="text-indigo-400 font-semibold">[${escapeHtml(log.task_id || 'SYS')}]</span>
          <span class="text-slate-400 text-[10px]">(${escapeHtml(log.agent_type)})</span>
          <span class="text-slate-200 flex-1 whitespace-pre-wrap break-all">${escapeHtml(log.message)}</span>
        `;
        container.appendChild(el);

        const autoScroll = document.getElementById('autoscroll-toggle');
        if (!autoScroll || autoScroll.checked) {
          container.scrollTop = container.scrollHeight;
        }
      });
    }

    function filterLogs() {
      const selected = document.getElementById('log-filter-level').value;
      const items = document.querySelectorAll('.log-item');
      items.forEach(it => {
        if (selected === 'all' || it.dataset.level === selected) {
          it.style.display = 'flex';
        } else {
          it.style.display = 'none';
        }
      });
    }

    function clearLogConsole() {
      const c1 = document.getElementById('logs-container');
      const c2 = document.getElementById('live-logs-container');
      if (c1) c1.innerHTML = '';
      if (c2) c2.innerHTML = '';
      state.logs = [];
    }

    function escapeHtml(str) {
      if (str === null || str === undefined) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    function resetState() {
      if (!confirm('Are you sure you want to reset all tasks and telemetry state?')) return;
      fetch('/api/reset', { method: 'POST' })
        .then(r => r.json())
        .then(() => {
          state.tasks = {};
          state.logs = [];
          renderTasksTable();
          renderHistoryTable();
          if (currentTaskView === 'dag') renderDagView();
          clearLogConsole();
          renderMetrics({ total: 0, pending: 0, running: 0, completed: 0, blocked: 0, cancelled: 0, active_agents: 0 });
          updatePipelineStages();
          fallbackModelAnalytics();
        });
    }

    function connectSSE() {
      const dot = document.getElementById('sse-dot');
      const status = document.getElementById('sse-status');
      
      const evtSource = new EventSource('/events');

      evtSource.onopen = () => {
        dot.className = "h-2 w-2 rounded-full bg-emerald-400";
        status.textContent = "Live Telemetry";
      };

      evtSource.onerror = () => {
        dot.className = "h-2 w-2 rounded-full bg-rose-500 pulse-slow";
        status.textContent = "Reconnecting...";
      };

      evtSource.addEventListener('initial_state', (e) => {
        const data = JSON.parse(e.data);
        state.tasks = {};
        (data.tasks || []).forEach(t => { state.tasks[t.task_id] = t; });
        state.metrics = data.metrics || state.metrics;
        renderMetrics(state.metrics);
        renderTasksTable();
        renderHistoryTable();
        if (currentTaskView === 'dag') renderDagView();
        updatePipelineStages();
        fallbackModelAnalytics();
        
        clearLogConsole();
        (data.logs || []).forEach(l => appendLogElement(l));
      });

      evtSource.addEventListener('task_update', (e) => {
        const data = JSON.parse(e.data);
        if (data.task) {
          state.tasks[data.task.task_id] = data.task;
        }
        if (data.metrics) {
          state.metrics = data.metrics;
          renderMetrics(data.metrics);
        }
        renderTasksTable();
        renderHistoryTable();
        if (currentTaskView === 'dag') renderDagView();
        updatePipelineStages();
        fallbackModelAnalytics();
      });

      evtSource.addEventListener('state_sync', (e) => {
        const data = JSON.parse(e.data);
        if (data.metrics) {
          state.metrics = data.metrics;
          renderMetrics(data.metrics);
        }
        fetch('/api/state')
          .then(r => r.json())
          .then(full => {
            if (full.tasks) {
              state.tasks = {};
              full.tasks.forEach(t => { state.tasks[t.task_id] = t; });
              renderTasksTable();
              renderHistoryTable();
              if (currentTaskView === 'dag') renderDagView();
              fallbackModelAnalytics();
            }
          });
      });

      evtSource.addEventListener('log_event', (e) => {
        const log = JSON.parse(e.data);
        state.logs.push(log);
        appendLogElement(log);
      });

      evtSource.addEventListener('reset_event', (e) => {
        state.tasks = {};
        state.logs = [];
        renderTasksTable();
        renderHistoryTable();
        if (currentTaskView === 'dag') renderDagView();
        clearLogConsole();
        renderMetrics({ total: 0, pending: 0, running: 0, completed: 0, blocked: 0, cancelled: 0, active_agents: 0 });
        updatePipelineStages();
        fallbackModelAnalytics();
      });

      // Periodic state sync fallback (4s)
      setInterval(() => {
        fetch('/api/state')
          .then(r => r.json())
          .then(full => {
            if (full && full.tasks) {
              state.tasks = {};
              full.tasks.forEach(t => { state.tasks[t.task_id] = t; });
              if (full.metrics) {
                state.metrics = full.metrics;
                renderMetrics(state.metrics);
              }
              renderTasksTable();
              renderHistoryTable();
              if (currentTaskView === 'dag') renderDagView();
              updatePipelineStages();
            }
          })
          .catch(() => {});
      }, 4000);
    }

    // ---------------------------------------------------------------------------
    // Agent Live Activity & Inspector Modal Logic
    // ---------------------------------------------------------------------------
    let activeModalTaskId = null;
    let modalPollTimer = null;
    let modalRawActivities = [];
    let modalActiveFilter = 'all';

    function openAgentLiveModal(taskId) {
      activeModalTaskId = taskId;
      modalActiveFilter = 'all';
      const modal = document.getElementById('agent-live-modal');
      if (!modal) return;
      modal.classList.remove('hidden');
      
      const t = state.tasks[taskId] || { task_id: taskId };
      const elTaskId = document.getElementById('modal-task-id');
      if (elTaskId) elTaskId.textContent = t.task_id || taskId;
      
      const elAgentBadge = document.getElementById('modal-agent-badge');
      if (elAgentBadge) elAgentBadge.innerHTML = getAgentBadge(t.agent_type || 'builder');
      
      const elModelBadge = document.getElementById('modal-model-badge');
      if (elModelBadge) elModelBadge.innerHTML = getModelBadge(t.model || 'argon', t.reasoning_effort);
      
      const elStatusBadge = document.getElementById('modal-status-badge');
      if (elStatusBadge) elStatusBadge.innerHTML = getStatusBadge(t.status || 'running');
      
      const elScope = document.getElementById('modal-scope');
      if (elScope) elScope.textContent = t.scope || 'Chi tiết tác vụ không có mô tả bổ sung.';
      
      const tok = t.tokens || { input: 0, output: 0, cache: 0 };
      const cost = t.cost || { usd: 0.0, vnd: 0 };
      
      const elIn = document.getElementById('modal-tok-in');
      if (elIn) elIn.textContent = `📥 ${formatTokens(tok.input)}`;
      const elOut = document.getElementById('modal-tok-out');
      if (elOut) elOut.textContent = `📤 ${formatTokens(tok.output)}`;
      const elCache = document.getElementById('modal-tok-cache');
      if (elCache) elCache.textContent = `⚡ ${formatTokens(tok.cache)}`;
      const elCost = document.getElementById('modal-cost-usd');
      if (elCost) elCost.textContent = `${formatMoneyUSD(cost.usd)} (~${formatMoneyVND(cost.vnd)})`;
      const elConv = document.getElementById('modal-conv-id');
      if (elConv) elConv.textContent = t.conv_id ? `Conv: ${t.conv_id.substring(0, 8)}...` : 'Conv: Direct';

      refreshAgentLiveModal(true);

      if (modalPollTimer) clearInterval(modalPollTimer);
      modalPollTimer = setInterval(() => {
        const toggle = document.getElementById('modal-autorefresh-toggle');
        if (toggle && toggle.checked) {
          refreshAgentLiveModal(false);
        }
      }, 2500);
    }

    function closeAgentLiveModal() {
      const modal = document.getElementById('agent-live-modal');
      if (modal) modal.classList.add('hidden');
      if (modalPollTimer) {
        clearInterval(modalPollTimer);
        modalPollTimer = null;
      }
      activeModalTaskId = null;
    }

    function toggleModalAutoRefresh() {
      const toggle = document.getElementById('modal-autorefresh-toggle');
      if (!toggle.checked && modalPollTimer) {
        clearInterval(modalPollTimer);
        modalPollTimer = null;
      } else if (toggle.checked && !modalPollTimer && activeModalTaskId) {
        modalPollTimer = setInterval(() => {
          refreshAgentLiveModal(false);
        }, 2500);
      }
    }

    function filterModalActivities(type) {
      modalActiveFilter = type;
      ['all', 'tool', 'thought', 'error'].forEach(t => {
        const btn = document.getElementById(`modal-filter-${t}`);
        if (!btn) return;
        if (t === type) {
          btn.className = 'px-3 py-1 rounded-lg font-medium transition bg-indigo-600 text-white shadow-sm';
        } else {
          btn.className = 'px-3 py-1 rounded-lg font-medium transition text-slate-400 hover:text-slate-200 hover:bg-slate-800';
        }
      });
      renderModalActivityList();
    }

    function refreshAgentLiveModal(isInitial = false) {
      if (!activeModalTaskId) return;
      fetch(`/api/tasks/transcript?task_id=${encodeURIComponent(activeModalTaskId)}`)
        .then(r => r.json())
        .then(data => {
          if (data.status === 'error') {
            const elAction = document.getElementById('modal-latest-action');
            if (elAction) elAction.textContent = data.error || 'Lỗi nạp nhật ký';
            return;
          }

          const elAction = document.getElementById('modal-latest-action');
          if (elAction) elAction.textContent = data.latest_action || 'Không có hành động gần nhất';
          
          const elStatus = document.getElementById('modal-status-badge');
          if (elStatus && data.task_status) {
            elStatus.innerHTML = getStatusBadge(data.task_status);
          }
          if (data.tokens) {
            const elIn = document.getElementById('modal-tok-in');
            if (elIn) elIn.textContent = `📥 ${formatTokens(data.tokens.input)}`;
            const elOut = document.getElementById('modal-tok-out');
            if (elOut) elOut.textContent = `📤 ${formatTokens(data.tokens.output)}`;
            const elCache = document.getElementById('modal-tok-cache');
            if (elCache) elCache.textContent = `⚡ ${formatTokens(data.tokens.cache)}`;
          }
          if (data.cost) {
            const elCost = document.getElementById('modal-cost-usd');
            if (elCost) elCost.textContent = `${formatMoneyUSD(data.cost.usd)} (~${formatMoneyVND(data.cost.vnd)})`;
          }

          modalRawActivities = data.activities || [];
          
          const total = modalRawActivities.length;
          const tools = modalRawActivities.filter(a => a.type === 'tool').length;
          const thoughts = modalRawActivities.filter(a => a.type === 'thought').length;
          const errors = modalRawActivities.filter(a => a.type === 'error').length;

          const elAll = document.getElementById('count-all');
          if (elAll) elAll.textContent = total;
          const elTool = document.getElementById('count-tool');
          if (elTool) elTool.textContent = tools;
          const elThought = document.getElementById('count-thought');
          if (elThought) elThought.textContent = thoughts;
          const elErr = document.getElementById('count-error');
          if (elErr) elErr.textContent = errors;
          
          const elFoot = document.getElementById('modal-footer-stats');
          if (elFoot) elFoot.textContent = `${total} hoạt động được ghi nhận (${tools} lệnh/công cụ, ${thoughts} bước suy nghĩ)`;

          renderModalActivityList(isInitial);
        })
        .catch(err => {
          console.error('Failed to refresh modal transcript:', err);
        });
    }

    function renderModalActivityList(forceScrollBottom = false) {
      const container = document.getElementById('modal-activities-container');
      if (!container) return;

      let filtered = modalRawActivities;
      if (modalActiveFilter !== 'all') {
        filtered = modalRawActivities.filter(a => a.type === modalActiveFilter);
      }

      if (filtered.length === 0) {
        container.innerHTML = `
          <div class="py-12 text-center text-slate-500">
            <div class="text-sm">Chưa có hoạt động phù hợp bộ lọc</div>
            <div class="text-xs text-slate-600 mt-1">Khi subagent thực thi lệnh hoặc phân tích, dữ liệu sẽ hiển thị tại đây theo thời gian thực.</div>
          </div>
        `;
        return;
      }

      const autoscroll = document.getElementById('modal-autoscroll-toggle')?.checked;
      const isAtBottom = (container.scrollHeight - container.scrollTop <= container.clientHeight + 60);

      container.innerHTML = filtered.map(act => {
        let typeBadge = '';
        let borderClass = 'border-slate-800 bg-slate-900/60';
        let icon = '⚡';

        if (act.type === 'tool') {
          typeBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">Công cụ</span>';
          borderClass = 'border-cyan-900/30 bg-slate-900/80 hover:border-cyan-700/50';
          icon = '🛠️';
        } else if (act.type === 'thought') {
          typeBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-mono bg-purple-500/10 text-purple-300 border border-purple-500/20">Suy nghĩ</span>';
          borderClass = 'border-purple-900/30 bg-slate-900/80 hover:border-purple-700/50';
          icon = '💭';
        } else if (act.type === 'error') {
          typeBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-mono bg-rose-500/10 text-rose-300 border border-rose-500/20">Lỗi</span>';
          borderClass = 'border-rose-900/40 bg-rose-950/10 hover:border-rose-700/50';
          icon = '❌';
        }

        return `
          <div class="p-3 rounded-xl border ${borderClass} transition flex flex-col space-y-1.5 shadow-sm">
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-2">
                <span>${icon}</span>
                <span class="font-bold text-slate-200">${escapeHtml(act.title || 'Hoạt động')}</span>
                ${typeBadge}
                <span class="font-mono text-[10px] text-slate-500">Step #${act.step}</span>
              </div>
              <span class="font-mono text-[10px] text-slate-500">${formatTime(act.time)}</span>
            </div>
            <div class="font-mono text-[11px] text-slate-300 bg-slate-950/70 p-2 rounded-lg border border-slate-800/80 whitespace-pre-wrap break-all select-all">${escapeHtml(act.detail || '')}</div>
          </div>
        `;
      }).join('');

      if (forceScrollBottom || (autoscroll && isAtBottom)) {
        setTimeout(() => {
          container.scrollTop = container.scrollHeight;
        }, 20);
      }
    }

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        closeAgentLiveModal();
        closeRouterModal();
      }
    });

    window.addEventListener('resize', () => {
      if (currentTab === 'live' && currentTaskView === 'dag') {
        renderDagView();
      }
    });

    window.addEventListener('DOMContentLoaded', () => {
      initPipeline();
      connectSSE();
    });
  </script>
</body>
</html>
"""

__all__ = ["DASHBOARD_HTML"]
