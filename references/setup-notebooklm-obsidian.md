# Setup Guide: NotebookLM + Obsidian for Research Stack

## 1. Install notebooklm-py

```bash
pip install notebooklm-py
pip install "notebooklm-py[browser]"
playwright install chromium
```

## 2. Authenticate NotebookLM

```bash
notebooklm login    # Opens browser for Google auth (one-time)
notebooklm list     # Verify authentication works
```

Use a dedicated Google account for automation, not your primary.

## 3. Research Vault

The vault lives at `~/Projects/research-vault/`. It was created by the research-stack skill with this structure:

```
research-vault/
├── CLAUDE.md          # Vault conventions
├── _Dashboard.md      # Dataview-powered dashboard
├── research/          # Research findings
├── sources/           # Individual source notes
├── synthesis/         # Cross-referenced analysis
├── moc/               # Maps of Content
│   └── MOC - Index.md
└── assets/            # Generated media (audio, slides, etc.)
```

## 4. Register Vault in Obsidian

1. Open Obsidian
2. "Open another vault" → "Open folder as vault"
3. Select `~/Projects/research-vault/`
4. Install recommended plugins: Dataview, Templater

## 5. Verification Checklist

- [ ] `notebooklm list` returns notebooks (or empty list)
- [ ] `~/Projects/research-vault/CLAUDE.md` exists
- [ ] Obsidian can open the vault and render `_Dashboard.md`
- [ ] Dataview plugin installed (for dashboard queries)

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `notebooklm: command not found` | `pip install notebooklm-py` |
| Auth expired | `notebooklm login` |
| Playwright missing | `pip install "notebooklm-py[browser]" && playwright install chromium` |
| Dataview not rendering | Install Dataview plugin in Obsidian settings |
