#!/usr/bin/env bash
# ==============================================================================
# Multi-Agent Orchestrator & Antigravity CLI Installer
# One-click automated setup for Linux and macOS
# ==============================================================================
set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}${BOLD}================================================================${NC}"
echo -e "${BLUE}${BOLD}  Multi-Agent Orchestrator & Antigravity CLI Installer          ${NC}"
echo -e "${BLUE}${BOLD}================================================================${NC}"
echo ""

# ------------------------------------------------------------------------------
# 1. Check & Install Antigravity CLI (agy)
# ------------------------------------------------------------------------------
echo -e "${BOLD}[1/5] Checking Antigravity CLI (agy)...${NC}"

ensure_local_bin_in_path() {
    local bin_dir="$HOME/.local/bin"
    if [[ ":$PATH:" != *":$bin_dir:"* ]]; then
        echo -e "${YELLOW}[!] $bin_dir is not in PATH. Adding to current session and shell profile...${NC}"
        export PATH="$bin_dir:$PATH"
        
        # Persist in shell config
        if [[ -n "${ZSH_VERSION:-}" ]] || [[ "$SHELL" == *"zsh"* ]]; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
        elif [[ -f "$HOME/.bashrc" ]]; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
        fi
    fi
}
ensure_local_bin_in_path

if command -v agy >/dev/null 2>&1; then
    AGY_VER=$(agy --version 2>/dev/null || echo "detected")
    echo -e "${GREEN}[✓] Antigravity CLI (agy) is already installed (version: ${AGY_VER})${NC}"
else
    echo -e "${YELLOW}[!] Antigravity CLI (agy) not found in PATH.${NC}"
    echo -e "    Installing via official Google installer: curl -fsSL https://antigravity.google/cli/install.sh | bash"
    if curl -fsSL https://antigravity.google/cli/install.sh | bash; then
        ensure_local_bin_in_path
        if command -v agy >/dev/null 2>&1; then
            echo -e "${GREEN}[✓] Antigravity CLI installed successfully!${NC}"
        else
            echo -e "${YELLOW}[!] Installed to ~/.local/bin/agy. Please ensure ~/.local/bin is in your PATH.${NC}"
        fi
    else
        echo -e "${RED}[X] Failed to auto-download agy. Please refer to docs/ANTIGRAVITY_CLI_SETUP.md${NC}"
    fi
fi

# ------------------------------------------------------------------------------
# 2. Check Python Environment
# ------------------------------------------------------------------------------
echo ""
echo -e "${BOLD}[2/5] Checking Python Environment...${NC}"
if ! command -v python3 >/dev/null 2>&1; then
    echo -e "${RED}[X] Python 3 is required but not installed. Please install python3 (>=3.8).${NC}"
    exit 1
fi
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
echo -e "${GREEN}[✓] Python detected: version ${PY_VER}${NC}"

# Check sqlite3 standard module
python3 -c "import sqlite3, http.server, json, threading" 2>/dev/null || {
    echo -e "${RED}[X] Missing standard Python modules. Ensure python3-sqlite3 is installed.${NC}"
    exit 1
}
echo -e "${GREEN}[✓] Standard library dependencies verified (sqlite3, http.server, json, threading)${NC}"

# ------------------------------------------------------------------------------
# 3. Install Global Antigravity Configurations
# ------------------------------------------------------------------------------
echo ""
echo -e "${BOLD}[3/5] Installing Global Antigravity Skills & Workflows...${NC}"

GLOBAL_CONFIG_DIR="$HOME/.gemini/config"
GLOBAL_COMMANDS_DIR="$HOME/.gemini/commands"
GLOBAL_TOOLS_DIR="$HOME/.gemini/tools/orchestrator"
mkdir -p "$GLOBAL_CONFIG_DIR/workflows" "$GLOBAL_CONFIG_DIR/global_workflows" "$GLOBAL_CONFIG_DIR/skills" "$GLOBAL_COMMANDS_DIR" "$GLOBAL_TOOLS_DIR"

# Copy All Agent Skills (addyosmani 1-Agent = 1-Skill package library)
echo -e "    -> Installing 1-Agent = 1-Skill packages..."
for skill_dir in "$SCRIPT_DIR/packages/skills/"*; do
    if [[ -d "$skill_dir" ]]; then
        sname=$(basename "$skill_dir")
        mkdir -p "$GLOBAL_CONFIG_DIR/skills/$sname"
        cp -r "$skill_dir/"* "$GLOBAL_CONFIG_DIR/skills/$sname/"
    fi
done
SKILL_COUNT=$(find "$SCRIPT_DIR/packages/skills" -mindepth 1 -maxdepth 1 -type d | wc -l)
echo -e "    -> Installed ${SKILL_COUNT} Agent Skills into: $GLOBAL_CONFIG_DIR/skills/"

# Copy Workflows (Slash commands)
for wf in "$SCRIPT_DIR/packages/workflows/"*.md; do
    cp "$wf" "$GLOBAL_CONFIG_DIR/workflows/"
    cp "$wf" "$GLOBAL_CONFIG_DIR/global_workflows/"
done
echo -e "    -> Installed Workflows: $GLOBAL_CONFIG_DIR/workflows/ (*.md)"

