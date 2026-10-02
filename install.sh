#!/bin/bash
# Install the research-stack skill into ~/.claude. Safe to re-run; never overwrites config/config.md.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="${HOME}/.claude/skills/research-stack"
CMD_DIR="${HOME}/.claude/commands"

echo "Installing Research Stack v3 into $SKILL_DIR ..."

mkdir -p "$SKILL_DIR/references" "$SKILL_DIR/focus" "$SKILL_DIR/scripts" "$SKILL_DIR/config" "$CMD_DIR"

cp "$REPO_DIR/SKILL.md" "$SKILL_DIR/SKILL.md"
cp "$REPO_DIR"/references/*.md "$REPO_DIR/references/tool-registry.json" "$SKILL_DIR/references/"
cp "$REPO_DIR"/focus/*.md "$REPO_DIR/focus/tags.json" "$SKILL_DIR/focus/"
rm -f "$SKILL_DIR/focus/CONTEXT.md" "$SKILL_DIR/references/CONTEXT.md"
cp "$REPO_DIR/scripts/validate_report.py" "$REPO_DIR/scripts/focus_check.py" "$SKILL_DIR/scripts/"
cp "$REPO_DIR/config/config.example.md" "$SKILL_DIR/config/config.example.md"
cp "$REPO_DIR/commands/research-stack.md" "$CMD_DIR/research-stack.md"

# Lint needs docs/ only for the table check, which is not run here.
if command -v python3 >/dev/null 2>&1; then
  python3 "$SKILL_DIR/scripts/focus_check.py" lint --root "$SKILL_DIR"
else
  echo "python3 not found: skipped the focus lint (the skill still runs; validation is manual)."
fi

echo ""
echo "Installed."
echo ""
echo "Quick start:"
echo "  /research-stack your topic here"
echo "  /research-stack your topic --focus seo,security     (or #seo #security)"
echo ""
echo "Optional:"
echo "  cp $SKILL_DIR/config/config.example.md $SKILL_DIR/config/config.md   # cache path, budgets, default focus"
echo "  python3 $SKILL_DIR/scripts/focus_check.py probe seo                  # which keys and CLIs are present"
echo "  NotebookLM + vault: $REPO_DIR/references/setup-notebooklm-obsidian.md"
