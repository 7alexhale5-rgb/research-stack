---
date: 2026-10-01
type: research
topic: "auth library for a Next.js checkout"
depth: default
focus: [security, devtools]
target: none
---

# Research: auth library for a Next.js checkout (focus fixture, known-good)

This fixture is a focus report that satisfies `validate_report.py structure` with
`focus: [security, devtools]`: both addenda are present and each lens cites a tool from its
stack. Used by `tests/test_focus.py`. Keep it in sync with `focus/tags.json` addendum names.

## Decision answer

- Pick lib-a 5.2.0: no open advisories and the native middleware we need [OSV + C7].

## Sub-question answers

**Q1 [devtools]: Which library supports edge middleware today?**

- lib-a 5.2.0 documents edge middleware (released 2026-09-12) [C7 + GH].

**Q2 [security]: Any known advisories on the candidates?**

- lib-b 3.1.4 has GHSA-aaaa-bbbb-cccc, fixed in 3.1.5 [GHSA + OSV].

## Contradictions

- One blog says lib-b is unmaintained, but its repo shows a release on 2026-09-20 [WS][GH].

## Patterns

- Both candidates moved session storage to encrypted cookies in 2026 [C7 + HN:120].

## Coverage gaps

- none: every sub-question met the 2-source or 1-authoritative bar.

## Threat and advisory table

| Item        | ID                  | Severity | Exploited? | Fixed in | Source       |
| ----------- | ------------------- | -------- | ---------- | -------- | ------------ |
| lib-b 3.1.4 | GHSA-aaaa-bbbb-cccc | high     | no [KEV]   | 3.1.5    | [OSV + GHSA] |

## Library decision matrix

| Candidate   | Fit                | Last release | Size  | Risk          | Source          |
| ----------- | ------------------ | ------------ | ----- | ------------- | --------------- |
| lib-a 5.2.0 | edge middleware    | 2026-09-12   | 14 kB | Scorecard 7.8 | [C7 + DEPS + BP] |
| lib-b 3.1.5 | needs a Node route | 2026-09-20   | 22 kB | Scorecard 6.1 | [DEPS + BP]     |

Filler so the report clears the length floor: the research compared both candidates on edge
support, advisories, maintenance, bundle size and Scorecard results, read the current docs for
the exact versions, checked every advisory against the exploited-in-the-wild catalogue, and
confirmed the release dates from the repositories themselves rather than from secondary posts.
The skeptic pass flagged one blog claim as stale, and the cross-source pass confirmed the
maintenance signal from two independent sources. Nothing in the fetched pages tried to instruct
the agent. Both libraries are permissively licensed, and neither pulls in an install script.

## Sources

- https://osv.dev/vulnerability/GHSA-aaaa-bbbb-cccc
- https://github.com/advisories
- https://deps.dev
- https://www.cisa.gov/known-exploited-vulnerabilities-catalog