# Copy Commands TOML
cp "$SCRIPT_DIR/packages/commands/orchestrator.toml" "$GLOBAL_COMMANDS_DIR/orchestrator.toml"
echo -e "    -> Installed Command: $GLOBAL_COMMANDS_DIR/orchestrator.toml"

# Copy Global Orchestrator Python Modules & Assets
echo -e "    -> Installing Global Orchestrator Modules into: $GLOBAL_TOOLS_DIR..."
cp "$SCRIPT_DIR/packages/orchestrator/"*.py "$GLOBAL_TOOLS_DIR/"
chmod +x "$GLOBAL_TOOLS_DIR/"*.py
if [[ -f "$SCRIPT_DIR/packages/orchestrator/requirements.txt" ]]; then
    cp "$SCRIPT_DIR/packages/orchestrator/requirements.txt" "$GLOBAL_TOOLS_DIR/"
fi
echo -e "    -> Installed Orchestrator Modules: (__init__.py, models.py, router.py, dashboard.py, server.py, client.py)"
echo -e "${GREEN}[✓] Global configurations & tools installed successfully!${NC}"

# ------------------------------------------------------------------------------
# 4. Optional: Install into Current Project Workspace
# ------------------------------------------------------------------------------
echo ""
echo -e "${BOLD}[4/5] Checking Workspace Installation...${NC}"
TARGET_DIR="${1:-.}"

sync_target_workspace() {
    local target_path="$1"
    local dest_dir="$(cd "$target_path" && pwd)"
    echo -e "    Targeting workspace: ${BOLD}${dest_dir}${NC}"
    mkdir -p "$dest_dir/.agents/skills" \
             "$dest_dir/.agents/workflows" \
             "$dest_dir/.gemini/commands" \
             "$dest_dir/tools/orchestrator" \
             "$dest_dir/docs/specs" \
             "$dest_dir/docs/plans" \
             "$dest_dir/docs/reports" \
             "$dest_dir/docs/reviews" \
             "$dest_dir/docs/security"

    for skill_dir in "$SCRIPT_DIR/packages/skills/"*; do
        if [[ -d "$skill_dir" ]]; then
            sname=$(basename "$skill_dir")
            mkdir -p "$dest_dir/.agents/skills/$sname"
            cp -r "$skill_dir/"* "$dest_dir/.agents/skills/$sname/"
        fi
    done
    cp "$SCRIPT_DIR/packages/workflows/"*.md "$dest_dir/.agents/workflows/"
    cp "$SCRIPT_DIR/packages/commands/orchestrator.toml" "$dest_dir/.gemini/commands/"
    cp "$SCRIPT_DIR/packages/orchestrator/"*.py "$dest_dir/tools/orchestrator/"
    chmod +x "$dest_dir/tools/orchestrator/"*.py
    if [[ -f "$SCRIPT_DIR/packages/rules/GEMINI.md" ]]; then
        cp "$SCRIPT_DIR/packages/rules/GEMINI.md" "$dest_dir/GEMINI.md"
        echo -e "    -> Installed GEMINI.md multi-agent workflow rules into workspace root."
    fi
    echo -e "${GREEN}[✓] Workspace synced: ${dest_dir}${NC}"
}

if [[ "$TARGET_DIR" != "." ]] && [[ -d "$TARGET_DIR" ]]; then
    sync_target_workspace "$TARGET_DIR"
elif [[ -d ".git" ]] || [[ -d ".agents" ]]; then
    sync_target_workspace "."
fi

# Auto-sync live active workspace if it exists (e.g. running daemon)
if [[ -d "$HOME/SourceCodes/hospital-suite/tools/orchestrator" ]]; then
    echo -e "    -> Auto-syncing live daemon workspace: $HOME/SourceCodes/hospital-suite..."
    sync_target_workspace "$HOME/SourceCodes/hospital-suite"
fi

# ------------------------------------------------------------------------------
# 5. Run Verification Test Suite
# ------------------------------------------------------------------------------
echo ""
echo -e "${BOLD}[5/5] Running Self-Test Verification Suite...${NC}"
PYTHONPATH="$SCRIPT_DIR/packages:$SCRIPT_DIR/packages/orchestrator:${PYTHONPATH:-}" python3 -m unittest discover -s "$SCRIPT_DIR/tests"

echo ""
echo -e "${GREEN}${BOLD}================================================================${NC}"
echo -e "${GREEN}${BOLD}  INSTALLATION COMPLETED SUCCESSFULLY!                          ${NC}"
echo -e "${GREEN}${BOLD}================================================================${NC}"
echo ""
echo -e "Quick Start Guide:"
echo -e "  1. Start Dashboard Server:"
echo -e "     ${BOLD}python3 packages/orchestrator/server.py --port 8484${NC}"
echo -e "     Dashboard UI:  ${BLUE}http://localhost:8484${NC}"
echo -e "     SSE Stream:    ${BLUE}http://localhost:8484/events${NC}"
echo ""
echo -e "  2. Launch Antigravity with Orchestrator:"
echo -e "     Run ${BOLD}agy${NC} in your terminal, then type:"
echo -e "     ${BOLD}/orchestrator${NC} or ${BOLD}/workflow-pipeline${NC}"
echo ""
echo -e "  3. Telemetry CLI:"
echo -e "     ${BOLD}python3 packages/orchestrator/client.py state${NC}"
echo ""
