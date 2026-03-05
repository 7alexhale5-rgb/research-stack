# Vault Alternatives (No Obsidian Required)

The Research Stack writes standard markdown with YAML frontmatter. Any tool that reads markdown files works. Pick whichever fits your workflow.

---

## 1. Plain Markdown (Zero Setup)

Create the vault directory and subdirectories:

```bash
mkdir -p ~/research-vault/{research,sources,moc}
```

That's it. The skill writes files directly to these directories:
- `research/` — research notes with analysis and citations
- `sources/` — individual source summaries
- `moc/` — maps of content (index files linking related notes)

All notes use standard markdown with YAML frontmatter (`title`, `date`, `tags`, `sources`). Search with grep or Claude's Grep tool:

```bash
grep -r "transformer architecture" ~/research-vault/
```

You lose graph view and Dataview queries. You keep persistent, linkable, version-controllable notes that any future tool can read.

Best for: minimalists, people who already have a text-file workflow, anyone who wants to start immediately.

---

## 2. Logseq

Local-first, open source knowledge base with graph view and wikilink support.

**Setup:**
1. Install from [logseq.com](https://logseq.com/)
2. Create a new graph or point it at your vault directory
3. Set `VAULT_PATH` in `config/config.md` to your Logseq graph's `pages/` directory

Logseq reads standard markdown natively. The skill's output format (YAML frontmatter + wikilinks) works without modification.

Logseq defaults to outline mode (bullet-based editing). Long-form notes from the Research Stack display fine in document mode — toggle per page with the `...` menu.

Best for: people who prefer outlining, want a graph view, and like open-source tools.

---

## 3. Foam (VS Code Extension)

Wikilinks, backlinks, and graph visualization inside VS Code. No separate app needed.

**Setup:**
1. Install the extension: `ext install foam.foam-vscode`
2. Open your vault directory as a VS Code workspace
3. Set `VAULT_PATH` in `config/config.md` to that workspace directory

Foam reads standard markdown and resolves `[[wikilinks]]` automatically. The graph view runs as a VS Code panel. Backlinks appear in the sidebar.

Foam has no equivalent to Obsidian's Dataview plugin. For structured queries across notes, use grep or Claude's Grep tool.

Best for: developers who already work in VS Code and don't want another app.

---

## Comparison

| Feature | Obsidian | Logseq | Foam | Plain MD |
|---------|----------|--------|------|----------|
| Graph view | Yes | Yes | Yes | No |
| Wikilinks | Yes | Yes | Yes | Manual |
| Dataview queries | Yes (plugin) | Limited | No | No |
| Local-first | Yes | Yes | Yes | Yes |
| Free | Yes | Yes | Yes | Yes |
| Setup time | 5 min | 5 min | 3 min | 0 min |
| Best for | Power users | Outline fans | VS Code devs | Minimalists |

All four options store notes as plain markdown files on disk. You can switch between them at any time without migrating data.
