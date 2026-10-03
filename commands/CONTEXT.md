# Commands room: the `/research-stack` slash command

One job: keep the command wrapper a true, short front door to `SKILL.md`. Paths relative to the
repo root.

## Inputs

- `commands/research-stack.md`, installed to `~/.claude/commands/research-stack.md`.
- The flags and steps it summarizes: `SKILL.md` (Step 0 flags, Step 0.4 focus) and
  `focus/tags.json` (tags, addenda, bundles).
- Missing input: a flag or tag the command lists that `SKILL.md` does not define is not shipped.

## Process

1. Change `SKILL.md` or `focus/tags.json` first; the command only mirrors them.
2. Update the usage lines, the focus-tag table (tag, tools, report section), the flags list and
   the examples. Every example must use real tags and flags.
3. Keep the `## Execution` block last and unchanged in shape: it hands `$ARGUMENTS` to the
   installed `SKILL.md`.
4. Re-run `./install.sh` into a temp `HOME` and confirm the command file lands.

## Outputs

- Edited `commands/research-stack.md`.

## Human check

The maintainer runs `/research-stack <topic> #<tag>` from the installed command. Pass: the run uses that
lens and every flag in the help text exists in `SKILL.md`. Fail: fix the command or the skill.
