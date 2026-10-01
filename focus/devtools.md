# Focus lens: devtools (libraries, frameworks and developer tools)

Use this lens when picking, upgrading or replacing a library, framework, SDK or CLI. It checks
the current version's real docs, maintenance signal, adoption trend, bundle and supply-chain cost,
and how other repos actually use it. Model memory about APIs is not a source.

## Triggers

Suggested when the topic mentions a library, framework, SDK, package, npm, PyPI, dependency,
"migrate to", CLI tools, or "which lib/tool/framework". Bundle: `#build-pick`.

## Sub-question lens

1. **Current API:** what does the latest stable version's documentation say about the exact
   feature we need (version number, date)? What changed in the last two majors?
2. **Health:** release cadence, open-issue trend, bus factor, licence, OpenSSF Scorecard and
   adoption trend for each candidate.
3. **Cost of adoption:** bundle size, transitive dependencies, supply-chain risk, and the
   migration path off it if it dies.

## Tool stack

| Tool           | Tier           | Use it for                                                         | Skip when                     |
| -------------- | -------------- | ------------------------------------------------------------------ | ----------------------------- |
| `context7`     | freemium (MCP) | Version-specific docs for the candidate                            | quota exhausted (use deepwiki)|
| `deepwiki`     | free (MCP)     | Questions answered from the repo's own code                        | closed-source tool            |
| `github-code`  | free (MCP)     | Releases, changelog, open issues, last commit                      | not on GitHub                 |
| `grep-app`     | free (MCP)     | Real usage of the API across public repos                          | brand-new API                 |
| `deps-dev`     | free           | Dependency graph, licences, advisories, Scorecard                  | not an open-source package    |
| `npm-stats`    | free           | Download trend over 12 months                                      | not on npm                    |
| `bundlephobia` | free           | Minified and gzipped size                                          | server-only package           |
| `socket`       | freemium (MCP) | Supply-chain risk score                                            | no new dependency             |
| `hn`           | free           | Practitioner reports ("we migrated off X because")                 | never skip for a "which" call |

All free or freemium. Fully usable with `--free` (Context7 falls back to DeepWiki).

## Authorities

The project's own docs, changelog and release notes outrank tutorials. GitHub issues from
maintainers outrank blog posts. npmjs.com, pypi.org and deps.dev are primary for metadata.

## Freshness

- Cache TTL: 7 days for versions and issues, 30 days for comparisons.
- Always state the version researched. "Latest" without a number is not a finding.
- Dated trap: model memory lags releases by months. Read the docs for the exact version you will pin.

## Audit mode

With `--target <repo>`: list direct dependencies, and for each one get the latest version versus
the pinned one, the last release date, the licence and the Scorecard score from `deps-dev`.
Flag anything unmaintained (no release for 12 months or more) or with licence conflicts. Tag
`[AUDIT:deps]`.

## Report addendum

Add a **Library decision matrix** section:

```text
### Library decision matrix
| Candidate (version) | Fit for need          | Last release | Downloads trend | Size (gz) | Risk (Scorecard, advisories) | Source            |
| ------------------- | --------------------- | ------------ | --------------- | --------- | ---------------------------- | ----------------- |
| lib-a 5.2.0         | native streaming      | 2026-09-12   | up 30% / 12 mo  | 14 kB     | 7.8, none open               | [C7 + DEPS + BP]  |
```

## Pathway mapping

- pathway-operating-layer: `research`, `techdebt`, plus the `supply-chain` overlay.
- development-protocol rows: `research`, `planning` (the pick goes into the plan), `premortem`.
