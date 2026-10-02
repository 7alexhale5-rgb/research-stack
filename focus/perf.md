# Focus lens: perf (performance)

Use this lens when speed is a requirement or a complaint. It separates field data (what users
actually experience) from lab data (one synthetic run), and turns findings into a budget a build
can be checked against.

## Triggers

Suggested when the topic mentions performance, perf, latency, Core Web Vitals, CWV, LCP, INP, CLS,
bundle size, page speed, Lighthouse or throughput. Bundles: `#launch`, `#ship-audit`.

## Sub-question lens

1. **Baseline:** what are the current field numbers at p75 (LCP, INP, CLS, TTFB) for the target or
   comparable sites, with the date?
2. **Causes:** what dominates the critical path (render-blocking resources, images, third-party
   scripts, JS bundle cost, server time)?
3. **Budget and levers:** what budget should the build hold to, and which changes move the numbers
   most per hour of work (with measured before and after numbers from sources)?

## Tool stack

| Tool              | Tier       | Use it for                                                 | Skip when                         |
| ----------------- | ---------- | ---------------------------------------------------------- | --------------------------------- |
| `crux`            | free       | Field Core Web Vitals by origin and URL                    | low traffic (no field data)       |
| `pagespeed`       | free       | Lab Lighthouse run plus CrUX in one call                   | no target                         |
| `lighthouse`      | free (CLI) | Repeatable local lab runs and budgets                      | no local build                    |
| `chrome-devtools` | free (MCP) | Traces, long tasks, network waterfall                      | no target                         |
| `bundlephobia`    | free       | Cost of each candidate npm dependency                      | not a JS project                  |
| `httparchive`     | free       | Population baselines (median page weight, CWV pass rates)  | you already have field data       |

All free. Data, not opinions.

## Authorities

web.dev, developer.chrome.com, MDN and HTTP Archive outrank performance blogs. A vendor's benchmark
of its own product counts as one source.

## Freshness

- Cache TTL: 7 days for field data (CrUX updates on a rolling 28-day window), 90 days for guidance.
- Dated trap: INP replaced FID as a Core Web Vital in 2024-03. Any source still citing FID is
  out of date.

## Audit mode

With `--target <url>`: `crux` (origin and URL), `pagespeed` mobile and desktop, and a
`chrome-devtools` trace of the main template. List the top 5 opportunities with their measured
savings. With a repo target, run `bundlephobia` on the heaviest dependencies. Tag `[AUDIT:psi]`
and `[AUDIT:cdt]`.

## Report addendum

Add a **Performance budget** section:

```text
### Performance budget
| Metric (p75, mobile) | Now (source, date)     | Target  | Biggest lever (measured saving)      |
| -------------------- | ---------------------- | ------- | ------------------------------------ |
| LCP                  | 3.4 s (2026-09) [CRUX]   | < 2.5 s | preload hero image (-0.9 s) [PSI]    |
| INP                  | 240 ms [CRUX]          | < 200 ms| split vendor bundle (-80 ms) [CDT]   |
| JS shipped           | 410 kB gz [BP]         | < 200 kB| drop moment.js (-67 kB) [BP]         |
```

## Pathway mapping

- pathway-operating-layer: `quality`, `observability` (keep measuring after release).
- development-protocol rows: `research`, `verify` (the budget is a check), `review`.
