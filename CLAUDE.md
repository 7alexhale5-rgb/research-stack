# Research Stack

> Status: active | Type: infra (public Claude Code skill) | Version: 3.0.0

Multi-source research pipeline. It decomposes a topic into sub-questions, searches in tiered
parallel rounds (free tools first, paid APIs and MCPs only when configured), runs focus lenses
(`--focus seo,security` or `#tag`) that each switch on a dedicated tool stack and a required
report section, challenges findings with skeptic passes, and writes a decision-first report where
every claim carries a source tag. Public repo: `github.com/7alexhale5-rgb/research-stack`.

## Where to go

This repo follows ICM (Jake Van Clief's folder method): this file routes, each room's
`CONTEXT.md` holds its contract.

| Task                                                        | Go to         | Read                                           | Skills |
| ----------------------------------------------------------- | ------------- | ---------------------------------------------- | ------ |
| Add or change a focus tag, lens, or registry tool           | `focus/`      | [focus/CONTEXT.md](focus/CONTEXT.md)           | none   |
| Change the skill's invocation or its command surface        | `commands/`   | none                                           | none   |
| Change a default or example config                          | `config/`     | [config/CONTEXT.md](config/CONTEXT.md)         | none   |
| Update architecture, tools-reference docs or a dossier      | `docs/`       | [docs/CONTEXT.md](docs/CONTEXT.md)             | none   |
| Update setup, routing, provider or output references        | `references/` | [references/CONTEXT.md](references/CONTEXT.md) | none   |

Root files stay where their tools expect them: `SKILL.md` (skill manifest), `install.sh`,
`README.md`, `CHANGELOG.md`, `LICENSE`. `scripts/` (validator and focus linter) and `tests/` are
code, not rooms.

## Verify

- `python3 -m unittest discover tests`
- `python3 scripts/focus_check.py lint` and `python3 scripts/focus_check.py docs`
- `python3 scripts/validate_report.py structure tests/fixtures/research-report-good.md` exits 0;
  the `-bad.md` fixture exits 1.

Python 3.9+ standard library only in `scripts/` and `tests/`.

## Downstream mirrors

`focus/tags.json` is canonical. development-protocol bundles a port of this skill
(`skills/research-stack/`, see its `docs/PORTING.md`), pathway-operating-layer mirrors the tag to
pathway map (`RESEARCH_FOCUS_MAP`), and gravity-stack evals the report format. Change them
together.

## Naming

Kebab-case `.md` throughout.
