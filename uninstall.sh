#!/usr/bin/env bash
# ==============================================================================
# Multi-Agent Orchestrator & Antigravity Global Uninstaller
# Cleans up global ~/.gemini installations
# ==============================================================================
set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}${BOLD}================================================================${NC}"
echo -e "${YELLOW}${BOLD}  Multi-Agent Orchestrator Uninstaller                          ${NC}"
echo -e "${YELLOW}${BOLD}================================================================${NC}"
echo ""

GLOBAL_CONFIG_DIR="$HOME/.gemini/config"
GLOBAL_COMMANDS_DIR="$HOME/.gemini/commands"
GLOBAL_TOOLS_DIR="$HOME/.gemini/tools/orchestrator"

# 1. Remove Orchestrator Command
if [[ -f "$GLOBAL_COMMANDS_DIR/orchestrator.toml" ]]; then
    rm -f "$GLOBAL_COMMANDS_DIR/orchestrator.toml"
    echo -e "${GREEN}[✓] Removed $GLOBAL_COMMANDS_DIR/orchestrator.toml${NC}"
fi

# 2. Remove Global Tools
if [[ -d "$GLOBAL_TOOLS_DIR" ]]; then
    rm -rf "$GLOBAL_TOOLS_DIR"
    echo -e "${GREEN}[✓] Removed $GLOBAL_TOOLS_DIR${NC}"
fi

# 3. Remove Orchestrator Workflows
for wf in orchestrator.md workflow-build.md workflow-pipeline.md workflow-plan.md workflow-review.md workflow-security.md workflow-spec.md workflow-test.md; do
    rm -f "$GLOBAL_CONFIG_DIR/workflows/$wf" 2>/dev/null || true
    rm -f "$GLOBAL_CONFIG_DIR/global_workflows/$wf" 2>/dev/null || true
done
echo -e "${GREEN}[✓] Cleaned up global workflows from $GLOBAL_CONFIG_DIR/workflows/${NC}"

# 4. Remove multi-agent-orchestrator skill
if [[ -d "$GLOBAL_CONFIG_DIR/skills/multi-agent-orchestrator" ]]; then
    rm -rf "$GLOBAL_CONFIG_DIR/skills/multi-agent-orchestrator"
    echo -e "${GREEN}[✓] Removed $GLOBAL_CONFIG_DIR/skills/multi-agent-orchestrator${NC}"
fi

echo ""
echo -e "${GREEN}${BOLD}Uninstallation complete!${NC}"
