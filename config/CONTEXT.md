# Config room: defaults and examples

One job: keep the shipped example config true to what the skill actually reads. Paths relative
to the repo root.

## Inputs

- The skill's actual config-reading step: `SKILL.md` Step 0 ("Config") and
  `references/power-tier.md` (model keys).
- Current example: `config/config.example.md`.
- Missing input: an option the code does not read is not documented here.

## Process

1. When a new config option ships, add it to `config.example.md` with its default and one-line
   purpose.
2. Remove options the code no longer reads.

## Outputs

- Edited `config/config.example.md`.

## Human check

The maintainer diffs `config.example.md` against the option list the code actually reads. Pass: every
documented option is read; every read option is documented. Fail: fix before release.
