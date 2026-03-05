#!/bin/bash
set -e

SKILL_DIR="${HOME}/.claude/skills/research-stack"
CMD_DIR="${HOME}/.claude/commands"

echo "Installing Research Stack skill..."

# Create directories
mkdir -p "$SKILL_DIR/references"
mkdir -p "$CMD_DIR"

# Copy skill files
cp SKILL.md "$SKILL_DIR/SKILL.md"
cp references/notebook-routing.md "$SKILL_DIR/references/notebook-routing.md"
cp references/setup-notebooklm-obsidian.md "$SKILL_DIR/references/setup-notebooklm-obsidian.md" 2>/dev/null || true
cp references/setup-alternatives.md "$SKILL_DIR/references/setup-alternatives.md" 2>/dev/null || true

# Copy command wrapper
cp commands/research-stack.md "$CMD_DIR/research-stack.md"

echo ""
echo "Installed successfully."
echo ""
echo "Quick start:"
echo "  1. Open Claude Code"
echo "  2. Run: /research-stack your topic here"
echo ""
echo "Optional: Configure NotebookLM + vault"
echo "  See: references/setup-notebooklm-obsidian.md"
echo "  Copy config/config.example.md to config/config.md and customize"
